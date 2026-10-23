<!-- session: 67dc39f0-4939-491f-9e80-10699d12362b -->

## user · 2026-10-23 13:02:31 · context 4.6% (46.3k / 1000k)

<command-message>wayfinder</command-message>
<command-name>/wayfinder</command-name>
<command-args>continue effort for https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/1?issue=dragomir-parvanov%7Cepam-preescreen-task-rag%7C12</command-args>

## assistant · 2026-10-23 13:02:42 · context 5.4% (54.1k / 1000k)

Unblocked and unclaimed. Claiming it first.

## assistant · 2026-10-23 13:04:19 · context 7.8% (78.5k / 1000k)

Ticket claimed — now putting the first round of chunking & retrieval questions to you, grounded in the corpus spec (#6), citation contract (#7), Haystack choice (#9) and the eval rules (#16).

**Facts I'm building on:**
- The Knowledge Base is small: 5 Articles of about 800–1,500 words each, with 4–8 H2/H3 Sections each. That comes to roughly 30–40 Sections, many only 100–250 words long.
- bge-small-en-v1.5 reads at most 512 tokens per input. Anything beyond that is silently cut off.
- Haystack's `MarkdownHeaderSplitter` gives us `header` and `parent_headers`, can split long Sections a second time, and never cuts inside a code fence. The fastembed document embedder can also embed chosen metadata fields alongside the text (`meta_fields_to_embed`).
- The Articles aren't written yet ([Write the Knowledge Base articles and golden questions](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/17) is still open), so we can't measure real scores today.
- [Choose the vector store](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/11) is still open, and the hybrid-search answer below limits which stores it can pick.

---

❓ **Q1** - **What this ticket fixes now vs. what the eval sets later**: We can't measure scores until the Articles exist. Should this ticket settle the **techniques, starting values and a written rule for setting the final numbers**, and let [Build the golden schema and keyless retrieval eval in CI](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/28) apply that rule to the real report and commit the final k and threshold? The alternative is to block on #17 and pick the numbers by hand afterwards.

➡️ Yes. Decide the strategy, starting values and calibration rule here. #28 applies the rule and records the final numbers, along with the report that justifies them.

---

❓ **Q2** - **Passage boundaries**: Should one Passage be one Section? The proposed rules:
- Split at every H2 and H3, so the deepest heading wins.
- Split a Section a second time only when it is over **~250 words**. That second split falls on paragraph or block boundaries, with **no overlap**. A table, list or code block is never cut.
- Any intro text before the first H2 becomes its own Passage, with the Article title as its Section path.

The alternatives are fixed token windows with overlap, or whole H2 Sections even when they contain H3s.

➡️ Yes. A Passage is one Section, or a paragraph-aligned piece of one when it runs past ~250 words, with no overlap. This lines up Citations with the click-through to the Section, keeps every table-lookup cell whole, and stays well under the 512-token limit. Overlap would only duplicate text across Citations, which is useless when every Passage already sits within one Section.

---

❓ **Q3** - **What gets embedded vs. what gets shown**: Should the text we embed have a header prepended, `"<Article title> > <Section path>"`, while the Passage text stored, shown and cited stays verbatim? This is aimed at the hard cases:
- A Section titled *Rate limits* inside *Nimbus v2 Legacy Reference* then carries "v2 Legacy" in its vector.
- A "30 days" table row carries "Deprovisioning" or "Feature matrix" with it, so the two near-duplicate facts embed differently.

Should queries also get bge's recommended prefix, "Represent this sentence for searching relevant passages: "?

➡️ Yes to both. The header goes in only at embedding time, via `meta_fields_to_embed`, so the verbatim-text promise in ADR-0001 is kept. The query prefix follows the model card's advice for short-query → passage retrieval, and #28 reports scores with it on and off once, so we can show evidence for keeping it.

---

❓ **Q4** - **Metadata on each Passage**: Should each Passage carry exactly these fields?
- Article `id` and `title`
- Section path, as a list
- the Article's `applies_to` and `status`
- its position within the Section
- a deterministic Passage id, `<article-id>#<section-slug>-<n>`

`doc_type`, `owner` and `last_updated` would be left off.

➡️ Yes. These are exactly what a Citation needs (#7), plus a stable id for click-through and for eval matching. Nothing gets indexed on the off chance it's useful.

---

❓ **Q5** - **Dense-only vs. hybrid (BM25 + dense)**: Should retrieval start **dense-only**, with BM25 hybrid and RRF fusion written up as the documented next step, to be built only if `eval-retrieval` misses a lexical case (AUTH-401, `X-Nimbus-Signature-256`, HMAC-SHA1)?

➡️ Yes, dense-only. RRF fusion scores ranks rather than relevance, which breaks the absolute threshold the Refusal gate depends on. You'd have to explain gating on one score while ranking by another. With ~35 Passages, the contextual headers and a gating recall check, there's no evidence yet that hybrid is needed, and the README can name the trigger that would justify adding it. It also leaves [Choose the vector store](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/11) free to pick any store.

---

❓ **Q6** - **Reranking**: Should we skip a cross-encoder reranker, such as fastembed's `bge-reranker-base`?

➡️ Yes, skip it. It would mean a second model baked into the image and more latency on CPU, all to reorder a top-k that already covers the relevant Sections of a 35-Passage index. The citation contract only needs relevant Passages to be *in* the top k, not perfectly ordered. Reranking goes in the README's "at scale" list.

---

❓ **Q7** - **k and version handling**: Should k start at **6**, with the rule "the smallest k at which every answerable Golden Question has all its `expected_sources` in the top k, plus 2 for headroom, capped at 8"? And should there be **no metadata filtering or boosting** by Platform Version? Under that approach, an unversioned question pulls both v3 and v2 Passages, and the prompt applies the v3-default / v2-note rule from #7.

➡️ Yes. *gq-entra-auto-deprovision* needs 3 Sections, and version-conflict questions need the v3 and v2 Passages side by side, so 6 leaves room. The headroom absorbs small changes when Articles are edited, and the cap of 8 keeps `qwen3.5:2b`'s context small. A version filter would hide exactly the v2 Passage that #7 promises to cite as a note.

---

❓ **Q8** - **Threshold: what it applies to and how it's set**: The proposal:
- The gate compares the **top-1 raw cosine score** against a single `min_score`. It does not filter individual Passages: once the gate passes, all k Passages go to the model.
- Calibration rule: `min_score` = (lowest top-1 score among answerable Golden Questions) − **0.05** margin.
- #28 reports how many unanswerable questions this catches, but doesn't assert it.
- The starting value is a placeholder until #28 measures it.

Should we go with that?

➡️ Yes. It follows directly from "a false Refusal is the worse error" (#16). A floor on each Passage would quietly drop the second Article in cross-article answers. bge-small's cosine scores cluster tightly, so the gate will probably catch only the far-off questions (pricing, LDAP), and the model sentinel stays the real backstop. That's an honest trade-off for the README.

---

❓ **Q9** - **Where the numbers live**: Should `top_k` and `min_score` be fields on the backend `Settings`, overridable as `BACKEND_RETRIEVAL_TOP_K` and `BACKEND_RETRIEVAL_MIN_SCORE`, with the calibrated defaults committed in code? The eval would read the same `Settings`, and its report header would record them. The splitter's ~250-word cap would stay a code constant, not a setting.

➡️ Yes. One source of truth that both the server and the eval read, which is what #16 asked for. The chunk size changes the index itself, so it belongs in code and in review, not in `.env`.

## user · 2026-10-23 13:04:51 · context 8.5% (85k / 1000k)

We will incude 150 manuals, with test data, change that everywhere and rephrase the questions

## assistant · 2026-10-23 13:05:16 · context 8.5% (85k / 1000k)

Before editing anything I'll find every place the 5-Article corpus is assumed.

## assistant · 2026-10-23 13:07:16 · context 9.6% (95.5k / 1000k)

I've updated everything that assumed 5 Articles. "Manuals" maps to **Article** in the glossary, so it's 150 Articles throughout.

- **Map:** the corpus gist now says "amended: 150 Articles with test data". The *Production-scale corpus* out-of-scope line is narrowed to *beyond 150 Articles* (incremental re-indexing, ANN tuning, sharding), and the document-formats line now says 150 Articles.
- **[Write the Knowledge Base articles and golden questions](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/17):** retargeted to 150 Articles, with a "don't start yet" note. It's now blocked by this ticket, because how the other 145 Articles get made is settled below.
- **[Knowledge-base corpus](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/6):** added an amendment comment. The 5 planted Articles, their facts and the 14 seed questions still stand.
- **[Build the Compose smoke job in CI](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/30):** `GET /api/articles` now returns every Article instead of "the five".
- **[Choose the vector store](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/11):** another session has claimed it, so I left its body alone and commented the new scale: about 1,000–2,000 Passages instead of 50–150.

**What changes at 150 Articles:** about 165k words, so roughly 1,000–1,500 Passages, with the same headings ("Troubleshooting", "Prerequisites") repeated across dozens of Articles. Two risks are new:
- Embedding-only search has far more near-misses to pick from.
- Any of the 145 new Articles could accidentally answer an "unanswerable" Golden Question (pricing, LDAP) or contradict a planted fact.

The corpus questions (Q1–Q4) come first, because the eval rules for k and the threshold depend on them. Those rules move to the next round.

---

❓ **Q1** - **How the other 145 Articles are produced**: The proposal:
- A committed generator script (`eval/corpus/generate.py`, run by hand with Claude) writes the 145 Articles from a committed **Nimbus fact sheet**: the canonical tiers, limits, versions and feature list.
- The 5 planted Articles stay hand-specified as in #6.
- The generated markdown is **committed**. Ingestion, CI and the evals only ever read the files and never call the generator.

The alternatives: write them by hand, generate them at build time, or pull in an existing public corpus.

➡️ Yes. A generated-then-committed corpus keeps the index deterministic and keyless, the fact sheet stops 150 Articles from contradicting each other, and a reviewer can read both the generator and its output. It's also cheap: about 300k output tokens, a few dollars.

---

❓ **Q2** - **What the 145 Articles cover and how they look**: Should they come from about **8 Article families**? For example: integration connector guides, admin how-tos, troubleshooting references, release notes per Platform Version, Plan-Tier feature guides, security/compliance notes, API endpoint references and FAQs. Each family has a fixed Section skeleton, so headings like "Prerequisites" and "Troubleshooting" deliberately repeat across Articles. They'd keep the #6 shape: front-matter, 800–1,500 words, 4–8 H2/H3 Sections, and mixed prose, steps, tables and code. Roughly 10% would be `applies_to: [v2]` / `deprecated`.

➡️ Yes. Repeated skeletons are what real manual sets look like, and they create the realistic near-duplicate pressure that the chunking choices below have to survive. Keeping the #6 shape means one schema and one splitter.

---

❓ **Q3** - **Protecting the planted hard cases**: Should the generator's prompt carry a **forbidden-topics list** (prices, LDAP, Google Workspace SSO steps, webhook IP ranges) and the **planted facts as must-not-restate rules**? And should a test in `pixi run test` lint every generated Article for those forbidden terms and conflicting values, such as a different SCIM tier, rate limit or signature header?

➡️ Yes. Without this, one generated FAQ that mentions "LDAP" quietly turns a Refusal question into an answerable one, and the eval can no longer be trusted. The lint test makes the guarantee checkable instead of hoped-for.

---

❓ **Q4** - **Test data: how the Golden Questions grow**: The proposal:
- The generator emits **one or two Golden Questions per generated Article**, with `expected_sources`, `must_mention` and `origin: generated`, all in the same YAML.
- The **14 hand-designed seeds** stay as `origin: curated`.
- About **10 more curated unanswerable questions** get added, worded close to real topics (for example "SCIM with OneLogin").
- About 10% of the generated questions are spot-checked by hand before commit.

➡️ Yes. That gives `eval-retrieval` about 250–300 answerable questions, enough for recall@k and the threshold to mean something statistically. The curated seeds remain the hard-case probes, and the extra unanswerable questions make "how often the gate catches them" a real number.

---

❓ **Q5** - **Passage boundaries**: Same rules as before, now across 150 Articles:
- one Passage per Section, splitting at every H2 and H3;
- a Section over **~250 words** is split again on paragraph or block boundaries, with **no overlap**;
- tables, lists and code blocks are never cut;
- intro text before the first H2 becomes its own Passage, with the Article title as its Section path.

Should we go with that?

➡️ Yes. Scale doesn't change the reasoning: each Citation maps to a Section click-through, table cells stay whole, everything stays under bge's 512-token limit, and there's no duplicated overlap text in Citations. At ~1,000–1,500 Passages the index is still small.

---

❓ **Q6** - **What gets embedded vs. what gets shown**: Should the embedded text have `"<Article title> > <Section path>"` prepended, while the stored and cited text stays verbatim? And should queries get bge's prefix, "Represent this sentence for searching relevant passages: "?

➡️ Yes to both, and the header matters more now. With 150 Articles there will be dozens of "Troubleshooting" Sections, and only the Article title tells *SAML SSO > Troubleshooting* apart from *Salesforce connector > Troubleshooting* in vector space. #28 reports scores with the query prefix on and off once, to justify keeping it.

---

❓ **Q7** - **Metadata on each Passage**: Should each Passage carry exactly these fields?
- Article `id` and `title`
- Section path
- `applies_to` and `status`
- its position within the Section
- a deterministic id, `<article-id>#<section-slug>-<n>`

And should `doc_type` be added *as a filterable field* now that release notes form a whole family?

➡️ Yes to the core set, and no to `doc_type` for now. Nothing in the citation contract or the prompt uses it, and adding a field later only costs a re-index, which happens at startup anyway.

---

❓ **Q8** - **Hybrid search**: Should retrieval now be **hybrid**, with BM25 + dense fused by reciprocal rank fusion (RRF), while the Refusal gate looks only at the **dense top-1 cosine score**? The trade-off is two scores with two jobs: "is anything semantically close?" for the gate, and "which Passages are best?" for ranking. This also requires the store chosen in #11 to offer a keyword retriever, or BM25 has to run in memory beside it.

➡️ Yes, hybrid. At 5 Articles I'd have said dense-only. At 1,000+ Passages with repeated skeletons, exact identifiers (AUTH-401, `X-Nimbus-Signature-256`, connector names) are exactly where bge-small blurs and BM25 is sharp. BM25 is cheap, keyless and in-process, and splitting the gate from the ranking is a clear, defensible line. I'll pass the keyword-retriever constraint to #11.

---

❓ **Q9** - **Reranking**: Should we still skip a cross-encoder reranker, with the README naming it as the next step if curated recall@k falls short?

➡️ Yes, skip it. Hybrid already fixes the specific failure we can predict. A reranker means a second model baked into the image and extra seconds per Turn on CPU, on top of Ollama's 13–19 s, and it should come in only when the eval shows a need.

---

❓ **Q10** - **Where the numbers live**: Should `top_k` and `min_score` be `Settings` fields (`BACKEND_RETRIEVAL_TOP_K`, `BACKEND_RETRIEVAL_MIN_SCORE`) with calibrated defaults committed, read by both the server and the eval, while the ~250-word cap stays a code constant?

➡️ Yes. One source of truth, as #16 asked. Passage size changes the index itself, so it belongs in reviewed code.

---

*Next round, once Q4 is answered:* the starting k, the threshold calibration rule, and whether the CI assertions (100% recall, zero false gate Refusals) apply to every answerable Golden Question or only to curated ones, with a lower floor for generated ones. Those rules hang on how the test data is built.

## user · 2026-10-23 13:08:33 · context 10.1% (101.4k / 1000k)

reccomended for all

## assistant · 2026-10-23 13:08:55 · context 10.1% (101.4k / 1000k)

Everything in round 1 accepted. Before round 2 I'm checking two facts it depends on: whether Haystack 3.x ships RRF fusion, and where the vector-store session has got to.

## assistant · 2026-10-23 13:09:25 · context 10.5% (104.8k / 1000k)

Both facts check out:
- Haystack 3.4.1's `DocumentJoiner` has a `reciprocal_rank_fusion` mode with a fixed constant of 61 and equal weights by default. It can be called as a standalone component, so ADR-0003's "indexing is the only `Pipeline`" still holds.
- RRF **overwrites each Document's `score`** with the fused score, so the dense cosine the gate needs has to be carried separately (Q2).
- [Choose the vector store](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/11) is still open in another session. I'll hand it the keyword-retriever constraint when this ticket resolves.

---

❓ **Q1** - **How the fusion works**: The proposal:
- BM25 and dense each pull their **top 20** candidates.
- Haystack's `DocumentJoiner` in RRF mode (constant 61, equal weights) fuses them, called as a standalone component inside the adapter.
- The fused list is cut to `top_k`.
- `eval-retrieval` also runs a **dense-only ablation** and reports both recall figures side by side.

➡️ Yes. A pool of 20 per retriever is wide enough that a Passage ranked well by only one retriever still survives fusion. Equal weights mean no extra tuning knob to defend. The ablation turns "why hybrid?" from an argument into a number in the README.

---

❓ **Q2** - **Which score a Passage carries**: Should every returned Passage carry its **dense cosine score**? For BM25-only hits, the adapter would compute it from the stored embedding. That cosine is what the gate compares against `min_score` and what the API exposes as the retrieval score from #7. The fused RRF score would be used only for ordering and never exposed.

➡️ Yes. An RRF score is only meaningful within a single query (≈0.016 always means "rank 1"), so exposing it would mislead anyone reading scores in debug output or eval reports. One meaningful score, shared by the gate, the API and the eval.

---

❓ **Q3** - **What CI asserts**: The proposed `eval-retrieval` bars:
- **curated** answerable questions: **100%** recall@k, all `expected_sources` in the top k;
- **generated** answerable questions: **≥ 95%** recall@k across the whole set;
- **zero** false gate Refusals on any answerable question, curated or generated;
- unanswerable questions: the gate catch rate is reported, not asserted.

Generated questions are single-turn only; follow-ups stay curated.

➡️ Yes. Curated questions are the planted hard cases, so any miss there is a real regression. Generated questions are machine-written, and a few will be ambiguous, so a 100% bar would make CI flaky for reasons that aren't retrieval. False Refusals stay at zero everywhere, because #16 calls them the worse error.

---

❓ **Q4** - **k**: Should k **start at 6**, with the rule "the smallest k that meets the Q3 bars, plus 2 for headroom, capped at **8**"? Failing the bars even at k = 8 would be the documented trigger for adding the reranker that round 1 deferred.

➡️ Yes. 6 already covers the 3-Section cross-article case plus a v2 note. The cap of 8 keeps the prompt about 2.5k tokens of Passages, which matters on CPU Ollama because reading the prompt dominates latency. Tying the cap to the reranker trigger gives a clean "what next" story.

---

❓ **Q5** - **How the threshold is set**: The proposal:
- `min_score` = (lowest dense top-1 cosine among **all** answerable questions) − **0.05**.
- The report lists the **5 lowest-scoring** answerable questions.
- If a generated question sets that minimum and the spot check shows it's badly worded, the question is fixed or dropped rather than the threshold lowered.
- #28 applies this rule to the real corpus and commits the resulting `min_score` and `top_k` as the `Settings` defaults.

➡️ Yes. This keeps zero false Refusals true by construction while preventing one bad generated question from quietly gutting the gate. With bge-small's tight score range, expect the gate to catch only far-off questions; the model sentinel remains the main Refusal path, and the README says so.

## user · 2026-10-23 13:09:41 · context 10.7% (107.2k / 1000k)

accept all

## assistant · 2026-10-23 13:10:08 · context 10.7% (107.2k / 1000k)

All decisions are in, so I'm recording them now: a resolution comment on this ticket, the map, and the downstream tickets ([Haystack retrieval adapter](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/21), [retrieval eval](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/28), [Knowledge Base articles](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/17) and [vector store](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/11)).

## assistant · 2026-10-23 13:10:54 · context 11.6% (116.3k / 1000k)

One accepted answer collides with a fact that landed while we were talking. **[Choose the vector store](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/11) chose pgvector**, and its only keyword option doesn't behave like BM25. I checked `pgvector-haystack`'s source:

```sql
SELECT …, ts_rank_cd(to_tsvector('english', content), query) AS score
FROM passages, plainto_tsquery('english', %s) query
WHERE to_tsvector('english', content) @@ query
```

- `plainto_tsquery` **ANDs every word of the question**. For "What does error AUTH-401 mean and how is it fixed?", a Passage has to contain *error* **and** *mean* **and** *fix* **and** *auth-401* to come back at all. Most natural-language questions would get no keyword hits, and "hybrid" would silently turn back into dense-only.
- `ts_rank_cd` has **no IDF**: a rare *auth-401* counts the same as a common *error*. IDF is exactly what made BM25 worth adding for identifiers.
- It searches `content` only, so the Article title / Section path header we embed never reaches it.

---

❓ **Q1** - **Where the keyword half of hybrid runs**: The options:
- **(a)** Real BM25 in memory: a Haystack `InMemoryDocumentStore` + `InMemoryBM25Retriever` filled **from the pgvector table at startup**. Each entry holds the Passage id and the same "title > Section path + text" string we embed, so pgvector stays the single source of truth and the BM25 index is a throwaway mirror that takes milliseconds to build at ~1,500 Passages.
- **(b)** Our own SQL in the adapter: an OR-query over the GIN index pgvector-haystack already creates. It's one store, but the ranking still has no IDF.
- **(c)** Drop hybrid and go dense-only.

➡️ (a). It gives real BM25 with IDF, which is the reason hybrid was chosen, plus OR semantics, and the header text. The grill answer is short and verifiable: "Postgres full-text ANDs the terms and has no IDF, so it can't find AUTH-401 inside a question. BM25 can." The cost is a second, derived index rebuilt on every boot, and the dense-only ablation in the eval report shows whether it pays for itself.

## user · 2026-10-23 13:11:31 · context 11.9% (118.5k / 1000k)

reccomended

## assistant · 2026-10-23 13:11:44 · context 11.9% (118.5k / 1000k)

Recording everything now.

## assistant · 2026-10-23 13:11:47 · context 12.2% (121.9k / 1000k)

Writing ADR-0005 and the glossary update.

## assistant · 2026-10-23 13:13:36 · context 13.7% (136.8k / 1000k)

The downstream tickets are updated and the new corpus-generation ticket is wired in. Next: closing this ticket and updating the map.

## assistant · 2026-10-23 13:14:17 · context 14% (140.5k / 1000k)

[Chunking & retrieval strategy](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/12) is decided and closed, and the map has a new Decisions-so-far entry for it.

**What was decided**
- **Knowledge Base:** 150 Articles. Five are hand-planted with the hard cases; the other 145 come from a generator you run by hand with Claude, working from a Nimbus fact sheet, and the output is committed. A lint test fails if a generated Article mentions a forbidden topic (pricing, LDAP and so on) or contradicts a planted fact, so questions meant to get a Refusal stay unanswerable.
- **Test data:** the generator writes 1–2 Golden Questions per generated Article. The curated ones are your 14 seeds plus about 10 new unanswerable questions.
- **Passages:** one per Section, split again only past about 250 words, with no overlap. The embedded text gets an "Article title > Section path" header, but citations quote the original text.
- **Retrieval:** hybrid search, combining pgvector embeddings with keyword (BM25) search held in memory and rebuilt from pgvector at startup. Every Passage carries its embedding-similarity score, and only that score decides whether to refuse. No reranker and no Platform Version filtering.
- **Numbers:** k starts at 6, capped at 8. The refusal threshold is the lowest top score among answerable questions, minus 0.05. Both are calibrated by the retrieval eval and stored in `Settings`.

**One change from what you approved:** you accepted BM25, but the store that got picked concurrently is pgvector, and its built-in keyword search (`PgvectorKeywordRetriever`) only returns Passages containing every word of the question. It also has no IDF weighting, so a rare term like `AUTH-401` counts no more than a common one. You chose an in-memory BM25 copy instead. That's recorded as a new decision record, `docs/adr/0005-hybrid-retrieval-with-an-in-memory-bm25-mirror.md`.

**Tracker changes**
- **New ticket:** [Generate the remaining 145 Articles and their Golden Questions](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/34). It's blocked by [Write the Knowledge Base articles and golden questions](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/17), and it blocks [Build the golden schema and keyless retrieval eval in CI](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/28).
- **Rewritten:**
  - #17 is now the 5 planted Articles, the fact sheet and the curated questions.
  - [Build the Haystack retrieval adapter and indexing pipeline](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/21) has the chunking and hybrid retrieval spec. Passage ids are now `<article-id>#<section-slug>-<n>`, and the content hash moves into the Passage's stored metadata so links survive edits.
  - #28 has the CI pass/fail thresholds, the calibration rules and the comparison reports. Its stale branch-and-PR workflow line now follows the map's work-on-`main` rule.
- **Corpus-size updates:** the map's scope lines, an amendment comment on [Knowledge-base corpus](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/6), and [Build the Compose smoke job in CI](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/30).
- **Notes added to:**
  - [Choose the vector store](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/11): the new corpus size.
  - [Operational readiness](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/15): readiness should also wait for the BM25 copy to be built.

**Needs your call:** [Build the full LLM evaluation and baseline reports](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/29). At about 300 questions, a full run on CPU Ollama takes over an hour. I proposed in a comment there that it run only the curated questions by default, with an `--all` flag for the full set. I haven't decided it; confirm or change it when that work comes up for review.

**Worth knowing:** the original brief asked for 3–5 mock Articles. The README should say why we went to 150.

**Not committed:** ADR-0005 and the Golden Question curated/generated definition in `GLOSSARY.md` are in your working tree, waiting for you to commit.

## user · 2026-10-23 13:15:20 · context 14.2% (142.3k / 1000k)

commit everything that we have now

## assistant · 2026-10-23 13:15:27 · context 14.4% (144.2k / 1000k)

Splitting this into two commits, matching earlier history: the decision docs, then the session logs. First, a quick scan of the new logs for anything that looks like a key.

## assistant · 2026-10-23 13:15:35 · context 14.5% (145k / 1000k)

I've committed everything to `main` in two commits; nothing is pushed yet.

- **`1e36ce4` docs: record ADRs 0004-0005, testing rules and Golden Question origins**: `AGENTS.md`, `GLOSSARY.md`, `docs/adr/0004-pgvector-as-the-passage-store.md` (from the vector-store session) and `docs/adr/0005-hybrid-retrieval-with-an-in-memory-bm25-mirror.md`.
- **`655edbc` docs: add wayfinder session conversations**: all new and changed files under `chats/`. A scan of the committed files for API keys found nothing.

The working tree is now clean. I can push whenever you want.

The Stop hook will log this session as another file in `chats/`, which will show up uncommitted afterwards.

