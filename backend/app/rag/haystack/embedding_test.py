import re
from pathlib import Path

from app.rag.haystack.embedding import EMBEDDING_MODEL

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_the_backend_image_bakes_in_the_embedding_model_the_backend_loads() -> None:
    dockerfile = (REPO_ROOT / "backend" / "Dockerfile").read_text()

    baked = re.findall(r"TextEmbedding\('([^']+)'\)", dockerfile)

    assert baked == [EMBEDDING_MODEL]
    assert re.search(r"^ENV FASTEMBED_CACHE_PATH=", dockerfile, flags=re.MULTILINE)
