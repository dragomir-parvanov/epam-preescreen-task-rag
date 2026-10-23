"""The embedding model: fastembed bge-small-en-v1.5 in-process, or Haystack's fakes in tests.

What gets embedded for a Passage is its `"<Article title> > <Section path>"` header plus its
verbatim text. With dozens of "Troubleshooting" Sections, the header is what tells them apart.
"""

import math
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
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
    passages: Callable[[], DocumentEmbedder]
    """Makes a component embedding `HEADER_FIELD` + the Passage text. A factory, because a
    component instance can only join one Pipeline. CPU-bound: run it off the event loop."""
    queries: TextEmbedder
    """CPU-bound: run it off the event loop."""


# One Passage per model call. A batch is padded to its longest text, and Passages run from a few
# dozen to 512 tokens, so fastembed's default of 256 per batch spent most of its time on padding.
# Measured on 4 CPUs: 8 Passages/s at 256 per batch, 18/s at 4, 32/s at 1 (1,150 Passages: 36 s).
PASSAGE_BATCH_SIZE: Final = 1

_CGROUP_CPU_MAX: Final = Path("/sys/fs/cgroup/cpu.max")


def cpu_budget(cpus: int | None = None, cpu_max: Path = _CGROUP_CPU_MAX) -> int:
    """How many CPUs this process may use: all of them, unless a cgroup v2 quota is lower.

    onnxruntime sizes its thread pool from the host's CPU count, so under `docker run --cpus 4`
    on a 12-CPU host it runs 12 threads on 4 CPUs' worth of time, which made embedding 3x slower.
    """
    cpus = cpus or os.process_cpu_count() or 1
    try:
        quota, period = cpu_max.read_text().split()
    except (OSError, ValueError):
        return cpus
    if quota == "max":
        return cpus
    return max(1, min(cpus, math.ceil(int(quota) / int(period))))


def fastembed_embedder(*, query_prefix: bool = True) -> Embedder:
    """The production model. `query_prefix=False` is for the eval's one-off with/without report."""
    threads = cpu_budget()
    return Embedder(
        model=EMBEDDING_MODEL,
        dimension=EMBEDDING_DIMENSION,
        # fastembed caches the loaded model, so each new component reuses it.
        passages=lambda: FastembedDocumentEmbedder(
            model=EMBEDDING_MODEL,
            threads=threads,
            batch_size=PASSAGE_BATCH_SIZE,
            progress_bar=False,
            meta_fields_to_embed=[HEADER_FIELD],
            embedding_separator=_HEADER_SEPARATOR,
        ),
        queries=FastembedTextEmbedder(
            model=EMBEDDING_MODEL,
            threads=threads,
            progress_bar=False,
            prefix=QUERY_PREFIX if query_prefix else "",
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
        passages=lambda: MockDocumentEmbedder(
            embedding_fn=embedding_fn,
            model=model,
            meta_fields_to_embed=[HEADER_FIELD],
            embedding_separator=_HEADER_SEPARATOR,
        ),
        queries=MockTextEmbedder(embedding_fn=embedding_fn, model=model),
    )
