// PROTOTYPE — throwaway. Conversation state driven by the fake SSE stream.
import { useCallback, useRef, useState } from "react";
import {
  fakeChatStream,
  type ChatError,
  type ChatEvent,
  type FinalPayload,
  type HistoryTurn,
  type Passage,
  type ProviderMode,
} from "./fakeBackend";

export type TurnPhase = "rewriting" | "retrieving" | "generating" | "done" | "stopped" | "error";

export type Turn = {
  id: number;
  question: string;
  isFollowUp: boolean;
  standaloneQuestion?: string;
  passages?: Passage[];
  /** Provisional text from `token` events; uses the prompt's Passage numbers. */
  streamed: string;
  final?: FinalPayload;
  error?: ChatError;
  phase: TurnPhase;
};

export type EventLogEntry = { turnId: number; at: number; event: ChatEvent | { type: "request"; body: unknown } };

function historyFrom(turns: Turn[]): HistoryTurn[] {
  // Stopped and failed Turns are left out (#8); the server caps at the last 3.
  return turns
    .filter((t) => t.phase === "done" && t.final)
    .map((t) => ({
      question: t.question,
      answer: t.final?.kind === "refusal" ? t.final.message : (t.final?.text ?? ""),
    }));
}

export function useFakeChat(mode: ProviderMode) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [log, setLog] = useState<EventLogEntry[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const nextId = useRef(1);

  const patch = useCallback((id: number, f: (t: Turn) => Turn) => {
    setTurns((ts) => ts.map((t) => (t.id === id ? f(t) : t)));
  }, []);

  const send = useCallback(
    async (question: string) => {
      const id = nextId.current++;
      const history = historyFrom(turns);
      const body = { question, history };
      const controller = new AbortController();
      abortRef.current = controller;
      const t0 = performance.now();
      const isFollowUp = history.length > 0;
      setTurns((ts) => [
        ...ts,
        { id, question, isFollowUp, streamed: "", phase: isFollowUp ? "rewriting" : "retrieving" },
      ]);
      setLog((l) => [...l, { turnId: id, at: 0, event: { type: "request", body } }]);

      try {
        for await (const ev of fakeChatStream(body, mode, controller.signal)) {
          setLog((l) => [...l, { turnId: id, at: Math.round(performance.now() - t0), event: ev }]);
          switch (ev.type) {
            case "rewritten":
              patch(id, (t) => ({ ...t, standaloneQuestion: ev.standaloneQuestion, phase: "retrieving" }));
              break;
            case "passages":
              patch(id, (t) => ({ ...t, passages: ev.passages, phase: "generating" }));
              break;
            case "token":
              patch(id, (t) => ({ ...t, streamed: t.streamed + ev.text }));
              break;
            case "done":
              patch(id, (t) => ({ ...t, final: ev.payload, phase: "done" }));
              break;
            case "error":
              patch(id, (t) => ({ ...t, error: ev.error, phase: "error" }));
              break;
          }
        }
      } catch (e) {
        if (e instanceof DOMException && e.name === "AbortError") {
          patch(id, (t) => ({ ...t, phase: "stopped" }));
        } else throw e;
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
      }
    },
    [turns, mode, patch],
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setTurns([]);
    setLog([]);
  }, []);

  const busy = turns.some((t) => !["done", "stopped", "error"].includes(t.phase));

  return { turns, log, busy, send, stop, reset };
}

export type Chat = ReturnType<typeof useFakeChat>;

/** Split answer text into prose and `[n]` markers. */
export function splitMarkers(text: string): (string | { marker: number })[] {
  const out: (string | { marker: number })[] = [];
  let last = 0;
  for (const m of text.matchAll(/\[(\d+)\]/g)) {
    if (m.index > last) out.push(text.slice(last, m.index));
    out.push({ marker: Number(m[1]) });
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function stripMarkers(text: string): string {
  return text.replaceAll(/\s?\[\d+\]/g, "");
}
