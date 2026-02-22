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
# --timeout-keep-alive keeps connections alive through Fly.io proxy
# --limit-max-requests prevents memory leaks over time
CMD ["uvicorn", "main:fastapi_app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--timeout-keep-alive", "120", "--limit-max-requests", "10000"]
