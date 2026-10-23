import json

from app.chat_model import TokenUsage
from evaluation.llm_report import RunInfo, cost_usd, render_markdown, report_json, report_stem
from evaluation.llm_scoring import QuestionScore, score_turn
from evaluation.llm_scoring_test import (
    OKTA,
    ONE_SOURCE,
    PRICING,
    answer,
    golden,
    refusal,
    run,
)

INFO = RunInfo(
    date="2026-10-23T12:00:00Z",
    git_sha="138f3b1",
    provider="anthropic",
    model="claude-opus-5-5",
    effort="low",
    prompt_version="v2",
    top_k=8,
    min_score=0.66,
    question_set="curated",
)


def scores() -> list[QuestionScore]:
    known_miss = golden("gq-google-sso", category="partial", known_retrieval_miss="never retrieved")
    return [
        score_turn(golden("gq-right"), ONE_SOURCE, run(answer("Okta [1].", OKTA))),
        score_turn(golden("gq-missed"), ONE_SOURCE, run(refusal(), retrieved=(PRICING,))),
        score_turn(golden("gq-ldap", category="unanswerable"), (), run(refusal())),
        score_turn(known_miss, ONE_SOURCE, run(refusal(), retrieved=(PRICING,))),
    ]


def test_the_report_is_named_by_provider_model_prompt_version_and_question_set() -> None:
    assert report_stem(INFO) == "anthropic-claude-opus-5-5-v2-curated"


def test_cost_uses_the_models_list_price_per_million_tokens() -> None:
    usage = TokenUsage(input_tokens=2_000_000, output_tokens=100_000)

    assert cost_usd("claude-opus-5-5", usage) == 2 * 4.0 + 0.1 * 20.0
    assert cost_usd("qwen3.5:2b", usage) is None


def test_the_header_records_what_the_run_ran_with() -> None:
    report = render_markdown(INFO, scores())

    for stamp in ("138f3b1", "claude-opus-5-5", "effort low", "v2", "top_k 8", "min_score 0.66"):
        assert stamp in report
    assert "curated (4 questions)" in report


def test_the_headline_leaves_known_retrieval_misses_out_and_lists_them_apart() -> None:
    report = render_markdown(INFO, scores())

    headline = report.split("## Known retrieval misses")[0]
    assert "| Outcome accuracy | 66.7% (2/3) |" in headline
    assert "| Refusal correctness | 1/1 unanswerable refused; 1 answerable refused |" in headline
    known = report.split("## Known retrieval misses")[1].split("##")[0]
    assert "gq-google-sso" in known


def test_a_wrong_outcome_shows_its_blame_and_retrieval_recall() -> None:
    report = render_markdown(INFO, scores())

    failures = report.split("## Wrong outcomes")[1].split("##")[0]
    assert "| gq-missed | answer | refusal (not_in_context) | retrieval | 0% |" in failures
    assert "gq-right" not in failures


def test_the_json_report_carries_the_run_the_totals_and_every_answer() -> None:
    data = json.loads(json.dumps(report_json(INFO, scores())))

    assert data["run"]["prompt_version"] == "v2"
    assert data["totals"]["questions"] == 3
    assert data["known_misses"]["questions"] == 1
    [right] = [q for q in data["questions"] if q["id"] == "gq-right"]
    assert right["text"] == "Okta [1]."
    assert right["cited"] == [{"article": "sso", "section": "okta"}]
    assert right["outcome_correct"] is True
