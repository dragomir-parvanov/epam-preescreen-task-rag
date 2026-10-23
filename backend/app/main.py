from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.config import Settings


class HealthResponse(BaseModel):
    status: Literal["ok"]


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title=settings.app_name)

    @app.get("/health", operation_id="getHealth")
    def health() -> HealthResponse:
        """Liveness: the process is up and serving requests."""
        return HealthResponse(status="ok")

    return app


app = create_app(Settings())
