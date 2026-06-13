# ─── Stage 1: build the React SPA ───────────────────────────────
FROM node:20-slim AS web
WORKDIR /web
# Install deps first (cached layer)
COPY web/package.json web/package-lock.json ./
RUN npm ci
# Build (outputs /web/dist, base="/app/")
COPY web/ ./
RUN npm run build

# ─── Stage 2: Python app ────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Drop in the built SPA from the web stage (after COPY . . so it isn't clobbered)
COPY --from=web /web/dist ./web/dist

# Create writable directory for NiceGUI storage
RUN mkdir -p /app/.nicegui

ENV PORT=8080
EXPOSE 8080

# Use single-worker uvicorn for NiceGUI compatibility (NiceGUI uses in-process state)
# --proxy-headers + --forwarded-allow-ips are required behind Fly.io's reverse proxy
#   so uvicorn/NiceGUI correctly handle X-Forwarded-Proto/Host for WebSocket connections
# --timeout-keep-alive keeps connections alive through Fly.io proxy
CMD ["uvicorn", "main:fastapi_app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*", "--timeout-keep-alive", "120"]
