"""A canned, keyless `ChatModel` for the CI Compose smoke job: `BACKEND_LLM_PROVIDER=fake`.

Not a model: it never reads the Passages. It exists so the real stack (image, Knowledge Base
mount, ingestion, the embedder and index, `ChatService`, nginx) can be checked end to end with
no key and no model download. The startup log warns whenever it is active.
"""

import asyncio
from collections.abc import AsyncIterator, Sequence
from typing import Final

from app.answer_assembly import NOT_IN_KNOWLEDGE_BASE
from app.chat_model import LlmHealth, Message

FAKE_REFUSAL_TRIGGER: Final = "[fake-refusal]"
"""A question carrying this gets the Refusal sentinel instead of the canned Answer."""

CANNED_REPLY: Final = (
    "This is the fake LLM provider's canned reply, ",
    "for smoke tests only: ",
    "it cites the top-ranked Passage ",
    "[1].",
)
_REFUSAL: Final = ("NOT_IN_", "KNOWLEDGE_", "BASE")
assert "".join(_REFUSAL) == NOT_IN_KNOWLEDGE_BASE

_FOLLOW_UP: Final = "Follow-up: "
"""Where the rewrite prompt (`app.prompts.rewrite_messages`) puts the Follow-up."""


class FakeChatModel:
    def __init__(self, delay_s: float = 0.15) -> None:
        self._delay_s = delay_s
        """Before every delta but the first, so a proxy that buffers the stream would show."""

    async def stream(self, messages: Sequence[Message]) -> AsyncIterator[str]:
        refuse = FAKE_REFUSAL_TRIGGER in _last_user_text(messages)
        for i, delta in enumerate(_REFUSAL if refuse else CANNED_REPLY):
            if i:
                await asyncio.sleep(self._delay_s)
            yield delta

    async def complete(self, messages: Sequence[Message]) -> str:
        """The Follow-up rewrite: the Follow-up, unchanged."""
        return _last_user_text(messages).rpartition(_FOLLOW_UP)[2]


class FakeLlmProbe:
    async def probe(self) -> LlmHealth:
        return LlmHealth()


def _last_user_text(messages: Sequence[Message]) -> str:
    return next((m.text for m in reversed(messages) if m.role == "user"), "")
