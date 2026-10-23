"""Passage <-> Haystack Document: the one place that knows the Document meta layout.

A Document's `content` is the Passage text, verbatim, and its JSONB `meta` holds the rest. Only
typed `Passage`s leave the adapter; no `dict[str, Any]` does.
"""

import hashlib
import json
from typing import Any, Final, cast, get_args

from haystack import Document

from app.passages import ArticleRef, ArticleStatus, Passage, PlatformVersion, SectionRef
from app.rag.haystack.embedding import HEADER_FIELD
from app.rag.haystack.splitting import SplitPassage

FINGERPRINT_FIELD: Final = "fingerprint"
_HEADER_JOINER: Final = " > "


def to_document(passage: SplitPassage, *, embedding_model: str) -> Document:
    """The Document to store for `passage`, not yet embedded.

    Its fingerprint hashes everything that goes into the stored row and its embedding: the text,
    the meta and the embedding model. A sync re-embeds a Passage only when it changes.
    """
    meta: dict[str, Any] = {
        "article_id": passage.article.id,
        "article_title": passage.article.title,
        "section_id": passage.section.id,
        "section_path": list(passage.section.path),
        "position": passage.position,
        "applies_to": list(passage.applies_to),
        "status": passage.status,
        HEADER_FIELD: _HEADER_JOINER.join(passage.section.path),
    }
    fingerprint_input = json.dumps(
        [passage.text, meta, embedding_model], sort_keys=True, ensure_ascii=False
    )
    meta[FINGERPRINT_FIELD] = hashlib.sha256(fingerprint_input.encode()).hexdigest()
    return Document(id=passage.id, content=passage.text, meta=meta)


def header_and_text(document: Document) -> str:
    """What both retrieval legs index: `"<Article title> > <Section path>"` + the text."""
    return f"{document.meta[HEADER_FIELD]}\n{document.content or ''}"


def to_passage(document: Document, *, score: float) -> Passage:
    meta = document.meta
    return Passage(
        id=document.id,
        article=ArticleRef(id=_str(meta, "article_id"), title=_str(meta, "article_title")),
        section=SectionRef(
            id=_str(meta, "section_id"), path=tuple(_str_list(meta, "section_path"))
        ),
        text=document.content or "",
        applies_to=tuple(_platform_version(v) for v in _str_list(meta, "applies_to")),
        status=_status(_str(meta, "status")),
        score=score,
    )


def _str(meta: dict[str, Any], key: str) -> str:
    value = meta[key]
    if not isinstance(value, str):
        raise TypeError(f"stored Passage meta {key!r} is not a string: {value!r}")
    return value


def _str_list(meta: dict[str, Any], key: str) -> list[str]:
    value = meta[key]
    if not isinstance(value, list) or not all(isinstance(v, str) for v in cast(list[Any], value)):
        raise TypeError(f"stored Passage meta {key!r} is not a list of strings: {value!r}")
    return cast(list[str], value)


def _platform_version(value: str) -> PlatformVersion:
    if value not in get_args(PlatformVersion.__value__):
        raise TypeError(f"stored Passage has an unknown Platform Version: {value!r}")
    return cast(PlatformVersion, value)


def _status(value: str) -> ArticleStatus:
    if value not in get_args(ArticleStatus.__value__):
        raise TypeError(f"stored Passage has an unknown status: {value!r}")
    return cast(ArticleStatus, value)
