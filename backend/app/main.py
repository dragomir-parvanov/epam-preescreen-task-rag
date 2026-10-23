from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.chat.answering import DEMO_SCRIPT, AnsweringService, StubAnsweringService
from app.chat.routes import chat_router
from app.config import Settings, load_settings
from app.errors import install_error_handlers
from app.logs import configure_logging, log_config_loaded
from app.request_id import RequestIdMiddleware


class HealthResponse(BaseModel):
    status: Literal["ok"]


def create_app(settings: Settings, answering: AnsweringService | None = None) -> FastAPI:
    app = FastAPI(title=settings.app_name)
    install_error_handlers(app)
    app.add_middleware(RequestIdMiddleware)

    @app.get("/health", operation_id="getHealth")
    def health() -> HealthResponse:
        """Liveness: the process is up and serving requests."""
        return HealthResponse(status="ok")

    # Until ChatService exists, every Turn plays back the demo script.
    app.include_router(
        chat_router(answering or StubAnsweringService(script=DEMO_SCRIPT, delay=0.2))
    )

    return app


def create_app_from_env() -> FastAPI:
    """The server entrypoint: `uvicorn --factory app.main:create_app_from_env`.

    A factory rather than a module-level `app`, so importing this module (tests, the OpenAPI
    export) never reads the environment, and an invalid config exits with its fix message.
    """
    settings = load_settings()
    configure_logging(settings.log_format, settings.log_level)
    log_config_loaded(settings)
    return create_app(settings)
