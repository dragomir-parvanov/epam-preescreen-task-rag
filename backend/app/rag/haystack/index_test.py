import psycopg
import pytest
from pydantic import SecretStr

from app.rag.haystack.conftest import KnowledgeBase, RecordingEmbedder
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
        "drop it (DROP TABLE passages;) and restart to re-ingest."
    )
