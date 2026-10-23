import asyncio
import time

import psycopg
import pytest
from pydantic import SecretStr

from app.rag.haystack.conftest import KnowledgeBase, RecordingEmbedder, keyword_embedding
from app.rag.haystack.embedding import fake_embedder
from app.rag.haystack.index import EmbeddingDimensionMismatchError, PassageIndex, SyncReport

pytestmark = [pytest.mark.pgvector, pytest.mark.anyio]

SSO = "## Okta\n\nAdd the Nimbus app in Okta.\n\n## Troubleshooting\n\nAUTH-401 is clock skew.\n"
WEBHOOKS = "## Rate limits\n\nBusiness: 600 req/min.\n"


async def open_index(url: str, embedder: RecordingEmbedder) -> PassageIndex:
    return await PassageIndex.open(SecretStr(url), top_k=6, embedder=embedder.embedder)


async def test_the_first_sync_embeds_and_writes_every_passage(
    pgvector_database_url: str, keyword_embedder: RecordingEmbedder, knowledge_base: KnowledgeBase
) -> None:
    knowledge_base.write("sso", SSO)
    knowledge_base.write("webhooks", WEBHOOKS)

    async with await open_index(pgvector_database_url, keyword_embedder) as index:
        report = await index.sync(knowledge_base.directory)

    assert report == SyncReport(
        written=("sso#okta-1", "sso#troubleshooting-1", "webhooks#rate-limits-1"),
        deleted=(),
        unchanged=0,
    )
    # The header that tells "Troubleshooting" Sections apart is embedded with the verbatim text.
    assert "Sso > Troubleshooting\nAUTH-401 is clock skew." in keyword_embedder.embedded


async def test_a_second_sync_of_an_unchanged_knowledge_base_writes_nothing(
    pgvector_database_url: str, keyword_embedder: RecordingEmbedder, knowledge_base: KnowledgeBase
) -> None:
    knowledge_base.write("sso", SSO)
    async with await open_index(pgvector_database_url, keyword_embedder) as index:
        await index.sync(knowledge_base.directory)
    keyword_embedder.embedded.clear()

    # A fresh process: the index persists in Postgres.
    async with await open_index(pgvector_database_url, keyword_embedder) as index:
        report = await index.sync(knowledge_base.directory)

    assert report == SyncReport(written=(), deleted=(), unchanged=2)
    assert keyword_embedder.embedded == []


async def test_editing_a_section_re_embeds_only_its_passages(
    pgvector_database_url: str, keyword_embedder: RecordingEmbedder, knowledge_base: KnowledgeBase
) -> None:
    knowledge_base.write("sso", SSO)
    async with await open_index(pgvector_database_url, keyword_embedder) as index:
        await index.sync(knowledge_base.directory)
        keyword_embedder.embedded.clear()
        knowledge_base.write("sso", SSO.replace("clock skew", "clock skew over 5 minutes"))

        report = await index.sync(knowledge_base.directory)

    assert report == SyncReport(written=("sso#troubleshooting-1",), deleted=(), unchanged=1)
    assert keyword_embedder.embedded == [
        "Sso > Troubleshooting\nAUTH-401 is clock skew over 5 minutes."
    ]


async def test_deleting_a_section_or_an_article_deletes_its_passages(
    pgvector_database_url: str, keyword_embedder: RecordingEmbedder, knowledge_base: KnowledgeBase
) -> None:
    knowledge_base.write("sso", SSO)
    knowledge_base.write("webhooks", WEBHOOKS)
    async with await open_index(pgvector_database_url, keyword_embedder) as index:
        await index.sync(knowledge_base.directory)
        knowledge_base.write("sso", "## Okta\n\nAdd the Nimbus app in Okta.\n")
        knowledge_base.delete("webhooks")

        report = await index.sync(knowledge_base.directory)
        again = await index.sync(knowledge_base.directory)

    assert report == SyncReport(
        written=(), deleted=("sso#troubleshooting-1", "webhooks#rate-limits-1"), unchanged=1
    )
    assert again == SyncReport(written=(), deleted=(), unchanged=1)


async def test_a_new_embedding_model_re_embeds_every_passage(
    pgvector_database_url: str, knowledge_base: KnowledgeBase
) -> None:
    knowledge_base.write("sso", SSO)
    async with await open_index(pgvector_database_url, RecordingEmbedder(model="old")) as index:
        await index.sync(knowledge_base.directory)

    async with await open_index(pgvector_database_url, RecordingEmbedder(model="new")) as index:
        report = await index.sync(knowledge_base.directory)

    assert report.written == ("sso#okta-1", "sso#troubleshooting-1")


async def test_opening_over_a_table_of_another_embedding_dimension_fails_with_the_fix(
    pgvector_database_url: str, keyword_embedder: RecordingEmbedder
) -> None:
    with psycopg.connect(pgvector_database_url) as conn:
        conn.execute("CREATE EXTENSION vector")
        conn.execute("CREATE TABLE passages (id varchar(128) PRIMARY KEY, embedding vector(768))")

    with pytest.raises(EmbeddingDimensionMismatchError) as error:
        await open_index(pgvector_database_url, keyword_embedder)

    assert str(error.value) == (
        "The passages table holds 768-dimension embeddings, but the embedding model "
        "keyword-overlap makes 384-dimension ones. The table is derived from knowledge-base/: "
        "rebuild it with `pixi run reindex`."
    )


async def test_two_backends_syncing_at_once_take_turns_and_the_second_writes_nothing(
    pgvector_database_url: str, knowledge_base: KnowledgeBase
) -> None:
    knowledge_base.write("sso", SSO)
    knowledge_base.write("webhooks", WEBHOOKS)

    def slow_embedding(text: str) -> list[float]:
        time.sleep(0.2)  # long enough for an unserialised second sync to see an empty table
        return keyword_embedding(text)

    embedder = fake_embedder(slow_embedding, model="keyword-overlap")
    # Two processes on a fresh database: opening creates the table, which must not race either.
    first, second = await asyncio.gather(
        PassageIndex.open(SecretStr(pgvector_database_url), top_k=6, embedder=embedder),
        PassageIndex.open(SecretStr(pgvector_database_url), top_k=6, embedder=embedder),
    )
    async with first, second:
        reports = await asyncio.gather(
            first.sync(knowledge_base.directory), second.sync(knowledge_base.directory)
        )

    assert sorted(len(report.written) for report in reports) == [0, 3]
    assert sorted(report.unchanged for report in reports) == [0, 3]


async def test_dropping_the_index_makes_the_next_sync_rebuild_everything(
    pgvector_database_url: str, keyword_embedder: RecordingEmbedder, knowledge_base: KnowledgeBase
) -> None:
    knowledge_base.write("sso", SSO)
    async with await open_index(pgvector_database_url, keyword_embedder) as index:
        await index.sync(knowledge_base.directory)

    await PassageIndex.drop(SecretStr(pgvector_database_url))
    async with await open_index(pgvector_database_url, keyword_embedder) as index:
        report = await index.sync(knowledge_base.directory)

    assert report.written == ("sso#okta-1", "sso#troubleshooting-1")


async def test_dropping_an_index_that_does_not_exist_is_a_no_op(pgvector_database_url: str) -> None:
    await PassageIndex.drop(SecretStr(pgvector_database_url))
