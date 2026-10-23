<!-- session: ccfa8624-ce34-4452-bf0b-86fec780fbf2 -->

## user · 2026-10-23 12:07:28 · context 4.2% (41.6k / 1000k)

continue /wayfinder effort for https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/9

## assistant · 2026-10-23 12:07:49 · context 4.3% (42.9k / 1000k)

The project has a wayfinder skill. I'll try invoking it.

## assistant · 2026-10-23 12:07:59 · context 5% (49.8k / 1000k)

Unblocked and unclaimed. Claiming it, then loading the map.

## assistant · 2026-10-23 12:09:32 · context 8.1% (80.9k / 1000k)

Ticket **Choose the RAG framework** is unblocked, and I've claimed it. I read the framework research, ADR-0001, ADR-0002 and the build ticket for answer assembly. I also checked PyPI: `haystack-ai` 3.4.1, `fastembed-haystack` and `chroma-haystack` all support our Python 3.13.

One thing has changed since the research was written. Its main argument for Haystack was `AnswerBuilder`, which maps `[n]` markers to documents. Since then, the citation contract and **Build answer assembly** have made `[n]` parsing, renumbering and the Uncited rule our own framework-free code. That advantage is mostly gone, so the framework has to win on its other building blocks. Round 1:

---

❓ **Q1 - Framework: Haystack 3.x over LangChain 1.x**

Without the citation mapper, the comparison looks like this:

- **Haystack 3.4:**
  - **For:**
    - Its Markdown header splitter skips code fences and sets `header` + `parent_headers`, so the Section path comes almost free.
    - Its fake embedder takes an `embedding_fn=` hook, so we can plug in a keyword-overlap fake and test retrieval ranking for real.
    - The indexing pipeline is an explicit graph that reads like the architecture diagram.
    - One `OpenAIChatGenerator` with `api_base_url` covers Ollama, OpenAI and Groq, which matches the "one OpenAI-compatible adapter" idea from the provider research.
    - The `fastembed-haystack` integration exists.
  - **Against:**
    - 3.0 shipped only 3 months ago, so most examples online, and most AI-generated code, are 2.x and won't run.
    - Pipeline inputs and outputs are `dict[str, Any]`.
    - Telemetry is on by default.
- **LangChain 1.x:**
  - **For:** typed end to end and the lightest dependency tree.
  - **Against:**
    - The splitter returns `{h1, h2}` and you merge your own metadata back in.
    - The fake embedder needs an undeclared `numpy`, and none of its fakes understand meaning.
    - Its docs are moving towards agents.
    - If we hand-write retrieve → prompt → cite, it's even harder to answer "why a framework at all?"
- **LlamaIndex:** not considered (worst under `pyright --strict`, unusable fakes, citation ids lost).

➡️ Haystack 3.x. We'd defend it as "the framework owns the building blocks (splitting, embedding, store, retriever, provider adapters, test fakes); we own the contract (orchestration, citations, refusals)".

---

❓ **Q2 - Our own code runs the chat flow, not one framework pipeline**

We'd write the query path ourselves as plain async Python in a `ChatService`:

rewrite (follow-ups only) → retrieve → threshold gate → emit `passages` → stream generation → answer assembly → `done`

The decisions we've already made don't fit a single `Pipeline.stream()`:

- **Order:** a single pipeline emits passages *after* the tokens, and we send them before.
- **Threshold gate:** it has to refuse without calling the LLM.
- **Rewrite failure:** a failed rewrite has to fail the Turn.
- **Stop:** has to cancel the LLM call when the client disconnects.

Framework `Pipeline`s would be used only for straight-line batch work, i.e. **indexing**.

➡️ Yes: we write the query flow ourselves, and the only framework `Pipeline` is the indexing one.

---

❓ **Q3 - Where the framework stops: two small interfaces**

- **One place for framework code.** Every framework import lives in a single adapter package, e.g. `app/rag/haystack/`.
- **What `ChatService` depends on.** Two Python `Protocol`s (typed interfaces):
  - `PassageRetriever`: takes a Standalone Question and returns ranked Passages with their scores.
  - `ChatModel`: `stream(messages)` gives an async stream of text pieces, and `complete(messages)` returns the whole reply (used for the rewrite).
- **Conversion at the edge.** Framework `Document`s become our own `Passage` type at that boundary, so `dict[str, Any]` never reaches our code.
- **What stays framework-free.** HTTP routes, `ChatService` and answer assembly never import the framework.
- **Tests:**
  - `ChatService` tests use small hand-written fakes of the two interfaces, so they're fast and deterministic and cover order, gate and cancellation.
  - Adapter tests use Haystack's fakes, with the keyword-overlap `embedding_fn`.
- **Indexing.** It gets no interface: one plain `build_index(...)` function in the adapter package, run at startup. There's only one implementation, so an interface would be ceremony.

➡️ Yes: the two interfaces as described, and the framework stays inside the adapter package.

---

❓ **Q4 - Pinning and hygiene for a three-month-old major version**

- Pin the framework and every integration to **exact** versions in `pixi.toml` (`==`, not `>=`).
- Set `HAYSTACK_TELEMETRY_ENABLED=False` in the backend config defaults and in Compose.
- Add a short note to `AGENTS.md`: "Haystack **3.x** only: 2.x examples (`OpenAIGenerator`, `AsyncPipeline`, `haystack.components.embedders.SentenceTransformers…`) won't run". Link the 3.x docs and the migration guide.

➡️ Yes, all three.

---

❓ **Q5 - Fallback for streaming plus Stop**

Haystack's chat generator streams through a `streaming_callback`; it doesn't hand back an async stream we can loop over. The plan:

- Inside the `ChatModel` adapter, feed that callback into an `asyncio.Queue` and read the queue as a stream.
- Write a test proving that cancelling the task cancels the HTTP call underneath.
- If that test can't be made to pass cleanly, implement `ChatModel` with the `openai` SDK directly (`AsyncOpenAI(base_url=…)`). Nothing changes outside the adapter, and the README records it as a deliberate, contained exception.

➡️ Yes: try the framework generator first, use the plain SDK only if the cancellation test fails, and decide this in the build ticket, not here.

---

❓ **Q6 - Record this as ADR-0003**

It passes all three tests for an ADR:

- **Hard to reverse:** every adapter and test depends on it.
- **Surprising without context:** "why use Haystack but not its `AnswerBuilder` or a query `Pipeline`?"
- **A real trade-off:** we chose it over LangChain.

Proposed title: "Haystack provides the building blocks; our own service runs the chat flow".

➡️ Yes.

## user · 2026-10-23 12:44:47 · context 8.5% (84.8k / 1000k)

reccomended all

## assistant · 2026-10-23 12:45:01 · context 8.5% (84.8k / 1000k)

Q1–Q6 are settled. One question is left: which build tickets this decision should create. The map says decisions spawn build work, but most of the Haystack code depends on choices that haven't been made yet: providers, vector store, and chunking.

---

❓ **Q7 - Build tickets to create from this decision**

- **A. Build the Haystack retrieval adapter and indexing pipeline.**
  - **Scope:** exact-pinned Haystack, telemetry off, the `AGENTS.md` 3.x note, the `PassageRetriever` interface, `build_index(...)` over `knowledge-base/`, and the conversion from `Document` to `Passage`.
  - **Tests:** adapter tests using the keyword-overlap `embedding_fn` fake.
  - **Blocked by:** **Choose the LLM & embedding providers and their configuration**, **Choose the vector store**, **Chunking & retrieval strategy**, and **Build answer assembly: citations, Uncited Answers and Refusals** (which defines the `Passage` type).
- **B. Build the `ChatModel` adapter with streaming and Stop.**
  - **Scope:** the `ChatModel` interface, the Haystack chat-generator adapter that turns the callback into a stream, and the cancellation test, with the `openai` SDK fallback as decided in Q5.
  - **Blocked by:** **Choose the LLM & embedding providers and their configuration**.
- **Left out on purpose:** the `ChatService` orchestration itself (rewrite → gate → events → assembly). It depends on the HTTP API contract and Prompt design, so the **HTTP API contract** ticket should create it, as it already plans to.

➡️ Yes: create A and B with those blockers, and leave `ChatService` to **HTTP API contract**.

## user · 2026-10-23 12:47:45 · context 8.6% (86.2k / 1000k)

yes

## assistant · 2026-10-23 12:48:02 · context 8.9% (89.3k / 1000k)

Now the build tickets.

## assistant · 2026-10-23 12:48:38 · context 9.2% (91.7k / 1000k)

The **HTTP API contract** ticket doesn't mention `ChatService` yet, so I'll add a hand-off comment to it, then record the resolution.

## assistant · 2026-10-23 12:49:14 · context 9.5% (94.9k / 1000k)

I closed **[Choose the RAG framework](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/9)** after posting the resolution, and added the decision to the map's Decisions so far.

**What we decided:**
- **Framework:** Haystack 3.x, used only for its building blocks: the Markdown splitter, embedders, document store, retriever, provider adapters and test fakes.
- **What we don't use:** Haystack's `AnswerBuilder`, because our own answer-assembly code already owns the `[n]` citation markers, and a Haystack query `Pipeline`, because one pipeline can't handle the passages-first order, the threshold gate, the rewrite-failure rule or Stop.
- **Who runs the chat flow:** our own `ChatService`, written as plain async Python. It talks to Haystack only through two interfaces, `PassageRetriever` and `ChatModel`, and all Haystack code lives in one adapter package. Routes, `ChatService` and answer assembly never import Haystack.
- **Housekeeping:**
  - Every Haystack package is pinned to an exact version.
  - Telemetry is off.
  - An `AGENTS.md` note warns that 2.x examples won't run on 3.x.
- **Fallback for Stop:** if the Haystack chat generator can't be made to cancel its HTTP call when the task is cancelled, the `ChatModel` adapter alone switches to the `openai` SDK.

**New and changed tickets:**
- **[Build the Haystack retrieval adapter and indexing pipeline](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/21)**: waits on **Choose the LLM & embedding providers and their configuration**, **Choose the vector store**, **Chunking & retrieval strategy** and **Build answer assembly: citations, Uncited Answers and Refusals**.
- **[Build the ChatModel adapter with streaming and Stop](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/22)**: waits on **Choose the LLM & embedding providers and their configuration**.
- **HTTP API contract**: I added a comment asking it to create the `ChatService` build ticket once it's resolved.

**Local change, not committed:** the new ADR at `docs/adr/0003-haystack-for-building-blocks-our-service-runs-the-chat-flow.md`.

No new glossary terms came out of this, and no "Not yet specified" items became specific enough to ticket.

Closing this ticket unblocks five: **Choose the LLM & embedding providers and their configuration** (first in map order, and it blocks both new build tickets), **Choose the vector store**, **Chunking & retrieval strategy**, **Test & evaluation strategy** and **Prompt design**.

## user · 2026-10-23 12:49:48 · context 9.6% (96k / 1000k)

commit everything

## assistant · 2026-10-23 12:49:59 · context 9.7% (96.8k / 1000k)

You're on `main` and I'm not supposed to commit directly to it, so I'll put the commits on a new branch: one for the decision docs, one for the chat logs.

## assistant · 2026-10-23 12:50:06 · context 9.8% (97.8k / 1000k)

I committed everything to a new branch, `docs/wayfinder-decisions`, because I shouldn't commit straight to `main`. The working tree is now clean.

- `e03dac7` **docs: record glossary and ADRs 0001-0003 from wayfinder decisions**: `GLOSSARY.md` and the three ADRs under `docs/adr/`.
- `4b1b6f2` **docs: add wayfinder session conversations**: the new and updated logs under `chats/`.

Nothing is pushed. If you'd rather have these on `main`, `git switch main && git merge --ff-only docs/wayfinder-decisions` will move them across. If you want a PR instead, I can push the branch and open one.

The recording hook rewrites this session's log in `chats/` at the end of each turn, so that file will show as modified again after this reply.

