import type { components } from "../api/schema";
import type { ChatStreamEvent } from "./chatStream";

type ChatResult = components["schemas"]["ChatResult"];
type ErrorBody = components["schemas"]["ErrorBody"];
type HistoryTurn = components["schemas"]["HistoryTurn"];
type Passage = components["schemas"]["Passage"];

/**
 * Where a Turn is. It moves forward only:
 * rewriting (Follow-ups only) → retrieving → generating → done | stopped | error.
 */
export type TurnPhase = "rewriting" | "retrieving" | "generating" | "done" | "stopped" | "error";

export type Turn = {
  /** Unique within the Conversation; a React key. */
  id: number;
  /** What the CSM typed. */
  question: string;
  phase: TurnPhase;
  /** The rewrite of a Follow-up Question, once known. */
  standaloneQuestion: string | null;
  /** Retrieved Passages, numbered in prompt order: `[n]` in `provisionalText` is `passages[n - 1]`. */
  passages: Passage[];
  /** Raw model text streamed so far. `result` supersedes it once the Turn is done. */
  provisionalText: string;
  /** The authoritative result, set when the Turn is done. */
  result: ChatResult | null;
  error: ErrorBody | null;
};

/** The Turns one CSM has with the assistant in this browser tab. Nothing is persisted. */
export type Conversation = {
  turns: Turn[];
  nextId: number;
};

/**
 * - `asked`: the CSM sent a question; a new Turn starts.
 * - `received`: a stream event for the Turn in progress.
 * - `stopped`: the CSM stopped the Turn in progress.
 * - `cleared`: New conversation.
 */
export type ConversationAction =
  | { type: "asked"; question: string }
  | { type: "received"; event: ChatStreamEvent }
  | { type: "stopped" }
  | { type: "cleared" };

export const emptyConversation: Conversation = { turns: [], nextId: 1 };

export function isInProgress(turn: Turn): boolean {
  return turn.phase === "rewriting" || turn.phase === "retrieving" || turn.phase === "generating";
}

export function conversationReducer(
  conversation: Conversation,
  action: ConversationAction,
): Conversation {
  switch (action.type) {
    case "asked": {
      const turn: Turn = {
        id: conversation.nextId,
        question: action.question,
        // The server rewrites exactly when it gets history.
        phase: historyOf(conversation).length > 0 ? "rewriting" : "retrieving",
        standaloneQuestion: null,
        passages: [],
        provisionalText: "",
        result: null,
        error: null,
      };
      return { turns: [...conversation.turns, turn], nextId: conversation.nextId + 1 };
    }
    case "received":
      return updateTurnInProgress(conversation, (turn) => applyEvent(turn, action.event));
    case "stopped":
      return updateTurnInProgress(conversation, (turn) => ({ ...turn, phase: "stopped" }));
    case "cleared":
      return { turns: [], nextId: conversation.nextId };
    default:
      return unreachable(action);
  }
}

function applyEvent(turn: Turn, event: ChatStreamEvent): Turn {
  switch (event.type) {
    case "rewritten":
      return { ...turn, phase: "retrieving", standaloneQuestion: event.standalone_question };
    case "passages":
      return { ...turn, phase: "generating", passages: event.passages };
    case "token":
      return { ...turn, provisionalText: turn.provisionalText + event.text };
    case "done":
      return {
        ...turn,
        phase: "done",
        result: event.result,
        standaloneQuestion: event.result.standalone_question ?? turn.standaloneQuestion,
      };
    case "error":
      return { ...turn, phase: "error", error: event.error };
    default:
      return unreachable(event);
  }
}

function unreachable(value: never): never {
  throw new Error(`Unhandled: ${JSON.stringify(value)}`);
}

/** Only the last Turn can be in progress; anything for a finished Turn is late and dropped. */
function updateTurnInProgress(
  conversation: Conversation,
  update: (turn: Turn) => Turn,
): Conversation {
  const last = conversation.turns.at(-1);
  if (!last || !isInProgress(last)) return conversation;
  return { ...conversation, turns: [...conversation.turns.slice(0, -1), update(last)] };
}

/**
 * The `history` for the next request: completed Turns only, Refusals included. Stopped and
 * failed Turns are left out (ADR-0002). The server caps and truncates it further.
 */
export function historyOf(conversation: Conversation): HistoryTurn[] {
  return conversation.turns.flatMap((turn): HistoryTurn[] => {
    const result = turn.result;
    if (turn.phase !== "done" || !result) return [];
    const answer = result.type === "refusal" ? result.message : result.text;
    return [{ question: turn.question, answer }];
  });
}
