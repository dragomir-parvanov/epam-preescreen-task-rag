"""`GET /ready`: can the stack answer? The Compose healthcheck probes it, so `up --wait` means yes.

| check      | gates `status`? | ok when                                         |
|------------|-----------------|-------------------------------------------------|
| `database` | yes             | Postgres answers `SELECT 1`                     |
| `index`    | yes             | the first sync since startup has completed      |
| `llm`      | no, reported    | the provider knows the model (no tokens spent)  |

`llm` doesn't gate: an outage at a shared provider would mark every instance unready, though no
instance can do anything about it. The UI shows it instead.
"""

import asyncio
import time
from collections.abc import Callable
from typing import Literal, Protocol

import structlog
from fastapi import APIRouter, Response
from pydantic import BaseModel

from app.chat_model import LlmHealth, LlmProbe, LlmProblem
from app.ingestion import IndexStatus

logger = structlog.stdlib.get_logger(__name__)

LLM_CACHE_TTL_S = 60.0


class DatabaseProbe(Protocol):
    async def ping(self) -> None:
        """Returns once the database answers; raises when it doesn't."""
        ...


class CachedLlmCheck:
    """The `llm` check: the probe runs at startup, then at most once a minute.

    `/ready` never waits for a slow probe longer than `wait_s`; it reports the last result
    meanwhile, or `unavailable` before the first.
    """

    def __init__(
        self,
        probe: LlmProbe,
        *,
        ttl_s: float = LLM_CACHE_TTL_S,
        wait_s: float = 1.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._probe = probe
        self._ttl_s = ttl_s
        self._wait_s = wait_s
        self._clock = clock
        self._health: LlmHealth | None = None
        self._probed_at = 0.0
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self._refresh()

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)

    async def current(self) -> LlmHealth:
        if self._health is None or self._clock() - self._probed_at >= self._ttl_s:
            self._refresh()
        if self._task is not None:
            # A probe that outlasts the wait keeps running, and its result lands in the cache.
            await asyncio.wait([self._task], timeout=self._wait_s)
        return self._health or LlmHealth(problem="unavailable")

    def _refresh(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name="llm-probe")

    async def _run(self) -> None:
        started = self._clock()
        try:
            health = await self._probe.probe()
        except Exception:
            logger.exception("llm_probe_failed")
            health = LlmHealth(problem="unavailable")
        if health != self._health:
            (logger.info if health.problem is None else logger.warning)(
                "llm_checked", problem=health.problem, command=health.command
            )
        self._health, self._probed_at = health, started


# --- The response ---------------------------------------------------------------------------


class Check(BaseModel):
    ok: bool
    detail: str | None = None
    """Why it isn't ok: the last error."""


class LlmCheck(BaseModel):
    ok: bool
    detail: LlmProblem | None = None
    command: str | None = None
    """For `model_missing` on Ollama, the command that pulls the model, to show and copy."""


class ReadinessChecks(BaseModel):
    database: Check
    """Gating: Postgres answers."""
    index: Check
    """Gating: the Knowledge Base has been synced into the index since startup."""
    llm: LlmCheck
    """Reported only: an LLM outage leaves `status` at `ready`."""


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: ReadinessChecks


def readiness_router(
    database: DatabaseProbe | None,
    index_status: Callable[[], IndexStatus],
    llm: CachedLlmCheck | None,
) -> APIRouter:
    """With no `database` or `llm` (an app built without its runtime), those checks fail."""
    router = APIRouter()

    @router.get(
        "/ready",
        operation_id="getReady",
        responses={503: {"model": ReadinessResponse, "description": "Not ready: see `checks`."}},
    )
    async def ready(response: Response) -> ReadinessResponse:
        """Readiness: 200 once the stack can answer, else 503. Both carry every check."""
        index = index_status()
        health = await llm.current() if llm else LlmHealth(problem="unavailable")
        checks = ReadinessChecks(
            database=await _database_check(database),
            index=Check(ok=index.ok, detail=index.detail),
            llm=LlmCheck(ok=health.problem is None, detail=health.problem, command=health.command),
        )
        ok = checks.database.ok and checks.index.ok
        response.status_code = 200 if ok else 503
        return ReadinessResponse(status="ready" if ok else "not_ready", checks=checks)

    return router


async def _database_check(database: DatabaseProbe | None) -> Check:
    if database is None:
        return Check(ok=False, detail="not configured")
    try:
        await database.ping()
    except Exception as error:
        return Check(ok=False, detail=str(error) or type(error).__name__)
    return Check(ok=True)
