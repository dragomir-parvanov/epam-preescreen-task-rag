# Build context: repo root (the pixi workspace lives there).
FROM ghcr.io/prefix-dev/pixi:0.81.0 AS build
WORKDIR /app
COPY pixi.toml pixi.lock ./
RUN pixi install --locked --environment backend
# Bake the embedding model (app.rag.haystack.embedding.EMBEDDING_MODEL) into the image, so
# startup never downloads it. Here rather than in the runtime stage, which has no CA certificates.
ENV FASTEMBED_CACHE_PATH=/app/models/fastembed
RUN .pixi/envs/backend/bin/python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

FROM ubuntu:24.04
WORKDIR /app/backend
# The conda env is relocatable only to the same path, so keep /app/.pixi/envs/backend.
COPY --from=build /app/.pixi/envs/backend /app/.pixi/envs/backend
ENV PATH=/app/.pixi/envs/backend/bin:$PATH
ENV HAYSTACK_TELEMETRY_ENABLED=False
ENV FASTEMBED_CACHE_PATH=/app/models/fastembed
COPY --from=build /app/models/fastembed /app/models/fastembed
COPY backend/app ./app
# Read at startup by the Article endpoints, at the path app.knowledge_base expects (/app/...).
COPY knowledge-base /app/knowledge-base
EXPOSE 8000
CMD ["uvicorn", "--factory", "app.main:create_app_from_env", "--host", "0.0.0.0", "--port", "8000"]
