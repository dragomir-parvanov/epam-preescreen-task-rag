from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.articles import articles_router
from app.chat.answering import (
    DEMO_SCRIPT,
    INDEX_NOT_READY,
    AnsweringService,
    RequireIndex,
    StubAnsweringService,
)
from app.chat.routes import chat_router
from app.chat.service import ChatService
from app.config import Settings, load_settings
from app.database import PostgresPing
from app.errors import AppError, install_error_handlers
from app.ingestion import IndexStatus, Ingestion, validate_knowledge_base
from app.knowledge_base import KNOWLEDGE_BASE_DIR, Article, load_articles
from app.logs import configure_logging, log_config_loaded
from app.passages import Passage

# Imports Haystack, which must happen before `configure_logging` takes its logger over.
from app.rag.haystack.chat_model import build_chat_model
from app.rag.haystack.index import PassageIndex
from app.rag.haystack.llm_probe import build_llm_probe
from app.readiness import CachedLlmCheck, DatabaseProbe, readiness_router
from app.request_id import RequestIdMiddleware


class HealthResponse(BaseModel):
    status: Literal["ok"]


@dataclass(frozen=True)
class Runtime:
    """What the lifespan starts and stops, and what `/ready` reports on."""

    ingestion: Ingestion[Any]
    """Startup phase 2: syncs the index in the background."""
    database: DatabaseProbe
    llm: CachedLlmCheck


def create_app(
    settings: Settings,
    answering: AnsweringService | None = None,
    articles: Sequence[Article] | None = None,
    runtime: Runtime | None = None,
) -> FastAPI:
    """The app; `articles` defaults to the Knowledge Base in `knowledge-base/`, read once here.

    Without a `runtime` (tests, the OpenAPI export) nothing runs in the background, `/ready`
    reports not ready, and `POST /chat` doesn't wait for an index.
    """

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
        if runtime is None:
            yield
            return
        runtime.ingestion.start()
        runtime.llm.start()
        try:
            yield
        finally:
            # uvicorn has already drained or, after --timeout-graceful-shutdown, cancelled the
            # in-flight Turns: a cancelled Turn takes the Stop path and hangs up on the LLM.
            await runtime.llm.stop()
            await runtime.ingestion.stop()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    install_error_handlers(app)
    app.add_middleware(RequestIdMiddleware)

    @app.get("/health", operation_id="getHealth")
    def health() -> HealthResponse:
        """Liveness: the process is up and serving requests."""
        return HealthResponse(status="ok")

    def index_status() -> IndexStatus:
        return runtime.ingestion.status if runtime else IndexStatus(ok=False, detail=None)

    app.include_router(
        readiness_router(
            runtime.database if runtime else None, index_status, runtime.llm if runtime else None
        )
    )

    # Without an `answering` (tests, the OpenAPI export), every Turn plays back the demo script.
    answering = answering or StubAnsweringService(script=DEMO_SCRIPT, delay=0.2)
    if runtime is not None:
        answering = RequireIndex(answering, lambda: index_status().ok)
    app.include_router(chat_router(answering))
    app.include_router(
        articles_router(load_articles(KNOWLEDGE_BASE_DIR) if articles is None else articles)
    )

    return app


def create_app_from_env() -> FastAPI:
    """The server entrypoint: `uvicorn --factory app.main:create_app_from_env`.

    A factory rather than a module-level `app`, so importing this module (tests, the OpenAPI
    export) never reads the environment, and an invalid config exits with its fix message.

    Startup phase 1 runs here, before anything is served: a malformed Article exits non-zero,
    naming the file. Phase 2, the index sync, runs in the background once the app starts.
    """
    settings = load_settings()
    configure_logging(settings.log_format, settings.log_level)
    log_config_loaded(settings)
    articles = validate_knowledge_base(KNOWLEDGE_BASE_DIR)

    async def open_index() -> PassageIndex:
        return await PassageIndex.open(settings.database_url, top_k=settings.retrieval_top_k)

    ingestion = Ingestion(open_index, KNOWLEDGE_BASE_DIR)
    runtime = Runtime(
        ingestion=ingestion,
        database=PostgresPing(settings.database_url),
        llm=CachedLlmCheck(build_llm_probe(settings)),
    )
    answering = ChatService(
        retriever=SyncedIndex(ingestion),
        chat_model=build_chat_model(settings),
        settings=settings,
    )
    return create_app(settings, answering=answering, articles=articles, runtime=runtime)


@dataclass(frozen=True)
class SyncedIndex:
    """The index as a `PassageRetriever`, once the first sync has opened it. `RequireIndex`
    already turns Turns away before then."""

    ingestion: Ingestion[PassageIndex]

    async def retrieve(self, question: str) -> tuple[Passage, ...]:
        index = self.ingestion.index
        if index is None:
            raise AppError("index_not_ready", INDEX_NOT_READY)
        return await index.retrieve(question)
