"""The embedding model: fastembed bge-small-en-v1.5 in-process, or Haystack's fakes in tests.

What gets embedded for a Passage is its `"<Article title> > <Section path>"` header plus its
verbatim text. With dozens of "Troubleshooting" Sections, the header is what tells them apart.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final, Protocol

from haystack import Document
from haystack.components.embedders import MockDocumentEmbedder, MockTextEmbedder

# haystack_integrations is a namespace package, so pyright misses its subpackages' py.typed;
# it still type-checks them from source.
from haystack_integrations.components.embedders.fastembed import (  # pyright: ignore[reportMissingTypeStubs]
    FastembedDocumentEmbedder,
    FastembedTextEmbedder,
)

# Fixed, with no setting to change it (#10). The backend image bakes this model in at build time
# (backend/Dockerfile), so startup never downloads it.
EMBEDDING_MODEL: Final = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSION: Final = 384
# bge's instruction for retrieval queries; Passages are embedded without it.
QUERY_PREFIX: Final = "Represent this sentence for searching relevant passages: "

# The Document meta field holding a Passage's "<Article title> > <Section path>" header.
HEADER_FIELD: Final = "header"
_HEADER_SEPARATOR: Final = "\n"


class DocumentEmbedder(Protocol):
    def run(self, documents: list[Document]) -> dict[str, Any]: ...


class TextEmbedder(Protocol):
    def run(self, text: str) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class Embedder:
    """One embedding model, as the pair of Haystack components that embed Passages and queries."""

    model: str
    """Part of every Passage's fingerprint, so a new model re-embeds everything on the next sync."""
    dimension: int
    passages: DocumentEmbedder
    """Embeds `HEADER_FIELD` + the Passage text. CPU-bound: run it off the event loop."""
    queries: TextEmbedder
    """CPU-bound: run it off the event loop."""


def fastembed_embedder(*, query_prefix: bool = True) -> Embedder:
    """The production model. `query_prefix=False` is for the eval's one-off with/without report."""
    return Embedder(
        model=EMBEDDING_MODEL,
        dimension=EMBEDDING_DIMENSION,
        passages=FastembedDocumentEmbedder(
            model=EMBEDDING_MODEL,
            progress_bar=False,
            meta_fields_to_embed=[HEADER_FIELD],
            embedding_separator=_HEADER_SEPARATOR,
        ),
        queries=FastembedTextEmbedder(
            model=EMBEDDING_MODEL, progress_bar=False, prefix=QUERY_PREFIX if query_prefix else ""
        ),
    )


def fake_embedder(
    embedding_fn: Callable[[str], list[float]], *, model: str, dimension: int = EMBEDDING_DIMENSION
) -> Embedder:
    """Haystack's mock embedders over `embedding_fn`, which sees exactly the text fastembed would
    (minus the query prefix). For keyless, offline tests."""
    return Embedder(
        model=model,
        dimension=dimension,
        passages=MockDocumentEmbedder(
            embedding_fn=embedding_fn,
            model=model,
            meta_fields_to_embed=[HEADER_FIELD],
            embedding_separator=_HEADER_SEPARATOR,
        ),
        queries=MockTextEmbedder(embedding_fn=embedding_fn, model=model),
    )
