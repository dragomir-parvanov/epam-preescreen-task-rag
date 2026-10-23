"""The Golden Question schema (#16) and its loader for `eval/golden-questions.yaml`."""

from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from evaluation.knowledge_base import REPO_ROOT

GOLDEN_QUESTIONS_PATH = REPO_ROOT / "eval" / "golden-questions.yaml"

Category = Literal[
    "cross-article",
    "version-conflict",
    "table-lookup",
    "near-duplicate",
    "unanswerable",
    "partial",
    "follow-up",
]

# Any one term in a group counts; every group must be hit. Matched case-insensitively.
TermGroups = list[list[str]]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExpectedSource(_Strict):
    article: str
    section: str  # a Section path, e.g. "Feature matrix" or "Enforcing SSO > Break-glass admin"


class HistoryTurn(_Strict):
    question: str
    answer: str


class GoldenQuestion(_Strict):
    id: str = Field(pattern=r"^gq-[a-z0-9]+(?:-[a-z0-9]+)*$")
    question: str = Field(min_length=1)
    category: Category
    answerable: bool
    origin: Literal["curated", "generated"]
    expected_sources: list[ExpectedSource] = []
    expected_facts: list[str] = []
    must_mention: TermGroups = []
    history: list[HistoryTurn] = []
    standalone_question: str | None = None
    standalone_must_mention: TermGroups = []

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if any(not group for group in (*self.must_mention, *self.standalone_must_mention)):
            raise ValueError("a term group must hold at least one term")
        if self.answerable and not (self.expected_sources and self.must_mention):
            raise ValueError("an answerable question needs expected_sources and must_mention")
        if not self.answerable and (self.expected_sources or self.must_mention):
            raise ValueError("a Refusal cites nothing: drop expected_sources and must_mention")
        if self.category == "unanswerable" and self.answerable:
            raise ValueError("an unanswerable question can't be answerable")
        is_follow_up = self.category == "follow-up"
        has_rewrite = bool(self.history or self.standalone_question or self.standalone_must_mention)
        if is_follow_up and not (self.history and self.standalone_question):
            raise ValueError("a follow-up needs history and a standalone_question")
        if not is_follow_up and has_rewrite:
            raise ValueError("only follow-up questions carry history or a rewrite")
        return self


_GOLDEN_LIST = TypeAdapter(list[GoldenQuestion])


def parse_golden_questions(data: Any) -> list[GoldenQuestion]:
    questions = _GOLDEN_LIST.validate_python(data)
    seen: set[str] = set()
    for question in questions:
        if question.id in seen:
            raise ValueError(f"duplicate Golden Question id: {question.id}")
        seen.add(question.id)
    return questions


def load_golden_questions(path: Path = GOLDEN_QUESTIONS_PATH) -> list[GoldenQuestion]:
    return parse_golden_questions(yaml.safe_load(path.read_text(encoding="utf-8")))
