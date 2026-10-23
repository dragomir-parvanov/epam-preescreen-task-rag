import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, test, vi } from "vite-plus/test";
import type { components } from "../api/schema";
import { READY, server } from "../test/server";
import { sseChannel, sseEvents } from "../test/sse";
import { ChatPage } from "./ChatPage";

type Passage = components["schemas"]["Passage"];
type ChatStreamEvent = components["schemas"]["ChatStreamEvent"];

const signing: Passage = {
  id: "nimbus-api-webhooks#signing",
  article: { id: "nimbus-api-webhooks", title: "Nimbus API and Webhooks" },
  section: { id: "webhook-signing", path: ["Nimbus API and Webhooks", "Webhooks", "Signing"] },
  text: "Every delivery carries an X-Nimbus-Signature header, an HMAC-SHA256 of the body.",
  applies_to: ["v3"],
  status: "current",
  score: 0.81,
};
const legacySigning: Passage = {
  id: "nimbus-v2-legacy#signing",
  article: { id: "nimbus-v2-legacy", title: "Nimbus v2 Legacy Reference" },
  section: { id: "v2-webhooks", path: ["Nimbus v2 Legacy Reference", "Webhooks"] },
  text: "On v2, deliveries are signed with HMAC-SHA1 in the X-Nimbus-Sig header.",
  applies_to: ["v2"],
  status: "deprecated",
  score: 0.74,
};
const rateLimits: Passage = {
  id: "nimbus-plan-tiers#rate-limits",
  article: { id: "nimbus-plan-tiers", title: "Nimbus Plan Tiers" },
  section: { id: "rate-limits", path: ["Nimbus Plan Tiers", "Rate limits"] },
  text: "Business clients get 600 API requests per minute.",
  applies_to: ["v3"],
  status: "current",
  score: 0.42,
};

const QUESTION = "Which header carries the webhook signature?";

function answerDone(text = "Use the X-Nimbus-Signature header [1]."): ChatStreamEvent {
  return {
    type: "done",
    result: {
      type: "answer",
      text,
      citations: [{ n: 1, passage: signing }],
      retrieved_passages: [rateLimits, signing],
      standalone_question: null,
    },
  };
}

/** Serve each `POST /chat` from the next script in line, recording what was sent. */
function serveTurns(...scripts: (() => Response)[]) {
  const requests: unknown[] = [];
  server.use(
    http.post("*/api/chat", async ({ request }) => {
      requests.push(await request.json());
      const script = scripts[requests.length - 1];
      if (!script) throw new Error(`no script for request ${requests.length}`);
      return script();
    }),
  );
  return requests;
}

/**
 * Render the page and let its first `GET /ready` (all ok) be answered before the test asks
 * anything. Under MSW 3 in Node, a `/ready` answered while a held SSE stream (`sseChannel`) is
 * open was seen to end that stream early, after its first chunk; browsers don't do this.
 */
async function renderPage() {
  const onOpenSection = vi.fn<(passage: Passage) => void>();
  const ready = vi.fn<() => Response>(() => HttpResponse.json(READY));
  server.use(http.get("*/api/ready", ready));
  render(<ChatPage onOpenSection={onOpenSection} />);
  await waitFor(() => expect(ready).toHaveBeenCalled());
  return { onOpenSection };
}

function ask(question: string) {
  fireEvent.change(screen.getByRole("textbox", { name: /question/i }), {
    target: { value: question },
  });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
}

function turn(question: string) {
  return within(screen.getByRole("article", { name: question }));
}

async function askAndFinish(question: string) {
  ask(question);
  await waitFor(() => expect(screen.getByRole("button", { name: "Send" })).toBeInTheDocument());
  return turn(question);
}

describe("the empty state", () => {
  test("offers suggested questions that ask themselves when clicked", async () => {
    const requests = serveTurns(() => sseEvents([answerDone()]));
    await renderPage();

    fireEvent.click(
      screen.getByRole("button", { name: "What is the API rate limit for a Business client?" }),
    );

    expect(
      await screen.findByRole("article", {
        name: "What is the API rate limit for a Business client?",
      }),
    ).toBeInTheDocument();
    expect(requests[0]).toMatchObject({
      question: "What is the API rate limit for a Business client?",
    });
  });
});

describe("a first Turn", () => {
  test("shows progress, then streams text with markers hidden, then the cited Answer", async () => {
    const channel = sseChannel();
    serveTurns(() => channel.response());
    await renderPage();

    ask(QUESTION);
    const t = turn(QUESTION);
    expect(await t.findByText("Searching the Knowledge Base…")).toBeInTheDocument();

    channel.send({ type: "passages", passages: [rateLimits, signing] });
    expect(await t.findByText("Found 2 Passages. Writing the answer…")).toBeInTheDocument();

    channel.send({ type: "token", text: "Use the X-Nimbus-Signature" });
    channel.send({ type: "token", text: " header [2]." });
    expect(await t.findByText("Use the X-Nimbus-Signature header.")).toBeInTheDocument();
    expect(t.queryByText(/\[2\]/)).not.toBeInTheDocument();

    channel.send(answerDone());
    const chip = await t.findByRole("button", { name: "Citation 1" });
    expect(chip).toBeInTheDocument();
    expect(t.queryByRole("button", { name: "Citation 2" })).not.toBeInTheDocument();
    expect(t.getByRole("list", { name: "Citations" })).toHaveTextContent(
      "Nimbus API and Webhooks › Webhooks › Signing",
    );
    expect(t.queryByText(/Searched for/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send" })).toBeInTheDocument();
  });
});

describe("a Follow-up Question", () => {
  test("sends the earlier Turn as history and shows what was searched for", async () => {
    const channel = sseChannel();
    const requests = serveTurns(
      () => sseEvents([{ type: "passages", passages: [signing] }, answerDone()]),
      () => channel.response(),
    );
    await renderPage();
    await askAndFinish(QUESTION);

    ask("and on v2?");
    const followUp = turn("and on v2?");
    expect(await followUp.findByText("Understanding the follow-up…")).toBeInTheDocument();
    channel.send({
      type: "rewritten",
      standalone_question: "Which header carries the webhook signature on v2?",
    });

    expect(
      await followUp.findByText("Which header carries the webhook signature on v2?"),
    ).toBeInTheDocument();
    expect(followUp.getByText(/Searched for/)).toBeInTheDocument();
    expect(requests[1]).toEqual({
      question: "and on v2?",
      history: [{ question: QUESTION, answer: "Use the X-Nimbus-Signature header [1]." }],
    });
  });

  test("doesn't show 'Searched for' when the rewrite is what the CSM typed", async () => {
    serveTurns(
      () => sseEvents([answerDone()]),
      () =>
        sseEvents([
          { type: "rewritten", standalone_question: "Does Nimbus support LDAP?" },
          {
            type: "done",
            result: {
              type: "answer",
              text: "No [1].",
              citations: [{ n: 1, passage: signing }],
              retrieved_passages: [signing],
              standalone_question: "Does Nimbus support LDAP?",
            },
          },
        ]),
    );
    await renderPage();
    await askAndFinish(QUESTION);

    const followUp = await askAndFinish("Does Nimbus support LDAP?");

    expect(followUp.getByRole("button", { name: "Citation 1" })).toBeInTheDocument();
    expect(followUp.queryByText(/Searched for/)).not.toBeInTheDocument();
  });
});

describe("an Answer", () => {
  test("a marker chip shows a quick look on focus, and on click opens its Citation's quote", async () => {
    serveTurns(() =>
      sseEvents([
        {
          type: "done",
          result: {
            type: "answer",
            text: "On v2 it is X-Nimbus-Sig [1].",
            citations: [{ n: 1, passage: legacySigning }],
            retrieved_passages: [legacySigning],
            standalone_question: null,
          },
        },
      ]),
    );
    await renderPage();
    const t = await askAndFinish(QUESTION);
    const chip = t.getByRole("button", { name: "Citation 1" });

    fireEvent.focus(chip);
    const quickLook = t.getByRole("tooltip");
    expect(quickLook).toHaveTextContent("Nimbus v2 Legacy Reference");
    expect(quickLook).toHaveTextContent("Webhooks");
    expect(quickLook).toHaveTextContent("v2");
    expect(quickLook).toHaveTextContent("Deprecated");
    expect(quickLook).toHaveTextContent("On v2, deliveries are signed");
    fireEvent.blur(chip);
    expect(t.queryByRole("tooltip")).not.toBeInTheDocument();

    fireEvent.click(chip);
    const row = within(t.getByRole("list", { name: "Citations" }));
    expect(row.getByRole("button", { expanded: true })).toHaveTextContent(
      "Nimbus v2 Legacy Reference",
    );
    expect(row.getByText(legacySigning.text)).toBeInTheDocument();
  });

  test("a Citation row expands to its verbatim quote and offers Open Section", async () => {
    serveTurns(() => sseEvents([answerDone()]));
    const { onOpenSection } = await renderPage();
    const t = await askAndFinish(QUESTION);
    const citations = within(t.getByRole("list", { name: "Citations" }));
    expect(citations.queryByText(signing.text)).not.toBeInTheDocument();

    fireEvent.click(citations.getByRole("button", { name: /Nimbus API and Webhooks/ }));
    fireEvent.click(citations.getByRole("button", { name: "Open Section" }));

    expect(citations.getByText(signing.text)).toBeInTheDocument();
    expect(onOpenSection).toHaveBeenCalledWith(signing);
  });

  test("a Citation's quote shows its Markdown formatted: a table, bold text and a heading", async () => {
    const errorCodes: Passage = {
      ...signing,
      id: "nimbus-sso-saml#troubleshooting-1",
      article: { id: "nimbus-sso-saml", title: "Configuring SSO with SAML 2.0" },
      section: {
        id: "troubleshooting",
        path: ["Configuring SSO with SAML 2.0", "Troubleshooting"],
      },
      text: [
        "## Error codes",
        "",
        "Nimbus shows the code on the login page [2].",
        "",
        "| Code | Fix |",
        "|---|---|",
        "| AUTH-401 | Sync the IdP clock with NTP. |",
        "| AUTH-409 | Rename the account in **Settings > Users**. |",
      ].join("\n"),
    };
    serveTurns(() =>
      sseEvents([
        {
          type: "done",
          result: {
            type: "answer",
            text: "Sync the IdP clock [1].",
            citations: [{ n: 1, passage: errorCodes }],
            retrieved_passages: [errorCodes],
            standalone_question: null,
          },
        },
      ]),
    );
    await renderPage();
    const t = await askAndFinish(QUESTION);
    const citations = within(t.getByRole("list", { name: "Citations" }));

    fireEvent.click(citations.getByRole("button", { name: /Configuring SSO with SAML 2.0/ }));

    expect(citations.getByRole("heading", { name: "Error codes" })).toBeInTheDocument();
    const [, auth401, auth409] = within(citations.getByRole("table")).getAllByRole("row");
    expect(
      within(auth401 ?? document.body)
        .getAllByRole("cell")
        .map((cell) => cell.textContent),
    ).toEqual(["AUTH-401", "Sync the IdP clock with NTP."]);
    expect(
      within(auth409 ?? document.body).getByText("Settings > Users", { selector: "strong" }),
    ).toBeInTheDocument();
    // Verbatim, so a marker inside the quote stays as written rather than becoming a chip.
    expect(citations.getByText("Nimbus shows the code on the login page [2].")).toBeInTheDocument();
    expect(t.queryByRole("button", { name: "Citation 2" })).not.toBeInTheDocument();
    const quote = citations.getByRole("blockquote");
    expect(quote).not.toHaveTextContent("|");
    expect(quote).not.toHaveTextContent("**");
    expect(quote).not.toHaveTextContent("##");
  });

  test("lists every retrieved Passage behind a toggle, marked cited or not cited", async () => {
    serveTurns(() => sseEvents([answerDone()]));
    await renderPage();
    const t = await askAndFinish(QUESTION);
    expect(t.queryByRole("list", { name: "Retrieved Passages" })).not.toBeInTheDocument();

    fireEvent.click(t.getByRole("button", { name: "Show all 2 retrieved Passages" }));

    const items = within(t.getByRole("list", { name: "Retrieved Passages" })).getAllByRole(
      "listitem",
    );
    expect(items[0]).toHaveTextContent("Nimbus Plan Tiers › Rate limits");
    expect(items[0]).toHaveTextContent("not cited");
    expect(items[1]).toHaveTextContent("Nimbus API and Webhooks › Webhooks › Signing");
    expect(items[1]).not.toHaveTextContent("not cited");
    expect(items[1]).toHaveTextContent("cited");
    expect(items[0]).not.toHaveTextContent("0.42");
  });
});

test("an Uncited Answer warns and lists the retrieved Passages, not cited", async () => {
  serveTurns(() =>
    sseEvents([
      {
        type: "done",
        result: {
          type: "uncited_answer",
          text: "Use the X-Nimbus-Signature header.",
          retrieved_passages: [signing, rateLimits],
          standalone_question: null,
        },
      },
    ]),
  );
  const { onOpenSection } = await renderPage();
  const t = await askAndFinish(QUESTION);

  expect(t.getByText(/didn't point to any Passage/)).toBeInTheDocument();
  expect(t.getByText("Use the X-Nimbus-Signature header.")).toBeInTheDocument();
  const retrieved = within(t.getByRole("list", { name: "Retrieved, not cited" }));
  expect(retrieved.getAllByRole("listitem")).toHaveLength(2);
  expect(t.queryByRole("button", { name: /Citation \d/ })).not.toBeInTheDocument();

  fireEvent.click(retrieved.getByRole("button", { name: /Nimbus Plan Tiers/ }));
  fireEvent.click(retrieved.getByRole("button", { name: "Open Section" }));
  expect(onOpenSection).toHaveBeenCalledWith(rateLimits);
});

test("a Retrieved, not cited row shows its quote's Markdown formatted", async () => {
  const limits: Passage = {
    ...rateLimits,
    text: "**Business** clients get 600 requests a minute.",
  };
  serveTurns(() =>
    sseEvents([
      {
        type: "done",
        result: {
          type: "uncited_answer",
          text: "Business clients get 600.",
          retrieved_passages: [limits],
          standalone_question: null,
        },
      },
    ]),
  );
  await renderPage();
  const t = await askAndFinish(QUESTION);
  const retrieved = within(t.getByRole("list", { name: "Retrieved, not cited" }));

  fireEvent.click(retrieved.getByRole("button", { name: /Nimbus Plan Tiers/ }));

  expect(retrieved.getByText("Business", { selector: "strong" })).toBeInTheDocument();
  expect(retrieved.getByRole("blockquote")).toHaveTextContent(
    "Business clients get 600 requests a minute.",
  );
  expect(retrieved.getByRole("blockquote")).not.toHaveTextContent("**");
});

test("a Refusal shows the server's message and no reason or Citations", async () => {
  serveTurns(() =>
    sseEvents([
      {
        type: "done",
        result: {
          type: "refusal",
          message: "The Knowledge Base doesn't cover this question.",
          reason: "no_relevant_passages",
          retrieved_passages: [],
          standalone_question: null,
        },
      },
    ]),
  );
  await renderPage();
  const t = await askAndFinish("How much does the Enterprise tier cost per seat?");

  expect(t.getByText("The Knowledge Base doesn't cover this question.")).toBeInTheDocument();
  expect(t.queryByText(/no_relevant_passages/)).not.toBeInTheDocument();
  expect(t.queryByRole("list", { name: "Citations" })).not.toBeInTheDocument();
});

describe("Stop", () => {
  test("keeps the partial text, labels it Stopped and leaves it out of the next history", async () => {
    const channel = sseChannel();
    const requests = serveTurns(
      () => sseEvents([answerDone()]),
      () => channel.response(),
      () => sseEvents([answerDone()]),
    );
    await renderPage();
    await askAndFinish(QUESTION);

    ask("and on v2?");
    channel.send({ type: "passages", passages: [legacySigning] });
    channel.send({ type: "token", text: "On v2 it is" });
    const stopped = turn("and on v2?");
    expect(await stopped.findByText("On v2 it is")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Stop" }));

    expect(await stopped.findByText("Stopped")).toBeInTheDocument();
    expect(stopped.getByText("On v2 it is")).toBeInTheDocument();
    await askAndFinish("and on v3?");
    expect(requests[2]).toEqual({
      question: "and on v3?",
      history: [{ question: QUESTION, answer: "Use the X-Nimbus-Signature header [1]." }],
    });
  });
});

describe("errors", () => {
  test("a pre-stream 503 shows its card, and Ask again resends the question", async () => {
    const requests = serveTurns(
      () =>
        HttpResponse.json(
          {
            error: {
              code: "index_not_ready",
              message: "Ingestion hasn't finished yet.",
              request_id: "req-7f3a",
            },
          },
          { status: 503 },
        ),
      () => sseEvents([answerDone()]),
    );
    await renderPage();
    const failed = await askAndFinish(QUESTION);

    const card = within(failed.getByRole("alert"));
    expect(card.getByText("The Knowledge Base is still loading")).toBeInTheDocument();
    expect(card.getByText("Ingestion hasn't finished yet.")).toBeInTheDocument();
    expect(card.getByText("index_not_ready")).toBeInTheDocument();
    expect(card.getByText("req-7f3a")).toBeInTheDocument();

    fireEvent.click(card.getByRole("button", { name: "Ask again" }));

    await waitFor(() => expect(requests).toHaveLength(2));
    expect(requests[1]).toEqual({ question: QUESTION, history: [] });
    expect(
      await screen.findByRole("button", { name: "Citation 1" }, { timeout: 2000 }),
    ).toBeInTheDocument();
  });

  test("a mid-stream error keeps the partial text above the card, with Ask again", async () => {
    serveTurns(() =>
      sseEvents([
        { type: "passages", passages: [signing] },
        { type: "token", text: "Use the X-Nimbus" },
        { type: "error", error: { code: "llm_timeout", message: "The model took too long." } },
      ]),
    );
    await renderPage();
    const failed = await askAndFinish(QUESTION);

    expect(failed.getByText("Use the X-Nimbus")).toBeInTheDocument();
    const card = within(failed.getByRole("alert"));
    expect(card.getByText("The assistant couldn't finish this answer")).toBeInTheDocument();
    expect(card.getByText("The model took too long.")).toBeInTheDocument();
    expect(card.getByRole("button", { name: "Ask again" })).toBeInTheDocument();
  });
});

test("New conversation clears the Turns and their history", async () => {
  const requests = serveTurns(
    () => sseEvents([answerDone()]),
    () => sseEvents([answerDone()]),
  );
  await renderPage();
  await askAndFinish(QUESTION);

  fireEvent.click(screen.getByRole("button", { name: "New conversation" }));

  expect(screen.queryByRole("article")).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "What is the API rate limit for a Business client?" }),
  ).toBeInTheDocument();
  await askAndFinish("Does Nimbus support LDAP?");
  expect(requests[1]).toEqual({ question: "Does Nimbus support LDAP?", history: [] });
});
