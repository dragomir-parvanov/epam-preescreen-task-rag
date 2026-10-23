"""Scoring for the full LLM eval (#16, #29): pure functions over what one Turn produced.

`evaluation.eval_llm` runs each Golden Question through the real `ChatService` and feeds the
result here as a `TurnRun`; nothing here touches I/O. All Section-level matching goes through
the Golden Question's resolved `ExpectedSections`, so citing or retrieving any alternative
Section of a source counts for it.
"""

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from app.chat.schemas import Answer, ChatResult, Refusal, UncitedAnswer
from app.chat_model import TokenUsage
from app.prompts import GAP_PHRASE
from evaluation.fact_sheet import mentions
from evaluation.golden import GoldenQuestion, TermGroups
from evaluation.retrieval_scoring import ExpectedSections, SectionKey

type Expected = Literal["answer", "partial", "refusal"]
type Outcome = Literal["answer", "partial", "refusal", "error"]
type Blame = Literal["retrieval", "model", "error"]
"""Why an outcome was wrong. `retrieval`: a Refusal or gap while an expected Section wasn't
retrieved, so the model never saw it (ADR-0001). `model`: anything else the model decided.
`error`: the Turn failed (`rewrite_failed`, `llm_unavailable`, ...)."""

NO_USAGE = TokenUsage(input_tokens=0, output_tokens=0)


@dataclass(frozen=True, slots=True, kw_only=True)
class TurnRun:
    """What one Golden Question's Turn produced, as read from its event stream."""

    result: ChatResult | None
    """What `done` carried; None when the Turn failed."""
    error: str | None = None
    """The failed Turn's error code."""
    retrieved: tuple[SectionKey, ...] = ()
    """The Sections of the `passages` event, in rank order."""
    standalone_question: str | None = None
    """What the `rewritten` event carried (Follow-ups only)."""
    latency_ms: float
    ttft_ms: float | None = None
    usage: TokenUsage = NO_USAGE
    """The Turn's model calls together: the rewrite and the generation."""


@dataclass(frozen=True, slots=True, kw_only=True)
class QuestionScore:
    question: GoldenQuestion
    expected: Expected
    outcome: Outcome
    outcome_correct: bool
    blame: Blame | None
    """None when the outcome is right."""
    refusal_reason: str | None
    error: str | None
    uncited: bool
    text: str
    """The Answer's text; empty for a Refusal or a failed Turn."""
    cited: tuple[SectionKey, ...]
    """The distinct Sections the Answer cites, in order of first Citation."""
    citation_precision: float | None
    """Of the cited Sections, the share that are expected. None when nothing is cited, or the
    question is unanswerable."""
    citation_recall: float | None
    """Of the expected sources, the share cited. None for an unanswerable question."""
    retrieval_recall: float | None
    """Of the expected sources, the share retrieved. None for an unanswerable question."""
    mentions_hit: int
    mentions_total: int
    missed_terms: tuple[str, ...]
    """The first term of each `must_mention` group the Answer missed."""
    standalone_question: str | None
    standalone_hit: int
    standalone_total: int
    latency_ms: float
    ttft_ms: float | None
    usage: TokenUsage

    @property
    def id(self) -> str:
        return self.question.id

    @property
    def known_miss(self) -> bool:
        return self.question.known_retrieval_miss is not None


def has_gap(text: str) -> bool:
    """Whether an Answer's text states the gap phrase (#42): anywhere, in any case, with a
    straight or curly apostrophe. Never asked of a Refusal, whose message starts alike."""
    return _normalise(GAP_PHRASE).casefold() in _normalise(text).casefold()


def score_turn(question: GoldenQuestion, expected: ExpectedSections, run: TurnRun) -> QuestionScore:
    result = run.result
    expected_outcome = _expected_outcome(question)
    outcome, text = _outcome(result)
    correct = outcome == expected_outcome

    cited: tuple[SectionKey, ...] = ()
    if isinstance(result, Answer):
        keys = (SectionKey(c.passage.article.id, c.passage.section.id) for c in result.citations)
        cited = tuple(dict.fromkeys(keys))
    answerable = question.answerable
    retrieval_recall = _share_found(expected, run.retrieved) if answerable else None
    hit, missed = _mentions(text, question.must_mention)
    standalone_hit, _ = _mentions(run.standalone_question or "", question.standalone_must_mention)

    return QuestionScore(
        question=question,
        expected=expected_outcome,
        outcome=outcome,
        outcome_correct=correct,
        blame=None if correct else _blame(outcome, retrieval_recall),
        refusal_reason=result.reason if isinstance(result, Refusal) else None,
        error=run.error if result is None else None,
        uncited=isinstance(result, UncitedAnswer),
        text=text,
        cited=cited,
        citation_precision=_precision(cited, expected) if answerable and cited else None,
        citation_recall=_share_found(expected, cited) if answerable else None,
        retrieval_recall=retrieval_recall,
        mentions_hit=hit,
        mentions_total=len(question.must_mention),
        missed_terms=missed,
        standalone_question=run.standalone_question,
        standalone_hit=standalone_hit,
        standalone_total=len(question.standalone_must_mention),
        latency_ms=run.latency_ms,
        ttft_ms=run.ttft_ms,
        usage=run.usage,
    )


def _expected_outcome(question: GoldenQuestion) -> Expected:
    if not question.answerable:
        return "refusal"
    return "partial" if question.category == "partial" else "answer"


def _outcome(result: ChatResult | None) -> tuple[Outcome, str]:
    match result:
        case None:
            return "error", ""
        case Refusal():
            return "refusal", ""
        case Answer() | UncitedAnswer():
            return ("partial" if has_gap(result.text) else "answer"), result.text


def _blame(outcome: Outcome, retrieval_recall: float | None) -> Blame:
    if outcome == "error":
        return "error"
    missed_a_source = retrieval_recall is not None and retrieval_recall < 1
    if missed_a_source and outcome in ("refusal", "partial"):
        return "retrieval"
    return "model"


def _share_found(expected: ExpectedSections, found: Iterable[SectionKey]) -> float | None:
    if not expected:
        return None
    present = set(found)
    return sum(1 for group in expected if present.intersection(group)) / len(expected)


def _precision(cited: Sequence[SectionKey], expected: ExpectedSections) -> float:
    options = {key for group in expected for key in group}
    return sum(1 for key in cited if key in options) / len(cited)


def _mentions(text: str, groups: TermGroups) -> tuple[int, tuple[str, ...]]:
    """(groups hit, the first term of each group missed). Whole words, case-insensitive."""
    normalised = _normalise(text)
    missed = tuple(
        group[0]
        for group in groups
        if not any(mentions(normalised, _normalise(term)) for term in group)
    )
    return len(groups) - len(missed), missed


def _normalise(text: str) -> str:
    return text.replace("’", "'").replace("‘", "'")


# --- Totals -------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class Totals:
    questions: int
    outcome_accuracy: float | None
    citation_precision: float | None
    """Mean over the answerable questions whose Answer cites a Section."""
    citation_recall: float | None
    """Mean over the answerable questions; a Refusal or an Uncited Answer scores 0."""
    retrieval_recall: float | None
    """Mean over the answerable questions."""
    uncited_rate: float | None
    """Uncited Answers among all Answers."""
    must_mention_rate: float | None
    """`must_mention` groups hit, over all the groups of the answerable questions."""
    standalone_rate: float | None
    """`standalone_must_mention` groups hit, over the Follow-ups' groups."""
    refusals: tuple[int, int]
    """(unanswerable questions refused, unanswerable questions)."""
    false_refusals: int
    """Answerable questions refused."""
    errors: int
    latency_p50_ms: float | None
    latency_p95_ms: float | None
    ttft_p50_ms: float | None
    usage: TokenUsage


def totals(scores: Sequence[QuestionScore]) -> Totals:
    answerable = [s for s in scores if s.question.answerable]
    unanswerable = [s for s in scores if not s.question.answerable]
    answers = [s for s in scores if s.outcome in ("answer", "partial")]
    latencies = [s.latency_ms for s in scores]
    return Totals(
        questions=len(scores),
        outcome_accuracy=_mean([float(s.outcome_correct) for s in scores]),
        citation_precision=_mean([s.citation_precision for s in answerable]),
        citation_recall=_mean([s.citation_recall for s in answerable]),
        retrieval_recall=_mean([s.retrieval_recall for s in answerable]),
        uncited_rate=_mean([float(s.uncited) for s in answers]),
        must_mention_rate=_ratio(
            sum(s.mentions_hit for s in scores), sum(s.mentions_total for s in scores)
        ),
        standalone_rate=_ratio(
            sum(s.standalone_hit for s in scores), sum(s.standalone_total for s in scores)
        ),
        refusals=(sum(1 for s in unanswerable if s.outcome == "refusal"), len(unanswerable)),
        false_refusals=sum(1 for s in answerable if s.outcome == "refusal"),
        errors=sum(1 for s in scores if s.outcome == "error"),
        latency_p50_ms=percentile(latencies, 50),
        latency_p95_ms=percentile(latencies, 95),
        ttft_p50_ms=percentile([s.ttft_ms for s in scores if s.ttft_ms is not None], 50),
        usage=TokenUsage(
            input_tokens=sum(s.usage.input_tokens for s in scores),
            output_tokens=sum(s.usage.output_tokens for s in scores),
        ),
    )


def percentile(values: Sequence[float], p: float) -> float | None:
    """The nearest-rank percentile: the smallest value at least p% of `values` are at or below."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(math.ceil(p / 100 * len(ordered)), 1) - 1]


def _mean(values: Iterable[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def _ratio(hit: int, total: int) -> float | None:
    return hit / total if total else None
