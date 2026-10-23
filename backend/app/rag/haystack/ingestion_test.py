"""Startup ingestion driving the real Passage index: retries until Postgres can be used."""

import asyncio
import itertools
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from pydantic import SecretStr

from app.ingestion import Ingestion
from app.rag.haystack.conftest import KnowledgeBase, RecordingEmbedder
from app.rag.haystack.index import PassageIndex

pytestmark = [pytest.mark.pgvector, pytest.mark.anyio]


async def test_ingestion_backs_off_until_the_database_exists_then_the_index_is_ready(
    pgvector_server_url: str, keyword_embedder: RecordingEmbedder, knowledge_base: KnowledgeBase
) -> None:
    knowledge_base.write("sso", "## Okta\n\nAdd the Nimbus app in Okta.\n")
    database = f"test_{uuid4().hex}"
    name = sql.Identifier(database)
    url = urlunsplit(urlsplit(pgvector_server_url)._replace(path=f"/{database}"))
    ingestion = Ingestion(
        lambda: PassageIndex.open(SecretStr(url), top_k=6, embedder=keyword_embedder.embedder),
        knowledge_base.directory,
        delays=lambda: itertools.repeat(0.05),
    )

    ingestion.start()
    try:
        async with asyncio.timeout(10):
            while ingestion.status.detail is None:
                await asyncio.sleep(0.01)
        failing = ingestion.status
        with psycopg.connect(pgvector_server_url, autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {}").format(name))
        async with asyncio.timeout(10):
            while not ingestion.status.ok:
                await asyncio.sleep(0.01)

        assert not failing.ok
        assert f'database "{database}" does not exist' in (failing.detail or "")
        assert ingestion.index is not None
        [passage] = await ingestion.index.retrieve("Okta")
        assert passage.id == "sso#okta-1"
    finally:
        await ingestion.stop()
        with psycopg.connect(pgvector_server_url, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(name))
