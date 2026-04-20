FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir fastapi uvicorn python-dotenv fpdf2

# Copy backend scripts
COPY scripts/ ./scripts/

# Copy all vault folders
COPY Accounting/ /vault/Accounting/
COPY Approved/ /vault/Approved/
COPY Archive/ /vault/Archive/
COPY Briefings/ /vault/Briefings/
COPY Bronze/ /vault/Bronze/
COPY Done/ /vault/Done/
COPY In_Progress/ /vault/In_Progress/
COPY Invoices/ /vault/Invoices/
COPY Logs/ /vault/Logs/
COPY Needs_Action/ /vault/Needs_Action/
COPY Pending_Approval/ /vault/Pending_Approval/
COPY Plans/ /vault/Plans/
COPY Updates/ /vault/Updates/
COPY tests/ /vault/tests/
COPY Dashboard.md /vault/Dashboard.md

ENV VAULT_PATH=/vault
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["uvicorn", "scripts.api_server:app", "--host", "0.0.0.0", "--port", "5000"]
