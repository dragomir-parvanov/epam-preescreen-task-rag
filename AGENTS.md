## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues on `dragomir-parvanov/epam-preescreen-task-rag`, using the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Uses the five default triage labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human` and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Haystack

Haystack **3.x** only, and only inside `backend/app/rag/haystack/` (a test enforces it). 2.x examples don't run: `OpenAIGenerator`, `AsyncPipeline` and `haystack.components.embedders.SentenceTransformers…` are gone. Check APIs against the installed source or the [3.x docs](https://docs.haystack.deepset.ai/docs/intro) and the [2.x → 3.x migration guide](https://docs.haystack.deepset.ai/docs/migration), not 2.x memory.

## Testing

Choose a test's layer by what it proves:

- **Pure logic** (answer assembly, history capping, Section slugs): plain unit tests.
- **`ChatService`**: hand-written fakes of `PassageRetriever` and `ChatModel`, passed in through those interfaces.
- **Haystack adapter**: Haystack's own fakes with a keyword-overlap `embedding_fn`, over a real pgvector started by `testcontainers` from the pinned `POSTGRES_IMAGE` (ADR-0004). These tests are marked `pgvector` and error, never skip, when Docker isn't running; deselect them with `-m 'not pgvector'`. Each `ChatModel` generator runs against an in-process fake server that speaks that provider's streaming protocol, so the fake sits at the HTTP boundary.
- **Routes**: `TestClient` over a stub answering service.
- **The wiring** (image, Knowledge Base mount, ingestion, `/ready`, nginx streaming): only the Compose smoke, `pixi run smoke` (CI's `smoke` job). It runs the real stack on the keyless `fake` LLM provider; `fake` is for this smoke only, never a default.
- **Frontend**: Vitest + Testing Library + MSW (SSE bodies streamed as `ReadableStream`), asserting what the CSM sees.

`pixi run test` is keyless. It is offline once the pinned `pgvector/pgvector` image has been pulled, and it needs Docker for the `pgvector` tests. The real embedder runs only in `pixi run eval-retrieval`, which CI gates on. A real LLM runs only in the opt-in `pixi run eval`, which never gates.
