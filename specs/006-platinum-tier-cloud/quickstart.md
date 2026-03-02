# Quickstart: Platinum Tier — Always-On Cloud + Local Executive

## Prerequisites

- Oracle Cloud Free Tier account (Always Free ARM VM)
- Local machine with existing Gold Tier AI Employee working
- Git configured with SSH keys on both machines
- Domain name pointing to Cloud VM public IP (for HTTPS)

## Environment Variables

### Cloud VM (`.env` on cloud)

```bash
# Zone
ZONE_MODE=cloud

# Vault
VAULT_PATH=/home/ai-employee/vault

# Odoo (cloud-local connection)
ODOO_URL=http://localhost:8069
ODOO_DB=mycompany
ODOO_USER=admin
ODOO_PASSWORD=<cloud-odoo-password>

# Gmail (read-only — credentials for polling)
GMAIL_CREDENTIALS_PATH=/home/ai-employee/.config/gmail/credentials.json
GMAIL_TOKEN_PATH=/home/ai-employee/.config/gmail/token.json
GMAIL_POLL_INTERVAL=60

# Health monitoring
HEALTH_CHECK_INTERVAL=60
HEALTH_ALERT_EMAIL=ceo@example.com
HEALTH_CONSECUTIVE_FAILURES=3

# Vault sync
SYNC_METHOD=git
SYNC_INTERVAL=120
SYNC_REMOTE=origin
SYNC_BRANCH=vault-sync

# A2A (Phase 2 — optional)
A2A_ENABLED=false
A2A_LOCAL_WEBHOOK_URL=http://local-ip:8765/a2a
```

### Local Machine (`.env` additions)

```bash
# Zone
ZONE_MODE=local

# A2A (Phase 2 — optional)
A2A_ENABLED=false
A2A_LISTEN_PORT=8765
```

## Quick Setup

### 1. Cloud VM Setup

```bash
# SSH into Oracle Cloud VM
ssh ubuntu@<vm-public-ip>

# Run provisioning script
bash deploy/setup-vm.sh

# Copy cloud env
cp deploy/.env.cloud.example .env
# Edit .env with your values

# Start services
sudo systemctl enable ai-employee
sudo systemctl start ai-employee
```

### 2. Odoo Deployment

```bash
# Start Odoo + PostgreSQL
cd deploy/
docker compose up -d

# Verify HTTPS
curl -I https://<your-domain>/web/health
```

### 3. Vault Sync

```bash
# On Cloud VM
bash deploy/sync/git-sync.sh --setup

# On Local machine
bash deploy/sync/git-sync.sh --setup

# Verify: create test file on cloud, check it appears locally
```

### 4. Verify

```bash
# On Cloud VM
python scripts/orchestrator.py --zone cloud --dry-run

# On Local machine
python scripts/orchestrator.py --zone local --dry-run

# Run demo
python scripts/platinum_demo.py
```

## Folder Structure After Setup

```
Vault/
├── Needs_Action/
│   ├── EMAIL/       ← Cloud writes email triage
│   ├── SOCIAL/      ← Cloud writes social drafts
│   └── ODOO/        ← Cloud writes Odoo triage
├── Plans/
│   ├── EMAIL/
│   ├── SOCIAL/
│   └── ODOO/
├── Pending_Approval/
│   ├── EMAIL/       ← Drafts for CEO to approve
│   ├── SOCIAL/
│   └── ODOO/
├── In_Progress/
│   ├── cloud/       ← Tasks claimed by cloud
│   └── local/       ← Tasks claimed by local
├── Updates/          ← Cloud → Local status channel
├── Done/             ← Completed tasks
└── Dashboard.md      ← Single-writer (Cloud)
```
