// PROTOTYPE — throwaway. Fake SSE backend for the "Chat UI with citations" prototype (issue #14).
// Emits the event sequence decided in "Conversation model" (#8) and the payloads decided in
// "Citation & grounding contract" (#7), with hard-coded Nimbus data. No network.

export type PlatformVersion = "v2" | "v3";

export type Passage = {
  /** The number the model saw in the prompt (retrieval order). */
  n: number;
  articleId: string;
  articleTitle: string;
  sectionPath: string[];
  text: string;
  appliesTo: PlatformVersion[];
  status: "current" | "deprecated";
  score: number;
  /** Stand-in for the click-through endpoint: the whole Section the Passage came from. */
  fullSection: string;
};

/** A Citation is a cited Passage, renumbered server-side in order of first appearance. */
export type Citation = Passage & { citationNumber: number };

export type FinalPayload =
  | { kind: "answer"; text: string; citations: Citation[]; retrieved: Passage[] }
  | { kind: "uncited"; text: string; retrieved: Passage[] }
  | {
      kind: "refusal";
      reason: "no_relevant_passages" | "not_in_context";
      message: string;
      retrieved: Passage[];
    };

export type ChatError = {
  code: "llm_not_configured" | "llm_unavailable" | "rewrite_failed";
  message: string;
};

export type ChatEvent =
  | { type: "rewritten"; standaloneQuestion: string }
  | { type: "passages"; passages: Passage[] }
  | { type: "token"; text: string }
  | { type: "done"; payload: FinalPayload }
  | { type: "error"; error: ChatError };

export type ProviderMode = "ok" | "missing_key" | "down_mid_stream" | "slow_first_token";

export type HistoryTurn = { question: string; answer: string };

const REFUSAL_MESSAGE =
  "The Knowledge Base doesn't cover this. Try rephrasing, or check with the owning team.";

// --- Passages -----------------------------------------------------------------

const P = {
  webhookSigV3: {
    articleId: "nimbus-api-webhooks",
    articleTitle: "API Rate Limits and Webhooks",
    sectionPath: ["Webhooks", "Verifying signatures"],
    text: "Every webhook request is signed with HMAC-SHA256 using the endpoint's signing secret. The hex digest is sent in the `X-Nimbus-Signature-256` header. Compute the HMAC of the raw request body and compare it using a constant-time comparison before parsing the payload.",
    appliesTo: ["v3"],
    status: "current",
    fullSection:
      "Every webhook request is signed with HMAC-SHA256 using the endpoint's signing secret. The hex digest is sent in the `X-Nimbus-Signature-256` header. Compute the HMAC of the raw request body and compare it using a constant-time comparison before parsing the payload.\n\nThe signing secret is shown once when the endpoint is created. Rotate it from Settings › Webhooks › Endpoint › Rotate secret; for 24 hours both the old and the new secret are accepted.\n\n```python\nexpected = hmac.new(secret, body, hashlib.sha256).hexdigest()\nif not hmac.compare_digest(expected, request.headers['X-Nimbus-Signature-256']):\n    abort(401)\n```",
  },
  webhookSigV2: {
    articleId: "nimbus-v2-legacy",
    articleTitle: "Nimbus v2 Legacy Reference",
    sectionPath: ["Webhooks (v2)"],
    text: "Webhook payloads are signed with HMAC-SHA1. The signature is sent in the `X-Nimbus-Signature` header as a hex digest of the raw request body.",
    appliesTo: ["v2"],
    status: "deprecated",
    fullSection:
      "Webhook payloads are signed with HMAC-SHA1. The signature is sent in the `X-Nimbus-Signature` header as a hex digest of the raw request body.\n\nFailed deliveries are retried 5 times at 10-minute intervals.",
  },
  webhookRetries: {
    articleId: "nimbus-api-webhooks",
    articleTitle: "API Rate Limits and Webhooks",
    sectionPath: ["Webhooks", "Retries and auto-disable"],
    text: "Failed deliveries are retried 8 times with exponential backoff over 24 hours. An endpoint that keeps failing for 3 days is disabled automatically and the workspace owners are emailed.",
    appliesTo: ["v3"],
    status: "current",
    fullSection:
      "A delivery fails when the endpoint does not answer with a 2xx status within 10 seconds.\n\nFailed deliveries are retried 8 times with exponential backoff over 24 hours. An endpoint that keeps failing for 3 days is disabled automatically and the workspace owners are emailed.\n\nRe-enable a disabled endpoint from Settings › Webhooks. Missed events are not replayed.",
  },
  v2EndOfSupport: {
    articleId: "nimbus-v2-legacy",
    articleTitle: "Nimbus v2 Legacy Reference",
    sectionPath: ["End of support"],
    text: "Nimbus v2 reaches end of support on 2027-03-31. After that date v2 workspaces receive no security fixes. See Upgrading to v3.",
    appliesTo: ["v2"],
    status: "deprecated",
    fullSection:
      "Nimbus v2 reaches end of support on 2027-03-31. After that date v2 workspaces receive no security fixes. See Upgrading to v3.\n\nv2 workspaces keep working read-only for 90 days after end of support.",
  },
  rateLimitsV3: {
    articleId: "nimbus-api-webhooks",
    articleTitle: "API Rate Limits and Webhooks",
    sectionPath: ["Rate limits"],
    text: "| Plan Tier | Requests per minute |\n|---|---|\n| Business | 600 |\n| Enterprise | 3,000 |\n\nShort bursts of up to 2× the limit are allowed for 10 seconds. Requests over the limit get `429 Too Many Requests` with a `Retry-After` header.",
    appliesTo: ["v3"],
    status: "current",
    fullSection:
      "API access is available on the Business and Enterprise tiers. Limits apply per workspace, across all API tokens.\n\n| Plan Tier | Requests per minute |\n|---|---|\n| Business | 600 |\n| Enterprise | 3,000 |\n\nShort bursts of up to 2× the limit are allowed for 10 seconds. Requests over the limit get `429 Too Many Requests` with a `Retry-After` header.",
  },
  rateLimitsV2: {
    articleId: "nimbus-v2-legacy",
    articleTitle: "Nimbus v2 Legacy Reference",
    sectionPath: ["API limits (v2)"],
    text: "The API allows 300 requests per minute per workspace on every Plan Tier. There is no burst allowance.",
    appliesTo: ["v2"],
    status: "deprecated",
    fullSection:
      "The API allows 300 requests per minute per workspace on every Plan Tier. There is no burst allowance.\n\nUse the `X-RateLimit-Remaining` header to pace requests.",
  },
  tierMatrix: {
    articleId: "nimbus-plan-tiers",
    articleTitle: "Plan Tiers and Entitlements",
    sectionPath: ["Feature matrix"],
    text: "| Feature | Starter | Business | Enterprise |\n|---|---|---|---|\n| SAML SSO | — | ✓ | ✓ |\n| SCIM provisioning | — | — | ✓ |\n| Audit-log retention | 30 days | 90 days | 365 days |",
    appliesTo: ["v3"],
    status: "current",
    fullSection:
      "| Feature | Starter | Business | Enterprise |\n|---|---|---|---|\n| SAML SSO | — | ✓ | ✓ |\n| SCIM provisioning | — | — | ✓ |\n| API access | — | ✓ | ✓ |\n| Audit-log retention | 30 days | 90 days | 365 days |\n| Data regions | EU, US | EU, US | EU, US, APAC |",
  },
  scimPrereq: {
    articleId: "nimbus-scim-provisioning",
    articleTitle: "Automated User Provisioning with SCIM 2.0",
    sectionPath: ["Prerequisites"],
    text: "SCIM provisioning requires the Enterprise tier. SAML SSO must be configured and enforced before SCIM can be enabled.",
    appliesTo: ["v3"],
    status: "current",
    fullSection:
      "SCIM provisioning requires the Enterprise tier. SAML SSO must be configured and enforced before SCIM can be enabled.\n\nYou need a workspace owner account and admin access to the identity provider.",
  },
  ssoOverview: {
    articleId: "nimbus-sso-saml",
    articleTitle: "Configuring SSO with SAML 2.0",
    sectionPath: ["Overview"],
    text: "Nimbus supports SAML 2.0 single sign-on with Okta and Microsoft Entra ID. Other identity providers are not documented.",
    appliesTo: ["v3"],
    status: "current",
    fullSection:
      "Nimbus supports SAML 2.0 single sign-on with Okta and Microsoft Entra ID. Other identity providers are not documented.\n\nSSO is available on the Business and Enterprise tiers.",
  },
  ssoAttributes: {
    articleId: "nimbus-sso-saml",
    articleTitle: "Configuring SSO with SAML 2.0",
    sectionPath: ["Attribute mapping"],
    text: "| SAML attribute | Required | Used for |\n|---|---|---|\n| `email` | yes | Login and user matching |\n| `firstName` | yes | Display name |\n| `lastName` | yes | Display name |\n| `groups` | no | Role mapping |",
    appliesTo: ["v3"],
    status: "current",
    fullSection:
      "Map these attributes in the identity provider's SAML app.\n\n| SAML attribute | Required | Used for |\n|---|---|---|\n| `email` | yes | Login and user matching |\n| `firstName` | yes | Display name |\n| `lastName` | yes | Display name |\n| `groups` | no | Role mapping |",
  },
  ssoTroubleshooting: {
    articleId: "nimbus-sso-saml",
    articleTitle: "Configuring SSO with SAML 2.0",
    sectionPath: ["Troubleshooting", "Error codes"],
    text: "| Code | Cause | Fix |\n|---|---|---|\n| AUTH-401 | Clock skew over 5 minutes between IdP and Nimbus | Sync the IdP clock with NTP |\n| AUTH-403 | User not assigned to the Nimbus app | Assign the user in the IdP |",
    appliesTo: ["v3"],
    status: "current",
    fullSection:
      "| Code | Cause | Fix |\n|---|---|---|\n| AUTH-401 | Clock skew over 5 minutes between IdP and Nimbus | Sync the IdP clock with NTP |\n| AUTH-403 | User not assigned to the Nimbus app | Assign the user in the IdP |\n| AUTH-409 | Another user already has this email | Merge or rename the duplicate user |",
  },
  ssoJit: {
    articleId: "nimbus-sso-saml",
    articleTitle: "Configuring SSO with SAML 2.0",
    sectionPath: ["Just-in-time provisioning"],
    text: "With JIT provisioning on, Nimbus creates a user the first time they sign in through SSO. JIT never deactivates or removes users.",
    appliesTo: ["v3"],
    status: "current",
    fullSection:
      "With JIT provisioning on, Nimbus creates a user the first time they sign in through SSO. JIT never deactivates or removes users.\n\nUse SCIM if leavers must be removed automatically.",
  },
  scimOverview: {
    articleId: "nimbus-scim-provisioning",
    articleTitle: "Automated User Provisioning with SCIM 2.0",
    sectionPath: ["Overview"],
    text: "SCIM keeps Nimbus users and groups in sync with the identity provider. Nimbus pulls changes every 40 minutes.",
    appliesTo: ["v3"],
    status: "current",
    fullSection:
      "SCIM keeps Nimbus users and groups in sync with the identity provider. Nimbus pulls changes every 40 minutes.\n\nUsers created by SCIM can't be edited in Nimbus.",
  },
  scimDeprovision: {
    articleId: "nimbus-scim-provisioning",
    articleTitle: "Automated User Provisioning with SCIM 2.0",
    sectionPath: ["Deprovisioning"],
    text: "When a user is unassigned in the identity provider, Nimbus suspends them at the next sync. Their data is kept for 30 days and then deleted.",
    appliesTo: ["v3"],
    status: "current",
    fullSection:
      "When a user is unassigned in the identity provider, Nimbus suspends them at the next sync. Their data is kept for 30 days and then deleted.\n\nA suspended user reassigned within 30 days is restored with their data.",
  },
} satisfies Record<string, Omit<Passage, "n" | "score">>;

type PassageSeed = Omit<Passage, "n" | "score">;

function numbered(seeds: [PassageSeed, number][]): Passage[] {
  return seeds.map(([seed, score], i) => ({ ...seed, n: i + 1, score }));
}

// --- Scenarios ------------------------------------------------------------------

type Scenario = {
  standalone?: (question: string) => string;
  passages: Passage[];
  /** Raw model output, using prompt numbers. Undefined → refused by the retrieval gate. */
  modelText?: string;
  sentinel?: boolean;
};

const SCENARIOS: { match: (q: string, hasHistory: boolean) => boolean; build: () => Scenario }[] = [
  {
    match: (q, h) => h && /\bv2\b/i.test(q) && q.length < 40,
    build: () => ({
      standalone: () => "What is the API rate limit for a Business-tier client on Nimbus v2?",
      passages: numbered([
        [P.rateLimitsV3, 0.71],
        [P.rateLimitsV2, 0.84],
        [P.v2EndOfSupport, 0.62],
      ]),
      modelText:
        "On v2 the API allows a flat 300 requests per minute per workspace on every Plan Tier, Business included, with no burst allowance [2].\n\nv2 is deprecated and reaches end of support on 2027-03-31 [3], so the client gets 600 requests per minute after upgrading to v3 [1].",
    }),
  },
  {
    match: (q) => /signature|signed|webhook header/i.test(q),
    build: () => ({
      passages: numbered([
        [P.webhookSigV3, 0.86],
        [P.webhookSigV2, 0.79],
        [P.webhookRetries, 0.55],
        [P.v2EndOfSupport, 0.51],
      ]),
      modelText:
        "Webhook requests are signed with HMAC-SHA256, and the hex digest is sent in the `X-Nimbus-Signature-256` header [1]. The client should compute the HMAC of the raw request body and compare it in constant time before parsing the payload [1].\n\nOn v2 (deprecated, end of support 2027-03-31) it is different: payloads are signed with HMAC-SHA1 in the `X-Nimbus-Signature` header [2][4].",
    }),
  },
  {
    match: (q) => /rate limit|requests per minute/i.test(q),
    build: () => ({
      passages: numbered([
        [P.rateLimitsV3, 0.88],
        [P.rateLimitsV2, 0.74],
        [P.tierMatrix, 0.48],
      ]),
      modelText:
        "A Business-tier client can make 600 requests per minute [1]. Short bursts of up to 2× that are allowed for 10 seconds; beyond that the API answers `429 Too Many Requests` with a `Retry-After` header [1].\n\nOn v2 (deprecated, end of support 2027-03-31) the limit is a flat 300 requests per minute on every Plan Tier [2].",
    }),
  },
  {
    match: (q) => /scim/i.test(q) && /business/i.test(q),
    build: () => ({
      passages: numbered([
        [P.scimPrereq, 0.83],
        [P.tierMatrix, 0.77],
        [P.ssoOverview, 0.61],
        [P.scimOverview, 0.58],
      ]),
      modelText:
        "No. SCIM provisioning is only available on the Enterprise tier [2][1], so a Business-tier client would have to upgrade first.\n\nSAML SSO also has to be configured and enforced before SCIM can be enabled [1]. Okta is one of the two documented identity providers [3].",
    }),
  },
  {
    match: (q) => /jit|just.in.time/i.test(q),
    // The model "forgot" its markers → Uncited Answer.
    build: () => ({
      passages: numbered([
        [P.ssoJit, 0.85],
        [P.scimOverview, 0.8],
        [P.scimDeprovision, 0.66],
      ]),
      modelText:
        "JIT provisioning creates a user the first time they sign in through SSO, but it never deactivates or removes anyone. SCIM keeps users in sync with the identity provider every 40 minutes, including leavers: an unassigned user is suspended at the next sync and their data is deleted after 30 days.",
    }),
  },
  {
    match: (q) => /google/i.test(q),
    build: () => ({
      passages: numbered([
        [P.ssoOverview, 0.72],
        [P.ssoAttributes, 0.69],
        [P.ssoTroubleshooting, 0.41],
      ]),
      modelText:
        "The Knowledge Base doesn't cover setting up SSO with Google Workspace: the SAML guide only documents Okta and Microsoft Entra ID [1].\n\nWhichever identity provider is used, Nimbus expects these SAML attributes [2]:\n- `email` (required): login and user matching\n- `firstName` and `lastName` (required): display name\n- `groups` (optional): role mapping",
    }),
  },
  {
    match: (q) => /auth-?401/i.test(q),
    build: () => ({
      passages: numbered([
        [P.ssoTroubleshooting, 0.9],
        [P.ssoOverview, 0.52],
      ]),
      modelText:
        "AUTH-401 means the SAML sign-in was rejected because the clocks on the identity provider and Nimbus differ by more than 5 minutes [1]. Fix it by syncing the IdP server's clock with NTP, then have the user sign in again [1].",
    }),
  },
  {
    match: (q) => /ldap/i.test(q),
    // Passages clear the gate but don't answer → model emits the sentinel.
    build: () => ({
      passages: numbered([
        [P.scimOverview, 0.58],
        [P.ssoOverview, 0.55],
      ]),
      sentinel: true,
    }),
  },
];

/** Anything unmatched (pricing, small talk, …) is refused by the retrieval gate. */
function gateRefusal(): Scenario {
  return {
    passages: numbered([
      [P.tierMatrix, 0.31],
      [P.ssoOverview, 0.22],
    ]),
  };
}

export const SUGGESTED_QUESTIONS = [
  "Which header carries the webhook signature and what algorithm is used?",
  "Can a Business-tier client set up SCIM provisioning with Okta?",
  "What is the API rate limit for a Business client?",
  "How do I set up SSO with Google Workspace, and which attributes are required?",
  "What's the difference between JIT provisioning and SCIM?",
  "How much does the Enterprise tier cost per seat?",
  "Does Nimbus support LDAP directory sync?",
  "What does error AUTH-401 mean?",
];

// --- Answer assembly (the server-side renumbering from #7, faked here) ----------

function assemble(scenario: Scenario): FinalPayload {
  const retrieved = scenario.passages;
  if (scenario.modelText === undefined) {
    return {
      kind: "refusal",
      reason: scenario.sentinel ? "not_in_context" : "no_relevant_passages",
      message: REFUSAL_MESSAGE,
      retrieved,
    };
  }
  const order: number[] = [];
  for (const m of scenario.modelText.matchAll(/\[(\d+)\]/g)) {
    const n = Number(m[1]);
    if (retrieved.some((p) => p.n === n) && !order.includes(n)) order.push(n);
  }
  if (order.length === 0) return { kind: "uncited", text: scenario.modelText, retrieved };
  const text = scenario.modelText.replaceAll(/\[(\d+)\]/g, (_, d: string) => {
    const i = order.indexOf(Number(d));
    return i === -1 ? "" : `[${i + 1}]`;
  });
  const citations = order.map((n, i) => {
    const p = retrieved.find((x) => x.n === n);
    if (!p) throw new Error("unreachable");
    return { ...p, citationNumber: i + 1 };
  });
  return { kind: "answer", text, citations, retrieved };
}

// --- The fake stream -------------------------------------------------------------

function sleep(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const t = setTimeout(resolve, ms);
    signal.addEventListener("abort", () => {
      clearTimeout(t);
      reject(new DOMException("Aborted", "AbortError"));
    });
  });
}

function tokenize(text: string): string[] {
  return text.match(/\S+\s*|\s+/g) ?? [];
}

export async function* fakeChatStream(
  request: { question: string; history: HistoryTurn[] },
  mode: ProviderMode,
  signal: AbortSignal,
): AsyncGenerator<ChatEvent> {
  const hasHistory = request.history.length > 0;
  const scenario =
    SCENARIOS.find((s) => s.match(request.question, hasHistory))?.build() ?? gateRefusal();

  if (mode === "missing_key") {
    await sleep(150, signal);
    yield {
      type: "error",
      error: {
        code: "llm_not_configured",
        message:
          "No chat model is configured. Set OPENAI_API_KEY in .env, or start the stack with the Ollama profile.",
      },
    };
    return;
  }

  if (hasHistory) {
    await sleep(1200, signal);
    yield {
      type: "rewritten",
      standaloneQuestion: scenario.standalone?.(request.question) ?? request.question,
    };
  }

  await sleep(500, signal);
  yield { type: "passages", passages: scenario.passages };

  const final = assemble(scenario);
  if (final.kind === "refusal" && final.reason === "no_relevant_passages") {
    await sleep(200, signal);
    yield { type: "done", payload: final };
    return;
  }

  await sleep(mode === "slow_first_token" ? 7000 : 900, signal);

  if (final.kind === "refusal") {
    // Sentinel: the server holds back tokens until it knows it isn't the sentinel.
    yield { type: "done", payload: final };
    return;
  }

  const tokens = tokenize(scenario.modelText ?? "");
  for (const [i, tok] of tokens.entries()) {
    if (mode === "down_mid_stream" && i === Math.floor(tokens.length / 3)) {
      yield {
        type: "error",
        error: {
          code: "llm_unavailable",
          message: "The chat model stopped responding (Ollama at http://ollama:11434).",
        },
      };
      return;
    }
    await sleep(45, signal);
    yield { type: "token", text: tok };
  }
  yield { type: "done", payload: final };
}
