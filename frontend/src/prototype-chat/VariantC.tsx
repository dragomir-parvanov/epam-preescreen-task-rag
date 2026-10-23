// PROTOTYPE — throwaway. Variant C: dense answer cards with hover popovers and a strip of Citation
// chips under each Answer; any chip or marker opens the full Section in a slide-over drawer.
// A pipeline stepper (rewrite → retrieve → write) shows progress. Provisional markers show as "…".
import { useState, type FormEvent } from "react";
import { SUGGESTED_QUESTIONS, type Passage } from "./fakeBackend";
import { Prose, VersionBadges } from "./Prose";
import type { Chat, Turn } from "./useFakeChat";

export const name = "Popovers + drawer";

function Stepper({ turn }: { turn: Turn }) {
  const steps = [
    ...(turn.isFollowUp ? [{ key: "rewriting", label: "Rewrite follow-up" }] : []),
    { key: "retrieving", label: turn.passages ? `Retrieved ${turn.passages.length}` : "Retrieve" },
    { key: "generating", label: "Write answer" },
  ];
  const order = steps.map((s) => s.key);
  const current = order.indexOf(turn.phase);
  return (
    <ol className="flex items-center gap-1 text-[11px]">
      {steps.map((s, i) => (
        <li key={s.key} className="flex items-center gap-1">
          <span
            className={`rounded-full px-2 py-0.5 ${
              i < current ? "bg-emerald-100 text-emerald-800" : i === current ? "animate-pulse bg-sky-100 text-sky-800" : "bg-zinc-100 text-zinc-400"
            }`}
          >
            {i < current ? "✓ " : ""}
            {s.label}
          </span>
          {i < steps.length - 1 && <span className="text-zinc-300">→</span>}
        </li>
      ))}
    </ol>
  );
}

function Marker({ n, p, onOpen }: { n: number; p: Passage | undefined; onOpen: () => void }) {
  return (
    <span className="group relative inline-block">
      <button
        type="button"
        onClick={onOpen}
        className="mx-0.5 rounded bg-sky-100 px-1 font-mono text-[11px] font-semibold text-sky-800 hover:bg-sky-600 hover:text-white"
      >
        {n}
      </button>
      {p && (
        <span className="invisible absolute bottom-full left-1/2 z-20 mb-1 w-80 -translate-x-1/2 rounded-lg border border-zinc-200 bg-white p-3 text-left text-xs opacity-0 shadow-xl transition group-hover:visible group-hover:opacity-100">
          <span className="mb-1 flex items-center justify-between gap-2">
            <span className="font-semibold text-zinc-900">{p.articleTitle}</span>
            <VersionBadges appliesTo={p.appliesTo} status={p.status} />
          </span>
          <span className="mb-1 block text-zinc-500">{p.sectionPath.join(" › ")}</span>
          <span className="line-clamp-4 block text-zinc-700">{p.text.replaceAll(/[|`]/g, " ")}</span>
          <span className="mt-1 block text-sky-700">Click to open the Section</span>
        </span>
      )}
    </span>
  );
}

function Chip({ label, p, dashed, onOpen }: { label: string; p: Passage; dashed?: boolean; onOpen: () => void }) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className={`flex max-w-64 items-center gap-1.5 rounded-md border px-2 py-1 text-left text-xs hover:bg-zinc-50 ${
        dashed ? "border-dashed border-zinc-300 text-zinc-500" : "border-zinc-200 text-zinc-700"
      } ${p.status === "deprecated" ? "bg-orange-50" : "bg-white"}`}
    >
      <span className="font-mono font-bold text-sky-700">{label}</span>
      <span className="truncate">
        {p.articleTitle} › {p.sectionPath.at(-1)}
      </span>
      {p.status === "deprecated" && <span className="font-mono text-[10px] text-orange-700">v2</span>}
    </button>
  );
}

function AnswerCard({ turn, onOpen }: { turn: Turn; onOpen: (p: Passage) => void }) {
  const f = turn.final;
  const byCitation = (n: number) => (f?.kind === "answer" ? f.citations.find((c) => c.citationNumber === n) : undefined);
  const byPrompt = (n: number) => turn.passages?.find((p) => p.n === n);

  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-zinc-500">
        <span className="text-zinc-400">You · </span>
        {turn.question}
      </p>
      <div
        className={`rounded-xl border bg-white p-4 shadow-sm ${
          f?.kind === "uncited" ? "border-l-4 border-amber-400" : f?.kind === "refusal" ? "border-zinc-200 bg-zinc-50" : "border-zinc-200"
        }`}
      >
        <div className="mb-2 flex flex-wrap items-center gap-2">
          {turn.standaloneQuestion && turn.standaloneQuestion !== turn.question && (
            <span className="text-xs text-zinc-500" title="The follow-up was rewritten into this standalone question">
              Searched for “{turn.standaloneQuestion}”
            </span>
          )}
          {f?.kind === "uncited" && <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[11px] font-semibold text-amber-800">UNCITED</span>}
          {f?.kind === "refusal" && <span className="rounded bg-zinc-200 px-1.5 py-0.5 text-[11px] font-semibold text-zinc-700">NOT IN THE KNOWLEDGE BASE</span>}
          {turn.phase === "stopped" && <span className="rounded bg-zinc-200 px-1.5 py-0.5 text-[11px] font-semibold text-zinc-600">STOPPED</span>}
        </div>
        {!f && !turn.error && turn.phase !== "stopped" && (
          <div className="mb-2">
            <Stepper turn={turn} />
          </div>
        )}

        {f?.kind === "answer" && (
          <Prose
            text={f.text}
            className="text-[15px] text-zinc-800"
            renderMarker={(n, key) => {
              const p = byCitation(n);
              return <Marker key={key} n={n} p={p} onOpen={() => p && onOpen(p)} />;
            }}
          />
        )}
        {f?.kind === "uncited" && (
          <>
            <Prose text={f.text} className="text-[15px] text-zinc-700" />
            <p className="mt-2 text-xs text-amber-800">No Citations: nothing ties this answer to the Knowledge Base. Check the retrieved Passages below.</p>
          </>
        )}
        {f?.kind === "refusal" && <p className="text-zinc-600">{f.message}</p>}
        {!f && turn.streamed && (
          <Prose
            text={turn.streamed}
            className={`text-[15px] ${turn.phase === "generating" ? "text-zinc-800" : "text-zinc-400"}`}
            renderMarker={(n, key) => {
              const p = byPrompt(n);
              return (
                <button key={key} type="button" onClick={() => p && onOpen(p)} className="mx-0.5 rounded bg-zinc-100 px-1 font-mono text-[11px] text-zinc-400">
                  …
                </button>
              );
            }}
          />
        )}
        {turn.error && (
          <div className="mt-2 flex items-start gap-2 rounded-md bg-red-50 p-2 text-sm text-red-800">
            <span>✕</span>
            <span>
              {turn.error.message}
              <span className="block font-mono text-[11px] text-red-500">{turn.error.code}</span>
            </span>
          </div>
        )}

        {f?.kind === "answer" && (
          <div className="mt-3 flex flex-wrap gap-1.5 border-t border-zinc-100 pt-3">
            {f.citations.map((c) => (
              <Chip key={c.citationNumber} label={String(c.citationNumber)} p={c} onOpen={() => onOpen(c)} />
            ))}
          </div>
        )}
        {f && f.kind !== "answer" && f.retrieved.length > 0 && (f.kind === "uncited" || f.reason === "not_in_context") && (
          <div className="mt-3 border-t border-zinc-100 pt-3">
            <p className="mb-1 text-[11px] uppercase tracking-wide text-zinc-400">Retrieved, not cited</p>
            <div className="flex flex-wrap gap-1.5">
              {f.retrieved.map((p) => (
                <Chip key={p.n} label="–" p={p} dashed onOpen={() => onOpen(p)} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Drawer({ p, onClose }: { p: Passage; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-30 flex justify-end bg-zinc-900/30" onClick={onClose}>
      <div className="h-full w-[520px] overflow-y-auto bg-white p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <p className="font-mono text-xs text-zinc-400">knowledge-base/{p.articleId}.md</p>
            <h3 className="text-xl font-semibold">{p.articleTitle}</h3>
            <p className="text-sm text-zinc-600">{p.sectionPath.join(" › ")}</p>
          </div>
          <button type="button" onClick={onClose} className="text-xl text-zinc-400 hover:text-zinc-800">
            ×
          </button>
        </div>
        {p.status === "deprecated" && (
          <p className="mb-3 rounded bg-orange-50 p-2 text-sm text-orange-900">
            This Article describes Nimbus v2, which is deprecated (end of support 2027-03-31).
          </p>
        )}
        <Prose text={p.fullSection} highlight={p.text} className="text-sm" />
        <p className="mt-4 text-xs text-zinc-400">Highlighted: the Passage the assistant was shown.</p>
      </div>
    </div>
  );
}

export function VariantC({ chat }: { chat: Chat }) {
  const [draft, setDraft] = useState("");
  const [drawer, setDrawer] = useState<Passage | null>(null);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!draft.trim() || chat.busy) return;
    void chat.send(draft.trim());
    setDraft("");
  };

  return (
    <div className="min-h-screen bg-zinc-100">
      <div className="mx-auto max-w-2xl px-4 pt-6 pb-48">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-sm font-bold tracking-tight">
            Nimbus<span className="text-sky-600">KB</span>
          </h1>
          {chat.turns.length > 0 && (
            <button type="button" onClick={chat.reset} className="text-xs text-zinc-500 hover:text-zinc-900">
              ↺ New conversation
            </button>
          )}
        </div>
        {chat.turns.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {SUGGESTED_QUESTIONS.map((q) => (
              <button key={q} type="button" onClick={() => void chat.send(q)} className="rounded-full border border-zinc-300 bg-white px-3 py-1 text-xs hover:border-sky-500">
                {q}
              </button>
            ))}
          </div>
        )}
        <div className="space-y-6">
          {chat.turns.map((t) => (
            <AnswerCard key={t.id} turn={t} onOpen={setDrawer} />
          ))}
        </div>
      </div>
      <form onSubmit={submit} className="fixed inset-x-0 bottom-16 mx-auto max-w-2xl px-4">
        <div className="flex items-center rounded-2xl border border-zinc-300 bg-white p-1.5 shadow-lg">
          <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Ask the Knowledge Base" className="flex-1 bg-transparent px-3 py-2 outline-none" />
          {chat.busy ? (
            <button type="button" onClick={chat.stop} className="grid h-9 w-9 place-items-center rounded-xl bg-zinc-900 text-white" title="Stop">
              ■
            </button>
          ) : (
            <button type="submit" className="grid h-9 w-9 place-items-center rounded-xl bg-sky-600 text-white" title="Ask">
              ↑
            </button>
          )}
        </div>
      </form>
      {drawer && <Drawer p={drawer} onClose={() => setDrawer(null)} />}
    </div>
  );
}
