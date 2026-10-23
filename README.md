# epam-preescreen-task-rag

## How to run

Everything (Python, Node and the tools) is installed by [pixi](https://pixi.sh); the stack runs in Docker Compose.

```sh
cp .env.example .env   # optional: host ports and backend settings
pixi run up            # build and start backend + frontend, wait until healthy
pixi run down          # stop
```

The app is at <http://localhost:8080>, the backend's API docs at <http://localhost:8000/docs>.

Development tasks:

| Task | What it does |
| --- | --- |
| `pixi run dev-backend` / `pixi run dev-frontend` | Run the backend (reload) and the Vite dev server locally |
| `pixi run lint` | ruff + ESLint |
| `pixi run typecheck` | pyright (strict) + tsc |
| `pixi run test` | pytest + Vitest |
| `pixi run gen-types` | Regenerate the frontend's API types from the backend's OpenAPI schema; commit the result |

## Chat recording

The task requires the AI assistant conversation logs to be committed, so a Claude Code `Stop` hook (`.claude/hooks/record-session.sh`) saves every session in this repo to `chats/<start-time>_<first-prompt>.md`.

- Only user and assistant text is kept, so the logs read as a conversation rather than a dump of tool output.
- Each message shows its time and how full the context window was, for example `context 5.7% (57.4k / 1000k)`.
- Showing context % to prevent getting into the dumb zone
