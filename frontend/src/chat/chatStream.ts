import { fetchClient } from "../api/client";
import type { components } from "../api/schema";

export type ChatRequest = components["schemas"]["ChatRequest"];
export type ChatStreamEvent = components["schemas"]["ChatStreamEvent"];
type ErrorBody = components["schemas"]["ErrorBody"];

const UNREACHABLE: ErrorBody = {
  code: "internal_error",
  message: "Couldn't reach the assistant. Check that the backend is running, then try again.",
};
const CUT_SHORT: ErrorBody = {
  code: "internal_error",
  message: "The connection to the assistant closed before the answer was finished.",
};
const GARBLED: ErrorBody = {
  code: "internal_error",
  message: "The assistant sent a reply this page couldn't read.",
};

/**
 * Ask one Turn over `POST /api/chat` and yield its stream events as they arrive.
 *
 * Every failure becomes the stream's last event, an `error`: a pre-stream HTTP status with the
 * error envelope, an `error` frame, an unreachable backend, or a stream that closes before
 * `done`. So unless `signal` aborts it, the stream always ends with exactly one `done` or
 * `error`. Aborting ends it quietly, with no further events.
 */
export async function* streamChat(
  request: ChatRequest,
  signal: AbortSignal,
): AsyncGenerator<ChatStreamEvent> {
  let body: ReadableStream<Uint8Array>;
  try {
    const { data, error, response } = await fetchClient.POST("/chat", {
      body: request,
      parseAs: "stream",
      signal,
    });
    if (!response.ok || !data) {
      yield { type: "error", error: error?.error ?? UNREACHABLE };
      return;
    }
    body = data;
  } catch {
    if (!signal.aborted) yield { type: "error", error: UNREACHABLE };
    return;
  }

  try {
    for await (const event of sseEvents(body)) {
      yield event;
      if (event.type === "done" || event.type === "error") return;
    }
    yield { type: "error", error: CUT_SHORT };
  } catch (error) {
    if (signal.aborted) return;
    yield { type: "error", error: error instanceof SyntaxError ? GARBLED : CUT_SHORT };
  }
}

/** Parse a `text/event-stream` body into the events its frames carry (WHATWG SSE framing). */
async function* sseEvents(body: ReadableStream<Uint8Array>): AsyncGenerator<ChatStreamEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let data: string[] = [];
  try {
    for (;;) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      const lines = buffer.split(/\r\n|\r|\n/);
      // The last piece may be a line that's still arriving, unless the body has ended.
      buffer = done ? "" : (lines.pop() ?? "");
      for (const line of lines) {
        if (line === "") {
          // A blank line dispatches the frame. Comment-only frames (`: ping`) carry no data.
          if (data.length > 0) yield parseEvent(data.join("\n"));
          data = [];
        } else if (line.startsWith("data:")) {
          data.push(line.slice(line.startsWith("data: ") ? 6 : 5));
        }
        // `event:` repeats the `type` inside `data`, and the backend sends no `id` or `retry`.
      }
      if (done) return;
    }
  } finally {
    // Also runs when the consumer stops early: let go of the connection.
    await reader.cancel().catch(() => undefined);
  }
}

const EVENT_TYPES: ReadonlySet<unknown> = new Set<ChatStreamEvent["type"]>([
  "rewritten",
  "passages",
  "token",
  "done",
  "error",
]);

function parseEvent(json: string): ChatStreamEvent {
  const value: unknown = JSON.parse(json);
  if (!isChatStreamEvent(value)) throw new SyntaxError(`Unknown chat stream event: ${json}`);
  return value;
}

// The backend validates each event against the same schema on the way out, so checking the
// discriminator is enough to tell a chat event from anything else on the wire.
function isChatStreamEvent(value: unknown): value is ChatStreamEvent {
  return (
    typeof value === "object" && value !== null && "type" in value && EVENT_TYPES.has(value.type)
  );
}
