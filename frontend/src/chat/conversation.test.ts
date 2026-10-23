import { describe, expect, test } from "vite-plus/test";
import type { components } from "../api/schema";
import type { ChatStreamEvent } from "./chatStream";
import {
  conversationReducer,
  emptyConversation,
  historyOf,
  type Conversation,
  type ConversationAction,
} from "./conversation";

type Passage = components["schemas"]["Passage"];

const passage: Passage = {
  id: "plan-tiers#2",
  article: { id: "nimbus-plan-tiers", title: "Nimbus Plan Tiers" },
  section: { id: "rate-limits", path: ["Nimbus Plan Tiers", "Rate limits"] },
  text: "Business: 600 requests per minute.",
  applies_to: ["v3"],
  status: "current",
  score: 0.8,
};

function run(actions: ConversationAction[], from: Conversation = emptyConversation) {
  return actions.reduce(conversationReducer, from);
}

const received = (event: ChatStreamEvent): ConversationAction => ({ type: "received", event });

function answered(question: string, text: string): ConversationAction[] {
  return [
    { type: "asked", question },
    received({ type: "passages", passages: [passage] }),
    received({
      type: "done",
      result: {
        type: "answer",
        text,
        citations: [{ n: 1, passage }],
        retrieved_passages: [passage],
        standalone_question: null,
      },
    }),
  ];
}

function lastTurn(conversation: Conversation) {
  const turn = conversation.turns.at(-1);
  if (!turn) throw new Error("no Turns");
  return turn;
}

describe("a first Turn", () => {
  test("starts by searching, since there's nothing to rewrite", () => {
    const turn = lastTurn(run([{ type: "asked", question: "What is the Business rate limit?" }]));

    expect(turn).toMatchObject({
      question: "What is the Business rate limit?",
      phase: "retrieving",
    });
  });

  test("moves to generating once Passages arrive", () => {
    const turn = lastTurn(
      run([
        { type: "asked", question: "What is the Business rate limit?" },
        received({ type: "passages", passages: [passage] }),
      ]),
    );

    expect(turn.phase).toBe("generating");
    expect(turn.passages).toEqual([passage]);
  });

  test("accumulates provisional text from tokens", () => {
    const turn = lastTurn(
      run([
        { type: "asked", question: "What is the Business rate limit?" },
        received({ type: "passages", passages: [passage] }),
        received({ type: "token", text: "600 requests " }),
        received({ type: "token", text: "per minute [1]." }),
      ]),
    );

    expect(turn.provisionalText).toBe("600 requests per minute [1].");
  });

  test("ends with the authoritative result from done", () => {
    const turn = lastTurn(run(answered("What is the Business rate limit?", "600 per minute [1].")));

    expect(turn.phase).toBe("done");
    expect(turn.result).toMatchObject({ type: "answer", text: "600 per minute [1]." });
  });

  test("ends in error on an error event, keeping the partial text", () => {
    const turn = lastTurn(
      run([
        { type: "asked", question: "What is the Business rate limit?" },
        received({ type: "token", text: "600 requests" }),
        received({ type: "error", error: { code: "llm_timeout", message: "Too slow." } }),
      ]),
    );

    expect(turn).toMatchObject({
      phase: "error",
      provisionalText: "600 requests",
      error: { code: "llm_timeout", message: "Too slow." },
    });
  });
});

describe("a Follow-up Question", () => {
  test("starts by rewriting, then searches with the Standalone Question", () => {
    const afterFirst = run(answered("What is the Business rate limit?", "600 per minute [1]."));

    const asked = run([{ type: "asked", question: "what about Enterprise?" }], afterFirst);
    const rewritten = run(
      [
        received({
          type: "rewritten",
          standalone_question: "What is the API rate limit for an Enterprise client?",
        }),
      ],
      asked,
    );

    expect(lastTurn(asked).phase).toBe("rewriting");
    expect(lastTurn(rewritten)).toMatchObject({
      phase: "retrieving",
      standaloneQuestion: "What is the API rate limit for an Enterprise client?",
    });
  });
});

describe("Stop", () => {
  test("keeps the partial text and ignores anything that arrives after it", () => {
    const turn = lastTurn(
      run([
        { type: "asked", question: "What is the Business rate limit?" },
        received({ type: "token", text: "600 requests" }),
        { type: "stopped" },
        received({ type: "token", text: " per minute" }),
      ]),
    );

    expect(turn).toMatchObject({ phase: "stopped", provisionalText: "600 requests" });
  });
});

describe("history", () => {
  test("is built from completed Turns only: stopped and failed Turns are left out", () => {
    const conversation = run([
      ...answered("What is the Business rate limit?", "600 per minute [1]."),
      { type: "asked", question: "and Enterprise?" },
      received({ type: "token", text: "Half" }),
      { type: "stopped" },
      { type: "asked", question: "and Starter?" },
      received({ type: "error", error: { code: "llm_unavailable", message: "Down." } }),
      ...answered("Does Nimbus support LDAP?", "No [1]."),
    ]);

    expect(historyOf(conversation)).toEqual([
      { question: "What is the Business rate limit?", answer: "600 per minute [1]." },
      { question: "Does Nimbus support LDAP?", answer: "No [1]." },
    ]);
  });

  test("carries an Uncited Answer's text and a Refusal's message", () => {
    const conversation = run([
      { type: "asked", question: "Is there an annual discount?" },
      received({
        type: "done",
        result: {
          type: "refusal",
          message: "The Knowledge Base doesn't cover this.",
          reason: "not_in_context",
          retrieved_passages: [],
          standalone_question: null,
        },
      }),
      { type: "asked", question: "What is JIT provisioning?" },
      received({
        type: "done",
        result: {
          type: "uncited_answer",
          text: "Accounts are created at first login.",
          retrieved_passages: [passage],
          standalone_question: null,
        },
      }),
    ]);

    expect(historyOf(conversation)).toEqual([
      {
        question: "Is there an annual discount?",
        answer: "The Knowledge Base doesn't cover this.",
      },
      { question: "What is JIT provisioning?", answer: "Accounts are created at first login." },
    ]);
  });

  test("a question after only a stopped Turn is not a Follow-up", () => {
    const conversation = run([
      { type: "asked", question: "What is the Business rate limit?" },
      { type: "stopped" },
      { type: "asked", question: "What is the Business rate limit?" },
    ]);

    expect(lastTurn(conversation).phase).toBe("retrieving");
  });
});

test("clearing starts a new, empty Conversation", () => {
  const conversation = run([
    ...answered("What is the Business rate limit?", "600 per minute [1]."),
    { type: "cleared" },
  ]);

  expect(conversation.turns).toEqual([]);
  expect(historyOf(conversation)).toEqual([]);
});
