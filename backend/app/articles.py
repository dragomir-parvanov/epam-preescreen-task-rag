"""Knowledge Base browsing: `GET /articles` and `GET /articles/{article_id}`.

The UI opens an Article from a Citation and scrolls to the Passage's `section.id`, which is the
`id` of one of the Sections returned here.
"""

from collections.abc import Sequence
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.errors import AppError, error_responses
from app.knowledge_base import Article, article_sections


class SectionSummary(BaseModel):
    id: str
    """Stable slug, unique within the Article: the `section.id` its Passages carry."""
    path: list[str]
    """The Article title, then the H2 and H3 headings down to this Section; the intro has just the
    title. The same path as on the Section's Passages."""


class ArticleSummary(BaseModel):
    id: str
    title: str
    applies_to: list[Literal["v2", "v3"]]
    status: Literal["current", "deprecated"]
    sections: list[SectionSummary]


class ArticleSection(SectionSummary):
    level: int
    """2 for an H2, 3 for an H3, 1 for the intro (the text before the first H2)."""
    markdown: str
    """Verbatim, starting with the Section's own heading line (the intro has none)."""


class ArticleDetail(BaseModel):
    id: str
    title: str
    applies_to: list[Literal["v2", "v3"]]
    status: Literal["current", "deprecated"]
    sections: list[ArticleSection]
    """In reading order."""


def _summary(article: Article) -> ArticleSummary:
    return ArticleSummary(
        id=article.id,
        title=article.title,
        applies_to=list(article.applies_to),
        status=article.status,
        sections=[SectionSummary(id=s.id, path=list(s.path)) for s in article_sections(article)],
    )


def _detail(article: Article) -> ArticleDetail:
    return ArticleDetail(
        id=article.id,
        title=article.title,
        applies_to=list(article.applies_to),
        status=article.status,
        sections=[
            ArticleSection(id=s.id, path=list(s.path), level=s.level, markdown=s.markdown)
            for s in article_sections(article)
        ],
    )


def articles_router(articles: Sequence[Article]) -> APIRouter:
    """Routes over `articles`, in the order given."""
    router = APIRouter()
    by_id = {article.id: article for article in articles}

    @router.get("/articles", operation_id="listArticles")
    def list_articles() -> list[ArticleSummary]:
        """Every Article in the Knowledge Base, with its Section outline."""
        return [_summary(article) for article in articles]

    @router.get(
        "/articles/{article_id}",
        operation_id="getArticle",
        responses=error_responses("not_found"),
    )
    def get_article(article_id: str) -> ArticleDetail:
        """One full Article, split into its ordered Sections, for Citation click-through."""
        article = by_id.get(article_id)
        if article is None:
            raise AppError("not_found", f"There is no Article `{article_id}`.")
        return _detail(article)

    return router
