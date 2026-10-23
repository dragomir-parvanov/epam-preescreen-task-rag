from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
import yaml

from evaluation.fact_sheet import FACT_SHEET_PATH, load_fact_sheet
from evaluation.generate_corpus import (
    GENERATED_MARKER,
    Corpus,
    Plan,
    Prompt,
    ReplyFormatError,
    generate,
    golden_entries,
    load_plan,
    merge_generated,
    parse_reply,
    render_article,
    review,
)
from evaluation.golden import parse_golden_questions
from evaluation.knowledge_base import KNOWLEDGE_BASE_DIR, parse_article

FACT_SHEET = load_fact_sheet()
PLANTED = {"nimbus-plan-tiers": "Plan Tiers and Entitlements"}

PLAN = Plan.model_validate(
    {
        "families": {
            "how-to": {
                "doc_type": "guide",
                "owner": "Workspace Administration Team",
                "max_h3": 1,
                "sections": ["Before you begin", "Step-by-step", "Troubleshooting"],
                "guidance": "A task in the console.",
            },
            "faq": {
                "doc_type": "reference",
                "owner": "Customer Success Enablement",
                "max_h3": 0,
                "sections": ["General questions", "Setup questions", "Where to find more"],
                "guidance": "Questions.",
            },
        },
        "articles": [
            {
                "id": "nimbus-admin-secrets",
                "family": "how-to",
                "title": "Storing Credentials in the Secrets Vault",
                "last_updated": "2026-02-23",
                "brief": "Create a secret and reference it as {{secrets.NAME}}.",
            },
            {
                "id": "nimbus-v2-faq",
                "family": "faq",
                "title": "Legacy Platform FAQ (v2)",
                "applies_to": ["v2"],
                "last_updated": "2025-06-16",
                "brief": "Questions from legacy clients.",
            },
        ],
    }
)
SECRETS = PLAN.spec("nimbus-admin-secrets")

FILLER = "Admins keep credentials out of workflow steps by storing them once in the vault. " * 30


def body(*, extra: str = "") -> str:
    return (
        "The secrets vault holds credentials that workflows use.\n\n"
        "## Before you begin\n\n"
        f"You need the Admin role. {FILLER}\n\n"
        "## Step-by-step\n\n"
        "1. Open **Settings > Secrets**.\n2. Click **New secret** and enter a NAME.\n\n"
        "```http\nPUT /secrets/CRM_TOKEN HTTP/1.1\nHost: api.nimbus.omnicorp.example\n```\n\n"
        f"Reference it as {{{{secrets.CRM_TOKEN}}}} in a step. {FILLER}\n\n"
        "### Rotating a secret\n\n"
        f"Saving a new value updates every workflow that uses it. {FILLER}\n\n"
        "## Troubleshooting\n\n"
        "| Problem | Fix |\n|---|---|\n| WF-400 on `{{secrets.X}}` | Check the name. |\n\n"
        f"See [Plan Tiers and Entitlements](nimbus-plan-tiers.md). {extra}\n"
    )


QUESTIONS = """\
- question: How does an Admin rotate a secret stored in the Nimbus secrets vault?
  sections: [Step-by-step > Rotating a secret]
  expected_facts: [Saving a new value updates every workflow that uses it.]
  must_mention: [[new value], [every workflow]]
"""


def reply(article_body: str, questions: str = QUESTIONS) -> str:
    questions_block = f"<golden_questions>\n{questions}</golden_questions>\n"
    return f"<article>\n{article_body}</article>\n{questions_block}"


def problems_with(article_body: str, questions: str = QUESTIONS) -> list[str]:
    return review(SECRETS, parse_reply(reply(article_body, questions)), PLAN, FACT_SHEET, PLANTED)


# --- Prompts ------------------------------------------------------------------------------------


def test_the_prompt_carries_the_fact_sheet_the_forbidden_terms_and_the_planted_facts() -> None:
    fact_sheet_text = FACT_SHEET_PATH.read_text(encoding="utf-8")
    prompt = Corpus(PLAN, FACT_SHEET, fact_sheet_text, PLANTED, Path(), Path()).prompt(SECRETS)

    assert fact_sheet_text.strip() in prompt.system
    assert '"LDAP"' in prompt.system
    assert "SCIM is Enterprise only. (nimbus-plan-tiers)" in prompt.system


def test_the_prompt_names_the_family_skeleton_and_the_articles_it_may_link_to() -> None:
    prompt = Corpus(PLAN, FACT_SHEET, "", PLANTED, Path(), Path()).prompt(SECRETS)

    assert "1. ## Before you begin\n2. ## Step-by-step\n3. ## Troubleshooting" in prompt.user
    assert "- nimbus-plan-tiers: Plan Tiers and Entitlements" in prompt.user
    assert "nimbus-v2-faq" not in prompt.user, "a later family isn't linkable"


# --- Replies ------------------------------------------------------------------------------------


def test_parses_the_article_and_its_questions() -> None:
    draft = parse_reply(reply(body()))

    assert draft.body.startswith("The secrets vault holds")
    assert draft.questions[0].sections == ["Step-by-step > Rotating a secret"]
    assert draft.questions[0].must_mention == [["new value"], ["every workflow"]]


@pytest.mark.parametrize(
    "text",
    [
        "Here is the article: ## Before you begin",
        "<article>\nText\n</article>\n",
        "<article>\nText\n</article>\n<golden_questions>\nnot: [a list\n</golden_questions>",
        "<article>\nText\n</article>\n<golden_questions>\n- question: Short?\n</golden_questions>",
    ],
    ids=["no-blocks", "no-questions", "bad-yaml", "incomplete-question"],
)
def test_rejects_a_reply_in_another_format(text: str) -> None:
    with pytest.raises(ReplyFormatError):
        parse_reply(text)


def test_renders_the_front_matter_from_the_plan() -> None:
    article = parse_article(render_article(PLAN.spec("nimbus-v2-faq"), PLAN, "Intro.\n"))

    assert article.front_matter.model_dump(mode="json") == {
        "id": "nimbus-v2-faq",
        "title": "Legacy Platform FAQ (v2)",
        "product": "OmniCorp Nimbus",
        "applies_to": ["v2"],
        "doc_type": "reference",
        "status": "deprecated",
        "last_updated": "2025-06-16",
        "owner": "Customer Success Enablement",
    }


# --- Review -------------------------------------------------------------------------------------


def test_accepts_a_draft_that_meets_every_rule() -> None:
    assert problems_with(body()) == []


def test_rejects_a_draft_off_the_family_skeleton() -> None:
    problems = problems_with(body().replace("## Troubleshooting", "## Common problems"))

    assert any("H2 headings must be exactly" in problem for problem in problems)


def test_rejects_a_draft_outside_the_word_range() -> None:
    assert problems_with(body().replace(FILLER, "Short.")) == ["85 words; write 800-1500"]


def test_rejects_a_link_to_an_article_it_may_not_link_to() -> None:
    problems = problems_with(body(extra="See [the FAQ](nimbus-v2-faq.md)."))

    assert problems == ["link to nimbus-v2-faq.md, which isn't an Article you may link to"]


def test_rejects_a_draft_that_fails_the_corpus_lint() -> None:
    problems = problems_with(body(extra="Secrets can also come from LDAP."))

    assert problems == ["lint: forbidden topic ldap: 'LDAP'"]


def test_rejects_a_question_whose_terms_are_not_in_its_sections() -> None:
    questions = QUESTIONS.replace("[[new value], [every workflow]]", "[[new value], [rollback]]")

    assert problems_with(body(), questions) == [
        "question 1: none of ['rollback'] appears in the text of "
        "['Step-by-step > Rotating a secret']"
    ]


def test_rejects_a_question_that_cites_a_missing_section() -> None:
    questions = QUESTIONS.replace("Step-by-step > Rotating a secret", "Rotating")

    [problem] = problems_with(body(), questions)
    assert problem.startswith("question 1: no Section path ['Rotating']")


# --- Golden Questions ---------------------------------------------------------------------------


def test_golden_entries_are_generated_single_article_questions() -> None:
    [entry] = golden_entries(SECRETS, parse_reply(reply(body())))

    [question] = parse_golden_questions([entry])
    assert question.id == "gq-admin-secrets-1"
    assert (question.category, question.origin, question.answerable) == (
        "single-article",
        "generated",
        True,
    )
    assert question.expected_sources[0].article == "nimbus-admin-secrets"


CURATED = """\
# Golden Questions: a header comment that must survive.

- id: gq-curated
  question: A curated question?
  category: table-lookup
  answerable: true
  origin: curated
  expected_sources:
    - { article: nimbus-plan-tiers, section: Feature matrix }
  must_mention:
    - [Enterprise]
"""


def generated(article: str, n: int) -> dict[str, Any]:
    return {
        "id": f"gq-{article.removeprefix('nimbus-')}-{n}",
        "question": f"Question {n} about {article}?",
        "category": "single-article",
        "answerable": True,
        "origin": "generated",
        "expected_sources": [{"article": article, "section": "Step-by-step"}],
        "expected_facts": ["A fact."],
        "must_mention": [["fact"]],
    }


def test_merging_appends_a_generated_block_after_the_curated_entries() -> None:
    merged = merge_generated(CURATED, [generated("nimbus-b", 1)], ["nimbus-b"])

    assert merged.startswith(CURATED + "\n" + GENERATED_MARKER)
    assert [q.id for q in parse_golden_questions(yaml.safe_load(merged))] == [
        "gq-curated",
        "gq-b-1",
    ]


def test_merging_replaces_only_the_regenerated_articles_entries() -> None:
    first = merge_generated(
        CURATED,
        [generated("nimbus-b", 1), generated("nimbus-b", 2), generated("nimbus-a", 1)],
        ["nimbus-a", "nimbus-b"],
    )

    merged = merge_generated(first, [generated("nimbus-b", 1)], ["nimbus-b"])

    assert merged.startswith(CURATED)
    assert [q.id for q in parse_golden_questions(yaml.safe_load(merged))] == [
        "gq-curated",
        "gq-a-1",
        "gq-b-1",
    ]


# --- Running it ---------------------------------------------------------------------------------


def test_generate_sends_the_problems_back_and_writes_the_accepted_reply(tmp_path: Path) -> None:
    (tmp_path / "golden.yaml").write_text(CURATED)
    corpus = Corpus(PLAN, FACT_SHEET, "", PLANTED, tmp_path, tmp_path / "golden.yaml")
    replies = [reply(body(extra="LDAP works too.")), reply(body())]
    seen: list[Sequence[tuple[str, str]]] = []

    def fake_model(prompt: Prompt, turns: Sequence[tuple[str, str]]) -> str:
        seen.append(list(turns))
        return replies[len(seen) - 1]

    assert generate(corpus, [SECRETS], fake_model, attempts=3) == 0

    assert "forbidden topic ldap" in seen[1][0][1]
    written = parse_article((tmp_path / "nimbus-admin-secrets.md").read_text())
    assert written.front_matter.title == "Storing Credentials in the Secrets Vault"
    golden = parse_golden_questions(yaml.safe_load((tmp_path / "golden.yaml").read_text()))
    assert [q.id for q in golden] == ["gq-curated", "gq-admin-secrets-1"]


def test_generate_gives_up_after_the_last_attempt(tmp_path: Path) -> None:
    (tmp_path / "golden.yaml").write_text(CURATED)
    corpus = Corpus(PLAN, FACT_SHEET, "", PLANTED, tmp_path, tmp_path / "golden.yaml")

    def stubborn_model(prompt: Prompt, turns: Sequence[tuple[str, str]]) -> str:
        return reply(body(extra="LDAP works too."))

    assert generate(corpus, [SECRETS], stubborn_model, attempts=2) == 1
    assert not (tmp_path / "nimbus-admin-secrets.md").exists()


# --- The committed plan -------------------------------------------------------------------------


def test_the_plan_covers_145_articles_in_8_families_about_a_tenth_of_them_v2() -> None:
    plan = load_plan()

    assert len(plan.articles) == 145
    assert len(plan.families) == 8
    v2 = [spec for spec in plan.articles if spec.applies_to == ["v2"]]
    assert 12 <= len(v2) <= 18


def test_every_planned_article_is_on_disk_and_matches_its_plan() -> None:
    plan = load_plan()
    on_disk = {path.stem for path in KNOWLEDGE_BASE_DIR.glob("*.md")}
    planned = [spec for spec in plan.articles if spec.id in on_disk]

    for spec in planned:
        article = parse_article((KNOWLEDGE_BASE_DIR / f"{spec.id}.md").read_text())
        expected = parse_article(render_article(spec, plan, "Intro.\n"))
        assert article.front_matter == expected.front_matter, spec.id
    assert len(on_disk) == 5 + len(planned), "every non-planted Article comes from the plan"
