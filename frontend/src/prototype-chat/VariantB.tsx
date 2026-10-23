// PROTOTYPE — throwaway. Variant B: chat on the left, a persistent Evidence pane on the right.
// The pane shows the selected Turn's Citations with their quotes always visible; hovering a marker
// highlights its card; "Open Section" turns the pane into a reader. While streaming, the pane shows the
// retrieved Passages and provisional markers point at them (grey) until `done` renumbers them.
import { useEffect, useState, type FormEvent } from "react";
import { SUGGESTED_QUESTIONS, type Passage } from "./fakeBackend";
import { Prose, VersionBadges } from "./Prose";
import type { Chat, Turn } from "./useFakeChat";

export const name = "Evidence pane";

type Card = { key: number; label: string; p: Passage };

function cardsFor(turn: Turn | undefined): { cited: Card[]; other: Card[]; provisional: boolean } {
  if (!turn) return { cited: [], other: [], provisional: false };
  const f = turn.final;
  if (f?.kind === "answer") {
    return {
      cited: f.citations.map((c) => ({ key: c.citationNumber, label: String(c.citationNumber), p: c })),
      other: f.retrieved
        .filter((p) => !f.citations.some((c) => c.n === p.n))
        .map((p) => ({ key: 100 + p.n, label: "–", p })),
      provisional: false,
    };
  }
  if (f) return { cited: [], other: f.retrieved.map((p) => ({ key: 100 + p.n, label: "–", p })), provisional: false };
  return {
    cited: (turn.passages ?? []).map((p) => ({ key: p.n, label: String(p.n), p })),
    other: [],
    provisional: true,
  };
}

function EvidencePane({ turn, hovered }: { turn: Turn | undefined; hovered: number | null }) {
  const [reading, setReading] = useState<Passage | null>(null);
  const [showOther, setShowOther] = useState(false);
  useEffect(() => setReading(null), [turn?.id]);
  const { cited, other, provisional } = cardsFor(turn);
  const f = turn?.final;

  useEffect(() => {
    if (hovered !== null) document.getElementById(`b-card-${hovered}`)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [hovered]);

  if (reading) {
    return (
      <div className="space-y-3 p-5">
        <button type="button" onClick={() => setReading(null)} className="text-sm text-indigo-700 hover:underline">
          ← Back to evidence
        </button>
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">{reading.articleId}</p>
          <h3 className="text-lg font-semibold">{reading.articleTitle}</h3>
          <p className="text-sm text-slate-600">{reading.sectionPath.join(" › ")}</p>
          <div className="mt-1">
            <VersionBadges appliesTo={reading.appliesTo} status={reading.status} />
          </div>
        </div>
        <Prose text={reading.fullSection} highlight={reading.text} className="text-sm" />
      </div>
    );
  }

  const renderCard = (c: Card, dim: boolean) => (
    <li
      key={c.key}
      id={`b-card-${c.key}`}
      className={`rounded-lg border bg-white p-3 text-sm transition ${
        hovered === c.key ? "border-indigo-500 ring-2 ring-indigo-200" : "border-slate-200"
      } ${dim ? "opacity-70" : ""}`}
    >
      <div className="mb-1 flex items-center gap-2">
        <span
          className={`grid h-5 w-5 place-items-center rounded-full font-mono text-[11px] font-bold ${
            provisional ? "bg-slate-200 text-slate-600" : dim ? "bg-slate-100 text-slate-400" : "bg-indigo-600 text-white"
          }`}
        >
          {c.label}
        </span>
        <span className="flex-1 truncate font-medium">{c.p.articleTitle}</span>
        <VersionBadges appliesTo={c.p.appliesTo} status={c.p.status} />
      </div>
      <p className="mb-2 text-xs text-slate-500">{c.p.sectionPath.join(" › ")}</p>
      <div className="border-l-2 border-slate-200 pl-2 text-slate-700">
        <Prose text={c.p.text} className="text-[13px]" />
      </div>
      <button type="button" onClick={() => setReading(c.p)} className="mt-2 text-xs font-medium text-indigo-700 hover:underline">
        Open Section →
      </button>
    </li>
  );

  return (
    <div className="space-y-4 p-5">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {!turn && "Evidence"}
        {turn && provisional && (turn.passages ? "Retrieved Passages (the answer may cite these)" : "Searching…")}
        {f?.kind === "answer" && `Citations (${cited.length})`}
        {f?.kind === "uncited" && "No Citations"}
        {f?.kind === "refusal" && "No Citations"}
      </h2>
      {!turn && <p className="text-sm text-slate-500">Citations for the selected answer appear here.</p>}
      {f?.kind === "uncited" && (
        <p className="rounded bg-amber-50 p-2 text-sm text-amber-900">
          The model didn't cite anything. These Passages were retrieved, but nothing says the answer came from them.
        </p>
      )}
      {f?.kind === "refusal" && (
        <p className="text-sm text-slate-500">
          {f.reason === "no_relevant_passages"
            ? "No Passage was relevant enough to answer from."
            : "The retrieved Passages didn't contain the answer."}
        </p>
      )}
      <ol className="space-y-2">{cited.map((c) => renderCard(c, false))}</ol>
      {other.length > 0 && (
        <div>
          <button type="button" onClick={() => setShowOther((s) => !s)} className="text-xs font-medium text-slate-500 hover:text-slate-800">
            {showOther || f?.kind === "uncited" ? "▾" : "▸"} Retrieved, not cited ({other.length})
          </button>
          {(showOther || f?.kind === "uncited") && <ol className="mt-2 space-y-2">{other.map((c) => renderCard(c, true))}</ol>}
        </div>
      )}
    </div>
  );
}

function Bubble({
  turn,
  selected,
  onSelect,
  onHover,
}: {
  turn: Turn;
  selected: boolean;
  onSelect: () => void;
  onHover: (n: number | null) => void;
}) {
  const f = turn.final;
  const marker = (provisional: boolean) => (n: number, key: string) => (
    <button
      key={key}
      type="button"
      onMouseEnter={() => {
        onSelect();
        onHover(n);
      }}
      onMouseLeave={() => onHover(null)}
      onClick={onSelect}
      className={`mx-0.5 inline-grid h-4 min-w-4 place-items-center rounded-full px-1 align-text-top font-mono text-[10px] font-bold ${
        provisional ? "bg-slate-200 text-slate-600" : "bg-indigo-600 text-white hover:bg-indigo-800"
      }`}
    >
      {n}
    </button>
  );

  return (
    <div className="space-y-2">
      <div className="ml-auto w-fit max-w-[80%] rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2 text-white">{turn.question}</div>
      <div
        onClick={onSelect}
        className={`max-w-[90%] cursor-pointer rounded-2xl rounded-bl-sm border bg-white px-4 py-3 ${
          selected ? "border-indigo-300 shadow" : "border-slate-200"
        }`}
      >
        {turn.standaloneQuestion && turn.standaloneQuestion !== turn.question && (
          <p className="mb-2 inline-block rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
            🔎 {turn.standaloneQuestion}
          </p>
        )}
        {f?.kind === "answer" && <Prose text={f.text} renderMarker={marker(false)} />}
        {f?.kind === "uncited" && (
          <>
            <p className="mb-2 text-xs font-semibold text-amber-700">⚠ Uncited Answer: verify before using</p>
            <Prose text={f.text} />
          </>
        )}
        {f?.kind === "refusal" && <p className="text-slate-600">{f.message}</p>}
        {!f && turn.streamed && <Prose text={turn.streamed} renderMarker={marker(true)} className={turn.phase === "generating" ? "" : "text-slate-500"} />}
        {!f && !turn.streamed && !turn.error && turn.phase !== "stopped" && (
          <p className="flex gap-1 py-1">
            {[0, 1, 2].map((i) => (
              <span key={i} className="h-2 w-2 animate-bounce rounded-full bg-slate-300" style={{ animationDelay: `${i * 120}ms` }} />
            ))}
            <span className="ml-2 text-xs text-slate-400">
              {turn.phase === "rewriting" ? "rewriting follow-up" : turn.phase === "retrieving" ? "searching" : "thinking"}
            </span>
          </p>
        )}
        {turn.phase === "stopped" && <p className="mt-1 text-xs italic text-slate-400">Stopped</p>}
        {turn.error && (
          <p className="mt-1 text-sm text-red-700">
            ⚠ {turn.error.message} <span className="font-mono text-xs">({turn.error.code})</span>
          </p>
        )}
      </div>
    </div>
  );
}

export function VariantB({ chat }: { chat: Chat }) {
  const [draft, setDraft] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [hovered, setHovered] = useState<number | null>(null);
  const latest = chat.turns.at(-1);
  // A new Turn takes over the pane.
  useEffect(() => setSelectedId(latest?.id ?? null), [latest?.id]);
  const selected = chat.turns.find((t) => t.id === selectedId);
  const configError = chat.turns.some((t) => t.error?.code === "llm_not_configured");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!draft.trim() || chat.busy) return;
    void chat.send(draft.trim());
    setDraft("");
  };

  return (
    <div className="grid h-screen grid-cols-[minmax(0,1fr)_420px] bg-slate-100">
      <section className="flex min-h-0 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-5 py-3">
          <span className="font-semibold text-indigo-900">Nimbus KB Assistant</span>
          <button type="button" onClick={chat.reset} className="rounded border border-slate-300 px-2 py-1 text-xs">
            + New conversation
          </button>
        </header>
        {configError && (
          <div className="bg-red-600 px-5 py-2 text-sm text-white">
            Chat model not configured. Answers are unavailable until an API key or Ollama is set up.
          </div>
        )}
        <div className="min-h-0 flex-1 space-y-6 overflow-y-auto px-5 py-6 pb-28">
          {chat.turns.length === 0 && (
            <div className="grid grid-cols-2 gap-2">
              {SUGGESTED_QUESTIONS.map((q) => (
                <button key={q} type="button" onClick={() => void chat.send(q)} className="rounded-lg border border-slate-200 bg-white p-3 text-left text-sm hover:border-indigo-400">
                  {q}
                </button>
              ))}
            </div>
          )}
          {chat.turns.map((t) => (
            <Bubble key={t.id} turn={t} selected={t.id === selectedId} onSelect={() => setSelectedId(t.id)} onHover={setHovered} />
          ))}
        </div>
        <form onSubmit={submit} className="flex gap-2 border-t border-slate-200 bg-white p-3 pb-16">
          <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Message the assistant" className="flex-1 rounded-full border border-slate-300 px-4 py-2" />
          {chat.busy ? (
            <button type="button" onClick={chat.stop} className="rounded-full bg-red-100 px-4 font-medium text-red-700">
              Stop
            </button>
          ) : (
            <button type="submit" className="rounded-full bg-indigo-600 px-4 font-medium text-white">
              Send
            </button>
          )}
        </form>
      </section>
      <aside className="min-h-0 overflow-y-auto border-l border-slate-200 bg-slate-50 pb-20">
        <EvidencePane turn={selected} hovered={hovered} />
      </aside>
    </div>
  );
}
