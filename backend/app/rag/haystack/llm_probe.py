"""`LlmProbe` for each provider: a cheap request that generates no tokens.

Claude: `GET /v1/models/{model}`. Ollama: `POST /api/show`, which also tells a model that hasn't
been pulled from one that has. Both reuse the `ChatModel`'s clients, with their timeouts, and
never retry: the readiness check asks again soon enough.
"""

import anthropic
import httpx
import ollama

from app.chat_model import LlmHealth, LlmProbe
from app.config import Settings
from app.rag.haystack.chat_model import anthropic_client, ollama_client


def build_llm_probe(settings: Settings) -> LlmProbe:
    match settings.llm_provider:
        case "anthropic":
            return _ClaudeProbe(settings)
        case "ollama":
            return _OllamaProbe(settings)


class _ClaudeProbe:
    def __init__(self, settings: Settings) -> None:
        self._client = anthropic_client(settings).with_options(max_retries=0)
        self._model = settings.llm_model

    async def probe(self) -> LlmHealth:
        try:
            await self._client.models.retrieve(self._model)
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError):
            return LlmHealth(problem="auth_failed")
        except anthropic.NotFoundError:
            return LlmHealth(problem="model_missing")
        except anthropic.APIError:
            return LlmHealth(problem="unavailable")
        return LlmHealth()


class _OllamaProbe:
    def __init__(self, settings: Settings) -> None:
        self._client = ollama_client(settings)
        self._model = settings.llm_model

    async def probe(self) -> LlmHealth:
        try:
            await self._client.show(self._model)
        except ollama.ResponseError as error:
            if error.status_code in (401, 403):
                return LlmHealth(problem="auth_failed")
            if error.status_code == 404:
                return LlmHealth(problem="model_missing", command=f"ollama pull {self._model}")
            return LlmHealth(problem="unavailable")
        # The client raises ConnectionError when it can't connect at all.
        except (ConnectionError, httpx.HTTPError):
            return LlmHealth(problem="unavailable")
        return LlmHealth()
