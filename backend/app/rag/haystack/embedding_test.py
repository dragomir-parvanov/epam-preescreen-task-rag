import re
from pathlib import Path

import pytest

from app.rag.haystack.embedding import EMBEDDING_MODEL, cpu_budget

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_the_backend_image_bakes_in_the_embedding_model_the_backend_loads() -> None:
    dockerfile = (REPO_ROOT / "backend" / "Dockerfile").read_text()

    baked = re.findall(r"TextEmbedding\('([^']+)'\)", dockerfile)

    assert baked == [EMBEDDING_MODEL]
    assert re.search(r"^ENV FASTEMBED_CACHE_PATH=", dockerfile, flags=re.MULTILINE)


@pytest.mark.parametrize(
    ("cpu_max", "budget"),
    [
        ("max 100000\n", 12),  # no limit: every CPU
        ("400000 100000\n", 4),  # `docker run --cpus 4` on a 12-CPU host
        ("150000 100000\n", 2),  # a fractional quota rounds up
        ("50000 100000\n", 1),
        (None, 12),  # no cgroup v2 file (macOS, cgroup v1)
    ],
)
def test_the_cpu_budget_respects_a_container_cpu_quota(
    tmp_path: Path, cpu_max: str | None, budget: int
) -> None:
    path = tmp_path / "cpu.max"
    if cpu_max is not None:
        path.write_text(cpu_max)

    assert cpu_budget(cpus=12, cpu_max=path) == budget
