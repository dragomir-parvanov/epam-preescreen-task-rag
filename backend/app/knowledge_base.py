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

# The repo's `knowledge-base/`; the backend image copies it to the same place relative to `app/`.
KNOWLEDGE_BASE_DIR: Final = Path(__file__).resolve().parents[2] / "knowledge-base"

# The Section that holds an Article's text before its first H2; its heading path is just the title.
INTRO_SECTION_ID: Final = "intro"
# Passage ids are `<article-id>#<section-id>-<n>` in a VARCHAR(128) column.
_MAX_SECTION_ID_LENGTH: Final = 80

# Section boundaries, by the rules of Haystack's `MarkdownHeaderSplitter` (header_split_levels
# [2, 3]), which splits the same Articles into Passages: an ATX heading with one space after the
# `#`s, never inside a fenced code block. `app/rag/haystack/section_parity_test.py` checks that the
# two agree on every Section's id and path.
_SECTION_HEADING = re.compile(r"^(#{2,3}) (.+)$", re.MULTILINE)
_CODE_BLOCK = re.compile(
    r"^(?P<fence>`{3,}|~{3,})[^\n]*\n.*?^(?P=fence)\s*$", re.MULTILINE | re.DOTALL
)
_LEADING_H1 = re.compile(r"\A\s*# [^\n]*(?:\n|\Z)")

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


@dataclass(frozen=True, slots=True, kw_only=True)
class Section:
    """A heading-delimited part of an Article, as the Article view shows it."""

    id: str
    """The `section.id` of the Section's Passages, from `section_ids`."""
    path: tuple[str, ...]
    """The Article title, then the H2 and H3 above and including this Section, as Passages have it.
    The intro's path is just the title."""
    level: int
    """The heading's level, 2 or 3; 1 for the intro."""
    markdown: str
    """Verbatim, starting with the Section's own heading line, minus surrounding blank lines."""


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


def article_sections(article: Article) -> list[Section]:
    """The Article split at every H2 and H3, in document order: the Sections Passages cite.

    The text before the first H2, minus a leading H1, is the intro. A heading with no text of its
    own holds no Passage, so it gets no id: it shows at the top of the next Section instead (or at
    the end of the last one). Deeper headings stay inside their Section.
    """
    body = article.body
    code_blocks = [match.span() for match in _CODE_BLOCK.finditer(body)]
    headings = [
        match
        for match in _SECTION_HEADING.finditer(body)
        if not any(start <= match.start() < end for start, end in code_blocks)
    ]

    found: list[tuple[tuple[str, ...], int, str]] = []  # (path below the title, level, markdown)
    intro = _LEADING_H1.sub("", body[: headings[0].start()] if headings else body, count=1)
    if intro.strip():
        found.append(((), 1, intro))
    parent: str | None = None
    held = ""  # headings with no text yet, waiting for the next Section
    for i, heading in enumerate(headings):
        level, text = len(heading[1]), heading[2].strip()
        if level == 2:
            parent = text
        path = (text,) if level == 2 or parent is None else (parent, text)
        end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
        if not body[heading.end() : end].strip():
            held += body[heading.start() : end]
            continue
        found.append((path, level, held + body[heading.start() : end]))
        held = ""
    if held and found:
        path, level, markdown = found[-1]
        found[-1] = (path, level, markdown.rstrip() + "\n\n" + held)

    ids = section_ids(path for path, _, _ in found)
    return [
        Section(id=id, path=(article.title, *path), level=level, markdown=markdown.strip())
        for (path, level, markdown), id in zip(found, ids, strict=True)
    ]
