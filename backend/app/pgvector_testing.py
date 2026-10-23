"""A real pgvector for the adapter tests, from the same image Compose ships (ADR-0004).

The fixtures in conftest.py wrap these: one server per session, a fresh database per test.
"""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Final
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from testcontainers.community.postgres import PostgresContainer
from testcontainers.core.config import testcontainers_config
from testcontainers.core.docker_client import DockerClient

# Compose's default and .env.example name this same tag; pgvector_testing_test.py keeps them equal.
POSTGRES_IMAGE: Final = "pgvector/pgvector:0.8.6-pg18-trixie"

DOCKER_REQUIRED: Final = "adapter tests need Docker; start it or run `pytest -m 'not pgvector'`"


@contextmanager
def running_pgvector() -> Generator[str]:
    """Start a pgvector server and yield its admin URL. Without Docker, fail: never skip."""
    docker_error = _docker_error()
    if docker_error is not None:
        pytest.fail(f"{DOCKER_REQUIRED}\n(cause: {docker_error})", pytrace=False)

    # Ryuk, the reaper container, is one more image to pull; with it off, `pixi run test` is
    # offline once POSTGRES_IMAGE is pulled. The `with` below still removes the container.
    testcontainers_config.ryuk_disabled = True
    # fsync off: the test server's data is thrown away, and it makes CREATE DATABASE cheap.
    server = PostgresContainer(
        POSTGRES_IMAGE, username="rag", password="rag", dbname="rag", driver=None
    ).with_command("postgres -c fsync=off")
    with server:
        yield server.get_connection_url()


def _docker_error() -> Exception | None:
    """Why the Docker daemon can't be reached, if it can't. Returned, not raised, so the failure
    message isn't buried under the docker SDK's chained tracebacks."""
    try:
        DockerClient().client.close()
    except Exception as exc:
        return exc
    return None


@contextmanager
def fresh_database(server_url: str) -> Generator[str]:
    """Create an empty database on the server, yield its URL, then drop it."""
    name = f"test_{uuid4().hex}"
    with psycopg.connect(server_url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        yield urlunsplit(urlsplit(server_url)._replace(path=f"/{name}"))
    finally:
        with psycopg.connect(server_url, autocommit=True) as admin:
            # FORCE: a test may leave connections open (a store's pool, say).
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
