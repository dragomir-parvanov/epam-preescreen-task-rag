from typing import Any

import pytest
from pydantic import ValidationError

from app.knowledge_base import KNOWLEDGE_BASE_DIR, load_articles
from evaluation.golden import GoldenQuestion, load_golden_questions, parse_golden_questions
from evaluation.retrieval_scoring import resolve_expected_sources


def entry(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "gq-audit-retention-business",
        "question": "How long are audit logs kept on the Business tier?",
        "category": "table-lookup",
        "answerable": True,
        "origin": "curated",
        "expected_sources": [{"article": "nimbus-plan-tiers", "section": "Feature matrix"}],
        "expected_facts": ["90 days"],
        "must_mention": [["90 days", "90-day"]],
    }
    return base | overrides


def test_parses_a_single_turn_question() -> None:
    [question] = parse_golden_questions([entry()])

    assert question.expected_sources[0].section == "Feature matrix"
    assert question.must_mention == [["90 days", "90-day"]]
    assert question.history == []
    assert question.standalone_question is None


def test_parses_a_follow_up_with_history_and_its_ideal_rewrite() -> None:
    [question] = parse_golden_questions(
        [
            entry(
                id="gq-followup-rate-limit-enterprise",
                question="what about Enterprise?",
                category="follow-up",
                history=[{"question": "Business rate limit?", "answer": "600 requests/minute."}],
                standalone_question="What is the API rate limit for an Enterprise client?",
                standalone_must_mention=[["Enterprise"]],
            )
        ]
    )

    assert question.history[0].answer == "600 requests/minute."
    assert question.standalone_must_mention == [["Enterprise"]]


INCONSISTENT: dict[str, dict[str, Any]] = {
    "answerable-without-sources": {"expected_sources": []},
    "answerable-without-must-mention": {"must_mention": []},
    "empty-term-group": {"must_mention": [["90 days"], []]},
    "refusal-with-sources": {"answerable": False},
    "unanswerable-marked-answerable": {"category": "unanswerable"},
    "follow-up-without-history": {"category": "follow-up"},
    "rewrite-on-single-turn": {"standalone_question": "Only follow-ups are rewritten?"},
    "unknown-origin": {"origin": "handmade"},
    "unknown-field": {"difficulty": "hard"},
}


@pytest.mark.parametrize("overrides", INCONSISTENT.values(), ids=INCONSISTENT.keys())
def test_rejects_inconsistent_entries(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        GoldenQuestion.model_validate(entry(**overrides))


def test_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="gq-audit-retention-business"):
        parse_golden_questions([entry(), entry()])


# --- The committed Golden Questions -----------------------------------------------------------


def test_every_expected_source_names_a_section_that_passages_cite() -> None:
    # Resolved the way the retrieval eval does, through the Sections ingestion splits into
    # Passages; raises, naming each source, if one names a missing Article or heading.
    resolve_expected_sources(load_golden_questions(), load_articles(KNOWLEDGE_BASE_DIR))
