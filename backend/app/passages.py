"""The Passage: a verbatim excerpt of one Section, the unit the assistant retrieves and cites.

Framework-free domain types, shared by retrieval, the prompts and answer assembly.
"""

from dataclasses import dataclass
from typing import Literal, Protocol

type PlatformVersion = Literal["v2", "v3"]
type ArticleStatus = Literal["current", "deprecated"]


@dataclass(frozen=True, slots=True, kw_only=True)
class ArticleRef:
    id: str
    title: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SectionRef:
    id: str
    """Stable slug; the same one the Article endpoint uses, so click-through can scroll to it."""
    path: tuple[str, ...]
    """Heading path, starting with the Article title."""


@dataclass(frozen=True, slots=True, kw_only=True)
class Passage:
    id: str
    article: ArticleRef
    section: SectionRef
    text: str
    """Verbatim, exactly as the model was shown it."""
    applies_to: tuple[PlatformVersion, ...]
    status: ArticleStatus
    score: float
    """Dense cosine similarity to the Standalone Question; drives the retrieval gate."""


class PassageRetriever(Protocol):
    async def retrieve(self, question: str) -> tuple[Passage, ...]:
        """The Passages most relevant to a Standalone Question, best first, at most `top_k`.

        Each carries its dense cosine score, whatever ranked it. Raises
        `AppError("retrieval_unavailable")` when the Passage store can't be reached.
        """
        ...
