"""Sync the Passage index with `knowledge-base/` once: `python -m app.ingest [--rebuild]`.

The same sync the backend runs at startup, under the same advisory lock, so it is safe while a
backend runs. `--rebuild` drops the table first; `pixi run reindex` stops the backend around it,
so nothing reads a half-built table. Unlike startup, it doesn't retry: it fails loudly.
"""

import argparse
import asyncio
from pathlib import Path

from pydantic import SecretStr

from app.config import load_settings
from app.ingestion import validate_knowledge_base
from app.knowledge_base import KNOWLEDGE_BASE_DIR
from app.logs import configure_logging

# Imports Haystack, which must happen before `configure_logging` takes its logger over.
from app.rag.haystack.embedding import Embedder
from app.rag.haystack.index import PassageIndex
from app.rag.haystack.indexing import SyncReport


async def ingest(
    database_url: SecretStr,
    knowledge_base: Path,
    *,
    rebuild: bool,
    embedder: Embedder | None = None,
) -> SyncReport:
    if rebuild:
        await PassageIndex.drop(database_url)
    # top_k only matters for retrieval, which this never does.
    async with await PassageIndex.open(database_url, top_k=1, embedder=embedder) as index:
        return await index.sync(knowledge_base)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.ingest", description=__doc__)
    parser.add_argument(
        "--rebuild", action="store_true", help="drop the Passage table and re-embed everything"
    )
    args = parser.parse_args()
    settings = load_settings()
    configure_logging(settings.log_format, settings.log_level)
    validate_knowledge_base(KNOWLEDGE_BASE_DIR)
    asyncio.run(ingest(settings.database_url, KNOWLEDGE_BASE_DIR, rebuild=args.rebuild))


if __name__ == "__main__":
    main()
