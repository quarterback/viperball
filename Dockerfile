FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

EXPOSE 8080

CMD ["uvicorn", "main:fastapi_app", "--host", "0.0.0.0", "--port", "8080"]
