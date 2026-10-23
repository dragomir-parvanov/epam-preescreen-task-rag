"""The Passage index: pgvector as the source of truth (ADR-0004), searched hybrid (ADR-0005).

`PassageIndex` is the adapter's whole interface to the rest of the backend: open it at startup,
`sync` it with `knowledge-base/`, and `retrieve` Passages for a Standalone Question. It is the
Haystack-backed `PassageRetriever`, and the `SyncableIndex` that startup ingestion drives.

Opening (which may create the table), syncing and dropping hold a Postgres advisory lock, so
backends starting together, or `python -m app.ingest`, take turns instead of racing. A connection
of its own holds the lock, which is released when it closes, even if the process dies.
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from types import TracebackType
from typing import Final, Self

import psycopg
import structlog
from haystack.document_stores.errors import DocumentStoreError
from haystack.utils import Secret

# haystack_integrations is a namespace package, so pyright misses its subpackages' py.typed;
# it still type-checks them from source.
from haystack_integrations.document_stores.pgvector import (  # pyright: ignore[reportMissingTypeStubs]
    PgvectorDocumentStore,
)
from pydantic import SecretStr

from app.database import conninfo as database_conninfo
from app.errors import AppError
from app.ingestion import UnrecoverableIndexError
from app.passages import Passage
from app.rag.haystack.embedding import Embedder, fastembed_embedder
from app.rag.haystack.indexing import SyncReport, build_index, indexing_pipeline
from app.rag.haystack.retrieval import Bm25Mirror, HybridRetriever

TABLE: Final = "passages"
# Every writer to the table takes the advisory lock keyed by `hashtext()` of this name.
_LOCK_NAME: Final = "passages-sync"

RETRIEVAL_UNAVAILABLE: Final = "The Knowledge Base can't be searched right now. Please try again."

logger = structlog.stdlib.get_logger(__name__)


class EmbeddingDimensionMismatchError(UnrecoverableIndexError):
    """The stored table was built for another embedding dimension; startup can't go on."""


class PassageIndex:
    def __init__(
        self,
        store: PgvectorDocumentStore,
        embedder: Embedder,
        mirror: Bm25Mirror,
        conninfo: str,
        *,
        top_k: int,
    ) -> None:
        """Use `PassageIndex.open`, which checks the store and loads the BM25 mirror."""
        self._store = store
        self._embedder = embedder
        self._mirror = mirror
        self._conninfo = conninfo
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
        conninfo = database_conninfo(database_url)
        store = PgvectorDocumentStore(
            connection_string=Secret.from_token(conninfo),
            create_extension=True,
            table_name=TABLE,
            embedding_dimension=embedder.dimension,
            vector_function="cosine_similarity",
            search_strategy="exact_nearest_neighbor",
        )
        async with _advisory_lock(conninfo):
            await _check_dimension(conninfo, embedder)
            # Connects, and creates the extension and the table if they're missing.
            mirror = Bm25Mirror(await store.filter_documents_async())
        return cls(store, embedder, mirror, conninfo, top_k=top_k)

    @staticmethod
    async def drop(database_url: SecretStr) -> None:
        """Drop the Passage table, if there is one, so the next `open` and `sync` rebuild it."""
        conninfo = database_conninfo(database_url)
        async with (
            _advisory_lock(conninfo),
            await psycopg.AsyncConnection.connect(conninfo, autocommit=True) as connection,
        ):
            await connection.execute(f"DROP TABLE IF EXISTS {TABLE}")
        logger.info("index_dropped", table=TABLE)

    async def sync(self, knowledge_base: Path) -> SyncReport:
        """Make the index match `knowledge_base`, re-embedding only what changed, then rebuild
        the BM25 mirror from the store. Retrieval waits while it runs, and so does another
        process's sync: the second of two concurrent syncs finds nothing left to write."""
        started = time.perf_counter()
        async with self._store_lock, _advisory_lock(self._conninfo):
            report = await build_index(
                knowledge_base, self._store, self._indexing, embedding_model=self._embedder.model
            )
            self._mirror = Bm25Mirror(await self._store.filter_documents_async())
        logger.info(
            "index_synced",
            written=len(report.written),
            deleted=len(report.deleted),
            unchanged=report.unchanged,
            duration_ms=round((time.perf_counter() - started) * 1000, 1),
        )
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


@asynccontextmanager
async def _advisory_lock(conninfo: str) -> AsyncGenerator[None]:
    """Hold the table's advisory lock, waiting for as long as another holder keeps it."""
    async with await psycopg.AsyncConnection.connect(conninfo, autocommit=True) as connection:
        # A first sync embeds every Passage, which takes longer than the statement timeout.
        await connection.execute("SET statement_timeout = 0")
        await connection.execute("SELECT pg_advisory_lock(hashtext(%s))", [_LOCK_NAME])
        yield
    # Closing the connection released the lock.


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
            "from knowledge-base/: rebuild it with `pixi run reindex`."
        )
