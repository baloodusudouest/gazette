# syntax=docker/dockerfile:1
# ---------- Étape 1 : interface Svelte compilée ----------
FROM node:22-bookworm-slim AS interface
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN mkdir -p /app && npx vite build --outDir /app/static --emptyOutDir

# ---------- Étape 2 : image d'exécution (Python + Chromium pour le rendu PDF) ----------
FROM python:3.12-slim-bookworm
LABEL org.opencontainers.image.title="gazette" \
      org.opencontainers.image.description="Gazette : le monde le jour de votre naissance, un livret A5 par proche" \
      org.opencontainers.image.source="https://github.com/baloodusudouest/gazette"

ENV TZ=Europe/Paris \
    GAZETTE_DATA=/data \
    APP_PORT=8099 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# gosu : abandon des droits root ; tzdata : heure française
RUN apt-get update && apt-get install -y --no-install-recommends gosu tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium \
    && chmod -R a+rX /ms-playwright \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app ./app
COPY --from=interface /app/static ./app/static
COPY entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh

EXPOSE 8099
HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
  CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('APP_PORT','8099')+'/health')" || exit 1
ENTRYPOINT ["/entrypoint.sh"]
