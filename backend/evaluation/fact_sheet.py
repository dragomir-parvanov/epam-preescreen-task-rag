"""The Nimbus fact sheet: planted facts the Knowledge Base must state and topics it must not."""

import re
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from evaluation.knowledge_base import REPO_ROOT

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


class FactSheet(BaseModel):
    """Only the parts the checks read; the rest of the sheet is prose input for the generator."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    planted_facts: list[PlantedFact]
    forbidden_topics: list[ForbiddenTopic]


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
