"""The Knowledge Base *format*: the full front-matter schema (#6) and the headings, which the shape
tests, the corpus lint and the generator hold every Article to.

Stricter than `app.knowledge_base`, the server's reader, which ignores the author-only fields.
Golden `expected_sources` resolve through that one instead (`evaluation.retrieval_scoring`), so
they name Sections exactly as Passages do.
"""

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

REPO_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_BASE_DIR = REPO_ROOT / "knowledge-base"

PlatformVersion = Literal["v2", "v3"]

_FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")


class ArticleFormatError(ValueError):
    """The Article's markdown or front-matter breaks the Knowledge Base format."""


class FrontMatter(BaseModel):
    """The agreed Article front-matter (#6); every field is required and no others are allowed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=1)
    product: Literal["OmniCorp Nimbus"]
    applies_to: list[PlatformVersion] = Field(min_length=1)
    doc_type: Literal["guide", "reference", "release-notes"]
    status: Literal["current", "deprecated"]
    last_updated: date
    owner: str = Field(min_length=1)


@dataclass(frozen=True)
class Heading:
    level: int
    text: str


@dataclass(frozen=True)
class Article:
    front_matter: FrontMatter
    body: str
    headings: tuple[Heading, ...]

    @property
    def section_paths(self) -> tuple[str, ...]:
        """The H2/H3 heading paths, e.g. `Enforcing SSO > Break-glass admin account`."""
        paths: list[str] = []
        parent: str | None = None
        for heading in self.headings:
            if heading.level == 2:
                parent = heading.text
                paths.append(heading.text)
            elif heading.level == 3:
                paths.append(f"{parent} > {heading.text}" if parent else heading.text)
        return tuple(paths)


def parse_article(text: str) -> Article:
    match = _FRONT_MATTER.match(text)
    if match is None:
        raise ArticleFormatError("an Article must start with a `---` front-matter block")
    try:
        front_matter = FrontMatter.model_validate(yaml.safe_load(match.group(1)))
    except (yaml.YAMLError, ValidationError) as error:
        raise ArticleFormatError(f"invalid front-matter: {error}") from error
    body = text[match.end() :]
    return Article(front_matter=front_matter, body=body, headings=_headings(body))


def _headings(body: str) -> tuple[Heading, ...]:
    headings: list[Heading] = []
    in_fence = False
    for line in body.splitlines():
        if _FENCE.match(line):
            in_fence = not in_fence
        elif not in_fence and (match := _HEADING.match(line)):
            headings.append(Heading(level=len(match.group(1)), text=match.group(2)))
    return tuple(headings)
