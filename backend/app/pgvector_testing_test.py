import json
import re
from pathlib import Path

import psycopg
import pytest

from app.pgvector_testing import POSTGRES_IMAGE, fresh_database, running_pgvector

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_compose_ships_the_postgres_image_the_tests_run_against() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text()

    defaults = re.findall(r"\$\{POSTGRES_IMAGE:-([^}]+)\}", compose)

    assert defaults == [POSTGRES_IMAGE]


def test_env_example_names_the_postgres_image_the_tests_run_against() -> None:
    env_example = (REPO_ROOT / ".env.example").read_text()

    values = re.findall(r"^POSTGRES_IMAGE=(.*)$", env_example, flags=re.MULTILINE)

    assert values == [POSTGRES_IMAGE]


def test_without_docker_the_server_fails_with_a_way_out_instead_of_skipping(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DOCKER_HOST", f"unix://{tmp_path / 'no-docker.sock'}")

    with (
        pytest.raises(pytest.fail.Exception, match="adapter tests need Docker") as failure,
        running_pgvector(),
    ):
        pass

    assert "pytest -m 'not pgvector'" in str(failure.value)


@pytest.mark.pgvector
def test_a_fresh_database_stores_and_returns_a_384_dimension_vector(
    pgvector_database_url: str,
) -> None:
    # Sixteenths: exact in float4 and short enough to survive vector's text output unrounded.
    embedding = [(i - 192) / 16 for i in range(384)]

    with psycopg.connect(pgvector_database_url) as conn:
        conn.execute("CREATE EXTENSION vector")
        conn.execute("CREATE TABLE passages (id int PRIMARY KEY, embedding vector(384))")
        conn.execute("INSERT INTO passages VALUES (1, %s::vector)", [str(embedding)])
        row = conn.execute("SELECT embedding::text FROM passages WHERE id = 1").fetchone()

    assert row is not None
    assert json.loads(row[0]) == embedding


@pytest.mark.pgvector
def test_each_fresh_database_starts_empty(pgvector_server_url: str) -> None:
    with fresh_database(pgvector_server_url) as first:
        with psycopg.connect(first) as conn:
            conn.execute("CREATE TABLE passages (id int)")

        with fresh_database(pgvector_server_url) as second, psycopg.connect(second) as conn:
            tables = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            ).fetchall()

    assert tables == []
