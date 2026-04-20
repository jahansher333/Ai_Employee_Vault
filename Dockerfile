###############################################
# Stage 1: Build Next.js Dashboard
###############################################
FROM node:22-alpine AS dashboard-builder
WORKDIR /dashboard

COPY dashboard/package.json dashboard/package-lock.json* ./
RUN npm ci || npm install

COPY dashboard/ .
ENV NEXT_TELEMETRY_DISABLED=1
ENV API_URL=http://localhost:5000
RUN npm run build

###############################################
# Stage 2: Production — Python API + Dashboard
###############################################
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies (Node.js for dashboard + gcc for Python)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc curl && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir fastapi uvicorn python-dotenv fpdf2

# Copy backend scripts
COPY scripts/ ./scripts/

# Copy entire vault structure (all folders + root md files)
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

# Copy built dashboard
COPY --from=dashboard-builder /dashboard/.next/standalone /app/dashboard/
COPY --from=dashboard-builder /dashboard/.next/static /app/dashboard/.next/static
COPY --from=dashboard-builder /dashboard/public /app/dashboard/public

# Startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh && sed -i 's/\r$//' /app/start.sh

ENV VAULT_PATH=/vault
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

CMD ["/app/start.sh"]
