from pathlib import Path

import pytest

from evaluation.fact_sheet import load_fact_sheet, mentions
from evaluation.knowledge_base import KNOWLEDGE_BASE_DIR, parse_article


@pytest.mark.parametrize(
    ("text", "term"),
    [
        ("Nimbus has no LDAP sync.", "ldap"),
        ("Pricing starts at $12.", "$"),
        ("Allowlist these IP ranges.", "IP ranges"),
        ("Configure SSO with Google\nWorkspace.", "Google Workspace"),
    ],
)
def test_finds_a_term_case_insensitively(text: str, term: str) -> None:
    assert mentions(text, term)


@pytest.mark.parametrize(
    ("text", "term"),
    [
        ("Signed with HMAC-SHA1.", "v1"),
        ("Two SLAs apply.", "SLA"),
        ("The email attribute.", "mail"),
    ],
)
def test_matches_word_terms_only_at_word_boundaries(text: str, term: str) -> None:
    assert not mentions(text, term)


# --- The committed fact sheet and Knowledge Base ----------------------------------------------

# Loaded once: the forbidden-topic check runs per Article, 150 times.
FACT_SHEET = load_fact_sheet()


def article_text(article_id: str) -> str:
    return (KNOWLEDGE_BASE_DIR / f"{article_id}.md").read_text(encoding="utf-8")


def test_every_planted_fact_is_stated_verbatim_in_its_article() -> None:
    missing = [
        f"{fact.id}: {fact.article} lacks {literal!r}"
        for fact in load_fact_sheet().planted_facts
        for literal in fact.verbatim
        if literal not in article_text(fact.article)
    ]

    assert missing == []


@pytest.mark.parametrize(
    "path", sorted(KNOWLEDGE_BASE_DIR.glob("*.md")), ids=lambda path: path.stem
)
def test_article_mentions_no_forbidden_topic(path: Path) -> None:
    article = parse_article(path.read_text(encoding="utf-8"))
    text = f"{article.front_matter.title}\n{article.body}"

    hits = [
        f"{topic.id}: {term!r}"
        for topic in FACT_SHEET.forbidden_topics
        for term in topic.terms
        if mentions(text, term)
    ]

    assert hits == []
