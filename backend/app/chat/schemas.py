"""Wire schemas for `POST /chat`: the request, the stream events and the result they carry.

Every union is discriminated on `type`, and every field is snake_case with no aliases, so the
generated TS types mirror the wire exactly. The `type` aliases below become named OpenAPI
components (`ChatResult`, `ChatStreamEvent`), and from there named TS types.

The domain types (`app.passages`, `app.answer_assembly`) stay framework-free; `chat_result` maps
a domain `Reply` onto the wire.
"""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field

from app import answer_assembly, passages
from app.errors import ErrorBody

QUESTION_MAX_CHARS = 2_000
HISTORY_ANSWER_MAX_CHARS = 20_000
HISTORY_MAX_TURNS = 20


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank")
    return value


# --- request ---


class HistoryTurn(BaseModel):
    """An earlier Turn of the Conversation, as the client remembers it."""

    question: Annotated[str, Field(max_length=QUESTION_MAX_CHARS)]
    answer: Annotated[str, Field(max_length=HISTORY_ANSWER_MAX_CHARS)]
    """The final Answer or Refusal text, without Citation payloads."""


class ChatRequest(BaseModel):
    # These caps guard against abuse. They don't shape the prompt: the server still uses only
    # the last few Turns, truncated (ADR-0002).
    question: Annotated[
        str, Field(min_length=1, max_length=QUESTION_MAX_CHARS), AfterValidator(_not_blank)
    ]
    history: Annotated[list[HistoryTurn], Field(max_length=HISTORY_MAX_TURNS)] = []


# --- Passages and Citations ---


class ArticleRef(BaseModel):
    id: str
    title: str


class SectionRef(BaseModel):
    id: str
    """Stable slug, shared with the Article view so Citation click-through can scroll to it."""
    path: list[str]
    """Heading path, starting with the Article title."""


class Passage(BaseModel):
    id: str
    article: ArticleRef
    section: SectionRef
    text: str
    """Verbatim excerpt of the Section."""
    applies_to: list[Literal["v2", "v3"]]
    status: Literal["current", "deprecated"]
    score: float
    """Retrieval score. Returned for debugging and evaluation; the UI doesn't render it."""


class Citation(BaseModel):
    n: int
    """The marker number `[n]` in the final text, renumbered from 1 in order of first use."""
    passage: Passage


# --- result: what `done` carries ---


class Answer(BaseModel):
    type: Literal["answer"] = "answer"
    text: str
    citations: list[Citation]
    retrieved_passages: list[Passage]
    standalone_question: str | None


class UncitedAnswer(BaseModel):
    """An Answer with no valid Citations, shown with a warning (ADR-0001)."""

    type: Literal["uncited_answer"] = "uncited_answer"
    text: str
    retrieved_passages: list[Passage]
    standalone_question: str | None


class Refusal(BaseModel):
    type: Literal["refusal"] = "refusal"
    message: str
    reason: Literal["no_relevant_passages", "not_in_context"]
    retrieved_passages: list[Passage]
    standalone_question: str | None


type ChatResult = Annotated[Answer | UncitedAnswer | Refusal, Field(discriminator="type")]


def wire_passage(passage: passages.Passage) -> Passage:
    return Passage(
        id=passage.id,
        article=ArticleRef(id=passage.article.id, title=passage.article.title),
        section=SectionRef(id=passage.section.id, path=list(passage.section.path)),
        text=passage.text,
        applies_to=list(passage.applies_to),
        status=passage.status,
        score=passage.score,
    )


def chat_result(reply: answer_assembly.Reply, standalone_question: str | None) -> ChatResult:
    """Map what answer assembly decided onto the wire, adding the Turn's Standalone Question."""
    retrieved = [wire_passage(passage) for passage in reply.retrieved_passages]
    match reply:
        case answer_assembly.Answer():
            return Answer(
                text=reply.text,
                citations=[
                    Citation(n=citation.n, passage=wire_passage(citation.passage))
                    for citation in reply.citations
                ],
                retrieved_passages=retrieved,
                standalone_question=standalone_question,
            )
        case answer_assembly.UncitedAnswer():
            return UncitedAnswer(
                text=reply.text,
                retrieved_passages=retrieved,
                standalone_question=standalone_question,
            )
        case answer_assembly.Refusal():
            return Refusal(
                message=reply.message,
                reason=reply.reason,
                retrieved_passages=retrieved,
                standalone_question=standalone_question,
            )


# --- stream events ---


class RewrittenEvent(BaseModel):
    """The Standalone Question a Follow-up Question was rewritten into. Follow-ups only."""

    type: Literal["rewritten"] = "rewritten"
    standalone_question: str


class PassagesEvent(BaseModel):
    """The retrieved Passages, numbered in prompt order. Sent before any token."""

    type: Literal["passages"] = "passages"
    passages: list[Passage]


class TokenEvent(BaseModel):
    """Raw model text. Its markers keep the prompt numbers from `passages`."""

    type: Literal["token"] = "token"
    text: str


class DoneEvent(BaseModel):
    """The authoritative result. It replaces all provisional text streamed before it."""

    type: Literal["done"] = "done"
    result: ChatResult


class ErrorEvent(BaseModel):
    """A failure after the stream has started, when the HTTP status has already gone out."""

    type: Literal["error"] = "error"
    error: ErrorBody


type ChatStreamEvent = Annotated[
    RewrittenEvent | PassagesEvent | TokenEvent | DoneEvent | ErrorEvent,
    Field(discriminator="type"),
]
