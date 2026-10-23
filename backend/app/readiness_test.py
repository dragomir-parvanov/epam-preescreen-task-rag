import asyncio
import threading
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response

from app.chat_model import LlmHealth
from app.config import Settings
from app.ingestion import Ingestion
from app.main import Runtime, create_app
from app.readiness import CachedLlmCheck

# --- Fakes of the three things readiness looks at -------------------------------------------


@dataclass
class FakeIndex:
    """Its sync blocks until `synced` is set (from the test's thread)."""

    synced: threading.Event = field(default_factory=threading.Event)
    closed: bool = False

    async def sync(self, knowledge_base: Path) -> None:
        await asyncio.to_thread(self.synced.wait)

    async def close(self) -> None:
        self.closed = True


@dataclass
class FakeDatabase:
    error: Exception | None = None

    async def ping(self) -> None:
        if self.error is not None:
            raise self.error


@dataclass
class FakeLlm:
    health: LlmHealth = field(default_factory=LlmHealth)
    probes: int = 0

    async def probe(self) -> LlmHealth:
        self.probes += 1
        return self.health


@dataclass
class Stack:
    client: TestClient
    index: FakeIndex
    database: FakeDatabase
    llm: FakeLlm


@contextmanager
def running_stack(
    *, database: FakeDatabase | None = None, llm: FakeLlm | None = None
) -> Generator[Stack]:
    index, database, llm = FakeIndex(), database or FakeDatabase(), llm or FakeLlm()

    async def open_index() -> FakeIndex:
        return index

    runtime = Runtime(
        ingestion=Ingestion(open_index, Path("/knowledge-base")),
        database=database,
        llm=CachedLlmCheck(llm),
    )
    app = create_app(Settings.model_construct(), articles=[], runtime=runtime)
    try:
        with TestClient(app) as client:
            yield Stack(client, index, database, llm)
    finally:
        index.synced.set()  # never leave the sync's worker thread waiting


def poll_until(client: TestClient, ok: Callable[[Response], bool]) -> Response:
    deadline = time.monotonic() + 5
    while not ok(response := client.get("/ready")) and time.monotonic() < deadline:
        time.sleep(0.01)
    return response


# --- GET /ready -----------------------------------------------------------------------------


def test_ready_is_503_with_the_index_not_ok_until_the_first_sync_completes() -> None:
    with running_stack() as stack:
        before = stack.client.get("/ready")
        stack.index.synced.set()
        after = poll_until(stack.client, lambda r: r.status_code == 200)

    assert before.status_code == 503
    assert before.json() == {
        "status": "not_ready",
        "checks": {
            "database": {"ok": True, "detail": None},
            "index": {"ok": False, "detail": None},
            "llm": {"ok": True, "detail": None, "command": None},
        },
    }
    assert after.json()["status"] == "ready"
    assert after.json()["checks"]["index"] == {"ok": True, "detail": None}


def test_a_failing_llm_leaves_the_stack_ready_and_says_how_to_fix_it() -> None:
    missing = LlmHealth(problem="model_missing", command="ollama pull qwen3.5:2b")
    with running_stack(llm=FakeLlm(missing)) as stack:
        stack.index.synced.set()
        response = poll_until(stack.client, lambda r: r.status_code == 200)

    assert response.json() == {
        "status": "ready",
        "checks": {
            "database": {"ok": True, "detail": None},
            "index": {"ok": True, "detail": None},
            "llm": {"ok": False, "detail": "model_missing", "command": "ollama pull qwen3.5:2b"},
        },
    }


def test_an_unreachable_database_makes_the_stack_not_ready() -> None:
    database = FakeDatabase(OSError("connection refused"))
    with running_stack(database=database) as stack:
        stack.index.synced.set()
        poll_until(stack.client, lambda r: r.json()["checks"]["index"]["ok"])
        response = stack.client.get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"]["database"] == {"ok": False, "detail": "connection refused"}


def test_stopping_the_app_closes_the_index() -> None:
    with running_stack() as stack:
        stack.index.synced.set()
        poll_until(stack.client, lambda r: r.status_code == 200)

    assert stack.index.closed


# --- POST /chat waits for the index ---------------------------------------------------------


def test_chat_is_index_not_ready_until_the_first_sync_completes() -> None:
    body: dict[str, Any] = {"question": "What is AUTH-403?", "history": []}
    with running_stack() as stack:
        before = stack.client.post("/chat", json=body)
        stack.index.synced.set()
        poll_until(stack.client, lambda r: r.status_code == 200)
        after = stack.client.post("/chat", json=body)

    assert before.status_code == 503
    assert before.json()["error"]["code"] == "index_not_ready"
    assert after.status_code == 200


# --- The llm check's cache ------------------------------------------------------------------


@pytest.mark.anyio
async def test_the_llm_probe_runs_at_startup_and_is_cached_for_60_seconds() -> None:
    llm = FakeLlm()
    now = [0.0]
    check = CachedLlmCheck(llm, clock=lambda: now[0])

    check.start()
    first = await check.current()
    now[0] = 59
    await check.current()
    probes_within_a_minute = llm.probes
    now[0] = 61
    await check.current()

    assert first == LlmHealth()
    assert probes_within_a_minute == 1
    assert llm.probes == 2


@pytest.mark.anyio
async def test_a_hanging_llm_probe_does_not_hold_up_readiness() -> None:
    class HangingLlm:
        async def probe(self) -> LlmHealth:
            await asyncio.Event().wait()
            raise AssertionError("unreachable")

    check = CachedLlmCheck(HangingLlm(), wait_s=0.05)

    async with asyncio.timeout(1):
        health = await check.current()
    await check.stop()

    assert health == LlmHealth(problem="unavailable")


@pytest.mark.anyio
async def test_a_probe_that_crashes_reports_unavailable(
    captured_logs: Callable[[], list[dict[str, Any]]],
) -> None:
    class BrokenLlm:
        async def probe(self) -> LlmHealth:
            raise RuntimeError("bug")

    health = await CachedLlmCheck(BrokenLlm()).current()

    assert health == LlmHealth(problem="unavailable")
    assert "llm_probe_failed" in [line["event"] for line in captured_logs()]
