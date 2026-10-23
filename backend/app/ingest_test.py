import pytest
from pydantic import SecretStr

from app.ingest import ingest
from app.rag.haystack.conftest import KnowledgeBase, RecordingEmbedder

pytestmark = [pytest.mark.pgvector, pytest.mark.anyio]

SSO = "## Okta\n\nAdd the Nimbus app in Okta.\n\n## Troubleshooting\n\nAUTH-401 is clock skew.\n"


async def test_ingest_syncs_and_a_second_run_writes_nothing(
    pgvector_database_url: str, tmp_path_factory: pytest.TempPathFactory
) -> None:
    knowledge_base = KnowledgeBase(tmp_path_factory.mktemp("knowledge-base"))
    knowledge_base.write("sso", SSO)
    url, embedder = SecretStr(pgvector_database_url), RecordingEmbedder().embedder

    first = await ingest(url, knowledge_base.directory, rebuild=False, embedder=embedder)
    second = await ingest(url, knowledge_base.directory, rebuild=False, embedder=embedder)

    assert first.written == ("sso#okta-1", "sso#troubleshooting-1")
    assert second.written == ()


async def test_ingest_with_rebuild_re_embeds_everything(
    pgvector_database_url: str, tmp_path_factory: pytest.TempPathFactory
) -> None:
    knowledge_base = KnowledgeBase(tmp_path_factory.mktemp("knowledge-base"))
    knowledge_base.write("sso", SSO)
    url, embedder = SecretStr(pgvector_database_url), RecordingEmbedder().embedder
    await ingest(url, knowledge_base.directory, rebuild=False, embedder=embedder)

    report = await ingest(url, knowledge_base.directory, rebuild=True, embedder=embedder)

    assert report.written == ("sso#okta-1", "sso#troubleshooting-1")
