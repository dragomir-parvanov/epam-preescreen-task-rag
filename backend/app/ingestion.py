"""Startup ingestion, phase 2: sync the Passage index with `knowledge-base/` in the background.

Phase 1, validating every Article before the app serves, is `validate_knowledge_base`.

The sync itself is idempotent and serialised across processes by the index (an advisory lock),
so this module only decides *when* it runs: once at startup, retried with exponential backoff
until it succeeds, without ever crashing the process. Until then the `index` readiness check
fails with the last error, and `POST /chat` answers `index_not_ready`.
"""

import asyncio
import sys
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import structlog

from app.knowledge_base import Article, InvalidArticleError, load_articles

logger = structlog.stdlib.get_logger(__name__)

BACKOFF_CAP_S = 30.0


class SyncableIndex(Protocol):
    async def sync(self, knowledge_base: Path) -> object:
        """Make the index match `knowledge_base`. Idempotent, so a retry after a failure is safe."""
        ...

    async def close(self) -> None: ...


class UnrecoverableIndexError(RuntimeError):
    """The index can't be used as it is, and retrying won't change that; the message says what
    to do. The sync stops retrying and the `index` check reports the message."""


@dataclass(frozen=True, slots=True)
class IndexStatus:
    ok: bool
    """The first sync since startup has completed."""
    detail: str | None
    """The last sync error while it isn't ok."""


def backoff_delays(initial_s: float = 1.0, cap_s: float = BACKOFF_CAP_S) -> Iterator[float]:
    """Seconds to wait before each retry: doubling from `initial_s`, capped at `cap_s`."""
    delay = initial_s
    while True:
        yield min(delay, cap_s)
        delay *= 2


class Ingestion[I: SyncableIndex]:
    """Opens the index and syncs it in a background task, retrying until the first success.

    `index` is the opened index once the first sync has completed (retrieval reads it then).
    """

    def __init__(
        self,
        open_index: Callable[[], Awaitable[I]],
        knowledge_base: Path,
        *,
        delays: Callable[[], Iterator[float]] = backoff_delays,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._open_index = open_index
        self._knowledge_base = knowledge_base
        self._delays = delays
        self._sleep = sleep
        self._opened: I | None = None
        self._status = IndexStatus(ok=False, detail=None)
        self._task: asyncio.Task[None] | None = None

    @property
    def status(self) -> IndexStatus:
        return self._status

    @property
    def index(self) -> I | None:
        return self._opened if self._status.ok else None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="ingestion")

    async def stop(self) -> None:
        """Cancel a sync in flight (the index's lock is released with its connection), then
        close the index."""
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        if self._opened is not None:
            await self._opened.close()

    async def _run(self) -> None:
        delays = self._delays()
        attempt = 0
        while True:
            attempt += 1
            try:
                if self._opened is None:
                    self._opened = await self._open_index()
                await self._opened.sync(self._knowledge_base)
            except UnrecoverableIndexError as error:
                self._status = IndexStatus(ok=False, detail=str(error))
                logger.error("index_unusable", error=str(error))
                return
            except Exception as error:
                detail = str(error) or type(error).__name__
                self._status = IndexStatus(ok=False, detail=detail)
                delay = next(delays)
                logger.warning("index_sync_failed", attempt=attempt, error=detail, retry_in_s=delay)
                await self._sleep(delay)
            else:
                self._status = IndexStatus(ok=True, detail=None)
                logger.info("index_ready", attempts=attempt)
                return


def validate_knowledge_base(directory: Path) -> list[Article]:
    """Startup phase 1: parse every Article, or exit non-zero with a log line naming the file.

    A malformed Article is a content bug, so the backend refuses to start rather than serve
    a partial Knowledge Base.
    """
    try:
        articles = load_articles(directory)
    except InvalidArticleError as error:
        logger.error("knowledge_base_invalid", error=str(error))
        sys.exit(1)
    logger.info("knowledge_base_loaded", articles=len(articles))
    return articles
