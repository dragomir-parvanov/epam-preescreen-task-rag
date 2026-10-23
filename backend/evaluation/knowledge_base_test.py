import re
from datetime import date
from pathlib import Path

import pytest

from evaluation.knowledge_base import (
    KNOWLEDGE_BASE_DIR,
    Article,
    ArticleFormatError,
    parse_article,
)

PLANTED_ARTICLES = {
    "nimbus-plan-tiers",
    "nimbus-sso-saml",
    "nimbus-scim-provisioning",
    "nimbus-api-webhooks",
    "nimbus-v2-legacy",
}
ARTICLE_PATHS = sorted(KNOWLEDGE_BASE_DIR.glob("*.md"))

FRONT_MATTER = """\
---
id: nimbus-example
title: An Example Article
product: OmniCorp Nimbus
applies_to: [v3]
doc_type: guide
status: current
last_updated: 2026-08-14
owner: Identity Team
---
"""


def test_parses_front_matter_and_section_paths() -> None:
    article = parse_article(
        FRONT_MATTER
        + "Intro text.\n\n## Setup\n\nSteps.\n\n### Okta\n\nMore.\n\n## Troubleshooting\n\nTable.\n"
    )

    assert article.front_matter.id == "nimbus-example"
    assert article.front_matter.applies_to == ["v3"]
    assert article.front_matter.last_updated == date(2026, 8, 14)
    assert article.section_paths == ("Setup", "Setup > Okta", "Troubleshooting")


def test_ignores_heading_lines_inside_code_blocks() -> None:
    code_block = "```bash\n# not a heading\n## nor this\n```\n"
    article = parse_article(FRONT_MATTER + "## Setup\n\n" + code_block)

    assert article.section_paths == ("Setup",)


def test_rejects_an_article_without_front_matter() -> None:
    with pytest.raises(ArticleFormatError, match="front-matter"):
        parse_article("## Setup\n\nText.\n")


@pytest.mark.parametrize(
    ("original", "replacement"),
    [
        ("owner: Identity Team\n", ""),
        ("owner: Identity Team\n", "owner: Identity Team\ntags: [sso]\n"),
        ("applies_to: [v3]", "applies_to: [v4]"),
        ("status: current", "status: archived"),
        ("doc_type: guide", "doc_type: tutorial"),
        ("id: nimbus-example", "id: Nimbus Example"),
    ],
    ids=["missing-field", "unknown-field", "unknown-version", "bad-status", "bad-type", "bad-id"],
)
def test_rejects_front_matter_outside_the_schema(original: str, replacement: str) -> None:
    with pytest.raises(ArticleFormatError, match="invalid front-matter"):
        parse_article(FRONT_MATTER.replace(original, replacement) + "## Setup\n")


# --- The committed Knowledge Base -------------------------------------------------------------


def read_article(path: Path) -> Article:
    return parse_article(path.read_text(encoding="utf-8"))


def test_the_knowledge_base_holds_the_planted_articles() -> None:
    assert {path.stem for path in ARTICLE_PATHS} >= PLANTED_ARTICLES


@pytest.mark.parametrize("path", ARTICLE_PATHS, ids=lambda path: path.stem)
def test_article_id_matches_its_file_name(path: Path) -> None:
    assert read_article(path).front_matter.id == path.stem


@pytest.mark.parametrize("path", ARTICLE_PATHS, ids=lambda path: path.stem)
def test_article_has_the_agreed_shape(path: Path) -> None:
    article = read_article(path)
    levels = [heading.level for heading in article.headings]
    words = len(article.body.split())

    assert 800 <= words <= 1500, f"{words} words"
    assert 4 <= len(article.section_paths) <= 8, article.section_paths
    assert set(levels) <= {2, 3}, "only H2/H3 headings: the title lives in the front-matter"
    assert levels[0] == 2, "the first heading is an H2"
    assert len(set(article.section_paths)) == len(article.section_paths), "Section paths repeat"


@pytest.mark.parametrize("path", ARTICLE_PATHS, ids=lambda path: path.stem)
def test_article_mixes_prose_steps_tables_and_code(path: Path) -> None:
    body = read_article(path).body

    assert re.search(r"^\|[ :-]*-{3,}", body, re.MULTILINE), "no table"
    assert re.search(r"^1\. ", body, re.MULTILINE), "no numbered steps"
    assert re.search(r"^```", body, re.MULTILINE), "no code or config block"


@pytest.mark.parametrize("path", ARTICLE_PATHS, ids=lambda path: path.stem)
def test_relative_links_point_at_existing_articles(path: Path) -> None:
    targets = re.findall(r"\]\(([^)#\s]+\.md)(?:#[^)]*)?\)", read_article(path).body)

    assert [t for t in targets if not (KNOWLEDGE_BASE_DIR / t).is_file()] == []


def test_among_planted_articles_only_the_legacy_reference_is_v2_and_deprecated() -> None:
    planted = {
        path.stem: read_article(path).front_matter
        for path in ARTICLE_PATHS
        if path.stem in PLANTED_ARTICLES
    }

    legacy = planted.pop("nimbus-v2-legacy")
    assert (legacy.applies_to, legacy.status) == (["v2"], "deprecated")
    assert {(fm.id, tuple(fm.applies_to), fm.status) for fm in planted.values()} == {
        (article_id, ("v3",), "current") for article_id in planted
    }


def test_the_legacy_reference_states_its_facts_without_version_framing() -> None:
    article = read_article(KNOWLEDGE_BASE_DIR / "nimbus-v2-legacy.md")
    prose = "\n".join(line for line in article.body.splitlines() if not line.startswith("#"))

    assert re.findall(r"\b(?:in|on|for|under|with) v2\b", prose, re.IGNORECASE) == []
