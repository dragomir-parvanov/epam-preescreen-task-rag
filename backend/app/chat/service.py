"""`ChatService`: runs one Turn, and is what fills the answering seam (ADR-0003).

Follow-up rewrite (Follow-ups only) → retrieval → threshold gate → `passages` → streamed
generation → answer assembly → `done`. Plain async Python over the `PassageRetriever` and
`ChatModel` ports: no Haystack here.
"""

import asyncio
import time
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Sequence
from dataclasses import dataclass, field
from typing import Final

import structlog

from app.answer_assembly import (
    NOT_IN_KNOWLEDGE_BASE,
    Refusal,
    Reply,
    assemble_reply,
    gate_retrieval,
)
from app.chat.answering import TurnEvent
from app.chat.schemas import (
    QUESTION_MAX_CHARS,
    ChatRequest,
    ChatResult,
    DoneEvent,
    Passage,
    PassagesEvent,
    RewrittenEvent,
    TokenEvent,
    chat_result,
    wire_passage,
)
from app.chat_model import ChatModel
from app.config import Settings
from app.errors import AppError, ErrorCode
from app.logs import TurnTimings, log_turn_completed
from app.passages import PassageRetriever
from app.prompts import (
    PROMPT_VERSION,
    UnusableRewrite,
    generation_messages,
    parse_rewrite,
    rewrite_messages,
)

logger = structlog.stdlib.get_logger(__name__)

REWRITE_FAILED: Final = (
    "The follow-up question couldn't be turned into a standalone question. "
    "Please ask it again in full."
)
EMPTY_REPLY: Final = "The language model returned an empty reply. Please try again."
TURN_TIMEOUT: Final = "The language model took too long to respond. Please try again."


class ChatService:
    """Answers Turns with `retriever` and `chat_model`; `settings` gives the retrieval threshold,
    the deadlines, and the provider and model to log."""

    def __init__(
        self, *, retriever: PassageRetriever, chat_model: ChatModel, settings: Settings
    ) -> None:
        self._retriever = retriever
        self._chat_model = chat_model
        self._settings = settings

    async def start_turn(self, request: ChatRequest) -> AsyncIterator[TurnEvent]:
        """Nothing is checked before the stream: `RequireIndex` gates on the index."""
        return self._turn(request)

    async def _turn(self, request: ChatRequest) -> AsyncIterator[TurnEvent]:
        # Everything, the deadline included, starts on the first read of the stream: that runs
        # in the task that consumes it, not the one that awaited `start_turn`.
        turn = _Progress(
            deadline=asyncio.get_running_loop().time() + self._settings.turn_deadline_s
        )
        outcome: ChatResult | ErrorCode | None = None
        try:
            standalone_question = None
            if request.history:
                standalone_question = await self._rewrite(request, turn)
                yield RewrittenEvent(standalone_question=standalone_question)
            question = standalone_question or request.question

            started = time.perf_counter()
            retrieved = await turn.by_deadline(self._retriever.retrieve(question))
            turn.retrieval_ms = _ms_since(started)
            turn.retrieved = [wire_passage(p) for p in retrieved]
            yield PassagesEvent(passages=turn.retrieved)

            reply = gate_retrieval(retrieved, self._settings.retrieval_min_score)
            if reply is None:
                hold_back = _SentinelHoldBack()
                stream = self._chat_model.stream(generation_messages(question, retrieved))
                try:
                    while (delta := await turn.by_deadline(anext(stream, None))) is not None:
                        if visible := hold_back.feed(delta):
                            turn.first_token()
                            yield TokenEvent(text=visible)
                        if hold_back.refused:
                            break  # a Refusal whatever follows, so stop generating
                finally:
                    await _close(stream)
                reply = _usable(assemble_reply(hold_back.text, retrieved))

            outcome = chat_result(reply, standalone_question)
            yield DoneEvent(result=outcome)
        except AppError as error:
            outcome = error.code
            raise
        except Exception:
            outcome = "internal_error"
            raise
        finally:
            self._log(request.question, outcome, turn)

    async def _rewrite(self, request: ChatRequest, turn: "_Progress") -> str:
        """The Follow-up's Standalone Question. No fallback to the raw question (ADR-0002)."""
        started = time.perf_counter()
        deadline = asyncio.get_running_loop().time() + self._settings.rewrite_deadline_s
        messages = rewrite_messages(request.history, request.question)
        reply = await turn.by_deadline(self._chat_model.complete(messages), deadline)
        turn.rewrite_ms = _ms_since(started)
        try:
            return parse_rewrite(reply, max_len=QUESTION_MAX_CHARS)
        except UnusableRewrite as error:
            raise AppError("rewrite_failed", REWRITE_FAILED) from error

    def _log(
        self, question: str, outcome: ChatResult | ErrorCode | None, turn: "_Progress"
    ) -> None:
        if outcome is None:
            # Stopped: the client hung up, or the server is shutting down.
            logger.info("turn_stopped", total_ms=_ms_since(turn.started))
            return
        log_turn_completed(
            question=question,
            outcome=outcome,
            retrieved=turn.retrieved,
            provider=self._settings.llm_provider,
            model=self._settings.llm_model,
            prompt_version=PROMPT_VERSION,
            timings=TurnTimings(
                rewrite_ms=turn.rewrite_ms,
                retrieval_ms=turn.retrieval_ms,
                ttft_ms=turn.ttft_ms,
                total_ms=_ms_since(turn.started),
            ),
        )


@dataclass(kw_only=True)
class _Progress:
    """One Turn's deadline, and what it has done so far, for its log line."""

    deadline: float
    """In event-loop time."""
    started: float = field(default_factory=time.perf_counter)
    rewrite_ms: float | None = None
    retrieval_ms: float | None = None
    ttft_ms: float | None = None
    retrieved: Sequence[Passage] = ()

    async def by_deadline[T](self, step: Awaitable[T], deadline: float | None = None) -> T:
        """Await `step`, failing the Turn with `llm_timeout` at the Turn's deadline, or at
        `deadline` if that comes first.

        Each step gets a timeout of its own rather than one around the whole Turn, so none is
        open across a `yield`, while the consumer is off doing something else.
        """
        timeout = asyncio.timeout_at(
            self.deadline if deadline is None else min(self.deadline, deadline)
        )
        try:
            async with timeout:
                return await step
        except TimeoutError:
            if timeout.expired():
                raise AppError("llm_timeout", TURN_TIMEOUT) from None
            raise

    def first_token(self) -> None:
        if self.ttft_ms is None:
            self.ttft_ms = _ms_since(self.started)


class _SentinelHoldBack:
    """Withholds the reply's opening while it could still be the Refusal sentinel (#19), so the
    CSM never sees `NOT_IN_KNOW…` before the Refusal arrives."""

    def __init__(self) -> None:
        self.text = ""
        self._holding = True

    @property
    def refused(self) -> bool:
        """The reply opens with the sentinel: answer assembly makes it a Refusal."""
        return self.text.lstrip().startswith(NOT_IN_KNOWLEDGE_BASE)

    def feed(self, delta: str) -> str:
        """Take the next delta; return the text that can be streamed now, if any."""
        self.text += delta
        if not self._holding:
            return delta
        if NOT_IN_KNOWLEDGE_BASE.startswith(self.text.lstrip()) or self.refused:
            return ""
        self._holding = False
        return self.text


def _usable(reply: Reply) -> Reply:
    """An Answer with no text left is a model failure, not something to show the CSM."""
    if not isinstance(reply, Refusal) and not reply.text.strip():
        raise AppError("llm_unavailable", EMPTY_REPLY)
    return reply


async def _close(stream: AsyncIterator[str]) -> None:
    """Hang up on the model if the stream is still open (`ChatModel.stream` is a generator)."""
    if isinstance(stream, AsyncGenerator):
        await stream.aclose()


def _ms_since(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 1)
