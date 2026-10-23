import type { components } from "../api/schema";
import { isV2Only, passageLocation, type OpenSection } from "./passages";

type Passage = components["schemas"]["Passage"];

/** An orange `v2` badge for v2-only content and `Deprecated` for deprecated content. */
export function VersionBadges({ of }: { of: Pick<Passage, "applies_to" | "status"> }) {
  return (
    <>
      {isV2Only(of) && (
        <span className="rounded bg-orange-100 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-orange-800">
          v2
        </span>
      )}
      {of.status === "deprecated" && (
        <span className="rounded bg-orange-600 px-1.5 py-0.5 text-[10px] font-semibold tracking-wide text-white uppercase">
          Deprecated
        </span>
      )}
    </>
  );
}

/**
 * One Passage in a Citations or "Retrieved, not cited" list: its location and badges, which
 * expand to the verbatim quote and an "Open Section" link.
 */
export function PassageRow({
  id,
  passage,
  n,
  expanded,
  onToggle,
  onOpenSection,
}: {
  id?: string;
  passage: Passage;
  /** The Citation number; absent for Passages that weren't cited. */
  n?: number;
  expanded: boolean;
  onToggle: () => void;
  onOpenSection: OpenSection;
}) {
  const quoteId = `${id ?? passage.id}-quote`;
  return (
    <li id={id} className="rounded-md border border-slate-200 bg-white">
      <button
        type="button"
        aria-expanded={expanded}
        aria-controls={quoteId}
        onClick={onToggle}
        className="flex w-full items-start gap-2 rounded-md px-3 py-2 text-left text-sm hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-blue-600"
      >
        {n !== undefined && (
          <span className="mt-0.5 min-w-5 font-mono text-xs font-semibold text-blue-700">{n}</span>
        )}
        <span className="flex-1 text-slate-700">{passageLocation(passage)}</span>
        <span className="flex shrink-0 items-center gap-1">
          <VersionBadges of={passage} />
        </span>
        <span aria-hidden className="text-slate-400">
          {expanded ? "▾" : "▸"}
        </span>
      </button>
      {expanded && (
        <div id={quoteId} className="space-y-2 border-t border-slate-100 px-3 py-2 text-sm">
          <blockquote className="border-l-2 border-slate-300 pl-3 whitespace-pre-wrap text-slate-700">
            {passage.text}
          </blockquote>
          <button
            type="button"
            onClick={() => onOpenSection(passage)}
            className="text-xs font-medium text-blue-700 hover:underline"
          >
            Open Section
          </button>
        </div>
      )}
    </li>
  );
}
