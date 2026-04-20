FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir fastapi uvicorn python-dotenv fpdf2

# Copy application code
COPY scripts/ ./scripts/

# Default vault path inside container
ENV VAULT_PATH=/vault
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["uvicorn", "scripts.api_server:app", "--host", "0.0.0.0", "--port", "5000"]
