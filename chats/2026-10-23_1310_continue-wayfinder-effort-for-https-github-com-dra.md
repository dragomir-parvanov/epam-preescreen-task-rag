<!-- session: ad5190f6-8c6d-48fd-b61a-2c0435b1fc06 -->

## user · 2026-10-23 13:10:54 · context 4.2% (42.2k / 1000k)

continue /wayfinder effort for https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/15

## assistant · 2026-10-23 13:11:07 · context 4.9% (49.2k / 1000k)

Unblocked and unclaimed. Claiming it first, then loading the map.

## assistant · 2026-10-23 13:12:45 · context 7.1% (71.1k / 1000k)

I've claimed **Operational readiness: config, health, ingestion lifecycle, logging** and assigned it to you. Both of its blockers are closed: **Choose the LLM & embedding providers** and **Choose the vector store**. I read their resolutions, the HTTP API contract's `/ready` shape and error codes, the Compose smoke-job ticket (which assumes ingestion runs at startup) and the current backend skeleton.

Some things are already settled and I won't reopen them:
- `/health` is a liveness check that always returns 200.
- Config-shape validation and `check-config` run at startup and fail fast.
- The dimension mismatch also fails fast.
- `ANTHROPIC_API_KEY` is read unprefixed.
- Postgres has a named volume and a `pg_isready` healthcheck.

Round 1 covers everything that doesn't depend on another open answer:

---

❓ **Q1 - When ingestion runs**: Options:
- (a) The backend syncs during startup in its lifespan.
- (b) A one-shot `ingest` Compose service that the backend waits on with `service_completed_successfully`, like a migrations job.
- (c) A manual CLI only.

Option (b) is the pattern for many replicas. But the Knowledge Base ships inside the repo, so a deploy and a content change are the same event. Syncing at boot keeps it simple: edit an Article, restart the backend, and the change is picked up.

➡️ Option (a), split in two phases. **Phase 1, blocking:** parse and validate every Article before the server takes traffic (milliseconds). A malformed Article is a content bug, so the backend exits non-zero and names the file. **Phase 2, a background task:** the idempotent sync, which embeds and writes. `/ready` returns 503 / `index_not_ready` until it finishes, even when nothing changed, because an unchanged sync is a quick no-op. The sync takes a Postgres **advisory lock**, so concurrent backends or a CLI run take turns instead of racing. The same function is exposed as `python -m app.ingest`. `knowledge-base/` is bind-mounted read-only.

---

❓ **Q2 - What `/ready` gates on**: Candidate checks:
- `database`: `SELECT 1`
- `index`: the first sync has finished
- `llm`: the key is valid or the Ollama model is present

A readiness check that depends on a shared external provider is a known anti-pattern: a Claude outage would mark every instance unready, even though there is nothing an instance can do about it. On the other hand, an invalid key or a model that was never pulled is exactly what a reviewer will run into.

➡️ Only `database` and `index` gate `status`. `llm` is still reported in `checks` with `{ok, detail}`, but it doesn't gate. It uses a cheap probe that generates no tokens: `GET /v1/models/{model}` for Claude, `POST /api/show` for Ollama. The probe runs at startup and is cached for 60 s. It distinguishes `auth_failed`, `unavailable` and `model_missing` (the last one includes the `ollama pull` hint). Later, the UI's banner can be driven by this check.

---

❓ **Q3 - Timeouts and retries towards the LLM**: The `anthropic` SDK's defaults are a 10-minute timeout and 2 retries.

➡️ Set them explicitly in Settings:
- **Connect timeout:** 5 s.
- **Read timeout** (the longest gap between stream chunks): 60 s for Claude, 120 s for Ollama, since a CPU Ollama takes 8–15 s to the first token.
- **Turn deadline:** `ChatService` wraps the whole Turn in `asyncio.timeout`, 120 s for Claude and 240 s for Ollama. Expiry maps to `llm_timeout`. All of these are below nginx's 300 s.
- **Rewrite step:** the same connect timeout and a 30 s total.
- **Retries:** keep the SDK's 2 retries for Claude (429/5xx/529), but only before the first byte; nothing is ever retried mid-stream. No retries for Ollama, which is local, so a failure is real.

---

❓ **Q4 - Postgres timeouts and failure during a Turn**: Retrieval runs after the `rewritten` event, so the stream has already started when it fails.

➡️ `connect_timeout=5s` and `statement_timeout=10s`, with no app-level retries; Compose ordering covers boot. A database failure during a Turn becomes an `error` event with a **new code, `retrieval_unavailable`** (HTTP 503 if it happens before the first byte). Lumping it into `internal_error` would hide the most likely operational failure. This adds one row to the HTTP API contract's error table.

---

❓ **Q5 - Structured logging**:

➡️ `structlog`, writing JSON to stdout in the image and a readable console format in `dev-backend` (`BACKEND_LOG_FORMAT=json|console`). Uvicorn's access log is replaced by one line per request from our middleware.
- **Per-Turn event:** each Turn logs one `turn_completed` event with outcome (`answer`/`uncited_answer`/`refusal`/`error`), provider, model, `PROMPT_VERSION`, Passage ids and scores, the Citation count, and timings (`rewrite_ms`, `retrieval_ms`, `ttft_ms`, `total_ms`).
- **No content at INFO:** question and Answer text are logged only at `DEBUG`. A CSM's question may contain client data.

---

❓ **Q6 - Request ids**:

➡️ nginx generates `$request_id` and forwards it as `X-Request-ID`. The backend accepts that header or makes a uuid4, binds it in a contextvar on every log line, and echoes it in a response header. It also fills the `request_id` field the HTTP API contract left open in the error envelope (the SSE `error` event included). The UI's error card shows it in small text so it can be quoted in a bug report.

---

❓ **Q7 - Pre-pulling the Ollama model**:

➡️ A one-shot `ollama-pull` service in the `ollama` profile runs `ollama pull qwen3.5:2b` against the `ollama` service, which has an `ollama list` healthcheck. Models go in a named volume, `ollama-models`, so the ~2.7 GB is downloaded once. The backend waits on it with `condition: service_completed_successfully, required: false`, so Claude users are unaffected. A Mac user running a native Ollama pulls the model themselves, and the `llm` check's `model_missing` detail tells them the exact command.

---

❓ **Q8 - Logging the effective config at startup**:

➡️ Yes. After validation succeeds, log one `config_loaded` line with the provider, model, base URLs, timeouts and the database host. `ANTHROPIC_API_KEY` and the database URL are `SecretStr`, so only "set" or "unset" is printed, and the database password is never printed.

---

Round 2 depends on these answers:
- which endpoint Compose's healthcheck probes, and therefore whether `pixi run up --wait` returns only once the index is built;
- how a reviewer resets the index without `down -v` also wiping the Ollama models;
- graceful shutdown while SSE streams are still open.

## user · 2026-10-23 13:13:03 · context 7.8% (78.4k / 1000k)

reccomended on all

## assistant · 2026-10-23 13:13:36 · context 7.8% (78.4k / 1000k)

Round 1 is settled as recommended. Round 2 covers the questions that depended on it:

---

❓ **Q9 - What Compose's healthcheck probes**: Compose has only one healthcheck slot, and both `pixi run up --wait` and the frontend's `depends_on: service_healthy` hang off it. If it probes `/health`, `up` returns as soon as the process starts, and the reviewer's first question gets `index_not_ready`. If it probes `/ready`, `up` returns only once the stack can answer. Because `llm` doesn't gate readiness (Q2), a bad key doesn't hold `up` back.

➡️ The healthcheck probes **`/ready`**. Failures during the first boot's embedding don't count: `start_period: 300s` with `start_interval: 2s` covers that. `pixi run up` gets an explicit `--wait-timeout`, and before that it prints a one-line hint: "first Ollama run downloads ~2.7 GB — follow with `docker compose logs -f ollama-pull`". `/health` stays as the liveness check for anything outside Compose. The README explains the split: in Kubernetes it would be two probes, and Compose has only one.

---

❓ **Q10 - Swapping the embedder triggers a re-embed**: Passage ids are deterministic, and "changed" is decided by comparing a content fingerprint. If the fingerprint covers only the text, swapping the embedder silently leaves stale vectors behind.

➡️ The fingerprint is a hash of the Passage text, its metadata and the embedder model id. A model swap therefore re-embeds everything on the next sync, without a manual rebuild. Only a dimension change still fails fast, per ADR-0004.

---

❓ **Q11 - Resetting the index**: `down -v` would also wipe `ollama-models` and force a fresh 2.7 GB download.

➡️ A new `pixi run reindex` task stops the backend, runs `docker compose run --rm backend python -m app.ingest --rebuild` (drop the table, then sync under the advisory lock), and brings the backend back with `--wait`. Stopping the backend first means nothing reads a half-built table. `pixi run down` never passes `-v`. The README documents `docker compose down -v` as the "remove everything, including downloaded models" option.

---

❓ **Q12 - Failures in the background sync and restart policy**: What happens when phase 2 fails, for example because Postgres drops mid-embed?

➡️ It retries with exponential backoff capped at 30 s. Meanwhile `/ready`'s `index` check stays `ok: false`, and its `detail` holds the last error. The process never crashes over this. A partial sync is safe because the sync is idempotent, and the advisory lock is released when the connection closes. **No restart policy** on any service. A phase-1 validation failure exits non-zero, `up --wait` fails loudly with the container's logs, and nothing crash-loops.

---

❓ **Q13 - Graceful shutdown**:

➡️ Uvicorn runs with `--timeout-graceful-shutdown 10` and Compose with `stop_grace_period: 15s`. The `CMD` is already in exec form, so uvicorn as PID 1 receives SIGTERM. On shutdown, the lifespan cancels the sync task and in-flight Turns. Cancelling a Turn takes the same path as Stop, so the LLM call is cancelled. The client sees the stream end without `done`, and the UI shows its connection-lost error card.

---

❓ **Q14 - Metrics and tracing**:

➡️ Out of scope for the build. The `turn_completed` log carries the timings. The README's "what I'd do next" section names OpenTelemetry traces (with spans for the rewrite, retrieval and generation) and a Prometheus `/metrics` endpoint.

## user · 2026-10-23 13:13:54 · context 8.2% (81.8k / 1000k)

reccomended for all

## assistant · 2026-10-23 13:14:20 · context 8.2% (81.8k / 1000k)

Round 2 is settled too, so every branch of this ticket has now been visited. Before I write anything to the tracker, please confirm this is the shared understanding.

**Decided**
- **Ingestion:** the backend syncs at startup in two phases.
  - Phase 1 blocks startup: it validates every Article and exits non-zero naming the bad file.
  - Phase 2 runs in the background: the idempotent sync under a Postgres advisory lock, retrying with backoff capped at 30 s and never crashing the process.
  - The same sync is available as `python -m app.ingest`, and `knowledge-base/` is bind-mounted read-only.
- **Re-embedding:** the change fingerprint includes the embedder model id, so swapping the embedder re-embeds automatically. A new `pixi run reindex` task stops the backend, rebuilds the index and restarts it. `down` never passes `-v`.
- **`/ready`:** `database` and `index` decide its status. `llm` is reported but doesn't gate it; it's a cheap probe with no token generation, cached for 60 s, with `auth_failed`, `unavailable` and `model_missing` details.
- **Compose:** the healthcheck probes `/ready` (`start_period: 300s`, `start_interval: 2s`), and `pixi run up` gets a `--wait-timeout` plus the Ollama-download hint. No restart policy on any service. A one-shot `ollama-pull` service fills the `ollama-models` volume, and the backend waits on it with `required: false`.
- **LLM timeouts:**
  - Connect: 5 s.
  - Read: 60 s for Claude, 120 s for Ollama.
  - Turn deadline: 120 s for Claude, 240 s for Ollama, mapped to `llm_timeout`.
  - Rewrite step: 30 s.
  - Retries: the SDK's 2 retries for Claude, only before the first byte; none for Ollama.
- **Postgres:** `connect_timeout` of 5 s and `statement_timeout` of 10 s, with no retries. A new error code, `retrieval_unavailable`, covers database failures during a Turn.
- **Logging:** structlog, JSON in the image and console format in dev. One access line per request. A `turn_completed` event carries outcome, model, `PROMPT_VERSION`, Passages, scores and timings; question and Answer text appear only at DEBUG. A redacted `config_loaded` line is logged at startup.
- **Request ids:** nginx generates `X-Request-ID`. The backend binds it to every log line, echoes it in a response header and adds it to the error envelope, and the UI's error card shows it.
- **Shutdown:** uvicorn gets 10 s of graceful shutdown and Compose a 15 s grace period. Shutdown cancels the background sync and any in-flight Turns.
- **Out of scope:** metrics and tracing go in the README's "what I'd do next" section.

**What I'll write**
- **New build tickets:**
  - **Build the startup ingestion lifecycle and readiness checks**: the two-phase sync, the advisory lock, the CLI, `reindex`, `/ready` with its three checks, the Compose healthcheck and graceful shutdown. It will be blocked by **Build the Haystack retrieval adapter and indexing pipeline**, **Build the pgvector Compose service and test fixture** and **Build the ChatModel adapter with streaming and Stop**.
  - **Build structured logging and request ids**.
- **Notes on existing tickets:**
  - **Build the ChatModel adapter with streaming and Stop**: timeouts, retries and the probe.
  - **Build LLM provider settings, startup validation and the Ollama Compose profile**: the timeout settings and `ollama-pull`.
  - **Build the Haystack retrieval adapter and indexing pipeline**: the fingerprint and the Postgres timeouts.
  - **Build the chat API contract over a stub pipeline**: `retrieval_unavailable` and `request_id`.
  - **Build ChatService orchestration**: the Turn deadline and `turn_completed`.
  - **Build the chat page: streaming Turns, Citations and states**: show `request_id`.
  - **Build the Compose smoke job in CI**: probe `/ready`.
- **Fog:** I'll move "Failure & degraded-mode UX" out of the fog into a new grilling ticket, **Readiness banner and degraded-mode UX**, since the backend half is now decided.
- **No ADR and no new glossary terms:** each of these choices can be changed through configuration, and none of them introduces a domain term.

Shall I go ahead?

