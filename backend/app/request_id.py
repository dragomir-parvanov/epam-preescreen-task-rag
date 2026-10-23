"""Request ids and the access log.

nginx generates `$request_id` and forwards it as `X-Request-ID`; called directly, the backend
makes its own. The id is bound in a structlog contextvar, so every log line of the request
carries it, is echoed in the `X-Request-ID` response header and fills the error envelope's
`request_id`. The CSM can quote it from the error card, and one grep finds the whole request.
"""

import re
import time
import uuid

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"

# nginx's $request_id is 32 hex characters. Anything else that a client could send is kept only
# when it is short and plain, so a forged header can't smuggle odd text into the logs.
_PLAUSIBLE_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")

# Polled by the Compose healthcheck; a successful probe would drown out the real traffic.
_PROBE_PATHS = frozenset({"/health", "/ready"})

logger = structlog.stdlib.get_logger(__name__)


def current_request_id() -> str | None:
    """The id of the request being handled, or None outside one."""
    request_id = structlog.contextvars.get_contextvars().get("request_id")
    return request_id if isinstance(request_id, str) else None


class RequestIdMiddleware:
    """Binds the request id, echoes it, and logs one `request_completed` line per request.

    A plain ASGI middleware rather than Starlette's `BaseHTTPMiddleware`, which pipes every
    response body through a memory stream in a task of its own: a detour the SSE stream and its
    cancellation on Stop don't need.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get(REQUEST_ID_HEADER)
        request_id = (
            incoming
            if incoming is not None and _PLAUSIBLE_ID.fullmatch(incoming)
            else uuid.uuid4().hex
        )
        # Cleared first, not after: the exception handler for an unexpected 500 runs outside
        # this middleware and still needs the id.
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        status: int | None = None

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = MutableHeaders(scope=message)
                if REQUEST_ID_HEADER not in headers:
                    headers[REQUEST_ID_HEADER] = request_id
            await send(message)

        started = time.perf_counter()
        try:
            await self.app(scope, receive, send_with_id)
        except Exception:
            # Starlette's outermost handler turns it into the 500 envelope after this.
            status = status or 500
            raise
        finally:
            path: str = scope["path"]
            quiet = path in _PROBE_PATHS and status is not None and status < 400
            (logger.debug if quiet else logger.info)(
                "request_completed",
                method=scope["method"],
                path=path,
                status=status,
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
            )
