import { useId, useState } from "react";
import type { components } from "../api/schema";
import { VersionBadges } from "./PassageRow";
import { passageLocation } from "./passages";

type Passage = components["schemas"]["Passage"];

const QUOTE_PREVIEW_CHARS = 160;

/**
 * A Citation marker in an Answer. Hover or focus shows a quick look at the cited Passage;
 * a click (or Enter) opens the Citation in the list under the Answer.
 */
export function MarkerChip({
  n,
  passage,
  onOpen,
}: {
  n: number;
  passage: Passage | undefined;
  onOpen: () => void;
}) {
  const [peeking, setPeeking] = useState(false);
  const quickLookId = useId();
  const show = () => setPeeking(true);
  const hide = () => setPeeking(false);
  const preview =
    passage && passage.text.length > QUOTE_PREVIEW_CHARS
      ? `${passage.text.slice(0, QUOTE_PREVIEW_CHARS).trimEnd()}…`
      : passage?.text;

  return (
    <span className="relative inline-block" onMouseEnter={show} onMouseLeave={hide}>
      <button
        type="button"
        aria-label={`Citation ${n}`}
        aria-describedby={peeking && passage ? quickLookId : undefined}
        onClick={onOpen}
        onFocus={show}
        onBlur={hide}
        onKeyDown={(event) => {
          if (event.key === "Escape") hide();
        }}
        className="mx-0.5 -translate-y-1 rounded bg-blue-100 px-1 font-mono text-[11px] leading-4 font-semibold text-blue-800 hover:bg-blue-600 hover:text-white focus-visible:outline-2 focus-visible:outline-blue-600"
      >
        {n}
      </button>
      {peeking && passage && (
        <span
          id={quickLookId}
          role="tooltip"
          className="absolute bottom-full left-1/2 z-20 mb-1 block w-80 max-w-[80vw] -translate-x-1/2 rounded-lg border border-slate-200 bg-white p-3 text-left text-xs leading-snug shadow-xl"
        >
          <span className="mb-1 flex flex-wrap items-center gap-1">
            <span className="font-semibold text-slate-900">{passage.article.title}</span>
            <VersionBadges of={passage} />
          </span>
          <span className="mb-1 block text-slate-500">{passageLocation(passage)}</span>
          <span className="block text-slate-700">{preview}</span>
        </span>
      )}
    </span>
  );
}
