"""Hybrid retrieval (ADR-0005): dense pgvector + an in-memory BM25 mirror, fused by RRF.

Each leg takes its top `CANDIDATES`; `DocumentJoiner` fuses them with reciprocal rank fusion,
called as a standalone component (there is no query Pipeline, ADR-0003), and the result is cut
to `top_k`. The RRF score only orders: every returned Passage carries its dense cosine score,
computed from its stored embedding when only BM25 found it.
"""

import asyncio
import math
from collections.abc import Iterable, Sequence
from typing import Final

from haystack import Document
from haystack.components.joiners import DocumentJoiner
from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
from haystack.document_stores.in_memory import InMemoryDocumentStore

# haystack_integrations is a namespace package, so pyright misses its subpackages' py.typed;
# it still type-checks them from source.
from haystack_integrations.components.retrievers.pgvector import (  # pyright: ignore[reportMissingTypeStubs]
    PgvectorEmbeddingRetriever,
)
from haystack_integrations.document_stores.pgvector import (  # pyright: ignore[reportMissingTypeStubs]
    PgvectorDocumentStore,
)

from app.passages import Passage
from app.rag.haystack.documents import header_and_text, to_passage
from app.rag.haystack.embedding import Embedder

CANDIDATES: Final = 20


class Bm25Mirror:
    """The stored Passages, BM25-indexed under their header + text. Rebuilt, never updated."""

    def __init__(self, stored: Iterable[Document]) -> None:
        self.stored: dict[str, Document] = {document.id: document for document in stored}
        """The Passages as pgvector holds them: verbatim text, meta and embedding."""
        store = InMemoryDocumentStore(shared=False)
        store.write_documents(
            [Document(id=d.id, content=header_and_text(d)) for d in self.stored.values()]
        )
        self._retriever = InMemoryBM25Retriever(document_store=store, top_k=CANDIDATES)

    async def search(self, question: str) -> list[Document]:
        documents: list[Document] = (await self._retriever.run_async(query=question))["documents"]
        return documents


class HybridRetriever:
    def __init__(self, store: PgvectorDocumentStore, embedder: Embedder, *, top_k: int) -> None:
        self._embedder = embedder
        self._top_k = top_k
        self._dense = PgvectorEmbeddingRetriever(document_store=store, top_k=CANDIDATES)
        self._fuse = DocumentJoiner(join_mode="reciprocal_rank_fusion")

    async def retrieve(
        self, question: str, mirror: Bm25Mirror, *, dense_only: bool = False
    ) -> tuple[Passage, ...]:
        """`dense_only` drops the BM25 leg: the eval's ablation, never the server's retrieval."""
        # fastembed is CPU-bound and sync-only: keep it off the event loop.
        embedded = await asyncio.to_thread(self._embedder.queries.run, text=question)
        query: list[float] = embedded["embedding"]
        dense: list[Document] = (await self._dense.run_async(query_embedding=query))["documents"]
        legs = [dense] if dense_only else [dense, await mirror.search(question)]

        fused: list[Document] = self._fuse.run(documents=legs, top_k=self._top_k)["documents"]
        cosine = {document.id: document.score for document in dense}
        stored = mirror.stored | {document.id: document for document in dense}
        passages: list[Passage] = []
        for document in fused:
            original = stored[document.id]
            score = cosine.get(document.id)
            if score is None:  # a BM25-only hit
                if original.embedding is None:
                    raise ValueError(f"stored Passage {original.id} has no embedding")
                score = _cosine(query, original.embedding)
            passages.append(to_passage(original, score=score))
        return tuple(passages)


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    norms = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b, strict=True)) / norms if norms else 0.0
