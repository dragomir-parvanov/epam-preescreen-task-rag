import sys
from pathlib import Path
from typing import Literal, NamedTuple, Self

from pydantic import Field, PositiveFloat, SecretStr, ValidationError, model_validator
from pydantic_core import ErrorDetails, PydanticCustomError
from pydantic_settings import BaseSettings, SettingsConfigDict

# The repo-root .env, for local runs; absent in the Docker image, where Compose injects it.
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

LlmProvider = Literal["anthropic", "ollama"]


class ProviderDefaults(NamedTuple):
    model: str
    read_timeout_s: float
    turn_deadline_s: float


# A CPU-bound local model takes 8-15 s to its first token, so Ollama gets twice Claude's budget.
# Every deadline stays under nginx's 300 s proxy_read_timeout.
PROVIDER_DEFAULTS: dict[LlmProvider, ProviderDefaults] = {
    "anthropic": ProviderDefaults("claude-opus-5-5", read_timeout_s=60, turn_deadline_s=120),
    "ollama": ProviderDefaults("qwen3.5:2b", read_timeout_s=120, turn_deadline_s=240),
}

MISSING_ANTHROPIC_KEY = """\
BACKEND_LLM_PROVIDER is anthropic (the default), but ANTHROPIC_API_KEY is not set. Either:
  - add ANTHROPIC_API_KEY to .env (or export it in your shell), or
  - run keyless on a local model: set BACKEND_LLM_PROVIDER=ollama and COMPOSE_PROFILES=ollama
    in .env.
.env.example has both blocks: cp .env.example .env"""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BACKEND_", env_file=ENV_FILE, extra="ignore")

    app_name: str = "RAG backend"
    # The Passage store (ADR-0004). The default is Compose's Postgres as seen from the host, with
    # its fixed local-only credentials. A SecretStr, so a real password is never logged.
    database_url: SecretStr = SecretStr("postgresql://rag:rag@localhost:5432/rag")

    llm_provider: LlmProvider = "anthropic"
    # The per-provider defaults below can read `llm_provider` because it is declared first.
    llm_model: str = Field(default_factory=lambda d: PROVIDER_DEFAULTS[d["llm_provider"]].model)
    # The Compose `ollama` service. A Mac with native Ollama: http://host.docker.internal:11434
    ollama_base_url: str = "http://ollama:11434"
    # Read unprefixed: reviewers already have the key under this name.
    anthropic_api_key: SecretStr | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")

    # LLM timeouts, in seconds. "Read" is the longest gap allowed between two stream chunks.
    llm_connect_timeout_s: PositiveFloat = 5
    llm_read_timeout_s: PositiveFloat = Field(
        default_factory=lambda d: PROVIDER_DEFAULTS[d["llm_provider"]].read_timeout_s
    )
    # Wall-clock budgets: a whole Turn, and the Follow-up rewrite inside it.
    turn_deadline_s: PositiveFloat = Field(
        default_factory=lambda d: PROVIDER_DEFAULTS[d["llm_provider"]].turn_deadline_s
    )
    rewrite_deadline_s: PositiveFloat = 30

    @model_validator(mode="after")
    def _require_key_for_anthropic(self) -> Self:
        key = self.anthropic_api_key
        if self.llm_provider == "anthropic" and (key is None or not key.get_secret_value().strip()):
            raise PydanticCustomError("missing_anthropic_api_key", MISSING_ANTHROPIC_KEY)
        return self


def load_settings(env_file: Path | None = ENV_FILE) -> Settings:
    """Settings from the environment and `env_file`; on an invalid config, exit with the fix.

    The one place startup (the uvicorn factory) and `pixi run check-config` validate the config.
    """
    try:
        # pydantic's dataclass_transform hides BaseSettings' init-only `_env_file` from pyright.
        return Settings(_env_file=env_file)  # pyright: ignore[reportCallIssue]
    except ValidationError as error:
        sys.exit(
            "\n".join(
                _describe(e)
                for e in error.errors()
                # A knock-on of a bad BACKEND_LLM_PROVIDER, which is reported on its own.
                if e["type"] != "default_factory_not_called"
            )
        )


def _describe(error: ErrorDetails) -> str:
    """One readable line per error, naming the env var rather than the field."""
    if not error["loc"]:  # a model-level check, whose message is already the whole story
        return error["msg"]
    name = str(error["loc"][0])
    env_var = name if name.isupper() else f"BACKEND_{name.upper()}"
    return f"{env_var}: {error['msg']}"
