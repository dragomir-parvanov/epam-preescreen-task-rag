from typing import Any

import pytest

from app.chat.schemas import (
    Answer,
    ArticleRef,
    ChatResult,
    Citation,
    Passage,
    Refusal,
    SectionRef,
    UncitedAnswer,
)
from app.chat_model import TokenUsage
from evaluation.golden import GoldenQuestion
from evaluation.llm_scoring import TurnRun, has_gap, percentile, score_turn, totals
from evaluation.retrieval_scoring import ExpectedSections, SectionKey

OKTA = SectionKey("sso", "okta")
OKTA_ALT = SectionKey("sso-legacy", "okta")
SCIM = SectionKey("scim", "provisioning")
PRICING = SectionKey("pricing", "tiers")


def golden(
    id: str = "gq-okta",
    *,
    category: str = "single-article",
    must_mention: list[list[str]] | None = None,
    **fields: Any,
) -> GoldenQuestion:
    answerable = category != "unanswerable" and fields.pop("answerable", True)
    data: dict[str, Any] = {
        "id": id,
        "question": f"Question {id}?",
        "category": category,
        "answerable": answerable,
        "origin": "curated",
        "expected_sources": [{"article": "sso", "section": "Okta"}] if answerable else [],
        "must_mention": (must_mention or [["Okta"]]) if answerable else [],
    }
    if category == "follow-up":
        data |= {"history": [{"question": "Earlier?", "answer": "Earlier answer."}]}
        data.setdefault("standalone_question", "Standalone?")
    return GoldenQuestion.model_validate(data | fields)


def wire(key: SectionKey) -> Passage:
    return Passage(
        id=f"{key.article}#{key.section}",
        article=ArticleRef(id=key.article, title=key.article.title()),
        section=SectionRef(id=key.section, path=[key.article.title(), key.section.title()]),
        text="Verbatim.",
        applies_to=["v3"],
        status="current",
        score=0.8,
    )


def answer(text: str, *cited: SectionKey) -> Answer:
    return Answer(
        text=text,
        citations=[Citation(n=n, passage=wire(key)) for n, key in enumerate(cited, start=1)],
        retrieved_passages=[],
        standalone_question=None,
    )


def uncited(text: str) -> UncitedAnswer:
    return UncitedAnswer(text=text, retrieved_passages=[], standalone_question=None)


def refusal(reason: str = "not_in_context") -> Refusal:
    return Refusal.model_validate(
        {
            "message": "The Knowledge Base doesn't cover this question.",
            "reason": reason,
            "retrieved_passages": [],
            "standalone_question": None,
        }
    )


def run(
    result: ChatResult | None,
    *,
    retrieved: tuple[SectionKey, ...] = (OKTA, PRICING),
    error: str | None = None,
    standalone_question: str | None = None,
    latency_ms: float = 1000.0,
) -> TurnRun:
    return TurnRun(
        result=result,
        error=error,
        retrieved=retrieved,
        standalone_question=standalone_question,
        latency_ms=latency_ms,
        ttft_ms=None,
        usage=TokenUsage(input_tokens=1000, output_tokens=100),
    )


ONE_SOURCE: ExpectedSections = ((OKTA, OKTA_ALT),)
TWO_SOURCES: ExpectedSections = ((OKTA, OKTA_ALT), (SCIM,))


# --- Outcome -----------------------------------------------------------------------------------


def test_a_cited_answer_to_an_answerable_question_is_the_right_outcome() -> None:
    score = score_turn(golden(), ONE_SOURCE, run(answer("Add the Okta app [1].", OKTA)))

    assert (score.expected, score.outcome, score.outcome_correct) == ("answer", "answer", True)
    assert score.blame is None


def test_a_refusal_of_an_unanswerable_question_is_the_right_outcome() -> None:
    score = score_turn(golden(category="unanswerable"), (), run(refusal("no_relevant_passages")))

    assert (score.expected, score.outcome, score.outcome_correct) == ("refusal", "refusal", True)
    assert score.refusal_reason == "no_relevant_passages"
    assert score.retrieval_recall is None
    assert score.citation_precision is None and score.citation_recall is None


def test_answering_an_unanswerable_question_is_the_models_failure() -> None:
    score = score_turn(golden(category="unanswerable"), (), run(answer("Yes [1].", PRICING)))

    assert (score.outcome, score.outcome_correct, score.blame) == ("answer", False, "model")


def test_a_partial_answer_is_one_that_states_the_gap_phrase() -> None:
    text = "Retries run 8 times [1]. I couldn't find anything about source IPs."
    score = score_turn(golden(category="partial"), ONE_SOURCE, run(answer(text, OKTA)))

    assert (score.expected, score.outcome, score.outcome_correct) == ("partial", "partial", True)


@pytest.mark.parametrize(
    "text",
    [
        "I couldn’t find anything about source IPs. Retries run 8 times [1].",  # curly, first
        "Retries run 8 times [1]. i COULDN'T FIND the IP list.",
    ],
)
def test_the_gap_phrase_counts_anywhere_in_any_case_with_either_apostrophe(text: str) -> None:
    assert has_gap(text)


def test_a_partial_question_answered_without_the_gap_phrase_is_the_wrong_outcome() -> None:
    score = score_turn(golden(category="partial"), ONE_SOURCE, run(answer("8 times [1].", OKTA)))

    assert (score.outcome, score.outcome_correct, score.blame) == ("answer", False, "model")


def test_an_uncited_answer_is_still_an_answer_but_counts_as_uncited() -> None:
    score = score_turn(golden(), ONE_SOURCE, run(uncited("Add the Okta app.")))

    assert (score.outcome, score.outcome_correct, score.uncited) == ("answer", True, True)
    assert score.citation_recall == 0.0
    assert score.citation_precision is None


def test_the_refusal_message_is_never_read_as_a_gap() -> None:
    score = score_turn(golden(category="partial"), ONE_SOURCE, run(refusal()))

    assert score.outcome == "refusal"


def test_a_refusal_or_gap_when_retrieval_missed_a_source_is_blamed_on_retrieval() -> None:
    missed = run(refusal(), retrieved=(PRICING,))
    gap = run(answer("I couldn't find it.", PRICING), retrieved=(PRICING,))

    assert score_turn(golden(), ONE_SOURCE, missed).blame == "retrieval"
    assert score_turn(golden(), ONE_SOURCE, gap).blame == "retrieval"
    assert score_turn(golden(), ONE_SOURCE, gap).retrieval_recall == 0.0


def test_a_refusal_when_retrieval_found_every_source_is_the_models_failure() -> None:
    score = score_turn(golden(), ONE_SOURCE, run(refusal(), retrieved=(OKTA,)))

    assert (score.outcome_correct, score.blame) == (False, "model")


def test_a_failed_turn_is_an_error_outcome() -> None:
    score = score_turn(golden(), ONE_SOURCE, run(None, error="rewrite_failed"))

    assert (score.outcome, score.error, score.outcome_correct) == ("error", "rewrite_failed", False)
    assert score.blame == "error"
    assert score.mentions_hit == 0


# --- Citations and retrieval, at Section level ---------------------------------------------------


def test_citing_an_alternative_section_counts_for_its_source() -> None:
    score = score_turn(golden(), ONE_SOURCE, run(answer("Okta [1].", OKTA_ALT)))

    assert (score.citation_precision, score.citation_recall) == (1.0, 1.0)


def test_citation_precision_and_recall_are_over_distinct_sections() -> None:
    # Two Passages of the Okta Section count once; the pricing Section isn't expected.
    text = "Okta [1][2]. Pricing [3]."
    score = score_turn(golden(), TWO_SOURCES, run(answer(text, OKTA, OKTA, PRICING)))

    assert score.citation_precision == 0.5
    assert score.citation_recall == 0.5


def test_retrieval_recall_is_the_share_of_sources_any_option_of_which_was_retrieved() -> None:
    score = score_turn(golden(), TWO_SOURCES, run(refusal(), retrieved=(OKTA_ALT, PRICING)))

    assert score.retrieval_recall == 0.5


# --- must_mention -----------------------------------------------------------------------------


def test_must_mention_counts_groups_with_any_term_matched_as_a_whole_word() -> None:
    gq = golden(must_mention=[["mail"], ["30 days", "30-day"], ["SCIM"]])
    text = "Send the email attribute [1]. Users are kept for 30-day [1] periods."

    score = score_turn(gq, ONE_SOURCE, run(answer(text, OKTA)))

    assert (score.mentions_hit, score.mentions_total) == (1, 3)
    assert score.missed_terms == ("mail", "SCIM")


def test_must_mention_treats_curly_and_straight_apostrophes_alike() -> None:
    gq = golden(must_mention=[["doesn't count"], ["can’t require"]])
    text = "A failed run doesn’t count [1]. An Admin can't require it [1]."

    score = score_turn(gq, ONE_SOURCE, run(answer(text, OKTA)))

    assert (score.mentions_hit, score.mentions_total) == (2, 2)


def test_a_follow_ups_standalone_question_is_checked_for_its_terms() -> None:
    gq = golden(category="follow-up", standalone_must_mention=[["v2"], ["signature"]])
    score = score_turn(
        gq,
        ONE_SOURCE,
        run(answer("Okta [1].", OKTA), standalone_question="Which header holds it on v2?"),
    )

    assert (score.standalone_hit, score.standalone_total) == (1, 2)


# --- Totals -------------------------------------------------------------------------------------


def test_totals_summarise_the_scores() -> None:
    scores = [
        score_turn(golden("gq-a"), ONE_SOURCE, run(answer("Okta [1].", OKTA), latency_ms=100)),
        score_turn(golden("gq-b"), ONE_SOURCE, run(uncited("Okta."), latency_ms=200)),
        score_turn(
            golden("gq-c"), ONE_SOURCE, run(refusal(), retrieved=(PRICING,), latency_ms=300)
        ),
        score_turn(golden("gq-d", category="unanswerable"), (), run(refusal(), latency_ms=400)),
        score_turn(golden("gq-e", category="unanswerable"), (), run(answer("Yes.", PRICING))),
        score_turn(
            golden("gq-f", category="unanswerable"), (), run(answer("I couldn't find X.", OKTA))
        ),
    ]

    summary = totals(scores)

    assert summary.questions == 6
    assert summary.outcome_accuracy == 3 / 6
    assert summary.citation_precision == 1.0  # only gq-a cites a Section
    assert summary.citation_recall == 1 / 3  # over the three answerable questions
    assert summary.retrieval_recall == 2 / 3
    assert summary.uncited_rate == 1 / 4  # of the four Answers
    assert summary.must_mention_rate == 2 / 3
    assert summary.refusals == (1, 3)  # unanswerable questions refused
    assert summary.gap_instead_of_refusal == 1  # gq-f: a soft refusal
    assert summary.false_refusals == 1
    assert summary.errors == 0
    assert summary.usage == TokenUsage(input_tokens=6000, output_tokens=600)


def test_percentiles_are_nearest_rank() -> None:
    latencies = [float(n) for n in range(1, 21)]

    assert (percentile(latencies, 50), percentile(latencies, 95)) == (10.0, 19.0)
    assert percentile([], 50) is None
