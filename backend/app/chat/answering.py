"""The answering seam: what `POST /chat` runs a Turn through.

`ChatService` (`app.chat.service`) fills this seam in the running app. `StubAnsweringService`
lets the route tests drive every path, and answers when no service is passed in.
"""

import asyncio
from collections.abc import AsyncIterator, Callable, Sequence
from dataclasses import dataclass
from typing import Final, Protocol

from app.chat.schemas import (
    Answer,
    ArticleRef,
    ChatRequest,
    Citation,
    DoneEvent,
    Passage,
    PassagesEvent,
    RewrittenEvent,
    SectionRef,
    TokenEvent,
)
from app.errors import AppError

INDEX_NOT_READY: Final = "The Knowledge Base is still being indexed. Please try again in a minute."

type TurnEvent = RewrittenEvent | PassagesEvent | TokenEvent | DoneEvent
"""What a Turn yields. Failures are raised, never yielded: the HTTP layer owns `error` events."""


class AnsweringService(Protocol):
    async def start_turn(self, request: ChatRequest) -> AsyncIterator[TurnEvent]:
        """Start answering one Turn and return its event stream.

        Two failure phases, which the caller maps differently:

        - Awaiting `start_turn` runs the checks that can fail before any byte is sent (LLM not
          configured, index not ready). An `AppError` raised here becomes a real HTTP status.
        - Iterating the returned stream does the work. It yields `rewritten` (Follow-ups only),
          then `passages`, then any `token`s, and ends with exactly one `done`. An exception
          raised mid-stream becomes an SSE `error` event, since a 200 has already gone out.

        The stream is consumed in a different task from the one that awaited `start_turn`, so
        it must not hold a context (a timeout, a cancel scope) open across the two phases.
        Cancelling the consuming task, as a client disconnect does, must stop the work.
        """
        ...


@dataclass(frozen=True)
class RequireIndex:
    """Refuses every Turn with `index_not_ready` until `index_ready()`, then answers through
    `answering`: retrieval before the first sync would search a missing or stale index."""

    answering: AnsweringService
    index_ready: Callable[[], bool]

    async def start_turn(self, request: ChatRequest) -> AsyncIterator[TurnEvent]:
        if not self.index_ready():
            raise AppError("index_not_ready", INDEX_NOT_READY)
        return await self.answering.start_turn(request)


@dataclass(frozen=True)
class StubAnsweringService:
    """Plays back a fixed script instead of answering.

    `script` holds events to yield and exceptions to raise mid-stream, in order. `start_error`,
    if set, is raised before the stream starts. `delay` spaces the events out, so a curl through
    the proxy can show them arriving one by one.
    """

    script: Sequence[TurnEvent | Exception]
    start_error: Exception | None = None
    delay: float = 0.0

    async def start_turn(self, request: ChatRequest) -> AsyncIterator[TurnEvent]:
        if self.start_error is not None:
            raise self.start_error
        return self._play()

    async def _play(self) -> AsyncIterator[TurnEvent]:
        for step in self.script:
            if self.delay:
                await asyncio.sleep(self.delay)
            if isinstance(step, Exception):
                raise step
            yield step


_DEMO_PASSAGE = Passage(
    id="stub-article#0",
    article=ArticleRef(id="stub-article", title="Stub Article"),
    section=SectionRef(id="stub-section", path=["Stub Section"]),
    text="The answering pipeline is not built yet; this Passage is a placeholder.",
    applies_to=["v3"],
    status="current",
    score=1.0,
)

_DEMO_TOKENS = ["This is ", "a stub ", "answer: ", "the pipeline ", "is not built yet [1]."]

DEMO_SCRIPT: Sequence[TurnEvent] = [
    PassagesEvent(passages=[_DEMO_PASSAGE]),
    *(TokenEvent(text=token) for token in _DEMO_TOKENS),
    DoneEvent(
        result=Answer(
            text="".join(_DEMO_TOKENS),
            citations=[Citation(n=1, passage=_DEMO_PASSAGE)],
            retrieved_passages=[_DEMO_PASSAGE],
            standalone_question=None,
        )
    ),
]
"""What `create_app` answers every Turn with when it isn't given an answering service."""
