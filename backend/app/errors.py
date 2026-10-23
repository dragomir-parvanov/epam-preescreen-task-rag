"""The one error envelope, `{error: {code, message, details?, request_id?}}`, and its status table.

Code anywhere in the backend fails a request by raising `AppError` with a code. The HTTP layer
turns it into a real status plus the envelope, or into an SSE `error` event once a stream has
started. Any other exception becomes `internal_error`, with its details kept out of the response.
"""

from typing import Any, Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.request_id import REQUEST_ID_HEADER, current_request_id

type ErrorCode = Literal[
    "validation_error",
    "not_found",
    "llm_not_configured",
    "llm_auth_failed",
    "llm_unavailable",
    "llm_timeout",
    "index_not_ready",
    "retrieval_unavailable",
    "internal_error",
]

HTTP_STATUS: dict[ErrorCode, int] = {
    "validation_error": 422,
    "not_found": 404,
    "llm_not_configured": 503,
    "llm_auth_failed": 502,
    "llm_unavailable": 503,
    "llm_timeout": 504,
    "index_not_ready": 503,
    "retrieval_unavailable": 503,
    "internal_error": 500,
}


class FieldError(BaseModel):
    loc: list[str | int]
    """Where the bad value is, e.g. `["body", "history"]`."""
    msg: str
    type: str


class ErrorBody(BaseModel):
    code: ErrorCode
    message: str
    """Human-readable; safe to show the CSM."""
    details: list[FieldError] | None = None
    """Field errors, for `validation_error` only."""
    request_id: str | None = Field(default_factory=current_request_id)
    """The request's `X-Request-ID`, which finds its log lines; the error card shows it."""


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class AppError(Exception):
    """A failure with a code from the API contract."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code: ErrorCode = code
        self.message = message

    def body(self) -> ErrorBody:
        return ErrorBody(code=self.code, message=self.message)


def error_responses(*codes: ErrorCode) -> dict[int | str, dict[str, Any]]:
    """OpenAPI `responses` documenting the envelope for `codes`, grouped by status.

    The schema is spelled out under `application/json` rather than passed as `model`, because
    FastAPI files a `model` under the route's own media type, which for `POST /chat` is
    `text/event-stream`. Its `$ref`s point at components that the routes register.
    """
    envelope = ErrorEnvelope.model_json_schema(ref_template="#/components/schemas/{model}")
    envelope.pop("$defs", None)
    by_status: dict[int, list[ErrorCode]] = {}
    for code in codes:
        by_status.setdefault(HTTP_STATUS[code], []).append(code)
    return {
        status: {
            "description": "Error codes: " + ", ".join(grouped),
            "content": {"application/json": {"schema": envelope}},
        }
        for status, grouped in by_status.items()
    }


def _envelope(body: ErrorBody, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(
        ErrorEnvelope(error=body).model_dump(mode="json"),
        status_code=HTTP_STATUS[body.code],
        headers=headers,
    )


async def _on_validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Rebuilt field by field so the offending input is never echoed back.
    details = [
        FieldError(loc=list(error["loc"]), msg=error["msg"], type=error["type"])
        for error in exc.errors()
    ]
    return _envelope(
        ErrorBody(code="validation_error", message="The request is invalid.", details=details)
    )


def internal_error() -> ErrorBody:
    """What any unexpected exception becomes. Its details go to the logs, never to the client."""
    return ErrorBody(code="internal_error", message="Something went wrong. Please try again.")


async def _on_app_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return _envelope(exc.body())


async def _on_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    # Starlette re-raises the exception after this response is sent, so the server logs it.
    # This handler runs outside the request-id middleware, so it echoes the id itself.
    body = internal_error()
    return _envelope(
        body, headers={REQUEST_ID_HEADER: body.request_id} if body.request_id else None
    )


def install_error_handlers(app: FastAPI) -> None:
    """Make every error response the envelope, FastAPI's own 422 included."""
    app.add_exception_handler(RequestValidationError, _on_validation_error)
    app.add_exception_handler(AppError, _on_app_error)
    app.add_exception_handler(Exception, _on_unexpected_error)
