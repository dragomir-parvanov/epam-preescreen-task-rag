import math
import re
import zlib
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from app.rag.haystack.embedding import EMBEDDING_DIMENSION, Embedder, fake_embedder


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def keyword_embedding(text: str) -> list[float]:
    """A bag of words hashed into EMBEDDING_DIMENSION buckets and normalised: texts sharing more
    words have a higher cosine, so ranking assertions mean something without a real model."""
    vector = [0.0] * EMBEDDING_DIMENSION
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        vector[zlib.crc32(word.encode()) % EMBEDDING_DIMENSION] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


@dataclass
class RecordingEmbedder:
    """The keyword embedder, recording every text it embeds."""

    model: str = "keyword-overlap"
    embedded: list[str] = field(default_factory=list[str])

    def embed(self, text: str) -> list[float]:
        self.embedded.append(text)
        return keyword_embedding(text)

    @property
    def embedder(self) -> Embedder:
        return fake_embedder(self.embed, model=self.model)


@pytest.fixture
def keyword_embedder() -> RecordingEmbedder:
    return RecordingEmbedder()


@dataclass
class KnowledgeBase:
    """A small Knowledge Base of test Articles in a temporary directory."""

    directory: Path

    def write(self, article_id: str, body: str, *, title: str | None = None) -> None:
        front_matter = (
            f"---\nid: {article_id}\ntitle: {title or article_id.title()}\n"
            "applies_to: [v3]\nstatus: current\n---\n"
        )
        (self.directory / f"{article_id}.md").write_text(front_matter + body)

    def delete(self, article_id: str) -> None:
        (self.directory / f"{article_id}.md").unlink()


@pytest.fixture
def knowledge_base(tmp_path: Path) -> KnowledgeBase:
    directory = tmp_path / "knowledge-base"
    directory.mkdir()
    return KnowledgeBase(directory)
