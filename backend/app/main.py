from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.config import Settings, load_settings


class HealthResponse(BaseModel):
    status: Literal["ok"]


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title=settings.app_name)

    @app.get("/health", operation_id="getHealth")
    def health() -> HealthResponse:
        """Liveness: the process is up and serving requests."""
        return HealthResponse(status="ok")

    return app


def create_app_from_env() -> FastAPI:
    """The server entrypoint: `uvicorn --factory app.main:create_app_from_env`.

    A factory rather than a module-level `app`, so importing this module (tests, the OpenAPI
    export) never reads the environment, and an invalid config exits with its fix message.
    """
    return create_app(load_settings())
