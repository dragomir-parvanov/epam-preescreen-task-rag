import { useEffect, useReducer, useRef } from "react";
import type { components } from "../api/schema";
import { streamChat } from "./chatStream";
import {
  conversationReducer,
  emptyConversation,
  historyOf,
  isInProgress,
  type Turn,
} from "./conversation";

type ErrorBody = components["schemas"]["ErrorBody"];

export type ConversationControls = {
  turns: Turn[];
  /** A Turn is in progress: the composer offers Stop instead of Send. */
  busy: boolean;
  ask: (question: string) => void;
  stop: () => void;
  /** New conversation: drop every Turn, stopping any in progress. */
  reset: () => void;
};

/**
 * The Conversation in this tab, wired to `POST /api/chat`. Nothing is persisted. `onTurnError`
 * hears each Turn that ends in an error.
 */
export function useConversation({
  onTurnError,
}: { onTurnError?: (error: ErrorBody) => void } = {}): ConversationControls {
  const [conversation, dispatch] = useReducer(conversationReducer, emptyConversation);
  const inFlight = useRef<AbortController | null>(null);

  const abort = () => {
    inFlight.current?.abort();
    inFlight.current = null;
  };

  // Leaving the page drops the stream.
  useEffect(() => () => inFlight.current?.abort(), []);

  const ask = (question: string) => {
    abort();
    const controller = new AbortController();
    inFlight.current = controller;
    const request = { question, history: historyOf(conversation) };
    dispatch({ type: "asked", question });
    void (async () => {
      for await (const event of streamChat(request, controller.signal)) {
        // An event can be in hand when Stop lands; it belongs to a Turn that's over.
        if (controller.signal.aborted) return;
        dispatch({ type: "received", event });
        if (event.type === "error") onTurnError?.(event.error);
      }
    })();
  };

  const last = conversation.turns.at(-1);
  return {
    turns: conversation.turns,
    busy: last !== undefined && isInProgress(last),
    ask,
    stop: () => {
      abort();
      dispatch({ type: "stopped" });
    },
    reset: () => {
      abort();
      dispatch({ type: "cleared" });
    },
  };
}
