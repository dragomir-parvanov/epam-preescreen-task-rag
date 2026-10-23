## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues on `dragomir-parvanov/epam-preescreen-task-rag`, using the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Uses the five default triage labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human` and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Haystack

Haystack **3.x** only, and only inside `backend/app/rag/haystack/` (a test enforces it). 2.x examples don't run: `OpenAIGenerator`, `AsyncPipeline` and `haystack.components.embedders.SentenceTransformers…` are gone. Check APIs against the installed source or the [3.x docs](https://docs.haystack.deepset.ai/docs/intro) and the [2.x → 3.x migration guide](https://docs.haystack.deepset.ai/docs/migration), not 2.x memory.
