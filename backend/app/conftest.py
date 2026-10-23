import io
import json
from collections.abc import Callable, Iterator
from typing import Any

import pytest

from app.logs import configure_logging
from app.pgvector_testing import fresh_database, running_pgvector


@pytest.fixture(scope="session")
def pgvector_server_url() -> Iterator[str]:
    """Admin URL of the session's pgvector server. Tests want `pgvector_database_url` instead."""
    with running_pgvector() as url:
        yield url


@pytest.fixture
def pgvector_database_url(pgvector_server_url: str) -> Iterator[str]:
    """URL of an empty database of its own, so tests never share rows, tables or extensions.

    Tests using it are marked `@pytest.mark.pgvector`, so `-m 'not pgvector'` runs without Docker.
    """
    with fresh_database(pgvector_server_url) as url:
        yield url


@pytest.fixture
def captured_logs() -> Callable[[], list[dict[str, Any]]]:
    """Route all logging, at INFO, as JSON into a buffer; call the result to read the lines."""
    stream = io.StringIO()
    configure_logging("json", "INFO", stream=stream)
    return lambda: [json.loads(line) for line in stream.getvalue().splitlines()]
