"""The corpus generator (#12, #34): writes the 145 generated Articles and their Golden Questions.

Run by hand, never in CI, at startup or by ingestion, which only read the committed files:

    pixi run generate-corpus run [--missing] [--only <id> ...]  # calls Claude (ANTHROPIC_API_KEY)
    pixi run generate-corpus prompts <dir> [--only <id> ...]    # writes the prompts, calls nothing
    pixi run generate-corpus ingest <dir> [--check] [--only ..] # reviews <dir>/<id>.md replies
    pixi run generate-corpus status                             # planned Articles not on disk yet

For each Article in `eval/corpus/articles.yaml` it builds a prompt from the Nimbus fact sheet, the
Article's family skeleton and brief, reviews the reply (shape, family skeleton, links, the corpus
lint, Golden Questions grounded in the cited Sections), and only then writes
`knowledge-base/<id>.md` and merges the Article's Golden Questions into
`eval/golden-questions.yaml` with `origin: generated`, leaving the curated entries untouched.
`run` sends a rejected reply back with the problems, up to `--attempts` times.

Committed run: 2026-10-23, model `claude-opus-5-5`. No API key was available to that session, so
the prompts were written with `prompts`, answered by Claude Opus 5.5 subagents in Claude Code (one
per batch of Articles), and the replies went through `ingest`, the same review `run` applies.
One more subagent pass made the replies agree on details the fact sheet left open (now its
`settled_details`), and 6 generated Golden Questions were edited by hand in the spot check (#34).
"""

import argparse
import os
import re
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from evaluation.corpus_lint import lint_article
from evaluation.fact_sheet import FACT_SHEET_PATH, FactSheet, load_fact_sheet, mentions
from evaluation.golden import GOLDEN_QUESTIONS_PATH, parse_golden_questions
from evaluation.knowledge_base import (
    KNOWLEDGE_BASE_DIR,
    REPO_ROOT,
    Article,
    ArticleFormatError,
    PlatformVersion,
    parse_article,
)

PLAN_PATH = REPO_ROOT / "eval" / "corpus" / "articles.yaml"
MODEL = "claude-opus-5-5"
GENERATED_MARKER = (
    "# --- Generated (#34) ------------------------------------------------------------------\n"
    "# Written by `pixi run generate-corpus` with each generated Article: one or two single-turn\n"
    "# questions answered by that Article alone. Regenerating an Article replaces its entries.\n"
)
MIN_WORDS, MAX_WORDS = 800, 1500
MIN_SECTIONS, MAX_SECTIONS = 4, 8

_LINK = re.compile(r"\]\(([^)#\s]+)\.md(?:#[^)]*)?\)")
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_TAGGED = re.compile(r"<(article|golden_questions)>\s*\n(.*?)\n\s*</\1>", re.DOTALL)


# --- The plan -----------------------------------------------------------------------------------


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Family(_Strict):
    doc_type: Literal["guide", "reference", "release-notes"]
    owner: str
    max_h3: int = Field(ge=0)
    sections: list[str] = Field(min_length=MIN_SECTIONS - 2, max_length=MAX_SECTIONS)
    guidance: str


class ArticleSpec(_Strict):
    id: str = Field(pattern=r"^nimbus-[a-z0-9]+(?:-[a-z0-9]+)*$")
    family: str
    title: str
    applies_to: list[PlatformVersion] = ["v3"]
    last_updated: date
    brief: str

    @property
    def status(self) -> Literal["current", "deprecated"]:
        return "deprecated" if self.applies_to == ["v2"] else "current"

    @property
    def slug(self) -> str:
        return self.id.removeprefix("nimbus-")


class Plan(_Strict):
    families: dict[str, Family]
    articles: list[ArticleSpec]

    def family(self, spec: ArticleSpec) -> Family:
        return self.families[spec.family]

    def spec(self, article_id: str) -> ArticleSpec:
        for spec in self.articles:
            if spec.id == article_id:
                return spec
        raise KeyError(f"{article_id} isn't in {PLAN_PATH.name}")

    def linkable(self, spec: ArticleSpec, planted: dict[str, str]) -> dict[str, str]:
        """Article ids and titles `spec` may link to: planted, its family and earlier families."""
        order = list(self.families)
        reach = set(order[: order.index(spec.family) + 1])
        titles = dict(planted)
        titles.update(
            (other.id, other.title)
            for other in self.articles
            if other.family in reach and other.id != spec.id
        )
        return titles


def load_plan(path: Path = PLAN_PATH) -> Plan:
    plan = Plan.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    ids = [spec.id for spec in plan.articles]
    unknown = sorted({spec.family for spec in plan.articles} - set(plan.families))
    if unknown or len(set(ids)) != len(ids):
        raise ValueError(f"{path.name}: unknown families {unknown} or duplicate Article ids")
    return plan


def planted_titles(directory: Path, fact_sheet: FactSheet) -> dict[str, str]:
    planted = sorted({fact.article for fact in fact_sheet.planted_facts})
    return {
        article_id: parse_article(
            (directory / f"{article_id}.md").read_text(encoding="utf-8")
        ).front_matter.title
        for article_id in planted
    }


# --- Prompts --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Prompt:
    system: str  # the same for every Article, so it can be cached
    user: str


SYSTEM_PROMPT = """\
You write Articles for the internal knowledge base of OmniCorp Nimbus, a fictional B2B workflow and
integration platform. Customer Success Managers (CSMs) read them to answer client questions, and a
retrieval assistant cites them Section by Section. Write like a real product manual: concrete,
specific and plain, in British-leaning technical English, with the console paths, field names,
error codes and API paths a CSM would quote. No marketing language, no filler, no "In this article
we will".

## The facts you write from

The Nimbus fact sheet below is canon. State only values that are in it or that follow from it.
Where the Article needs a detail the sheet doesn't give (a field name, a step in a third-party
app's own console, an issue id in release notes), invent one that is plausible and consistent with
the sheet, and never contradict the sheet.

<fact_sheet>
{fact_sheet}
</fact_sheet>

## Rules that are checked automatically

A reply that breaks any of these is rejected and sent back.

1. Never mention a forbidden topic, not even to say it isn't supported. Not one of these terms may
   appear anywhere, matched case-insensitively as whole words: {forbidden_terms}.
   In particular: no prices or costs and no `$`, `€` or `£` character at all (write expressions as
   {{{{...}}}}, shell prompts without `$`, JSONPath without `$`); no LDAP or Active Directory; no
   Google identity products; no network addresses, address ranges or firewall allowlists (say
   "the private connector agent" or "outbound TLS" instead); no identity providers other than Okta
   and Microsoft Entra ID; no Platform Versions other than v2 and v3 (no `v1` anywhere, not even in
   a third-party URL such as an API path, and no "Nimbus 1" or "Nimbus 4"); no SAML logout; no
   uptime, availability percentages or SLAs (not even a ticketing tool's own SLA fields).
2. Don't restate the planted facts below. They live in five hand-written Articles; link to that
   Article instead (e.g. "see [Configuring SSO with SAML 2.0](nimbus-sso-saml.md)").
   {planted_statements}
3. If a sentence, list item, table row or code line still touches one of those subjects, it must
   agree with the planted value. The checks are strict and work per statement:
   - a statement that mentions SCIM names no Plan Tier but Enterprise (no "Starter", "Business",
     "all tiers"), and gives no interval other than "every 40 minutes";
   - a statement with a request rate ("N req/min", "N requests per minute/second/hour/day") gives
     only 600, 1,200, 3,000 or 6,000 on v3 (300 on v2), with Business only 600 or 1,200, Enterprise
     only 3,000 or 6,000, and Starter none. So don't quote third-party API request rates at all;
   - a statement about bursts gives only {times}2 and 10 s;
   - webhook signatures: on v3 only `X-Nimbus-Signature-256` and SHA-256; on v2 only
     `X-Nimbus-Signature` and SHA-1;
   - the SAML email attribute is `email` on v3 and `mail` on v2;
   - a statement that mentions the audit log and a number of days gives only 30, 90 or 365, matched
     to Starter, Business and Enterprise; better, give no retention period at all;
   - a statement that mentions deprovisioning, suspension or deactivation and a number of days gives
     only 30, so never put another day count in a sentence about suspended users;
   - never mention the error codes AUTH-401, AUTH-403 or AUTH-409, and invent no other AUTH- codes;
   - APAC is named only together with Enterprise.
4. A v2 Article (applies_to [v2]) states its facts plainly, like the legacy reference: never write
   "in v2", "on v2", "for v2", "under v2" or "with v2" in prose; its metadata says the version.
   It describes only the legacy platform (fact_sheet.v2_details), and any SCIM, burst, APAC,
   rate-limit header or auto-disable mention must say it is absent.

## Shape

- Markdown body only: no front-matter, no H1, no title line. Start with one or two intro paragraphs,
  then the family's H2 Sections, with exactly the H2 headings given, in the given order. You may add
  a few H3 Sections under them where noted. Headings are short and plain.
- {min_words}-{max_words} words in all (aim for 1,000-1,250), {min_sections}-{max_sections} H2/H3
  Sections in all.
- Mix prose with at least one table, at least one numbered list starting `1. `, and at least one
  fenced code or config block (HTTP, JSON, YAML, SQL, bash, Python, cron). Write each paragraph on
  one line.
- Links to other Articles are relative: `[Title](article-id.md)`, only to the Article ids you are
  given. Link where it genuinely helps, typically 1-4 times.

## Golden Questions

After the Article, write 2 questions a CSM would really type that this Article alone answers, each
from one or two of its Sections. Name the specific subject (the connector, feature, endpoint or
release) so the question can't be answered by a sibling Article with the same headings. Vary the
form: a how-to, a fact lookup, a "what happens when". Never ask about a forbidden topic.
For each give:
- `sections`: the Section paths that answer it, as `H2` or `H2 > H3`, exactly as in the Article;
- `expected_facts`: one or two short notes of the expected answer;
- `must_mention`: one to three term groups; a group is a list of alternative spellings, any one of
  which counts, and every term must appear verbatim (case-insensitive) in the text of the cited
  Sections themselves, not only in their headings.

## Reply format

Reply with exactly these two blocks and nothing else:

<article>
...the markdown body...
</article>
<golden_questions>
- question: ...
  sections: [...]
  expected_facts: [...]
  must_mention: [[...], [...]]
</golden_questions>
"""


def build_prompt(
    spec: ArticleSpec,
    plan: Plan,
    fact_sheet: FactSheet,
    fact_sheet_text: str,
    planted: dict[str, str],
) -> Prompt:
    terms = sorted({term for topic in fact_sheet.forbidden_topics for term in topic.terms})
    planted_lines = "\n   ".join(
        f"- {fact.statement} ({fact.article})" for fact in fact_sheet.planted_facts
    )
    system = SYSTEM_PROMPT.format(
        fact_sheet=fact_sheet_text.strip(),
        forbidden_terms=", ".join(f'"{term}"' for term in terms),
        planted_statements=planted_lines,
        min_words=MIN_WORDS,
        max_words=MAX_WORDS,
        min_sections=MIN_SECTIONS,
        max_sections=MAX_SECTIONS,
        times="\u00d7",
    )
    family = plan.family(spec)
    links = "\n".join(
        f"- {aid}: {title}" for aid, title in sorted(plan.linkable(spec, planted).items())
    )
    headings = "\n".join(f"{n}. ## {heading}" for n, heading in enumerate(family.sections, 1))
    user = f"""\
Write the Article `{spec.id}`.

Title: {spec.title}
Platform Versions: {", ".join(spec.applies_to)} ({spec.status})
Family: {spec.family} ({family.doc_type}, owned by the {family.owner})
Last updated: {spec.last_updated}

What it covers: {spec.brief}

The family's H2 Sections, exactly and in this order (up to {family.max_h3} extra H3 Sections):
{headings}

How the family uses them: {family.guidance}

Article ids you may link to:
{links}
"""
    return Prompt(system=system, user=user)


# --- Replies --------------------------------------------------------------------------------------


class ReplyFormatError(ValueError):
    """The reply isn't an <article> block followed by a <golden_questions> YAML block."""


class DraftQuestion(_Strict):
    question: str = Field(min_length=10)
    sections: list[str] = Field(min_length=1)
    expected_facts: list[str] = Field(min_length=1)
    must_mention: list[list[str]] = Field(min_length=1, max_length=4)


@dataclass(frozen=True)
class Draft:
    body: str
    questions: tuple[DraftQuestion, ...]


def parse_reply(text: str) -> Draft:
    blocks = {match.group(1): match.group(2) for match in _TAGGED.finditer(text)}
    if set(blocks) != {"article", "golden_questions"}:
        raise ReplyFormatError("reply with an <article> block and a <golden_questions> block")
    try:
        raw = yaml.safe_load(blocks["golden_questions"])
        if not isinstance(raw, list):
            raise ReplyFormatError("<golden_questions> must hold a YAML list")
        questions = tuple(DraftQuestion.model_validate(item) for item in raw)  # type: ignore[reportUnknownVariableType]
    except (yaml.YAMLError, ValidationError) as error:
        raise ReplyFormatError(f"invalid <golden_questions>: {error}") from error
    return Draft(body=blocks["article"].strip() + "\n", questions=questions)


def render_article(spec: ArticleSpec, plan: Plan, body: str) -> str:
    family = plan.family(spec)
    front_matter = (
        "---\n"
        f"id: {spec.id}\n"
        f"title: {spec.title}\n"
        "product: OmniCorp Nimbus\n"
        f"applies_to: [{', '.join(spec.applies_to)}]\n"
        f"doc_type: {family.doc_type}\n"
        f"status: {spec.status}\n"
        f"last_updated: {spec.last_updated}\n"
        f"owner: {family.owner}\n"
        "---\n\n"
    )
    return front_matter + body.strip() + "\n"


# --- Review ---------------------------------------------------------------------------------------


def review(
    spec: ArticleSpec, draft: Draft, plan: Plan, fact_sheet: FactSheet, planted: dict[str, str]
) -> list[str]:
    """Every reason not to accept `draft` for `spec`; empty when it can be written."""
    try:
        article = parse_article(render_article(spec, plan, draft.body))
    except ArticleFormatError as error:
        return [str(error)]
    problems = shape_problems(article, plan.family(spec))
    linkable = plan.linkable(spec, planted)
    problems += [
        f"link to {target}.md, which isn't an Article you may link to"
        for target in _LINK.findall(article.body)
        if target not in linkable
    ]
    problems += [f"lint: {violation}" for violation in lint_article(article, fact_sheet)]
    problems += question_problems(article, draft.questions, fact_sheet)
    return problems


def shape_problems(article: Article, family: Family) -> list[str]:
    problems: list[str] = []
    body = article.body
    words = len(body.split())
    if not MIN_WORDS <= words <= MAX_WORDS:
        problems.append(f"{words} words; write {MIN_WORDS}-{MAX_WORDS}")
    levels = [heading.level for heading in article.headings]
    if set(levels) - {2, 3}:
        problems.append("use only H2 and H3 headings (no H1: the title is in the front-matter)")
    paths = article.section_paths
    if not MIN_SECTIONS <= len(paths) <= MAX_SECTIONS:
        problems.append(f"{len(paths)} Sections; write {MIN_SECTIONS}-{MAX_SECTIONS} of H2/H3")
    if len(set(paths)) != len(paths):
        problems.append("two Sections have the same heading path")
    h2s = [heading.text for heading in article.headings if heading.level == 2]
    if h2s != family.sections:
        problems.append(f"the H2 headings must be exactly {family.sections}, in order; got {h2s}")
    h3s = sum(1 for level in levels if level == 3)
    if h3s > family.max_h3:
        problems.append(f"{h3s} H3 Sections; this family allows {family.max_h3}")
    if not re.search(r"^\|[ :-]*-{3,}", body, re.MULTILINE):
        problems.append("add a markdown table")
    if not re.search(r"^1\. ", body, re.MULTILINE):
        problems.append("add a numbered list starting `1. `")
    if not re.search(r"^```", body, re.MULTILINE):
        problems.append("add a fenced code or config block")
    return problems


def section_texts(article: Article) -> dict[str, str]:
    """Each Section path's own text, without its heading and without its H3 sub-Sections."""
    texts: dict[str, list[str]] = {}
    current: list[str] | None = None
    parent = ""
    in_fence = False
    for line in article.body.splitlines():
        if _FENCE.match(line):
            in_fence = not in_fence
        match = None if in_fence else _HEADING.match(line)
        if match and len(match.group(1)) in (2, 3):
            text = match.group(2)
            if len(match.group(1)) == 2:
                parent, path = text, text
            else:
                path = f"{parent} > {text}"
            current = texts.setdefault(path, [])
        elif current is not None:
            current.append(line)
    return {path: "\n".join(lines) for path, lines in texts.items()}


def question_problems(
    article: Article, questions: Sequence[DraftQuestion], fact_sheet: FactSheet
) -> list[str]:
    if not 1 <= len(questions) <= 2:
        return [f"{len(questions)} Golden Questions; write 1 or 2"]
    texts = section_texts(article)
    problems: list[str] = []
    for n, question in enumerate(questions, 1):
        unknown = [path for path in question.sections if path not in texts]
        if unknown:
            problems.append(f"question {n}: no Section path {unknown}; use one of {list(texts)}")
            continue
        cited = "\n".join(texts[path] for path in question.sections).casefold()
        problems += [
            f"question {n}: none of {group} appears in the text of {question.sections}"
            for group in question.must_mention
            if not group or not any(term.casefold() in cited for term in group)
        ]
        problems += [
            f"question {n}: mentions the forbidden topic {topic.id} ({term!r})"
            for topic in fact_sheet.forbidden_topics
            for term in topic.terms
            if mentions(question.question, term)
        ]
    return problems


# --- Golden Questions -----------------------------------------------------------------------------


def golden_entries(spec: ArticleSpec, draft: Draft) -> list[dict[str, Any]]:
    return [
        {
            "id": f"gq-{spec.slug}-{n}",
            "question": question.question,
            "category": "single-article",
            "answerable": True,
            "origin": "generated",
            "expected_sources": [
                {"article": spec.id, "section": path} for path in question.sections
            ],
            "expected_facts": question.expected_facts,
            "must_mention": question.must_mention,
        }
        for n, question in enumerate(draft.questions, 1)
    ]


def merge_generated(
    existing: str, entries: Iterable[dict[str, Any]], articles: Iterable[str]
) -> str:
    """`existing` with the generated entries of `articles` replaced by `entries`.

    Everything before the generated marker (the curated entries and their comments) is kept byte
    for byte. Generated entries of other Articles are kept, and the block is sorted by id.
    """
    curated, marker, generated = existing.partition(GENERATED_MARKER)
    kept: list[dict[str, Any]] = []
    if marker:
        loaded: Any = yaml.safe_load(generated) or []
        replaced = set(articles)
        kept = [
            entry for entry in loaded if entry["expected_sources"][0]["article"] not in replaced
        ]
    merged = sorted([*kept, *entries], key=lambda entry: str(entry["id"]))
    parse_golden_questions(merged)  # rejects duplicate ids and schema breaks before writing
    rendered = "\n".join(_render(entry) for entry in merged)
    return curated.rstrip("\n") + "\n\n" + GENERATED_MARKER + "\n" + rendered


def _render(entry: dict[str, Any]) -> str:
    """One entry in the curated entries' style: block keys, flow-style sources and term groups."""

    def flow(value: Any) -> str:
        return yaml.safe_dump(
            value, default_flow_style=True, allow_unicode=True, width=1000, sort_keys=False
        ).strip()

    def scalar(value: Any) -> str:
        text = yaml.safe_dump(value, allow_unicode=True, width=1000)
        return text.removesuffix("\n").removesuffix("\n...")

    lines: list[str] = []
    for key, value in entry.items():
        prefix = "- " if not lines else "  "
        if isinstance(value, list):
            items = cast(list[Any], value)
            lines.append(f"{prefix}{key}:")
            lines += [
                f"    - {flow(item) if isinstance(item, dict | list) else scalar(item)}"
                for item in items
            ]
        else:
            lines.append(f"{prefix}{key}: {scalar(value)}")
    return "\n".join(lines) + "\n"


# --- Running it ---------------------------------------------------------------------------------


Complete = Callable[[Prompt, Sequence[tuple[str, str]]], str]
"""Sends a prompt (plus earlier (reply, feedback) turns) to the model and returns its reply."""


@dataclass
class Corpus:
    plan: Plan
    fact_sheet: FactSheet
    fact_sheet_text: str
    planted: dict[str, str]
    knowledge_base: Path
    golden_path: Path

    @classmethod
    def load(cls) -> "Corpus":
        fact_sheet = load_fact_sheet()
        return cls(
            plan=load_plan(),
            fact_sheet=fact_sheet,
            fact_sheet_text=FACT_SHEET_PATH.read_text(encoding="utf-8"),
            planted=planted_titles(KNOWLEDGE_BASE_DIR, fact_sheet),
            knowledge_base=KNOWLEDGE_BASE_DIR,
            golden_path=GOLDEN_QUESTIONS_PATH,
        )

    def prompt(self, spec: ArticleSpec) -> Prompt:
        return build_prompt(spec, self.plan, self.fact_sheet, self.fact_sheet_text, self.planted)

    def review(self, spec: ArticleSpec, reply: str) -> tuple[Draft | None, list[str]]:
        try:
            draft = parse_reply(reply)
        except ReplyFormatError as error:
            return None, [str(error)]
        return draft, review(spec, draft, self.plan, self.fact_sheet, self.planted)

    def write(self, accepted: dict[str, Draft]) -> None:
        entries: list[dict[str, Any]] = []
        for article_id, draft in accepted.items():
            spec = self.plan.spec(article_id)
            (self.knowledge_base / f"{spec.id}.md").write_text(
                render_article(spec, self.plan, draft.body), encoding="utf-8"
            )
            entries += golden_entries(spec, draft)
        existing = self.golden_path.read_text(encoding="utf-8")
        self.golden_path.write_text(merge_generated(existing, entries, accepted), encoding="utf-8")


def generate(
    corpus: Corpus, specs: Sequence[ArticleSpec], complete: Complete, attempts: int
) -> int:
    accepted: dict[str, Draft] = {}
    failed: list[str] = []
    for spec in specs:
        prompt = corpus.prompt(spec)
        turns: list[tuple[str, str]] = []
        for attempt in range(1, attempts + 1):
            reply = complete(prompt, turns)
            draft, problems = corpus.review(spec, reply)
            if draft is not None and not problems:
                accepted[spec.id] = draft
                print(f"ok      {spec.id} (attempt {attempt})")
                break
            print(f"retry   {spec.id}: {len(problems)} problems", file=sys.stderr)
            turns.append((reply, _feedback(problems)))
        else:
            failed.append(spec.id)
            print(f"FAILED  {spec.id}: {turns[-1][1]}", file=sys.stderr)
        if spec.id in accepted:
            corpus.write({spec.id: accepted[spec.id]})
    return 1 if failed else 0


def _feedback(problems: Sequence[str]) -> str:
    listed = "\n".join(f"- {problem}" for problem in problems)
    return f"The reply was rejected. Fix every problem and reply again in full:\n{listed}"


def claude(model: str) -> Complete:  # pragma: no cover - the one part that calls the real API
    import anthropic

    client = anthropic.Anthropic()

    def complete(prompt: Prompt, turns: Sequence[tuple[str, str]]) -> str:
        messages: list[anthropic.types.MessageParam] = [{"role": "user", "content": prompt.user}]
        for reply, feedback in turns:
            messages.append({"role": "assistant", "content": reply})
            messages.append({"role": "user", "content": feedback})
        with client.messages.stream(
            model=model,
            max_tokens=32000,
            system=[
                {"type": "text", "text": prompt.system, "cache_control": {"type": "ephemeral"}}
            ],
            messages=messages,
            output_config={"effort": "high"},
        ) as stream:
            message = stream.get_final_message()
        if message.stop_reason != "end_turn":
            raise RuntimeError(f"the model stopped with {message.stop_reason}")
        return "".join(block.text for block in message.content if block.type == "text")

    return complete


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="generate-corpus", description="Generate the corpus (#34)."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="generate Articles with Claude (needs ANTHROPIC_API_KEY)")
    run.add_argument("--model", default=MODEL)
    run.add_argument("--attempts", type=int, default=3)
    run.add_argument("--missing", action="store_true", help="only Articles not on disk yet")
    prompts = commands.add_parser("prompts", help="write each Article's prompt to a directory")
    prompts.add_argument("directory", type=Path)
    ingest = commands.add_parser("ingest", help="review and write replies saved as <dir>/<id>.md")
    ingest.add_argument("directory", type=Path)
    ingest.add_argument("--check", action="store_true", help="review only; write nothing")
    commands.add_parser("status", help="list planned Articles that aren't on disk yet")
    for command in (run, prompts, ingest):
        command.add_argument("--only", nargs="+", metavar="ARTICLE_ID")
    args = parser.parse_args(argv)

    corpus = Corpus.load()
    specs = (
        [corpus.plan.spec(aid) for aid in args.only]
        if getattr(args, "only", None)
        else list(corpus.plan.articles)
    )
    if args.command == "status":
        missing = [s.id for s in specs if not (corpus.knowledge_base / f"{s.id}.md").exists()]
        print("\n".join(missing) or f"all {len(specs)} planned Articles are on disk")
        return 0
    if args.command == "prompts":
        args.directory.mkdir(parents=True, exist_ok=True)
        (args.directory / "system.md").write_text(corpus.prompt(specs[0]).system, encoding="utf-8")
        for spec in specs:
            (args.directory / f"{spec.id}.prompt.md").write_text(
                corpus.prompt(spec).user, encoding="utf-8"
            )
        print(f"wrote system.md and {len(specs)} prompts to {args.directory}")
        return 0
    if args.command == "ingest":
        return _ingest(corpus, specs, args.directory, write=not args.check)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("set ANTHROPIC_API_KEY to generate Articles", file=sys.stderr)
        return 2
    if args.missing:
        specs = [s for s in specs if not (corpus.knowledge_base / f"{s.id}.md").exists()]
    return generate(corpus, specs, claude(args.model), args.attempts)


def _ingest(corpus: Corpus, specs: Sequence[ArticleSpec], directory: Path, *, write: bool) -> int:
    accepted: dict[str, Draft] = {}
    failed = 0
    for spec in specs:
        path = directory / f"{spec.id}.md"
        if not path.exists():
            continue
        draft, problems = corpus.review(spec, path.read_text(encoding="utf-8"))
        if draft is None or problems:
            failed += 1
            print(f"REJECTED {spec.id}\n" + "\n".join(f"  - {p}" for p in problems))
        else:
            accepted[spec.id] = draft
            print(f"ok       {spec.id}")
    if write and accepted:
        corpus.write(accepted)
    verb = "wrote" if write else "accepted"
    print(f"{verb} {len(accepted)} Articles; {failed} rejected")
    return 1 if failed or not accepted else 0


if __name__ == "__main__":
    raise SystemExit(main())
