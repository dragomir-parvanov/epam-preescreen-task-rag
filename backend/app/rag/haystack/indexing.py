"""`build_index`: the idempotent sync of `knowledge-base/` into the pgvector Passage store."""

from dataclasses import dataclass
from pathlib import Path

from haystack import Pipeline
from haystack.components.writers import DocumentWriter
from haystack.document_stores.types import DuplicatePolicy

# haystack_integrations is a namespace package, so pyright misses its subpackages' py.typed;
# it still type-checks them from source.
from haystack_integrations.document_stores.pgvector import (  # pyright: ignore[reportMissingTypeStubs]
    PgvectorDocumentStore,
)

from app.knowledge_base import load_articles
from app.rag.haystack.documents import FINGERPRINT_FIELD, to_document
from app.rag.haystack.embedding import Embedder
from app.rag.haystack.splitting import split_article


@dataclass(frozen=True, slots=True, kw_only=True)
class SyncReport:
    written: tuple[str, ...]
    """Ids of the new or changed Passages, embedded and upserted."""
    deleted: tuple[str, ...]
    """Ids of the stored Passages that no longer exist in the Knowledge Base."""
    unchanged: int


def indexing_pipeline(store: PgvectorDocumentStore, embedder: Embedder) -> Pipeline:
    """embed -> write."""
    pipeline = Pipeline()
    pipeline.add_component("embedder", embedder.passages())
    pipeline.add_component(
        "writer", DocumentWriter(document_store=store, policy=DuplicatePolicy.OVERWRITE)
    )
    pipeline.connect("embedder.documents", "writer.documents")
    return pipeline


async def build_index(
    knowledge_base: Path, store: PgvectorDocumentStore, pipeline: Pipeline, *, embedding_model: str
) -> SyncReport:
    """Make the store hold exactly the Knowledge Base's Passages, embedding only what changed.

    `pipeline` is the store's `indexing_pipeline` for the `embedding_model` embedder. A Passage is
    new or changed when its id isn't stored, or its stored fingerprint (text, meta and embedding
    model) differs. Running it twice on an unchanged Knowledge Base writes nothing.
    """
    documents = [
        to_document(passage, embedding_model=embedding_model)
        for article in load_articles(knowledge_base)
        for passage in split_article(article)
    ]
    wanted = {document.id: document for document in documents}
    if len(wanted) != len(documents):
        clashes = sorted({d.id for d in documents if sum(e.id == d.id for e in documents) > 1})
        raise ValueError(f"two Passages would share an id; rename a heading: {clashes}")
    stored = {
        document.id: document.meta.get(FINGERPRINT_FIELD)
        for document in await store.filter_documents_async()
    }
    changed = [
        document
        for id, document in wanted.items()
        if stored.get(id) != document.meta[FINGERPRINT_FIELD]
    ]
    deleted = sorted(stored.keys() - wanted.keys())

    if changed:
        # Pipeline.run_async runs the (sync, CPU-bound) embedder in a worker thread.
        await pipeline.run_async({"embedder": {"documents": changed}})
    await store.delete_documents_async(deleted)

    return SyncReport(
        written=tuple(sorted(document.id for document in changed)),
        deleted=tuple(deleted),
        unchanged=len(wanted) - len(changed),
    )
