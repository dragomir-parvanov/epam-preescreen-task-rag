<!-- session: 6cb0310a-6a34-4455-b1f6-ec64ee483b81 -->

## user · 2026-10-23 11:52:30 · context 4.2% (41.7k / 1000k)

continue /wayfinder effort for https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/8

## assistant · 2026-10-23 11:52:43 · context 4.9% (48.6k / 1000k)

Unclaimed and unblocked. Claiming it first, then loading the map.

## assistant · 2026-10-23 11:53:40 · context 6.9% (69.5k / 1000k)

I've claimed the ticket and read the map, the related tickets and both research branches. Now the first grilling round.

**Context that shapes these questions:**
- With keyless Ollama on a CPU, one answer took 13–19 s in the provider benchmark, and 8–15 s of that was spent reading the prompt before the first token. Every extra LLM call or extra history token costs real seconds. Streaming only hides the 3–5 s of generation, not the reading.
- In Haystack, `AnswerBuilder` parses the `[n]` markers only **after** the stream finishes. Retrieved sources can go out first only if retrieval runs as its own step.
- None of the 14 golden questions is a follow-up. All of them are standalone.
- The nginx `/api/` proxy has default buffering on, which would hold back a stream.

---

❓ **Q1** - **Single-turn or multi-turn, and do we rewrite follow-ups?**

There are three options:
- **(a) Single-turn Q&A shown as a thread.** Each question is answered on its own. It's the simplest and honest, but "what about Enterprise?" or "and on v2?" fails or gets refused. A reviewer is likely to try exactly that on something called a chatbot.
- **(b) Multi-turn, history passed to generation only.** Retrieval runs on the raw follow-up. "What about Enterprise?" then embeds to almost nothing and retrieves the wrong chunks, while the LLM sounds confident. This is the classic RAG bug, so it's indefensible.
- **(c) Multi-turn with query rewriting.** When there is earlier history, an extra LLM call turns the follow-up into a standalone question ("What is the API rate limit for an Enterprise client?"). Retrieval runs on that rewritten question. Generation sees the rewritten question plus the retrieved chunks, but not the raw history, so grounding stays strictly on the Articles. The first turn skips the rewrite and costs nothing extra. A follow-up adds a small call (no chunks in it, about 300 tokens), roughly 3–5 s on CPU Ollama. The UI shows the rewritten question ("Searched for: …") so the CSM can see what was actually asked.

➡️ **(c)**. Multi-turn with a visible standalone rewrite. History goes only to the rewrite step and is capped at the last N turns (e.g. 3 exchanges), with answers trimmed. Generation gets no history, which keeps citations tied to the chunks retrieved for this turn.

---

❓ **Q2** - **Streaming: SSE with typed events, sources first?**

There are three options:
- **Single JSON response.** It's simple, but the CSM stares at a spinner for 13–19 s on Ollama.
- **Raw chunked text.** It has nowhere to put citations, refusals or errors.
- **SSE over `POST`**, read with `fetch` + `ReadableStream`, because `EventSource` only supports GET. It carries typed events in this order:
  1. `rewritten`: the standalone question, only when Q1 is (c) and this is a follow-up.
  2. `sources`: the numbered retrieved chunks, sent before any token.
  3. `token`: text deltas.
  4. `done`: the authoritative final answer, holding only the citations actually referenced (`AnswerBuilder`'s `referenced` flag) and the refusal flag.
  5. `error`: a typed error in the middle of the stream.

  This works with whatever the *Citation & grounding contract* decides, because the UI renders the streamed text provisionally and swaps in `done`. A refusal decided by the retrieval threshold sends `done` without ever calling the LLM. A mid-stream failure arrives as an `error` event, because by then the HTTP status has already gone out as 200. nginx needs `proxy_buffering off` on that route.

➡️ **SSE with typed events, sources first and the `done` payload authoritative.** The same service also gets a non-streaming JSON entry point that returns exactly the `done` payload. That entry point is for curl, the golden-question eval and simpler tests. The endpoint shapes themselves are left to *HTTP API contract*.

---

Persistence and where history lives depend on Q1, so they come in the next round.

## user · 2026-10-23 11:57:36 · context 7.2% (72.4k / 1000k)

reccomended

## assistant · 2026-10-23 11:57:57 · context 7.2% (72.4k / 1000k)

❓ **Q3** - **Where history lives: client-sent, with a stateless server?**

There are two options:
- **Client-sent.** Each request carries the earlier turns, and the server keeps nothing between requests. There's no `conversation_id`, no session store and no expiry policy, and it survives a restart by construction. Since there's no auth (out of scope), trusting client-supplied history is fine. The worst a caller can do is fake their own context. The server still enforces the cap from Q1, keeping the last 3 exchanges and truncating each answer.
- **Server session.** The server stores conversations keyed by an id. That means a store, cleanup and restart semantics, all for a single-user local prototype. It's harder to defend than it's worth.

➡️ **Client-sent and stateless.** Each request is `{question, history: [{question, answer}]}`, where `question` is what the CSM typed and `answer` is the plain final text with no citation payloads. The server applies the cap itself instead of trusting the client to.

---

❓ **Q4** - **No persistence: does a refresh or "New conversation" start fresh?**

Possible extras are a `localStorage` transcript or server-side history. Neither is required by the brief, and both add states to test (stale citations after re-ingestion, for example).

➡️ **No persistence anywhere.** A backend restart is invisible to the user. A page refresh or the **New conversation** button starts an empty Conversation. Saved history goes in the README as future work.

---

❓ **Q5** - **What feeds the rewrite step, and what happens to refusals?**

➡️ The rewrite gets the last 3 Turns, each as question plus answer truncated to about 500 characters, then the new question. Its instruction: "rewrite as a self-contained question; if it already is one, or it changes topic, return it unchanged; don't answer it."
- Refusals stay in history, so "ok, what about LDAP then?" still makes sense.
- Version context carries through. If the earlier Turn was about v2, "and the signature header?" becomes a v2 question.
- If the rewrite call fails, the Turn fails with an `error` event. It doesn't quietly fall back to the raw question, which would hide the bug and retrieve the wrong context.

---

❓ **Q6** - **Stop and cancellation?**

On CPU Ollama an unwanted answer ties up the model for 15 s.

➡️ The UI gets a **Stop** button that aborts the `fetch`. The backend notices the disconnect and cancels the in-flight LLM call. The stopped answer stays visible, marked *Stopped*, but is **left out** of the history sent with later Turns. Only completed answers feed the rewrite.

---

❓ **Q7** - **Domain terms for `GLOSSARY.md`?**

Answer, Citation and Refusal belong to *Citation & grounding contract*. This ticket owns the conversation terms.

➡️
- **Conversation**: the ordered Turns one CSM has in a single browser session. It isn't saved.
- **Turn**: one Question from the CSM plus the assistant's response to it. _Avoid_: exchange, message pair.
- **Follow-up Question**: a Question that only makes sense given earlier Turns.
- **Standalone Question**: the self-contained rewrite of a Follow-up Question that retrieval actually searches with. _Avoid_: condensed query, rephrased query.

## user · 2026-10-23 11:58:43 · context 7.4% (74.4k / 1000k)

reccomended

## assistant · 2026-10-23 11:58:53 · context 7.4% (74.4k / 1000k)

Frontier is empty, so I'm recording the agreed terms in the glossary now.

## assistant · 2026-10-23 11:59:11 · context 7.6% (76.2k / 1000k)

I've added the Conversation, Turn, Follow-up Question and Standalone Question terms to `GLOSSARY.md`. Before I close the ticket, here's what we agreed, so you can confirm it's right:

**Conversation model: what we agreed**
1. **Multi-turn, with the follow-up rewritten first.**
   - On a Follow-up Question, one small LLM call rewrites it into a Standalone Question, and retrieval searches with that.
   - Generation sees only the Standalone Question and this Turn's chunks, never the earlier history, so citations stay tied to what was retrieved for this Turn.
   - The first Turn skips the rewrite.
   - The UI shows "Searched for: …".
2. **Streaming over SSE (Server-Sent Events) via `POST`.**
   - Events arrive in this order: `rewritten`, then `sources`, then `token`, then `done`.
   - `done` carries the final answer, and its contents override anything shown during the stream.
   - A failure partway through arrives as an `error` event.
   - A Refusal triggered by the retrieval threshold sends `done` without calling the LLM at all.
   - nginx needs `proxy_buffering off` on this route.
   - There's also a non-streaming JSON endpoint that returns the `done` payload, for curl, the evaluation runs and tests.
3. **The client sends the history; the server stores nothing between requests.**
   - A request looks like `{question, history: [{question, answer}]}`.
   - The server keeps only the last 3 Turns itself and truncates each answer to about 500 characters.
   - There's no session store and no conversation id.
4. **Nothing is saved.** A page refresh or **New conversation** starts empty, and a backend restart is invisible to the user. Saved history goes in the README as future work.
5. **What the rewrite sees:**
   - Refusals stay in the history.
   - The Platform Version (v2 or v3) carries over to the follow-up.
   - If the rewrite call fails, the Turn fails. It never quietly falls back to the raw question.
6. **Stop button:**
   - Stopping cancels the LLM call on the backend.
   - The partial answer stays on screen, marked *Stopped*.
   - Stopped answers are not sent as history in later Turns.

When I close it, I'll also:
- post this as the resolution comment and add a line to the map's Decisions so far;
- update *Test & evaluation strategy* so it covers follow-up cases. All 14 golden questions are single questions, so nothing tests the rewrite yet;
- create no build ticket now. This feeds *HTTP API contract* and *Chat UI with citations*, which this ticket was blocking.

One more choice: **should I record an ADR (architecture decision record) for "the client sends the history, and only the rewrite step sees it"?** I think it's worth one. Keeping history away from generation is the choice reviewers will question most, and it's hard to undo once the API and UI depend on it. Confirm the summary and say yes or no to the ADR, and I'll close it out.

## user · 2026-10-23 12:06:37 · context 7.7% (77.3k / 1000k)

yes

## assistant · 2026-10-23 12:07:06 · context 8.2% (82k / 1000k)

Now the resolution comment, closing, the map pointer, and the follow-up input for the evaluation ticket.

## assistant · 2026-10-23 12:07:37 · context 8.6% (85.9k / 1000k)

The citation session also landed and created *Prompt design*. The Follow-up rewrite prompt is a prompt too, so I'm adding it there as an input.

## assistant · 2026-10-23 12:07:59 · context 8.7% (87.2k / 1000k)

I've closed [Conversation model: single vs multi-turn, streaming](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/8), with the full decision in its [resolution comment](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/8#issuecomment-6361446687) and a pointer added to the map's Decisions so far.

**What was decided:**
- **Conversations are multi-turn.** A follow-up question is first rewritten into a self-contained question, and retrieval searches with that. Only the rewrite step sees earlier turns; answer generation sees just this turn's retrieved passages.
- **The browser sends the history with each request.** The server stores nothing and keeps the last 3 turns itself. Nothing is saved: a refresh or **New conversation** starts empty.
- **Answers stream over SSE (Server-Sent Events) via `POST`.** Events arrive in the order `rewritten` → `passages` → `token` → `done` / `error`, and `done` holds the final answer. A non-streaming JSON endpoint returns the same `done` payload, for curl and the golden-question evaluation runs.
- **Stop cancels the LLM call.** A stopped answer stays on screen marked *Stopped* and isn't sent as history later.

**Files changed (not committed):**
- `GLOSSARY.md` now defines Conversation, Turn, Follow-up Question and Standalone Question.
- `docs/adr/0002-history-feeds-only-the-follow-up-rewrite.md` is new.

**Tracker updates:**
- *Test & evaluation strategy* now notes that nothing tests the follow-up rewrite yet, since all 14 golden questions are single questions.
- *Prompt design* now includes the follow-up rewrite prompt as a second prompt to design.
- I created no build ticket. The work arrives through the build tickets that *HTTP API contract* and *Chat UI with citations* will create.

**Overlap with the citation session:** the parallel *Citation & grounding contract* session finished while I worked. Its glossary says to avoid "Source", so I named the streaming event `passages` rather than `sources`.

**Next on the map:** *Choose the RAG framework*, *HTTP API contract* and *Chat UI with citations* are open and unclaimed, so they can be picked up next. *Build answer assembly: citations, Uncited Answers and Refusals* is also open and unclaimed.

