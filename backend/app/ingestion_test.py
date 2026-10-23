import asyncio
import itertools
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from app.ingestion import (
    IndexStatus,
    Ingestion,
    UnrecoverableIndexError,
    backoff_delays,
    validate_knowledge_base,
)

pytestmark = pytest.mark.anyio

KNOWLEDGE_BASE = Path("/knowledge-base")


@dataclass
class FakeIndex:
    """Fails its first syncs with the scripted errors, then succeeds; `release` gates each sync."""

    failures: list[Exception] = field(default_factory=list[Exception])
    synced: list[Path] = field(default_factory=list[Path])
    closed: bool = False
    release: asyncio.Event | None = None

    async def sync(self, knowledge_base: Path) -> None:
        if self.release is not None:
            await self.release.wait()
        if self.failures:
            raise self.failures.pop(0)
        self.synced.append(knowledge_base)

    async def close(self) -> None:
        self.closed = True


def no_wait() -> Iterator[float]:
    return itertools.repeat(0.0)


async def settled(ingestion: Ingestion[FakeIndex]) -> None:
    """Wait until the background sync has finished, one way or another."""
    while ingestion.running:
        await asyncio.sleep(0)


def test_backoff_doubles_from_one_second_and_is_capped_at_30() -> None:
    assert list(itertools.islice(backoff_delays(), 8)) == [1, 2, 4, 8, 16, 30, 30, 30]


async def test_the_index_is_not_ready_until_the_first_sync_completes() -> None:
    index = FakeIndex(release=asyncio.Event())

    async def open_index() -> FakeIndex:
        return index

    ingestion = Ingestion(open_index, KNOWLEDGE_BASE, delays=no_wait)
    ingestion.start()
    await asyncio.sleep(0)
    before = ingestion.status

    assert index.release is not None
    index.release.set()
    await settled(ingestion)

    assert before == IndexStatus(ok=False, detail=None)
    assert ingestion.status == IndexStatus(ok=True, detail=None)
    assert ingestion.index is index
    assert index.synced == [KNOWLEDGE_BASE]
    await ingestion.stop()


async def test_a_failed_sync_is_reported_and_retried_after_the_backoff() -> None:
    index = FakeIndex(failures=[RuntimeError("connection refused")])
    waits: list[float] = []

    async def open_index() -> FakeIndex:
        return index

    async def sleep(seconds: float) -> None:
        waits.append(seconds)
        assert ingestion.status == IndexStatus(ok=False, detail="connection refused")

    ingestion = Ingestion(open_index, KNOWLEDGE_BASE, sleep=sleep)
    ingestion.start()
    await settled(ingestion)

    assert waits == [1]
    assert ingestion.status == IndexStatus(ok=True, detail=None)
    await ingestion.stop()


async def test_opening_the_index_is_retried_too_and_happens_once() -> None:
    index = FakeIndex()
    opens: list[str] = []

    async def open_index() -> FakeIndex:
        opens.append("open")
        if len(opens) == 1:
            raise OSError("database starting up")
        return index

    ingestion = Ingestion(open_index, KNOWLEDGE_BASE, delays=no_wait)
    ingestion.start()
    await settled(ingestion)

    assert opens == ["open", "open"]
    assert ingestion.status.ok
    await ingestion.stop()


async def test_an_unrecoverable_index_stops_the_retries_and_keeps_its_fix_as_the_detail() -> None:
    attempts = 0

    async def open_index() -> FakeIndex:
        nonlocal attempts
        attempts += 1
        raise UnrecoverableIndexError("drop the table and re-ingest")

    ingestion = Ingestion(open_index, KNOWLEDGE_BASE, delays=no_wait)
    ingestion.start()
    await settled(ingestion)

    assert attempts == 1
    assert ingestion.status == IndexStatus(ok=False, detail="drop the table and re-ingest")
    await ingestion.stop()


async def test_stopping_cancels_a_sync_in_flight_and_closes_the_index() -> None:
    index = FakeIndex(release=asyncio.Event())  # never released: the sync hangs

    async def open_index() -> FakeIndex:
        return index

    ingestion = Ingestion(open_index, KNOWLEDGE_BASE, delays=no_wait)
    ingestion.start()
    await asyncio.sleep(0)

    await asyncio.wait_for(ingestion.stop(), timeout=1)

    assert not ingestion.running
    assert index.closed
    assert not ingestion.status.ok


def test_a_malformed_article_exits_non_zero_with_a_log_line_naming_the_file(
    tmp_path: Path, captured_logs: Callable[[], list[dict[str, Any]]]
) -> None:
    (tmp_path / "sso.md").write_text("---\nid: sso\ntitle: SSO\napplies_to: [v3]\n---\nBody\n")

    with pytest.raises(SystemExit) as exit:
        validate_knowledge_base(tmp_path)

    assert exit.value.code != 0
    [line] = [line for line in captured_logs() if line["event"] == "knowledge_base_invalid"]
    assert line["level"] == "error"
    assert line["error"].startswith("sso.md: invalid front-matter: status: Field required")


def test_a_valid_knowledge_base_returns_its_articles(tmp_path: Path) -> None:
    (tmp_path / "sso.md").write_text(
        "---\nid: sso\ntitle: SSO\napplies_to: [v3]\nstatus: current\n---\nBody\n"
    )

    assert [article.id for article in validate_knowledge_base(tmp_path)] == ["sso"]
