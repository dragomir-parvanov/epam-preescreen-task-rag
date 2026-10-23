import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import type { components } from "../api/schema";

type ReadinessResponse = components["schemas"]["ReadinessResponse"];

/** `GET /ready` with every check passing: the page polls it on load. */
export const READY: ReadinessResponse = {
  status: "ready",
  checks: { database: { ok: true }, index: { ok: true }, llm: { ok: true } },
};

// Shared mock of the backend's HTTP boundary; tests add handlers with `server.use`. A ready
// stack is the default, so only the readiness tests need to think about `/ready`.
export const server = setupServer(http.get("*/api/ready", () => HttpResponse.json(READY)));
