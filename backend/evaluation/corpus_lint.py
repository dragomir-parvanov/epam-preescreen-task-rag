"""The corpus lint: what a generated Article must never say (#34).

A generated Article fails the lint if it mentions a forbidden topic, states a value that
contradicts a planted fact (the `conflict_rules` in the fact sheet), or, when it applies to v2
only, frames its facts as "in v2" instead of leaving that to its front-matter. The planted
Articles are written by hand and checked by their own tests instead.
"""

import re

from evaluation.fact_sheet import ConflictRule, FactSheet, mentions
from evaluation.knowledge_base import Article

_FENCE = re.compile(r"^\s*(```|~~~)")
_BLOCK_START = re.compile(r"^\s*(?:#{1,6}\s|[-*+]\s|\d+\.\s|>|\|)")
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9`*\[(\"])")
_VERSION_FRAMING = re.compile(r"\b(?:in|on|for|under|with) v2\b", re.IGNORECASE)


def lint_article(article: Article, fact_sheet: FactSheet) -> list[str]:
    """Every violation in `article`, as messages naming the topic or rule; empty when clean."""
    text = f"{article.front_matter.title}\n{article.body}"
    found = [
        f"forbidden topic {topic.id}: {term!r}"
        for topic in fact_sheet.forbidden_topics
        for term in topic.terms
        if mentions(text, term)
    ]
    versions = set(article.front_matter.applies_to)
    rules = [rule for rule in fact_sheet.conflict_rules if versions <= set(rule.versions)]
    for statement in statements(article.body):
        found.extend(message for rule in rules for message in _check(rule, statement))
    if versions == {"v2"}:
        prose = "\n".join(line for line in article.body.splitlines() if not line.startswith("#"))
        found.extend(f"version framing: {m!r}" for m in _VERSION_FRAMING.findall(prose))
    return found


def statements(markdown: str) -> list[str]:
    """The units a conflict rule reads: prose sentences, list items, table rows and code lines."""
    found: list[str] = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            found.extend(_SENTENCE_BREAK.split(" ".join(paragraph)))
            paragraph.clear()

    in_fence = False
    for line in markdown.splitlines():
        stripped = line.strip()
        if _FENCE.match(line):
            flush()
            in_fence = not in_fence
        elif in_fence or stripped.startswith("|"):
            flush()
            if stripped:
                found.append(stripped)
        elif not stripped or _BLOCK_START.match(line):
            flush()
            if stripped:
                paragraph.append(stripped)
        else:
            paragraph.append(stripped)
    flush()
    return found


def _check(rule: ConflictRule, statement: str) -> list[str]:
    if not all(re.search(pattern, statement, re.IGNORECASE) for pattern in rule.when):
        return []
    if rule.requires is not None:
        if re.search(rule.requires, statement, re.IGNORECASE):
            return []
        return [f"conflict {rule.id}: {statement!r}"]
    assert rule.value is not None
    allowed = {_normalized(value) for value in rule.allowed}
    return [
        f"conflict {rule.id}: {match.group(0)!r} in {statement!r}"
        for match in re.finditer(rule.value, statement, re.IGNORECASE)
        if _normalized(match.group(0)) not in allowed
    ]


def _normalized(value: str) -> str:
    return re.sub(r"[\s,-]", "", value).casefold()
