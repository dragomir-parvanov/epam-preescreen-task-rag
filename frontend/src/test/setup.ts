import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach } from "vite-plus/test";
import { server } from "./server";

// Listen before any test module is imported: the API client captures `fetch` when it is created.
server.listen({ onUnhandledFrame: "error" });

// jsdom doesn't lay pages out, so it has no scrolling.
Element.prototype.scrollIntoView = () => undefined;

afterEach(() => {
  cleanup();
  server.resetHandlers();
});

afterAll(() => {
  server.close();
});
