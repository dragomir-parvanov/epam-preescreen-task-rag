# Python RAG framework options: LlamaIndex vs LangChain vs Haystack

Research for [#5](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/5). It feeds the decision in [#9 "Choose the RAG framework"](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/9). Researched on 2026-10-23 against current releases.

**Gist:** **Haystack 3.x** fits this project best. It has a first-class citation mapper (`AnswerBuilder(reference_pattern=…)`), a heading-aware Markdown splitter, built-in mock LLM and embedders (new in 3.0), and an explicit pipeline graph that is easy to defend in review. It passed `pyright --strict` cleanly in a spike. **LangChain 1.x** is the strong runner-up: it has the best typing and the lightest dependencies, but you write citations yourself. **LlamaIndex** has the most "magic" citation engine, but it had the most `pyright --strict` friction, the heaviest dependencies, and its maintainer now says its main focus is elsewhere.

Sources are primary throughout: PyPI metadata, GitHub source at release tags, release notes and official docs. Statements marked **[spike]** come from running code locally (see [§6](#6-spike-what-was-actually-run)).

---

## 1. Versions and churn (as of 2026-10-23)

| | LlamaIndex | LangChain | Haystack |
|---|---|---|---|
| Core package | `llama-index-core` **0.14.25** (2026-09-21) | `langchain-core` **1.7.0** (2026-10-22), `langchain` 1.4.7 | `haystack-ai` **3.4.1** (2026-10-21) |
| Current major line since | 0.14.0, 2025-09-08 (still 0.x) | 1.0.0 GA, 2025-10-17 | **3.0.0, 2026-07-20** |
| Python floor | ≥3.10 | ≥3.10 | **≥3.11** (integrations dropped 3.10 in Oct 2026) |
| Release cadence | Monthly patch releases; no minor bump in 13 months | `langchain-core` minor roughly every 1–2 months (1.3 → 1.7 in 2026) | Minor roughly every 2–4 weeks (3.0 → 3.4 in 3 months) |
| Recent breaking change | 0.13/0.14 in 2025 | v1: legacy chains, retrievers, indexing API and hub moved to `langchain-classic`; `create_agent` replaced `create_react_agent` | v3: `AsyncPipeline` merged into `Pipeline`, legacy non-chat Generators removed, 30 components moved to separate packages, `Document.id` hash changed, prompt variables required by default |
| Project direction | README: *"our primary focus has shifted towards LlamaParse… we still have the OSS framework available as an open toolkit"* | Docs now centre on agents and **Deep Agents**: the official RAG tutorial is built on `create_deep_agent` | 3.0 is framed as "production-grade agents", but RAG pipelines remain first-class |

Sources: PyPI JSON for [llama-index-core](https://pypi.org/project/llama-index-core/), [langchain-core](https://pypi.org/project/langchain-core/), [langchain](https://pypi.org/project/langchain/) and [haystack-ai](https://pypi.org/project/haystack-ai/); [LlamaIndex README](https://github.com/run-llama/llama_index/blob/v0.14.25/README.md); [LangChain v1 migration guide](https://docs.langchain.com/oss/python/migrate/langchain-v1); [LangChain RAG tutorial](https://docs.langchain.com/oss/python/langchain/rag); [Haystack 3.0.0 release notes](https://github.com/deepset-ai/haystack/releases/tag/v3.0.0) and [migration guide](https://docs.haystack.deepset.ai/docs/migration); [chroma-haystack CHANGELOG](https://github.com/deepset-ai/haystack-core-integrations/blob/main/integrations/chroma/CHANGELOG.md).

**Churn risk for an AI-assisted build:** Haystack 3.0 is only three months old. Most tutorials, Stack Overflow answers and model training data show 2.x code (`OpenAIGenerator`, `AsyncPipeline`, `haystack.components.embedders.SentenceTransformers…`), and none of that works in 3.x. LangChain has the same problem with pre-v1 `RetrievalQA` and `create_retrieval_chain` code, which now lives only in `langchain-classic`. Pin exact versions, and point agents at the 3.x and v1 docs.

---

## 2. Comparison table

| Dimension | LlamaIndex 0.14 | LangChain 1.x | Haystack 3.x |
|---|---|---|---|
| **First-class citations** | ✅ `CitationQueryEngine`: re-chunks retrieved nodes into numbered `Source N:` chunks and prompts the LLM to cite `[N]`. Result: `Response.response` (text) + `source_nodes: list[NodeWithScore]` | ❌ None in core v1. You number the retrieved `Document`s in your prompt and parse `[n]` yourself, or use provider-native citations (e.g. Anthropic `citations` blocks via `langchain-anthropic`) | ✅ `AnswerBuilder(reference_pattern=r"\[(\d+)\]")`: parses `[n]` from the reply and maps it to the input documents |
| **What a source looks like** | `NodeWithScore{score, node: TextNode{node_id, text, metadata}}`. ⚠️ Citation nodes get a **fresh id**: the source node's `id_` and char offsets are deliberately dropped. Metadata is kept | `Document{id, page_content, metadata}`, with score from `similarity_search_with_score` | `GeneratedAnswer{data, query, documents: list[Document], meta}`. Each `Document{id, content, score, meta}` gains `meta.source_index` (1-based) and `meta.referenced: bool`. `return_only_referenced_documents=True` by default |
| **Markdown-aware chunking** | `MarkdownNodeParser`: splits on headings and sets `metadata["header_path"]` (e.g. `/Leave policy/`). Emits heading-only nodes **[spike]** | `MarkdownHeaderTextSplitter(headers_to_split_on=[("#","h1"),…])`: metadata `{h1:…, h2:…}`. Works on a string, so you merge your own `source` metadata back in **[spike]** | `MarkdownHeaderSplitter`: metadata `header`, `parent_headers`, `source_id`, `split_id`, `page_number`. Optional secondary split by word, passage or line. Fence-aware. Keeps document meta **[spike]** |
| **In-memory store** | `SimpleVectorStore` (default in `VectorStoreIndex`) | `langchain_core.vectorstores.InMemoryVectorStore` | `InMemoryDocumentStore` + `InMemoryEmbeddingRetriever` / `InMemoryBM25Retriever` |
| **Chroma** | `llama-index-vector-stores-chroma` 0.6.0 | `langchain-chroma` 1.1.0 | `chroma-haystack` 5.0.0 |
| **pgvector** | `llama-index-vector-stores-postgres` 0.9.0 | `langchain-postgres` **0.0.19** (still pre-1.0) | `pgvector-haystack` 8.1.2 |
| **OpenAI** | `llama-index-llms-openai`, `-embeddings-openai` | `langchain-openai` | Built into core (`OpenAIChatGenerator`, `OpenAI*Embedder`) |
| **Anthropic** | `llama-index-llms-anthropic` | `langchain-anthropic` (incl. native citations) | `anthropic-haystack` |
| **Groq** | `llama-index-llms-groq` | `langchain-groq` | No package. Use `OpenAIChatGenerator(api_base_url="https://api.groq.com/openai/v1")` (OpenAI-compatible, per the [Groq integration page](https://haystack.deepset.ai/integrations/groq)) |
| **Ollama** | `llama-index-llms-ollama`, `-embeddings-ollama` | `langchain-ollama` | `ollama-haystack` (chat + embedders) |
| **Local embeddings** | `-embeddings-huggingface`, `-embeddings-fastembed` (declares `python <3.13`) | `langchain-huggingface`; `FastEmbedEmbeddings` in `langchain-community` | `sentence-transformers-haystack` (moved out of core in 3.0), `fastembed-haystack` |
| **Fake LLM** | `MockLLM`: echoes the prompt, or emits `"text text…"` when `max_tokens` is set. You can't script the reply text. `MockFunctionCallingLLM` | `FakeListChatModel(responses=[…])`, `GenericFakeChatModel(messages=iter([...]))` (streams), `ParrotFakeChatModel`. Documented in the official unit-testing guide | `MockChatGenerator`: fixed, cycling, `response_fn` or echo. Supports streaming and `run_async`. New in 3.0 |
| **Fake embeddings** | `MockEmbedding`: **the same constant vector `[0.5]*dim` for every text**, so every score is identical and ranking can't be tested | `DeterministicFakeEmbedding`: a SHA-256-seeded random vector. ⚠️ Needs `numpy`, which `langchain-core` does not declare (it failed with `NameError: np` **[spike]**) | `MockTextEmbedder` / `MockDocumentEmbedder`: hash-derived and stable, **plus an `embedding_fn=` hook** for a custom, meaning-aware fake |
| **Upstream typing discipline** | `py.typed` in core; mypy with `disallow_untyped_defs` only. Many integration packages lack `py.typed` | `py.typed` everywhere; core runs **mypy `strict = true`** | `py.typed` in core and integrations; mypy `check_untyped_defs` + `disallow_incomplete_defs` |
| **`pyright --strict` [spike]** | ❌ 1–2 errors per small file: `reportUnknownMemberType` (`BaseIndex[Unknown]` in `from_args` / `as_query_engine`), `reportMissingTypeStubs` for `llama_index.embeddings.openai`. `query()` returns a 4-way union, so you need `isinstance` narrowing | ✅ 0 errors | ✅ 0 errors. But pipeline outputs are `dict[str, Any]`, so the boundary is *permissive* rather than *typed*: you narrow with `isinstance(…, GeneratedAnswer)` |
| **Resolved deps** (uv, py3.12, core + OpenAI) | **68** packages (`llama-index-core` pulls nltk, sqlalchemy, pillow, tiktoken, aiohttp, …) | **39** (`langchain-core` + splitters + `langchain-openai`); 45 with the `langchain` meta-package (adds langgraph) | **43** (`haystack-ai`, OpenAI included). Includes `posthog` telemetry, **on by default**: set `HAYSTACK_TELEMETRY_ENABLED=False` |
| **Streaming** | `as_query_engine(streaming=True)` + `await engine.aquery()` → `AsyncStreamingResponse`. **`source_nodes` are available before the first token**, then `async_response_gen()` | You own it: `await store.asimilarity_search_with_score()` then `llm.astream(...)` yields `AIMessageChunk`s. Sources come first naturally | `handle = pipeline.stream(data)`; `async for chunk in handle` yields `StreamingChunk`s; `handle.result` holds the final outputs (incl. `AnswerBuilder`). Sources come **after** the stream unless you run retrieval as a separate step first |
| **FastAPI fit** | Wrap the async generator in `StreamingResponse` / SSE. Watch out for the global `Settings` singleton in tests | Async generator → `StreamingResponse`. All primitives are plain async methods | Async generator → `StreamingResponse`. `warm_up()` / `close()` lifecycle maps onto FastAPI `lifespan` |

---

## 3. Per-framework notes

### LlamaIndex (0.14.25)

- **Citations.** `CitationQueryEngine.from_args(index, citation_chunk_size=512, similarity_top_k=k)` swaps in `CITATION_QA_TEMPLATE`, which tells the LLM to cite `[N]`. It re-splits every retrieved node with a `SentenceSplitter` and prefixes each piece with `Source N:`. The response gives you the answer text and the numbered `source_nodes`. You still parse `[N]` out of the text yourself: nothing marks which sources were actually used. In the source, the citation nodes are built from `model_dump()` with `id_` popped, so **the cited chunk's id is not the id stored in the vector store**. Map back through metadata such as `source` / `header_path` instead. Sources: [citation_query_engine.py @ v0.14.25](https://github.com/run-llama/llama_index/blob/v0.14.25/llama-index-core/llama_index/core/query_engine/citation_query_engine.py), [docs example](https://developers.llamaindex.ai/python/examples/query_engine/citation_query_engine/), [response schema](https://github.com/run-llama/llama_index/blob/v0.14.25/llama-index-core/llama_index/core/base/response/schema.py).
- **Chunking.** `MarkdownNodeParser` adds `header_path` metadata with a configurable separator ([markdown.py](https://github.com/run-llama/llama_index/blob/v0.14.25/llama-index-core/llama_index/core/node_parser/file/markdown.py)).
- **Testing.** `MockLLM` and `MockEmbedding` exist ([mock.py](https://github.com/run-llama/llama_index/blob/v0.14.25/llama-index-core/llama_index/core/llms/mock.py), [mock_embed_model.py](https://github.com/run-llama/llama_index/blob/v0.14.25/llama-index-core/llama_index/core/embeddings/mock_embed_model.py)), but neither is good enough for this project's deterministic tests. `MockLLM` can't return a scripted cited answer, and `MockEmbedding` gives every text the same vector. You would write your own `CustomLLM` / `BaseEmbedding` subclasses anyway.
- **Risks.** The maintainer's README says the company's main focus is now LlamaParse. Releases have stayed on 0.14.x for 13 months. Heaviest dependency tree. The global `Settings.llm` / `Settings.embed_model` defaults to OpenAI when not passed explicitly, which is a test-isolation hazard. It had the most pyright-strict friction.

### LangChain (langchain-core 1.7.0 / langchain 1.4.7)

- **Citations.** v1 has no citation component. The `langchain` package now centres on agents, and legacy chains moved to `langchain-classic` ([migration guide](https://docs.langchain.com/oss/python/migrate/langchain-v1)). The [retrieval page](https://docs.langchain.com/oss/python/langchain/retrieval) describes "2-step RAG" only as a diagram. The [RAG tutorial](https://docs.langchain.com/oss/python/langchain/rag) now uses Deep Agents. So you number the retrieved docs, prompt for `[n]` and parse the markers yourself: about 20–40 lines that you fully own and can explain. Alternatively, Anthropic's native citations come back as content blocks with `cited_text`, `document_index` and `start/end_char_index` ([langchain-anthropic docs](https://docs.langchain.com/oss/python/integrations/chat/anthropic)), but that ties citations to one provider.
- **Chunking.** `MarkdownHeaderTextSplitter` gives `{h1, h2…}` metadata ([markdown.py](https://github.com/langchain-ai/langchain/blob/langchain-core%3D%3D1.7.0/libs/text-splitters/langchain_text_splitters/markdown.py)).
- **Testing.** It has the best-documented fakes. `FakeListChatModel` and `GenericFakeChatModel` (with streaming) are covered in the official [unit-testing guide](https://docs.langchain.com/oss/python/langchain/test/unit-testing). `DeterministicFakeEmbedding` is hash-seeded ([fake.py](https://github.com/langchain-ai/langchain/blob/langchain-core%3D%3D1.7.0/libs/core/langchain_core/embeddings/fake.py)) but needs `numpy` installed separately. `FakeListChatModel` streams character by character.
- **Typing.** `langchain-core` is checked with `mypy strict = true` ([pyproject](https://github.com/langchain-ai/langchain/blob/langchain-core%3D%3D1.7.0/libs/core/pyproject.toml)), and partner packages ship `py.typed`. It passed the pyright-strict spike cleanly.
- **Risks.** Choosing LangChain and then hand-writing the retrieve → prompt → cite flow uses only its primitives (splitter, vector store, model wrappers), so a reviewer may ask "why a framework at all?" The answer is the provider and vector-store swap layer plus the fakes. Docs churn is high, with tutorials reorganised around agents. `langchain-postgres` is still 0.0.x.

### Haystack (haystack-ai 3.4.1)

- **Citations.** `AnswerBuilder(reference_pattern=r"\[(\d+)\]")` parses the reply's `[n]` markers and returns a `GeneratedAnswer` whose `documents` carry `meta.source_index` and `meta.referenced`. By default only referenced documents are returned; pass `return_only_referenced_documents=False` to get all of them, flagged. That is exactly the "answer + the citations behind it" contract the UI needs. Sources: [AnswerBuilder docs](https://docs.haystack.deepset.ai/docs/answerbuilder), [answer_builder.py @ v3.4.1](https://github.com/deepset-ai/haystack/blob/v3.4.1/haystack/components/builders/answer_builder.py), [answer.py](https://github.com/deepset-ai/haystack/blob/v3.4.1/haystack/dataclasses/answer.py).
- **Chunking.** `MarkdownHeaderSplitter` handles header levels, `keep_headers`, a secondary split and CommonMark-fence awareness, and sets `header` and `parent_headers` metadata ([markdown_header_splitter.py](https://github.com/deepset-ai/haystack/blob/v3.4.1/haystack/components/preprocessors/markdown_header_splitter.py)). A `MarkdownToDocument` converter also exists.
- **Testing.** 3.0 added `MockChatGenerator`, `MockTextEmbedder` and `MockDocumentEmbedder` "so no API keys, no network, no flaky CI" ([3.0.0 release](https://github.com/deepset-ai/haystack/releases/tag/v3.0.0), [mock.py](https://github.com/deepset-ai/haystack/blob/v3.4.1/haystack/components/generators/chat/mock.py), [mock_text_embedder.py](https://github.com/deepset-ai/haystack/blob/v3.4.1/haystack/components/embedders/mock_text_embedder.py)). `embedding_fn=` lets you plug in a meaning-aware fake, such as bag-of-words, so retrieval-ranking tests are meaningful.
- **Streaming.** In 3.x, `Pipeline` has `run`, `run_async`, `run_async_generator` and `stream()`. `stream()` returns a `PipelineStreamHandle` that you iterate with `async for`; `handle.result` then holds the final outputs ([pipeline.py](https://github.com/deepset-ai/haystack/blob/v3.4.1/haystack/core/pipeline/pipeline.py)). The `warm_up` / `close` lifecycle fits FastAPI `lifespan`.
- **Typing.** `py.typed` and mypy in core and integrations ([pyproject](https://github.com/deepset-ai/haystack/blob/v3.4.1/pyproject.toml)). Pipeline I/O is `dict[str, Any]`, so wrap the pipeline in a typed service function that returns your own Pydantic models. That seam is what #9 already wants.
- **Risks.** It is a very fresh major, so most examples online are 2.x. Python ≥3.11. Telemetry is on by default. The pipeline graph is wired by string names (`"retrieve.documents"`), so wiring mistakes surface at `connect()` / run time rather than at type-check time. There is no Groq package; use the OpenAI-compatible endpoint instead.

---

## 4. Sharp trade-offs

1. **Citations: built-in vs owned.** Haystack's `AnswerBuilder` gives a tested `[n]` → document mapping with a `referenced` flag. LlamaIndex numbers the sources, but you still parse the markers, and it re-chunks and re-ids the sources. LangChain makes you write it, though the code is small and fully explainable. If the interview story is "the framework does the plumbing, I own the contract", Haystack fits best.
2. **Typing at the boundary.** LangChain is *typed* end to end. Haystack is *permissive* (`Any` from pipelines), which is clean under pyright-strict but needs one narrowing seam. LlamaIndex is *noisy*: expect `# pyright: ignore` comments or a stub/shim layer.
3. **Determinism.** All three have a fake LLM. Only Haystack's fake embedder takes a custom function, and only LangChain's and Haystack's fakes give distinct vectors per text. None of the built-in fake embeddings are meaningful, so plan a ~15-line keyword-overlap fake for retrieval assertions whichever framework you choose.
4. **Stability vs freshness.** LangChain v1 is a year old with a strong compatibility promise inside 1.x, but its docs keep moving towards agents. Haystack 3 is three months old and ships minors fast. LlamaIndex is "stable" mostly because development has slowed.
5. **Explicitness.** Haystack's `add_component` / `connect` graph reads like an architecture diagram, which is good for a reviewed take-home. LlamaIndex's `index.as_query_engine()` hides the most, which is fastest to demo and hardest to defend line by line.

## 5. Recommendation (input to #9; the human decides there)

**Haystack 3.x**, pinned exactly (`haystack-ai==3.4.*`), on Python 3.12, with telemetry disabled in `.env.example` / Compose. Proposed usage:

- **Indexing pipeline.** `MarkdownToDocument` (or read files yourself) → `MarkdownHeaderSplitter` → embedder → `DocumentWriter`. Use `InMemoryDocumentStore` for the prototype, with `chroma-haystack` / `pgvector-haystack` as the documented upgrade path.
- **Query pipeline.** Text embedder → retriever → `ChatPromptBuilder` (numbered sources) → chat generator → `AnswerBuilder(reference_pattern=r"\[(\d+)\]", return_only_referenced_documents=False)`.
- **Seams.** A typed `ChatService` turns `GeneratedAnswer` into our own Pydantic `Answer` / `Citation` models, so FastAPI routes never import Haystack. For streaming, run retrieval first so citations can go out as the first SSE event, then stream generation.
- **Tests.** `MockChatGenerator` + `MockTextEmbedder(embedding_fn=keyword_fake)`.

**Choose LangChain instead if** typed end-to-end code and the smallest dependency tree matter more than a framework-provided citation mapper, and you're happy to own ~30 lines of prompt numbering and citation parsing. **Avoid LlamaIndex** for this project: it had the most pyright-strict friction, its bundled fakes are unusable for retrieval tests, its citation ids are lost, its dependency tree is heaviest, and its maintainer has signalled a shift in focus.

## 6. Spike: what was actually run

On 2026-10-23, in throwaway uv venvs (Python 3.12), with `pyright 1.1.414` and `# pyright: strict`. Each framework got two files: an offline "markdown → index → query with sources" script using that framework's own fakes, and a type-check-only file using the real OpenAI classes and async streaming. Files and venvs lived in a scratch directory and were not committed.

| | Offline script ran? | pyright strict, hello world | pyright strict, OpenAI + streaming |
|---|---|---|---|
| LlamaIndex 0.14.25 | ✅ (all scores identical: constant mock vector) | 1 error (`reportUnknownMemberType` on `from_args`) | 2 errors (`reportMissingTypeStubs` on `llama_index.embeddings.openai`; `reportUnknownMemberType` on `as_query_engine`) |
| LangChain core 1.7.0 | ✅ after installing `numpy` (first run: `NameError: name 'np' is not defined`) | 0 | 0 |
| Haystack 3.4.1 | ✅ `referenced: True`, `source_index: 1`, `header: 'Annual leave'`, `parent_headers: ['Leave policy']` | 0 | 0 |

Dependency counts come from `uv pip compile --python-version 3.12` on each set of requirements. Note that uv ignores upper `requires-python` bounds: `llama-index-embeddings-fastembed` declares `<3.13` but still resolved for 3.13. pip would reject it.

### Hello-world sketches (verified to run offline)

**LlamaIndex**
```python
from llama_index.core import Document, VectorStoreIndex
from llama_index.core.base.response.schema import Response
from llama_index.core.embeddings import MockEmbedding
from llama_index.core.llms import MockLLM
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.core.query_engine import CitationQueryEngine

docs = [Document(text=MD, metadata={"source": "hr/leave.md"})]
nodes = MarkdownNodeParser().get_nodes_from_documents(docs)
index = VectorStoreIndex(nodes, embed_model=MockEmbedding(embed_dim=8))
engine = CitationQueryEngine.from_args(index, llm=MockLLM(max_tokens=5), similarity_top_k=2)
result = engine.query("How many days of annual leave?")
assert isinstance(result, Response)            # query() returns a 4-way union
for sn in result.source_nodes:                 # sn.score, sn.node.node_id, sn.node.metadata["header_path"]
    print(sn.score, sn.node.metadata, sn.node.get_content())   # content starts with "Source N:"
```

**LangChain**
```python
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding   # needs numpy
from langchain_core.language_models import FakeListChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import MarkdownHeaderTextSplitter

splitter = MarkdownHeaderTextSplitter(headers_to_split_on=[("#", "h1"), ("##", "h2")])
chunks = [Document(page_content=c.page_content, metadata={**c.metadata, "source": "hr/leave.md"})
          for c in splitter.split_text(MD)]
store = InMemoryVectorStore(embedding=DeterministicFakeEmbedding(size=8))
store.add_documents(chunks)
hits = store.similarity_search_with_score(question, k=2)              # list[tuple[Document, float]]
context = "\n\n".join(f"[{i}] {d.page_content}" for i, (d, _) in enumerate(hits, 1))
llm = FakeListChatModel(responses=["Employees get 25 days [1]."])
answer = llm.invoke([SystemMessage(f"Cite sources as [n].\n\n{context}"), HumanMessage(question)])
# citation parsing of answer.text -> hits[n-1] is yours to write
```

**Haystack**
```python
from haystack import Document, Pipeline
from haystack.components.builders import AnswerBuilder, ChatPromptBuilder
from haystack.components.embedders import MockDocumentEmbedder, MockTextEmbedder
from haystack.components.generators.chat import MockChatGenerator
from haystack.components.preprocessors import MarkdownHeaderSplitter
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.components.writers import DocumentWriter
from haystack.dataclasses import ChatMessage, GeneratedAnswer
from haystack.document_stores.in_memory import InMemoryDocumentStore

store = InMemoryDocumentStore()
indexing = Pipeline()
indexing.add_component("split", MarkdownHeaderSplitter())
indexing.add_component("embed", MockDocumentEmbedder(dimension=8))
indexing.add_component("write", DocumentWriter(document_store=store))
indexing.connect("split", "embed"); indexing.connect("embed", "write")
indexing.run({"split": {"documents": [Document(content=MD, meta={"source": "hr/leave.md"})]}})

template = [ChatMessage.from_system("Cite sources as [n].\n{% for d in documents %}[{{ loop.index }}] {{ d.content }}\n{% endfor %}"),
            ChatMessage.from_user("{{ question }}")]
rag = Pipeline()
rag.add_component("embed", MockTextEmbedder(dimension=8))
rag.add_component("retrieve", InMemoryEmbeddingRetriever(document_store=store, top_k=2))
rag.add_component("prompt", ChatPromptBuilder(template=template))
rag.add_component("llm", MockChatGenerator(responses="Employees get 25 days [1]."))
rag.add_component("answer", AnswerBuilder(reference_pattern=r"\[(\d+)\]"))
rag.connect("embed.embedding", "retrieve.query_embedding")
rag.connect("retrieve.documents", "prompt.documents")
rag.connect("prompt.prompt", "llm.messages")
rag.connect("llm.replies", "answer.replies")
rag.connect("retrieve.documents", "answer.documents")
out = rag.run({"embed": {"text": q}, "prompt": {"question": q}, "answer": {"query": q}})
ans = out["answer"]["answers"][0]; assert isinstance(ans, GeneratedAnswer)
# ans.documents[0].meta -> {'source': 'hr/leave.md', 'header': 'Annual leave',
#   'parent_headers': ['Leave policy'], 'source_index': 1, 'referenced': True, ...}
```

**Streaming shapes (type-checked, not run)**
```python
# LlamaIndex: sources first, then tokens
result = await index.as_query_engine(llm=llm, streaming=True).aquery(q)   # AsyncStreamingResponse
result.source_nodes; async for tok in result.async_response_gen(): ...
# LangChain: you control ordering
hits = await store.asimilarity_search_with_score(q, k=4); async for chunk in llm.astream(msgs): chunk.text
# Haystack: tokens, then final outputs
handle = pipeline.stream(data, include_outputs_from={"retrieve"})
async for chunk in handle: chunk.content
handle.result["answer"]["answers"]
```

## 7. Open questions / not verified

- Pyright strict was checked only on small sketches. A full app touches more surface: custom `@component` classes in Haystack (`reportUntypedClassDecorator`?), Chroma / pgvector integration classes, and Ollama.
- Runtime behaviour against real providers was not exercised: streaming chunk granularity, how reliably each model emits `[n]` markers, and Haystack `AnswerBuilder` with multi-citation `[1][3]` or range forms (it has an `expand_reference_ranges` option).
- Exact provider facts (embedding pairings, Docker footprint) belong to sibling research #4.
