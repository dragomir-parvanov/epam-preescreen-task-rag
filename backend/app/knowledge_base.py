"""The Knowledge Base on disk: Articles as markdown files with YAML front-matter.

Framework-free, so ingestion and the Article endpoints read Articles, and name Sections, the
same way. A Passage's `section.id` must equal the id the Article endpoint returns, or Citation
click-through can't scroll to the Section.
"""

import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from app.passages import ArticleStatus, PlatformVersion

# The Section that holds an Article's text before its first H2; its heading path is just the title.
INTRO_SECTION_ID: Final = "intro"
# Passage ids are `<article-id>#<section-id>-<n>` in a VARCHAR(128) column.
_MAX_SECTION_ID_LENGTH: Final = 80

_FRONT_MATTER = re.compile(r"\A---[ \t]*\n(?P<yaml>.*?)\n---[ \t]*(?:\n|\Z)", re.DOTALL)


class InvalidArticleError(ValueError):
    """An Article file that can't be read; the message names the file and what to fix."""


@dataclass(frozen=True, slots=True, kw_only=True)
class Article:
    id: str
    title: str
    applies_to: tuple[PlatformVersion, ...]
    status: ArticleStatus
    body: str
    """The markdown after the front-matter."""


class _FrontMatter(BaseModel):
    # `product`, `doc_type`, `owner` and `last_updated` are for authors; nothing reads them.
    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str
    title: str
    applies_to: tuple[PlatformVersion, ...]
    status: ArticleStatus


def parse_article(text: str, *, source: str) -> Article:
    """One Article from its file's text. `source` names the file in error messages."""
    match = _FRONT_MATTER.match(text)
    if match is None:
        raise InvalidArticleError(f"{source}: an Article starts with YAML front-matter between ---")
    try:
        front_matter = _FrontMatter.model_validate(yaml.safe_load(match["yaml"]))
    except yaml.YAMLError as error:
        raise InvalidArticleError(f"{source}: front-matter is not valid YAML: {error}") from error
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in e['loc'])}: {e['msg']}" for e in error.errors()
        )
        raise InvalidArticleError(f"{source}: invalid front-matter: {problems}") from error
    return Article(
        id=front_matter.id,
        title=front_matter.title,
        applies_to=front_matter.applies_to,
        status=front_matter.status,
        body=text[match.end() :],
    )


def load_articles(directory: Path) -> list[Article]:
    """Every `*.md` Article under `directory`, in id order. Article ids must be unique."""
    articles = [
        parse_article(path.read_text(encoding="utf-8"), source=str(path.relative_to(directory)))
        for path in directory.rglob("*.md")
    ]
    duplicates = sorted(id for id, n in Counter(a.id for a in articles).items() if n > 1)
    if duplicates:
        raise InvalidArticleError(f"more than one Article has the id: {', '.join(duplicates)}")
    return sorted(articles, key=lambda a: a.id)


def section_ids(heading_paths: Iterable[Sequence[str]]) -> list[str]:
    """The stable ids of an Article's Sections, given their heading paths in document order.

    A heading path is the Section's headings *below* the Article title: `()` is the intro. The
    id slugs the whole path, so the same heading under two parents ("Okta > Example", "Entra >
    Example") gets two ids, and an id survives edits to the text and to other Sections. A path
    that repeats exactly gets `-2`, `-3`, ... in order of appearance.
    """
    seen: Counter[str] = Counter()
    ids: list[str] = []
    for path in heading_paths:
        slug = _slugify(" ".join(path)) if path else INTRO_SECTION_ID
        seen[slug] += 1
        ids.append(slug if seen[slug] == 1 else f"{slug}-{seen[slug]}")
    return ids


def _slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    ascii_text = ascii_text.replace("'", "")  # "client's" -> "clients", as GitHub's anchors do
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug[:_MAX_SECTION_ID_LENGTH].rstrip("-") or "section"
