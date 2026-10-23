<!-- session: 2fc52221-9452-4773-812a-551e8eae41af -->

## user · 2026-10-23 12:07:51 · context 4.2% (41.7k / 1000k)

continue /wayfinder effort for https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/13

## assistant · 2026-10-23 12:08:20 · context 5.4% (53.6k / 1000k)

Claimed **HTTP API contract**; now loading its inputs (the citation and conversation decisions, ADRs, glossary, current code) before the first grilling round.

## assistant · 2026-10-23 12:10:14 · context 6.9% (69.3k / 1000k)

I've read the inputs: the citation and conversation decisions, both ADRs, the glossary, and the walking-skeleton code. I also checked one fact. FastAPI 0.161 in this repo has native SSE (`fastapi.sse.EventSourceResponse`). It sends a `: ping` keepalive every 15 s and puts a discriminated-union event schema into OpenAPI, so the stream's event types can be generated into TS just like the JSON types. Here's round 1.

---

❓ **Q1 - Path prefix & versioning**: Right now nginx and Vite strip `/api`, and the backend serves `/health` at its root. Options: (a) no version in paths, e.g. `/api/chat`; (b) the backend owns a `/v1` prefix, so the browser sees `/api/v1/chat` and the strip stays as is; (c) the backend owns the full `/api/v1` and the proxy stops stripping.

➡️ (b). Business routes go under `/v1`, and the infra probes (`/health`, `/ready`) stay unversioned at the root. It costs almost nothing and gives a ready answer to "how would you evolve this?" The README notes that the only client ships in the same commit with generated types, so `/v2` would come in only when there's a breaking change for an external consumer.

---

❓ **Q2 - Chat entry points**: ADR 0002 has an SSE stream plus a non-streaming JSON twin. Options: (a) one path that picks a format from `Accept` (content negotiation); (b) two operations.

➡️ (b). `POST /v1/chat` returns the `done` payload as JSON, and `POST /v1/chat/stream` returns `text/event-stream`. Content negotiation on a single operation turns into a muddy union in OpenAPI and the generated TS. With two operations each one is typed exactly, and both use one shared service function.

---

❓ **Q3 - Request schema & limits**: The decided shape is `{question, history: [{question, answer}]}`. Limits:

➡️ `question`: 1–2,000 characters, and it must not be blank after stripping whitespace. `history`: at most 20 items, each `question` ≤ 2,000 and each `answer` ≤ 20,000 characters. The server still uses only the last 3 Turns and truncates each answer to ~500 characters. The generous caps are there to block abuse, not to shape the prompt, so a long Conversation never gets a 422. Breaking a limit returns a 422 in the standard error envelope (Q8). nginx sets `client_max_body_size 256k` as a coarse backstop. No rate limiting: one local user, and it goes in the README as future work.

---

❓ **Q4 - The result (`done` / JSON) shape**: A discriminated union on `type` with three members, because the UI renders each one differently:

```
ChatResult =
  | { type: "answer",         text, citations: Citation[], retrieved_passages: Passage[], standalone_question: str | null }
  | { type: "uncited_answer", text, retrieved_passages: Passage[], standalone_question }
  | { type: "refusal",        message, reason: "no_relevant_passages" | "not_in_context", retrieved_passages, standalone_question }
```

The alternative is a single `answer` type with an `uncited: bool` or an empty `citations` list.

➡️ The three-member union as drafted. "Uncited Answer" is a glossary term, so it gets its own type rather than a boolean the UI could forget to check. `retrieved_passages` is on every member, including a Refusal, for evals and threshold tuning (it can be empty for a gate Refusal). No `usage`/latency metadata in the payload; that goes in logs.

---

❓ **Q5 - Passage & Citation schemas**:

```
Passage  { id, article: {id, title}, section: {id, path: str[]}, text, applies_to: ("v2"|"v3")[], status: "current"|"deprecated", score: float }
Citation { n: int, passage: Passage }
```

Here `section.path` is the heading path as a list (the UI joins it with `›`), and `section.id` is a stable slug that the click-through (Q9) uses as an anchor. A Citation embeds its Passage instead of pointing at an id in `retrieved_passages`.

➡️ Yes, as drafted. Embedding the Passage duplicates about 5 Passages of text at most, and in return a Citation is self-contained and the UI does no joins. `score` stays in the API but isn't rendered (per #7).

---

❓ **Q6 - Marker numbering during the stream**: The model writes markers using its *prompt* numbers, which match the `passages` event (`[3]`). `done` renumbers them `[1]..[k]`. Options: (a) stream the raw tokens; the UI resolves `[3]` against the `passages` event for now, and `done` replaces the text, so the numbers can visibly jump from [3] to [1] at the end; (b) the server renumbers incrementally as it streams, holding back a partial `[1`, so the streamed text already matches `done`.

➡️ (a) for now. The stream stays dumb, there's exactly one authoritative assembly in `done` (ADR 0001/0002), and the provisional markers still resolve correctly. (b) is listed as a polish item that *Chat UI with citations* can promote if the jump looks bad in the prototype. It's a contained change, because the renumbering logic from the answer-assembly build ticket can be made incremental.

---

❓ **Q7 - SSE framing**: Each frame is `event: <type>` + `data: <JSON>`, using FastAPI's native `EventSourceResponse` with a discriminated `ChatStreamEvent` union, so the events are in OpenAPI and come out as TS types. Payloads: `rewritten {standalone_question}`, `passages {passages: Passage[]}` numbered by prompt order, `token {text}`, `done {result: ChatResult}`, `error {error: ErrorBody}`. The JSON `data` repeats `type`, so the client can parse the data alone. No `id`/`retry`, because a dropped stream isn't resumed and the user just asks again. The built-in 15 s `: ping` keepalive covers slow CPU first tokens.

➡️ Yes, as drafted.

---

❓ **Q8 - Error envelope & status codes**: One envelope everywhere: `{error: {code, message, details?}}`. FastAPI's default `{detail: [...]}` for 422 gets overridden so that clients only ever parse one shape. The same `ErrorBody` is the payload of the SSE `error` event. Codes:

| code | HTTP | when |
|---|---|---|
| `validation_error` | 422 | bad request body (`details` = field errors) |
| `not_found` | 404 | unknown Article id |
| `llm_not_configured` | 503 | selected provider needs a key that isn't set |
| `llm_auth_failed` | 502 | provider rejected the key |
| `llm_unavailable` | 503 | provider unreachable / 5xx / model not pulled |
| `llm_timeout` | 504 | provider exceeded timeout |
| `index_not_ready` | 503 | ingestion hasn't completed |
| `internal_error` | 500 | anything else (message generic, details logged) |

Key rule: on `/chat/stream`, anything detectable **before the first byte** (validation, not configured, index not ready) returns a real HTTP status with a JSON envelope. Only failures *after* the stream has started use the SSE `error` event.

➡️ Yes, as drafted. Do you want `request_id` in the envelope? I'd say yes, but that depends on *Operational readiness* deciding to have request ids, so I'd leave it as an optional field that ticket fills in.

---

❓ **Q9 - Knowledge Base browsing & click-through**: Options: (a) `GET /v1/articles` (list: id, title, applies_to, status, and each Section's {id, path}) plus `GET /v1/articles/{article_id}` (the full Article as ordered `sections: [{id, path, level, markdown}]`). The UI opens the Article, scrolls to `section.id` and highlights it. (b) A per-Section endpoint `GET /v1/articles/{id}/sections/{section_id}`. (c) No list endpoint.

➡️ (a). Opening the whole Article gives the CSM the context around the cited Section, and the Articles are small. The list endpoint is cheap and lets a reviewer see what's in the Knowledge Base, which also helps explain Refusals. Sections come back as server-split markdown, so anchors can't drift between the backend's slugs and a frontend markdown slugger.

---

❓ **Q10 - Health vs readiness paths**: Keep `GET /health` (liveness, always 200 while serving), and add `GET /ready` → 200 or 503 with `{status: "ready"|"not_ready", checks: {<name>: {ok, detail?}}}`. *What* the checks are (index built? LLM reachable?) stays with *Operational readiness*. This ticket fixes only the paths and the shape.

➡️ Yes, as drafted.

---

❓ **Q11 - CORS & proxy shape**: Everything is same-origin: nginx in Compose, the Vite proxy in dev. So **no CORS middleware at all**, and a cross-origin browser call is simply blocked by the browser, which is the right default for a no-auth app. The nginx `location /api/v1/chat/stream` gets `proxy_buffering off; proxy_cache off; proxy_http_version 1.1; proxy_read_timeout 300s`, and the backend also sends `X-Accel-Buffering: no`. Backend port 8000 stays published to the host for curl and the eval runner.

➡️ Yes, as drafted.

---

❓ **Q12 - JSON field casing**: snake_case on the wire, and the generated TS types use it as is, versus camelCase aliases on every Pydantic model.

➡️ snake_case end to end. The TS types are generated, so there's no hand-written mapping to keep in sync. Aliases add a layer of config, and with it a class of bugs, for purely cosmetic reasons.

## user · 2026-10-23 12:46:04 · context 7.3% (73.1k / 1000k)

q1:no freaking v1s, just remove v1s, 
q2: why we need 2 paths for the same thing?
q3: reccomended
q4: reccomended
q5: reccomended
q6: reccomended
q7: recomended
q8: reccomended
q9: reccomended
q10: reccomended
q11: reccomended
q12: reccomended

## assistant · 2026-10-23 12:46:22 · context 7.3% (73.1k / 1000k)

Q1: no versioning. Browser paths are `/api/chat` and `/api/articles`, and the backend serves them at its root (`/chat`, `/articles`, `/health`, `/ready`). The proxy keeps stripping `/api`.

Q2 was my mistake to present as settled, so here's the reasoning and a new recommendation.

❓ **Q13 - One chat path or two?**: The JSON twin came from the Conversation-model decision (ADR 0002). It was meant for three uses: curl, the golden-question evaluation, and simpler tests. I split it into two paths only so each one would be typed cleanly. None of those three uses actually needs a second HTTP endpoint:

- **Tests** can call the service function that builds a `ChatResult` directly, in-process. They don't need HTTP at all.
- **The evaluation** can do the same in-process. If it goes over HTTP, it reads the stream until `done`, which is about 10 lines of client code.
- **curl** works with SSE: `curl -N -X POST .../api/chat -d '{...}'` prints the events as they arrive. The `done` line holds the full result.

The options:
- (a) **One streaming endpoint**, `POST /chat` → `text/event-stream`. The JSON twin is dropped, and ADR 0002 gets a note about that change.
- (b) **One path, format chosen by `Accept`.** It keeps a JSON curl path, but the OpenAPI types get muddy.
- (c) Two paths, as I first proposed.

➡️ (a). There's one endpoint and one contract, and the "final answer as one object" need is met by the service function and the `done` event. I'll add a short note to ADR 0002 that the JSON twin was dropped and why.

If you say yes to Q13, the frontier is empty. This is the contract I'd record:

- `POST /chat` is SSE (`rewritten` → `passages` → `token` → `done` / `error`), with a 15 s keepalive. Markers stream raw with their prompt numbers, and `done` is authoritative.
- The request is `{question, history}` with abuse-level caps, plus `client_max_body_size 256k` in nginx.
- `ChatResult` = `answer` | `uncited_answer` | `refusal`. Each Citation embeds its Passage.
- `GET /articles` and `GET /articles/{article_id}` return server-split Sections, and the UI scrolls to a Section by its `section.id`.
- `GET /health` (liveness) and `GET /ready` (readiness; which checks it runs is up to *Operational readiness*).
- One error envelope `{error: {code, message, details?}}` with the status table above. Errors found before the first byte get a real HTTP status.
- Same-origin, so no CORS. The nginx chat location turns buffering off, and the backend sends `X-Accel-Buffering: no`. Fields are snake_case.

An ADR for this one? Most of it is reversible. I'd write the ADR only for "single SSE endpoint, no JSON twin" (as an amendment to ADR 0002) and record the rest in the ticket's resolution comment. OK?

## user · 2026-10-23 12:47:12 · context 7.5% (74.6k / 1000k)

a

## assistant · 2026-10-23 12:47:39 · context 7.8% (78.5k / 1000k)

Recording the resolution: amending ADR 0002, closing the ticket, opening the build tickets, and updating the map.

## assistant · 2026-10-23 12:48:52 · context 8.6% (85.7k / 1000k)

Now the map: one Decisions line, plus sharpening the degraded-mode fog with what the API now fixes.

## assistant · 2026-10-23 12:49:14 · context 8.7% (87.1k / 1000k)

**HTTP API contract** is decided and closed. The full contract is in [its resolution comment](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/13#issuecomment-6362148666), and the map now has a Decisions-so-far line for it.

**What was decided:**
- **No versioning.** The backend serves at its root and the proxy strips `/api`, so there's no `/v1` anywhere.
- **One chat endpoint:** `POST /chat`, streamed only, using FastAPI's built-in streaming support. The stream sends typed events: `rewritten` → `passages` → `token` → `done` / `error`. Tokens carry the model's raw `[n]` numbers, and `done` is the final word.
- **No separate JSON endpoint.** Tests and the evaluation call the answering code directly in Python, and curl can read the stream with `-N`.
- **Result types:** each answer is one of `answer`, `uncited_answer` or `refusal`. Each Citation includes its Passage.
- **Click-through:** `GET /articles` and `GET /articles/{id}` return Articles split into Sections. Each Section has a stable id that the UI scrolls to.
- **Health checks:** `/health` and `/ready`. Which checks `/ready` runs is left to **Operational readiness**.
- **Errors:** one error shape, `{error: {code, message, details?}}`, with a table of codes and HTTP statuses. Any error caught before the stream starts gets a real HTTP status instead of a 200 stream.
- **Proxy:** same origin, so no CORS. The nginx chat route has buffering turned off. Fields are snake_case.

**New build tickets:**
- [Build the chat API contract over a stub pipeline](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/23) can be picked up now.
- [Build Knowledge Base browsing endpoints](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/24) is blocked by **Write the Knowledge Base articles and golden questions**.

**Other changes:**
- **Local file, not committed:** I added a line to `docs/adr/0002-history-feeds-only-the-follow-up-rewrite.md` recording that the JSON endpoint was dropped. The whole `docs/adr/` folder is still untracked, so commit it whenever you're ready.
- **Map fog:** the "Failure & degraded-mode UX" item now says the API side is settled by the error codes, and only the UI copy and recovery per code remain open.
- **Glossary:** no new terms, so `GLOSSARY.md` is unchanged.

**Choose the RAG framework** is already assigned to you, probably from another session, so the next free decision is **Choose the LLM & embedding providers and their configuration**.

