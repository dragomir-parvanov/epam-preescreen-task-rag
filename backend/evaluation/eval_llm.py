"""`pixi run eval`: the full LLM eval (#16, #29). Opt-in, and never gates CI.

Runs Golden Questions in-process through the real `ChatService`: the real hybrid retriever over a
throwaway pgvector holding the whole Knowledge Base (the pinned image, so it needs Docker), and
the configured `ChatModel` (so it needs ANTHROPIC_API_KEY, or a pulled Ollama model). Each Turn
is read to `done` and scored by `evaluation.llm_scoring`; the report from `evaluation.llm_report`
goes to stdout, and to `eval/results/` as Markdown and JSON.

    pixi run eval                              # the 27 curated questions, the configured model
    pixi run eval --model claude-haiku-5-5     # another model of the configured provider
    pixi run eval --all --concurrency 4        # all 317 questions, 4 Turns at a time
    pixi run eval --only gq-ldap gq-auth-401   # a few questions; prints, writes no files

The provider, model, `top_k` and `min_score` come from `Settings` (.env and BACKEND_*), as the
server reads them. `fake` is refused: its canned reply measures nothing.
"""

import argparse
import asyncio
import json
import logging
import subprocess
import sys
import time
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import SecretStr

from app.chat.answering import AnsweringService
from app.chat.schemas import (
    ChatRequest,
    ChatResult,
    DoneEvent,
    HistoryTurn,
    PassagesEvent,
    RewrittenEvent,
    TokenEvent,
)
from app.chat.service import ChatService
from app.chat_model import TokenUsage
from app.config import Settings, load_settings
from app.errors import AppError
from app.knowledge_base import KNOWLEDGE_BASE_DIR, load_articles
from app.logs import configure_logging
from app.pgvector_testing import fresh_database, running_pgvector
from app.prompts import PROMPT_VERSION

# Imports Haystack, which must happen before `configure_logging` takes its logger over.
from app.rag.haystack.chat_model import CLAUDE_EFFORT, build_chat_model
from app.rag.haystack.index import PassageIndex
from app.rag.haystack.llm_probe import build_llm_probe
from evaluation.golden import GoldenQuestion, load_golden_questions
from evaluation.knowledge_base import REPO_ROOT
from evaluation.llm_report import RunInfo, render_markdown, report_json, report_stem
from evaluation.llm_scoring import QuestionScore, TurnRun, score_turn
from evaluation.retrieval_scoring import ExpectedSections, SectionKey, resolve_expected_sources

RESULTS_DIR = REPO_ROOT / "eval" / "results"

FAKE_PROVIDER = """\
BACKEND_LLM_PROVIDER is fake: its canned reply measures nothing, so the eval won't run on it.
Set BACKEND_LLM_PROVIDER=anthropic (with ANTHROPIC_API_KEY) or ollama in .env."""


# --- Usage per question -------------------------------------------------------------------------


@dataclass
class UsageMeter:
    """Charges each model call's usage to the question whose Turn made it.

    `on_usage` is the listener `build_chat_model` gets. The question is found through a context
    variable, so Turns running concurrently, each in a task of its own, never mix their usage.
    """

    _current: ContextVar[list[TokenUsage] | None] = field(
        default_factory=lambda: ContextVar("eval_usage", default=None)
    )

    def on_usage(self, usage: TokenUsage) -> None:
        if (calls := self._current.get()) is not None:
            calls.append(usage)

    @contextmanager
    def measuring(self) -> Generator[list[TokenUsage]]:
        calls: list[TokenUsage] = []
        token = self._current.set(calls)
        try:
            yield calls
        finally:
            self._current.reset(token)


# --- Running Turns ------------------------------------------------------------------------------


async def run_questions(
    questions: Sequence[GoldenQuestion],
    answering: AnsweringService,
    expected: dict[str, ExpectedSections],
    meter: UsageMeter,
    *,
    concurrency: int = 1,
    progress: Callable[[QuestionScore], None] | None = None,
) -> list[QuestionScore]:
    """Each question's Turn, read to `done` and scored, in the order of `questions`."""
    slots = asyncio.Semaphore(concurrency)

    async def one(question: GoldenQuestion) -> QuestionScore:
        async with slots:
            score = score_turn(
                question, expected[question.id], await run_turn(answering, question, meter)
            )
        if progress is not None:
            progress(score)
        return score

    # A task per question, so each has its own copy of the meter's context variable.
    return list(await asyncio.gather(*(asyncio.create_task(one(q)) for q in questions)))


async def run_turn(
    answering: AnsweringService, question: GoldenQuestion, meter: UsageMeter
) -> TurnRun:
    request = ChatRequest(
        question=question.question,
        history=[HistoryTurn(question=t.question, answer=t.answer) for t in question.history],
    )
    result: ChatResult | None = None
    error: str | None = None
    retrieved: tuple[SectionKey, ...] = ()
    standalone_question: str | None = None
    ttft_ms: float | None = None
    started = time.perf_counter()
    with meter.measuring() as calls:
        try:
            async for event in await answering.start_turn(request):
                match event:
                    case RewrittenEvent():
                        standalone_question = event.standalone_question
                    case PassagesEvent():
                        retrieved = tuple(
                            SectionKey(p.article.id, p.section.id) for p in event.passages
                        )
                    case TokenEvent():
                        if ttft_ms is None:
                            ttft_ms = _ms_since(started)
                    case DoneEvent():
                        result = event.result
        except AppError as failure:
            error = failure.code
    return TurnRun(
        result=result,
        error=error,
        retrieved=retrieved,
        standalone_question=standalone_question,
        latency_ms=_ms_since(started),
        ttft_ms=ttft_ms,
        usage=TokenUsage(
            input_tokens=sum(c.input_tokens for c in calls),
            output_tokens=sum(c.output_tokens for c in calls),
        ),
    )


def _ms_since(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 1)


def select_questions(
    questions: Sequence[GoldenQuestion], *, everything: bool = False, only: Sequence[str] = ()
) -> tuple[list[GoldenQuestion], str]:
    """The questions to run and the name of the set: `curated` by default, `all`, or the
    `selected` ids."""
    if only:
        by_id = {q.id: q for q in questions}
        if unknown := [id for id in only if id not in by_id]:
            raise ValueError(f"no Golden Question with id: {', '.join(unknown)}")
        return [by_id[id] for id in only], "selected"
    if everything:
        return list(questions), "all"
    return [q for q in questions if q.origin == "curated"], "curated"


# --- The command --------------------------------------------------------------------------------


async def evaluate(
    settings: Settings,
    questions: Sequence[GoldenQuestion],
    expected: dict[str, ExpectedSections],
    *,
    concurrency: int,
) -> list[QuestionScore]:
    health = await build_llm_probe(settings).probe()
    if health.problem is not None:
        fix = f" Fix: {health.command}" if health.command else ""
        sys.exit(
            f"The {settings.llm_provider} model {settings.llm_model} can't be used: "
            f"{health.problem}.{fix}"
        )
    meter = UsageMeter()
    with running_pgvector() as server, fresh_database(server) as url:
        database_url = SecretStr(url)
        async with await PassageIndex.open(database_url, top_k=settings.retrieval_top_k) as index:
            started = time.perf_counter()
            report = await index.sync(KNOWLEDGE_BASE_DIR)
            _progress(f"Indexed {len(report.written)} Passages in {_s_since(started)}.")
            service = ChatService(
                retriever=index,
                chat_model=build_chat_model(settings, on_usage=meter.on_usage),
                settings=settings,
            )
            started = time.perf_counter()
            done = 0

            def progress(score: QuestionScore) -> None:
                nonlocal done
                done += 1
                mark = "ok " if score.outcome_correct else "BAD"
                _progress(
                    f"[{done}/{len(questions)}] {mark} {score.id}: {score.outcome} "
                    f"in {score.latency_ms / 1000:.1f} s"
                )

            scores = await run_questions(
                questions, service, expected, meter, concurrency=concurrency, progress=progress
            )
            _progress(f"Ran {len(questions)} Turns in {_s_since(started)}.")
    return scores


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    settings = load_settings()  # exits with the fix when no LLM is configured
    if args.model:
        settings = settings.model_copy(update={"llm_model": args.model})
    if settings.llm_provider == "fake":
        sys.exit(FAKE_PROVIDER)
    # On stderr, so stdout is the report alone. Turns log at INFO; only problems are shown.
    configure_logging("console", "WARNING", stream=sys.stderr)
    logging.getLogger("haystack").setLevel(logging.WARNING)

    try:
        questions, question_set = select_questions(
            load_golden_questions(), everything=args.all, only=args.only
        )
    except ValueError as error:
        sys.exit(str(error))
    expected = resolve_expected_sources(questions, load_articles(KNOWLEDGE_BASE_DIR))
    info = RunInfo(
        date=datetime.now(UTC).isoformat(timespec="seconds"),
        git_sha=_git_sha(),
        provider=settings.llm_provider,
        model=settings.llm_model,
        effort=CLAUDE_EFFORT if settings.llm_provider == "anthropic" else None,
        prompt_version=PROMPT_VERSION,
        top_k=settings.retrieval_top_k,
        min_score=settings.retrieval_min_score,
        question_set=question_set,
        concurrency=args.concurrency,
    )
    _progress(f"Running {len(questions)} {question_set} questions on {info.model}.")
    try:
        scores = asyncio.run(evaluate(settings, questions, expected, concurrency=args.concurrency))
    except pytest.fail.Exception as error:  # running_pgvector found no Docker
        sys.exit(str(error))

    markdown = render_markdown(info, scores)
    print(markdown)
    if question_set != "selected":
        _write(args.out, info, markdown, scores)


def _write(out: Path, info: RunInfo, markdown: str, scores: Sequence[QuestionScore]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    stem = out / report_stem(info)
    stem.with_suffix(".md").write_text(markdown, encoding="utf-8")
    data = json.dumps(report_json(info, scores), indent=2, ensure_ascii=False)
    stem.with_suffix(".json").write_text(data + "\n", encoding="utf-8")
    _progress(f"Wrote {stem}.md and .json")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pixi run eval", description="The full LLM eval over the Golden Questions."
    )
    parser.add_argument(
        "--all", action="store_true", help="all questions, not just the curated ones"
    )
    parser.add_argument(
        "--only", nargs="+", default=[], metavar="ID", help="just these questions; writes no files"
    )
    parser.add_argument("--model", help="override BACKEND_LLM_MODEL for this run")
    parser.add_argument(
        "--concurrency", type=int, default=1, help="Turns at a time (default 1: clean latency)"
    )
    parser.add_argument(
        "--out", type=Path, default=RESULTS_DIR, help=f"report directory (default {RESULTS_DIR})"
    )
    return parser


def _git_sha() -> str:
    try:
        described = subprocess.run(
            ["git", "describe", "--always", "--dirty", "--abbrev=7"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return described.stdout.strip()


def _s_since(started: float) -> str:
    return f"{time.perf_counter() - started:.0f} s"


def _progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
