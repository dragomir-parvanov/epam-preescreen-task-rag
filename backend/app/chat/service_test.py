import asyncio
import json
from collections.abc import AsyncIterator, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

import pytest

from app.answer_assembly import REFUSAL_MESSAGE
from app.chat.answering import TurnEvent
from app.chat.schemas import (
    Answer,
    ChatRequest,
    Citation,
    DoneEvent,
    HistoryTurn,
    PassagesEvent,
    Refusal,
    RewrittenEvent,
    TokenEvent,
    wire_passage,
)
from app.chat.service import ChatService
from app.chat_model import Message
from app.config import Settings
from app.errors import AppError
from app.passages import ArticleRef, Passage, SectionRef
from app.prompts import PROMPT_VERSION, generation_messages, rewrite_messages

pytestmark = pytest.mark.anyio


def passage(n: int, score: float = 0.8) -> Passage:
    return Passage(
        id=f"sso-setup#{n}",
        article=ArticleRef(id="sso-setup", title="Setting up SSO"),
        section=SectionRef(id=f"section-{n}", path=("Setting up SSO", f"Section {n}")),
        text=f"Verbatim text of Passage {n}.",
        applies_to=("v3",),
        status="current",
        score=score,
    )


RETRIEVED = (passage(1), passage(2))
WIRE = [wire_passage(p) for p in RETRIEVED]


@dataclass
class FakeRetriever:
    passages: tuple[Passage, ...] = RETRIEVED
    error: Exception | None = None
    questions: list[str] = field(default_factory=list[str])

    async def retrieve(self, question: str) -> tuple[Passage, ...]:
        self.questions.append(question)
        if self.error is not None:
            raise self.error
        return self.passages


@dataclass
class FakeChatModel:
    """Streams `deltas`, then waits forever if `hold_open`. `rewrite` is what `complete` returns
    or raises; None waits forever."""

    deltas: Sequence[str] = ()
    hold_open: bool = False
    rewrite: str | Exception | None = ""
    streamed: list[list[Message]] = field(default_factory=list[list[Message]])
    completed: list[list[Message]] = field(default_factory=list[list[Message]])
    cancelled: bool = False
    closed: bool = False

    def stream(self, messages: Sequence[Message]) -> AsyncIterator[str]:
        self.streamed.append(list(messages))
        return self._stream()

    async def _stream(self) -> AsyncIterator[str]:
        try:
            for delta in self.deltas:
                yield delta
            if self.hold_open:
                await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        finally:
            self.closed = True

    async def complete(self, messages: Sequence[Message]) -> str:
        self.completed.append(list(messages))
        try:
            if self.rewrite is None:
                await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        if isinstance(self.rewrite, Exception):
            raise self.rewrite
        return self.rewrite or ""


def settings(**overrides: Any) -> Settings:
    return Settings.model_construct(llm_provider="ollama", retrieval_min_score=0.5, **overrides)


def service(retriever: FakeRetriever, model: FakeChatModel, **overrides: Any) -> ChatService:
    return ChatService(retriever=retriever, chat_model=model, settings=settings(**overrides))


async def run_turn(answering: ChatService, request: ChatRequest) -> list[TurnEvent]:
    return [event async for event in await answering.start_turn(request)]


async def test_a_first_question_streams_passages_then_tokens_then_the_answer() -> None:
    retriever = FakeRetriever()
    model = FakeChatModel(deltas=["Renew the IdP ", "certificate [2]."])

    events = await run_turn(service(retriever, model), ChatRequest(question="What is AUTH-403?"))

    assert events == [
        PassagesEvent(passages=WIRE),
        TokenEvent(text="Renew the IdP "),
        TokenEvent(text="certificate [2]."),
        DoneEvent(
            result=Answer(
                text="Renew the IdP certificate [1].",
                citations=[Citation(n=1, passage=WIRE[1])],
                retrieved_passages=WIRE,
                standalone_question=None,
            )
        ),
    ]
    # A first question is searched and answered as asked, with no rewrite call.
    assert retriever.questions == ["What is AUTH-403?"]
    assert model.completed == []
    assert model.streamed == [generation_messages("What is AUTH-403?", RETRIEVED)]


async def test_a_follow_up_is_rewritten_then_searched_and_answered_as_the_standalone_question() -> (
    None
):
    retriever = FakeRetriever()
    model = FakeChatModel(deltas=["On v2 it differs [1]."], rewrite="What is AUTH-403 on v2?")
    history = [HistoryTurn(question="What is AUTH-403?", answer="An expired certificate [1].")]

    events = await run_turn(
        service(retriever, model), ChatRequest(question="and on v2?", history=history)
    )

    assert events[0] == RewrittenEvent(standalone_question="What is AUTH-403 on v2?")
    assert events[1] == PassagesEvent(passages=WIRE)
    assert model.completed == [rewrite_messages(history, "and on v2?")]
    assert retriever.questions == ["What is AUTH-403 on v2?"]
    assert model.streamed == [generation_messages("What is AUTH-403 on v2?", RETRIEVED)]
    done = events[-1]
    assert isinstance(done, DoneEvent)
    assert done.result.standalone_question == "What is AUTH-403 on v2?"


FOLLOW_UP = ChatRequest(
    question="and on v2?",
    history=[HistoryTurn(question="What is AUTH-403?", answer="An expired certificate [1].")],
)


@pytest.mark.parametrize(
    "reply",
    [
        pytest.param("", id="empty"),
        pytest.param("  \n ", id="blank"),
        pytest.param("x" * 2_001, id="longer-than-a-question"),
    ],
)
async def test_an_unusable_rewrite_fails_the_turn_without_searching(reply: str) -> None:
    retriever = FakeRetriever()
    model = FakeChatModel(rewrite=reply)

    with pytest.raises(AppError) as failure:
        await run_turn(service(retriever, model), FOLLOW_UP)

    # No fallback to the raw question (ADR-0002).
    assert failure.value.code == "rewrite_failed"
    assert retriever.questions == []
    assert model.streamed == []


async def test_a_failed_rewrite_call_fails_the_turn_with_the_providers_error() -> None:
    retriever = FakeRetriever()
    model = FakeChatModel(rewrite=AppError("llm_unavailable", "Down."))

    with pytest.raises(AppError) as failure:
        await run_turn(service(retriever, model), FOLLOW_UP)

    assert failure.value.code == "llm_unavailable"
    assert retriever.questions == []


FIRST = ChatRequest(question="What is AUTH-403?")


async def test_no_passage_above_the_threshold_refuses_without_calling_the_model() -> None:
    weak = (passage(1, score=0.49), passage(2, score=0.2))
    model = FakeChatModel(deltas=["Should never be asked."])

    events = await run_turn(service(FakeRetriever(passages=weak), model), FIRST)

    wire = [wire_passage(p) for p in weak]
    assert events == [
        PassagesEvent(passages=wire),
        DoneEvent(
            result=Refusal(
                message=REFUSAL_MESSAGE,
                reason="no_relevant_passages",
                retrieved_passages=wire,
                standalone_question=None,
            )
        ),
    ]
    assert model.streamed == []


@pytest.mark.parametrize(
    "deltas",
    [
        pytest.param(["NOT_IN_KNOWLEDGE_BASE"], id="in-one-delta"),
        pytest.param(["NOT", "_IN_KNOW", "LEDGE_", "BASE"], id="split-across-deltas"),
        pytest.param(["\n  NOT_IN_", "KNOWLEDGE_BASE. Sorry."], id="after-whitespace"),
    ],
)
async def test_a_sentinel_reply_streams_no_tokens_and_ends_in_a_refusal(
    deltas: list[str],
) -> None:
    # Held open: the Turn must stop reading once the opening is the sentinel.
    model = FakeChatModel(deltas=deltas, hold_open=True)

    events = await run_turn(service(FakeRetriever(), model), FIRST)

    assert events == [
        PassagesEvent(passages=WIRE),
        DoneEvent(
            result=Refusal(
                message=REFUSAL_MESSAGE,
                reason="not_in_context",
                retrieved_passages=WIRE,
                standalone_question=None,
            )
        ),
    ]
    assert model.closed  # generation was stopped, not left running


async def test_a_reply_that_only_starts_like_the_sentinel_streams_once_it_differs() -> None:
    model = FakeChatModel(deltas=["NOT", "E: renew ", "the certificate [1]."])

    events = await run_turn(service(FakeRetriever(), model), FIRST)

    assert events[1:-1] == [
        TokenEvent(text="NOTE: renew "),
        TokenEvent(text="the certificate [1]."),
    ]
    done = events[-1]
    assert isinstance(done, DoneEvent)
    assert isinstance(done.result, Answer)
    assert done.result.text == "NOTE: renew the certificate [1]."


async def test_the_sentinel_later_in_the_reply_is_an_ordinary_answer() -> None:
    model = FakeChatModel(deltas=["Renew the certificate [1]. ", "NOT_IN_KNOWLEDGE_BASE"])

    events = await run_turn(service(FakeRetriever(), model), FIRST)

    assert events[1:-1] == [
        TokenEvent(text="Renew the certificate [1]. "),
        TokenEvent(text="NOT_IN_KNOWLEDGE_BASE"),
    ]
    done = events[-1]
    assert isinstance(done, DoneEvent)
    assert isinstance(done.result, Answer)
    assert done.result.text == "Renew the certificate [1]."


@pytest.mark.parametrize(
    "deltas",
    [
        pytest.param([], id="nothing"),
        pytest.param([" \n", "  "], id="whitespace"),
        pytest.param(["[7]"], id="only-markers-to-no-passage"),
    ],
)
async def test_an_empty_reply_fails_the_turn(deltas: list[str]) -> None:
    model = FakeChatModel(deltas=deltas)

    with pytest.raises(AppError) as failure:
        await run_turn(service(FakeRetriever(), model), FIRST)

    assert failure.value.code == "llm_unavailable"


async def test_a_retrieval_failure_fails_the_turn_before_the_model_is_asked() -> None:
    retriever = FakeRetriever(error=AppError("retrieval_unavailable", "No database."))
    model = FakeChatModel(deltas=["Never asked."])

    with pytest.raises(AppError) as failure:
        await run_turn(service(retriever, model), FIRST)

    assert failure.value.code == "retrieval_unavailable"
    assert model.streamed == []


async def test_a_turn_past_its_deadline_is_llm_timeout_and_stops_generating() -> None:
    model = FakeChatModel(deltas=["Renew the "], hold_open=True)
    answering = service(FakeRetriever(), model, turn_deadline_s=0.05)

    with pytest.raises(AppError) as failure:
        await run_turn(answering, FIRST)

    assert failure.value.code == "llm_timeout"
    assert model.cancelled


async def test_a_rewrite_past_its_deadline_is_llm_timeout() -> None:
    retriever = FakeRetriever()
    model = FakeChatModel(rewrite=None)
    answering = service(retriever, model, rewrite_deadline_s=0.05)

    with pytest.raises(AppError) as failure:
        await run_turn(answering, FOLLOW_UP)

    assert failure.value.code == "llm_timeout"
    assert model.cancelled
    assert retriever.questions == []


async def test_the_deadline_opens_with_the_stream_not_with_start_turn() -> None:
    # The route awaits `start_turn` in one task and reads the stream in another (#23).
    model = FakeChatModel(deltas=["Renew it [1]."])
    stream = await service(FakeRetriever(), model, turn_deadline_s=0.05).start_turn(FIRST)
    await asyncio.sleep(0.1)

    events = [event async for event in stream]

    assert isinstance(events[-1], DoneEvent)


async def test_stopping_the_turn_cancels_the_model_call() -> None:
    model = FakeChatModel(deltas=["Renew the "], hold_open=True)
    stream = await service(FakeRetriever(), model).start_turn(FIRST)
    first_token = asyncio.Event()

    async def consume() -> None:
        async for event in stream:
            if isinstance(event, TokenEvent):
                first_token.set()

    turn = asyncio.create_task(consume())
    await asyncio.wait_for(first_token.wait(), timeout=5)
    turn.cancel()  # what Stop (a client disconnect) and shutdown do

    with pytest.raises(asyncio.CancelledError):
        await turn
    assert model.cancelled
    assert model.closed


def turn_lines(logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [line for line in logs if line["event"] in ("turn_completed", "turn_stopped")]


async def test_an_answered_follow_up_logs_one_turn_completed_line(
    captured_logs: Callable[[], list[dict[str, Any]]],
) -> None:
    model = FakeChatModel(deltas=["Renew it [2]."], rewrite="What is AUTH-403 on v2?")

    await run_turn(service(FakeRetriever(), model, llm_model="qwen3.5:2b"), FOLLOW_UP)

    [line] = turn_lines(captured_logs())
    expected = {
        "event": "turn_completed",
        "outcome": "answer",
        "citation_count": 1,
        "provider": "ollama",
        "model": "qwen3.5:2b",
        "prompt_version": PROMPT_VERSION,
        "passages": [{"id": "sso-setup#1", "score": 0.8}, {"id": "sso-setup#2", "score": 0.8}],
    }
    assert {key: line[key] for key in expected} == expected
    for timing in ("rewrite_ms", "retrieval_ms", "ttft_ms", "total_ms"):
        assert line[timing] >= 0
    # No question or Answer text at INFO.
    assert "AUTH-403" not in json.dumps(line)


async def test_a_first_question_refused_by_the_gate_logs_no_rewrite_or_first_token(
    captured_logs: Callable[[], list[dict[str, Any]]],
) -> None:
    weak = (passage(1, score=0.1),)

    await run_turn(service(FakeRetriever(passages=weak), FakeChatModel()), FIRST)

    [line] = turn_lines(captured_logs())
    assert line["outcome"] == "refusal"
    assert line["refusal_reason"] == "no_relevant_passages"
    assert (line["rewrite_ms"], line["ttft_ms"]) == (None, None)


async def test_a_failed_turn_logs_its_error_code_and_what_was_retrieved(
    captured_logs: Callable[[], list[dict[str, Any]]],
) -> None:
    with pytest.raises(AppError):
        await run_turn(service(FakeRetriever(), FakeChatModel(deltas=[" "])), FIRST)

    [line] = turn_lines(captured_logs())
    assert (line["outcome"], line["error_code"]) == ("error", "llm_unavailable")
    assert [p["id"] for p in line["passages"]] == ["sso-setup#1", "sso-setup#2"]


async def test_an_unexpected_failure_logs_internal_error(
    captured_logs: Callable[[], list[dict[str, Any]]],
) -> None:
    retriever = FakeRetriever(error=RuntimeError("a bug"))

    with pytest.raises(RuntimeError):
        await run_turn(service(retriever, FakeChatModel()), FIRST)

    [line] = turn_lines(captured_logs())
    assert (line["outcome"], line["error_code"], line["retrieval_ms"]) == (
        "error",
        "internal_error",
        None,
    )


async def test_a_stopped_turn_logs_turn_stopped(
    captured_logs: Callable[[], list[dict[str, Any]]],
) -> None:
    model = FakeChatModel(hold_open=True)
    turn = asyncio.create_task(run_turn(service(FakeRetriever(), model), FIRST))
    while not model.streamed:
        await asyncio.sleep(0)

    turn.cancel()
    with pytest.raises(asyncio.CancelledError):
        await turn

    [line] = turn_lines(captured_logs())
    assert line["event"] == "turn_stopped"
