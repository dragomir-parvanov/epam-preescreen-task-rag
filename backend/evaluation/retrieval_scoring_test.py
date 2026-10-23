import pytest

from app.knowledge_base import parse_article
from app.passages import ArticleRef, Passage, SectionRef
from evaluation.golden import GoldenQuestion
from evaluation.retrieval_scoring import (
    QuestionRetrieval,
    SectionKey,
    UnresolvedSourcesError,
    calibrate,
    failures,
    render_report,
    resolve_expected_sources,
    sources_rank,
)

SSO_ARTICLE = parse_article(
    "---\nid: sso\ntitle: Configuring SSO\napplies_to: [v3]\nstatus: current\n---\n"
    "Intro.\n\n## Okta\n\nAdd the app.\n\n## Enforcing SSO\n\n### Break-glass admin\n\nKeep one.\n",
    source="sso.md",
)


def question(
    id: str = "gq-okta",
    *,
    sources: tuple[tuple[str, str], ...] = (("sso", "Okta"),),
    origin: str = "curated",
    answerable: bool = True,
) -> GoldenQuestion:
    return GoldenQuestion.model_validate(
        {
            "id": id,
            "question": f"Question {id}?",
            "category": "single-article" if answerable else "unanswerable",
            "answerable": answerable,
            "origin": origin,
            "expected_sources": [{"article": a, "section": s} for a, s in sources]
            if answerable
            else [],
            "must_mention": [["term"]] if answerable else [],
        }
    )


# --- Expected sources -> the Section ids retrieval returns -------------------------------------


def test_resolves_a_section_path_to_the_section_id_passages_carry() -> None:
    gq = question(sources=(("sso", "Okta"), ("sso", "Enforcing SSO > Break-glass admin")))

    resolved = resolve_expected_sources([gq], [SSO_ARTICLE])

    assert resolved == {
        "gq-okta": (SectionKey("sso", "okta"), SectionKey("sso", "enforcing-sso-break-glass-admin"))
    }


def test_names_every_source_that_resolves_to_no_section() -> None:
    questions = [
        question("gq-a", sources=(("sso", "Entra ID"),)),
        # "Enforcing SSO" holds no text of its own, so no Passage cites it.
        question("gq-b", sources=(("sso", "Enforcing SSO"),)),
        question("gq-c", sources=(("scim", "Okta"),)),
    ]

    with pytest.raises(UnresolvedSourcesError) as error:
        resolve_expected_sources(questions, [SSO_ARTICLE])

    assert error.value.unresolved == (
        "gq-a: sso > Entra ID",
        "gq-b: sso > Enforcing SSO",
        "gq-c: scim > Okta",
    )


# --- Recall@k ---------------------------------------------------------------------------------


def passage(article: str, section: str, score: float = 0.8, n: int = 1) -> Passage:
    return Passage(
        id=f"{article}#{section}-{n}",
        article=ArticleRef(id=article, title=article.title()),
        section=SectionRef(id=section, path=(article.title(), section)),
        text="Text.",
        applies_to=("v3",),
        status="current",
        score=score,
    )


def test_the_sources_rank_is_the_depth_that_holds_every_expected_section() -> None:
    expected = (SectionKey("sso", "okta"), SectionKey("scim", "prerequisites"))
    ranking = (
        passage("sso", "okta"),
        passage("sso", "okta", n=2),
        passage("plans", "feature-matrix"),
        passage("scim", "prerequisites"),
    )

    assert sources_rank(expected, ranking) == 4
    assert sources_rank(expected, ranking[:3]) is None


# --- The CI bars ------------------------------------------------------------------------------

OKTA = SectionKey("sso", "okta")


def retrieval(
    id: str,
    *,
    origin: str = "curated",
    answerable: bool = True,
    rank: int | None = 1,
    top_score: float = 0.8,
) -> QuestionRetrieval:
    """A question expecting sso > Okta, retrieved at `rank` (None: not at all) among decoys."""
    ranking = [
        passage("plans", "best", score=top_score),
        *(passage("plans", f"decoy-{n}", score=top_score - 0.1) for n in range(8)),
    ]
    if rank is not None:
        ranking.insert(rank - 1, passage("sso", "okta", score=top_score - 0.05))
    passages = tuple(ranking[:8])
    return QuestionRetrieval(
        question=question(id, origin=origin, answerable=answerable),
        expected=(OKTA,) if answerable else (),
        hybrid=passages,
        dense_only=passages,
        no_prefix=passages,
    )


def test_passes_when_every_answerable_question_finds_its_sources_above_the_gate() -> None:
    retrievals = [
        retrieval("gq-curated", rank=3),
        retrieval("gq-generated", origin="generated", rank=6),
        retrieval("gq-off-topic", answerable=False, top_score=0.4),
    ]

    assert failures(retrievals, top_k=6, min_score=0.6) == []


def test_every_curated_question_must_find_its_sources_within_top_k() -> None:
    retrievals = [
        retrieval("gq-a", rank=1),
        retrieval("gq-b", rank=7),
        retrieval("gq-c", rank=None),
    ]

    assert failures(retrievals, top_k=6, min_score=0.6) == [
        "curated recall@6 is 33.3% (1/3), below 100%: gq-b, gq-c"
    ]


def test_generated_questions_must_reach_95_percent_recall_at_top_k() -> None:
    found = [retrieval(f"gq-g{n}", origin="generated", rank=2) for n in range(19)]
    missed = retrieval("gq-g-missed", origin="generated", rank=None)

    assert failures([*found, missed], top_k=6, min_score=0.6) == []
    assert failures([*found[:18], missed, missed], top_k=6, min_score=0.6) == [
        "generated recall@6 is 90.0% (18/20), below 95%: gq-g-missed, gq-g-missed"
    ]


def test_the_gate_must_not_refuse_an_answerable_question() -> None:
    retrievals = [
        retrieval("gq-weak", origin="generated", top_score=0.55),
        # Unanswerable questions that pass the gate are reported, never failed.
        retrieval("gq-near-topic", answerable=False, top_score=0.9),
    ]

    assert failures(retrievals, top_k=6, min_score=0.6) == [
        "the gate (min_score 0.6) refuses 1 answerable question: gq-weak (0.550)"
    ]


# --- Calibration ------------------------------------------------------------------------------


def test_calibrates_k_as_the_smallest_passing_k_plus_headroom() -> None:
    retrievals = [
        retrieval("gq-a", rank=1),
        retrieval("gq-b", rank=3),
        *(retrieval(f"gq-g{n}", origin="generated", rank=2) for n in range(19)),
        retrieval("gq-g-late", origin="generated", rank=8),
    ]

    calibration = calibrate(retrievals)

    assert (calibration.smallest_k, calibration.top_k) == (3, 5)


def test_k_stops_at_the_cap() -> None:
    calibration = calibrate([retrieval("gq-a", rank=7)])

    assert (calibration.smallest_k, calibration.top_k) == (7, 8)


def test_no_k_when_the_bars_fail_at_the_cap() -> None:
    calibration = calibrate([retrieval("gq-a", rank=1), retrieval("gq-b", rank=None)])

    assert (calibration.smallest_k, calibration.top_k) == (None, None)


def test_min_score_sits_a_margin_below_the_weakest_answerable_dense_top_1() -> None:
    retrievals = [
        retrieval("gq-strong", top_score=0.81),
        retrieval("gq-weakest", origin="generated", top_score=0.7166),
        # Unanswerable questions don't move it.
        retrieval("gq-near-topic", answerable=False, top_score=0.5),
    ]

    calibration = calibrate(retrievals)

    assert calibration.weakest.id == "gq-weakest"
    assert calibration.min_score == 0.66  # 0.7166 - 0.05, rounded down to 2 places


# --- The report -------------------------------------------------------------------------------


def report_lines(retrievals: list[QuestionRetrieval]) -> list[str]:
    report = render_report(retrievals, top_k=6, min_score=0.6)
    return [" ".join(line.split()) for line in report.splitlines()]


def test_the_report_has_a_row_per_question_with_its_ranks_and_gate_outcome() -> None:
    lines = report_lines(
        [
            retrieval("gq-found", rank=2, top_score=0.81),
            retrieval("gq-missed", origin="generated", rank=None, top_score=0.55),
            retrieval("gq-off-topic", answerable=False, top_score=0.4),
        ]
    )

    assert "gq-found curated single-article 2 2 2 0.810 answered" in lines
    assert "gq-missed generated single-article - - - 0.550 REFUSED" in lines
    assert "gq-off-topic curated unanswerable 0.400 refused" in lines


def test_the_report_compares_recall_across_runs_and_reports_the_gate_on_unanswerables() -> None:
    lines = report_lines(
        [
            retrieval("gq-a", rank=1),
            retrieval("gq-b", rank=3),
            retrieval("gq-near-topic", answerable=False, top_score=0.7),
            retrieval("gq-off-topic", answerable=False, top_score=0.4),
        ]
    )

    assert "curated hybrid 50.0% 50.0% 100.0% 100.0% 100.0% 100.0% 100.0% 100.0%" in lines
    assert "curated dense-only 50.0% 50.0% 100.0% 100.0% 100.0% 100.0% 100.0% 100.0%" in lines
    assert "The gate refuses 1 of 2 unanswerable questions (50.0%)." in lines


def test_the_report_ends_with_the_verdict() -> None:
    assert report_lines([retrieval("gq-a", rank=1)])[-1] == "PASS"
    assert report_lines([retrieval("gq-a", rank=None)])[-2:] == [
        "FAIL",
        "- curated recall@6 is 0.0% (0/1), below 100%: gq-a",
    ]
