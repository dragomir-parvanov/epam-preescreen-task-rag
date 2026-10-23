<!-- session: 2af97256-4e8d-46f3-8c43-34d111892dd0 -->

## user · 2026-10-23 12:51:32 · context 4.2% (41.6k / 1000k)

continue /wayfinder effort for https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/16

## assistant · 2026-10-23 12:51:54 · context 4.9% (49.1k / 1000k)

Unblocked and unclaimed. Claiming it first, then loading the map.

## assistant · 2026-10-23 12:53:32 · context 8% (79.5k / 1000k)

Claimed **Test & evaluation strategy** and read its inputs: the corpus, the citation contract, the conversation model, the framework choice and the HTTP API contract (closed, but not yet listed on the map). Here is the first round of decisions.

Some context first. Under ADR-0003, `ChatService` depends on two `Protocol`s, and all Haystack code sits in one adapter package. Under the HTTP API contract, the evaluation runs in-process against the answering service. **Choose the LLM & embedding providers** is still open in another session, so I've worded everything below to work with whichever provider is configured.

---

❓ **Q1** - **Test layers and what each one proves**: I propose five layers, each proving something the others can't:

1. **Pure unit tests** (no I/O): answer assembly (marker parsing, renumbering, Uncited flag, Refusal), history capping and truncation, Section-path/slug derivation.
2. **`ChatService` tests** with hand-written fakes of `PassageRetriever` and `ChatModel`: event order, the threshold gate skipping the LLM, the rewrite running only on follow-ups, a rewrite failure failing the Turn, the sentinel becoming a Refusal, and cancellation.
3. **Adapter tests** using Haystack's fakes with a keyword-overlap `embedding_fn` for the splitter, indexing and retriever. The `ChatModel` adapter is tested against a **tiny in-process fake OpenAI-compatible HTTP server**, mocking at the HTTP boundary rather than the SDK, so the "cancelling the task cancels the HTTP call" test is real.
4. **API tests**: `TestClient` over a stub answering service (already the scope of **Build the chat API contract over a stub pipeline**).
5. **Frontend tests**: Vitest + RTL + MSW, with SSE bodies streamed through MSW `ReadableStream`s. They assert what a user sees (Citations, the Uncited warning, Refusal, error per `code`, Stopped).

Also: no `unittest.mock` patching of our own code, no real fastembed or LLM in `pixi run test`, no coverage gate, and no Playwright browser E2E.

➡️ Yes, these five layers with those rules.

---

❓ **Q2** - **CI smoke test of the real Compose stack**: Unit tests can't catch the failures a reviewer hits first: the Docker build, the read-only Knowledge Base mount, ingestion at startup, `/ready`, and nginx buffering SSE. Options:
- (a) No smoke test in CI; `pixi run up` is checked by hand.
- (b) A CI job that runs `pixi run up` with **`LLM_PROVIDER=fake`**, waits for `/ready`, then runs `curl -N` against `/api/chat` through nginx and asserts that `passages` arrives before `done`, frame by frame.
- (c) The same job with real Ollama in CI (~6 GB pull, slow).

(b) needs **Choose the LLM & embedding providers** to offer a `fake` provider selectable by config. I'd leave a comment there.

➡️ Yes to (b): a keyless Compose smoke job, plus a request for a `fake` provider mode.

---

❓ **Q3** - **Split the evaluation into a keyless retrieval eval and a full LLM eval**: Retrieval doesn't need an LLM. With the real fastembed embedder it is deterministic. So:
- **`pixi run eval-retrieval`** (keyless, deterministic, **gates CI**): asserts that every answerable golden question's `expected_sources` appear in the retrieved Passages (recall@k), and that the threshold gate **doesn't** fire on answerable questions (a false Refusal is the worse error). Whether the gate fires on unanswerable questions is **reported, not asserted**, because the model sentinel is the backstop there. The fastembed model (~130 MB) is cached in CI.
- **`pixi run eval`** (opt-in, needs a configured LLM, **never gates CI**): the full pipeline in-process against `ChatService`. A public repo can't safely hold a key secret for PRs from forks, and LLM output varies from run to run.

The actual recall@k and threshold numbers are left to **Chunking & retrieval strategy**.

➡️ Yes: two evals, with only the retrieval one gating CI.

---

❓ **Q4** - **What the full eval scores, and how facts are checked**: For each question it would score:
- **Outcome**: Refusal expected vs. got. On a Refusal it also records the reason.
- **Citation precision and recall** at **Section** level against `expected_sources`.
- **Retrieval recall**, so a citation failure can be told apart from a retrieval failure (ADR-0001's reason for keeping `retrieved_passages`).
- **Uncited Answer** rate.
- **Facts.**

For facts, prose `expected_facts` can't be matched mechanically. Options:
- (a) An **LLM judge**. Rejected in spirit by ADR-0001, and small local models are poor judges.
- (b) Change the schema to **`must_mention`**: a list of term groups, any one of which counts (e.g. `[["Enterprise"], ["SSO", "single sign-on"]]`), matched case-insensitively. Keep `expected_facts` as human-readable notes.
- (c) No automated fact check: print the answers for a human to read.

For **partial** questions, ask **Prompt design** to fix a canonical gap phrase (e.g. "The Knowledge Base doesn't cover …") so the eval can detect it lexically.

➡️ Yes to (b) plus the canonical gap phrase. I'd comment on **Write the Knowledge Base articles and golden questions** (for the schema) and on **Prompt design** (for the phrase).

---

❓ **Q5** - **Testing the Follow-up rewrite**: The plumbing is covered by `ChatService` tests with a fake `ChatModel` (Q1). For rewrite *quality*, I propose an optional **`history: [{question, answer}]`** field in the golden schema, with **authored, fixed** history answers (not generated live) so each case stands alone, and a new category, `follow-up`. Three to start:
- "and on v2?" after the webhook-signature question → expects the v2 Section, and `must_mention` "v2" in the Standalone Question.
- "what about Enterprise?" after the Business rate-limit question → expects the Rate limits Section.
- A topic change ("Does Nimbus support LDAP?" after an SSO Turn) → must stay unchanged and be refused.

The case matches on `expected_sources` and `must_mention` against `standalone_question`, never on an exact string.

➡️ Yes: the `history` field, a `follow-up` category and these three cases. The retrieval eval runs them too, using the authored ideal Standalone Question in a `standalone_question` field, so CI checks retrieval for follow-ups without an LLM.

---

❓ **Q6** - **Eval report and committed baselines**: Every `pixi run eval` prints a per-question table plus totals (outcome accuracy, citation precision and recall, retrieval recall, Uncited rate, `must_mention` hit rate, p50/p95 latency). It also writes **`eval/results/<provider>-<model>.json` + `.md`**, with the date, git SHA and settings in the header. You commit a baseline for each provider and model you ran (e.g. keyless Ollama vs BYOK OpenAI), and the README quotes them. That gives reviewers real numbers for the "small models cite poorly" trade-off.

➡️ Yes: a console table plus committed per-model JSON/Markdown baselines in `eval/results/`, which the README cites.

## user · 2026-10-23 12:55:24 · context 8.5% (85.2k / 1000k)

reccomended

## assistant · 2026-10-23 12:55:42 · context 8.5% (85.2k / 1000k)

All six accepted. One short final round on where the eval code lives and how the build work is split:

---

❓ **Q7** - **Eval code location and keeping the golden set honest**: The runner is backend Python, because it calls `ChatService` and the adapters in-process. I'd put it in a `backend/evaluation/` package, beside `app/` rather than inside it, so the server never imports it. It would read `../eval/golden-questions.yaml` and write to `../eval/results/`. A Pydantic model defines the golden schema, including `history`, `standalone_question` and `must_mention`.

A plain test in `pixi run test` would also load the YAML and check that every `expected_sources` entry (Article id + Section) **exists in `knowledge-base/`**. That way an edit to an Article that renames a heading fails CI straight away, not in the next eval run.

➡️ Yes: `backend/evaluation/`, a Pydantic golden schema, and a drift test that checks golden sources against the Knowledge Base.

---

❓ **Q8** - **How the build work is split**: Three build tickets:

1. **Build the golden schema and keyless retrieval eval in CI**: the schema, the drift test, `pixi run eval-retrieval`, the CI step and the fastembed cache. Blocked by **Write the Knowledge Base articles and golden questions**, **Build the Haystack retrieval adapter and indexing pipeline** and **Chunking & retrieval strategy** (for the thresholds).
2. **Build the full LLM evaluation and baseline reports**: `pixi run eval`, the scoring, and the JSON/Markdown reports. Blocked by ticket 1, **Prompt design** and **Choose the LLM & embedding providers**.
3. **Build the Compose smoke job in CI**. Blocked by **Choose the LLM & embedding providers** (the `fake` mode), **Operational readiness** (`/ready`, ingestion at startup) and **Build the chat API contract over a stub pipeline**.

The Q1 test layers aren't a ticket. They're the standard every build ticket already follows (TDD). I'd record them in the resolution and, if you want, as a short "Testing" section in `AGENTS.md` so agents follow them.

➡️ Yes: these three tickets with those blockers, plus a short "Testing" section in `AGENTS.md`.

## user · 2026-10-23 12:58:48 · context 8.7% (86.9k / 1000k)

reccomended

## assistant · 2026-10-23 12:58:59 · context 8.7% (86.9k / 1000k)

Both accepted, so the frontier is empty. Now recording: the glossary term, the `AGENTS.md` Testing section, comments on the tickets this feeds, three build tickets, then the resolution and the map.

## assistant · 2026-10-23 12:59:22 · context 9.4% (93.9k / 1000k)

Now the three build tickets.

## assistant · 2026-10-23 13:00:56 · context 10.4% (103.5k / 1000k)

I'm folding the `fake` provider into the smoke ticket and re-pointing its blockers. The full eval also needs **Build ChatService orchestration**.

## assistant · 2026-10-23 13:01:18 · context 10.5% (105.3k / 1000k)

**Prompt design** has also closed, so I'm checking whether it already fixed a canonical gap phrase before I comment on it.

## assistant · 2026-10-23 13:01:53 · context 11% (109.8k / 1000k)

Fixing the `AGENTS.md` adapter line for the native providers, then posting the resolution.

## assistant · 2026-10-23 13:02:21 · context 11.3% (113k / 1000k)

Now the map: I'm re-reading it fresh (other sessions edit it too) and appending one line to Decisions-so-far.

## assistant · 2026-10-23 13:02:47 · context 11.7% (116.9k / 1000k)

I've settled and closed **Test & evaluation strategy**, and added its line to the map's Decisions so far.

**What we decided:**
- **Five test layers**, each proving one thing: pure unit tests, `ChatService` tests with hand-written fakes, adapter tests, API tests and frontend tests. `pixi run test` never needs a key or network access, and there's no coverage gate and no browser end-to-end tests.
- **A keyless smoke test of the real Compose stack in CI.** It adds a `fake` LLM provider and streams one chat request through nginx.
- **Two evaluations:**
  - `pixi run eval-retrieval` uses the real embedder with no LLM, and CI fails if it fails.
  - `pixi run eval` runs the full pipeline against Claude or Ollama when you choose to, and never blocks CI.
- **Facts are checked by keyword matching** against a new `must_mention` field, not by an LLM judge.
- **Follow-up questions get their own golden cases**, with fixed earlier Turns and the ideal rewrite. Results per model are committed to `eval/results/` for the README to quote.

**Two things changed during the session.** Other sessions closed **Choose the LLM & embedding providers** and **Prompt design** while we talked:
- The providers are now native Anthropic and Ollama, so each provider's tests fake that provider's own streaming format rather than one OpenAI-style server.
- The providers decision left no `fake` mode and handed it to this ticket. Building it is now part of the smoke-test ticket.
- **Prompt design** only says to name the gap "plainly". The fixed "not covered" phrase the eval needs is requested on **Build the prompt module** instead.

**New build tickets:**
- [Build the golden schema and keyless retrieval eval in CI](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/28), blocked by the articles, the retrieval adapter and **Chunking & retrieval strategy**.
- [Build the full LLM evaluation and baseline reports](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/29), blocked by the ticket above and **Build ChatService orchestration**.
- [Build the Compose smoke job in CI](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/30), blocked by **Operational readiness**, the stub chat API, ChatService orchestration, provider settings and the ChatModel adapter.

I also commented on the tickets this feeds: the golden-question schema changes, the gap phrase, what the retrieval eval checks for chunking, how to test each provider for the ChatModel adapter, and ChatService orchestration.

**Local changes, not committed** (on `docs/wayfinder-decisions`): `GLOSSARY.md` has a new term, **Golden Question**. `AGENTS.md` has a new **Testing** section with the layer rules.

**Two problems on the map from other sessions:**
- **HTTP API contract** is closed but missing from Decisions so far.
- The **Conversation model** line still mentions a non-streaming JSON twin, which the HTTP API contract dropped. **Build ChatService orchestration** still lists that twin in its scope; I flagged it there.

Want me to fix those two map lines?

## user · 2026-10-23 13:03:50 · context 11.8% (118.2k / 1000k)

yes

## assistant · 2026-10-23 13:04:09 · context 12% (119.6k / 1000k)

I've fixed both lines on the map:

- **Conversation model** no longer lists the non-streaming JSON twin as part of the decision. It now notes that **HTTP API contract** dropped the twin later.
- **HTTP API contract** now has its own line in Decisions so far, placed after **Choose the RAG framework**. It summarises the endpoints, the stream events, the `ChatResult` union and the error envelope, and links the two build tickets it spawned: **Build the chat API contract over a stub pipeline** and **Build Knowledge Base browsing endpoints**.

I re-read the map just before saving, and nothing else on it had changed.

