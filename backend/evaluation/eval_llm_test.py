import asyncio
from collections.abc import AsyncIterator, Sequence
from typing import Any

import pytest

from app.chat.service import ChatService
from app.chat.service_test import FakeChatModel, FakeRetriever, settings
from app.chat_model import Message, TokenUsage
from evaluation.eval_llm import UsageMeter, run_questions, select_questions
from evaluation.golden import GoldenQuestion
from evaluation.retrieval_scoring import ExpectedSections, SectionKey

pytestmark = pytest.mark.anyio

# The Passages FakeRetriever returns by default: Sections section-1 and section-2 of sso-setup.
SECTION_1 = SectionKey("sso-setup", "section-1")
SECTION_9 = SectionKey("sso-setup", "section-9")


def golden(id: str, **fields: Any) -> GoldenQuestion:
    data: dict[str, Any] = {
        "id": id,
        "question": f"Question {id}?",
        "category": "single-article",
        "answerable": True,
        "origin": "curated",
        "expected_sources": [{"article": "sso-setup", "section": "Section 1"}],
        "must_mention": [["certificate"]],
    }
    return GoldenQuestion.model_validate(data | fields)


def follow_up(id: str) -> GoldenQuestion:
    return golden(
        id,
        category="follow-up",
        history=[{"question": "What is AUTH-403?", "answer": "An expired certificate [1]."}],
        standalone_question="What is AUTH-403 on v2?",
        standalone_must_mention=[["v2"]],
    )


def chat_service(model: Any, retriever: FakeRetriever | None = None) -> ChatService:
    return ChatService(
        retriever=retriever or FakeRetriever(), chat_model=model, settings=settings()
    )


async def test_a_golden_question_is_answered_by_chat_service_and_scored() -> None:
    model = FakeChatModel(deltas=["Renew the IdP ", "certificate [1]."])
    expected: dict[str, ExpectedSections] = {"gq-a": ((SECTION_1,),)}

    [score] = await run_questions([golden("gq-a")], chat_service(model), expected, UsageMeter())

    assert (score.outcome, score.outcome_correct) == ("answer", True)
    assert score.text == "Renew the IdP certificate [1]."
    assert (score.citation_recall, score.retrieval_recall) == (1.0, 1.0)
    assert (score.mentions_hit, score.mentions_total) == (1, 1)
    assert score.ttft_ms is not None and score.latency_ms >= score.ttft_ms


async def test_a_follow_up_sends_its_history_and_is_searched_with_its_rewrite() -> None:
    retriever = FakeRetriever()
    model = FakeChatModel(deltas=["On v2, renew the certificate [1]."], rewrite="AUTH-403 on v2?")

    [score] = await run_questions(
        [follow_up("gq-f")], chat_service(model, retriever), {"gq-f": ((SECTION_1,),)}, UsageMeter()
    )

    assert "Assistant: An expired certificate" in model.completed[0][-1].text
    assert retriever.questions == ["AUTH-403 on v2?"]
    assert score.standalone_question == "AUTH-403 on v2?"
    assert (score.standalone_hit, score.standalone_total) == (1, 1)


async def test_a_failed_turn_is_scored_as_an_error_and_the_run_goes_on() -> None:
    model = FakeChatModel(deltas=["Renew the certificate [1]."], rewrite="")  # an unusable rewrite
    expected: dict[str, ExpectedSections] = {"gq-f": ((SECTION_1,),), "gq-a": ((SECTION_1,),)}

    scores = await run_questions(
        [follow_up("gq-f"), golden("gq-a")], chat_service(model), expected, UsageMeter()
    )

    assert [(s.id, s.outcome, s.error) for s in scores] == [
        ("gq-f", "error", "rewrite_failed"),
        ("gq-a", "answer", None),
    ]


async def test_a_refusal_shows_what_retrieval_found() -> None:
    model = FakeChatModel(deltas=["NOT_IN_KNOWLEDGE_BASE"])

    [score] = await run_questions(
        [golden("gq-a")], chat_service(model), {"gq-a": ((SECTION_9,),)}, UsageMeter()
    )

    assert (score.outcome, score.blame, score.retrieval_recall) == ("refusal", "retrieval", 0.0)


class MeteredModel:
    """Reports its own usage, a different amount per question, after a pause so that
    concurrent Turns interleave."""

    def __init__(self, meter: UsageMeter) -> None:
        self._meter = meter

    def stream(self, messages: Sequence[Message]) -> AsyncIterator[str]:
        return self._stream(messages)

    async def _stream(self, messages: Sequence[Message]) -> AsyncIterator[str]:
        tokens = 100 if "gq-slow" in messages[-1].text else 1
        await asyncio.sleep(0.05 if tokens == 100 else 0)
        self._meter.on_usage(TokenUsage(input_tokens=tokens, output_tokens=tokens))
        yield "Renew the certificate [1]."

    async def complete(self, messages: Sequence[Message]) -> str:
        return ""


async def test_each_question_is_charged_its_own_usage_when_questions_run_concurrently() -> None:
    meter = UsageMeter()
    questions = [golden("gq-slow"), golden("gq-fast")]
    expected: dict[str, ExpectedSections] = {q.id: ((SECTION_1,),) for q in questions}

    scores = await run_questions(
        questions, chat_service(MeteredModel(meter)), expected, meter, concurrency=2
    )

    assert [(s.id, s.usage.input_tokens) for s in scores] == [("gq-slow", 100), ("gq-fast", 1)]


def test_the_default_question_set_is_the_curated_one() -> None:
    curated, generated = golden("gq-c"), golden("gq-g", origin="generated")

    assert select_questions([curated, generated]) == ([curated], "curated")
    assert select_questions([curated, generated], everything=True) == (
        [curated, generated],
        "all",
    )
    assert select_questions([curated, generated], only=["gq-g"]) == ([generated], "selected")


def test_selecting_an_unknown_question_id_fails() -> None:
    with pytest.raises(ValueError, match="gq-nope"):
        select_questions([golden("gq-c")], only=["gq-nope"])
