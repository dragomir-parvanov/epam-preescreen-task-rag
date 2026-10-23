// Citation markers, as answer assembly reads them on the backend: `[n]`, a comma list `[n, m]`,
// or adjacent markers `[n][m]`. Anything else in brackets (`[doc2]`, `[1-3]`) is plain text.
const MARKER = String.raw`\[\s*\d+(?:\s*,\s*\d+)*\s*\]`;
const CLUSTER = new RegExp(String.raw`[ \t]*(?:${MARKER})+`, "g");
/** The start of a marker cut off by the end of the text so far, e.g. `[`, `[1`, `[1, `. */
const ARRIVING = /[ \t]*\[[\d,\s]*$/;

/**
 * Provisional text without its markers. While tokens stream, markers carry prompt numbers,
 * which `done` renumbers, so they are hidden rather than shown and then changed.
 */
export function stripMarkers(text: string): string {
  return text.replace(CLUSTER, "").replace(ARRIVING, "");
}

export type Marker = { n: number };

/** Split a final Answer's text into text runs and Citation numbers, dropping the space before each marker. */
export function splitMarkers(text: string): (string | Marker)[] {
  const parts: (string | Marker)[] = [];
  let last = 0;
  for (const cluster of text.matchAll(CLUSTER)) {
    if (cluster.index > last) parts.push(text.slice(last, cluster.index));
    for (const n of cluster[0].match(/\d+/g) ?? []) parts.push({ n: Number(n) });
    last = cluster.index + cluster[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}
