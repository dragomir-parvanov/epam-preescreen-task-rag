import { http, HttpResponse } from "msw";
import { expect, test } from "vite-plus/test";
import type { components } from "../api/schema";
import { server } from "../test/server";
import { frame, sseResponse } from "../test/sse";
import { streamChat, type ChatStreamEvent } from "./chatStream";

type Passage = components["schemas"]["Passage"];

const passage: Passage = {
  id: "webhooks#3",
  article: { id: "nimbus-api-webhooks", title: "Nimbus API and Webhooks" },
  section: { id: "signing", path: ["Nimbus API and Webhooks", "Signing"] },
  text: "Every delivery carries an `X-Nimbus-Signature` header.",
  applies_to: ["v3"],
  status: "current",
  score: 0.82,
};

async function collect(events: AsyncIterable<ChatStreamEvent>): Promise<ChatStreamEvent[]> {
  const seen: ChatStreamEvent[] = [];
  for await (const event of events) seen.push(event);
  return seen;
}

function ask(signal = new AbortController().signal) {
  return streamChat({ question: "Which header carries the signature?", history: [] }, signal);
}

test("yields each event of the stream, even when frames are split across chunks", async () => {
  const done: ChatStreamEvent = {
    type: "done",
    result: {
      type: "answer",
      text: "The `X-Nimbus-Signature` header [1].",
      citations: [{ n: 1, passage }],
      retrieved_passages: [passage],
      standalone_question: null,
    },
  };
  const wire =
    frame({ type: "passages", passages: [passage] }) +
    ": ping\n\n" +
    frame({ type: "token", text: "The `X-Nimbus" }) +
    frame({ type: "token", text: "-Signature` header [1]." }) +
    frame(done);
  // Cut the wire into 7-byte chunks so frames, lines and JSON straddle reads.
  const chunks = wire.match(/[\s\S]{1,7}/g) ?? [];
  server.use(http.post("*/api/chat", () => sseResponse(chunks)));

  expect(await collect(ask())).toEqual([
    { type: "passages", passages: [passage] },
    { type: "token", text: "The `X-Nimbus" },
    { type: "token", text: "-Signature` header [1]." },
    done,
  ]);
});

test("sends the question and history as the request body", async () => {
  let body: unknown;
  server.use(
    http.post("*/api/chat", async ({ request }) => {
      body = await request.json();
      return sseResponse([]);
    }),
  );

  await collect(
    streamChat(
      { question: "and on v2?", history: [{ question: "Which header?", answer: "This one [1]." }] },
      new AbortController().signal,
    ),
  );

  expect(body).toEqual({
    question: "and on v2?",
    history: [{ question: "Which header?", answer: "This one [1]." }],
  });
});

test("turns a pre-stream error envelope into a closing error event", async () => {
  server.use(
    http.post("*/api/chat", () =>
      HttpResponse.json(
        { error: { code: "index_not_ready", message: "The Knowledge Base is still loading." } },
        { status: 503 },
      ),
    ),
  );

  expect(await collect(ask())).toEqual([
    {
      type: "error",
      error: { code: "index_not_ready", message: "The Knowledge Base is still loading." },
    },
  ]);
});

test("passes a mid-stream error event through and stops there", async () => {
  server.use(
    http.post("*/api/chat", () =>
      sseResponse([
        frame({ type: "passages", passages: [passage] }),
        frame({
          type: "error",
          error: { code: "llm_timeout", message: "The model took too long to answer." },
        }),
      ]),
    ),
  );

  const events = await collect(ask());

  expect(events.at(-1)).toEqual({
    type: "error",
    error: { code: "llm_timeout", message: "The model took too long to answer." },
  });
});

test("ends with an error event when the stream closes before done", async () => {
  server.use(
    http.post("*/api/chat", () => sseResponse([frame({ type: "token", text: "Half an" })])),
  );

  const events = await collect(ask());

  expect(events).toHaveLength(2);
  expect(events[1]).toMatchObject({ type: "error", error: { code: "internal_error" } });
});

test("ends with an error event when the backend can't be reached", async () => {
  server.use(http.post("*/api/chat", () => HttpResponse.error()));

  const events = await collect(ask());

  expect(events).toEqual([
    expect.objectContaining({
      type: "error",
      error: expect.objectContaining({ code: "internal_error" }),
    }),
  ]);
});

test("ends quietly, with no error event, when aborted mid-stream", async () => {
  server.use(
    http.post("*/api/chat", () =>
      sseResponse([frame({ type: "token", text: "Still writing" })], { hold: true }),
    ),
  );
  const controller = new AbortController();
  const seen: ChatStreamEvent[] = [];

  for await (const event of ask(controller.signal)) {
    seen.push(event);
    controller.abort();
  }

  expect(seen).toEqual([{ type: "token", text: "Still writing" }]);
});
