import os

import pytest

from app.chat_model import LlmHealth
from app.config import Settings
from app.rag.haystack.fake_llm_server import (
    anthropic_error,
    anthropic_model,
    fake_llm_server,
    ollama_error,
    ollama_show,
)
from app.rag.haystack.llm_probe import build_llm_probe

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """No real key, base URL or BACKEND_* override from the developer's shell reaches a test."""
    for name in list(os.environ):
        if name.startswith(("BACKEND_", "ANTHROPIC_", "OLLAMA_")):
            monkeypatch.delenv(name)


def claude(url: str, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("ANTHROPIC_BASE_URL", url)
    return Settings(_env_file=None, ANTHROPIC_API_KEY="sk-test")  # pyright: ignore[reportCallIssue]


def ollama(url: str) -> Settings:
    return Settings(_env_file=None, llm_provider="ollama", ollama_base_url=url)  # pyright: ignore[reportCallIssue]


async def test_claude_is_healthy_when_the_configured_model_can_be_looked_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with fake_llm_server(anthropic_model("claude-opus-5-5")) as server:
        health = await build_llm_probe(claude(server.url, monkeypatch)).probe()

    assert health == LlmHealth()
    # Looking the model up generates no tokens.
    assert [(r.method, r.path) for r in server.requests] == [("GET", "/v1/models/claude-opus-5-5")]


async def test_a_rejected_claude_key_is_auth_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    async with fake_llm_server(anthropic_error(401, "authentication_error")) as server:
        health = await build_llm_probe(claude(server.url, monkeypatch)).probe()

    assert health == LlmHealth(problem="auth_failed")


async def test_an_unknown_claude_model_is_model_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    async with fake_llm_server(anthropic_error(404, "not_found_error")) as server:
        health = await build_llm_probe(claude(server.url, monkeypatch)).probe()

    assert health == LlmHealth(problem="model_missing")


async def test_an_overloaded_claude_is_unavailable_without_retrying(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with fake_llm_server(anthropic_error(529, "overloaded_error")) as server:
        health = await build_llm_probe(claude(server.url, monkeypatch)).probe()

    assert health == LlmHealth(problem="unavailable")
    assert len(server.requests) == 1


async def test_ollama_is_healthy_when_the_model_is_pulled() -> None:
    async with fake_llm_server(ollama_show()) as server:
        health = await build_llm_probe(ollama(server.url)).probe()

    assert health == LlmHealth()
    assert [(r.method, r.path, r.body) for r in server.requests] == [
        ("POST", "/api/show", {"model": "qwen3.5:2b"})
    ]


async def test_an_ollama_model_that_is_not_pulled_is_model_missing_with_the_pull_command() -> None:
    async with fake_llm_server(ollama_error(404, 'model "qwen3.5:2b" not found')) as server:
        health = await build_llm_probe(ollama(server.url)).probe()

    assert health == LlmHealth(problem="model_missing", command="ollama pull qwen3.5:2b")


async def test_an_unreachable_ollama_is_unavailable() -> None:
    async with fake_llm_server() as server:
        url = server.url  # nothing listens here once the server has shut down

    assert await build_llm_probe(ollama(url)).probe() == LlmHealth(problem="unavailable")
