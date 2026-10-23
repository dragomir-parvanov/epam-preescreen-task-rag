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

Development tasks:

| Task | What it does |
| --- | --- |
| `pixi run check-config` | Validate `.env` and the shell's backend settings; exits non-zero with the fix |
| `pixi run dev-backend` / `pixi run dev-frontend` | Run the backend (reload) and the Vite+ dev server locally |
| `pixi run lint` | ruff + `vp check` (oxfmt, type-aware oxlint) |
| `pixi run typecheck` | pyright (strict) + TypeScript 7 via `vp check` |
| `pixi run test` | pytest + Vitest (via Vite+). Needs Docker for the `pgvector` tests; `pytest -m "not pgvector"` in `backend/` leaves them out |
| `pixi run gen-types` | Regenerate the frontend's API types from the backend's OpenAPI schema; commit the result |

## Chat recording

The task requires the AI assistant conversation logs to be committed, so a Claude Code `Stop` hook (`.claude/hooks/record-session.sh`) saves every session in this repo to `chats/<start-time>_<first-prompt>.md`.

- Only user and assistant text is kept, so the logs read as a conversation rather than a dump of tool output.
- Each message shows its time and how full the context window was, for example `context 5.7% (57.4k / 1000k)`.
- Showing context % to prevent getting into the dumb zone
