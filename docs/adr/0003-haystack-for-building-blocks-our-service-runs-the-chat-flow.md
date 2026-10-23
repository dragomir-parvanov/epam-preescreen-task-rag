# Haystack provides the building blocks; our own service runs the chat flow

We build on **Haystack 3.x**, but only for its building blocks: the Markdown splitter, embedders, document store, retriever, chat-generator provider adapters and test fakes. The query path (Follow-up rewrite → retrieval → threshold gate → `passages` event → streamed generation → answer assembly) is plain async Python in our own `ChatService`, not a Haystack `Pipeline`. The only `Pipeline` is the straight-line indexing one. `ChatService` depends on two small `Protocol`s, `PassageRetriever` and `ChatModel`. Every Haystack import lives in a single adapter package, which converts Haystack `Document`s to our own `Passage` type at the boundary. HTTP routes, `ChatService` and answer assembly never import Haystack.

We don't use `AnswerBuilder` either, although it was the research's headline reason for picking Haystack. Parsing `[n]` markers, renumbering, and flagging Uncited Answers is our own framework-free code (ADR-0001), so there is exactly one place that owns the citation contract.

## Considered Options

- **LangChain 1.x.** It is typed end to end and has the lightest dependency tree. We rejected it because once we write the orchestration ourselves, its remaining value is thinner: the Markdown splitter loses document metadata, its fake embedder needs an undeclared `numpy` and has no hook for meaning-aware vectors, and its docs are moving towards agents.
- **LlamaIndex.** Rejected: it raised errors under `pyright --strict` even on small sketches, its fake embedder gives every text the same vector, it gives cited chunks new ids so they can't be mapped back to the store, and its maintainers now focus on other products.
- **One Haystack query `Pipeline` with `stream()`.** Rejected: it emits passages *after* the tokens, and it gives no natural place for the threshold gate (which refuses without calling the LLM), for failing the Turn when the rewrite fails, or for cancelling on Stop. ADR-0002 needs all four.

## Consequences

- Haystack 3.0 shipped in July 2026. Most examples online, and most AI-generated code, show 2.x APIs that don't run on 3.x. Every Haystack package is pinned to an exact version, and `AGENTS.md` warns agents to use the 3.x docs only.
- Haystack telemetry is on by default, so we disable it in config and Compose.
- Haystack pipeline inputs and outputs are `dict[str, Any]`. That typing gap stays inside the adapter package, behind the two `Protocol`s.
- Haystack's chat generator streams through a callback. The `ChatModel` adapter feeds it into an async stream through a queue. If a test can't show that cancelling the task cancels the HTTP call underneath, that adapter alone falls back to the `openai` SDK.
