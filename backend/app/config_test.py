import os
import re

import pytest
from pydantic import ValidationError

from app.config import MISSING_ANTHROPIC_KEY, Settings, load_settings

MISSING_KEY = re.escape("add ANTHROPIC_API_KEY to .env")
DATABASE_URL = "postgresql://rag:hunter2@db.internal:5432/rag"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate each test from the developer's shell: no key, no BACKEND_* overrides."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    for name in list(os.environ):
        if name.startswith("BACKEND_"):
            monkeypatch.delenv(name)


def load() -> Settings:
    # Never read the repo's .env, so a developer's real key can't leak into a test.
    return Settings(_env_file=None)  # pyright: ignore[reportCallIssue]


def test_anthropic_without_a_key_is_rejected_with_both_fixes() -> None:
    with pytest.raises(ValidationError) as excinfo:
        load()

    message = str(excinfo.value)
    assert "add ANTHROPIC_API_KEY to .env" in message
    assert "BACKEND_LLM_PROVIDER=ollama" in message
    assert "COMPOSE_PROFILES=ollama" in message
    assert ".env.example" in message


def test_an_empty_key_counts_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    # .env.example ships `ANTHROPIC_API_KEY=`, so a copied-but-unfilled .env must still fail.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "  ")

    with pytest.raises(ValidationError, match=MISSING_KEY):
        load()


def test_ollama_needs_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BACKEND_LLM_PROVIDER", "ollama")

    settings = load()

    assert settings.llm_provider == "ollama"
    assert settings.anthropic_api_key is None


def test_the_fake_provider_for_the_smoke_job_needs_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BACKEND_LLM_PROVIDER", "fake")

    settings = load()

    assert settings.llm_provider == "fake"
    assert settings.anthropic_api_key is None


def test_the_key_is_read_from_the_unprefixed_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    settings = load()

    assert settings.anthropic_api_key is not None
    assert settings.anthropic_api_key.get_secret_value() == "sk-ant-test"


def test_a_prefixed_key_is_not_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BACKEND_ANTHROPIC_API_KEY", "sk-ant-test")

    with pytest.raises(ValidationError, match=MISSING_KEY):
        load()


@pytest.mark.parametrize(
    ("provider", "model"), [("anthropic", "claude-opus-5-5"), ("ollama", "qwen3.5:2b")]
)
def test_each_provider_has_its_own_default_model(
    monkeypatch: pytest.MonkeyPatch, provider: str, model: str
) -> None:
    monkeypatch.setenv("BACKEND_LLM_PROVIDER", provider)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    assert load().llm_model == model


def test_the_model_can_be_overridden(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("BACKEND_LLM_MODEL", "claude-haiku-5-5")

    assert load().llm_model == "claude-haiku-5-5"


def test_the_key_never_shows_in_the_settings_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    settings = load()

    assert "sk-ant-test" not in repr(settings)
    assert "sk-ant-test" not in str(settings)
    assert "sk-ant-test" not in settings.model_dump_json()


@pytest.mark.parametrize(
    ("provider", "read_timeout", "turn_deadline"), [("anthropic", 60, 120), ("ollama", 120, 240)]
)
def test_slower_local_models_get_longer_timeouts(
    monkeypatch: pytest.MonkeyPatch, provider: str, read_timeout: float, turn_deadline: float
) -> None:
    monkeypatch.setenv("BACKEND_LLM_PROVIDER", provider)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    settings = load()

    assert settings.llm_connect_timeout_s == 5
    assert settings.llm_read_timeout_s == read_timeout
    assert settings.turn_deadline_s == turn_deadline
    assert settings.rewrite_deadline_s == 30


def test_an_invalid_config_exits_non_zero_with_only_the_fix_message() -> None:
    with pytest.raises(SystemExit) as excinfo:
        load_settings(env_file=None)

    # A str code is printed to stderr and exits with status 1, with no pydantic traceback.
    assert excinfo.value.code == MISSING_ANTHROPIC_KEY


def test_an_unknown_provider_exits_naming_the_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BACKEND_LLM_PROVIDER", "openai")

    with pytest.raises(SystemExit) as excinfo:
        load_settings(env_file=None)

    assert excinfo.value.code == (
        "BACKEND_LLM_PROVIDER: Input should be 'anthropic', 'ollama' or 'fake'"
    )


def test_database_url_comes_from_the_environment_and_is_never_printed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BACKEND_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("BACKEND_DATABASE_URL", DATABASE_URL)

    settings = load()

    assert settings.database_url.get_secret_value() == DATABASE_URL
    assert "hunter2" not in repr(settings)


def test_retrieval_returns_6_passages_unless_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BACKEND_LLM_PROVIDER", "ollama")
    assert load().retrieval_top_k == 6

    monkeypatch.setenv("BACKEND_RETRIEVAL_TOP_K", "8")
    monkeypatch.setenv("BACKEND_RETRIEVAL_MIN_SCORE", "0.62")
    settings = load()

    assert (settings.retrieval_top_k, settings.retrieval_min_score) == (8, 0.62)


def test_retrieval_top_k_must_be_positive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BACKEND_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("BACKEND_RETRIEVAL_TOP_K", "0")

    with pytest.raises(ValidationError, match="retrieval_top_k"):
        load()
