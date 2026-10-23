from collections.abc import Sequence

from fastapi.testclient import TestClient

from app.config import Settings
from app.knowledge_base import KNOWLEDGE_BASE_DIR, Article, parse_article
from app.main import create_app

ARTICLE = parse_article(
    """\
---
id: nimbus-example
title: An Example Article
product: OmniCorp Nimbus
applies_to: [v2, v3]
doc_type: guide
status: deprecated
last_updated: 2026-08-14
owner: Identity Team
---

Intro text.

## Setup

Steps.

### Okta

More.
""",
    source="nimbus-example.md",
)


def client(articles: Sequence[Article] | None = None) -> TestClient:
    """Over `articles`, or over the committed Knowledge Base in `knowledge-base/` by default."""
    return TestClient(create_app(Settings.model_construct(), articles=articles))


def test_lists_every_article_in_the_knowledge_base() -> None:
    response = client().get("/articles")

    assert response.status_code == 200
    assert [article["id"] for article in response.json()] == sorted(
        path.stem for path in KNOWLEDGE_BASE_DIR.glob("*.md")
    )


def test_lists_an_article_with_its_section_outline() -> None:
    response = client([ARTICLE]).get("/articles")

    assert response.json() == [
        {
            "id": "nimbus-example",
            "title": "An Example Article",
            "applies_to": ["v2", "v3"],
            "status": "deprecated",
            "sections": [
                {"id": "intro", "path": ["An Example Article"]},
                {"id": "setup", "path": ["An Example Article", "Setup"]},
                {"id": "setup-okta", "path": ["An Example Article", "Setup", "Okta"]},
            ],
        }
    ]


def test_gets_one_article_with_its_ordered_sections() -> None:
    response = client([ARTICLE]).get("/articles/nimbus-example")

    assert response.status_code == 200
    assert response.json() == {
        "id": "nimbus-example",
        "title": "An Example Article",
        "applies_to": ["v2", "v3"],
        "status": "deprecated",
        "sections": [
            {"id": "intro", "path": ["An Example Article"], "level": 1, "markdown": "Intro text."},
            {
                "id": "setup",
                "path": ["An Example Article", "Setup"],
                "level": 2,
                "markdown": "## Setup\n\nSteps.",
            },
            {
                "id": "setup-okta",
                "path": ["An Example Article", "Setup", "Okta"],
                "level": 3,
                "markdown": "### Okta\n\nMore.",
            },
        ],
    }


def test_an_unknown_article_is_not_found() -> None:
    response = client([ARTICLE]).get(
        "/articles/nimbus-missing", headers={"X-Request-ID": "req-404"}
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "There is no Article `nimbus-missing`.",
            "details": None,
            "request_id": "req-404",
        }
    }
