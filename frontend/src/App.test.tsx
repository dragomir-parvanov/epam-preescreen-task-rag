import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { expect, test } from "vite-plus/test";
import type { components } from "./api/schema";
import App from "./App";
import { server } from "./test/server";

function renderApp() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>,
  );
}

test("shows the status the backend reports on /health", async () => {
  server.use(
    http.get("*/api/health", () =>
      HttpResponse.json<components["schemas"]["HealthResponse"]>({ status: "ok" }),
    ),
  );

  renderApp();

  expect(await screen.findByText("ok")).toBeInTheDocument();
});
