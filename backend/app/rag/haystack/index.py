"""The Passage index: pgvector as the source of truth (ADR-0004), searched hybrid (ADR-0005).

`PassageIndex` is the adapter's whole interface to the rest of the backend: open it at startup,
`sync` it with `knowledge-base/`, and `retrieve` Passages for a Standalone Question. It is the
Haystack-backed `PassageRetriever`.
"""

import asyncio
from pathlib import Path
from types import TracebackType
from typing import Final, Self

import psycopg
from haystack.document_stores.errors import DocumentStoreError
from haystack.utils import Secret

# haystack_integrations is a namespace package, so pyright misses its subpackages' py.typed;
# it still type-checks them from source.
from haystack_integrations.document_stores.pgvector import (  # pyright: ignore[reportMissingTypeStubs]
    PgvectorDocumentStore,
)
from psycopg.conninfo import make_conninfo
from pydantic import SecretStr

from app.errors import AppError
from app.passages import Passage
from app.rag.haystack.embedding import Embedder, fastembed_embedder
from app.rag.haystack.indexing import SyncReport, build_index, indexing_pipeline
from app.rag.haystack.retrieval import Bm25Mirror, HybridRetriever

TABLE: Final = "passages"
# From operational readiness (#15): fail fast rather than hang; no retries.
CONNECT_TIMEOUT_S: Final = 5
STATEMENT_TIMEOUT_MS: Final = 10_000

RETRIEVAL_UNAVAILABLE: Final = "The Knowledge Base can't be searched right now. Please try again."


class EmbeddingDimensionMismatchError(RuntimeError):
    """The stored table was built for another embedding dimension; startup can't go on."""


class PassageIndex:
    def __init__(
        self, store: PgvectorDocumentStore, embedder: Embedder, mirror: Bm25Mirror, *, top_k: int
    ) -> None:
        """Use `PassageIndex.open`, which checks the store and loads the BM25 mirror."""
        self._store = store
        self._embedder = embedder
        self._mirror = mirror
        self._indexing = indexing_pipeline(store, embedder)
        self._retriever = HybridRetriever(store, embedder, top_k=top_k)
        # The store shares one connection and its cursors between calls, so concurrent calls
        # could read each other's results: one store call at a time.
        self._store_lock = asyncio.Lock()

    @classmethod
    async def open(
        cls, database_url: SecretStr, *, top_k: int, embedder: Embedder | None = None
    ) -> Self:
        """Connect to the Passage store, creating the table and the `vector` extension if missing,
        and build the BM25 mirror from what it holds.

        Raises EmbeddingDimensionMismatchError if the table holds embeddings of a dimension other
        than the embedder's: the table is a derived index, so the fix is to drop and re-ingest.
        """
        embedder = embedder or fastembed_embedder()
        conninfo = make_conninfo(
            database_url.get_secret_value(),
            connect_timeout=CONNECT_TIMEOUT_S,
            options=f"-c statement_timeout={STATEMENT_TIMEOUT_MS}",
        )
        await _check_dimension(conninfo, embedder)
        store = PgvectorDocumentStore(
            connection_string=Secret.from_token(conninfo),
            create_extension=True,
            table_name=TABLE,
            embedding_dimension=embedder.dimension,
            vector_function="cosine_similarity",
            search_strategy="exact_nearest_neighbor",
        )
        # Connects, and creates the table if it's missing.
        mirror = Bm25Mirror(await store.filter_documents_async())
        return cls(store, embedder, mirror, top_k=top_k)

    async def sync(self, knowledge_base: Path) -> SyncReport:
        """Make the index match `knowledge_base`, re-embedding only what changed, then rebuild
        the BM25 mirror from the store. Retrieval waits while it runs."""
        async with self._store_lock:
            report = await build_index(
                knowledge_base, self._store, self._indexing, embedding_model=self._embedder.model
            )
            self._mirror = Bm25Mirror(await self._store.filter_documents_async())
        return report

    async def retrieve(self, question: str) -> tuple[Passage, ...]:
        """The `PassageRetriever` interface: see `app.passages.PassageRetriever`."""
        try:
            async with self._store_lock:
                return await self._retriever.retrieve(question, self._mirror)
        except (DocumentStoreError, psycopg.Error) as error:
            raise AppError("retrieval_unavailable", RETRIEVAL_UNAVAILABLE) from error

    async def close(self) -> None:
        await self._store.close_async()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()


async def _check_dimension(conninfo: str, embedder: Embedder) -> None:
    async with await psycopg.AsyncConnection.connect(conninfo) as connection:
        cursor = await connection.execute(
            # A vector(n) column's type modifier is n.
            "SELECT atttypmod FROM pg_attribute"
            " WHERE attrelid = to_regclass(%s) AND attname = 'embedding'",
            [TABLE],
        )
        row = await cursor.fetchone()
    if row is not None and row[0] != embedder.dimension:
        raise EmbeddingDimensionMismatchError(
            f"The {TABLE} table holds {row[0]}-dimension embeddings, but the embedding model "
            f"{embedder.model} makes {embedder.dimension}-dimension ones. The table is derived "
            f"from knowledge-base/: drop it (DROP TABLE {TABLE};) and restart to re-ingest."
        )
