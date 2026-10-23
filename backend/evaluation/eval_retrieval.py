"""`pixi run eval-retrieval`: the keyless retrieval eval that gates CI (#16, #28).

Indexes `knowledge-base/` with the real embedder into a throwaway pgvector (the same pinned
image as the adapter tests, so it needs Docker), retrieves for every Golden Question (a
follow-up with its `standalone_question`), prints the report from `evaluation.retrieval_scoring`
and exits non-zero if a CI bar fails. k and `min_score` come from `Settings`
(`BACKEND_RETRIEVAL_TOP_K`, `BACKEND_RETRIEVAL_MIN_SCORE`), as the server reads them.

Three rankings per question, each `MAX_TOP_K` deep (deeper if top_k is): hybrid as the server
runs it, the dense-only ablation, and hybrid with the query embedded without bge's prefix. The
last needs no second index: Passages are embedded without the prefix either way.
"""

import asyncio
import logging
import sys
import time

import pytest
from pydantic import SecretStr

from app.config import Settings
from app.knowledge_base import KNOWLEDGE_BASE_DIR, load_articles
from app.logs import configure_logging
from app.pgvector_testing import fresh_database, running_pgvector

# Imports Haystack, which must happen before `configure_logging` takes its logger over.
from app.rag.haystack.embedding import fastembed_embedder
from app.rag.haystack.index import PassageIndex
from evaluation.golden import GoldenQuestion, load_golden_questions
from evaluation.retrieval_scoring import (
    MAX_TOP_K,
    QuestionRetrieval,
    failures,
    render_report,
    resolve_expected_sources,
)


async def retrieve_all(questions: list[GoldenQuestion], *, depth: int) -> list[QuestionRetrieval]:
    expected = resolve_expected_sources(questions, load_articles(KNOWLEDGE_BASE_DIR))
    searched = [question.standalone_question or question.question for question in questions]
    with running_pgvector() as server, fresh_database(server) as url:
        database_url = SecretStr(url)
        started = time.perf_counter()
        async with await PassageIndex.open(database_url, top_k=depth) as index:
            report = await index.sync(KNOWLEDGE_BASE_DIR)
            _progress(f"Indexed {len(report.written)} Passages in {_since(started)}.")
            started = time.perf_counter()
            hybrid = [await index.retrieve(text) for text in searched]
            dense_only = [await index.retrieve(text, dense_only=True) for text in searched]
        unprefixed = fastembed_embedder(query_prefix=False)
        async with await PassageIndex.open(database_url, top_k=depth, embedder=unprefixed) as index:
            no_prefix = [await index.retrieve(text) for text in searched]
        _progress(f"Retrieved for {len(questions)} questions, three ways, in {_since(started)}.")
    return [
        QuestionRetrieval(
            question=question,
            expected=expected[question.id],
            hybrid=hybrid[i],
            dense_only=dense_only[i],
            no_prefix=no_prefix[i],
        )
        for i, question in enumerate(questions)
    ]


def main() -> None:
    # The LLM plays no part here, so no key is needed whatever .env says.
    settings = Settings(llm_provider="fake")
    # On stderr, so stdout is the report alone. The first sync logs its progress.
    configure_logging("console", "INFO", stream=sys.stderr)
    logging.getLogger("haystack").setLevel(logging.WARNING)  # one line per pipeline run otherwise
    top_k, min_score = settings.retrieval_top_k, settings.retrieval_min_score
    try:
        retrievals = asyncio.run(retrieve_all(load_golden_questions(), depth=max(top_k, MAX_TOP_K)))
    except pytest.fail.Exception as error:  # running_pgvector found no Docker
        sys.exit(str(error))
    print(render_report(retrievals, top_k=top_k, min_score=min_score))
    if failures(retrievals, top_k=top_k, min_score=min_score):
        sys.exit(1)


def _since(started: float) -> str:
    return f"{time.perf_counter() - started:.0f} s"


def _progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
