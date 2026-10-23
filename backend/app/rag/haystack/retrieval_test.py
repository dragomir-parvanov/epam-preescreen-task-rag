import math
from pathlib import Path

import psycopg
import pytest
from pydantic import SecretStr

from app.errors import AppError
from app.passages import ArticleRef, Passage, PassageRetriever, SectionRef
from app.rag.haystack.conftest import KnowledgeBase, RecordingEmbedder, keyword_embedding
from app.rag.haystack.embedding import Embedder, fake_embedder
from app.rag.haystack.index import PassageIndex

pytestmark = [pytest.mark.pgvector, pytest.mark.anyio]


async def synced_index(
    url: str, embedder: Embedder, knowledge_base: Path, *, top_k: int = 6
) -> PassageIndex:
    index = await PassageIndex.open(SecretStr(url), top_k=top_k, embedder=embedder)
    await index.sync(knowledge_base)
    return index


async def test_a_question_retrieves_the_passages_that_share_its_words_best_first(
    pgvector_database_url: str, keyword_embedder: RecordingEmbedder, knowledge_base: KnowledgeBase
) -> None:
    knowledge_base.write(
        "sso",
        "## Okta\n\nAdd the Nimbus app in Okta.\n\n"
        "## Troubleshooting\n\nAUTH-401 means the IdP clock is skewed.\n",
        title="Configuring SSO",
    )
    knowledge_base.write("webhooks", "## Rate limits\n\nBusiness: 600 req/min.\n")

    async with await synced_index(
        pgvector_database_url, keyword_embedder.embedder, knowledge_base.directory
    ) as index:
        retriever: PassageRetriever = index
        best, *rest = await retriever.retrieve("What does AUTH-401 mean? Is the clock skewed?")

    assert best == Passage(
        id="sso#troubleshooting-1",
        article=ArticleRef(id="sso", title="Configuring SSO"),
        section=SectionRef(id="troubleshooting", path=("Configuring SSO", "Troubleshooting")),
        text="AUTH-401 means the IdP clock is skewed.",
        applies_to=("v3",),
        status="current",
        score=best.score,
    )
    assert all(best.score > passage.score for passage in rest)


async def test_retrieval_returns_at_most_top_k_passages(
    pgvector_database_url: str, keyword_embedder: RecordingEmbedder, knowledge_base: KnowledgeBase
) -> None:
    body = "".join(f"## Limit {n}\n\nThe limit is {n} requests.\n\n" for n in range(10))
    knowledge_base.write("limits", body)

    async with await synced_index(
        pgvector_database_url, keyword_embedder.embedder, knowledge_base.directory, top_k=4
    ) as index:
        passages = await index.retrieve("What is the requests limit?")

    assert len(passages) == 4


# A fake that, like a real model, sees "logon" and "login" as the same word, while BM25 doesn't.
SYNONYMS = {"logon": "login"}


def semantic_embedding(text: str) -> list[float]:
    words = text.lower().split()
    return keyword_embedding(" ".join(SYNONYMS.get(word, word) for word in words))


def write_logon_decoys_and_an_error_table(knowledge_base: KnowledgeBase) -> None:
    """25 short "logon" Sections that dense search ranks first for a "login" question, and one
    long error table holding the exact identifier, which only BM25 ranks highly."""
    decoys = "".join(f"## Logon step {n}\n\nopen the portal logon page\n\n" for n in range(25))
    knowledge_base.write("logon", decoys, title="Logon")
    filler = " ".join(f"word{n}" for n in range(60))
    knowledge_base.write(
        "errors", f"## Codes\n\nAUTH-409 duplicate email. {filler}\n", title="Errors"
    )


QUESTION = "login fails with AUTH-409"


async def test_an_exact_identifier_that_only_bm25_ranks_highly_still_reaches_the_top_k(
    pgvector_database_url: str, knowledge_base: KnowledgeBase
) -> None:
    write_logon_decoys_and_an_error_table(knowledge_base)
    embedder = fake_embedder(semantic_embedding, model="semantic")

    async with await synced_index(
        pgvector_database_url, embedder, knowledge_base.directory, top_k=3
    ) as index:
        passages = await index.retrieve(QUESTION)

    ids = [passage.id for passage in passages]
    assert "errors#codes-1" in ids
    # Dense search alone ranks it below every logon decoy, so it's there thanks to BM25.
    error_table = passages[ids.index("errors#codes-1")]
    assert all(error_table.score < p.score for p in passages if p is not error_table)


async def test_every_passage_carries_its_dense_cosine_score_even_a_bm25_only_hit(
    pgvector_database_url: str, knowledge_base: KnowledgeBase
) -> None:
    write_logon_decoys_and_an_error_table(knowledge_base)
    embedder = fake_embedder(semantic_embedding, model="semantic")
    query = semantic_embedding(QUESTION)

    async with await synced_index(
        pgvector_database_url, embedder, knowledge_base.directory, top_k=3
    ) as index:
        passages = await index.retrieve(QUESTION)

    assert "errors#codes-1" in [p.id for p in passages]  # a BM25-only hit
    # What was embedded for each Passage: its "<Article title> > <Section path>" header + text.
    cosines = [
        _cosine(query, semantic_embedding(" > ".join(p.section.path) + "\n" + p.text))
        for p in passages
    ]
    assert [p.score for p in passages] == pytest.approx(cosines)


async def test_a_new_process_rebuilds_the_bm25_mirror_from_the_store(
    pgvector_database_url: str, knowledge_base: KnowledgeBase
) -> None:
    write_logon_decoys_and_an_error_table(knowledge_base)
    embedder = fake_embedder(semantic_embedding, model="semantic")
    await (await synced_index(pgvector_database_url, embedder, knowledge_base.directory)).close()

    async with await PassageIndex.open(
        SecretStr(pgvector_database_url), top_k=3, embedder=embedder
    ) as index:
        passages = await index.retrieve(QUESTION)

    assert "errors#codes-1" in [passage.id for passage in passages]


async def test_retrieval_follows_the_latest_sync(
    pgvector_database_url: str, keyword_embedder: RecordingEmbedder, knowledge_base: KnowledgeBase
) -> None:
    knowledge_base.write("sso", "## Okta\n\nAdd the Nimbus app in Okta.\n")
    async with await synced_index(
        pgvector_database_url, keyword_embedder.embedder, knowledge_base.directory
    ) as index:
        knowledge_base.write("sso", "## Entra\n\nAdd the Nimbus app in Entra ID.\n")
        await index.sync(knowledge_base.directory)

        passages = await index.retrieve("Okta or Entra?")

    assert [passage.id for passage in passages] == ["sso#entra-1"]


async def test_a_database_failure_during_retrieval_is_retrieval_unavailable(
    pgvector_database_url: str, keyword_embedder: RecordingEmbedder, knowledge_base: KnowledgeBase
) -> None:
    knowledge_base.write("sso", "## Okta\n\nAdd the Nimbus app in Okta.\n")
    async with await synced_index(
        pgvector_database_url, keyword_embedder.embedder, knowledge_base.directory
    ) as index:
        with psycopg.connect(pgvector_database_url, autocommit=True) as conn:
            conn.execute("DROP TABLE passages")

        with pytest.raises(AppError) as error:
            await index.retrieve("Okta?")

    assert error.value.code == "retrieval_unavailable"


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))
