import { fetchClient } from "../api/client";
import type { components } from "../api/schema";

type ErrorCode = components["schemas"]["ErrorCode"];
type ReadinessChecks = components["schemas"]["ReadinessChecks"];
type ReadinessResponse = components["schemas"]["ReadinessResponse"];
type LlmCheck = components["schemas"]["LlmCheck"];
type LlmProblem = components["schemas"]["LlmProblem"];

/**
 * What the last `GET /api/ready` said: every check, whether it came with 200 or 503, or that
 * nothing usable answered (a fetch error, a proxy's 502/504, a body without the readiness shape).
 */
export type Readiness =
  | { reachable: true; checks: ReadinessChecks }
  | { reachable: false; failure: string };

const STATUS_TEXT: Record<number, string> = {
  502: "Bad Gateway",
  503: "Service Unavailable",
  504: "Gateway Timeout",
};

export async function fetchReadiness(signal: AbortSignal): Promise<Readiness> {
  try {
    // openapi-fetch hands back the readiness body as `data` on 200 and as `error` on 503, and
    // the text of anything else (a proxy's error page) as `error`.
    const { data, error, response } = await fetchClient.GET("/ready", { signal });
    const body: unknown = data ?? error;
    if (isReadiness(body)) return { reachable: true, checks: body.checks };
    const { status } = response;
    return { reachable: false, failure: `${status} ${STATUS_TEXT[status] ?? response.statusText}` };
  } catch (error) {
    if (signal.aborted) throw error;
    // A 200 whose body isn't JSON throws a SyntaxError; nothing answering throws a TypeError.
    return {
      reachable: false,
      failure: error instanceof SyntaxError ? "a reply that isn't JSON" : "network error",
    };
  }
}

function isReadiness(body: unknown): body is ReadinessResponse {
  if (typeof body !== "object" || body === null || !("checks" in body)) return false;
  const { checks } = body;
  if (typeof checks !== "object" || checks === null) return false;
  return (
    "database" in checks &&
    isCheck(checks.database) &&
    "index" in checks &&
    isCheck(checks.index) &&
    "llm" in checks &&
    isCheck(checks.llm)
  );
}

function isCheck(check: unknown): boolean {
  return (
    typeof check === "object" && check !== null && "ok" in check && typeof check.ok === "boolean"
  );
}

/** Every check passes: polling stops. */
export function isAllOk(readiness: Readiness): boolean {
  if (!readiness.reachable) return false;
  const { database, index, llm } = readiness.checks;
  return database.ok && index.ok && llm.ok;
}

/** `database` or `index` is failing, so a question would fail too: Send waits. `llm` never gates. */
export function blocksSending(readiness: Readiness | null): boolean {
  if (readiness === null || !readiness.reachable) return false;
  return !readiness.checks.database.ok || !readiness.checks.index.ok;
}

/** A Turn failed for a reason `/ready` reports on, so it's worth checking again at once. */
export function isOperational(code: ErrorCode): boolean {
  return code === "index_not_ready" || code === "retrieval_unavailable" || code.startsWith("llm_");
}

/** An `llm` failure shown with the `unavailable` copy: that code, a missing one, or an unknown one. */
function looksUnavailable(llm: LlmCheck): boolean {
  return !llm.ok && !(llm.detail === "auth_failed" || llm.detail === "model_missing");
}

/**
 * Debounce `llm` reporting `unavailable`, as it does for about a second after the backend starts,
 * until its first probe answers: it is shown only once the next check says it again.
 */
export function debounceLlm(next: Readiness, previous: Readiness | null): Readiness {
  if (!next.reachable || !looksUnavailable(next.checks.llm)) return next;
  if (previous?.reachable && looksUnavailable(previous.checks.llm)) return next;
  return { reachable: true, checks: { ...next.checks, llm: { ok: true } } };
}

// --- What the banner says -------------------------------------------------------------------

/** Blue while the index builds, amber for the `llm`, red when the CSM can't get answers. */
export type Tone = "info" | "warning" | "error";

/** One failing check, for whoever runs the assistant: `subject` is shown as code. */
export type Problem = { subject: string; text: string; command?: string };

export type BannerView = {
  tone: Tone;
  headline: string;
  subline: string;
  /** Every failing check, not just the one the headline is about. */
  problems: Problem[];
};

const NOT_SET_UP = {
  headline: "The assistant isn't set up correctly",
  subline: "Answers will fail until whoever runs the assistant fixes its configuration.",
};

const LLM_COPY: Record<LlmProblem, { headline: string; subline: string; text: string }> = {
  auth_failed: {
    ...NOT_SET_UP,
    text: "The API key was rejected. Set a valid ANTHROPIC_API_KEY in .env and restart the backend.",
  },
  unavailable: {
    headline: "The AI provider isn't responding",
    subline: "Answers may fail. You can still try, and this page checks again automatically.",
    text: "The configured provider couldn't be reached.",
  },
  model_missing: { ...NOT_SET_UP, text: "The model isn't pulled." },
};

function llmCopy(llm: LlmCheck) {
  // A `detail` this build doesn't know (a newer backend's) reads as `unavailable`.
  return (llm.detail && LLM_COPY[llm.detail]) ?? LLM_COPY.unavailable;
}

/** The banner for the most severe state, unreachable > `database` > `index` > `llm`; none when all pass. */
export function bannerFor(readiness: Readiness): BannerView | null {
  if (!readiness.reachable) {
    return {
      tone: "error",
      headline: "Can't reach the assistant right now",
      subline: "It may be restarting. This page reconnects automatically.",
      problems: [{ subject: "GET /api/ready", text: `→ ${readiness.failure}` }],
    };
  }
  const { database, index, llm } = readiness.checks;
  const problems: Problem[] = [];
  if (!database.ok) problems.push({ subject: "database:", text: database.detail ?? "not ok" });
  if (!index.ok) {
    problems.push({
      subject: "index:",
      text: index.detail ?? "first sync since startup hasn't finished",
    });
  }
  if (!llm.ok) {
    const copy = llmCopy(llm);
    const command = llm.detail === "model_missing" ? (llm.command ?? undefined) : undefined;
    problems.push({ subject: "llm:", text: copy.text, command });
  }

  if (!database.ok) {
    return {
      tone: "error",
      headline: "The Knowledge Base is unavailable",
      subline: "Questions can't be sent until it's back. This page checks again automatically.",
      problems,
    };
  }
  if (!index.ok && index.detail) {
    return {
      tone: "error",
      headline: "The Knowledge Base is having trouble loading",
      subline: "It retries automatically. If this persists, contact whoever runs the assistant.",
      problems,
    };
  }
  if (!index.ok) {
    return {
      tone: "info",
      headline: "The Knowledge Base is still loading",
      subline:
        "This usually takes under a minute. You can type your question now and send it once loading finishes.",
      problems,
    };
  }
  if (!llm.ok) {
    const { headline, subline } = llmCopy(llm);
    return { tone: "warning", headline, subline, problems };
  }
  return null;
}
