// PROTOTYPE — throwaway. Just-enough markdown (paragraphs, "- " lists, pipe tables, ``` fences,
// `code`) for the fake answers and Passages, with a hook for rendering `[n]` markers.
import type { ReactNode } from "react";
import { splitMarkers } from "./useFakeChat";

type MarkerRenderer = (n: number, key: string) => ReactNode;

function inline(text: string, renderMarker: MarkerRenderer | undefined, key: string): ReactNode[] {
  return splitMarkers(text).flatMap((part, i): ReactNode[] => {
    if (typeof part !== "string") {
      return renderMarker ? [renderMarker(part.marker, `${key}-m${i}`)] : [`[${part.marker}]`];
    }
    return part.split(/(`[^`]+`)/).map((s, j) =>
      s.startsWith("`") && s.endsWith("`") && s.length > 1 ? (
        <code key={`${key}-${i}-${j}`} className="rounded bg-slate-100 px-1 font-mono text-[0.85em] text-slate-800">
          {s.slice(1, -1)}
        </code>
      ) : (
        s
      ),
    );
  });
}

export function Prose({
  text,
  renderMarker,
  className = "",
  highlight,
}: {
  text: string;
  renderMarker?: MarkerRenderer;
  className?: string;
  /** Verbatim substring to highlight (the cited Passage inside its full Section). */
  highlight?: string;
}) {
  const blocks = text.split(/\n\n+/);
  return (
    <div className={`space-y-3 leading-relaxed ${className}`}>
      {blocks.map((block, bi) => {
        const key = `b${bi}`;
        const isHighlighted = highlight !== undefined && highlight.includes(block.trim());
        const wrap = (node: ReactNode) =>
          isHighlighted ? (
            <div key={key} className="-mx-2 rounded border-l-4 border-amber-400 bg-amber-50 px-2 py-1">
              {node}
            </div>
          ) : (
            node
          );
        if (block.startsWith("```")) {
          return wrap(
            <pre key={key} className="overflow-x-auto rounded bg-slate-900 p-3 font-mono text-xs text-slate-100">
              {block.replace(/^```\w*\n?/, "").replace(/```$/, "")}
            </pre>,
          );
        }
        const lines = block.split("\n");
        if (lines.every((l) => l.trim().startsWith("|"))) {
          const rows = lines
            .filter((l) => !/^\|[\s|:-]+\|$/.test(l.trim()))
            .map((l) =>
              l
                .trim()
                .replace(/^\||\|$/g, "")
                .split("|")
                .map((c) => c.trim()),
            );
          const [head, ...body] = rows;
          return wrap(
            <table key={key} className="w-full border-collapse text-sm">
              <thead>
                <tr>
                  {head?.map((c, i) => (
                    <th key={i} className="border-b border-slate-300 px-2 py-1 text-left font-semibold">
                      {inline(c, renderMarker, `${key}h${i}`)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {body.map((r, ri) => (
                  <tr key={ri}>
                    {r.map((c, i) => (
                      <td key={i} className="border-b border-slate-100 px-2 py-1">
                        {inline(c, renderMarker, `${key}r${ri}c${i}`)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>,
          );
        }
        const listStart = lines.findIndex((l) => l.startsWith("- "));
        if (listStart !== -1) {
          const lead = lines.slice(0, listStart).join(" ");
          return wrap(
            <div key={key}>
              {lead && <p>{inline(lead, renderMarker, `${key}lead`)}</p>}
              <ul className="mt-1 list-disc space-y-0.5 pl-5">
                {lines.slice(listStart).map((l, i) => (
                  <li key={i}>{inline(l.slice(2), renderMarker, `${key}li${i}`)}</li>
                ))}
              </ul>
            </div>,
          );
        }
        return wrap(<p key={key}>{inline(block, renderMarker, key)}</p>);
      })}
    </div>
  );
}

export function VersionBadges({ appliesTo, status }: { appliesTo: string[]; status: string }) {
  return (
    <span className="inline-flex gap-1">
      {appliesTo.map((v) => (
        <span
          key={v}
          className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold ${
            v === "v2" ? "bg-orange-100 text-orange-800" : "bg-slate-100 text-slate-600"
          }`}
        >
          {v}
        </span>
      ))}
      {status === "deprecated" && (
        <span className="rounded bg-orange-600 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-white">
          deprecated
        </span>
      )}
    </span>
  );
}
