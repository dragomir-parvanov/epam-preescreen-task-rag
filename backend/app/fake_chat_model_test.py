import os
import time
from itertools import pairwise

import pytest

from app.answer_assembly import NOT_IN_KNOWLEDGE_BASE
from app.chat.schemas import HistoryTurn
from app.chat_model import ChatModel, LlmHealth, Message
from app.config import Settings
from app.fake_chat_model import FAKE_REFUSAL_TRIGGER, FakeChatModel
from app.prompts import generation_messages, rewrite_messages
from app.rag.haystack.chat_model import build_chat_model
from app.rag.haystack.llm_probe import build_llm_probe

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(os.environ):
        if name.startswith(("BACKEND_", "ANTHROPIC_")):
            monkeypatch.delenv(name)


def fake_settings() -> Settings:
    return Settings(_env_file=None, llm_provider="fake")  # pyright: ignore[reportCallIssue]


async def deltas(model: ChatModel, messages: list[Message]) -> list[str]:
    return [delta async for delta in model.stream(messages)]


async def test_the_fake_provider_streams_a_canned_reply_citing_the_top_passage() -> None:
    model = build_chat_model(fake_settings())

    reply = await deltas(model, generation_messages("How do I set up SSO?", []))

    assert len(reply) > 1
    assert "".join(reply).rstrip().endswith("[1].")
    assert "fake" in "".join(reply).lower()


async def test_the_deltas_are_spaced_out_so_a_buffering_proxy_would_show() -> None:
    model = FakeChatModel(delay_s=0.05)
    arrivals: list[float] = []

    async for _ in model.stream(generation_messages("How do I set up SSO?", [])):
        arrivals.append(time.monotonic())

    gaps = [later - earlier for earlier, later in pairwise(arrivals)]
    assert gaps
    assert min(gaps) >= 0.04


async def test_a_question_carrying_the_trigger_gets_the_refusal_sentinel() -> None:
    model = FakeChatModel(delay_s=0)
    question = f"How do I set up SSO? {FAKE_REFUSAL_TRIGGER}"

    reply = await deltas(model, generation_messages(question, []))

    assert len(reply) > 1
    assert "".join(reply) == NOT_IN_KNOWLEDGE_BASE


async def test_the_rewrite_returns_the_follow_up_unchanged() -> None:
    model = build_chat_model(fake_settings())
    history = [HistoryTurn(question="How do I set up SSO?", answer="Like this [1].")]

    rewrite = await model.complete(rewrite_messages(history, "and on v2?"))

    assert rewrite == "and on v2?"


async def test_the_fake_provider_is_always_healthy() -> None:
    assert await build_llm_probe(fake_settings()).probe() == LlmHealth()
