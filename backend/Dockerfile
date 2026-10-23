# Build context: repo root (the pixi workspace lives there).
FROM ghcr.io/prefix-dev/pixi:0.81.0 AS build
WORKDIR /app
COPY pixi.toml pixi.lock ./
RUN pixi install --locked --environment backend

FROM ubuntu:24.04
WORKDIR /app/backend
# The conda env is relocatable only to the same path, so keep /app/.pixi/envs/backend.
COPY --from=build /app/.pixi/envs/backend /app/.pixi/envs/backend
ENV PATH=/app/.pixi/envs/backend/bin:$PATH
COPY backend/app ./app
EXPOSE 8000
CMD ["uvicorn", "--factory", "app.main:create_app_from_env", "--host", "0.0.0.0", "--port", "8000"]
