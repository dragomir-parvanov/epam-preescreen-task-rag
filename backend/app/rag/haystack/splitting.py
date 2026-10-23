"""Article -> Passages: one per H2/H3 Section, with long Sections split at block boundaries.

Haystack's `MarkdownHeaderSplitter` does the header split: it is fence-aware, so a `## comment`
inside a code block is not a heading, and it hands back each Section's parent headings. A
Section over `MAX_PASSAGE_WORDS` is then split again here, packing whole markdown blocks
(paragraphs, tables, lists, code blocks) into Passages with no overlap. A block is never cut, so a
single block over the cap becomes one oversized Passage.
"""

import re
from dataclasses import dataclass
from typing import Final

from haystack import Document
from haystack.components.preprocessors import MarkdownHeaderSplitter

from app.knowledge_base import Article, section_ids
from app.passages import ArticleRef, ArticleStatus, PlatformVersion, SectionRef

MAX_PASSAGE_WORDS: Final = 250

_LEADING_H1 = re.compile(r"\A\s*# [^\n]*(?:\n|\Z)")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")


@dataclass(frozen=True, slots=True, kw_only=True)
class SplitPassage:
    """A Passage as cut from its Article: not yet embedded, so not yet scored."""

    id: str
    """`<article-id>#<section-id>-<position>`: stable across edits, so Citation links survive."""
    article: ArticleRef
    section: SectionRef
    position: int
    """1-based, within the Section."""
    text: str
    """Verbatim from the Article, minus surrounding blank lines."""
    applies_to: tuple[PlatformVersion, ...]
    status: ArticleStatus


def split_article(article: Article) -> list[SplitPassage]:
    """The Article's Passages, in document order."""
    sections = _sections(article)
    ids = section_ids(path for path, _ in sections)
    article_ref = ArticleRef(id=article.id, title=article.title)
    return [
        SplitPassage(
            id=f"{article.id}#{section_id}-{position}",
            article=article_ref,
            section=SectionRef(id=section_id, path=(article.title, *path)),
            position=position,
            text=text,
            applies_to=article.applies_to,
            status=article.status,
        )
        for (path, body), section_id in zip(sections, ids, strict=True)
        for position, text in enumerate(_pack_blocks(body), start=1)
    ]


def _sections(article: Article) -> list[tuple[tuple[str, ...], str]]:
    """(heading path below the title, body) per Section that has text; `()` is the intro."""
    splitter = MarkdownHeaderSplitter(header_split_levels=[2, 3], keep_headers=False)
    chunks: list[Document] = splitter.run(documents=[Document(content=article.body)])["documents"]
    sections: list[tuple[tuple[str, ...], str]] = []
    for chunk in chunks:
        header: str = chunk.meta.get("header", "")
        parents: list[str] = chunk.meta.get("parent_headers", [])
        body = chunk.content or ""
        if not header:  # the text before the first H2, or an Article with no H2/H3 at all
            body = _LEADING_H1.sub("", body, count=1)
        if body.strip():
            sections.append(((*parents, header) if header else (), body))
    return sections


def _pack_blocks(text: str) -> list[str]:
    """Greedily pack whole blocks into chunks of at most MAX_PASSAGE_WORDS words."""
    chunks: list[str] = []
    start: int | None = None
    end = 0
    words = 0
    for block_start, block_end in _blocks(text):
        block_words = len(text[block_start:block_end].split())
        if start is not None and words + block_words > MAX_PASSAGE_WORDS:
            chunks.append(text[start:end])
            start = None
        if start is None:
            start, words = block_start, 0
        end = block_end
        words += block_words
    if start is not None:
        chunks.append(text[start:end])
    return chunks


def _blocks(text: str) -> list[tuple[int, int]]:
    """(start, end) offsets of the markdown blocks in `text`, which a split may fall between.

    Blocks are separated by blank lines, except that a fenced code block is one block however
    many blank lines it holds, and a list whose items are separated by blank lines is one block.
    """
    blocks: list[tuple[int, int]] = []
    start: int | None = None
    end = 0
    fence: str | None = None
    offset = 0
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\n")
        stripped = content.strip()
        if fence is not None:
            if stripped.startswith(fence) and set(stripped) == {fence[0]}:
                fence = None
        elif opening := _FENCE.match(content):
            fence = opening[1]
        elif not stripped:
            if start is not None:
                blocks.append((start, end))
                start = None
            offset += len(line)
            continue
        if start is None:
            start = offset
        end = offset + len(content)
        offset += len(line)
    if start is not None:
        blocks.append((start, end))
    return _merge_list_items(text, blocks)


def _merge_list_items(text: str, blocks: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Join a list block with the list items and indented continuations that follow it."""
    merged: list[tuple[int, int]] = []
    for start, end in blocks:
        if merged and _LIST_ITEM.match(text[merged[-1][0] : merged[-1][1]]):
            line = text[start:end]
            if _LIST_ITEM.match(line) or line[:1].isspace():
                merged[-1] = (merged[-1][0], end)
                continue
        merged.append((start, end))
    return merged
