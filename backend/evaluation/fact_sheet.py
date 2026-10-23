"""The Nimbus fact sheet: planted facts the Knowledge Base must state and topics it must not."""

import re
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from evaluation.knowledge_base import REPO_ROOT, PlatformVersion

FACT_SHEET_PATH = REPO_ROOT / "eval" / "corpus" / "fact-sheet.yaml"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PlantedFact(_Strict):
    id: str
    article: str  # the planted Article that states it
    statement: str
    verbatim: list[str] = Field(min_length=1)  # literal strings the Article must contain


class ForbiddenTopic(_Strict):
    id: str
    description: str
    terms: list[str] = Field(min_length=1)  # mentioning any one of these is a violation


class ConflictRule(_Strict):
    """A statement-level check that no generated Article contradicts a planted value.

    The rule reads each statement that matches every `when` pattern, in an Article whose Platform
    Versions are all in `versions`. Every match of `value` must then be in `allowed`, or the
    statement must match `requires`.
    """

    id: str
    facts: list[str]  # the planted facts it protects, for traceability
    versions: list[PlatformVersion] = Field(min_length=1)
    when: list[str] = Field(min_length=1)
    value: str | None = None
    allowed: list[str] = []
    requires: str | None = None

    @model_validator(mode="after")
    def _one_check(self) -> Self:
        if (self.value is None) == (self.requires is None):
            raise ValueError(f"{self.id}: a rule has either `value` (+ `allowed`) or `requires`")
        if self.requires is not None and self.allowed:
            raise ValueError(f"{self.id}: `allowed` goes with `value`, not `requires`")
        for pattern in (*self.when, self.value or "", self.requires or ""):
            re.compile(pattern)
        return self


class FactSheet(BaseModel):
    """Only the parts the checks read; the rest of the sheet is prose input for the generator."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    planted_facts: list[PlantedFact]
    forbidden_topics: list[ForbiddenTopic]
    conflict_rules: list[ConflictRule]


def load_fact_sheet(path: Path = FACT_SHEET_PATH) -> FactSheet:
    return FactSheet.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def mentions(text: str, term: str) -> bool:
    """Case-insensitive, and a space in the term matches any run of whitespace (wrapped lines).

    A term that starts or ends with a word character must match there at a word boundary.
    """
    pattern = r"\s+".join(re.escape(word) for word in term.split())
    if re.match(r"\w", term):
        pattern = r"\b" + pattern
    if re.search(r"\w$", term):
        pattern += r"\b"
    return re.search(pattern, text, re.IGNORECASE) is not None
