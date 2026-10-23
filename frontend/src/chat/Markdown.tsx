// A deliberately small Markdown renderer for Answer text and Knowledge Base Sections:
// paragraphs, bulleted and numbered lists, headings, fenced code, pipe tables, inline code,
// **bold** and links (shown as their text). It builds React elements, never HTML strings, so
// model text can't inject markup. Citation markers are handed to `renderMarker`, which is why
// this isn't a library: markers become components mid-text.
import { createElement, type ReactNode } from "react";
import { splitMarkers } from "./markers";

type Align = "left" | "center" | "right" | undefined;

type Block =
  | { kind: "paragraph"; lines: string[] }
  | { kind: "heading"; level: number; text: string }
  | { kind: "list"; ordered: boolean; items: string[] }
  | { kind: "code"; text: string }
  | { kind: "table"; align: Align[]; header: string[]; rows: string[][] };

const BULLET = /^\s*[-*+]\s+(.*)$/;
const NUMBERED = /^\s*\d+[.)]\s+(.*)$/;
const HEADING = /^(#{1,6})\s+(.*)$/;
const FENCE = /^\s*```/;
const TABLE_ROW = /^\s*\|/;
const TABLE_SEPARATOR = /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$/;

/** The cells of a `| a | b |` row. `\|` is a pipe inside a cell, as in GitHub Markdown. */
function tableCells(line: string): string[] {
  const row = line
    .trim()
    .replace(/^\|/, "")
    .replace(/(?<!\\)\|$/, "");
  return row.split(/(?<!\\)\|/).map((cell) => cell.trim().replaceAll("\\|", "|"));
}

function cellAlign(separator: string): Align {
  const left = separator.startsWith(":");
  const right = separator.endsWith(":");
  if (left && right) return "center";
  if (right) return "right";
  return left ? "left" : undefined;
}

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
    if (TABLE_ROW.test(line) && TABLE_SEPARATOR.test(lines[i + 1] ?? "")) {
      close();
      const header = tableCells(line);
      const align = tableCells(lines[++i] ?? "").map(cellAlign);
      const rows: string[][] = [];
      while (i + 1 < lines.length && TABLE_ROW.test(lines[i + 1] ?? "")) {
        const cells = tableCells(lines[++i] ?? "");
        rows.push(header.map((_, c) => cells[c] ?? ""));
      }
      blocks.push({ kind: "table", align, header, rows });
      continue;
    }
    const heading = HEADING.exec(line);
    if (heading) {
      close();
      blocks.push({ kind: "heading", level: heading[1]?.length ?? 1, text: heading[2] ?? "" });
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

const INLINE = /(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)\s]+\))/;
const LINK = /^\[([^\]]+)\]\([^)\s]+\)$/;

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
      // Links point at files and pages this app doesn't serve, so only their text is shown.
      return LINK.exec(run)?.[1] ?? run;
    });
  });
}

export function Markdown({
  text,
  renderMarker,
  headingOffset,
}: {
  text: string;
  /** Renders Citation marker `n` in place. Without it, markers stay as written. */
  renderMarker?: MarkerRenderer;
  /**
   * Renders `#`…`######` as real headings, this many levels down (`##` with 1 is an `<h3>`).
   * Without it, headings are bold lines, as an Answer's should be.
   */
  headingOffset?: number;
}) {
  return (
    <div className="space-y-3 leading-relaxed">
      {parseBlocks(text).map((block, b) => {
        const key = String(b);
        switch (block.kind) {
          case "paragraph":
            return <p key={key}>{renderInline(block.lines.join(" "), renderMarker, key)}</p>;
          case "heading": {
            const content = renderInline(block.text, renderMarker, key);
            if (headingOffset === undefined) {
              return (
                <p key={key} className="font-semibold">
                  {content}
                </p>
              );
            }
            const level = Math.min(block.level + headingOffset, 6);
            return createElement(
              `h${level}`,
              { key, className: level <= 3 ? "pt-2 text-lg font-semibold" : "pt-1 font-semibold" },
              content,
            );
          }
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
          case "table":
            return (
              <div key={key} className="overflow-x-auto">
                <table className="min-w-full border-collapse text-left text-sm">
                  <thead>
                    <tr>
                      {block.header.map((cell, c) => (
                        <th
                          key={c}
                          style={{ textAlign: block.align[c] }}
                          className="border border-slate-300 bg-slate-100 px-2 py-1 font-semibold"
                        >
                          {renderInline(cell, renderMarker, `${key}.h${c}`)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {block.rows.map((row, r) => (
                      <tr key={r}>
                        {row.map((cell, c) => (
                          <td
                            key={c}
                            style={{ textAlign: block.align[c] }}
                            className="border border-slate-300 px-2 py-1 align-top"
                          >
                            {renderInline(cell, renderMarker, `${key}.${r}.${c}`)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          default:
            return null;
        }
      })}
    </div>
  );
}
