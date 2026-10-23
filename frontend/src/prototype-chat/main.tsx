// PROTOTYPE — throwaway. "Chat UI with citations" (issue #14).
// Three variants of the chat page, switchable via `?variant=A|B|C` on /prototype-chat.html,
// all driven by the same fake SSE stream. Run: `pixi run dev-frontend`, then open
// http://localhost:5173/prototype-chat.html
import { StrictMode, useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "../index.css";
import type { ProviderMode } from "./fakeBackend";
import { useFakeChat, type Chat } from "./useFakeChat";
import { VariantA, name as nameA } from "./VariantA";
import { VariantB, name as nameB } from "./VariantB";
import { VariantC, name as nameC } from "./VariantC";

const VARIANTS: { key: string; name: string; Component: (p: { chat: Chat }) => React.ReactNode }[] = [
  { key: "A", name: nameA, Component: VariantA },
  { key: "B", name: nameB, Component: VariantB },
  { key: "C", name: nameC, Component: VariantC },
];

const MODES: { key: ProviderMode; label: string }[] = [
  { key: "ok", label: "Provider OK" },
  { key: "slow_first_token", label: "Slow first token (7 s)" },
  { key: "down_mid_stream", label: "Provider dies mid-stream" },
  { key: "missing_key", label: "Missing API key" },
];

function useSearchParam(name: string, fallback: string) {
  const [value, setValue] = useState(() => new URLSearchParams(location.search).get(name) ?? fallback);
  const set = useCallback(
    (v: string) => {
      const url = new URL(location.href);
      url.searchParams.set(name, v);
      history.replaceState(null, "", url);
      setValue(v);
    },
    [name],
  );
  return [value, set] as const;
}

function Switcher({ current, onChange }: { current: string; onChange: (k: string) => void }) {
  const i = Math.max(0, VARIANTS.findIndex((v) => v.key === current));
  const go = useCallback(
    (d: number) => {
      const next = VARIANTS[(i + d + VARIANTS.length) % VARIANTS.length];
      if (next) onChange(next.key);
    },
    [i, onChange],
  );
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = document.activeElement;
      if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement || (el instanceof HTMLElement && el.isContentEditable)) return;
      if (e.key === "ArrowLeft") go(-1);
      if (e.key === "ArrowRight") go(1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go]);
  const v = VARIANTS[i];
  return (
    <div className="fixed bottom-3 left-1/2 z-50 flex -translate-x-1/2 items-center gap-3 rounded-full bg-fuchsia-700 px-4 py-1.5 font-mono text-sm text-white shadow-xl ring-2 ring-fuchsia-300">
      <button type="button" onClick={() => go(-1)} aria-label="Previous variant">
        ◀
      </button>
      <span>
        {v?.key} ({v?.name})
      </span>
      <button type="button" onClick={() => go(1)} aria-label="Next variant">
        ▶
      </button>
    </div>
  );
}

function DevPanel({ chat, mode, setMode }: { chat: Chat; mode: string; setMode: (m: string) => void }) {
  const [open, setOpen] = useState(false);
  const lastTurn = chat.turns.at(-1);
  return (
    <div className="fixed right-3 bottom-3 z-50 font-mono text-xs">
      {open && (
        <div className="mb-2 max-h-[70vh] w-[460px] overflow-y-auto rounded-lg bg-fuchsia-950 p-3 text-fuchsia-50 shadow-2xl">
          <p className="mb-1 font-bold">Provider mode (applies to the next question)</p>
          {MODES.map((m) => (
            <label key={m.key} className="block">
              <input type="radio" name="mode" checked={mode === m.key} onChange={() => setMode(m.key)} /> {m.label}
            </label>
          ))}
          <p className="mt-3 mb-1 font-bold">Turn state</p>
          <pre className="whitespace-pre-wrap text-[10px] text-fuchsia-200">
            {chat.turns.map((t) => `#${t.id} ${t.phase.padEnd(10)} ${t.final?.kind ?? t.error?.code ?? ""}  ${t.question}`).join("\n") || "(no Turns)"}
          </pre>
          {lastTurn && (
            <>
              <p className="mt-3 mb-1 font-bold">Events for Turn #{lastTurn.id}</p>
              <pre className="whitespace-pre-wrap text-[10px] text-fuchsia-200">
                {chat.log
                  .filter((e) => e.turnId === lastTurn.id)
                  .filter((e, i, all) => e.event.type !== "token" || all[i - 1]?.event.type !== "token")
                  .map((e) => {
                    const { type, ...rest } = e.event;
                    const body = type === "token" ? "(token stream…)" : JSON.stringify(rest, (k, val: unknown) => (k === "fullSection" || k === "text" ? undefined : val));
                    return `${String(e.at).padStart(5)}ms ${type} ${body}`;
                  })
                  .join("\n")}
              </pre>
            </>
          )}
        </div>
      )}
      <button type="button" onClick={() => setOpen((o) => !o)} className="ml-auto block rounded-full bg-fuchsia-700 px-3 py-1.5 text-white shadow-xl">
        {open ? "close" : "scenario / state"} · {mode}
      </button>
    </div>
  );
}

function Prototype() {
  const [variant, setVariant] = useSearchParam("variant", "A");
  const [mode, setMode] = useSearchParam("mode", "ok");
  const chat = useFakeChat(mode as ProviderMode);
  const v = VARIANTS.find((x) => x.key === variant) ?? VARIANTS[0];
  if (!v) return null;
  return (
    <>
      <v.Component chat={chat} />
      {!import.meta.env.PROD && (
        <>
          <Switcher current={v.key} onChange={setVariant} />
          <DevPanel chat={chat} mode={mode} setMode={setMode} />
        </>
      )}
    </>
  );
}

const root = document.getElementById("root");
if (!root) throw new Error("missing #root");
createRoot(root).render(
  <StrictMode>
    <Prototype />
  </StrictMode>,
);
