// PROTOTYPE — throwaway. Variant A: single reading column, footnote-style Citations.
// Markers are superscripts; clicking one expands its Citation inline under the Answer, quote first,
// with the full Section unfolding in place. Provisional markers are hidden while streaming.
import { useState, type FormEvent } from "react";
import type { Citation, Passage } from "./fakeBackend";
import { Prose, VersionBadges } from "./Prose";
import { SUGGESTED_QUESTIONS } from "./fakeBackend";
import { stripMarkers, type Chat, type Turn } from "./useFakeChat";

export const name = "Footnotes column";

function CitationItem({ c, open, onToggle }: { c: Citation | Passage; open: boolean; onToggle: () => void }) {
  const [full, setFull] = useState(false);
  const label = "citationNumber" in c ? c.citationNumber : "·";
  return (
    <li id={`a-cite-${"citationNumber" in c ? c.citationNumber : c.n}`} className="rounded border border-slate-200 bg-white">
      <button type="button" onClick={onToggle} className="flex w-full items-start gap-2 px-3 py-2 text-left text-sm">
        <span className="mt-0.5 min-w-5 font-mono text-xs font-semibold text-blue-700">{label}</span>
        <span className="flex-1">
          <span className="font-medium">{c.articleTitle}</span>
          <span className="text-slate-500"> › {c.sectionPath.join(" › ")}</span>
        </span>
        <VersionBadges appliesTo={c.appliesTo} status={c.status} />
        <span className="text-slate-400">{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <div className="border-t border-slate-100 px-3 py-2 pl-10 text-sm">
          {full ? (
            <Prose text={c.fullSection} highlight={c.text} />
          ) : (
            <blockquote className="border-l-2 border-slate-300 pl-3 text-slate-700">
              <Prose text={c.text} />
            </blockquote>
          )}
          <button type="button" onClick={() => setFull((f) => !f)} className="mt-2 text-xs font-medium text-blue-700 hover:underline">
            {full ? "Show only the quoted Passage" : `Show the full Section (${c.articleId})`}
          </button>
        </div>
      )}
    </li>
  );
}

function TurnView({ turn }: { turn: Turn }) {
  const [open, setOpen] = useState<Set<number>>(new Set());
  const toggle = (n: number) =>
    setOpen((s) => {
      const next = new Set(s);
      if (next.has(n)) next.delete(n);
      else next.add(n);
      return next;
    });
  const [showRetrieved, setShowRetrieved] = useState(false);
  const f = turn.final;

  return (
    <article className="space-y-3">
      <h2 className="text-lg font-semibold text-slate-900">{turn.question}</h2>
      {turn.standaloneQuestion && turn.standaloneQuestion !== turn.question && (
        <p className="text-xs text-slate-500">
          Searched for: <span className="italic">{turn.standaloneQuestion}</span>
        </p>
      )}

      {!f && !turn.error && turn.phase !== "stopped" && (
        <p className="animate-pulse text-sm text-slate-500">
          {turn.phase === "rewriting" && "Understanding the follow-up…"}
          {turn.phase === "retrieving" && "Searching the Knowledge Base…"}
          {turn.phase === "generating" &&
            (turn.streamed ? "Writing…" : `Found ${turn.passages?.length ?? 0} Passages. Writing the answer…`)}
        </p>
      )}

      {!f && turn.streamed && (
        <div className={turn.phase === "stopped" || turn.phase === "error" ? "text-slate-500" : "text-slate-800"}>
          <Prose text={stripMarkers(turn.streamed)} />
          {turn.phase === "generating" && <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-slate-400 align-middle" />}
        </div>
      )}

      {turn.phase === "stopped" && (
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
          Stopped. This partial answer has no Citations and won't be used as context for follow-ups.
        </p>
      )}

      {turn.error && (
        <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          <p className="font-semibold">
            {turn.error.code === "llm_not_configured" ? "The assistant isn't set up yet" : "The answer couldn't be finished"}
          </p>
          <p>{turn.error.message}</p>
          <p className="mt-1 font-mono text-xs text-red-500">{turn.error.code}</p>
        </div>
      )}

      {f?.kind === "refusal" && (
        <div className="rounded border border-slate-200 bg-slate-100 p-3 text-sm text-slate-700">
          <p>{f.message}</p>
          <p className="mt-1 font-mono text-xs text-slate-400">reason: {f.reason}</p>
        </div>
      )}

      {f?.kind === "uncited" && (
        <>
          <div className="rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
            <strong>Uncited Answer.</strong> The assistant didn't point to any Passage for this. Check it against the
            retrieved Passages below before passing it on.
          </div>
          <div className="text-slate-800">
            <Prose text={f.text} />
          </div>
          <section>
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Retrieved, not cited</h3>
            <ol className="space-y-1">
              {f.retrieved.map((p) => (
                <CitationItem key={p.n} c={p} open={open.has(p.n)} onToggle={() => toggle(p.n)} />
              ))}
            </ol>
          </section>
        </>
      )}

      {f?.kind === "answer" && (
        <>
          <div className="text-slate-800">
            <Prose
              text={f.text}
              renderMarker={(n, key) => (
                <sup key={key}>
                  <button
                    type="button"
                    onClick={() => toggle(n)}
                    className={`mx-px rounded px-0.5 font-mono text-[11px] font-semibold ${
                      open.has(n) ? "bg-blue-700 text-white" : "text-blue-700 hover:bg-blue-100"
                    }`}
                  >
                    {n}
                  </button>
                </sup>
              )}
            />
          </div>
          <section>
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Citations</h3>
            <ol className="space-y-1">
              {f.citations.map((c) => (
                <CitationItem key={c.citationNumber} c={c} open={open.has(c.citationNumber)} onToggle={() => toggle(c.citationNumber)} />
              ))}
            </ol>
            <button type="button" onClick={() => setShowRetrieved((s) => !s)} className="mt-2 text-xs text-slate-400 hover:text-slate-600">
              {showRetrieved ? "Hide" : "Show"} all {f.retrieved.length} retrieved Passages
            </button>
            {showRetrieved && (
              <ul className="mt-1 space-y-0.5 font-mono text-xs text-slate-500">
                {f.retrieved.map((p) => (
                  <li key={p.n}>
                    #{p.n} {p.score.toFixed(2)} {p.articleId} › {p.sectionPath.join(" › ")}
                    {f.citations.some((c) => c.n === p.n) ? "" : "  (not cited)"}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </article>
  );
}

export function VariantA({ chat }: { chat: Chat }) {
  const [draft, setDraft] = useState("");
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!draft.trim() || chat.busy) return;
    void chat.send(draft.trim());
    setDraft("");
  };

  return (
    <div className="min-h-screen bg-stone-50">
      <header className="sticky top-0 z-10 border-b border-stone-200 bg-stone-50/90 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-3">
          <span className="font-semibold">OmniCorp Knowledge Base</span>
          <button type="button" onClick={chat.reset} className="text-sm text-slate-600 hover:text-slate-900">
            New conversation
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-3xl space-y-10 px-6 pt-8 pb-48">
        {chat.turns.length === 0 && (
          <div className="space-y-3 text-slate-600">
            <p>Ask about OmniCorp Nimbus. Answers come only from the Knowledge Base, with Citations.</p>
            <ul className="space-y-1 text-sm">
              {SUGGESTED_QUESTIONS.map((q) => (
                <li key={q}>
                  <button type="button" onClick={() => void chat.send(q)} className="text-left text-blue-700 hover:underline">
                    {q}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
        {chat.turns.map((t) => (
          <TurnView key={t.id} turn={t} />
        ))}
      </main>
      <form onSubmit={submit} className="fixed inset-x-0 bottom-16 mx-auto flex max-w-3xl gap-2 px-6">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask a question…"
          className="flex-1 rounded border border-stone-300 bg-white px-3 py-2 shadow-sm"
        />
        {chat.busy ? (
          <button type="button" onClick={chat.stop} className="rounded bg-slate-200 px-4 py-2 font-medium text-slate-800">
            ■ Stop
          </button>
        ) : (
          <button type="submit" className="rounded bg-slate-900 px-4 py-2 font-medium text-white">
            Ask
          </button>
        )}
      </form>
    </div>
  );
}
