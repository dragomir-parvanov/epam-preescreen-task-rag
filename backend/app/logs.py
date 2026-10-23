"""Structured logging: one structlog setup for our loggers and every library's.

Every line is one JSON object on stdout (`BACKEND_LOG_FORMAT=json`, the image's default) or a
readable console line (`console`, what `pixi run dev-backend` uses). Context bound with
`structlog.contextvars`, such as the request id, lands on every line, whichever logger wrote it.

Question and Answer text may contain client data, so it is logged only at DEBUG, never at INFO.
"""

import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, TextIO, get_args
from urllib.parse import urlsplit

import structlog
from pydantic import SecretStr
from structlog.typing import Processor

from app.chat.schemas import Answer, ChatResult, Passage, Refusal, UncitedAnswer
from app.config import LogFormat, LogLevel, Settings
from app.errors import ErrorCode

logger = structlog.stdlib.get_logger(__name__)


_LIBRARY_LOGGERS = ("uvicorn", "uvicorn.error", "haystack")


class _AppHandler(logging.StreamHandler[TextIO]):
    """Our one root handler, told apart so reconfiguring replaces it and nothing else."""


def configure_logging(log_format: LogFormat, level: LogLevel, stream: TextIO | None = None) -> None:
    """Route every logger through structlog, rendering to `stream` (stdout by default).

    Called once at startup, after uvicorn has set up its loggers and Haystack has been imported,
    so it can take theirs over.
    """
    # Applied to stdlib records ("foreign") and to our own events alike.
    shared: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        # Off, so loggers created at import time pick up this configuration whenever it runs.
        cache_logger_on_first_use=False,
    )
    renderer: list[Processor] = (
        [structlog.processors.format_exc_info, structlog.processors.JSONRenderer()]
        if log_format == "json"
        else [structlog.dev.ConsoleRenderer()]
    )
    handler = _AppHandler(stream or sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            # ExtraAdder keeps the key-value data that Haystack's loggers pass as `extra`.
            foreign_pre_chain=[*shared, structlog.stdlib.ExtraAdder()],
            processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, *renderer],
        )
    )

    root = logging.getLogger()
    root.handlers = [h for h in root.handlers if not isinstance(h, _AppHandler)]
    root.addHandler(handler)
    root.setLevel(level)

    # uvicorn, and Haystack on import when structlog is installed, give their loggers handlers of
    # their own, which would print a second, differently formatted copy. Ours takes over.
    for name in _LIBRARY_LOGGERS:
        library_logger = logging.getLogger(name)
        library_logger.handlers.clear()
        library_logger.propagate = True
    # Replaced by the request-id middleware's own line per request, which carries the id.
    logging.getLogger("uvicorn.access").disabled = True


def log_config_loaded(settings: Settings) -> None:
    """One `config_loaded` line with every setting. Secrets print only as `set` or `unset`.

    The `fake` provider (smoke tests only) adds a warning line, so it never goes unnoticed.
    """
    fields: dict[str, Any] = {}
    for name, field in type(settings).model_fields.items():
        value = getattr(settings, name)
        # By declared type, so an optional secret that is unset still prints as such.
        if field.annotation is SecretStr or SecretStr in get_args(field.annotation):
            fields[name] = "unset" if value is None else "set"
        else:
            fields[name] = value
    database = urlsplit(settings.database_url.get_secret_value())
    fields["database_host"] = f"{database.hostname}:{database.port or 5432}"
    logger.info("config_loaded", **fields)
    if settings.llm_provider == "fake":
        logger.warning(
            "fake_llm_provider_active",
            detail="Every Answer is a canned reply, not a model's: for smoke tests only.",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class TurnTimings:
    """Where a Turn's time went, in milliseconds."""

    rewrite_ms: float | None
    """How long the Follow-up rewrite took; None for a first question, which isn't rewritten."""
    retrieval_ms: float | None
    """How long retrieval took; None when the Turn failed before retrieving."""
    ttft_ms: float | None
    """From the Turn's start to its first `token`; None if none was sent (a Refusal, a failure)."""
    total_ms: float
    """From the Turn's start to its `done` or `error`."""


def log_turn_completed(
    *,
    question: str,
    outcome: ChatResult | ErrorCode,
    retrieved: Sequence[Passage],
    provider: str,
    model: str,
    prompt_version: str,
    timings: TurnTimings,
) -> None:
    """Log one `turn_completed` line per Turn, however it ended, and its text at DEBUG only.

    `outcome` is the result `done` carried, or the code of the `error` that ended the Turn.
    `retrieved` is what retrieval returned, so a Turn that failed after it still shows it.
    """
    facts: dict[str, Any]
    if isinstance(outcome, str):
        facts = {"outcome": "error", "error_code": outcome, "citation_count": 0}
        standalone_question, text = None, None
    else:
        standalone_question = outcome.standalone_question
        match outcome:
            case Answer():
                facts = {"outcome": outcome.type, "citation_count": len(outcome.citations)}
                text = outcome.text
            case UncitedAnswer():
                facts = {"outcome": outcome.type, "citation_count": 0}
                text = outcome.text
            case Refusal():
                facts = {
                    "outcome": outcome.type,
                    "refusal_reason": outcome.reason,
                    "citation_count": 0,
                }
                text = outcome.message

    logger.debug(
        "turn_content", question=question, standalone_question=standalone_question, text=text
    )
    logger.info(
        "turn_completed",
        **facts,
        provider=provider,
        model=model,
        prompt_version=prompt_version,
        passages=[{"id": p.id, "score": p.score} for p in retrieved],
        rewrite_ms=timings.rewrite_ms,
        retrieval_ms=timings.retrieval_ms,
        ttft_ms=timings.ttft_ms,
        total_ms=timings.total_ms,
    )
