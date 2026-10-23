<!-- session: 7819f07f-f194-4637-a5f6-85e84f8e5c37 -->

## user · 2026-10-23 11:51:57 · context 4.2% (41.7k / 1000k)

continue /wayfinder effort for https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/7

## assistant · 2026-10-23 11:52:37 · context 5.5% (55.1k / 1000k)

I've claimed **Citation & grounding contract**. Next I'll load the grilling and domain-modeling skills and read the earlier decisions it depends on.

## assistant · 2026-10-23 11:53:45 · context 6.5% (64.7k / 1000k)

I've read the map, the corpus decision (its planted hard cases and golden questions) and both research findings. Nothing blocks **Citation & grounding contract**. Its answer unblocks **Choose the RAG framework**, **HTTP API contract** and **Chat UI with citations**. It also sets up the prompt-design area that's still in the map's fog.

Two earlier findings shape this round:
- **Small local models cite poorly.** `llama3.2:3b` emitted no `[docN]` markers, and in JSON mode both small models listed *every* chunk as a source. These results are from the **LLM & embedding provider options** research.
- **Haystack's `AnswerBuilder` maps `[n]` markers back to retrieved documents** and flags each one as `referenced`. This is from the **Python RAG framework options** research.

None of these questions depend on each other, so this is the whole round.

---

❓ **Q1 - What a Citation points at**: Options:
- (a) Article only.
- (b) Article + Section heading path.
- (c) Article + Section + the **verbatim passage** the model was shown, plus the Article's `applies_to` / `status` metadata.

With (c), a CSM can verify a claim without leaving the chat: they read the quoted passage and the heading path (`nimbus-sso-saml › Troubleshooting`), then click through to the full Section. The verbatim text is exactly what the model saw, so a mismatch between claim and quote is visible straight away. Retrieval score: include it in the API so evals and debugging can use it, but don't show it in the UI, because cosine scores mean nothing to a CSM. If a long Section is split into two passages and both are cited, they stay **two Citations**, so each quote stays exact.

➡️ (c): Article + Section path + verbatim passage + version/status metadata. The score is in the API but hidden in the UI, and there is one Citation per cited passage.

---

❓ **Q2 - How Citations attach to the Answer**: Options:
- (a) Inline numbered markers `[1]` in the answer text, tied to an ordered Citation list.
- (b) Per-sentence attribution (each sentence carries its own source spans).
- (c) A sources list under the answer, with no inline markers.

(b) is beyond what a 3B model can do reliably, and (c) can't show *which* claim came from where. With (a), the model cites by the numbers it saw in the prompt (`[3]`, `[7]`). The server then **renumbers** the cited passages as `[1]..[k]` in order of first appearance, so the UI never shows gaps like "[3][7]".

➡️ (a): inline markers, renumbered server-side in order of first appearance.

---

❓ **Q3 - "Displayed Citations were actually used": what counts and what happens when the model doesn't cite**: Options:
- (a) **Citations = passages the model marked.** Markers pointing at passages that don't exist are removed. Retrieved but uncited passages never appear as Citations.
- (b) Show every retrieved passage as a Citation. This is honest about what the model saw, but it breaks "cited = used". It is also exactly the "lists every chunk" failure the small models had.
- (c) A verification step: an LLM judge or lexical overlap check per claim. This costs more latency and money, and the judge has its own failure modes.

The hard part is a non-refusal answer with **no valid markers**. That will be common with `llama3.2:3b`. Options:
- (i) Turn it into a Refusal. This is strict, but most keyless answers would become refusals, so the demo dies.
- (ii) Return the answer marked as **uncited**, with a visible warning, and show the retrieved passages separately as "retrieved, not cited". They are never shown as Citations.
- (iii) Silently fall back to showing the retrieved passages as Citations. This is dishonest.

"Used" can only mean "the model claimed to use it". We don't verify it per request. Instead, the evaluation measures citation precision and recall against `expected_sources` in the golden questions (the scoring itself belongs to **Test & evaluation strategy**).

➡️ (a) + (ii): only marked passages become Citations, and an answer with no valid markers is returned flagged as uncited with its retrieved passages kept apart. The system never fakes a Citation, and the weak-model behaviour is visible rather than hidden.

---

❓ **Q4 - Refusal: when and how**: Options:
- (a) A **retrieval threshold** gate: if no passage scores above a cut-off, refuse without calling the LLM. This is deterministic, cheap and unit-testable, but the threshold is tuned and brittle around near-misses.
- (b) **Model-judged**: the prompt tells the model to emit a fixed sentinel (e.g. `NOT_IN_KNOWLEDGE_BASE`) when the context doesn't answer the question.
- (c) Both: (a) catches clear misses like "LDAP" and "pricing" early, and (b) catches cases where retrieval found something on-topic that still doesn't answer (e.g. the Enterprise row exists, but has no price).

Either way, the **Refusal message is fixed server text** ("The Knowledge Base doesn't cover this…"), not the model's free text, and a Refusal carries **no Citations**. The actual threshold value is left to **Chunking & retrieval strategy**.

➡️ (c): a threshold gate plus a model sentinel, a fixed Refusal message, and no Citations on a Refusal.

---

❓ **Q5 - Partially answerable questions** (Google Workspace SSO; webhook retries + IP ranges): Options:
- (a) Refuse the whole question.
- (b) Answer the covered part with Citations, and **state explicitly** which part the Knowledge Base doesn't cover (it doesn't say "no", and it doesn't guess).
- (c) (b), plus a structured `uncovered` field the model has to fill in.

(c) can't be extracted reliably from small models. Under (b), the answer is still an ordinary Answer, not a Refusal. The prompt requires the explicit "not covered" sentence, and the golden questions check for it.

➡️ (b): answer the covered part with Citations and name the gap in prose. There is no separate partial status.

---

❓ **Q6 - Version conflicts when the question doesn't name a Platform Version** (e.g. "What's the rate limit for a Business client?"): Options:
- (a) Answer for **v3 (current)**. If a cited v2 passage disagrees, add one note: "On v2 (deprecated, end of support 2027-03-31) it is 300 req/min [2]".
- (b) Always give both versions side by side.
- (c) Ask a clarifying question. This needs multi-turn, which is still open in **Conversation model: single vs multi-turn, streaming**.

If the question *does* name v2, answer for v2 and mention that v2 is deprecated. Each Citation carries its Article's `applies_to` and `status`, so the UI can badge a v2 or deprecated Citation.

➡️ (a): default to v3, add a cited v2 note only when the passages conflict, follow an explicitly named version, and badge version/status on each Citation.

---

❓ **Q7 - Domain terms for `GLOSSARY.md`**: Proposed:
- **Answer**: the assistant's grounded reply to a CSM's question, with its Citations.
- **Citation**: a numbered reference in an Answer to the Passage it drew on. Avoid: Source, reference, footnote.
- **Passage**: a verbatim excerpt of one Section, the unit the assistant retrieves and cites. Avoid: Chunk (outside technical discussion, like Corpus), snippet.
- **Refusal**: a reply saying the Knowledge Base doesn't cover the question. It carries no Citations. Avoid: "no answer", fallback.
- **Uncited Answer**: depends on Q3; this is what Q3 (ii) would add.

The point is that **Source** is *not* a separate concept: it is ambiguous between Article, Section and Passage, so it goes under Avoid. Passage replaces "Chunk" in domain language, because a CSM sees quoted passages, not chunks. "Chunk" stays fine in code and in technical discussion of **Chunking & retrieval strategy**.

➡️ Yes to these terms: Source goes under Avoid, and Passage is the domain word for a chunk.

## user · 2026-10-23 11:57:30 · context 7% (69.8k / 1000k)

reccomended

## assistant · 2026-10-23 11:57:58 · context 7.2% (72k / 1000k)

All seven accepted. `GLOSSARY.md` now defines **Passage**, **Answer**, **Citation**, **Uncited Answer** and **Refusal**. The file is still untracked; I haven't committed anything.

Your answers left three small branches open:

---

❓ **Q8 - Should a Refusal say why it refused?** A Refusal can come from either of two checks in Q4: the retrieval threshold or the model's sentinel. The CSM should see the same fixed message either way. Should the API also return a machine-readable reason, `no_relevant_passages` or `not_in_context`? Both the logs and the evaluation can then tell "retrieval missed" apart from "retrieval found something but the model judged it insufficient". That distinction is exactly what tuning the threshold needs.

➡️ Yes: same message in the UI, and a reason field in the API for logs and the evaluation.

---

❓ **Q9 - Retrieved but uncited Passages: when are they returned?** Options:
- (a) Only on an Uncited Answer, as the "retrieved, not cited" list from Q3.
- (b) Always, in a separate `retrieved` field next to `citations`. The UI shows them only for an Uncited Answer, and maybe in a collapsed debug drawer (that's for the **Chat UI with citations** prototype).

(b) lets the evaluation compare what was retrieved with what was cited on every question. That comparison separates a retrieval failure from a citation failure. Exact field names stay with **HTTP API contract**.

➡️ (b): always return them, kept strictly apart from `citations`.

---

❓ **Q10 - Should this be an ADR?** The decision "Citations are only the Passages the model marked; an answer without valid markers is flagged Uncited, never padded with retrieved Passages and never forced into a Refusal" meets all three ADR tests:
- **Hard to reverse:** it shapes the API schema, the UI and the evaluation metrics.
- **Surprising:** a reviewer will ask why we don't just show the retrieved chunks.
- **Real trade-off:** the alternatives were show everything retrieved, refuse, or add a judge.

I'd write `docs/adr/0001-citations-are-model-marked-passages.md`. It would record the small-model benchmark as the reason and the rejected options with why each lost.

➡️ Yes: write that one ADR. The other decisions (v3 default, partial answers in prose, the fixed Refusal text) are easy to reverse, so they stay in the resolution comment only.

---

If you accept these, the design tree is fully covered. I'll then post the resolution on **Citation & grounding contract**, close it and add it to the map's Decisions so far. I'll also move the decisions that affect the prompt into the map's "Prompt design" note and check whether that area is now clear enough to become its own ticket.

## user · 2026-10-23 11:59:49 · context 7.3% (73k / 1000k)

yes

## assistant · 2026-10-23 12:00:13 · context 7.7% (76.6k / 1000k)

Posting the resolution comment, then closing the ticket.

## assistant · 2026-10-23 12:00:41 · context 7.9% (78.8k / 1000k)

Ticket closed. Next I'll create the new tickets: **Prompt design** (graduating from the map's fog) and a build ticket for answer assembly.

## assistant · 2026-10-23 12:01:00 · context 8.1% (80.8k / 1000k)

Both tickets are created. Now I'll attach them to the map and add the blocking links.

## assistant · 2026-10-23 12:01:15 · context 8.2% (81.5k / 1000k)

Now updating the map: add the decision pointer and remove "Prompt design" from the fog, since it's now a ticket. I'm re-fetching the map first because other sessions may have edited it.

## assistant · 2026-10-23 12:01:26 · context 8.4% (83.8k / 1000k)

Finally, checking what's takeable now.

## assistant · 2026-10-23 12:01:44 · context 8.5% (84.7k / 1000k)

I've resolved **Citation & grounding contract**, closed it and added it to the map's Decisions so far.

**What we decided**
- **What a Citation is:** one Passage, meaning the Article, the Section heading path, the exact text the model was shown, and the Article's version and status.
- **How Citations appear:** inline `[n]` markers that the server renumbers `[1]..[k]` in order of first use.
- **Only what the model marked counts as a Citation.** An answer with no valid markers is shown as an **Uncited Answer** with a warning. It is never padded with retrieved Passages and never turned into a Refusal. Retrieved Passages are always returned in a separate field.
- **Refusals:** either a retrieval-score cut-off or a fixed marker string the model is told to emit. The CSM sees a fixed message with no Citations, and the API also returns the reason (`no_relevant_passages` / `not_in_context`).
- **Partly answerable questions:** answer the covered part and say in plain text what the Knowledge Base doesn't cover.
- **Questions that don't name a version:** answer for v3, adding a cited v2 note only when the v2 Article disagrees.

**Files (not committed, as you prefer)**
- `GLOSSARY.md` gained Passage, Answer, Citation, Uncited Answer and Refusal. It is still untracked, as it was at the start of the session.
- `docs/adr/0001-citations-are-model-marked-passages.md` is new. The resolution comment links to it on `main`, so that link stays broken until it's merged.

**Map changes**
- [Prompt design](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/19) moved from "Not yet specified" into its own grilling ticket. It is blocked by **Conversation model: single vs multi-turn, streaming** and **Choose the RAG framework**.
- [Build answer assembly: citations, Uncited Answers and Refusals](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/20) is a new build ticket that doesn't depend on the framework choice. It is takeable now: its only blocker, the walking skeleton, is already closed.
- **HTTP API contract**, **Chat UI with citations** and **Test & evaluation strategy** each lost one blocker but are still waiting on one more.

**Takeable now:** **Choose the RAG framework**, **Write the Knowledge Base articles and golden questions**, and the new answer-assembly build ticket. **Conversation model: single vs multi-turn, streaming** is also unblocked, but it's assigned to you, so another session may be working on it.

