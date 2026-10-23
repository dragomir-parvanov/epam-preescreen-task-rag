<!-- session: b262d9a7-563e-4b95-a175-2b22632edabb -->

## user · 2026-10-23 10:45:26 · context 4.8% (47.7k / 1000k)

<command-message>wayfinder</command-message>
<command-name>/wayfinder</command-name>
<command-args>I am given this task:
# Enterprise Knowledge Base RAG Chatbot

_For: Dragomir Parvanov_

_Language: TypeScript • Due in 5 days • Suggested time: ~6h_

## Overview
Customer Success Managers (CSMs) at OmniCorp Solutions currently spend hours manually searching through hundreds of internal product manuals to answer complex client configuration questions. You have been contracted to build a prototype Retrieval-Augmented Generation (RAG) chatbot that allows CSMs to ask natural language questions and receive accurate, cited answers based strictly on internal documentation.
Your task is to build a full-stack application consisting of a backend API and a frontend chat interface. The backend should ingest a small set of provided text documents (you should create 3-5 mock enterprise knowledge base articles), chunk them, store them in a local or in-memory vector store, and expose a chat endpoint. The frontend must be a web-based UI where users can type questions, view the AI's response, and critically, see the specific document citations used to generate the answer.
As a Lead Engineer, we expect you to focus on system architecture, API design, and operational readiness. You are free to choose the backend language you are most comfortable with (we recommend **C# / .NET** or **Python** based on your background). The solution should be easy to run locally (e.g., via Docker Compose), well-structured, and include basic tests. You may use any external LLM provider (e.g., OpenAI, Anthropic, Groq) by allowing the reviewer to supply their own API key via environment variables, or use a local model via Ollama. Do not include any paid API keys in your submission.

## Deliverables
- A single public GitHub repository (or gist URL) containing your complete solution.
- A backend service (e.g., C#/.NET Core, Python, or Node.js) implementing the document ingestion, RAG pipeline, and API endpoints.
- A frontend UI (e.g., React, Next.js, or Vite in TypeScript) demonstrating the chat workflow and displaying source citations.
- A `docker-compose.yml` file (or equivalent automated script) that spins up the entire stack seamlessly.
- A `README.md` explaining your architectural decisions, API design, trade-offs, and instructions on how to run and test the system.
- **MANDATORY:** An export of your AI assistant conversation logs (e.g., Cursor chat history, Copilot export, or Claude transcripts) committed to the repository.

## Suggested tools / libraries
- **Frontend:** React, Next.js, or Vite + TailwindCSS
- **Backend:** ASP.NET Core (C#), FastAPI/Flask (Python), or Express/NestJS (Node.js)
- **Vector Store:** ChromaDB, pgvector (via Docker), or a simple in-memory cosine similarity implementation
- **AI/RAG:** Microsoft Semantic Kernel, LangChain, LlamaIndex, or raw SDKs
- **LLM:** OpenAI API, Anthropic API (Bring Your Own Key), Groq API, or local Ollama

## On AI assistants & follow-up
- We expect and encourage you to use AI assistants (GitHub Copilot, ChatGPT, Claude, Cursor, etc.) to accelerate your work.
- **MANDATORY:** You must commit your AI assistant conversation logs to the repository and add a brief note in the README describing which tools were used and for what parts of the codebase.
- Be prepared to walk us through any block of code you submit. We will ask deep-dive questions on your architectural choices, API design, and trade-offs during the technical interview.

## How to submit
Reply to this email with **one** public GitHub repository or gist URL containing your solution.

lets solve it in a map.</command-args>

## assistant · 2026-10-23 10:46:04 · context 5.5% (55.1k / 1000k)

Before charting anything I need to settle the **destination**, because it fixes the scope of every ticket. I checked the repo: it's a fresh repo pushed to a public GitHub remote (`dragomir-parvanov/epam-preescreen-task-rag`), `gh` is authenticated, and there's no tracker config. Your Stop hook already records every session to `chats/`, which covers the mandatory AI-log deliverable as long as those files get committed. `engineering-principles.md` is empty.

Round 1 covers the destination and scope only. The breadth-first frontier comes after.

❓ **Q1 - What the map produces**: Wayfinder plans by default: the map is done when nothing is left to decide, and the build is handed off afterwards (e.g. `/to-spec` → `/to-tickets` → `/implement`). The other option is to override that in the Notes and carry implementation into the map itself.

➡️ Yes, planning only. The destination is **a locked build spec for the OmniCorp RAG chatbot submission**: stack, architecture, API contract, knowledge-base corpus, retrieval/citation behaviour, ops/run story, test strategy and README narrative are all decided and ready to hand to implementation. The ~6h budget goes on the build, not on the map.

---

❓ **Q2 - Where the map lives**: The options are GitHub issues on the public repo (a `wayfinder:map` issue with sub-issues and native blocking) or local markdown in `.scratch/`. GitHub issues are visible to the reviewers, which works in your favour for a "Lead Engineer, focus on architecture" brief: they can see how the decisions were reached. The downside is that it's public and can't be taken back cleanly.

➡️ Yes, GitHub issues on this repo. I'll also record that choice in a CLAUDE.md tracker note so later sessions find it.

---

❓ **Q3 - Language constraint**: The task header says **"Language: TypeScript"**, but the body recommends C#/.NET or Python and allows Node.js. Should the header count as binding, so the whole stack is TypeScript (Node backend + React/Vite frontend)?

➡️ Yes, TypeScript end to end. The header is the most specific instruction, and one language lets the API contract be a single shared type package. *(If you'd rather show off .NET, say so; this would then become a grilling ticket instead.)*

---

❓ **Q4 - Ambition level**: The suggested time is ~6h and the deadline is 5 days. Should we aim for **a small, deep, operationally credible prototype**? That means a few things done visibly well (cited answers, refusal when the docs don't cover it, health/readiness, one-command `docker compose up`, tests) instead of a wide feature list.

➡️ Yes. Target roughly 6–8h of build time and favour depth and defensibility over features. You'll be grilled on every block.

---

❓ **Q5 - Out of scope up front**: Should these be ruled **out of scope** for this effort: auth/RBAC, multi-tenancy, cloud deployment/IaC, ingesting real file formats (PDF/DOCX) or uploads, and a production-scale corpus ("hundreds of manuals")? The README would cover them as trade-offs and future work, but they wouldn't be built.

➡️ Yes, rule all five out. Each one gets a line in the README's "what I'd do next".

---

❓ **Q6 - The chat-log deliverable**: Should the existing `chats/` recording hook count as the answer to the mandatory AI-log requirement, so the map only has to decide how the README *presents* it and not how logs are captured?

➡️ Yes. Capture is already solved, and the README presentation becomes part of the README-narrative fog.

## user · 2026-10-23 10:49:53 · context 5.7% (57.4k / 1000k)

q1: actually, I want planning and implementing. When something is decided, spawn a ticket that can be picked by an agent. We do not want to accumulate one big pile of work and then start the coding, we want constant iteration
q2: github issues
q3: python for backend and react for frontend with vite with full typescript typing
q4: we do not care about time constraints, let that to me
q5: yep
q6: yes

## assistant · 2026-10-23 10:50:51 · context 5.7% (57.4k / 1000k)

Settled so far:

- **Destination:** a finished, submittable public repo. It has a FastAPI-style Python backend, a React + Vite + strict-TypeScript frontend, a one-command run, tests, a README covering architecture, API and trade-offs, and the AI logs committed.
- **Execution happens on the map:** each decision spawns build tickets that agents pick up.
- **Tracker:** GitHub issues.
- **Out of scope:** auth/RBAC, multi-tenancy, cloud/IaC, real file formats and uploads, a production-scale corpus.
- **AI logs:** the `chats/` hook already captures them.

Round 2 maps the frontier breadth-first. Q1–Q6 are meta and foundation decisions I think we can settle now, so the first build ticket can start right away. Q7 is the proposed set of decision tickets.

❓ **Q1 - A label for build work**: The four built-in wayfinder types (research/prototype/grilling/task) are all for *deciding*. Since this map also executes, should I add a fifth label, `wayfinder:build` (AFK, agent-driven, one vertical slice per ticket), declared in the map's Notes? That way the frontier visibly separates "needs you" from "an agent can just do it".

➡️ Yes, add `wayfinder:build`.

---

❓ **Q2 - How build tickets deliver**: Your standing rule is that I never commit unless asked. Should a build ticket count as that ask, scoped narrowly? The agent would work on a `build/<slug>` branch, commit there, push, and open a PR that closes the ticket. **You review and merge**, and nothing touches `main` without you. The alternative is to leave changes uncommitted in a worktree for you to commit.

➡️ Yes, branch + PR per build ticket, with the Notes recording that build tickets are a durable commit-on-branch authorization and never a push to `main`.

---

❓ **Q3 - Start coding immediately with a walking skeleton**: Should the first build ticket go on the frontier now? It would be a tracer bullet with no RAG yet: `docker compose up` brings up the backend `/health` endpoint and a Vite page that calls it through the generated typed client, plus tests and CI running in GitHub Actions. All the RAG decisions then land on a skeleton that already runs.

➡️ Yes.

---

❓ **Q4 - Toolchain**: Backend: **FastAPI, Pydantic v2, pydantic-settings, `uv`, `ruff`, `pyright --strict`, `pytest`**. Frontend: **Vite, React, TS `strict`, Tailwind, Vitest + Testing Library, ESLint**. To make "full TypeScript typing" hold across the wire, the frontend types would be **generated from FastAPI's OpenAPI schema** (`openapi-typescript` + `openapi-fetch`), with a CI check that fails if the generated types are stale.

➡️ Yes to all of it. The OpenAPI → TS codegen is the part worth defending in the interview.

---

❓ **Q5 - Repo layout**: `backend/`, `frontend/`, `knowledge-base/` (the corpus as markdown), `docs/adr/`, `chats/`, with a root `docker-compose.yml`, a `Makefile` (`make up`, `make test`, `make gen-types`) and `.env.example`.

➡️ Yes.

---

❓ **Q6 - No RAG framework**: Should we skip LangChain/LlamaIndex/Semantic Kernel and build the pipeline ourselves (chunker → embedder → vector store → retriever → prompt builder → LLM) behind small interfaces, using the provider's raw SDK? It's a few hundred lines, every block can be explained in the interview, and a fake LLM/embedder can be swapped in for tests.

➡️ Yes, our own pipeline on raw SDKs. The README explains why.

---

❓ **Q7 - The first set of decision tickets**: These are the questions that seem sharp enough to ticket now. **Unblocked** means takeable immediately.

| # | Ticket | Type | Blocked by |
|---|---|---|---|
| A | LLM & embedding provider options for a keyless / bring-your-own-key local run (OpenAI, Anthropic, Groq, Ollama, local fastembed/sentence-transformers): embeddings availability, image size, CPU latency, SDK ergonomics | research | — |
| B | Choose the LLM & embedding providers and the shape of the provider abstraction | grilling | A |
| C | Knowledge-base corpus: product domain, 3–5 articles, metadata schema, deliberately planted hard cases (cross-doc answers, version conflicts, tables, unanswerable questions) | grilling | — |
| D | Citation & grounding contract: what a citation *is* (doc/section/snippet), inline markers vs source list, refusal when the docs don't cover the question | grilling | — |
| E | Conversation model: single-turn vs multi-turn with history, streaming (SSE) vs one JSON response | grilling | — |
| F | Vector store: in-memory cosine vs Chroma vs pgvector | grilling | B |
| G | Chunking & retrieval: chunk shape, overlap, top-k, score threshold, hybrid/keyword search | grilling | B, C |
| H | API contract: endpoints, request/response schemas, error envelope, streaming protocol, versioning | grilling | D, E |
| I | Chat UI with citations: how sources, snippets and refusals look | prototype | D, E |
| J | Operational readiness: config, health vs readiness, ingestion lifecycle (startup vs job), logging, compose healthchecks | grilling | B, F |
| K | Test & evaluation strategy: unit/API/UI tests plus a golden-question eval that checks expected citations | grilling | C, D |

The **README narrative and how the AI tools are presented** stay in the fog until most of these land, along with prompt design details and error UX. Each resolved ticket will spawn its own build tickets, for example the corpus articles once C is decided.

➡️ Yes, chart these 11 plus the walking-skeleton build ticket. Once it's charted, I fire the research subagent for A.

## user · 2026-10-23 10:54:04 · context 6.3% (63.2k / 1000k)

q1: reccomended
q2: reccomended
q3: reccomended
q4: yes, install all of them through pixi, so we have easier setup
q5: yes
q6: lets use real RAG framework 
q7: yes

## assistant · 2026-10-23 10:54:46 · context 7% (69.8k / 1000k)

Now the map itself.

## assistant · 2026-10-23 10:55:07 · context 7.2% (71.7k / 1000k)

Map is #1. Next, the tickets: the foundation record first, then the walking skeleton, then the decisions in frontier order.

## assistant · 2026-10-23 10:57:06 · context 7.9% (78.9k / 1000k)

Next: close the foundation ticket with its resolution, fix the skeleton ticket's cross-reference to use the real id, and add the foundation decision to the map.

## assistant · 2026-10-23 10:57:24 · context 8.1% (81.4k / 1000k)

Charting is done. Now firing both research tickets in parallel. Each runs in its own worktree so their `research/*` branches don't collide.

## assistant · 2026-10-23 10:57:54 · context 8.5% (84.9k / 1000k)

The map is up as [Map: Enterprise Knowledge Base RAG Chatbot](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/1), with 15 child tickets and native blocking set up between them.

**Decided so far:** [Foundation: stack, toolchain, repo layout and build workflow](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/2). It holds everything we settled while charting: Python/FastAPI, React/Vite with strict TypeScript, pixi for all tooling, frontend types generated from the backend's API schema, a real RAG framework, and build work delivered as PRs that you merge. It's closed and is the first entry in the map's decisions list.

**Running now:** two research agents, each in its own worktree:
- [LLM & embedding provider options for a keyless or BYOK local run](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/4)
- [Python RAG framework options: LlamaIndex vs LangChain vs Haystack](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/5)

Each writes its findings to a `research/*` branch, comments a summary on its ticket and closes it. They don't open PRs or touch `main`. When they report back I'll add their pointers to the map.

**Ready to take now:**
- [Walking skeleton: pixi + FastAPI health + typed Vite client + Compose + CI](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/3) is a build ticket an agent can pick up immediately, so coding starts in parallel with the decisions.
- [Knowledge-base corpus: domain, articles, metadata and planted hard cases](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/6) needs you (grilling).
- [Citation & grounding contract](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/7) needs you (grilling).
- [Conversation model: single vs multi-turn, streaming](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/8) needs you (grilling).

**Waiting on other tickets:** choosing the RAG framework (needs the framework research), then the providers, vector store, chunking/retrieval, operational readiness and test strategy. The API contract and the chat-UI prototype wait on the citation and conversation tickets.

**Fog:** the README narrative, prompt design, what the reviewer sees when things fail (missing key, provider down, empty index), and a final submission checklist.

**Things to know:**
- I assumed **pixi tasks replace the Makefile**. It's recorded in the foundation ticket, so tell me if you want the Makefile back.
- I added a fifth label, `wayfinder:build`. The map's Notes treat picking up a build ticket as permission to commit on that ticket's own branch only, never `main`.
- The repo has no saved tracker config yet. To have other skills like `/to-tickets` and `/triage` default to GitHub issues, run `/setup-matt-pocock-skills` once.

To continue, run `/wayfinder` with the map (optionally naming a ticket), or point an agent at the walking skeleton.

## user · 2026-10-23 11:01:13 · context 8.6% (86.2k / 1000k)

i did setup the skills, yes we want to use pixi not makefiles

## assistant · 2026-10-23 11:01:22 · context 8.7% (86.7k / 1000k)

Both are confirmed, and nothing on the map needs to change:

- **Pixi:** the [Foundation](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/2) decision and the [Walking skeleton](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/3) ticket already say pixi tasks (`pixi run up`, `test`, `gen-types`, …) are the task runner and there's no Makefile.
- **Skills setup:** `CLAUDE.md` now points every skill at GitHub Issues, so build agents and later `/wayfinder` sessions will use the tracker without being told.

`git status` shows `.claude/worktrees/` as untracked. That's where the two research agents are running. When the walking skeleton adds the repo's `.gitignore`, it should ignore `.claude/worktrees/` so they never get committed by accident. Want me to add that to the walking-skeleton ticket's scope?

Both research agents are still running. When they finish I'll add their pointers to the map and pass on anything surprising.

## assistant · 2026-10-23 11:09:10 · context 9.1% (90.9k / 1000k)

The framework research is finished and closed: [Python RAG framework options: LlamaIndex vs LangChain vs Haystack](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/5). I've added its pointer to the map. The full findings are in [`research/rag-frameworks.md`](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/blob/research/rag-frameworks/research/rag-frameworks.md) on its research branch.

**The gist:**
- **Haystack 3.x is recommended.** It has a built-in step that matches the `[n]` markers in an answer to their source documents, it splits Markdown by heading, and it lets us plug in our own fake embedder for tests. It also passed `pyright --strict` in the agent's small offline trial. The catch is that it's only three months old and a major rewrite, and most tutorials and AI-generated examples still target 2.x and won't run. Exact version pins are needed, and Python must be ≥3.11.
- **LangChain 1.x is the runner-up.** It has the best typing and the fewest dependencies, but no citation component, so we'd write that ourselves.
- **LlamaIndex is not recommended.** It fails strict type-checking, its test fakes are useless (every text gets the same vector), and the company says its focus has shifted to its LlamaParse product.
- **No framework ships a fake embedder that ranks by meaning.** We'll need a small keyword-overlap fake whichever we choose, and in Haystack it slots straight in.

**Your unpushed commits are now public on the research branch.** The agent branched from your local `main`, which is 5 commits ahead of `origin/main` (the chat-recording hook, the agent skills, README edits, and the agent-skills setup in `69c35c2`). They're now visible on `research/rag-frameworks`. `origin/main` is unchanged, and `chats/` was untracked so no transcripts went up. The provider-research agent will probably do the same. These commits all have to go public anyway, so I'd leave it and simply push `main`. Say if you'd rather have the research branches rebased onto `origin/main` and force-pushed.

[Choose the RAG framework](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/9) is now on the frontier, alongside the walking skeleton, the corpus, the citation contract and the conversation model. The provider research is still running.

## assistant · 2026-10-23 11:12:46 · context 9.6% (96.2k / 1000k)

Both research tickets are now closed and on the map. The second one: [LLM & embedding provider options for a keyless or BYOK local run](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/4).

**The gist:** treat the embedder and the chat model as separate choices.
- **Embeddings always run locally, in-process, with fastembed** (`bge-small-en-v1.5`, 67 MB, no PyTorch). The index then never needs a key and never has to be rebuilt when the LLM changes.
- **The chat model is a runtime switch** behind one adapter that speaks OpenAI's API:
  - **Keyless default: Ollama.** The agent benchmarked it on this machine, CPU only: roughly 13–19 s per answer, and the first run downloads about 6 GB (the Ollama image alone is about 5 GB on disk).
  - **Bring your own key: OpenAI `gpt-4.1-mini`**, at under $0.001 per question.
  - **Optional: Groq**, which is free but limited to 8K tokens per minute and dropped all Llama models in August.
- Anthropic and Groq have no embeddings of their own.

**Findings I've put on the decision tickets they affect:**
- **On [Citation & grounding contract](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/7):** small local models cite poorly. One produced no `[n]` markers at all, and in JSON mode both listed every chunk as a source. The UI's source list may need to come from the retrieved chunks, not from the model's own citations.
- **On [Operational readiness](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/15):**
  - fastembed caches its model in `/tmp` by default, so the cache needs a volume or the model baked into the image.
  - Ollama in Docker on a Mac gets no GPU, so Mac reviewers may need a native Ollama.
  - `qwen3.5` needs thinking turned off, or answers get much slower.

**A correction to two things I said earlier:**
- **The repo is private, not public.** So the 5 local commits the research branches pushed are only visible to you, and there's nothing to worry about there.
- **Reviewers can't see the map yet.** It only becomes visible when you make the repo public, which is already on the submission checklist in the fog.

**Ready to take now:**
- [Walking skeleton](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/3), the build ticket an agent can pick up.
- Four decisions that need you:
  - [Knowledge-base corpus](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/6)
  - [Citation & grounding contract](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/7)
  - [Conversation model](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/8)
  - [Choose the RAG framework](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/9)

  The provider decision needs the framework decided first.

The research agents left two worktrees under `.claude/worktrees/`. I can remove them, since the findings are already on the pushed branches. I'd also add `.claude/worktrees/` to the walking skeleton's `.gitignore` scope.

