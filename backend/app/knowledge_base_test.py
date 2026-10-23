from pathlib import Path

import pytest

from app.knowledge_base import (
    KNOWLEDGE_BASE_DIR,
    Article,
    InvalidArticleError,
    Section,
    article_sections,
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


# --- An Article's Sections, as the Article view shows them ------------------------------------


def sections_of(body: str) -> list[Section]:
    return article_sections(
        Article(
            id="nimbus-example", title="Example", applies_to=("v3",), status="current", body=body
        )
    )


def test_an_article_reads_as_its_intro_then_one_section_per_h2_and_h3() -> None:
    sections = sections_of(
        "Intro text.\n\n## Setup\n\nSteps.\n\n### Okta\n\nMore.\n\n## Troubleshooting\n\nTable.\n"
    )

    assert sections == [
        Section(id="intro", path=("Example",), level=1, markdown="Intro text."),
        Section(id="setup", path=("Example", "Setup"), level=2, markdown="## Setup\n\nSteps."),
        Section(
            id="setup-okta",
            path=("Example", "Setup", "Okta"),
            level=3,
            markdown="### Okta\n\nMore.",
        ),
        Section(
            id="troubleshooting",
            path=("Example", "Troubleshooting"),
            level=2,
            markdown="## Troubleshooting\n\nTable.",
        ),
    ]


def test_front_matter_stays_out_of_the_first_section() -> None:
    article = parse_article(SSO_ARTICLE, source="nimbus-sso-saml.md")

    first = article_sections(article)[0]

    assert first.markdown == "Nimbus supports SAML 2.0 single sign-on."


def test_repeated_heading_paths_get_numbered_ids_in_order() -> None:
    sections = sections_of(
        "## Okta\n\n### Errors\n\nA.\n\n## Entra\n\n### Errors\n\nB.\n\n"
        "## Notes\n\nC.\n\n## Notes\n\nD.\n\n## Notes\n\nE.\n"
    )

    assert [s.id for s in sections] == [
        "okta-errors",
        "entra-errors",
        "notes",
        "notes-2",
        "notes-3",
    ]


def test_a_heading_with_no_text_of_its_own_shows_with_the_next_section() -> None:
    # It holds no Passage to cite, so it takes no id; its heading still shows in the Article view.
    sections = sections_of("## Okta\n\n### Errors\n\nA.\n\n## Appendix\n")

    assert [(s.id, s.path, s.level, s.markdown) for s in sections] == [
        (
            "okta-errors",
            ("Example", "Okta", "Errors"),
            3,
            "## Okta\n\n### Errors\n\nA.\n\n## Appendix",
        )
    ]


def test_code_blocks_and_deeper_headings_stay_inside_their_section() -> None:
    body = "## Setup\n\n```bash\n## not a heading\n```\n\n#### Detail\n\nMore.\n"

    assert [(s.id, s.markdown) for s in sections_of(body)] == [("setup", body.strip())]


def test_an_h3_before_any_h2_hangs_off_the_title() -> None:
    sections = sections_of("### Okta\n\nText.\n")

    assert [(s.id, s.path, s.level) for s in sections] == [("okta", ("Example", "Okta"), 3)]


def test_a_leading_h1_repeating_the_title_is_not_intro_text() -> None:
    sections = sections_of("# Example\n\n## Setup\n\nSteps.\n")

    assert [s.id for s in sections] == ["setup"]


def test_section_ids_survive_edits_to_section_text() -> None:
    before = sections_of("Intro.\n\n## Setup\n\nOld.\n\n### Okta\n\nOld.\n")
    after = sections_of("Intro.\n\n## Setup\n\nNew text.\n\n### Okta\n\nNew text, longer.\n")

    assert [s.id for s in after] == [s.id for s in before] == ["intro", "setup", "setup-okta"]


@pytest.mark.parametrize("article", load_articles(KNOWLEDGE_BASE_DIR), ids=lambda a: a.id)
def test_every_committed_section_has_a_unique_id(article: Article) -> None:
    ids = [section.id for section in article_sections(article)]

    assert len(set(ids)) == len(ids)
