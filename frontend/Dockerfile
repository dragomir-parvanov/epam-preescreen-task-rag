# Build context: repo root (the pixi workspace lives there).
FROM ghcr.io/prefix-dev/pixi:0.81.0 AS build
WORKDIR /app
COPY pixi.toml pixi.lock ./
RUN pixi install --locked --environment frontend
COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN pixi run --frozen --environment frontend npm ci --prefix frontend
COPY frontend ./frontend
RUN pixi run --frozen --environment frontend npm run build --prefix frontend

FROM nginx:1.29-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html
