import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, test, vi } from "vite-plus/test";
import type { components } from "../api/schema";
import { ChatPage } from "../chat/ChatPage";
import type { OpenSection } from "../chat/passages";
import { server } from "../test/server";
import { POLL_INTERVAL_MS } from "./useReadiness";

type ReadinessChecks = components["schemas"]["ReadinessChecks"];

const QUESTION = "Which header carries the webhook signature?";
const SEND_PAUSED = "Questions can be sent once the Knowledge Base is ready.";

beforeEach(() => {
  // Fake clocks that still advance on their own, so Testing Library's waits keep working.
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  vi.useRealTimers();
  Reflect.deleteProperty(document, "hidden");
  Reflect.deleteProperty(navigator, "clipboard");
});

/** Hide or show the tab, the way the browser reports it. */
function setHidden(hidden: boolean) {
  Object.defineProperty(document, "hidden", { configurable: true, get: () => hidden });
  document.dispatchEvent(new Event("visibilitychange"));
}

function typeQuestion(question: string) {
  fireEvent.change(screen.getByRole("textbox", { name: /question/i }), {
    target: { value: question },
  });
}

/** A readiness body with the given checks failing, served with 200 or 503 as the backend does. */
function readiness(failing: Partial<ReadinessChecks>) {
  const checks = { database: { ok: true }, index: { ok: true }, llm: { ok: true }, ...failing };
  const ready = checks.database.ok && checks.index.ok;
  return HttpResponse.json(
    { status: ready ? "ready" : "not_ready", checks },
    { status: ready ? 200 : 503 },
  );
}

/** Serve each `GET /ready` from the next reply in line, the last one repeating. */
function serveReadiness(...replies: (() => Response)[]) {
  let count = 0;
  server.use(
    http.get("*/api/ready", () => {
      count += 1;
      const reply = replies[Math.min(count, replies.length) - 1];
      if (!reply) throw new Error("no reply for /ready");
      return reply();
    }),
  );
  return { requests: () => count };
}

function renderPage() {
  render(<ChatPage onOpenSection={vi.fn<OpenSection>()} />);
}

/** Open the banner's collapsed Details, returning the lines it lists. */
function openDetails(banner: HTMLElement) {
  const summary = within(banner).getByText("Details for whoever runs this");
  const list = within(banner).getByRole("list", { hidden: true });
  expect(list).not.toBeVisible();
  fireEvent.click(summary);
  expect(list).toBeVisible();
  return detailLines(banner);
}

/** The lines the banner's open Details lists. */
function detailLines(banner: HTMLElement) {
  return within(within(banner).getByRole("list"))
    .getAllByRole("listitem")
    .map((item) => item.textContent);
}

const CANT_REACH = {
  role: "alert",
  headline: "Can't reach the assistant right now",
  subline: "It may be restarting. This page reconnects automatically.",
} as const;
const NOT_SET_UP = {
  role: "status",
  headline: "The assistant isn't set up correctly",
  subline: "Answers will fail until whoever runs the assistant fixes its configuration.",
} as const;

describe("the copy for each state", () => {
  test.each([
    {
      state: "unreachable: a proxy's 502",
      reply: () =>
        new HttpResponse("<html>502 Bad Gateway</html>", {
          status: 502,
          headers: { "Content-Type": "text/html" },
        }),
      ...CANT_REACH,
      details: ["GET /api/ready → 502 Bad Gateway"],
    },
    {
      state: "unreachable: a network error",
      reply: () => HttpResponse.error(),
      ...CANT_REACH,
      details: ["GET /api/ready → network error"],
    },
    {
      state: "unreachable: a 503 without the readiness shape",
      reply: () => HttpResponse.json({ detail: "Service Unavailable" }, { status: 503 }),
      ...CANT_REACH,
      details: ["GET /api/ready → 503 Service Unavailable"],
    },
    {
      state: "database down",
      reply: () => readiness({ database: { ok: false, detail: "connection refused" } }),
      role: "alert",
      headline: "The Knowledge Base is unavailable",
      subline: "Questions can't be sent until it's back. This page checks again automatically.",
      details: ["database: connection refused"],
    },
    {
      state: "index building",
      reply: () => readiness({ index: { ok: false } }),
      role: "status",
      headline: "The Knowledge Base is still loading",
      subline:
        "This usually takes under a minute. You can type your question now and send it once loading finishes.",
      details: ["index: first sync since startup hasn't finished"],
    },
    {
      state: "index retrying",
      reply: () => readiness({ index: { ok: false, detail: "embedding failed: timed out" } }),
      role: "alert",
      headline: "The Knowledge Base is having trouble loading",
      subline: "It retries automatically. If this persists, contact whoever runs the assistant.",
      details: ["index: embedding failed: timed out"],
    },
    {
      state: "llm auth_failed",
      reply: () => readiness({ llm: { ok: false, detail: "auth_failed" } }),
      ...NOT_SET_UP,
      details: [
        "llm: The API key was rejected. Set a valid ANTHROPIC_API_KEY in .env and restart the backend.",
      ],
    },
    {
      state: "llm model_missing",
      reply: () =>
        readiness({
          llm: { ok: false, detail: "model_missing", command: "ollama pull llama3.2:3b" },
        }),
      ...NOT_SET_UP,
      details: ["llm: The model isn't pulled. Run: ollama pull llama3.2:3bCopy"],
    },
  ])("$state", async ({ reply, role, headline, subline, details }) => {
    serveReadiness(reply);
    renderPage();

    const banner = await screen.findByRole(role, { name: headline });
    expect(banner).toHaveTextContent(subline);
    expect(openDetails(banner)).toEqual(details);
  });
});

test("the model_missing command has a copy button", async () => {
  const writeText = vi.fn<(text: string) => Promise<void>>().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
  serveReadiness(() =>
    readiness({ llm: { ok: false, detail: "model_missing", command: "ollama pull llama3.2:3b" } }),
  );
  renderPage();
  const banner = await screen.findByRole("status", { name: NOT_SET_UP.headline });
  openDetails(banner);

  fireEvent.click(within(banner).getByRole("button", { name: "Copy" }));

  expect(await within(banner).findByRole("button", { name: "Copied" })).toBeInTheDocument();
  expect(writeText).toHaveBeenCalledWith("ollama pull llama3.2:3b");
});

describe("an llm that reports unavailable", () => {
  // The index failing too keeps a banner up, so what it lists shows whether the llm is held back.
  const BUILDING = "index: first sync since startup hasn't finished";
  const UNAVAILABLE = "llm: The configured provider couldn't be reached.";

  test("is held back for one check, then shown once the next says it again", async () => {
    serveReadiness(
      () => readiness({ index: { ok: false }, llm: { ok: false, detail: "unavailable" } }),
      () => readiness({ llm: { ok: false, detail: "unavailable" } }),
    );
    renderPage();
    const loading = await screen.findByRole("status", {
      name: "The Knowledge Base is still loading",
    });
    expect(openDetails(loading)).toEqual([BUILDING]);

    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);

    const banner = await screen.findByRole("status", { name: "The AI provider isn't responding" });
    expect(banner).toHaveTextContent(
      "Answers may fail. You can still try, and this page checks again automatically.",
    );
    // Details stays open across the change of state.
    expect(detailLines(banner)).toEqual([UNAVAILABLE]);
  });

  test("isn't shown when it's the blip before the first probe answers", async () => {
    const ready = serveReadiness(
      () => readiness({ index: { ok: false }, llm: { ok: false, detail: "unavailable" } }),
      () => readiness({ index: { ok: false } }),
    );
    renderPage();
    const banner = await screen.findByRole("status", {
      name: "The Knowledge Base is still loading",
    });
    expect(openDetails(banner)).toEqual([BUILDING]);

    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
    await waitFor(() => expect(ready.requests()).toBe(2));

    expect(detailLines(banner)).toEqual([BUILDING]);
  });

  test("an llm detail this page doesn't know reads as unavailable", async () => {
    serveReadiness(() =>
      HttpResponse.json({
        status: "ready",
        checks: {
          database: { ok: true },
          index: { ok: true },
          llm: { ok: false, detail: "quota" },
        },
      }),
    );
    renderPage();

    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);

    const banner = await screen.findByRole("status", { name: "The AI provider isn't responding" });
    expect(openDetails(banner)).toEqual(["llm: The configured provider couldn't be reached."]);
  });
});

describe("when several checks fail", () => {
  test("the database outranks the index and the llm, and Details lists all three", async () => {
    serveReadiness(() =>
      readiness({
        database: { ok: false, detail: "connection refused" },
        index: { ok: false, detail: "connection refused" },
        llm: { ok: false, detail: "auth_failed" },
      }),
    );
    renderPage();

    const banner = await screen.findByRole("alert", { name: "The Knowledge Base is unavailable" });
    expect(openDetails(banner)).toEqual([
      "database: connection refused",
      "index: connection refused",
      "llm: The API key was rejected. Set a valid ANTHROPIC_API_KEY in .env and restart the backend.",
    ]);
  });

  test("the index outranks the llm", async () => {
    serveReadiness(() =>
      readiness({
        index: { ok: false },
        llm: { ok: false, detail: "model_missing", command: "ollama pull llama3.2:3b" },
      }),
    );
    renderPage();

    const banner = await screen.findByRole("status", {
      name: "The Knowledge Base is still loading",
    });
    expect(openDetails(banner)).toHaveLength(2);
  });
});

describe("the composer", () => {
  test.each([
    { state: "database down", failing: { database: { ok: false, detail: "connection refused" } } },
    { state: "index building", failing: { index: { ok: false } } },
  ])("while $state, Send waits, with a reason, but typing doesn't", async ({ failing }) => {
    serveReadiness(() => readiness(failing));
    renderPage();
    await screen.findByText("Details for whoever runs this");

    typeQuestion(QUESTION);

    expect(screen.getByRole("textbox", { name: /question/i })).toBeEnabled();
    const send = screen.getByRole("button", { name: "Send" });
    expect(send).toBeDisabled();
    expect(send).toHaveAccessibleDescription(SEND_PAUSED);
    expect(
      screen.getByRole("button", { name: "What is the API rate limit for a Business client?" }),
    ).toBeDisabled();
  });

  test.each([
    {
      state: "the llm failing",
      reply: () => readiness({ llm: { ok: false, detail: "auth_failed" } }),
    },
    { state: "the backend unreachable", reply: () => HttpResponse.error() },
  ])("with $state, Send still works", async ({ reply }) => {
    serveReadiness(reply);
    renderPage();
    await screen.findByText("Details for whoever runs this");

    typeQuestion(QUESTION);

    expect(screen.getByRole("button", { name: "Send" })).toBeEnabled();
    expect(screen.queryByText(SEND_PAUSED)).not.toBeInTheDocument();
  });

  test("on recovery the banner goes quietly and focus stays in the composer", async () => {
    serveReadiness(
      () => readiness({ index: { ok: false } }),
      () => readiness({}),
    );
    renderPage();
    await screen.findByRole("status", { name: "The Knowledge Base is still loading" });
    const composer = screen.getByRole("textbox", { name: /question/i });
    composer.focus();
    typeQuestion(QUESTION);

    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);

    await waitFor(() => expect(screen.getByRole("button", { name: "Send" })).toBeEnabled());
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(composer).toHaveFocus();
    expect(composer).toHaveValue(QUESTION);
  });
});

describe("polling", () => {
  test("repeats every 5 s while a check fails and stops once all pass", async () => {
    const ready = serveReadiness(
      () => readiness({ index: { ok: false } }),
      () => readiness({ index: { ok: false } }),
      () => readiness({}),
    );
    renderPage();
    await waitFor(() => expect(ready.requests()).toBe(1));

    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
    await waitFor(() => expect(ready.requests()).toBe(2));
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
    await waitFor(() => expect(ready.requests()).toBe(3));
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 4);

    expect(ready.requests()).toBe(3);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  test("pauses while the tab is hidden and checks as soon as it's back", async () => {
    const ready = serveReadiness(() => readiness({ index: { ok: false } }));
    renderPage();
    await waitFor(() => expect(ready.requests()).toBe(1));

    setHidden(true);
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 4);
    expect(ready.requests()).toBe(1);

    setHidden(false);
    await waitFor(() => expect(ready.requests()).toBe(2));
  });

  test.each([
    { code: "index_not_ready", title: "The Knowledge Base is still loading" },
    { code: "retrieval_unavailable", title: "The Knowledge Base can't be reached right now" },
    { code: "llm_unavailable", title: "The assistant couldn't finish this answer" },
  ] as const)("checks again once after a Turn fails with $code", async ({ code, title }) => {
    const ready = serveReadiness(
      () => readiness({}),
      () => readiness({ index: { ok: false, detail: "connection refused" } }),
    );
    server.use(
      http.post("*/api/chat", () =>
        HttpResponse.json({ error: { code, message: "Not now." } }, { status: 503 }),
      ),
    );
    renderPage();
    await waitFor(() => expect(ready.requests()).toBe(1));

    typeQuestion(QUESTION);
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    // The card records what happened to that Turn; the banner shows the stack now.
    const turn = within(await screen.findByRole("article", { name: QUESTION }));
    expect(await turn.findByRole("alert")).toHaveTextContent(title);
    expect(
      await screen.findByRole("alert", { name: "The Knowledge Base is having trouble loading" }),
    ).toBeInTheDocument();
    expect(ready.requests()).toBe(2);
  });

  test("doesn't check again after a Turn fails for a reason readiness can't explain", async () => {
    const ready = serveReadiness(() => readiness({}));
    server.use(
      http.post("*/api/chat", () =>
        HttpResponse.json(
          { error: { code: "validation_error", message: "Too long." } },
          { status: 422 },
        ),
      ),
    );
    renderPage();
    await waitFor(() => expect(ready.requests()).toBe(1));

    typeQuestion(QUESTION);
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText("Too long.");
    await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);

    expect(ready.requests()).toBe(1);
  });
});
