// A deliberately tiny Markdown renderer for Answer text: paragraphs, bulleted and numbered
// lists, headings (as bold lines), fenced code, inline code and **bold**. It builds React
// elements, never HTML strings, so model text can't inject markup. Citation markers are handed
// to `renderMarker`, which is why this isn't a library: markers become components mid-text.
import type { ReactNode } from "react";
import { splitMarkers } from "./markers";

type Block =
  | { kind: "paragraph"; lines: string[] }
  | { kind: "heading"; text: string }
  | { kind: "list"; ordered: boolean; items: string[] }
  | { kind: "code"; text: string };

const BULLET = /^\s*[-*+]\s+(.*)$/;
const NUMBERED = /^\s*\d+[.)]\s+(.*)$/;
const HEADING = /^#{1,6}\s+(.*)$/;
const FENCE = /^\s*```/;

function parseBlocks(text: string): Block[] {
  const blocks: Block[] = [];
  const lines = text.split(/\r?\n/);
  // The paragraph or list still taking lines. Held in an object so `close` can reset it.
  const open: { block: Block | null } = { block: null };
  const close = () => {
    if (open.block) blocks.push(open.block);
    open.block = null;
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i] ?? "";
    if (FENCE.test(line)) {
      close();
      const code: string[] = [];
      while (i + 1 < lines.length && !FENCE.test(lines[i + 1] ?? "")) code.push(lines[++i] ?? "");
      i++; // the closing fence, if there is one
      blocks.push({ kind: "code", text: code.join("\n") });
      continue;
    }
    if (line.trim() === "") {
      close();
      continue;
    }
    const heading = HEADING.exec(line);
    if (heading) {
      close();
      blocks.push({ kind: "heading", text: heading[1] ?? "" });
      continue;
    }
    const bullet = BULLET.exec(line);
    const numbered = bullet ? null : NUMBERED.exec(line);
    const item = bullet ?? numbered;
    if (item) {
      const ordered = numbered !== null;
      const list = open.block;
      if (list?.kind === "list" && list.ordered === ordered) {
        list.items.push(item[1] ?? "");
      } else {
        close();
        open.block = { kind: "list", ordered, items: [item[1] ?? ""] };
      }
      continue;
    }
    const block = open.block;
    if (block?.kind === "list" && /^\s/.test(line)) {
      // An indented line continues the last list item.
      const last = block.items.length - 1;
      block.items[last] = `${block.items[last] ?? ""} ${line.trim()}`;
    } else if (block?.kind === "paragraph") {
      block.lines.push(line.trim());
    } else {
      close();
      open.block = { kind: "paragraph", lines: [line.trim()] };
    }
  }
  close();
  return blocks;
}

type MarkerRenderer = (n: number, key: string) => ReactNode;

const INLINE = /(`[^`]+`|\*\*[^*]+\*\*)/;

function renderInline(text: string, renderMarker: MarkerRenderer | undefined, key: string) {
  const parts = renderMarker ? splitMarkers(text) : [text];
  return parts.flatMap((part, i): ReactNode[] => {
    if (typeof part !== "string") return [renderMarker?.(part.n, `${key}.${i}`)];
    return part.split(INLINE).map((run, j) => {
      const runKey = `${key}.${i}.${j}`;
      if (run.length > 2 && run.startsWith("`") && run.endsWith("`")) {
        return (
          <code key={runKey} className="rounded bg-slate-100 px-1 font-mono text-[0.9em]">
            {run.slice(1, -1)}
          </code>
        );
      }
      if (run.length > 4 && run.startsWith("**") && run.endsWith("**")) {
        return <strong key={runKey}>{run.slice(2, -2)}</strong>;
      }
      return run;
    });
  });
}

export function Markdown({
  text,
  renderMarker,
}: {
  text: string;
  /** Renders Citation marker `n` in place. Without it, markers stay as written. */
  renderMarker?: MarkerRenderer;
}) {
  return (
    <div className="space-y-3 leading-relaxed">
      {parseBlocks(text).map((block, b) => {
        const key = String(b);
        switch (block.kind) {
          case "paragraph":
            return <p key={key}>{renderInline(block.lines.join(" "), renderMarker, key)}</p>;
          case "heading":
            return (
              <p key={key} className="font-semibold">
                {renderInline(block.text, renderMarker, key)}
              </p>
            );
          case "list": {
            const items = block.items.map((item, i) => (
              <li key={i}>{renderInline(item, renderMarker, `${key}.${i}`)}</li>
            ));
            return block.ordered ? (
              <ol key={key} className="list-decimal space-y-1 pl-6">
                {items}
              </ol>
            ) : (
              <ul key={key} className="list-disc space-y-1 pl-6">
                {items}
              </ul>
            );
          }
          case "code":
            return (
              <pre
                key={key}
                className="overflow-x-auto rounded bg-slate-900 p-3 font-mono text-xs text-slate-100"
              >
                {block.text}
              </pre>
            );
          default:
            return null;
        }
      })}
    </div>
  );
}
