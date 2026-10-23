import { useId, useState } from "react";
import type { components } from "../api/schema";
import type { Turn } from "./conversation";
import { ErrorCard } from "./ErrorCard";
import { Markdown } from "./Markdown";
import { MarkerChip } from "./MarkerChip";
import { stripMarkers } from "./markers";
import { PassageRow, VersionBadges } from "./PassageRow";
import { passageLocation, type OpenSection } from "./passages";

type Answer = components["schemas"]["Answer"];
type Passage = components["schemas"]["Passage"];

/** One Turn, top to bottom: the question, what was searched for, then the reply and its evidence. */
export function TurnView({
  turn,
  canAskAgain,
  onAskAgain,
  onOpenSection,
}: {
  turn: Turn;
  canAskAgain: boolean;
  onAskAgain: (question: string) => void;
  onOpenSection: OpenSection;
}) {
  const headingId = useId();
  const result = turn.result;
  const searchedFor = turn.standaloneQuestion;
  const rewroteIt = searchedFor !== null && searchedFor.trim() !== turn.question.trim();

  return (
    <article aria-labelledby={headingId} className="space-y-3">
      <h2 id={headingId} className="text-lg font-semibold text-slate-900">
        {turn.question}
      </h2>
      {rewroteIt && (
        <p className="text-xs text-slate-500">
          Searched for: <q className="italic">{searchedFor}</q>
        </p>
      )}

      {result === null && <InProgressOrCutShort turn={turn} />}

      {result?.type === "answer" && (
        <CitedAnswer key={turn.id} answer={result} turnId={turn.id} onOpenSection={onOpenSection} />
      )}

      {result?.type === "uncited_answer" && (
        <>
          <div
            role="note"
            className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"
          >
            <strong>Uncited Answer.</strong> The assistant didn't point to any Passage for this.
            Check it against the retrieved Passages below before passing it on.
          </div>
          <div className="text-slate-800">
            <Markdown text={stripMarkers(result.text)} />
          </div>
          <PassageList
            label="Retrieved, not cited"
            passages={result.retrieved_passages}
            onOpenSection={onOpenSection}
          />
        </>
      )}

      {result?.type === "refusal" && (
        <div className="rounded-md border border-slate-200 bg-slate-100 p-3 text-slate-700">
          {result.message}
        </div>
      )}

      {turn.error && (
        <ErrorCard
          error={turn.error}
          disabled={!canAskAgain}
          onAskAgain={() => onAskAgain(turn.question)}
        />
      )}
    </article>
  );
}

function progressLine(turn: Turn): string {
  if (turn.phase === "rewriting") return "Understanding the follow-up…";
  if (turn.phase === "retrieving") return "Searching the Knowledge Base…";
  const found = turn.passages.length;
  return `Found ${found} ${found === 1 ? "Passage" : "Passages"}. Writing the answer…`;
}

const CURSOR =
  "[&>div>:last-child]:after:ml-0.5 [&>div>:last-child]:after:animate-pulse [&>div>:last-child]:after:text-slate-400 [&>div>:last-child]:after:content-['▍']";

/** Before `done`: a status line, then the provisional text with its markers hidden. */
function InProgressOrCutShort({ turn }: { turn: Turn }) {
  const text = stripMarkers(turn.provisionalText);
  const streaming = turn.phase === "generating";

  if (turn.phase === "rewriting" || turn.phase === "retrieving" || (streaming && !text)) {
    return (
      <p role="status" className="animate-pulse text-sm text-slate-500">
        {progressLine(turn)}
      </p>
    );
  }
  if (!text) {
    return turn.phase === "stopped" ? <StoppedLabel /> : null;
  }
  return (
    <>
      {/* While streaming, a cursor follows the last line of text. */}
      <div className={streaming ? `text-slate-800 ${CURSOR}` : "text-slate-400"}>
        <Markdown text={text} />
      </div>
      {turn.phase === "stopped" && <StoppedLabel />}
    </>
  );
}

function StoppedLabel() {
  return <p className="text-xs font-medium tracking-wide text-slate-500 uppercase">Stopped</p>;
}

/** A cited Answer: text with marker chips, its Citations, and every retrieved Passage on demand. */
function CitedAnswer({
  answer,
  turnId,
  onOpenSection,
}: {
  answer: Answer;
  turnId: number;
  onOpenSection: OpenSection;
}) {
  const [expanded, setExpanded] = useState<ReadonlySet<number>>(new Set());
  const [showRetrieved, setShowRetrieved] = useState(false);
  const rowId = (n: number) => `turn-${turnId}-citation-${n}`;
  const citedIds = new Set(answer.citations.map((citation) => citation.passage.id));

  const toggle = (n: number) =>
    setExpanded((open) => {
      const next = new Set(open);
      if (!next.delete(n)) next.add(n);
      return next;
    });
  const openCitation = (n: number) => {
    setExpanded((open) => new Set(open).add(n));
    const row = document.getElementById(rowId(n));
    row?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    row?.querySelector("button")?.focus({ preventScroll: true });
  };

  return (
    <>
      <div className="text-slate-800">
        <Markdown
          text={answer.text}
          renderMarker={(n, key) => (
            <MarkerChip
              key={key}
              n={n}
              passage={answer.citations.find((citation) => citation.n === n)?.passage}
              onOpen={() => openCitation(n)}
            />
          )}
        />
      </div>
      <section className="space-y-2">
        <h3 className="text-xs font-semibold tracking-wide text-slate-500 uppercase">Citations</h3>
        <ol aria-label="Citations" className="space-y-1">
          {answer.citations.map((citation) => (
            <PassageRow
              key={citation.n}
              id={rowId(citation.n)}
              n={citation.n}
              passage={citation.passage}
              expanded={expanded.has(citation.n)}
              onToggle={() => toggle(citation.n)}
              onOpenSection={onOpenSection}
            />
          ))}
        </ol>
        <button
          type="button"
          aria-expanded={showRetrieved}
          onClick={() => setShowRetrieved((show) => !show)}
          className="text-xs text-slate-500 hover:text-slate-800"
        >
          {showRetrieved ? "Hide" : "Show"} all {answer.retrieved_passages.length} retrieved
          Passages
        </button>
        {showRetrieved && (
          <ul aria-label="Retrieved Passages" className="space-y-1 text-xs text-slate-600">
            {answer.retrieved_passages.map((passage) => (
              <li key={passage.id} className="flex flex-wrap items-center gap-1.5">
                <span>{passageLocation(passage)}</span>
                <VersionBadges of={passage} />
                {citedIds.has(passage.id) ? (
                  <span className="rounded bg-blue-50 px-1.5 text-blue-800">cited</span>
                ) : (
                  <span className="rounded bg-slate-100 px-1.5 text-slate-500">not cited</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}

/** Passages shown as expandable rows without numbers: the evidence behind an Uncited Answer. */
function PassageList({
  label,
  passages,
  onOpenSection,
}: {
  label: string;
  passages: Passage[];
  onOpenSection: OpenSection;
}) {
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(new Set());
  const toggle = (id: string) =>
    setExpanded((open) => {
      const next = new Set(open);
      if (!next.delete(id)) next.add(id);
      return next;
    });

  return (
    <section className="space-y-2">
      <h3 className="text-xs font-semibold tracking-wide text-slate-500 uppercase">{label}</h3>
      <ul aria-label={label} className="space-y-1">
        {passages.map((passage) => (
          <PassageRow
            key={passage.id}
            passage={passage}
            expanded={expanded.has(passage.id)}
            onToggle={() => toggle(passage.id)}
            onOpenSection={onOpenSection}
          />
        ))}
      </ul>
    </section>
  );
}
