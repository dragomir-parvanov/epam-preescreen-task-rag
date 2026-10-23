# Hybrid retrieval with an in-memory BM25 mirror; the gate reads the dense score

With 150 Articles (~1,000–1,500 Passages) sharing repeated Section skeletons, exact identifiers like `AUTH-401` or `X-Nimbus-Signature-256` are where `bge-small-en-v1.5` blurs, so retrieval is **hybrid**: BM25 and dense each take their top 20 candidates, and Haystack's `DocumentJoiner` fuses them with reciprocal rank fusion (RRF) before the list is cut to `top_k`. The BM25 half does **not** use Postgres full-text search, even though pgvector (ADR-0004) has it. It runs on a Haystack `InMemoryDocumentStore`, rebuilt from the pgvector table at every startup. Each Passage is indexed under the same "Article title > Section path" + text string that gets embedded. pgvector stays the only source of truth, and the BM25 mirror is a derived index that takes milliseconds to build.

An RRF score only means "rank within this query", so it is used for ordering and nothing else. Every returned Passage carries its **dense cosine score** (for BM25-only hits it is computed from the stored embedding), and that score alone drives the Refusal threshold gate, the API's retrieval score and the eval reports.

## Considered Options

- **`PgvectorKeywordRetriever` (Postgres full-text search).** Rejected. It builds its query with `plainto_tsquery`, which requires *every* word of the question to appear in the Passage, so natural-language questions mostly get no keyword hits. It ranks with `ts_rank_cd`, which has no IDF, so a rare `auth-401` counts no more than a common `error`. And it searches only the Passage text, not the Article title or Section path.
- **Our own OR-query over the same GIN index.** It would keep one store, but ranking would still have no IDF, and IDF is the reason a keyword leg is worth having.
- **Dense-only.** Fine at 5 Articles. At 150, the eval's dense-only ablation is what has to prove that hybrid pays for itself.
- **Gating on the fused score.** Rejected: RRF can't say "nothing is relevant", only "this ranked first".

## Consequences

- Two scores with two jobs: RRF orders the Passages, cosine answers "is anything relevant?". Anyone reading a Passage's `score` sees cosine, never RRF.
- Startup reads every Passage from pgvector to rebuild the BM25 mirror. That's trivial at this size, and the README names it as something to revisit past ~100k Passages (move keyword search into a store with real BM25).
- `eval-retrieval` reports hybrid and dense-only recall side by side.
