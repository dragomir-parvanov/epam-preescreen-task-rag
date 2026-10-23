"""The ChatModel port: how `ChatService` talks to an LLM, without knowing which one (ADR-0003).

The Haystack adapter in `app.rag.haystack` implements it for each provider; tests pass
hand-written fakes.
"""

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

type Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True, slots=True)
class Message:
    role: Role
    text: str


class ChatModel(Protocol):
    """One configured provider and model.

    Provider failures surface as `AppError`s with the contract's codes: `llm_auth_failed`,
    `llm_unavailable` or `llm_timeout`. Cancelling the task that awaits either method cancels
    the HTTP call underneath, which is how Stop reaches the provider (ADR-0002).
    """

    def stream(self, messages: Sequence[Message]) -> AsyncIterator[str]:
        """The reply's text, as deltas in the order the model writes them."""
        ...

    async def complete(self, messages: Sequence[Message]) -> str:
        """The whole reply at once. The Follow-up rewrite uses it."""
        ...


type LlmProblem = Literal["auth_failed", "unavailable", "model_missing"]


@dataclass(frozen=True, slots=True, kw_only=True)
class LlmHealth:
    """What the readiness `llm` check reports. No `problem` means the model can be used."""

    problem: LlmProblem | None = None
    command: str | None = None
    """The command that fixes the problem, when there is one: `ollama pull <model>`."""


class LlmProbe(Protocol):
    """A sibling of `ChatModel`: can the configured provider and model be used right now?"""

    async def probe(self) -> LlmHealth:
        """Asks the provider without generating any tokens. Never raises for a provider failure."""
        ...
