from pathlib import Path

import pytest

from evaluation.corpus_lint import lint_article
from evaluation.fact_sheet import load_fact_sheet
from evaluation.knowledge_base import KNOWLEDGE_BASE_DIR, parse_article

FACT_SHEET = load_fact_sheet()


def article(body: str, *, applies_to: str = "[v3]") -> str:
    status = "deprecated" if applies_to == "[v2]" else "current"
    return (
        "---\n"
        "id: nimbus-handmade\n"
        "title: A Hand-made Article\n"
        "product: OmniCorp Nimbus\n"
        f"applies_to: {applies_to}\n"
        "doc_type: guide\n"
        f"status: {status}\n"
        "last_updated: 2026-09-01\n"
        "owner: Identity Team\n"
        "---\n\n"
        "Intro.\n\n## Setup\n\n" + body + "\n"
    )


def violations(body: str, *, applies_to: str = "[v3]") -> list[str]:
    return lint_article(parse_article(article(body, applies_to=applies_to)), FACT_SHEET)


def rules_hit(body: str, *, applies_to: str = "[v3]") -> list[str]:
    return [v.split(":")[0] for v in violations(body, applies_to=applies_to)]


def test_an_article_that_mentions_ldap_fails() -> None:
    assert violations("Nimbus can also sync users from LDAP.") == ["forbidden topic ldap: 'LDAP'"]


def test_an_article_that_puts_scim_on_business_fails() -> None:
    assert violations("SCIM provisioning is available on the Business tier.") == [
        "conflict scim-tier: 'Business' in 'SCIM provisioning is available on the Business tier.'"
    ]


def test_an_article_that_agrees_with_the_planted_facts_passes() -> None:
    body = (
        "SCIM provisioning needs the Enterprise tier. Changes sync every 40 minutes.\n\n"
        "| Plan Tier | Sustained limit |\n|---|---|\n| Business | 600 req/min |\n\n"
        "Deliveries are signed with HMAC-SHA256 in `X-Nimbus-Signature-256`."
    )

    assert violations(body) == []


CONTRADICTIONS = {
    "rate-limit-business": "| Business | 900 req/min |",
    "burst": "Bursts go to \u00d73 the limit for 10 s.",
    "webhook-signature-header": "```http\nX-Nimbus-Signature: abc\n```",
    "saml-email-attribute": "The SAML assertion carries the address in `mail`.",
    "audit-log-retention": "Business keeps audit-log events for 180 days.",
    "auth-403-meaning": "AUTH-403 means the SAML certificate expired.",
    "scim-sync-interval": "SCIM changes reach Nimbus every 15 minutes.",
    "deprovisioned-data-retention": "A deprovisioned user's data is kept for 60 days.",
}


@pytest.mark.parametrize(("rule", "body"), CONTRADICTIONS.items(), ids=CONTRADICTIONS.keys())
def test_a_statement_that_contradicts_a_planted_value_fails(rule: str, body: str) -> None:
    assert f"conflict {rule}" in rules_hit(body)


def test_v2_articles_are_checked_against_the_v2_facts() -> None:
    assert violations("Signed with HMAC-SHA1 in `X-Nimbus-Signature`.", applies_to="[v2]") == []
    assert rules_hit("Signed with HMAC-SHA256.", applies_to="[v2]") == [
        "conflict webhook-signature-algorithm-v2"
    ]


def test_a_v2_article_may_mention_scim_only_as_missing() -> None:
    assert violations("There is no SCIM provisioning.", applies_to="[v2]") == []
    assert violations("SCIM syncs users every 40 minutes.", applies_to="[v2]") == [
        "conflict scim-absent-on-v2: 'SCIM syncs users every 40 minutes.'"
    ]


def test_a_v2_article_leaves_its_version_to_the_front_matter() -> None:
    assert violations("Webhooks in v2 can't be paused.", applies_to="[v2]") == [
        "version framing: 'in v2'"
    ]


# --- The committed Knowledge Base -------------------------------------------------------------

PLANTED_ARTICLES = {fact.article for fact in FACT_SHEET.planted_facts}
GENERATED_PATHS = sorted(
    path for path in KNOWLEDGE_BASE_DIR.glob("*.md") if path.stem not in PLANTED_ARTICLES
)


@pytest.mark.parametrize("path", GENERATED_PATHS, ids=lambda path: path.stem)
def test_generated_article_passes_the_lint(path: Path) -> None:
    generated = parse_article(path.read_text(encoding="utf-8"))

    assert lint_article(generated, FACT_SHEET) == []
