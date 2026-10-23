"""Answer assembly: turn the model's raw text into an Answer, an Uncited Answer or a Refusal.

Framework-free. The spec is ADR-0001 and the resolutions of #7 and #19.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final, Literal

from app.passages import Passage

NOT_IN_KNOWLEDGE_BASE: Final = "NOT_IN_KNOWLEDGE_BASE"
"""The Refusal sentinel the prompt tells the model to reply with when no Passage answers."""

REFUSAL_MESSAGE: Final = "The Knowledge Base doesn't cover this question."
"""What the CSM sees for any Refusal, never the model's own words."""

type RefusalReason = Literal["no_relevant_passages", "not_in_context"]


@dataclass(frozen=True, slots=True, kw_only=True)
class Citation:
    n: int
    """The marker number in the Answer text, `[n]`."""
    passage: Passage


@dataclass(frozen=True, slots=True, kw_only=True)
class Answer:
    text: str
    citations: tuple[Citation, ...]
    retrieved_passages: tuple[Passage, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class UncitedAnswer:
    """An Answer with no valid Citations: shown with a warning, never backfilled (ADR-0001)."""

    text: str
    retrieved_passages: tuple[Passage, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class Refusal:
    """The Knowledge Base doesn't cover the question. Carries no Citations."""

    reason: RefusalReason
    """`no_relevant_passages`: the retrieval gate refused. `not_in_context`: the model did."""
    retrieved_passages: tuple[Passage, ...]

    @property
    def message(self) -> str:
        return REFUSAL_MESSAGE


type Reply = Answer | UncitedAnswer | Refusal
"""What a Turn ends in. The HTTP layer maps it onto the wire `ChatResult` union."""

_LATER_SENTINEL = re.compile(rf"[ \t]*{NOT_IN_KNOWLEDGE_BASE}")

# One marker: `[n]` or a comma list `[n, m]`.
# Anything else (`[doc2]`, `[1-3]`, `[^1]`) is plain text and left as written.
_MARKER = r"\[\s*\d+(?:\s*,\s*\d+)*\s*\]"
# A cluster: adjacent markers such as `[2][5]`, with the spaces before them.
_CLUSTER = re.compile(rf"(?P<space>[ \t]*)(?P<markers>(?:{_MARKER})+)")
_NUMBER = re.compile(r"\d+")


def gate_retrieval(passages: Sequence[Passage], min_score: float) -> Refusal | None:
    """The retrieval-threshold gate, run before the model is called.

    Returns a `no_relevant_passages` Refusal when no Passage scores at least `min_score`
    (including when none were retrieved), else None: go ahead and ask the model.
    """
    if any(passage.score >= min_score for passage in passages):
        return None
    return Refusal(reason="no_relevant_passages", retrieved_passages=tuple(passages))


def assemble_reply(model_text: str, passages: Sequence[Passage]) -> Reply:
    """Turn the model's raw text into an Answer, an Uncited Answer or a Refusal.

    `passages` are the Passages exactly as numbered in the prompt: `[n]` is `passages[n - 1]`.
    They come back unchanged as `retrieved_passages` on every result.

    - A reply that starts (after trimming) with `NOT_IN_KNOWLEDGE_BASE` is a `not_in_context`
      Refusal, whatever follows. The sentinel anywhere later is stripped.
    - Markers are `[n]`, adjacent `[n][m]` and comma lists `[n, m]`. Numbers that point at no
      Passage are dropped, as are repeats within one cluster of markers.
    - The cited Passages are renumbered `[1]..[k]` in order of first appearance, and the text
      is rewritten to match. Citations are exactly those Passages, one each, ordered by `n`.
    - No valid marker left: an Uncited Answer. Retrieved Passages are never promoted to
      Citations (ADR-0001).
    """
    retrieved = tuple(passages)
    if model_text.strip().startswith(NOT_IN_KNOWLEDGE_BASE):
        return Refusal(reason="not_in_context", retrieved_passages=retrieved)
    model_text = _LATER_SENTINEL.sub("", model_text)

    # Prompt number -> Citation number, in order of first appearance.
    renumbered: dict[int, int] = {}

    def renumber(cluster: re.Match[str]) -> str:
        prompt_ns = (int(number) for number in _NUMBER.findall(cluster["markers"]))
        valid = dict.fromkeys(n for n in prompt_ns if 1 <= n <= len(passages))
        if not valid:
            return ""  # with the space before it, so no "Settings ." is left behind
        ns = (renumbered.setdefault(prompt_n, len(renumbered) + 1) for prompt_n in valid)
        return cluster["space"] + "".join(f"[{n}]" for n in ns)

    text = _CLUSTER.sub(renumber, model_text).strip()
    if not renumbered:
        return UncitedAnswer(text=text, retrieved_passages=retrieved)
    citations = tuple(
        Citation(n=n, passage=passages[prompt_n - 1]) for prompt_n, n in renumbered.items()
    )
    return Answer(text=text, citations=citations, retrieved_passages=retrieved)
