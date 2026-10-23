import logging
from collections.abc import AsyncIterable, AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.chat.answering import AnsweringService, TurnEvent
from app.chat.schemas import ChatRequest, ChatStreamEvent, ErrorEvent
from app.errors import AppError, error_responses, internal_error

logger = logging.getLogger(__name__)


def _frame(event: TurnEvent | ErrorEvent) -> Any:
    """Frame `event` as `event: <type>` + `data: <json>`.

    Typed `Any` because FastAPI reads the endpoint's declared item type (`ChatStreamEvent`) to
    document `data` in OpenAPI, while the `event:` line needs a `ServerSentEvent` wrapper.
    """
    return ServerSentEvent(event=event.type, data=event)


def chat_router(answering: AnsweringService) -> APIRouter:
    router = APIRouter()

    async def start_turn(body: ChatRequest) -> AsyncIterator[TurnEvent]:
        # A dependency runs before the response starts, so what it raises gets a real status.
        return await answering.start_turn(body)

    @router.post(
        "/chat",
        operation_id="postChat",
        response_class=EventSourceResponse,
        # Only what can fail before the first byte gets a status; the rest are `error` events.
        responses=error_responses(
            "validation_error",
            "llm_not_configured",
            "index_not_ready",
            "retrieval_unavailable",
            "internal_error",
        ),
    )
    async def chat(
        turn: Annotated[AsyncIterator[TurnEvent], Depends(start_turn)],
    ) -> AsyncIterable[ChatStreamEvent]:
        """Answer one Turn, streamed as Server-Sent Events.

        `rewritten` (Follow-ups only) -> `passages` -> `token`s -> `done`, or `error` once the
        stream has started.
        """
        try:
            async for event in turn:
                yield _frame(event)
        except AppError as error:
            yield _frame(ErrorEvent(error=error.body()))
        except Exception:
            # Cancellation (a client disconnect) is a BaseException and passes through.
            logger.exception("chat stream failed")
            yield _frame(ErrorEvent(error=internal_error()))

    return router
