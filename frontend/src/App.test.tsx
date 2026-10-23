import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { StrictMode } from "react";
import { afterEach, expect, test, vi } from "vite-plus/test";
import type { components } from "./api/schema";
import App from "./App";
import { server } from "./test/server";
import { sseEvents } from "./test/sse";

type Passage = components["schemas"]["Passage"];
type ArticleDetail = components["schemas"]["ArticleDetail"];
type ChatResult = components["schemas"]["ChatResult"];

const webhooks: ArticleDetail = {
  id: "nimbus-api-webhooks",
  title: "API Rate Limits and Webhooks",
  applies_to: ["v3"],
  status: "current",
  sections: [
    {
      id: "api-rate-limits-and-webhooks",
      path: ["API Rate Limits and Webhooks"],
      level: 1,
      markdown: "API access is available on the Business and Enterprise tiers.",
    },
    {
      id: "webhooks",
      path: ["API Rate Limits and Webhooks", "Webhooks"],
      level: 2,
      markdown: "## Webhooks\n\nNimbus posts an event to each registered endpoint.",
    },
    {
      id: "webhooks-signing",
      path: ["API Rate Limits and Webhooks", "Webhooks", "Signing"],
      level: 3,
      markdown:
        "### Signing\n\nEvery delivery is signed.\n\n| Header | Algorithm |\n|---|---|\n| `X-Nimbus-Signature` | HMAC-SHA256 |",
    },
  ],
};
const legacy: ArticleDetail = {
  id: "nimbus-v2-legacy",
  title: "Nimbus v2 Legacy Reference",
  applies_to: ["v2"],
  status: "deprecated",
  sections: [
    {
      id: "end-of-support",
      path: ["Nimbus v2 Legacy Reference", "End of support"],
      level: 2,
      markdown: "## End of support\n\nSupport for the legacy platform ends on 2027-03-31.",
    },
  ],
};

const signing: Passage = {
  id: "nimbus-api-webhooks#webhooks-signing#0",
  article: { id: webhooks.id, title: webhooks.title },
  section: {
    id: "webhooks-signing",
    path: ["API Rate Limits and Webhooks", "Webhooks", "Signing"],
  },
  text: "Every delivery is signed.",
  applies_to: ["v3"],
  status: "current",
  score: 0.81,
};
const endOfSupport: Passage = {
  id: "nimbus-v2-legacy#end-of-support#0",
  article: { id: legacy.id, title: legacy.title },
  section: { id: "end-of-support", path: ["Nimbus v2 Legacy Reference", "End of support"] },
  text: "Support for the legacy platform ends on 2027-03-31.",
  applies_to: ["v2"],
  status: "deprecated",
  score: 0.62,
};
const unknown: Passage = {
  ...signing,
  id: "nimbus-gone#intro#0",
  article: { id: "nimbus-gone", title: "A Removed Article" },
};

const QUESTION = "Which header carries the webhook signature?";

afterEach(() => {
  vi.restoreAllMocks();
});

/** Serve `GET /articles/{id}` from `articles`, with the backend's `not_found` envelope otherwise. */
function serveArticles(...articles: ArticleDetail[]) {
  const requested: string[] = [];
  server.use(
    http.get("*/api/articles/:articleId", ({ params }) => {
      const id = String(params.articleId);
      requested.push(id);
      const article = articles.find((a) => a.id === id);
      if (article) return HttpResponse.json(article);
      return HttpResponse.json(
        { error: { code: "not_found", message: `No Article with id '${id}'.` } },
        { status: 404 },
      );
    }),
  );
  return requested;
}

/** Render the app and ask one question, answered with `result`. */
async function renderAnswered(result: ChatResult) {
  server.use(http.post("*/api/chat", () => sseEvents([{ type: "done", result }])));
  render(
    <StrictMode>
      <QueryClientProvider client={new QueryClient()}>
        <App />
      </QueryClientProvider>
    </StrictMode>,
  );
  fireEvent.change(screen.getByRole("textbox", { name: /question/i }), {
    target: { value: QUESTION },
  });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Send" })).toBeInTheDocument());
  return within(screen.getByRole("article", { name: QUESTION }));
}

function cited(passage: Passage): ChatResult {
  return {
    type: "answer",
    text: "It's signed [1].",
    citations: [{ n: 1, passage }],
    retrieved_passages: [passage],
    standalone_question: null,
  };
}

/** Expand `passage`'s row in the named list and press its Open Section, the way a keyboard user does. */
function openSection(turn: ReturnType<typeof within>, list: string, passage: Passage) {
  const rows = within(turn.getByRole("list", { name: list }));
  const row = rows.getByRole("button", { name: new RegExp(passage.article.title) });
  if (row.getAttribute("aria-expanded") === "false") fireEvent.click(row);
  const button = rows.getByRole("button", { name: "Open Section" });
  button.focus();
  fireEvent.click(button);
  return button;
}

test("Open Section on a Citation opens its Article, scrolled to the highlighted Section", async () => {
  const requested = serveArticles(webhooks);
  const scrolled = vi.spyOn(Element.prototype, "scrollIntoView");
  const turn = await renderAnswered(cited(signing));

  openSection(turn, "Citations", signing);

  const panel = screen.getByRole("dialog", { name: webhooks.title });
  expect(panel).toHaveFocus();
  expect(within(panel).getByText("Loading the Article…")).toBeInTheDocument();

  const section = await within(panel).findByRole("region", { name: "Webhooks › Signing" });
  expect(section).toHaveAttribute("aria-current", "location");
  expect(within(section).getByRole("heading", { name: "Signing" })).toBeInTheDocument();
  expect(within(section).getByRole("table")).toHaveTextContent("X-Nimbus-Signature");
  expect(scrolled.mock.contexts).toContain(section);
  expect(within(panel).getByRole("region", { name: "Webhooks" })).not.toHaveAttribute(
    "aria-current",
  );
  expect(
    within(panel).getByText("API access is available on the Business and Enterprise tiers."),
  ).toBeInTheDocument();
  expect(within(panel).getByText("knowledge-base/nimbus-api-webhooks.md")).toBeInTheDocument();
  expect(within(panel).queryByText(/deprecated/i)).not.toBeInTheDocument();
  expect(new Set(requested)).toEqual(new Set(["nimbus-api-webhooks"]));
});

test("Escape closes the panel and returns focus to the Open Section button", async () => {
  serveArticles(webhooks);
  const turn = await renderAnswered(cited(signing));
  const button = openSection(turn, "Citations", signing);
  const panel = screen.getByRole("dialog", { name: webhooks.title });
  await within(panel).findByRole("region", { name: "Webhooks › Signing" });

  fireEvent.keyDown(panel, { key: "Escape" });

  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(button).toHaveFocus();
  expect(turn.getByText(/It's signed/)).toBeInTheDocument();
});

test("the close button and a click on the backdrop close the panel too", async () => {
  serveArticles(webhooks);
  const turn = await renderAnswered(cited(signing));

  openSection(turn, "Citations", signing);
  fireEvent.click(screen.getByRole("button", { name: "Close" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

  openSection(turn, "Citations", signing);
  fireEvent.click(await screen.findByText("Every delivery is signed."));
  expect(screen.getByRole("dialog")).toBeInTheDocument();
  fireEvent.click(screen.getByTestId("article-panel-backdrop"));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

test("reopening an Article uses the copy already fetched", async () => {
  const requested = serveArticles(webhooks);
  const turn = await renderAnswered(cited(signing));
  openSection(turn, "Citations", signing);
  await screen.findByRole("region", { name: "Webhooks › Signing" });
  fireEvent.click(screen.getByRole("button", { name: "Close" }));
  const fetched = requested.length;

  openSection(turn, "Citations", signing);

  expect(screen.getByRole("region", { name: "Webhooks › Signing" })).toBeInTheDocument();
  expect(requested).toHaveLength(fetched);
});

test("a deprecated Article, opened from a Passage that wasn't cited, shows its banner", async () => {
  serveArticles(legacy);
  const turn = await renderAnswered({
    type: "uncited_answer",
    text: "Support ends in 2027.",
    retrieved_passages: [endOfSupport],
    standalone_question: null,
  });

  openSection(turn, "Retrieved, not cited", endOfSupport);

  const panel = screen.getByRole("dialog", { name: legacy.title });
  expect(
    await within(panel).findByText(
      "This Article describes Nimbus v2, which is deprecated: end of support 2027-03-31.",
    ),
  ).toBeInTheDocument();
  expect(within(panel).getByText("v2")).toBeInTheDocument();
  expect(within(panel).getByText("Deprecated")).toBeInTheDocument();
  expect(within(panel).getByRole("region", { name: "End of support" })).toHaveAttribute(
    "aria-current",
    "location",
  );
});

test("an Article the Knowledge Base doesn't have shows the server's not_found message", async () => {
  serveArticles(webhooks);
  const turn = await renderAnswered(cited(unknown));

  openSection(turn, "Citations", unknown);

  const panel = screen.getByRole("dialog", { name: unknown.article.title });
  expect(await within(panel).findByRole("alert")).toHaveTextContent(
    "No Article with id 'nimbus-gone'.",
  );
  expect(within(panel).getByText("not_found")).toBeInTheDocument();
});

test("a reply that isn't the error envelope shows a stand-in message and offers Try again", async () => {
  let gatewayDown = true;
  server.use(
    http.get("*/api/articles/:articleId", () => {
      if (!gatewayDown) return HttpResponse.json(webhooks);
      return new HttpResponse("<html>502 Bad Gateway</html>", {
        status: 502,
        headers: { "Content-Type": "text/html" },
      });
    }),
  );
  const turn = await renderAnswered(cited(signing));

  openSection(turn, "Citations", signing);

  const panel = screen.getByRole("dialog", { name: webhooks.title });
  expect(await within(panel).findByRole("alert")).toHaveTextContent(
    "Check that the backend is running",
  );
  gatewayDown = false;
  fireEvent.click(within(panel).getByRole("button", { name: "Try again" }));
  expect(
    await within(panel).findByRole("region", { name: "Webhooks › Signing" }),
  ).toBeInTheDocument();
});
