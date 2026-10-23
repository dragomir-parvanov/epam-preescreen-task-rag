from dataclasses import replace

from app.knowledge_base import Article
from app.passages import ArticleRef, SectionRef
from app.rag.haystack.splitting import MAX_PASSAGE_WORDS, SplitPassage, split_article

ARTICLE = ArticleRef(id="nimbus-sso-saml", title="Configuring SSO with SAML 2.0")


def article(body: str) -> Article:
    return Article(
        id=ARTICLE.id, title=ARTICLE.title, applies_to=("v3",), status="current", body=body
    )


def words(n: int, word: str = "word") -> str:
    return " ".join([word] * n)


def table(rows: int) -> str:
    """A markdown table of ~10 words per row."""
    lines = ["| Code | Meaning | Fix |", "| --- | --- | --- |"]
    lines += [
        f"| AUTH-{400 + i} | the clock is off by minutes | sync the clocks |" for i in range(rows)
    ]
    return "\n".join(lines)


def test_each_h2_and_h3_section_becomes_one_passage_with_its_heading_path() -> None:
    body = (
        "## Troubleshooting\n\nCheck the error code first.\n\n"
        "### AUTH-401\n\nThe clock is skewed by more than 5 minutes.\n\n"
        "#### Fixing it\n\nSync the IdP clock.\n"
    )

    passages = split_article(article(body))

    assert passages == [
        SplitPassage(
            id="nimbus-sso-saml#troubleshooting-1",
            article=ARTICLE,
            section=SectionRef(
                id="troubleshooting", path=("Configuring SSO with SAML 2.0", "Troubleshooting")
            ),
            position=1,
            text="Check the error code first.",
            applies_to=("v3",),
            status="current",
        ),
        SplitPassage(
            id="nimbus-sso-saml#troubleshooting-auth-401-1",
            article=ARTICLE,
            section=SectionRef(
                id="troubleshooting-auth-401",
                path=("Configuring SSO with SAML 2.0", "Troubleshooting", "AUTH-401"),
            ),
            position=1,
            # Deeper headings stay inside their Section, verbatim.
            text=(
                "The clock is skewed by more than 5 minutes.\n\n"
                "#### Fixing it\n\nSync the IdP clock."
            ),
            applies_to=("v3",),
            status="current",
        ),
    ]


def test_text_before_the_first_h2_is_a_passage_whose_path_is_the_article_title() -> None:
    body = "Nimbus supports SAML 2.0 single sign-on.\n\n## Prerequisites\n\nA Business tier.\n"

    intro, _ = split_article(article(body))

    assert intro.id == "nimbus-sso-saml#intro-1"
    assert intro.section == SectionRef(id="intro", path=("Configuring SSO with SAML 2.0",))
    assert intro.text == "Nimbus supports SAML 2.0 single sign-on."


def test_a_leading_h1_repeating_the_title_is_not_intro_text() -> None:
    body = "# Configuring SSO with SAML 2.0\n\n## Prerequisites\n\nA Business tier.\n"

    passages = split_article(article(body))

    assert [p.section.id for p in passages] == ["prerequisites"]


def test_a_section_over_the_cap_is_split_at_block_boundaries_keeping_a_long_table_whole() -> None:
    long_table = table(30)  # ~300 words: over the cap on its own
    body = f"## Errors\n\n{words(40, 'before')}\n\n{long_table}\n\n{words(40, 'after')}\n"

    passages = split_article(article(body))

    assert [p.text for p in passages] == [words(40, "before"), long_table, words(40, "after")]
    assert [p.id for p in passages] == [
        "nimbus-sso-saml#errors-1",
        "nimbus-sso-saml#errors-2",
        "nimbus-sso-saml#errors-3",
    ]
    assert [p.position for p in passages] == [1, 2, 3]


def test_blocks_are_packed_into_passages_up_to_the_cap_with_no_overlap() -> None:
    paragraphs = [words(100, f"p{i}") for i in range(5)]  # 500 words in 100-word blocks
    body = "## Limits\n\n" + "\n\n".join(paragraphs) + "\n"

    passages = split_article(article(body))

    assert [p.text for p in passages] == [
        "\n\n".join(paragraphs[0:2]),
        "\n\n".join(paragraphs[2:4]),
        paragraphs[4],
    ]
    assert all(len(p.text.split()) <= MAX_PASSAGE_WORDS for p in passages)


def test_a_code_block_with_blank_lines_and_hash_comments_is_never_cut() -> None:
    code = (
        "```bash\n## not a heading\n" + "\n\n".join(words(30, "echo") for _ in range(4)) + "\n```"
    )
    body = f"## Example\n\n{words(200, 'intro')}\n\n{code}\n"

    passages = split_article(article(body))

    assert [p.text for p in passages] == [words(200, "intro"), code]


def test_a_loose_list_is_never_cut_between_its_items() -> None:
    items = "\n\n".join(f"{i}. {words(40, 'step')}" for i in range(1, 6))  # 200+ words
    body = f"## Setup\n\n{words(100, 'intro')}\n\n{items}\n"

    passages = split_article(article(body))

    assert [p.text for p in passages] == [words(100, "intro"), items]


def test_passage_ids_stay_the_same_when_a_sections_text_changes() -> None:
    before = split_article(article("## Rate limits\n\nBusiness: 600 req/min.\n"))
    after = split_article(article("## Rate limits\n\nBusiness: 900 req/min, burst x2.\n"))

    assert [p.id for p in after] == [p.id for p in before]
    assert after != before


def test_the_passages_carry_the_articles_platform_versions_and_status() -> None:
    legacy = replace(article("## Webhooks\n\nSigned with HMAC-SHA1.\n"), applies_to=("v2",))
    legacy = replace(legacy, status="deprecated")

    (passage,) = split_article(legacy)

    assert (passage.applies_to, passage.status) == (("v2",), "deprecated")
