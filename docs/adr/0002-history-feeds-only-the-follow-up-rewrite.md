# Conversation history feeds only the Follow-up rewrite, is sent by the client, and is never stored

Conversations are multi-turn, but generation never sees earlier Turns. When a question has history, one small LLM call rewrites it into a Standalone Question. Retrieval searches with that, and generation gets only the Standalone Question plus this Turn's Passages, so every Citation is tied to Passages retrieved for this Turn. The client sends the history with every request, as `{question, answer}` pairs capped server-side at the last 3 Turns with answers truncated. The server keeps no state, so there is no session store, no conversation id and nothing to lose on restart. Turns that a Refusal ended stay in the history. Turns the CSM stopped are left out.

## Considered Options

- **Single-turn only.** Rejected: "and on v2?" or "what about Enterprise?" is the first thing a reviewer will type into a chatbot, and it would fail.
- **History passed to generation, retrieval on the raw follow-up.** Rejected: "what about Enterprise?" embeds to almost nothing, so retrieval returns the wrong Passages while the model answers confidently from history. Grounding becomes unverifiable.
- **Server-side sessions.** Rejected: a store, expiry and restart semantics for a single-user local prototype with no auth. Nothing is gained, because the browser already holds the transcript.

## Consequences

- A Follow-up Question costs one extra LLM call, about 3–5 s on keyless CPU Ollama. The first Turn costs nothing extra.
- A bad rewrite is the new failure mode. The UI shows the Standalone Question ("Searched for: …"), so the CSM can spot it. If the rewrite call fails, the Turn fails rather than silently searching with the raw question.
- Answers can't refer to their own earlier wording beyond what the rewrite carries forward. That's acceptable, because every Answer must stand on its own Citations.
- Because history is client-supplied, a caller can fabricate context. That only affects their own Conversation, and auth is out of scope.
- Chat has one HTTP endpoint, `POST /chat`, and it streams SSE. The non-streaming JSON twin planned alongside this decision was dropped when the HTTP API contract was settled: tests and the evaluation call the answering service in-process, curl reads the stream with `-N`, and the `done` event already carries the whole result as one object.
