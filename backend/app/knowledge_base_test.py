from pathlib import Path

import pytest

from app.knowledge_base import (
    Article,
    InvalidArticleError,
    load_articles,
    parse_article,
    section_ids,
)

SSO_ARTICLE = """\
---
id: nimbus-sso-saml
title: Configuring SSO with SAML 2.0
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-08-14
owner: Identity Team
---
Nimbus supports SAML 2.0 single sign-on.

## Troubleshooting

AUTH-401 means clock skew.
"""


def test_an_article_is_its_front_matter_and_its_markdown_body() -> None:
    article = parse_article(SSO_ARTICLE, source="nimbus-sso-saml.md")

    assert article == Article(
        id="nimbus-sso-saml",
        title="Configuring SSO with SAML 2.0",
        applies_to=("v3",),
        status="current",
        body=(
            "Nimbus supports SAML 2.0 single sign-on.\n\n"
            "## Troubleshooting\n\nAUTH-401 means clock skew.\n"
        ),
    )


def test_an_article_without_front_matter_is_rejected_naming_its_file() -> None:
    with pytest.raises(InvalidArticleError, match=r"README\.md.*front-matter"):
        parse_article("# Knowledge Base\n\nSome notes.\n", source="README.md")


def test_an_article_with_an_unknown_platform_version_is_rejected_naming_the_field() -> None:
    text = SSO_ARTICLE.replace("applies_to: [v3]", "applies_to: [v4]")

    with pytest.raises(InvalidArticleError, match=r"sso\.md.*applies_to"):
        parse_article(text, source="sso.md")


def test_the_knowledge_base_is_every_markdown_article_in_the_directory_in_id_order(
    tmp_path: Path,
) -> None:
    (tmp_path / "sso.md").write_text(SSO_ARTICLE)
    (tmp_path / "v2").mkdir()
    (tmp_path / "v2" / "legacy.md").write_text(
        SSO_ARTICLE.replace("nimbus-sso-saml", "nimbus-v2-legacy")
    )
    (tmp_path / "notes.txt").write_text("not an Article")

    articles = load_articles(tmp_path)

    assert [a.id for a in articles] == ["nimbus-sso-saml", "nimbus-v2-legacy"]


def test_two_articles_with_the_same_id_are_rejected(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text(SSO_ARTICLE)
    (tmp_path / "b.md").write_text(SSO_ARTICLE)

    with pytest.raises(InvalidArticleError, match="nimbus-sso-saml"):
        load_articles(tmp_path)


def test_a_section_id_is_the_slug_of_its_heading_path_below_the_title() -> None:
    ids = section_ids(
        [(), ("Troubleshooting",), ("Troubleshooting", "Error AUTH-403: User not assigned")]
    )

    assert ids == ["intro", "troubleshooting", "troubleshooting-error-auth-403-user-not-assigned"]


def test_the_same_heading_under_different_parents_gets_different_ids() -> None:
    ids = section_ids([("Okta", "Example"), ("Microsoft Entra ID", "Example")])

    assert ids == ["okta-example", "microsoft-entra-id-example"]


def test_a_repeated_heading_path_is_disambiguated_in_order_of_appearance() -> None:
    ids = section_ids([("Notes",), ("Limits",), ("Notes",), ("Notes",)])

    assert ids == ["notes", "limits", "notes-2", "notes-3"]


def test_a_section_id_keeps_only_ascii_letters_and_digits() -> None:
    ids = section_ids([("Café & `X-Nimbus-Signature-256` (v3)!",), ("Checking a client's tier",)])

    assert ids == ["cafe-x-nimbus-signature-256-v3", "checking-a-clients-tier"]
