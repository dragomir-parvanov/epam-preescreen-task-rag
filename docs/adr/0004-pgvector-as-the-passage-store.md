# pgvector stores the Passages, even at prototype scale

Passages and their embeddings live in **Postgres with pgvector**, run as a Compose service and accessed through `pgvector-haystack`. They are not kept in Haystack's `InMemoryDocumentStore`. The Knowledge Base is 150 Articles, a few thousand Passages, and an in-memory store would handle that. We still pick pgvector because it is what a real deployment would run, so "how does this scale to hundreds of manuals" becomes a configuration change (switch on HNSW, sync incrementally) instead of a store migration. The cost is one more container and a real database in the test path.

- **The index persists** in a named volume. Re-ingesting is an idempotent sync: deterministic Passage ids, upsert the Passages that changed, delete the ones that no longer exist. When the sync runs, and whether readiness waits for it, is decided under operational readiness.
- **Haystack owns the schema.** Its store creates the table and the extension. The table is a derived index that can always be rebuilt from `knowledge-base/` plus the pinned embedder, so there is no Alembic: a schema change means dropping the table and re-ingesting. The table name and `embedding_dimension=384` are set explicitly (the store's default is 768), and startup fails fast if the stored dimension differs.
- **Retrieval uses cosine similarity with exact nearest-neighbour search.** A score is `1 - cosine distance`, and higher is better. At a few thousand rows a sequential scan takes milliseconds and is exact, which keeps the CI-gating retrieval eval deterministic. HNSW is approximate and is the named scaling lever: one setting, tuned against the retrieval eval.

## Considered Options

- **`InMemoryDocumentStore`, rebuilt at startup.** It is the simplest option and needs no extra container. Rejected: it makes the scaling story hypothetical, and every restart would re-embed every Passage.
- **Chroma.** Rejected: it adds persistence without the rest. There's no SQL metadata filtering, its Haystack integration has no keyword retrieval, and nobody has verified it on Haystack 3.x.

## Consequences

- `pgvector-haystack` declares `haystack-ai>=2.28` with no upper bound, and nobody has run it on 3.x. It is exact-pinned like every other Haystack package, and the adapter tests are what prove it works.
- Adapter tests and `eval-retrieval` run against a real pgvector through `testcontainers`, so they need Docker. They error rather than skip when Docker is missing, so a broken adapter can't pass silently. The test path and the shipped path use the same Postgres because the image tag is pinned in one place, read by both Compose and the test fixture.
- Postgres full-text search (`PgvectorKeywordRetriever`) is available if retrieval wants a keyword or hybrid component, with no second store.
