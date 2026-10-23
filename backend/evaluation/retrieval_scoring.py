"""Scoring for the keyless retrieval eval (#16, #28): pure functions over retrieved Passages.

`evaluation.eval_retrieval` runs the real embedder and feeds these; they never touch I/O.
"""

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Final, Literal

from app.answer_assembly import gate_retrieval
from app.knowledge_base import Article, article_sections
from app.passages import Passage
from evaluation.golden import GoldenQuestion

type Origin = Literal["curated", "generated"]
type Run = Literal["hybrid", "dense-only", "no-prefix"]

# The rules from Chunking & retrieval strategy (#12). k and min_score are values, in Settings.
RECALL_BARS: Final[dict[Origin, float]] = {"curated": 1.0, "generated": 0.95}
MAX_TOP_K: Final = 8
"""k is capped here: not meeting the bars at 8 is the trigger for a reranker, not a bigger k."""
TOP_K_HEADROOM: Final = 2
MIN_SCORE_MARGIN: Final = 0.05

# Golden `expected_sources` name a Section by its heading path below the Article title.
_PATH_SEPARATOR = " > "


@dataclass(frozen=True, slots=True)
class SectionKey:
    """A Section as retrieved Passages name it: Article id + Section id (a path slug)."""

    article: str
    section: str


type ExpectedSections = tuple[tuple[SectionKey, ...], ...]
"""One group per expected source: the Section and its alternatives, any one of which counts."""


class UnresolvedSourcesError(ValueError):
    def __init__(self, unresolved: Sequence[str]) -> None:
        self.unresolved = tuple(unresolved)
        super().__init__(
            "expected_sources that name no Section a Passage can cite:\n  "
            + "\n  ".join(self.unresolved)
        )


def resolve_expected_sources(
    questions: Iterable[GoldenQuestion], articles: Iterable[Article]
) -> dict[str, ExpectedSections]:
    """Each question's `expected_sources` (alternatives included) as the Section ids its Passages
    carry, by question id.

    Resolved through `app.knowledge_base.article_sections`, the Sections ingestion splits into
    Passages, so a heading with no text of its own (no Passage) doesn't resolve.
    """
    section_ids = {
        (article.id, _PATH_SEPARATOR.join(section.path[1:])): section.id
        for article in articles
        for section in article_sections(article)
    }
    resolved: dict[str, ExpectedSections] = {}
    unresolved: list[str] = []
    for question in questions:
        groups: list[tuple[SectionKey, ...]] = []
        for source in question.expected_sources:
            group: list[SectionKey] = []
            for option in source.options:
                section_id = section_ids.get((option.article, option.section))
                if section_id is None:
                    unresolved.append(f"{question.id}: {option.article} > {option.section}")
                else:
                    group.append(SectionKey(option.article, section_id))
            groups.append(tuple(group))
        resolved[question.id] = tuple(groups)
    if unresolved:
        raise UnresolvedSourcesError(unresolved)
    return resolved


def sources_rank(expected: ExpectedSections, ranking: Sequence[Passage]) -> int | None:
    """The smallest k whose top k Passages hold a Section of every expected group; None if
    `ranking` doesn't. A Section counts once any of its Passages is there."""
    first_rank: dict[SectionKey, int] = {}
    for rank, passage in enumerate(ranking, start=1):
        first_rank.setdefault(SectionKey(passage.article.id, passage.section.id), rank)
    group_ranks: list[int] = []
    for group in expected:
        ranks = [first_rank[key] for key in group if key in first_rank]
        if not ranks:
            return None
        group_ranks.append(min(ranks))
    return max(group_ranks, default=0)


@dataclass(frozen=True, slots=True, kw_only=True)
class QuestionRetrieval:
    """One Golden Question's rankings, each at least `MAX_TOP_K` deep. A follow-up is searched
    with its `standalone_question`."""

    question: GoldenQuestion
    expected: ExpectedSections
    hybrid: tuple[Passage, ...]
    """What the server retrieves: hybrid, with bge's query prefix."""
    dense_only: tuple[Passage, ...]
    """The ablation: the dense leg alone. Its first Passage holds the dense top-1 cosine."""
    no_prefix: tuple[Passage, ...]
    """Hybrid, with the query embedded without bge's prefix."""

    @property
    def id(self) -> str:
        return self.question.id

    def rank(self, ranking: Sequence[Passage] | None = None) -> int | None:
        """`sources_rank` in `ranking`, by default the hybrid one."""
        return sources_rank(self.expected, self.hybrid if ranking is None else ranking)


def recall_at_k(
    retrievals: Sequence[QuestionRetrieval], k: int, ranking: Run = "hybrid"
) -> tuple[int, int]:
    """(questions whose top k hold all their expected Sections, questions) over `retrievals`."""
    found = [r for r in retrievals if _found_within(r.rank(_ranking(r, ranking)), k)]
    return len(found), len(retrievals)


def _found_within(rank: int | None, k: int) -> bool:
    return rank is not None and rank <= k


def gate_refuses(retrieval: QuestionRetrieval, *, top_k: int, min_score: float) -> bool:
    """Whether `ChatService`'s threshold gate refuses before calling the model."""
    return gate_retrieval(retrieval.hybrid[:top_k], min_score) is not None


def top_score(passages: Sequence[Passage]) -> float:
    return max((passage.score for passage in passages), default=0.0)


def answerable(retrievals: Iterable[QuestionRetrieval], origin: Origin) -> list[QuestionRetrieval]:
    """The answerable questions of `origin` that the recall bars count: all but known misses."""
    return [
        r
        for r in retrievals
        if r.question.answerable
        and r.question.origin == origin
        and r.question.known_retrieval_miss is None
    ]


def known_misses(retrievals: Iterable[QuestionRetrieval]) -> list[QuestionRetrieval]:
    return [r for r in retrievals if r.question.known_retrieval_miss is not None]


def failures(retrievals: Sequence[QuestionRetrieval], *, top_k: int, min_score: float) -> list[str]:
    """What breaks the CI bars (#12), one line each; empty when the eval passes.

    Unanswerable questions never fail it: whether the gate catches them is only reported.
    """
    problems: list[str] = []
    for origin, bar in RECALL_BARS.items():
        group = answerable(retrievals, origin)
        found, total = recall_at_k(group, top_k)
        if total and found / total < bar:
            missed = ", ".join(r.id for r in group if not _found_within(r.rank(), top_k))
            problems.append(
                f"{origin} recall@{top_k} is {found / total:.1%} ({found}/{total}), "
                f"below {bar:.0%}: {missed}"
            )
    refused = [
        r
        for r in retrievals
        if r.question.answerable and gate_refuses(r, top_k=top_k, min_score=min_score)
    ]
    if refused:
        listed = ", ".join(f"{r.id} ({top_score(r.hybrid[:top_k]):.3f})" for r in refused)
        problems.append(
            f"the gate (min_score {min_score}) refuses {len(refused)} answerable "
            f"question{'s' if len(refused) > 1 else ''}: {listed}"
        )
    return problems


@dataclass(frozen=True, slots=True, kw_only=True)
class Calibration:
    """The #12 rules applied to a run. The committed Settings defaults are set from it by hand."""

    smallest_k: int | None
    """The smallest k (up to `MAX_TOP_K`) that meets the recall bars; None if none does."""
    top_k: int | None
    """`smallest_k` + headroom, capped at `MAX_TOP_K`; None when the bars fail at the cap."""
    weakest: QuestionRetrieval
    """The answerable question with the lowest dense top-1 cosine."""
    min_score: float
    """That cosine minus the margin, rounded down to 2 places."""


def calibrate(retrievals: Sequence[QuestionRetrieval]) -> Calibration:
    smallest_k = next(
        (k for k in range(1, MAX_TOP_K + 1) if _meets_recall_bars(retrievals, k)), None
    )
    weakest = min(
        (r for r in retrievals if r.question.answerable), key=lambda r: top_score(r.dense_only)
    )
    margin_below = round((top_score(weakest.dense_only) - MIN_SCORE_MARGIN) * 100, 6)
    return Calibration(
        smallest_k=smallest_k,
        top_k=None if smallest_k is None else min(smallest_k + TOP_K_HEADROOM, MAX_TOP_K),
        weakest=weakest,
        min_score=math.floor(margin_below) / 100,
    )


def _meets_recall_bars(retrievals: Sequence[QuestionRetrieval], k: int) -> bool:
    for origin, bar in RECALL_BARS.items():
        found, total = recall_at_k(answerable(retrievals, origin), k)
        if total and found / total < bar:
            return False
    return True


def _ranking(retrieval: QuestionRetrieval, run: Run) -> tuple[Passage, ...]:
    match run:
        case "hybrid":
            return retrieval.hybrid
        case "dense-only":
            return retrieval.dense_only
        case "no-prefix":
            return retrieval.no_prefix


RUNS: Final[tuple[Run, ...]] = ("hybrid", "dense-only", "no-prefix")
LOWEST_SHOWN: Final = 5


def render_report(retrievals: Sequence[QuestionRetrieval], *, top_k: int, min_score: float) -> str:
    """The per-question table, the reported comparisons, the calibration and the verdict.

    A rank is the depth at which all of a question's expected Sections are in, `-` if they
    aren't within `MAX_TOP_K`. "top-1" is the dense top-1 cosine. The gate column is what
    `ChatService` does with the hybrid top k at `min_score`; REFUSED marks a failure.
    """
    title = f"Retrieval eval: top_k={top_k}, min_score={min_score}, {len(retrievals)} questions"
    header = ("question", "origin", "category", *RUNS, "top-1", "gate", "note")
    rows = [header, *(_question_row(r, top_k=top_k, min_score=min_score) for r in retrievals)]

    ks = range(1, MAX_TOP_K + 1)
    recall_rows: list[tuple[str, ...]] = [("recall@k", "run", *(str(k) for k in ks))]
    for origin in RECALL_BARS:
        group = answerable(retrievals, origin)
        for run in RUNS:
            recall_rows.append((origin, run, *(_percent(recall_at_k(group, k, run)) for k in ks)))

    weakest = sorted(
        (r for r in retrievals if r.question.answerable), key=lambda r: top_score(r.dense_only)
    )[:LOWEST_SHOWN]
    problems = failures(retrievals, top_k=top_k, min_score=min_score)
    sections = [
        [title, "=" * len(title)],
        _table(rows),
        _table(recall_rows),
        _prefix_comparison(retrievals),
        _known_misses(retrievals, top_k=top_k),
        _gate_on_unanswerables(retrievals, top_k=top_k, min_score=min_score),
        [
            f"The {len(weakest)} answerable questions with the lowest dense top-1:",
            *(f"  {top_score(r.dense_only):.3f} {r.id}: {_searched(r)}" for r in weakest),
        ],
        _calibration(retrievals),
        ["FAIL", *(f"- {problem}" for problem in problems)] if problems else ["PASS"],
    ]
    return "\n\n".join("\n".join(section) for section in sections)


def _question_row(retrieval: QuestionRetrieval, *, top_k: int, min_score: float) -> tuple[str, ...]:
    gq = retrieval.question
    if gq.answerable:
        ranks = tuple(_rank(retrieval.rank(_ranking(retrieval, run))) for run in RUNS)
    else:
        ranks = ("",) * len(RUNS)
    refused = gate_refuses(retrieval, top_k=top_k, min_score=min_score)
    gate = "refused" if refused else "answered"
    if refused and gq.answerable:
        gate = gate.upper()
    return (
        retrieval.id,
        gq.origin,
        gq.category,
        *ranks,
        f"{top_score(retrieval.dense_only):.3f}",
        gate,
        "known miss" if gq.known_retrieval_miss else "",
    )


def _known_misses(retrievals: Sequence[QuestionRetrieval], *, top_k: int) -> list[str]:
    lines = ["Known retrieval misses, left out of the recall bars:"]
    for retrieval in known_misses(retrievals):
        rank = retrieval.rank()
        status = _rank(rank)
        if _found_within(rank, top_k):
            status += ", now found: drop the mark?"
        lines.append(
            f"  {retrieval.id} (hybrid rank {status}): {retrieval.question.known_retrieval_miss}"
        )
    return lines if len(lines) > 1 else ["No known retrieval misses."]


def _prefix_comparison(retrievals: Sequence[QuestionRetrieval]) -> list[str]:
    lines = ["Mean top score (the gate's input, in the top MAX_TOP_K), bge query prefix on vs off:"]
    for label, keep in (("answerable", True), ("unanswerable", False)):
        group = [r for r in retrievals if r.question.answerable is keep]
        if not group:
            continue
        on = sum(top_score(r.hybrid) for r in group) / len(group)
        off = sum(top_score(r.no_prefix) for r in group) / len(group)
        lines.append(f"  {label}: on {on:.3f}, off {off:.3f}")
    return lines


def _gate_on_unanswerables(
    retrievals: Sequence[QuestionRetrieval], *, top_k: int, min_score: float
) -> list[str]:
    group = [r for r in retrievals if not r.question.answerable]
    if not group:
        return ["No unanswerable questions."]
    caught = [r for r in group if gate_refuses(r, top_k=top_k, min_score=min_score)]
    lines = [
        f"The gate refuses {len(caught)} of {len(group)} unanswerable questions "
        f"({len(caught) / len(group):.1%})."
    ]
    lines += [
        f"  {top_score(r.hybrid[:top_k]):.3f} {'refused ' if r in caught else 'answered'} {r.id}"
        for r in sorted(group, key=lambda r: top_score(r.hybrid[:top_k]), reverse=True)
    ]
    return lines


def _calibration(retrievals: Sequence[QuestionRetrieval]) -> list[str]:
    calibration = calibrate(retrievals)
    if calibration.smallest_k is None:
        k_line = f"No k up to {MAX_TOP_K} meets the recall bars: the trigger for a reranker (#12)."
    else:
        k_line = (
            f"Smallest k meeting the recall bars: {calibration.smallest_k}; "
            f"with headroom, top_k = {calibration.top_k}."
        )
    weakest = calibration.weakest
    return [
        "Calibration (#12):",
        f"  {k_line}",
        f"  Lowest answerable dense top-1: {top_score(weakest.dense_only):.3f} ({weakest.id}); "
        f"min_score = {calibration.min_score}.",
    ]


def _searched(retrieval: QuestionRetrieval) -> str:
    return retrieval.question.standalone_question or retrieval.question.question


def _rank(rank: int | None) -> str:
    return "-" if rank is None else str(rank)


def _percent(found_of: tuple[int, int]) -> str:
    found, total = found_of
    return f"{found / total:.1%}" if total else "n/a"


def _table(rows: Sequence[Sequence[str]]) -> list[str]:
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    return [
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True)).rstrip()
        for row in rows
    ]
