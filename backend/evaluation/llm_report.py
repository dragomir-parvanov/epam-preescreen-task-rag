"""The full LLM eval's report (#29): a Markdown summary and a machine-readable JSON, both stamped
with what the run ran with. Pure: `evaluation.eval_llm` prints and writes them.

The headline and the per-category table leave the known retrieval misses out: their Sections are
never retrieved, so they measure retrieval, not the model (#28). They get a section of their own.
"""

import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any, Final

from app.chat_model import TokenUsage
from evaluation.llm_scoring import QuestionScore, Totals, totals

PRICES_PER_MTOK: Final[dict[str, tuple[float, float]]] = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-haiku-5-5": (0.10, 0.50),
}
"""(input, output) list prices in USD per million tokens, October 2026. Thinking is billed as
output. Haiku's price holds for prompts up to 100K tokens, far above ours."""


@dataclass(frozen=True, slots=True, kw_only=True)
class RunInfo:
    date: str
    git_sha: str
    provider: str
    model: str
    effort: str | None
    """Claude's `output_config.effort`; None for a provider without one."""
    prompt_version: str
    top_k: int
    min_score: float
    question_set: str
    """`curated`, `all`, or `selected` for a hand-picked `--only` run."""
    concurrency: int = 1
    """Turns run at a time. Above 1, latency includes waiting for the shared index."""


def report_stem(info: RunInfo) -> str:
    """The report's file name, without its extension."""
    model = re.sub(r"[^A-Za-z0-9.-]+", "-", info.model)
    return f"{info.provider}-{model}-{info.prompt_version}-{info.question_set}"


def cost_usd(model: str, usage: TokenUsage) -> float | None:
    """What `usage` costs at `model`'s list price; None for a model without one (Ollama)."""
    if model not in PRICES_PER_MTOK:
        return None
    input_price, output_price = PRICES_PER_MTOK[model]
    return (usage.input_tokens * input_price + usage.output_tokens * output_price) / 1_000_000


def _split(scores: Sequence[QuestionScore]) -> tuple[list[QuestionScore], list[QuestionScore]]:
    return [s for s in scores if not s.known_miss], [s for s in scores if s.known_miss]


# --- Markdown -----------------------------------------------------------------------------------


def render_markdown(info: RunInfo, scores: Sequence[QuestionScore]) -> str:
    scored, known = _split(scores)
    summary = totals(scored)
    title = f"# LLM eval: {info.provider} {info.model}, prompt {info.prompt_version}"
    effort = f" (effort {info.effort})" if info.effort else ""
    run_cost = cost_usd(info.model, totals(scores).usage)
    sections = [
        [
            title,
            "",
            *_table(
                ("Run", ""),
                [
                    ("Date", info.date),
                    ("Git SHA", info.git_sha),
                    ("Provider", info.provider),
                    ("Model", f"{info.model}{effort}"),
                    ("Prompt version", info.prompt_version),
                    ("Retrieval", f"hybrid, top_k {info.top_k}, min_score {info.min_score}"),
                    ("Questions", f"{info.question_set} ({len(scores)} questions)"),
                    ("Concurrency", f"{info.concurrency} Turn(s) at a time"),
                ],
            ),
        ],
        [
            "## Headline",
            "",
            f"Over {summary.questions} questions: the {len(known)} known retrieval misses are "
            "reported apart below.",
            "",
            *_table(("Metric", "Value"), _headline(summary, info.model)),
            "",
            f"Whole run, known misses included: {_tokens(totals(scores).usage)}"
            + (f", ${run_cost:.2f}." if run_cost is not None else "."),
        ],
        ["## By category", "", *_by_category(scored)],
        ["## Wrong outcomes", "", *_wrong_outcomes(scored)],
        ["## Missed must_mention terms", "", *_missed_terms(scored)],
        ["## Known retrieval misses", "", *_known_misses(known)],
        ["## Every question", "", *_every_question(scores)],
        [_DEFINITIONS],
    ]
    return "\n\n".join("\n".join(section) for section in sections) + "\n"


_DEFINITIONS: Final = """\
## How it is scored

- **Outcome**: an unanswerable question expects a Refusal, a `partial` one an Answer stating \
the gap phrase (`GAP_PHRASE`, anywhere, any case, either apostrophe), any other an Answer \
without it. An Uncited Answer counts as an Answer. A failed Turn (`rewrite_failed`, \
`llm_unavailable`, ...) is an `error`.
- **Blame** for a wrong outcome: `retrieval` when it is a Refusal or a gap and an expected \
Section wasn't retrieved, so the model never saw it; `model` otherwise; `error` for a failed Turn.
- **Citation precision and recall** are at Section level, over distinct Sections; citing any \
alternative of an expected source counts for it. Precision averages over the Answers that cite \
something; recall over the answerable questions, where a Refusal or an Uncited Answer scores 0.
- **Retrieval recall**: the share of expected sources with any option among the retrieved \
Passages.
- **must_mention**: whole-word, case-insensitive term groups (any term in a group counts), \
over every group of the answerable questions. **Standalone** checks a Follow-up's \
`standalone_must_mention` against its rewrite.
- **Latency** is the whole Turn, rewrite included; **TTFT** is to the first streamed token.
- **Cost** is at list price from the providers' reported token usage. A model Refusal \
(`not_in_context`) stops its stream at the sentinel, before the provider reports usage, so its \
generation call isn't charged: each one is under-counted by its prompt (about 3K input tokens)."""


def _headline(summary: Totals, model: str) -> list[tuple[str, str]]:
    refused, unanswerable = summary.refusals
    cost = cost_usd(model, summary.usage)
    per_question = ""
    if cost is not None and summary.questions:
        per_question = f" (${cost / summary.questions:.4f} a question)"
    correct = round((summary.outcome_accuracy or 0) * summary.questions)
    return [
        ("Outcome accuracy", f"{_pct(summary.outcome_accuracy)} ({correct}/{summary.questions})"),
        (
            "Refusal correctness",
            f"{refused}/{unanswerable} unanswerable refused; "
            f"{summary.false_refusals} answerable refused",
        ),
        ("Citation precision", _pct(summary.citation_precision)),
        ("Citation recall", _pct(summary.citation_recall)),
        ("Retrieval recall", _pct(summary.retrieval_recall)),
        ("Uncited rate", _pct(summary.uncited_rate)),
        ("must_mention hit rate", _pct(summary.must_mention_rate)),
        ("Standalone must_mention", _pct(summary.standalone_rate)),
        ("Errors", str(summary.errors)),
        ("Latency p50 / p95", f"{_s(summary.latency_p50_ms)} / {_s(summary.latency_p95_ms)}"),
        ("TTFT p50", _s(summary.ttft_p50_ms)),
        ("Tokens", _tokens(summary.usage)),
        ("Cost", "n/a" if cost is None else f"${cost:.2f}{per_question}"),
    ]


def _by_category(scores: Sequence[QuestionScore]) -> list[str]:
    categories = sorted({s.question.category for s in scores})
    rows: list[tuple[str, ...]] = []
    for category in categories:
        group = totals([s for s in scores if s.question.category == category])
        rows.append(
            (
                category,
                str(group.questions),
                _pct(group.outcome_accuracy),
                _pct(group.citation_precision),
                _pct(group.citation_recall),
                _pct(group.retrieval_recall),
                _pct(group.must_mention_rate),
                _s(group.latency_p50_ms),
            )
        )
    header = ("Category", "n", "Outcome", "Cit. P", "Cit. R", "Retr. R", "must_mention", "p50")
    return _table(header, rows)


def _got(score: QuestionScore) -> str:
    if score.outcome == "refusal":
        return f"refusal ({score.refusal_reason})"
    if score.outcome == "error":
        return f"error ({score.error})"
    return f"{score.outcome}{' (uncited)' if score.uncited else ''}"


def _wrong_outcomes(scores: Sequence[QuestionScore]) -> list[str]:
    wrong = [s for s in scores if not s.outcome_correct]
    if not wrong:
        return ["None."]
    rows = [
        (s.id, s.expected, _got(s), s.blame or "", _pct(s.retrieval_recall), _excerpt(s.text))
        for s in wrong
    ]
    return _table(("Question", "Expected", "Got", "Blame", "Retr. R", "Answer"), rows)


def _missed_terms(scores: Sequence[QuestionScore]) -> list[str]:
    """Among Answers: a Refusal or failed Turn misses every term, and is listed above."""
    missed = [s for s in scores if s.missed_terms and s.outcome in ("answer", "partial")]
    if not missed:
        return ["None."]
    rows = [(s.id, ", ".join(f"`{t}`" for t in s.missed_terms), _excerpt(s.text)) for s in missed]
    return _table(("Question", "Missed (first term of each group)", "Answer"), rows)


def _known_misses(scores: Sequence[QuestionScore]) -> list[str]:
    if not scores:
        return ["None in this run."]
    rows = [
        (
            s.id,
            s.expected,
            _got(s),
            _pct(s.retrieval_recall),
            s.question.known_retrieval_miss or "",
        )
        for s in scores
    ]
    return [
        "Their answering Sections are never retrieved, so expect a Refusal or a gap Answer.",
        "",
        *_table(("Question", "Expected", "Got", "Retr. R", "Why retrieval misses"), rows),
    ]


def _every_question(scores: Sequence[QuestionScore]) -> list[str]:
    rows = [
        (
            s.id,
            s.question.category + (" (known miss)" if s.known_miss else ""),
            s.expected,
            _got(s),
            "yes" if s.outcome_correct else "**no**",
            _pct(s.citation_precision),
            _pct(s.citation_recall),
            _pct(s.retrieval_recall),
            f"{s.mentions_hit}/{s.mentions_total}" if s.mentions_total else "",
            _s(s.latency_ms),
        )
        for s in scores
    ]
    header = (
        "Question",
        "Category",
        "Expected",
        "Got",
        "Right",
        "Cit. P",
        "Cit. R",
        "Retr. R",
        "Terms",
        "Latency",
    )
    return _table(header, rows)


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    def line(cells: Sequence[str]) -> str:
        return "| " + " | ".join(cells) + " |"

    return [line(header), line(["---"] * len(header)), *(line(row) for row in rows)]


def _pct(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.1%}" if 0 < value < 1 else f"{value:.0%}"


def _s(ms: float | None) -> str:
    return "-" if ms is None else f"{ms / 1000:.1f} s"


def _tokens(usage: TokenUsage) -> str:
    return f"{usage.input_tokens:,} input + {usage.output_tokens:,} output tokens"


def _excerpt(text: str, limit: int = 160) -> str:
    flat = " ".join(text.split()).replace("|", "\\|")
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


# --- JSON ---------------------------------------------------------------------------------------


def report_json(info: RunInfo, scores: Sequence[QuestionScore]) -> dict[str, Any]:
    scored, known = _split(scores)
    return {
        "run": asdict(info),
        "totals": _totals_json(totals(scored), info.model),
        "known_misses": _totals_json(totals(known), info.model),
        "by_category": {
            category: _totals_json(
                totals([s for s in scored if s.question.category == category]), info.model
            )
            for category in sorted({s.question.category for s in scored})
        },
        "questions": [_question_json(s) for s in scores],
    }


def _totals_json(summary: Totals, model: str) -> dict[str, Any]:
    data = asdict(summary)
    data["cost_usd"] = cost_usd(model, summary.usage)
    return data


_QUESTION_FIELDS: Final[tuple[str, ...]] = (
    "expected",
    "outcome",
    "outcome_correct",
    "blame",
    "refusal_reason",
    "error",
    "uncited",
    "citation_precision",
    "citation_recall",
    "retrieval_recall",
    "mentions_hit",
    "mentions_total",
    "missed_terms",
    "standalone_question",
    "standalone_hit",
    "standalone_total",
    "latency_ms",
    "ttft_ms",
    "text",
)


def _question_json(score: QuestionScore) -> dict[str, Any]:
    gq = score.question
    return {
        "id": gq.id,
        "origin": gq.origin,
        "category": gq.category,
        "known_retrieval_miss": gq.known_retrieval_miss is not None,
        "question": gq.question,
        **{name: getattr(score, name) for name in _QUESTION_FIELDS},
        "cited": [{"article": key.article, "section": key.section} for key in score.cited],
        "usage": asdict(score.usage),
    }
