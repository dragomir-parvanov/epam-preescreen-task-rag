import json
from collections.abc import Sequence
from typing import Any

import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient

from app.chat.answering import StubAnsweringService, TurnEvent
from app.chat.schemas import (
    Answer,
    ArticleRef,
    ChatResult,
    Citation,
    DoneEvent,
    Passage,
    PassagesEvent,
    Refusal,
    RewrittenEvent,
    SectionRef,
    TokenEvent,
    UncitedAnswer,
)
from app.config import Settings
from app.errors import AppError
from app.main import create_app

PASSAGE = Passage(
    id="sso-setup#0",
    article=ArticleRef(id="sso-setup", title="Setting up SSO"),
    section=SectionRef(id="troubleshooting-error-auth-403", path=["Troubleshooting", "AUTH-403"]),
    text="AUTH-403 means the IdP certificate has expired.",
    applies_to=["v3"],
    status="current",
    score=0.82,
)

PASSAGE_JSON = {
    "id": "sso-setup#0",
    "article": {"id": "sso-setup", "title": "Setting up SSO"},
    "section": {"id": "troubleshooting-error-auth-403", "path": ["Troubleshooting", "AUTH-403"]},
    "text": "AUTH-403 means the IdP certificate has expired.",
    "applies_to": ["v3"],
    "status": "current",
    "score": 0.82,
}

ANSWER = Answer(
    text="The IdP certificate has expired [1].",
    citations=[Citation(n=1, passage=PASSAGE)],
    retrieved_passages=[PASSAGE],
    standalone_question=None,
)


def client_over(
    script: Sequence[TurnEvent | Exception], start_error: Exception | None = None
) -> TestClient:
    answering = StubAnsweringService(script=script, start_error=start_error)
    app = create_app(Settings.model_construct(), answering=answering)
    # Unexpected exceptions must come back as responses, as a real client would see them.
    return TestClient(app, raise_server_exceptions=False)


def frames(response: httpx.Response) -> list[tuple[str, dict[str, Any]]]:
    """Split an SSE body into (event name, parsed data) pairs, ignoring keepalive comments."""
    parsed: list[tuple[str, dict[str, Any]]] = []
    for block in response.text.split("\n\n"):
        lines = [line for line in block.splitlines() if not line.startswith(":")]
        if not lines:
            continue
        assert len(lines) == 2, f"expected an event line and a data line, got {lines!r}"
        event_line, data_line = lines
        assert event_line.startswith("event: ")
        assert data_line.startswith("data: ")
        parsed.append((event_line.removeprefix("event: "), json.loads(data_line[len("data: ") :])))
    return parsed


def ask(client: TestClient, body: dict[str, Any]) -> httpx.Response:
    return client.post("/chat", json=body)


def test_chat_streams_the_turn_events_in_order_as_named_sse_frames() -> None:
    client = client_over(
        [
            RewrittenEvent(standalone_question="How do I fix AUTH-403 on v3?"),
            PassagesEvent(passages=[PASSAGE]),
            TokenEvent(text="The IdP certificate "),
            TokenEvent(text="has expired [1]."),
            DoneEvent(result=ANSWER),
        ]
    )

    response = ask(client, {"question": "and on v3?", "history": []})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-accel-buffering"] == "no"
    events = frames(response)
    assert [name for name, _ in events] == ["rewritten", "passages", "token", "token", "done"]
    assert all(data["type"] == name for name, data in events)
    assert events[0][1] == {
        "type": "rewritten",
        "standalone_question": "How do I fix AUTH-403 on v3?",
    }
    assert events[1][1] == {"type": "passages", "passages": [PASSAGE_JSON]}
    assert events[2][1] == {"type": "token", "text": "The IdP certificate "}


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        (
            ANSWER,
            {
                "type": "answer",
                "text": "The IdP certificate has expired [1].",
                "citations": [{"n": 1, "passage": PASSAGE_JSON}],
                "retrieved_passages": [PASSAGE_JSON],
                "standalone_question": None,
            },
        ),
        (
            UncitedAnswer(
                text="Probably the certificate.",
                retrieved_passages=[PASSAGE],
                standalone_question="How do I fix AUTH-403?",
            ),
            {
                "type": "uncited_answer",
                "text": "Probably the certificate.",
                "retrieved_passages": [PASSAGE_JSON],
                "standalone_question": "How do I fix AUTH-403?",
            },
        ),
        (
            Refusal(
                message="The Knowledge Base doesn't cover this.",
                reason="no_relevant_passages",
                retrieved_passages=[],
                standalone_question=None,
            ),
            {
                "type": "refusal",
                "message": "The Knowledge Base doesn't cover this.",
                "reason": "no_relevant_passages",
                "retrieved_passages": [],
                "standalone_question": None,
            },
        ),
    ],
    ids=["answer", "uncited_answer", "refusal"],
)
def test_done_carries_the_whole_result(result: ChatResult, expected: dict[str, Any]) -> None:
    client = client_over([PassagesEvent(passages=[PASSAGE]), DoneEvent(result=result)])

    events = frames(ask(client, {"question": "How do I fix AUTH-403?"}))

    assert events[-1] == ("done", {"type": "done", "result": expected})


@pytest.mark.parametrize(
    ("body", "bad_field"),
    [
        ({"question": "   \n\t"}, ["body", "question"]),
        ({"question": "x" * 2_001}, ["body", "question"]),
        (
            {"question": "ok?", "history": [{"question": "q", "answer": "a"}] * 21},
            ["body", "history"],
        ),
        (
            {"question": "ok?", "history": [{"question": "q", "answer": "a" * 20_001}]},
            ["body", "history", 0, "answer"],
        ),
    ],
    ids=["blank_question", "over_long_question", "too_much_history", "over_long_history_answer"],
)
def test_an_invalid_request_gets_a_422_envelope_naming_the_field(
    body: dict[str, Any], bad_field: list[str | int]
) -> None:
    client = client_over([DoneEvent(result=ANSWER)])

    response = ask(client, body)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["message"]
    assert [detail["loc"] for detail in error["details"]] == [bad_field]


def test_a_failure_before_the_stream_starts_gets_a_real_status_instead_of_a_stream() -> None:
    client = client_over(
        [DoneEvent(result=ANSWER)],
        start_error=AppError("llm_not_configured", "Set ANTHROPIC_API_KEY or use Ollama."),
    )

    response = ask(client, {"question": "How do I fix AUTH-403?"})

    assert response.status_code == 503
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {
        "error": {
            "code": "llm_not_configured",
            "message": "Set ANTHROPIC_API_KEY or use Ollama.",
            "details": None,
        }
    }


def test_a_failure_after_the_stream_starts_ends_it_with_an_error_event() -> None:
    client = client_over(
        [
            PassagesEvent(passages=[PASSAGE]),
            TokenEvent(text="The IdP "),
            AppError("llm_timeout", "The language model took too long to answer."),
            TokenEvent(text="never sent"),
        ]
    )

    response = ask(client, {"question": "How do I fix AUTH-403?"})

    assert response.status_code == 200
    events = frames(response)
    assert [name for name, _ in events] == ["passages", "token", "error"]
    assert events[-1][1] == {
        "type": "error",
        "error": {
            "code": "llm_timeout",
            "message": "The language model took too long to answer.",
            "details": None,
        },
    }


SECRET = "password=hunter2 at db:5432"


def test_an_unexpected_failure_before_the_stream_is_a_generic_500() -> None:
    client = client_over([DoneEvent(result=ANSWER)], start_error=RuntimeError(SECRET))

    response = ask(client, {"question": "How do I fix AUTH-403?"})

    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "internal_error"
    assert "hunter2" not in response.text


def test_an_unexpected_failure_mid_stream_is_a_generic_error_event() -> None:
    client = client_over([PassagesEvent(passages=[PASSAGE]), RuntimeError(SECRET)])

    response = ask(client, {"question": "How do I fix AUTH-403?"})

    assert response.status_code == 200
    events = frames(response)
    assert [name for name, _ in events] == ["passages", "error"]
    assert events[-1][1]["error"]["code"] == "internal_error"
    assert "hunter2" not in response.text


def test_openapi_documents_the_stream_as_the_event_union_and_errors_as_the_envelope() -> None:
    openapi = create_app(Settings.model_construct()).openapi()

    responses = openapi["paths"]["/chat"]["post"]["responses"]
    data = responses["200"]["content"]["text/event-stream"]["itemSchema"]["properties"]["data"]
    assert data["contentSchema"] == {"$ref": "#/components/schemas/ChatStreamEvent"}
    event_union = openapi["components"]["schemas"]["ChatStreamEvent"]
    assert event_union["discriminator"]["propertyName"] == "type"
    assert set(event_union["discriminator"]["mapping"]) == {
        "rewritten",
        "passages",
        "token",
        "done",
        "error",
    }
    # Only what can fail before the first byte; later failures arrive as `error` events.
    for status in ["422", "503", "500"]:
        assert list(responses[status]["content"]) == ["application/json"], status
        schema = responses[status]["content"]["application/json"]["schema"]
        assert schema["required"] == ["error"]
        assert schema["properties"]["error"] == {"$ref": "#/components/schemas/ErrorBody"}
    assert "ErrorBody" in openapi["components"]["schemas"]
