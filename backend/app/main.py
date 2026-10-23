from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.chat.answering import DEMO_SCRIPT, AnsweringService, StubAnsweringService
from app.chat.routes import chat_router
from app.config import Settings, load_settings
from app.errors import install_error_handlers


class HealthResponse(BaseModel):
    status: Literal["ok"]


def create_app(settings: Settings, answering: AnsweringService | None = None) -> FastAPI:
    app = FastAPI(title=settings.app_name)
    install_error_handlers(app)

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
    return create_app(load_settings())
