"""Ingestion and the Article view must split Articles into the same Sections.

Passages come from Haystack's `MarkdownHeaderSplitter`; the Article endpoints use the framework-free
`article_sections`. Citation click-through scrolls to a Passage's `section.id`, so every Passage's
Section has to be one of the Article view's Sections, with the same id and path.
"""

import pytest

from app.knowledge_base import KNOWLEDGE_BASE_DIR, Article, article_sections, load_articles
from app.rag.haystack.splitting import split_article

AWKWARD_BODY = """\
# Example

Intro text.

## Setup

## Setup

Steps, under the second of two identical headings.

```markdown
## not a heading, inside a code block
```

### Okta

#### A deeper heading stays inside its Section

More text.

### Okta

The same path again.

##No space, so not a heading

## Empty parent

### Child

Text.

## Trailing empty heading
"""


def section_outline(article: Article) -> list[tuple[str, tuple[str, ...]]]:
    return [(section.id, section.path) for section in article_sections(article)]


def passage_sections(article: Article) -> list[tuple[str, tuple[str, ...]]]:
    sections: list[tuple[str, tuple[str, ...]]] = []
    for passage in split_article(article):
        section = (passage.section.id, passage.section.path)
        if section not in sections:
            sections.append(section)
    return sections


@pytest.mark.parametrize("article", load_articles(KNOWLEDGE_BASE_DIR), ids=lambda a: a.id)
def test_every_committed_article_splits_into_the_same_sections(article: Article) -> None:
    assert passage_sections(article) == section_outline(article)


def test_an_awkward_article_splits_into_the_same_sections() -> None:
    article = Article(
        id="nimbus-example",
        title="Example",
        applies_to=("v3",),
        status="current",
        body=AWKWARD_BODY,
    )

    assert passage_sections(article) == section_outline(article)
    assert [id for id, _ in section_outline(article)] == [
        "intro",
        "setup",
        "setup-okta",
        "setup-okta-2",
        "empty-parent-child",
    ]
