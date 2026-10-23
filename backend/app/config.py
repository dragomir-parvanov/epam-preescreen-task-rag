from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# The repo-root .env, for local runs; absent in the Docker image, where Compose injects it.
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BACKEND_", env_file=ENV_FILE, extra="ignore")

    app_name: str = "RAG backend"
    # The Passage store (ADR-0004). The default is Compose's Postgres as seen from the host, with
    # its fixed local-only credentials. A SecretStr, so a real password is never logged.
    database_url: SecretStr = SecretStr("postgresql://rag:rag@localhost:5432/rag")
