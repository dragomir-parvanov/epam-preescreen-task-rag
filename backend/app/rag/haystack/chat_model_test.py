import asyncio
import os
from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.chat_model import ChatModel, Message
from app.config import Settings
from app.errors import AppError
from app.rag.haystack.chat_model import build_chat_model
from app.rag.haystack.fake_llm_server import (
    FakeLlmServer,
    anthropic_error,
    anthropic_message,
    anthropic_stream,
    anthropic_stream_error,
    fake_llm_server,
    ollama_error,
    ollama_message,
    ollama_stream,
)

pytestmark = pytest.mark.anyio

MESSAGES = [Message("system", "Answer from the Passages."), Message("user", "What is AUTH-403?")]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """No real key, base URL or BACKEND_* override from the developer's shell reaches a test."""
    for name in list(os.environ):
        if name.startswith(("BACKEND_", "ANTHROPIC_", "OLLAMA_")):
            monkeypatch.delenv(name)


def anthropic_settings(
    server: FakeLlmServer, monkeypatch: pytest.MonkeyPatch, **overrides: Any
) -> Settings:
    # The SDK reads its base URL from the environment; production never sets it.
    monkeypatch.setenv("ANTHROPIC_BASE_URL", server.url)
    return Settings(_env_file=None, ANTHROPIC_API_KEY="sk-test", **overrides)  # pyright: ignore[reportCallIssue]


def ollama_settings(url: str, **overrides: Any) -> Settings:
    return Settings(
        _env_file=None,  # pyright: ignore[reportCallIssue]
        llm_provider="ollama",
        ollama_base_url=url,
        **overrides,
    )


async def stop_mid_stream(model: ChatModel, server: FakeLlmServer) -> None:
    """Start streaming, cancel the consuming task after the first delta, as Stop does."""
    first_delta = asyncio.Event()

    async def consume() -> None:
        async for _ in model.stream(MESSAGES):
            first_delta.set()

    turn = asyncio.create_task(consume())
    await asyncio.wait_for(first_delta.wait(), timeout=5)
    turn.cancel()
    with pytest.raises(asyncio.CancelledError):
        await turn
    await asyncio.wait_for(server.hung_up.wait(), timeout=5)


async def collect(deltas: AsyncIterator[str]) -> list[str]:
    return [delta async for delta in deltas]


async def test_claude_streams_the_reply_as_text_deltas(monkeypatch: pytest.MonkeyPatch) -> None:
    async with fake_llm_server(
        anthropic_stream("AUTH-403 means ", "the certificate expired [1].")
    ) as server:
        model: ChatModel = build_chat_model(anthropic_settings(server, monkeypatch))

        deltas = await collect(model.stream(MESSAGES))

    assert deltas == ["AUTH-403 means ", "the certificate expired [1]."]


async def test_stopping_a_claude_stream_closes_the_http_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with fake_llm_server(anthropic_stream("AUTH-403 means ", hold_open=True)) as server:
        model = build_chat_model(anthropic_settings(server, monkeypatch))

        await stop_mid_stream(model, server)

    assert server.hung_up.is_set()


async def test_claude_runs_the_default_model_at_low_effort_with_no_sampling_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with fake_llm_server(anthropic_stream("ok")) as server:
        model = build_chat_model(anthropic_settings(server, monkeypatch))
        await collect(model.stream(MESSAGES))

    [request] = server.requests
    assert (request.method, request.path) == ("POST", "/v1/messages")
    assert request.body["model"] == "claude-opus-5-5"
    assert request.body["output_config"] == {"effort": "low"}
    assert request.body["stream"] is True
    # API version 2026-10-21 rejects every one of these with a 400.
    assert not {"temperature", "top_p", "top_k"} & request.body.keys()
    assert request.body["system"] == [{"type": "text", "text": "Answer from the Passages."}]
    assert request.body["messages"] == [
        {"role": "user", "content": [{"type": "text", "text": "What is AUTH-403?"}]}
    ]


async def test_claude_model_can_be_overridden(monkeypatch: pytest.MonkeyPatch) -> None:
    async with fake_llm_server(anthropic_stream("ok")) as server:
        settings = anthropic_settings(server, monkeypatch, llm_model="claude-haiku-5-5")
        await collect(build_chat_model(settings).stream(MESSAGES))

    assert server.requests[0].body["model"] == "claude-haiku-5-5"


async def test_ollama_streams_the_reply_from_the_default_model_without_thinking() -> None:
    async with fake_llm_server(
        ollama_stream("AUTH-403 means ", "the certificate expired [1].")
    ) as server:
        deltas = await collect(build_chat_model(ollama_settings(server.url)).stream(MESSAGES))

    assert deltas == ["AUTH-403 means ", "the certificate expired [1]."]
    [request] = server.requests
    assert (request.method, request.path) == ("POST", "/api/chat")
    assert request.body["model"] == "qwen3.5:2b"
    # qwen3.5's <think> blocks would leak into the tokens and hide the Refusal sentinel.
    assert request.body["think"] is False
    assert request.body["stream"] is True
    assert request.body["messages"] == [
        {"role": "system", "content": "Answer from the Passages."},
        {"role": "user", "content": "What is AUTH-403?"},
    ]


async def test_stopping_an_ollama_stream_closes_the_http_connection() -> None:
    async with fake_llm_server(ollama_stream("AUTH-403 means ", hold_open=True)) as server:
        model = build_chat_model(ollama_settings(server.url))

        await stop_mid_stream(model, server)

    assert server.hung_up.is_set()


async def test_claude_completes_the_whole_reply_in_one_unstreamed_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with fake_llm_server(anthropic_message("How do I fix AUTH-403 on v2?")) as server:
        reply = await build_chat_model(anthropic_settings(server, monkeypatch)).complete(MESSAGES)

    assert reply == "How do I fix AUTH-403 on v2?"
    assert server.requests[0].body.get("stream") in (None, False)


async def test_ollama_completes_the_whole_reply_in_one_unstreamed_call() -> None:
    async with fake_llm_server(ollama_message("How do I fix AUTH-403 on v2?")) as server:
        reply = await build_chat_model(ollama_settings(server.url)).complete(MESSAGES)

    assert reply == "How do I fix AUTH-403 on v2?"
    assert server.requests[0].body["stream"] is False


async def test_ollama_runs_both_calls_at_temperature_zero() -> None:
    async with fake_llm_server(ollama_stream("AUTH-403."), ollama_message("Q?")) as server:
        model = build_chat_model(ollama_settings(server.url))
        await collect(model.stream(MESSAGES))
        await model.complete(MESSAGES)

    # Prompt design (#19): the same Passages should give the same Answer, and evals repeatable.
    assert [request.body["options"]["temperature"] for request in server.requests] == [0, 0]


# --- Failures map to the contract's error codes ---------------------------------------------


async def test_a_rejected_claude_key_is_llm_auth_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    async with fake_llm_server(anthropic_error(401, "authentication_error")) as server:
        model = build_chat_model(anthropic_settings(server, monkeypatch))

        with pytest.raises(AppError) as streamed:
            await collect(model.stream(MESSAGES))
        with pytest.raises(AppError) as completed:
            await model.complete(MESSAGES)

    assert streamed.value.code == completed.value.code == "llm_auth_failed"
    assert len(server.requests) == 2  # an auth failure is never retried


async def test_claude_overloaded_mid_stream_is_llm_unavailable_and_not_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with fake_llm_server(anthropic_stream_error("overloaded_error", "AUTH-403 ")) as server:
        model = build_chat_model(anthropic_settings(server, monkeypatch))
        deltas: list[str] = []

        with pytest.raises(AppError) as excinfo:
            async for delta in model.stream(MESSAGES):
                deltas.append(delta)

    assert excinfo.value.code == "llm_unavailable"
    assert deltas == ["AUTH-403 "]
    assert len(server.requests) == 1


async def test_a_claude_stream_that_stalls_past_the_read_timeout_is_llm_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with fake_llm_server(anthropic_stream("AUTH-403 ", hold_open=True)) as server:
        settings = anthropic_settings(server, monkeypatch, llm_read_timeout_s=0.2)

        with pytest.raises(AppError) as excinfo:
            await collect(build_chat_model(settings).stream(MESSAGES))

    assert excinfo.value.code == "llm_timeout"


async def test_an_ollama_stream_that_stalls_past_the_read_timeout_is_llm_timeout() -> None:
    async with fake_llm_server(ollama_stream("AUTH-403 ", hold_open=True)) as server:
        settings = ollama_settings(server.url, llm_read_timeout_s=0.2)

        with pytest.raises(AppError) as excinfo:
            await collect(build_chat_model(settings).stream(MESSAGES))

    assert excinfo.value.code == "llm_timeout"


async def test_an_ollama_model_that_is_not_pulled_is_llm_unavailable() -> None:
    async with fake_llm_server(ollama_error(404, 'model "qwen3.5:2b" not found')) as server:
        model = build_chat_model(ollama_settings(server.url))

        with pytest.raises(AppError) as streamed:
            await collect(model.stream(MESSAGES))
        with pytest.raises(AppError) as completed:
            await model.complete(MESSAGES)

    assert streamed.value.code == completed.value.code == "llm_unavailable"


async def test_an_unreachable_ollama_is_llm_unavailable_without_retrying() -> None:
    async with fake_llm_server() as server:
        url = server.url  # nothing listens here once the server has shut down
    with pytest.raises(AppError) as excinfo:
        await collect(build_chat_model(ollama_settings(url)).stream(MESSAGES))

    assert excinfo.value.code == "llm_unavailable"
