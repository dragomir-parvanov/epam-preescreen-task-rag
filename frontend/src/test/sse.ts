import { HttpResponse } from "msw";
import type { components } from "../api/schema";

type ChatStreamEvent = components["schemas"]["ChatStreamEvent"];

/** One SSE frame, as the backend writes it: `event: <type>` + `data: <json>`. */
export function frame(event: ChatStreamEvent): string {
  return `event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`;
}

/**
 * A `text/event-stream` response whose body is streamed chunk by chunk.
 *
 * Chunks are raw text, so a test can split frames anywhere. With `hold`, the stream stays open
 * after the last chunk, the way a slow model does, until the request is aborted.
 */
export function sseResponse(chunks: string[], { hold = false } = {}): HttpResponse<ReadableStream> {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      if (!hold) controller.close();
    },
  });
  return new HttpResponse(body, { headers: { "Content-Type": "text/event-stream" } });
}

/** A stream of whole frames, one chunk each. */
export function sseEvents(
  events: ChatStreamEvent[],
  options?: { hold?: boolean },
): HttpResponse<ReadableStream> {
  return sseResponse(events.map(frame), options);
}

/**
 * A stream the test feeds one event at a time, to assert what the CSM sees between events.
 * Serve it with `http.post("*\/api/chat", () => channel.response())`.
 */
export function sseChannel() {
  const encoder = new TextEncoder();
  let controller: ReadableStreamDefaultController<Uint8Array> | undefined;
  const body = new ReadableStream<Uint8Array>({
    start(c) {
      controller = c;
    },
  });
  return {
    response: () => new HttpResponse(body, { headers: { "Content-Type": "text/event-stream" } }),
    send(event: ChatStreamEvent) {
      controller?.enqueue(encoder.encode(frame(event)));
    },
  };
}
