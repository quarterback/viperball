FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create writable directory for NiceGUI storage
RUN mkdir -p /app/.nicegui

ENV PORT=8080
EXPOSE 8080

# Use single-worker uvicorn for NiceGUI compatibility (NiceGUI uses in-process state)
# --proxy-headers + --forwarded-allow-ips are required behind Fly.io's reverse proxy
#   so uvicorn/NiceGUI correctly handle X-Forwarded-Proto/Host for WebSocket connections
# --timeout-keep-alive keeps connections alive through Fly.io proxy
CMD ["uvicorn", "main:fastapi_app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*", "--timeout-keep-alive", "120"]
