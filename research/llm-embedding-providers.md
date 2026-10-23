# LLM and embedding provider options for a keyless or BYOK local run

Research for [#4](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/4). It feeds the decision in [#10](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/10) (provider choice). Researched on 2026-10-23 against current docs, pricing pages and releases. The framework side is covered by [#5 / `research/rag-frameworks.md`](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/blob/research/rag-frameworks/research/rag-frameworks.md). This file only repeats the integration-package facts that matter for the provider choice.

**Gist:** Decouple the two choices. **Always embed locally and in-process with fastembed** (`BAAI/bge-small-en-v1.5`: 384-dim, 67 MB ONNX model, no PyTorch, about 2 s to embed the whole corpus on CPU). The index then never depends on a key, and switching the LLM never forces a re-index. Make the **chat LLM a runtime switch** over an OpenAI-compatible client:
1. **Keyless default:** Ollama in Compose with `qwen3.5:2b` (2.7 GB) or `llama3.2:3b` (2.0 GB). Expect about 13–19 s per answer on a 6-core desktop CPU.
2. **BYOK OpenAI** (`OPENAI_API_KEY`) with `gpt-4.1-mini` / `gpt-5-mini`. This costs well under a cent per question.
3. **Optional free BYOK** via Groq (`openai/gpt-oss-20b`). It is fast and has a free tier, but tight rate limits.

Anthropic and Groq have **no first-party embeddings** (confirmed). That is one more reason to keep embeddings local.

Facts marked **[measured]** come from running code on this machine. See [§6](#6-what-was-actually-run). Everything else cites a primary source.

---

## 1. Comparison table

| | **OpenAI** (BYOK) | **Anthropic** (BYOK) | **Groq** (BYOK, free tier) | **Ollama** (keyless, local container) | **fastembed** (keyless, in-process) | **sentence-transformers** (keyless, in-process) |
|---|---|---|---|---|---|---|
| Chat | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Embeddings | ✅ `text-embedding-3-small` (1536-d, $0.02/MTok), `-3-large` (3072-d, $0.13/MTok). `dimensions` param truncates | ❌ **None.** The docs say: *"Anthropic does not offer its own embedding model"*. They point to Voyage AI (`voyage-4-lite`/`voyage-4`, 1024-d default, 200M free tokens per model, separate key) | ❌ None on the models page. Pair it with local or OpenAI embeddings | ✅ `/api/embed`: `nomic-embed-text` (274 MB, 768-d), `embeddinggemma` (622 MB, 300M params), `embeddinggemma-2` (304 MB–1.3 GB, 768-d, Matryoshka) | ✅ Its whole purpose: `bge-small-en-v1.5` 384-d / 67 MB, `all-MiniLM-L6-v2` 384-d / 90 MB, `nomic-embed-text-v1.5` 768-d / 520 MB | ✅ `all-MiniLM-L6-v2` (384-d, 22.7M params, 256-token max) and any HF model |
| Suggested model | `gpt-4.1-mini` ($0.40/$1.60 per MTok) or `gpt-5-mini` ($0.25/$2.00); `gpt-4.1-nano` ($0.10/$0.40) / `gpt-5-nano` ($0.05/$0.40) for cheapest | `claude-haiku-5-5` ($0.10/$0.50 per MTok up to 100K-token prompts) | `openai/gpt-oss-20b` ($0.075/$0.30) or `openai/gpt-oss-120b` ($0.15/$0.60) | `qwen3.5:2b` (2.7 GB, 256K ctx, thinking model, so disable thinking) or `llama3.2:3b` (2.0 GB, 128K ctx) | `BAAI/bge-small-en-v1.5` | `all-MiniLM-L6-v2` |
| Docker footprint | Python SDK only | Python SDK only | Python SDK only (or the OpenAI SDK with `base_url`) | **Image: 3.37 GB compressed (amd64) / 5.03 GB on disk [measured]** + model 2.0–2.7 GB + embedder 0.27 GB | `onnxruntime` wheel 24 MB. **Whole site-packages 221 MB [measured]** + model 67 MB | **PyTorch: default Linux wheel 555 MB *plus* CUDA 13 libs** (e.g. cuDNN 537 MB, NCCL 305 MB, cuda-toolkit…). The CPU-only wheel is 196 MB but needs the PyTorch CPU index |
| First start | Instant | Instant | Instant | Container ready in **0.6 s**. Model pull **45 s (2.0 GB) / 60 s (2.7 GB)** on this connection. First load into RAM **2.1–2.5 s [measured]** | `pip install` 7 s. Model download + load **3.5 s** first time, **0.5 s** cached [measured] | Slower (torch import). Not measured |
| CPU latency, short RAG answer | Network-bound: a few seconds | Network-bound | Groq's selling point is speed. Not measured (no key) | **13–19 s** wall for a 1.3K-token prompt → 50–90-token answer on a Ryzen 5 5600X. Prompt eval dominates: **8–15 s** (90–168 tok/s); generation **12–16 tok/s** [measured] | Index 40×~250-token chunks: **~2 s**; query embed **6–7 ms** [measured] | Not measured |
| Structured output | ✅ Strict `json_schema` (*"always generate responses that adhere to your supplied JSON Schema"*); `responses.parse(text_format=PydanticModel)` | ✅ GA, no beta header: `output_config.format` json_schema; `client.messages.parse(output_format=PydanticModel)`; supported on `claude-haiku-5-5` | ⚠️ Strict `json_schema` only on `gpt-oss-20b/120b`, `qwen3.8-27b`, `muse-spark-open`. **Not with streaming or tool use.** JSON-object mode on all models | ✅ `format=<JSON schema>` (constrained), also via OpenAI-compat `response_format`. Worked on both models, including `/v1` `json_schema` strict [measured]. ⚠️ Small models over-cite (see §4) | n/a | n/a |
| Python SDK | `openai` 3.37.0 (2026-10-22) | `anthropic` 2.1.0 (2026-10-21) | `groq` 1.7.0 (2026-08-26). Also OpenAI-compatible at `https://api.groq.com/openai/v1` | `ollama` 0.6.3 (2026-09-29). Also OpenAI-compatible `/v1/chat/completions`, `/v1/embeddings` (api_key "required but ignored") | `fastembed` 0.9.0 (2026-10-07), Python ≥3.10 | `sentence-transformers` 6.2.0 (2026-10-21), "Production/Stable" |
| Free tier / cost posture | No free API tier on the pricing page. Pay-as-you-go. ≈ **$0.0002–0.001 per question** (1.5K in / 200 out) | No free tier. Postpaid. ≈ **$0.00025 per question** on Haiku 5.5 | **Free plan exists** (a payment method is only needed to upgrade). Published table: 30 RPM, 1K RPD, **8K TPM**, 200K TPD for gpt-oss-20b (labelled "base limits for the Developer plan"; free numbers only in the console) | Free; costs disk, RAM (2.4–2.6 GB per loaded chat model at 4K ctx [measured]) and patience | Free | Free |
| LlamaIndex | `llama-index-llms-openai` 0.8.3, `-embeddings-openai` 0.7.0 | `llama-index-llms-anthropic` 0.12.3 (+ `-embeddings-voyageai` 0.7.0) | `llama-index-llms-groq` 0.6.1 | `llama-index-llms-ollama` 0.11.0, `-embeddings-ollama` 0.10.0 | `llama-index-embeddings-fastembed` 0.7.0 | `llama-index-embeddings-huggingface` 0.8.0 |
| LangChain | `langchain-openai` 1.7.2 | `langchain-anthropic` 1.7.6 (+ `langchain-voyageai` 0.4.1) | `langchain-groq` 1.1.3 | `langchain-ollama` 1.1.0 | `FastEmbedEmbeddings` in `langchain-community` 0.4.2 | `langchain-huggingface` 1.2.3 |
| Haystack 3.x | In core (`OpenAIChatGenerator`, `OpenAI*Embedder`) | `anthropic-haystack` 8.0.0 (+ `voyage-embedders-haystack` 3.0.0) | **No package.** Use `OpenAIChatGenerator(api_base_url="https://api.groq.com/openai/v1")` | `ollama-haystack` 7.0.2 (chat + embedders) | `fastembed-haystack` 3.0.0 | `sentence-transformers-haystack` (moved out of core in 3.0, per #5 research) |

Sources: see §7.

---

## 2. Recommended configurations

### A. Keyless default: Ollama chat + fastembed embeddings *(what `pixi run up` does with no `.env`)*

- `LLM_PROVIDER=ollama`, `OLLAMA_MODEL=qwen3.5:2b` (or `llama3.2:3b`), `EMBEDDINGS=fastembed:BAAI/bge-small-en-v1.5`.
- Compose runs `ollama/ollama:<pinned tag>` with a named volume. A one-shot init service (or a backend startup step) runs `ollama pull` for the model, so the first `up` downloads about **3.4 GB image + 2–2.7 GB model** (≈ 5.5–6 GB, 2–3 minutes on a fast line). Later starts are seconds.
- Put Ollama behind a **Compose profile**, or make it the default but skippable, so BYOK reviewers don't pay the 5 GB download.
- Expect **13–19 s per answer** on a modern 6-core desktop. Laptops will likely be slower (this is an estimate, not measured). Streaming tokens to the UI makes this tolerable. Keep the prompt small: about 3–4 chunks of about 300 tokens, `num_ctx` 4096.
- **macOS caveat:** Docker Desktop GPU support covers only Windows + WSL2 + NVIDIA. Ollama in a container on a Mac is CPU-only, which is what we measured. Offer `OLLAMA_BASE_URL=http://host.docker.internal:11434` so Mac reviewers can point at a native (Metal-accelerated) Ollama instead.

### B. BYOK OpenAI: OpenAI chat + the same fastembed embeddings *(recommended "fast path")*

- `LLM_PROVIDER=openai`, `OPENAI_API_KEY=…`, `OPENAI_MODEL=gpt-4.1-mini` (non-reasoning, so fast first token) or `gpt-5-mini`.
- Keep embeddings local: there is no re-index when switching providers, the embedder never needs a key, and the index is identical in both modes. OpenAI embeddings (`text-embedding-3-small`) would raise retrieval quality a bit, but would make the index provider-dependent: a 1536-d index can't be queried with a 384-d query vector. If you want that, gate it behind an explicit `EMBEDDINGS=openai` setting and key the persisted index by embedder name and dimension.
- Cost for a whole review session (≈ 50 questions + indexing): **under $0.05**.

### C. Optional free BYOK: Groq *(via the OpenAI-compatible client, near-zero code)*

- `LLM_PROVIDER=openai-compatible`, `OPENAI_BASE_URL=https://api.groq.com/openai/v1`, `OPENAI_API_KEY=$GROQ_API_KEY`, model `openai/gpt-oss-20b`.
- Pros: free plan, very fast, and the same client code as B (and as Ollama's `/v1`).
- Cons: **8K tokens/minute** means only about 3–5 RAG questions per minute with 1.5K-token prompts. Strict structured output **can't be combined with streaming**. The model line-up churns: every Llama model was **deprecated for free and developer tiers on 2026-08-16**.
- **Anthropic** fits the same slot as a BYOK alternative (`claude-haiku-5-5`, cheap, GA structured outputs, and native citation blocks via `langchain-anthropic`). But it needs its own client, not the OpenAI-compatible one, and has no embeddings. Worth it only if native citations are wanted.

**Design implication for #10:** one `ChatModel` port with two adapters covers all of A/B/C: an **OpenAI-compatible adapter** (OpenAI, Groq, Ollama `/v1`) and optionally a native Ollama or Anthropic adapter. Plus one **local embedder** fixed at startup. A **deterministic fake** chat model for tests rounds it out (see #5 research for each framework's fakes).

---

## 3. Per-provider notes

### OpenAI
- Current cheap chat models (Standard tier, per MTok in/out): `gpt-5.4-nano` $0.20/$1.25, `gpt-5.4-mini` $0.75/$4.50, `gpt-5-nano` $0.05/$0.40, `gpt-5-mini` $0.25/$2.00, `gpt-4.1-nano` $0.10/$0.40, `gpt-4.1-mini` $0.40/$1.60, `gpt-4o-mini` $0.15/$0.60.
- The gpt-5 family are reasoning models, so they spend output tokens and time on reasoning unless you lower the effort. `gpt-4.1-mini` / `-nano` don't reason, which makes them the low-latency choice for a chat UI.
- Embeddings: `text-embedding-3-small` 1536-d default, 62,500 pages/$, MTEB 62.3%. `text-embedding-3-large` 3072-d, MTEB 64.6%. No newer embedding generation is listed.
- Structured outputs: strict `json_schema`, supported "starting with GPT-4o" (incl. `gpt-4o-mini`). OpenAI recommends it over JSON mode.

### Anthropic
- No embedding model. The docs recommend Voyage AI (now a MongoDB product): `voyage-4-lite` $0.02/MTok, `voyage-4` $0.06, `voyage-4-large` $0.12; 200M free tokens per model; the key comes from MongoDB Atlas. That is a **second key** for a reviewer, so it's a poor fit here.
- Cheapest model: **Claude Haiku 5.5**, $0.10 in / $0.50 out per MTok for prompts ≤100K tokens. Haiku 4.5 is $1/$5.
- Structured outputs are **GA** on `claude-haiku-5-5` (and others). `output_format` is deprecated in favour of `output_config.format`, so older tutorials will break.

### Groq
- Production chat models today: `openai/gpt-oss-20b`, `openai/gpt-oss-120b`. `llama-3.1-8b-instant` / `llama-3.3-70b-versatile` still appear on the models page as "Contact sales", but the deprecations page says they were **shut down for free and developer tiers on 2026-08-16** (replacement: `openai/gpt-oss-20b` / `-120b`). Most blog posts and LLM training data still say "use llama3 on Groq", so beware.
- No embeddings. JSON-object mode on all models. Strict `json_schema` only on four models, and not with streaming or tool use.
- Rate limits: the published table (30 RPM / 1K RPD / 8K TPM / 200K TPD for gpt-oss-20b) is labelled as Developer-plan base limits, while the free-plan numbers render only in the console. Third-party sources quoting the free plan disagree (1K vs 14.4K RPD). **Treat 8K TPM as the binding constraint.**

### Ollama
- Image `ollama/ollama:0.40.9` (released 2026-10-23): **3,372 MB compressed amd64 / 2,818 MB arm64**, **5.03 GB unpacked [measured]**. It bundles CUDA/Vulkan runtimes. The `rocm` tag is 1.45 GB but AMD-only.
- Model sizes (Ollama library, default quant): `llama3.2:3b` 2.0 GB, `llama3.2:1b` 1.3 GB, `qwen3.5:0.8b` 1.2–1.3 GB, `qwen3.5:2b` 2.7–3.1 GB, `qwen3.5:4b` 3.3–4.0 GB, `qwen3:1.7b` 1.4 GB, `qwen3:4b` 2.5 GB. `gemma4:e2b` is 4.6 GB+, so it isn't small. Embedders: `nomic-embed-text` 274 MB (768-d [measured]), `embeddinggemma` 622 MB, `embeddinggemma-2:270m` 304–378 MB (768-d, Matryoshka 512/256/128).
- `qwen3.5` is a thinking model. Pass `think: false` (native API) or `reasoning_effort: "none"` (`/v1`), or latency balloons. Both worked [measured].
- Structured outputs: native `format=<schema>` and OpenAI-compat `response_format` `json_schema` both enforced the schema [measured]. Ollama's *cloud* doesn't support structured outputs (irrelevant here).
- `ollama` is also on conda-forge (0.32.15, behind upstream 0.40.9). It could be installed through pixi for a native, non-Docker run, but check that it's new enough for `qwen3.5`.

### fastembed (Qdrant)
- ONNX Runtime, no PyTorch: *"We don't require a GPU and don't download GBs of PyTorch dependencies, and instead use the ONNX Runtime."* Deps: `onnxruntime`, `tokenizers`, `huggingface-hub`, `numpy`, etc.
- Models download from Hugging Face on first use into a temp-dir cache (`/tmp/fastembed_cache` in the container [measured]). **Set `FASTEMBED_CACHE_PATH`** (`cache_dir=`) to a volume, or pre-download during `docker build`. Otherwise every container start re-downloads the model, and an offline reviewer breaks.
- Has `query_embed()` / `passage_embed()` to apply BGE-style query prefixes correctly.
- ⚠️ `llama-index-embeddings-fastembed` declares `python <3.13` (from #5 research). That only matters if LlamaIndex is chosen.

### sentence-transformers
- The most flexible option (any HF model, rerankers), but PyTorch makes the image heavy. The default Linux `torch` 2.14.1 wheel is 555 MB and depends on CUDA 13 packages worth well over 1 GB (cuDNN alone is 537 MB). The CPU-only wheel (196 MB) needs `--index-url https://download.pytorch.org/whl/cpu`, which is awkward to express in pixi. There are `[onnx]` and `[openvino]` extras, but torch is still a dependency. Prefer fastembed unless a model fastembed lacks is needed.

---

## 4. Quality notes from the spike (small local models)

The same 4-chunk HR-policy prompt was sent to both models, with a system prompt asking for `[docN]` citations:
- `qwen3.5:2b` answered correctly and cited `[doc1]` in plain-text mode.
- `llama3.2:3b` answered correctly but **didn't use bracket citations** in plain-text mode ("According to the policies…").
- In JSON mode (`{answer, citations[]}`), **both listed all four docs** as citations, even though the four chunks had identical text in this synthetic test, so this is a weak signal.

Takeaway: with a 2–3B local model, don't make the UI's citation list depend solely on the model's self-reported citations. Return the retrieved chunks as sources, and treat model-marked references as a highlight on top. This feeds the citation-contract and prompt-design work.

---

## 5. Facts #10 needs (checklist)

- Anthropic and Groq: **no embeddings** (confirmed in the Anthropic docs and the Groq models page).
- One local embedder for every mode → **no re-index on provider switch**. `bge-small-en-v1.5` is 384-d, 67 MB, 221 MB total site-packages with fastembed.
- Keyless Ollama costs the reviewer **≈ 5.5–6 GB download, ≈ 3 GB RAM, 13–19 s/answer on a desktop CPU**, and is **CPU-only on macOS Docker**.
- BYOK OpenAI costs **< $0.001/question**. There is no free tier, so the reviewer needs a funded key.
- Groq is free but limited to **8K TPM**, and has **no streaming + strict JSON together**. Its model list churns (Llama removed 2026-08-16).
- An OpenAI-compatible client covers OpenAI, Groq and Ollama (`/v1`) with one adapter. All three frameworks support all providers (Haystack via `api_base_url` for Groq).
- Pin model tags and the Ollama image tag. Model line-ups changed several times in 2026.

---

## 6. What was actually run

Run on 2026-10-23 on an AMD Ryzen 5 5600X (6c/12t), 31 GB RAM, Linux, Docker 28.1.1, with no GPU used. The Ollama log reported `library=cpu`.

- `docker pull ollama/ollama:0.40.9` → `docker images` size 5.03 GB. Container start → `/api/version` responding: 0.6 s.
- `ollama pull`: `nomic-embed-text` 7 s, `llama3.2:3b` 45 s, `qwen3.5:2b` 60 s.
- RAG answer benchmark: a system prompt plus 4 chunks (≈1.3K prompt tokens), `temperature 0`, `num_ctx 4096`, `think: false`. A nonce at the start of the prompt defeats Ollama's prompt cache. A cached second run of an identical prompt took only 3.8 s, which would be misleading. Figures come from Ollama's `prompt_eval_*` / `eval_*` counters:

| Model | Mode | Wall | Load | Prompt eval | Generation |
|---|---|---|---|---|---|
| llama3.2:3b | text (cold) | 20.3 s | 2.5 s | 1309 tok in 13.1 s (100 tok/s) | 59 tok, 12.7 tok/s |
| llama3.2:3b | text | 16.9 / 17.9 s | 0 | 1320 tok, 90–99 tok/s | 48 tok, 13.8–15.6 tok/s |
| llama3.2:3b | JSON schema | 18.8 s | 0 | 98 tok/s | 65 tok, 12.4 tok/s |
| qwen3.5:2b | text (cold container) | 14.5–15.3 s | 2.1 s | 1343 tok, 138–168 tok/s | 56–66 tok, 14.9–16.3 tok/s |
| qwen3.5:2b | text | 12.7 / 13.0 s | 0 | 144–150 tok/s | 56 tok, 15.4 tok/s |
| qwen3.5:2b | JSON schema | 14.8 s | 0 | 143 tok/s | 86 tok, 16.0 tok/s |

- Memory: `ollama ps` showed `qwen3.5:2b` 2.4 GB, `llama3.2:3b` 2.6 GB, `nomic-embed-text` 389 MB. The container used 6.5 GB with all three loaded.
- Embeddings: 40 chunks × ≈250 tokens.
  - fastembed `bge-small-en-v1.5` (in `python:3.12-slim`): 2.12 s / 1.92 s to index, 6–7 ms per query, 3.5 s first load including download, 0.5 s cached.
  - fastembed `nomic-embed-text-v1.5`: 5.73 s to index, 19 ms per query, 12.8 s first load.
  - Ollama `nomic-embed-text`: 3.7 s to index, 12–13 ms per query.
- `pip install fastembed==0.9.0` in `python:3.12-slim`: 7 s, site-packages 221 MB. The cache held 587 MB after both models.
- Wheel sizes are from the PyPI JSON API and `download.pytorch.org` (HEAD `content-length`).
- All containers, images and volumes were removed afterwards.

---

## 7. Sources

- OpenAI pricing: https://developers.openai.com/api/docs/pricing
- OpenAI embeddings guide: https://developers.openai.com/api/docs/guides/embeddings
- OpenAI structured outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- Anthropic embeddings (no first-party model; Voyage): https://platform.claude.com/docs/en/build-with-claude/embeddings
- Anthropic pricing: https://platform.claude.com/docs/en/about-claude/pricing
- Anthropic structured outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Voyage AI pricing and free tokens: https://www.mongodb.com/docs/voyageai/management/billing/
- Groq models: https://console.groq.com/docs/models
- Groq rate limits: https://console.groq.com/docs/rate-limits
- Groq deprecations: https://console.groq.com/docs/deprecations
- Groq structured outputs: https://console.groq.com/docs/structured-outputs
- Groq billing FAQ (free → developer tier): https://console.groq.com/docs/billing-faqs
- Ollama Docker Hub tags (sizes): https://hub.docker.com/r/ollama/ollama/tags
- Ollama Docker docs: https://docs.ollama.com/docker
- Ollama structured outputs: https://docs.ollama.com/capabilities/structured-outputs
- Ollama embeddings: https://docs.ollama.com/capabilities/embeddings
- Ollama OpenAI compatibility: https://docs.ollama.com/api/openai-compatibility
- Ollama library: https://ollama.com/library/llama3.2/tags, https://ollama.com/library/qwen3.5/tags, https://ollama.com/library/qwen3/tags, https://ollama.com/library/gemma4/tags, https://ollama.com/library/nomic-embed-text, https://ollama.com/library/embeddinggemma, https://ollama.com/library/embeddinggemma-2
- Docker Desktop GPU support (Windows/WSL2/NVIDIA only): https://docs.docker.com/desktop/features/gpu/
- fastembed README: https://github.com/qdrant/fastembed. Supported models: https://qdrant.github.io/fastembed/examples/Supported_Models/. PyPI: https://pypi.org/project/fastembed/
- sentence-transformers install: https://sbert.net/docs/installation.html. all-MiniLM-L6-v2 card: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- PyTorch wheel: https://pypi.org/project/torch/ (2.14.1), CPU index https://download.pytorch.org/whl/cpu/torch/
- Haystack Groq integration: https://haystack.deepset.ai/integrations/groq. OpenAIChatGenerator: https://docs.haystack.deepset.ai/docs/openaichatgenerator
- Package versions: PyPI JSON API (`https://pypi.org/pypi/<pkg>/json`) for every package named in §1, queried 2026-10-23
- conda-forge ollama: https://anaconda.org/conda-forge/ollama
- Secondary (not primary; used only to corroborate the macOS point): https://chariotsolutions.com/tags/ollama/, https://insiderllm.com/guides/docker-local-ai-ollama-open-webui-gpu-passthrough/

### Not chased / uncertain
- **Groq free-plan numbers:** the published table is labelled Developer plan, and third-party sources disagree. Confirm in a console if it matters.
- **Gemini** (not asked for, but relevant as a *free* BYOK option *with* embeddings): `gemini-3.5-flash-lite` / `gemini-3.6-flash` and `gemini-embedding-2` (3072-d default, 128–3072 via `output_dimensionality`) are free on the Free Tier, but free-tier content *"is used to improve our products"*. The models page lists the embedder as `gemini-embedding-2-preview` while the embeddings guide says `gemini-embedding-2`. Sources: https://ai.google.dev/gemini-api/docs/pricing, https://ai.google.dev/gemini-api/docs/embeddings, https://ai.google.dev/gemini-api/docs/models
- **CPU latency on laptops and Apple Silicon** (Docker, CPU) was not measured. Expect it to be slower than the desktop figures above.
- **Hosted-provider latency** was not measured (no keys).
