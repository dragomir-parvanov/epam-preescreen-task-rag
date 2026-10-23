"""`ChatModel` over Haystack's native chat generators: Claude or a local Ollama model.

A generator streams through a callback. `HaystackChatModel` runs it in a task of its own whose
callback feeds a queue, and yields from that queue, so the caller gets a plain async stream.
Cancelling the caller cancels that task, and with it the provider's HTTP call.

Each provider gets its own HTTP client, built here rather than by the generator, so it carries
both timeouts from `Settings`: connect, and read (the longest gap between two stream chunks).
`anthropic_client` and `ollama_client` are public so the `llm` readiness probe can reuse them.
"""

import asyncio
from collections.abc import AsyncIterator, Callable, Sequence
from typing import Final, Protocol

import anthropic
import httpx
import httpx2
import ollama
from haystack.dataclasses import ChatMessage, StreamingCallbackT, StreamingChunk

# The integrations ship without py.typed; pyright still infers their types from the source.
from haystack_integrations.components.generators.anthropic import (  # pyright: ignore[reportMissingTypeStubs]
    AnthropicChatGenerator,
)
from haystack_integrations.components.generators.ollama.chat.chat_generator import (  # pyright: ignore[reportMissingTypeStubs]
    OllamaChatGenerator,
)

from app.chat_model import ChatModel, Message
from app.config import Settings
from app.errors import AppError

LLM_AUTH_FAILED: Final = "The language model provider rejected the configured credentials."
LLM_UNAVAILABLE: Final = "The language model is unavailable right now. Please try again."
LLM_TIMEOUT: Final = "The language model took too long to respond. Please try again."


class _Generator(Protocol):
    async def run_async(
        self, messages: list[ChatMessage], *, streaming_callback: StreamingCallbackT | None = None
    ) -> dict[str, list[ChatMessage]]: ...


type ErrorTranslator = Callable[[Exception], AppError | None]
"""A provider failure as the contract's error, or None for one that is our own bug."""

_END: Final = object()


class HaystackChatModel:
    def __init__(self, generator: _Generator, translate_error: ErrorTranslator) -> None:
        self._generator = generator
        self._translate_error = translate_error

    async def stream(self, messages: Sequence[Message]) -> AsyncIterator[str]:
        deltas: asyncio.Queue[str | object] = asyncio.Queue()

        async def on_chunk(chunk: StreamingChunk) -> None:
            if chunk.content:  # thinking and bookkeeping chunks carry no text
                deltas.put_nowait(chunk.content)

        async def generate() -> None:
            try:
                await self._run(messages, streaming_callback=on_chunk)
            finally:
                deltas.put_nowait(_END)

        generation = asyncio.create_task(generate())
        try:
            while (delta := await deltas.get()) is not _END:
                assert isinstance(delta, str)
                yield delta
            await generation  # re-raises what ended the generation early
        finally:
            # Reached early when the caller is cancelled or stops reading: hang up on the provider.
            generation.cancel()
            await asyncio.gather(generation, return_exceptions=True)

    async def complete(self, messages: Sequence[Message]) -> str:
        result = await self._run(messages)
        return result["replies"][0].text or ""

    async def _run(
        self, messages: Sequence[Message], streaming_callback: StreamingCallbackT | None = None
    ) -> dict[str, list[ChatMessage]]:
        try:
            return await self._generator.run_async(
                _to_haystack(messages), streaming_callback=streaming_callback
            )
        except Exception as error:
            if (app_error := self._translate_error(error)) is None:
                raise
            raise app_error from error


def _to_haystack(messages: Sequence[Message]) -> list[ChatMessage]:
    build = {
        "system": ChatMessage.from_system,
        "user": ChatMessage.from_user,
        "assistant": ChatMessage.from_assistant,
    }
    return [build[message.role](message.text) for message in messages]


def build_chat_model(settings: Settings) -> ChatModel:
    """The configured provider's model. `Settings` has already checked the config's shape."""
    match settings.llm_provider:
        case "anthropic":
            return HaystackChatModel(_claude(settings), _claude_error)
        case "ollama":
            return HaystackChatModel(_ollama(settings), _ollama_error)


def anthropic_client(settings: Settings) -> anthropic.AsyncAnthropic:
    key = settings.anthropic_api_key
    assert key is not None  # Settings requires it for the anthropic provider
    return anthropic.AsyncAnthropic(
        api_key=key.get_secret_value(),
        timeout=anthropic.Timeout(
            settings.llm_read_timeout_s, connect=settings.llm_connect_timeout_s
        ),
        # The SDK retries 429, 5xx and 529 only until the stream starts; never mid-stream.
        max_retries=2,
    )


def _claude(settings: Settings) -> AnthropicChatGenerator:
    # Thinking can't be turned off on the default model (Opus 5.5), so effort is the latency
    # control. No temperature, top_p or top_k: API version 2026-10-21 rejects them.
    generator = AnthropicChatGenerator(
        model=settings.llm_model, generation_kwargs={"output_config": {"effort": "low"}}
    )
    generator.async_client = anthropic_client(settings)
    return generator


def _claude_error(error: Exception) -> AppError | None:
    match error:
        case anthropic.AuthenticationError() | anthropic.PermissionDeniedError():
            return AppError("llm_auth_failed", LLM_AUTH_FAILED)
        # A stall before the stream starts is the SDK's; one mid-stream is raw httpx2.
        case anthropic.APITimeoutError() | httpx2.TimeoutException():
            return AppError("llm_timeout", LLM_TIMEOUT)
        case anthropic.BadRequestError() | anthropic.UnprocessableEntityError():
            return None  # a request we built wrong
        # Includes an `error` event mid-stream, such as overloaded_error.
        case anthropic.APIError() | httpx2.TransportError():
            return AppError("llm_unavailable", LLM_UNAVAILABLE)
        case _:
            return None


def ollama_client(settings: Settings) -> ollama.AsyncClient:
    return ollama.AsyncClient(
        host=settings.ollama_base_url,
        timeout=httpx.Timeout(settings.llm_read_timeout_s, connect=settings.llm_connect_timeout_s),
    )


def _ollama(settings: Settings) -> OllamaChatGenerator:
    # qwen3.5 would otherwise write <think> blocks into the reply text. No retries for Ollama.
    # Temperature 0, as Prompt design (#19) asks; only Claude's API rejects sampling parameters.
    generator = OllamaChatGenerator(
        model=settings.llm_model,
        url=settings.ollama_base_url,
        think=False,
        max_retries=0,
        generation_kwargs={"temperature": 0},
    )
    # The generator's own `timeout` is one number for connect and read alike, so swap in ours.
    generator._async_client = ollama_client(settings)  # pyright: ignore[reportPrivateUsage]
    return generator


def _ollama_error(error: Exception) -> AppError | None:
    match error:
        case ollama.ResponseError(status_code=401 | 403):
            return AppError("llm_auth_failed", LLM_AUTH_FAILED)
        case httpx.TimeoutException():
            return AppError("llm_timeout", LLM_TIMEOUT)
        # A model that isn't pulled is a 404; the client raises ConnectionError when it can't
        # connect at all.
        case ollama.ResponseError() | ConnectionError() | httpx.TransportError():
            return AppError("llm_unavailable", LLM_UNAVAILABLE)
        case _:
            return None
