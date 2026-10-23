import io
import json
import logging
from collections.abc import Callable
from typing import Any

import structlog
from pydantic import SecretStr

from app.chat.schemas import (
    Answer,
    ArticleRef,
    ChatResult,
    Citation,
    Passage,
    Refusal,
    SectionRef,
)
from app.config import Settings
from app.errors import ErrorCode
from app.logs import TurnTimings, configure_logging, log_config_loaded, log_turn_completed

type LogLines = Callable[[], list[dict[str, Any]]]


def test_json_lines_carry_the_bound_context_for_our_loggers_and_stdlib_ones(
    captured_logs: LogLines,
) -> None:
    with structlog.contextvars.bound_contextvars(request_id="req-1"):
        structlog.stdlib.get_logger("app.test").info("something_happened", answer=42)
        logging.getLogger("uvicorn.error").warning("Uvicorn says %s", "hi")

    ours, theirs = captured_logs()
    assert ours["event"] == "something_happened"
    assert ours["answer"] == 42
    assert ours["level"] == "info"
    assert ours["logger"] == "app.test"
    assert ours["request_id"] == "req-1"
    assert "timestamp" in ours
    assert theirs["event"] == "Uvicorn says hi"
    assert theirs["level"] == "warning"
    assert theirs["request_id"] == "req-1"


def test_a_library_logger_with_its_own_handler_is_taken_over_not_duplicated() -> None:
    # What importing Haystack does when structlog is installed: a handler of its own.
    theirs = io.StringIO()
    haystack = logging.getLogger("haystack")
    haystack.addHandler(logging.StreamHandler(theirs))
    ours = io.StringIO()
    configure_logging("json", "INFO", stream=ours)

    logging.getLogger("haystack.components").warning("slow embedder")

    assert theirs.getvalue() == ""
    [line] = [json.loads(line) for line in ours.getvalue().splitlines()]
    assert line["event"] == "slow embedder"


def test_uvicorns_own_access_log_is_silenced(captured_logs: LogLines) -> None:
    logging.getLogger("uvicorn.access").info('127.0.0.1 - "GET /health HTTP/1.1" 200')

    assert captured_logs() == []


def test_an_exception_is_logged_as_one_json_line_with_its_traceback(
    captured_logs: LogLines,
) -> None:
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        structlog.stdlib.get_logger("app.test").exception("it_failed")

    [line] = captured_logs()
    assert line["event"] == "it_failed"
    assert "RuntimeError: boom" in line["exception"]


def test_console_format_is_for_humans_not_json() -> None:
    stream = io.StringIO()
    configure_logging("console", "INFO", stream=stream)

    structlog.stdlib.get_logger("app.test").info("something_happened", answer=42)

    output = stream.getvalue()
    assert "something_happened" in output
    assert "answer" in output
    assert not output.lstrip().startswith("{")


def test_debug_lines_are_dropped_at_info(captured_logs: LogLines) -> None:
    structlog.stdlib.get_logger("app.test").debug("noisy")

    assert captured_logs() == []


API_KEY = "sk-ant-api03-very-secret"
DB_PASSWORD = "hunter2"


def test_config_loaded_reports_the_config_without_its_secrets(captured_logs: LogLines) -> None:
    settings = Settings.model_construct(
        anthropic_api_key=SecretStr(API_KEY),
        database_url=SecretStr(f"postgresql://rag:{DB_PASSWORD}@db.internal:5432/rag"),
        llm_provider="anthropic",
        llm_model="claude-opus-5-5",
        ollama_base_url="http://ollama:11434",
        llm_connect_timeout_s=5,
        llm_read_timeout_s=60,
        turn_deadline_s=120,
        rewrite_deadline_s=30,
    )

    log_config_loaded(settings)

    [line] = captured_logs()
    raw = json.dumps(line)
    assert API_KEY not in raw
    assert DB_PASSWORD not in raw
    assert line["event"] == "config_loaded"
    assert line["llm_provider"] == "anthropic"
    assert line["llm_model"] == "claude-opus-5-5"
    assert line["ollama_base_url"] == "http://ollama:11434"
    assert line["llm_read_timeout_s"] == 60
    assert line["turn_deadline_s"] == 120
    assert line["database_host"] == "db.internal:5432"
    assert line["anthropic_api_key"] == "set"
    assert line["database_url"] == "set"


def test_config_loaded_says_unset_for_a_missing_secret(captured_logs: LogLines) -> None:
    log_config_loaded(Settings.model_construct(anthropic_api_key=None, llm_provider="ollama"))

    [line] = captured_logs()
    assert line["anthropic_api_key"] == "unset"
    assert line["database_host"] == "localhost:5432"


QUESTION = "Why can't ACME-CLIENT-42 log in?"
STANDALONE = "Why can't ACME-CLIENT-42 log in with SSO on v3?"
ANSWER_TEXT = "ACME-CLIENT-42's IdP certificate expired [1]."


def passage(id: str, score: float) -> Passage:
    return Passage(
        id=id,
        article=ArticleRef(id="sso-setup", title="Setting up SSO"),
        section=SectionRef(id="troubleshooting", path=["Troubleshooting"]),
        text="AUTH-403 means the IdP certificate has expired.",
        applies_to=["v3"],
        status="current",
        score=score,
    )


RETRIEVED = [passage("sso-setup#0", 0.82), passage("sso-setup#1", 0.61)]
ANSWER = Answer(
    text=ANSWER_TEXT,
    citations=[Citation(n=1, passage=RETRIEVED[0])],
    retrieved_passages=RETRIEVED,
    standalone_question=STANDALONE,
)
TIMINGS = TurnTimings(rewrite_ms=310.2, retrieval_ms=42.0, ttft_ms=880.5, total_ms=2400.1)


def log_turn(outcome: ChatResult | ErrorCode, retrieved: list[Passage] = RETRIEVED) -> None:
    log_turn_completed(
        question=QUESTION,
        outcome=outcome,
        retrieved=retrieved,
        provider="anthropic",
        model="claude-opus-5-5",
        prompt_version="2026-10-01",
        timings=TIMINGS,
    )


def test_turn_completed_records_the_turn_without_any_of_its_text(captured_logs: LogLines) -> None:
    log_turn(ANSWER)

    [line] = captured_logs()
    assert line == {
        "event": "turn_completed",
        "outcome": "answer",
        "provider": "anthropic",
        "model": "claude-opus-5-5",
        "prompt_version": "2026-10-01",
        "passages": [{"id": "sso-setup#0", "score": 0.82}, {"id": "sso-setup#1", "score": 0.61}],
        "citation_count": 1,
        "rewrite_ms": 310.2,
        "retrieval_ms": 42.0,
        "ttft_ms": 880.5,
        "total_ms": 2400.1,
        "level": "info",
        "logger": "app.logs",
        "timestamp": line["timestamp"],
    }
    assert "ACME-CLIENT-42" not in json.dumps(line)


def test_a_refusal_records_why(captured_logs: LogLines) -> None:
    refusal = Refusal(
        message="The Knowledge Base doesn't cover this.",
        reason="no_relevant_passages",
        retrieved_passages=[],
        standalone_question=None,
    )

    log_turn(refusal, retrieved=[])

    [line] = captured_logs()
    assert line["outcome"] == "refusal"
    assert line["refusal_reason"] == "no_relevant_passages"
    assert line["citation_count"] == 0
    assert line["passages"] == []


def test_a_failed_turn_records_its_error_code(captured_logs: LogLines) -> None:
    log_turn("llm_timeout")

    [line] = captured_logs()
    assert line["outcome"] == "error"
    assert line["error_code"] == "llm_timeout"
    assert line["citation_count"] == 0
    assert len(line["passages"]) == 2


def test_at_debug_the_turns_text_is_logged_too() -> None:
    stream = io.StringIO()
    configure_logging("json", "DEBUG", stream=stream)

    log_turn(ANSWER)

    content, completed = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert content["event"] == "turn_content"
    assert content["level"] == "debug"
    assert content["question"] == QUESTION
    assert content["standalone_question"] == STANDALONE
    assert content["text"] == ANSWER_TEXT
    assert completed["event"] == "turn_completed"
