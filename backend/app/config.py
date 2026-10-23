from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# The repo-root .env, for local runs; absent in the Docker image, where Compose injects it.
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BACKEND_", env_file=ENV_FILE, extra="ignore")

    app_name: str = "RAG backend"
