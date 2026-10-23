# epam-preescreen-task-rag

## How to run

Everything (Python, Node and the tools) is installed by [pixi](https://pixi.sh); the stack runs in Docker Compose.

```sh
cp .env.example .env   # then set ANTHROPIC_API_KEY, or switch to the keyless Ollama block
pixi run up            # check the config, then build and start the stack and wait until healthy
pixi run down          # stop
```

The LLM is Claude (`claude-opus-5-5`) by default, which needs `ANTHROPIC_API_KEY` in `.env` or exported in your shell. Without a key, `BACKEND_LLM_PROVIDER=ollama` plus `COMPOSE_PROFILES=ollama` runs `qwen3.5:2b` locally instead: the first `up` downloads about 8 GB (the Ollama image and the model) into Docker, and `docker compose logs -f ollama-pull` follows the model download. `pixi run up` first runs `pixi run check-config`, which validates `.env` with the backend's own settings and prints the fix before any Docker build.

The app is at <http://localhost:8080>, the backend's API docs at <http://localhost:8000/docs>.

### First boot and readiness

`pixi run up` returns only once the stack can answer: the backend's Compose healthcheck probes `GET /ready`, which passes when Postgres answers and the Knowledge Base has been synced into the index, and the frontend waits for a healthy backend. So <http://localhost:8080> answers only after `up` returns; the browser has no first-boot screen of its own. On a keyless first run, follow the Ollama model download with `docker compose logs -f ollama-pull`.

The first boot embeds every Passage of the Knowledge Base (about 1,150) on the CPU, which takes about 40 s on a 12-CPU machine and a few minutes on a small laptop or CI runner; later boots re-embed only what changed. `docker compose logs -f backend` shows it as `index_sync_progress` lines (`done` of `total`), then `index_synced`. The healthcheck allows 5 minutes for it before marking the backend unhealthy.

At startup the backend:

1. validates every Article in `knowledge-base/` (bind-mounted read-only). A malformed Article stops it with a log line naming the file, so `up` fails;
2. syncs the index in the background, re-embedding only Passages that changed, under a Postgres advisory lock. A failed sync is retried with backoff (up to 30 s apart); `/ready`'s `index` check shows the last error meanwhile.

To pick up an edited Article, restart the backend (`docker compose restart backend`). `GET /ready` also reports an `llm` check (is the key valid, is the Ollama model pulled?), but a provider outage doesn't make the stack unready: the UI shows it instead. Kubernetes would get two probes, `/health` for liveness and `/ready` for readiness; Compose has a single healthcheck, so it uses readiness.

`pixi run down` keeps the index and the downloaded Ollama models. `docker compose down -v` deletes both.

Development tasks:

| Task | What it does |
| --- | --- |
| `pixi run check-config` | Validate `.env` and the shell's backend settings; exits non-zero with the fix |
| `pixi run ingest` | Sync the index with `knowledge-base/` once, in the backend image (what startup does) |
| `pixi run reindex` | Stop the backend, drop and rebuild the index, start the backend again; leaves the Ollama models alone |
| `pixi run dev-backend` / `pixi run dev-frontend` | Run the backend (reload) and the Vite+ dev server locally |
| `pixi run lint` | ruff + `vp check` (oxfmt, type-aware oxlint) |
| `pixi run typecheck` | pyright (strict) + TypeScript 7 via `vp check` |
| `pixi run test` | pytest + Vitest (via Vite+). Needs Docker for the `pgvector` tests; `pytest -m "not pgvector"` in `backend/` leaves them out |
| `pixi run smoke` | What CI's smoke job runs: the whole stack on the keyless `fake` LLM provider (a canned reply, smoke tests only), as its own Compose project on ports 18080/18000/15432, checked through nginx (`/ready`, the Articles, a streamed cited Answer, a Follow-up, a Refusal); then removed with its volume |
| `pixi run eval-retrieval` | The keyless retrieval eval: indexes the Knowledge Base with the real embedder in a throwaway pgvector (needs Docker; ~1.5 min on 12 CPUs) and prints, per Golden Question, where its expected Sections rank (hybrid, dense-only, and without bge's query prefix) and what the threshold gate does at the configured `BACKEND_RETRIEVAL_TOP_K` / `BACKEND_RETRIEVAL_MIN_SCORE`. Exits non-zero below the recall bars or on a gate Refusal of an answerable question |
| `pixi run gen-types` | Regenerate the frontend's API types from the backend's OpenAPI schema; commit the result |

## Chat recording

The task requires the AI assistant conversation logs to be committed, so a Claude Code `Stop` hook (`.claude/hooks/record-session.sh`) saves every session in this repo to `chats/<start-time>_<first-prompt>.md`.

- Only user and assistant text is kept, so the logs read as a conversation rather than a dump of tool output.
- Each message shows its time and how full the context window was, for example `context 5.7% (57.4k / 1000k)`.
- Showing context % to prevent getting into the dumb zone
