# AI Employee - Platinum Tier

A local-first, privacy-focused Digital FTE built with Claude Code + Obsidian + watchdog + Gmail API + Playwright + pandas + Odoo + MCP servers. Platinum Tier adds always-on Cloud VM + synced vault + work-zone specialization.

## Tier Status

| Tier | Status | Features |
|------|--------|----------|
| Bronze | COMPLETE | File watcher, task processing, audit logging, dashboard |
| Silver | COMPLETE | Gmail watcher, WhatsApp watcher, LinkedIn posting, CSV analytics, reasoning loop, CEO briefing, orchestrator, 11 agent skills |
| Gold | COMPLETE | Odoo accounting (MCP), multi-platform social posting (FB/IG/X), 3 MCP servers, auto-restart orchestrator, Ralph Wiggum autonomous loop, error recovery, weekly audit with Odoo financials |
| Platinum | COMPLETE | Always-on Cloud VM, work-zone specialization (cloud drafts / local executes), synced vault with domain folders, claim-by-move protocol, Odoo cloud deploy (Docker + nginx HTTPS + backups), health monitoring, A2A messaging, local approval workflow |

## What It Does

### File Watcher (Bronze Tier)
Drop a `.md` task file into `Needs_Action/` and the AI employee will:
1. **Detect** the new file (via watchdog file system watcher)
2. **Analyze** the content and parse YAML frontmatter
3. **Generate** an action plan with recommended steps
4. **Flag** sensitive actions for human approval in `Pending_Approval/`
5. **Log** every action to an audit trail in `Logs/`

### Gmail Watcher (Silver Tier)
The Gmail watcher monitors your inbox and:
1. **Polls** Gmail every 60 seconds for unread emails
2. **Creates** task files (`EMAIL_*.md`) in `Needs_Action/` with sender, subject, snippet
3. **Assigns priority**: important emails = high, others = medium
4. **Marks** processed emails as read to prevent duplicates
5. **Integrates** with the existing file watcher pipeline

### WhatsApp Watcher (Silver Tier)
The WhatsApp watcher monitors WhatsApp Web for urgent messages:
1. **Monitors** WhatsApp Web via Playwright browser automation
2. **Detects** messages containing priority keywords (urgent, invoice, payment, help, deadline, ASAP)
3. **Creates** task files (`WHATSAPP_*.md`) in `Needs_Action/` with sender, message, priority
4. **Persists** session across restarts (QR code scan only once)
5. **Runs headless** after initial setup — no visible browser window

### LinkedIn Poster (Silver Tier)
Automated LinkedIn post drafting with human-in-the-loop approval:
1. **Generates** professional post drafts from 3 templates (service promotion, case study, thought leadership)
2. **Saves** drafts to `Pending_Approval/LINKEDIN_*.md` for human review
3. **Publishes** approved posts (simulation mode by default, LinkedIn API optional)
4. **Moves** posted files to `Done/` with full audit trail
5. **Updates** Dashboard with "Recent Social Posts" section

### Reasoning Loop (Silver Tier)
Multi-step reasoning for complex tasks:
1. **Detects** complex tasks (invoices, payments, multi-step workflows)
2. **Creates** structured `PLAN_*.md` in `Plans/` with checkboxed steps
3. **Executes** non-approval steps automatically
4. **Routes** approval-requiring steps to `Pending_Approval/`
5. **Completes** plans and moves to `Done/` when all steps are done

### Weekly CEO Briefing (Silver Tier)
Scheduled executive briefing reports:
1. **Collects** financial summary (revenue, expenses, anomalies)
2. **Analyzes** task pipeline status and bottlenecks
3. **Generates** `Briefings/YYYY-MM-DD_Monday_Briefing.md`
4. **Recommends** actions for the upcoming week
5. **Scheduled** via Windows Task Scheduler or cron (Sunday 8 PM PKT)

### Orchestrator (Gold Tier)
Single entry point to launch and manage all components:
1. **Launches** all watchers + MCP servers as subprocesses
2. **Starts** weekly briefing scheduler in background
3. **Monitors** component health every 10 seconds
4. **Auto-restarts** crashed components (up to 3 attempts with `--auto-restart`)
5. **Handles** graceful shutdown on Ctrl+C
6. **Skips** components via `--no-gmail`, `--no-whatsapp`, `--no-odoo`, `--no-social`

### Odoo Accounting (Gold Tier)
Self-hosted Odoo Community integration via JSON-RPC:
1. **Connects** to local Odoo 19.0 at `http://localhost:8069`
2. **Lists** invoices, journal entries, and account balances
3. **Detects** overdue invoices with aging analysis
4. **Generates** financial summaries for CEO briefings
5. **MCP server** exposes 6 tools for Claude Code interaction

### Multi-Platform Social Posting (Gold Tier)
Draft and publish posts across Facebook, Instagram, Twitter/X, and LinkedIn:
1. **Generates** platform-specific drafts with hashtags and character limits
2. **Saves** drafts to `Pending_Approval/` for human review
3. **Publishes** approved posts via API (simulation mode by default)
4. **Summarizes** weekly social activity across all platforms
5. **MCP server** exposes 4 tools for Claude Code interaction

### Ralph Wiggum Loop (Gold Tier)
Autonomous multi-step task execution:
1. **Detects** cross-domain tasks (accounting, social, email, reporting)
2. **Creates** domain-tagged plans with dependency tracking
3. **Executes** steps with per-step retry (max 1 retry per step)
4. **Continues** independent steps after approval blocks
5. **Tracks** execution metrics (steps completed/failed, retries, elapsed time, domains)
6. **Validates** no circular dependencies at plan creation time

### Error Recovery (Gold Tier)
Unified error handling across all integrations:
1. **`safe_call()`** wraps external calls with structured error returns
2. **`HealthTracker`** monitors service health (operational/degraded/unavailable)
3. **Graceful degradation**: Odoo down → CSV fallback for briefings
4. **Auto-restart**: orchestrator restarts crashed components

### Work-Zone Specialization (Platinum Tier)
Two-zone architecture separating Cloud (24/7 VM) from Local (your machine):
1. **Cloud zone**: Email triage, email/social drafts, Odoo reads, health monitoring, vault sync
2. **Local zone**: Email send, social publish, WhatsApp interaction, Odoo writes, payment execution, approvals
3. **Zone enforcement**: `@zone_required` decorator blocks unauthorized operations at runtime
4. **Orchestrator**: `--zone cloud|local` flag to launch zone-appropriate components only

### Synced Vault + Claim-by-Move (Platinum Tier)
Structured vault delegation between Cloud and Local via Git sync:
1. **Domain folders**: `Needs_Action/<domain>/`, `Plans/<domain>/`, `Pending_Approval/<domain>/` for EMAIL, SOCIAL, ODOO
2. **Claim-by-move**: Atomic `os.rename()` to `In_Progress/<agent>/` prevents double-processing
3. **Updates protocol**: Cloud writes to `Updates/`, Local reads and merges
4. **Git sync**: Automatic push/pull every 2 minutes via systemd timer
5. **Syncthing alternative**: `.syncignore` patterns for file-based sync
6. **Security**: `.env`, `credentials.json`, `token.json` excluded from all sync methods

### Cloud Health Monitoring (Platinum Tier)
Watchdog service for Cloud zone components:
1. **Process checks**: Monitor PIDs of running watchers/services
2. **HTTP checks**: Verify Odoo, nginx, and other endpoints respond
3. **Sync freshness**: Alert if vault sync is stale (>5 minutes)
4. **Alert threshold**: After 3 consecutive failures, writes `ALERT_*.md` to `Updates/`
5. **Continuous loop**: Runs every 60 seconds with summary logging

### Odoo Cloud Deploy (Platinum Tier)
Docker-based Odoo Community deployment on Oracle Cloud VM:
1. **Docker Compose**: Odoo 17 + PostgreSQL 16 with health checks and persistent volumes
2. **HTTPS**: nginx reverse proxy with Let's Encrypt SSL certificates
3. **Backups**: Daily `pg_dump` with 7-day retention via cron
4. **Health watchdog**: Monitors Odoo web endpoint and restarts if down
5. **VM setup**: One-script Oracle Cloud ARM VM provisioning

### Local Approval Service (Platinum Tier)
Human-in-the-loop approval for Cloud-drafted actions:
1. **Scans** `Pending_Approval/<domain>/` for tasks promoted by Cloud
2. **Claims** tasks atomically via claim-by-move
3. **Presents** actions for human review (auto-approve mode for testing)
4. **Executes** approved actions via Local-zone-allowed operations
5. **Logs** all approval decisions to audit trail

### A2A Messaging (Platinum Tier — Optional)
Agent-to-Agent direct messaging with vault audit:
1. **HTTP webhook**: Cloud sends to Local's `/a2a` endpoint
2. **Vault fallback**: If webhook unreachable, writes to `Needs_Action/<domain>/A2A_FALLBACK_*.md`
3. **Audit trail**: Every A2A message recorded in `Updates/A2A_*.md`
4. **Message validation**: Enforced schema for task, status, sync, and alert message types
5. **Health endpoint**: `GET /a2a/health` for monitoring

### Data Analyzer (Silver Tier)
Analyze financial CSV data:
1. **Reads** CSV files from `Accounting/`
2. **Cleans** data (duplicates, missing values, column normalization)
3. **Calculates** total revenue, expenses, net income
4. **Groups** by month for trend analysis
5. **Detects anomalies** (transactions >2x category average)
6. **Updates** Dashboard.md with Business Analytics section

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Set Up Environment

```bash
cp .env.example .env
# Edit .env with your vault path
```

### 3. Odoo Setup (Gold Tier)

1. Download [Odoo Community](https://www.odoo.com/page/download) (free, self-hosted)
2. Install and run — opens at `http://localhost:8069`
3. Create a database (e.g., `odoodb`) with demo data
4. Install the **Accounting** module from Apps
5. Add to `.env`:
   ```
   ODOO_URL=http://localhost:8069
   ODOO_DB=odoodb
   ODOO_USER=admin
   ODOO_PASSWORD=admin
   ```
6. Verify:
   ```bash
   python scripts/odoo_client.py --test
   ```

### 4. Launch Everything (Recommended)

```bash
# Start all components with one command (local zone, default)
python scripts/orchestrator.py

# With auto-restart for crashed components
python scripts/orchestrator.py --auto-restart

# Launch in cloud zone (on VM)
python scripts/orchestrator.py --zone cloud --auto-restart

# Launch in local zone (on your machine)
python scripts/orchestrator.py --zone local --auto-restart

# Selectively disable components
python scripts/orchestrator.py --no-whatsapp --no-gmail --no-odoo --no-social

# Preview what would launch
python scripts/orchestrator.py --dry-run
```

### 4. Start File Watcher Only (Bronze)

```bash
python scripts/watcher.py
```

### 5. Gmail Setup (Silver)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable the **Gmail API**
3. Create **OAuth 2.0 Client ID** (Application type: Desktop)
4. Download `credentials.json` to vault root
5. Add to `.env`:
   ```
   GMAIL_CREDENTIALS_PATH=credentials.json
   GMAIL_TOKEN_PATH=token.json
   GMAIL_POLL_INTERVAL=60
   ```
6. First-time authorization:
   ```bash
   python scripts/gmail_watcher.py --auth-only
   ```
7. Start the Gmail watcher:
   ```bash
   python scripts/gmail_watcher.py
   ```

### 6. WhatsApp Setup (Silver)

1. First-time QR code authentication:
   ```bash
   python scripts/whatsapp_watcher.py --setup
   ```
   A browser window opens — scan the QR code with your phone's WhatsApp app.
   Session is saved to `~/.ai_employee/whatsapp_session/`.

2. Quick check (one-shot):
   ```bash
   python scripts/whatsapp_watcher.py --check
   ```

3. Start the WhatsApp watcher (headless):
   ```bash
   python scripts/whatsapp_watcher.py
   ```

Configure keywords and interval in `.env`:
```
WHATSAPP_POLL_INTERVAL=30
WHATSAPP_KEYWORDS=urgent,invoice,payment,help,deadline,asap
```

### 7. LinkedIn Posting (Silver)

1. Generate a post draft:
   ```bash
   python scripts/linkedin_poster.py --draft "AI Automation for Small Businesses"
   ```
   Templates: `service_promotion` (default), `case_study`, `thought_leadership`

2. Review the draft in `Pending_Approval/LINKEDIN_*.md`

3. **To approve**: Move the file to `Approved/`

4. Publish approved posts:
   ```bash
   python scripts/linkedin_poster.py --publish
   ```

5. (Optional) Continuous approval watcher:
   ```bash
   python scripts/linkedin_poster.py --watch
   ```

**Default mode is simulation** — no LinkedIn credentials needed. For real posting, add to `.env`:
```
LINKEDIN_POST_MODE=linkedin_api
LINKEDIN_ACCESS_TOKEN=your_token
LINKEDIN_PERSON_URN=urn:li:person:your_id
```

### 8. Weekly Briefing Setup (Silver)

**One-shot (generate now):**
```bash
python scripts/weekly_briefing.py
```

**Scheduled (built-in loop):**
```bash
python scripts/weekly_briefing.py --schedule
# Runs every Sunday at 8:00 PM PKT automatically
```

**Windows Task Scheduler (recommended for production):**
1. Open Task Scheduler → Create Basic Task
2. Name: "AI Employee Weekly Briefing"
3. Trigger: Weekly → Sunday → 8:00 PM
4. Action: Start a program
   - Program: `python`
   - Arguments: `D:\Hac3\Ai_Employee_Vault\scripts\weekly_briefing.py`
   - Start in: `D:\Hac3\Ai_Employee_Vault`

**Linux/Mac cron:**
```bash
# Edit crontab: crontab -e
# Add (adjust time for PKT = UTC+5, so 20:00 PKT = 15:00 UTC):
0 15 * * 0 cd /path/to/Ai_Employee_Vault && python scripts/weekly_briefing.py
```

### 9. Run Data Analytics

```bash
# Place CSV files in Accounting/ then run:
python scripts/data_analyzer.py

# Or analyze a specific file:
python scripts/data_analyzer.py --file Accounting/q1-report.csv
```

### 10. Platinum Tier: Cloud VM Setup

**Oracle Cloud Always Free VM** (no credit card required):

1. Sign up at [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/) — requires only email verification
2. Create an ARM-based Ampere A1 instance (1 OCPU, 6 GB RAM, Ubuntu 22.04)
3. SSH into the VM and run the setup script:
   ```bash
   scp deploy/setup-vm.sh ubuntu@<VM_IP>:~/
   ssh ubuntu@<VM_IP>
   chmod +x setup-vm.sh && sudo ./setup-vm.sh
   ```
4. Configure environment:
   ```bash
   cp deploy/.env.cloud.example /opt/ai-employee/.env
   # Edit .env with your domain and Odoo credentials
   ```
5. Start Odoo (Docker):
   ```bash
   cd /opt/ai-employee && docker compose up -d
   ```
6. Set up HTTPS (replace `your-domain.com`):
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```
7. Enable systemd services:
   ```bash
   sudo systemctl enable --now ai-employee vault-sync.timer
   ```

### 11. Platinum Tier: Vault Sync Setup

**Option A: Git Sync (recommended)**
```bash
# On Cloud VM
cd /path/to/vault && git init
git remote add origin <your-private-repo>
# Systemd timer handles automatic push/pull every 2 minutes
```

**Option B: Syncthing**
```bash
# Run the setup script on both machines
bash deploy/sync/syncthing-setup.sh
# Configure shared folder in Syncthing GUI (http://localhost:8384)
```

### 12. Platinum Tier: Local Approval Service

```bash
# Start the local approval watcher
python scripts/local_approval.py

# One-shot scan for pending approvals
python scripts/local_approval.py --once

# Auto-approve mode (for testing)
python scripts/local_approval.py --auto-approve
```

### 13. Platinum Demo (Validate All Requirements)

```bash
# Run the full Platinum demo (46 checkpoints)
python scripts/platinum_demo.py --verbose

# Run the Platinum self-test suite (31 tests)
python -m pytest tests/test_platinum_tier_selftest.py -v
```

## Test: End-to-End Verification

### Test 1: File Watcher Pipeline

```bash
# Terminal 1: Start the file watcher
python scripts/watcher.py

# Terminal 2: Create a test task
python -c "
from pathlib import Path
Path('Needs_Action/test-silver.md').write_text('''---
type: task
priority: high
category: review
status: new
---

# Silver Tier Test

Verify file watcher + task processor pipeline.
''', encoding='utf-8')
"

# Verify: Dashboard.md pending tasks updated, audit log entry created
```

### Test 2: Gmail Watcher (requires credentials)

```bash
# Start both watchers
python scripts/watcher.py &
python scripts/gmail_watcher.py &

# Send a test email to the monitored account
# Wait ~60 seconds
# Verify: EMAIL_*.md appears in Needs_Action/, file watcher processes it
```

### Test 3: WhatsApp Watcher

```bash
# Terminal 1: Start all 3 watchers
python scripts/watcher.py &
python scripts/gmail_watcher.py &
python scripts/whatsapp_watcher.py &

# Send a WhatsApp message containing "urgent" to the monitored number
# Wait ~30 seconds
# Verify: WHATSAPP_*.md appears in Needs_Action/ with priority: high
```

### Test 4: LinkedIn Post Flow

```bash
# Step 1: Generate a draft
python scripts/linkedin_poster.py --draft "Test Service Launch"
# Verify: LINKEDIN_*.md appears in Pending_Approval/

# Step 2: Approve (move to Approved/)
mv Pending_Approval/LINKEDIN_*.md Approved/

# Step 3: Publish
python scripts/linkedin_poster.py --publish
# Verify: File moves to Done/ with status: posted, post_mode: simulate

# Step 4: Update Dashboard
python scripts/update_dashboard.py
# Verify: "Recent Social Posts" section shows the post
```

### Test 5: End-to-End Silver Tier Flow

```bash
# 1. Start all watchers
python scripts/watcher.py &
python scripts/whatsapp_watcher.py &

# 2. WhatsApp message with "urgent invoice" arrives
# → WHATSAPP_*.md created in Needs_Action/
# → File watcher processes it (status: planned)

# 3. Generate LinkedIn post
python scripts/linkedin_poster.py --draft "Our AI Services"

# 4. Approve and publish
mv Pending_Approval/LINKEDIN_*.md Approved/
python scripts/linkedin_poster.py --publish

# 5. Update Dashboard
python scripts/update_dashboard.py

# Verify: Dashboard shows all activity, audit log has full trail
```

### Test 6: CEO Briefing

```bash
# Generate a briefing now
python scripts/weekly_briefing.py

# Verify: Briefings/YYYY-MM-DD_Monday_Briefing.md created
# Contains: Executive Summary, Financial Overview, Task Pipeline, Bottlenecks

# Update Dashboard to show briefing
python scripts/update_dashboard.py
```

### Test 7: Data Analytics

```bash
# Run analyzer on sample data
python scripts/data_analyzer.py

# Verify: Dashboard.md shows Business Analytics section with:
# - Financial Summary (revenue, expenses, net income)
# - Monthly Breakdown
# - Top 5 Expenses
# - Anomaly Alerts
```

### Test 8: Orchestrator

```bash
# Dry-run to see all components
python scripts/orchestrator.py --dry-run

# Launch everything (Ctrl+C to stop)
python scripts/orchestrator.py

# Launch without WhatsApp or Gmail
python scripts/orchestrator.py --no-whatsapp --no-gmail
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Vault Structure

```
Ai_Employee_Vault/
├── Dashboard.md              # Live dashboard (tasks + analytics + social posts)
├── Company_Handbook.md       # Operating principles
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
├── .syncignore               # Syncthing exclusion patterns
├── Needs_Action/             # Drop tasks here / watchers create files
│   ├── EMAIL/                # Email domain tasks (Platinum)
│   ├── SOCIAL/               # Social domain tasks (Platinum)
│   └── ODOO/                 # Odoo domain tasks (Platinum)
├── Plans/                    # Active reasoning loop plans
│   ├── EMAIL/                # Email plans (Platinum)
│   ├── SOCIAL/               # Social plans (Platinum)
│   └── ODOO/                 # Odoo plans (Platinum)
├── Pending_Approval/         # Sensitive actions + drafts awaiting approval
│   ├── EMAIL/                # Email drafts for Local approval (Platinum)
│   ├── SOCIAL/               # Social drafts for Local approval (Platinum)
│   └── ODOO/                 # Odoo drafts for Local approval (Platinum)
├── In_Progress/              # Claimed tasks (Platinum)
│   ├── cloud/                # Tasks claimed by Cloud agent
│   └── local/                # Tasks claimed by Local agent
├── Updates/                  # Cloud→Local status updates (Platinum)
├── Approved/                 # Posts approved for publishing
├── Done/                     # Completed items (timestamped)
├── Briefings/                # Weekly CEO briefing reports
├── Accounting/               # CSV financial data for analytics
├── Logs/                     # Audit trail (JSON Lines)
├── scripts/
│   ├── watcher.py            # File system watcher (watchdog)
│   ├── gmail_watcher.py      # Gmail API polling watcher
│   ├── whatsapp_watcher.py   # WhatsApp Web message monitor
│   ├── linkedin_poster.py    # LinkedIn draft & publishing
│   ├── process_inbox.py      # Task processor + report
│   ├── data_analyzer.py      # CSV analytics (pandas)
│   ├── reasoning_loop.py     # Multi-step reasoning & plan execution
│   ├── weekly_briefing.py    # Scheduled CEO briefing generator
│   ├── orchestrator.py       # Launch all components (--zone cloud|local)
│   ├── update_dashboard.py   # Dashboard regenerator
│   ├── audit_logger.py       # Shared logging module
│   ├── zone_config.py        # Zone enforcement (cloud/local) [Platinum]
│   ├── claim_task.py         # Claim-by-move protocol [Platinum]
│   ├── vault_delegation.py   # Vault communication protocol [Platinum]
│   ├── vault_sync.py         # Git-based vault sync [Platinum]
│   ├── cloud_health_monitor.py # Health watchdog [Platinum]
│   ├── local_approval.py     # Local approval service [Platinum]
│   ├── a2a_client.py         # A2A webhook sender [Platinum]
│   ├── a2a_server.py         # A2A webhook receiver [Platinum]
│   └── platinum_demo.py      # Platinum demo (46 checkpoints)
├── deploy/                   # Deployment files [Platinum]
│   ├── setup-vm.sh           # Oracle Cloud VM provisioning
│   ├── docker-compose.yml    # Odoo 17 + PostgreSQL 16
│   ├── .env.cloud.example    # Cloud environment template
│   ├── nginx/
│   │   ├── odoo.conf         # Reverse proxy + HTTPS
│   │   └── ssl-renew.sh      # Certbot renewal
│   ├── backup/
│   │   └── odoo-backup.sh    # Daily pg_dump with retention
│   ├── systemd/
│   │   ├── ai-employee.service  # Orchestrator service
│   │   ├── vault-sync.service   # Git sync oneshot
│   │   └── vault-sync.timer     # 2-minute sync timer
│   └── sync/
│       ├── git-sync.sh       # Git push/pull wrapper
│       └── syncthing-setup.sh # Syncthing alternative
└── tests/
    ├── test_platinum_tier_selftest.py  # 31 Platinum tests
    ├── test_zone_config.py    # 25 zone enforcement tests
    ├── test_claim_task.py     # 16 claim-by-move tests
    ├── test_a2a.py            # 10 A2A messaging tests
    └── ... (Bronze/Silver/Gold tests)
```

## Scripts

| Script | Purpose | Tier |
|--------|---------|------|
| `watcher.py` | Monitors `Needs_Action/` for new `.md` files | Bronze |
| `gmail_watcher.py` | Polls Gmail for unread emails, creates task files | Silver |
| `whatsapp_watcher.py` | Monitors WhatsApp Web for urgent messages | Silver |
| `linkedin_poster.py` | Generates LinkedIn drafts, publishes approved posts | Silver |
| `process_inbox.py` | Processes tasks, generates plans, routes sensitive items | Bronze |
| `data_analyzer.py` | Reads CSVs, calculates financials, updates Dashboard | Silver |
| `reasoning_loop.py` | Multi-step reasoning with cross-domain detection | Gold |
| `weekly_briefing.py` | CEO briefing with Odoo financials + social activity | Gold |
| `orchestrator.py` | Process manager with auto-restart | Gold |
| `update_dashboard.py` | Regenerates Dashboard.md with counts and activity | Bronze |
| `audit_logger.py` | Shared logging module (JSON Lines, append-only) | Bronze |
| `odoo_client.py` | Odoo Community JSON-RPC client | Gold |
| `social_poster.py` | Multi-platform social posting (FB/IG/X/LinkedIn) | Gold |
| `error_recovery.py` | `safe_call()` wrapper + `HealthTracker` | Gold |
| `mcp_odoo_server.py` | MCP server for Odoo accounting tools | Gold |
| `mcp_social_server.py` | MCP server for social posting tools | Gold |
| `mcp_email_server.py` | MCP server for Gmail tools | Gold |
| `zone_config.py` | Zone enforcement (cloud/local operations) | Platinum |
| `claim_task.py` | Atomic claim-by-move protocol | Platinum |
| `vault_delegation.py` | Vault communication (create/promote/update) | Platinum |
| `vault_sync.py` | Git-based vault synchronization | Platinum |
| `cloud_health_monitor.py` | Health watchdog (process/HTTP/sync) | Platinum |
| `local_approval.py` | Local approval service for Cloud drafts | Platinum |
| `a2a_client.py` | A2A webhook sender with vault fallback | Platinum |
| `a2a_server.py` | A2A webhook receiver with validation | Platinum |
| `platinum_demo.py` | Platinum demo (46 checkpoints) | Platinum |

## Agent Skills

| Skill | Description | Tier |
|-------|-------------|------|
| SimpleTaskReaderSkill | Reads task files and generates action plans | Bronze |
| ProcessInboxItemSkill | Full inbox processing with sensitivity detection | Bronze |
| MoveToDoSkill | Task completion with audit trail | Bronze |
| CheckPendingApprovalsSkill | Approval workflow processing | Bronze |
| DataAnalyzerSkill | CSV financial analysis | Silver |
| GenerateStatusReportSkill | Dashboard regeneration | Bronze |
| WhatsAppMessageParserSkill | WhatsApp urgent message detection | Silver |
| LinkedInPostSkill | LinkedIn post drafting and publishing | Silver |
| ReasoningLoopSkill | Multi-step plan creation and execution | Silver |
| CEOBriefingSkill | Weekly CEO briefing generation | Silver |
| OrchestratorSkill | Launch and manage all components | Silver |
| OdooIntegrationSkill | Odoo accounting via JSON-RPC | Gold |
| SocialPosterSkill | Multi-platform social posting | Gold |
| RalphWiggumLoopSkill | Autonomous cross-domain task execution | Gold |

## CSV Format

Place CSV files in `Accounting/` with financial data:

```csv
date,description,amount,category
2026-01-15,Client Payment,5000.00,Revenue
2026-01-16,Office Rent,-1500.00,Operations
```

Positive amounts = revenue, negative = expenses. Columns are flexibly mapped
(accepts synonyms like `value`, `memo`, `trans_date`, `type`).

## Requirements Met

### Bronze Tier
- [x] Obsidian vault with Dashboard.md and Company_Handbook.md
- [x] File system watcher monitoring /Needs_Action (watchdog)
- [x] Claude Code reading from and writing to the vault
- [x] Folder structure: /Needs_Action, /Done, /Pending_Approval, /Logs
- [x] All AI functionality as reusable Agent Skills
- [x] SimpleTaskReaderSkill reads files and appends to Dashboard.md

### Silver Tier
- [x] Gmail Watcher: monitors unread/important emails
- [x] Email tasks created in /Needs_Action with priority
- [x] DataAnalyzerSkill: CSV analysis with pandas
- [x] Revenue/expense/anomaly detection
- [x] Dashboard Business Analytics section
- [x] WhatsApp Watcher: monitors for urgent messages (Playwright)
- [x] WhatsApp task files in /Needs_Action with keyword matching
- [x] LinkedIn Poster: draft generation with 3 templates
- [x] LinkedIn approval workflow (Pending_Approval → Approved → Done)
- [x] Simulate + real LinkedIn API posting modes
- [x] Dashboard "Recent Social Posts" section
- [x] 3 concurrent watchers (file + Gmail + WhatsApp)
- [x] Reasoning Loop: complexity detection + Plan.md creation + step execution
- [x] Weekly CEO Briefing: scheduled Monday briefings with financial summary
- [x] Scheduling support: Windows Task Scheduler + cron instructions
- [x] Orchestrator: single entry point for all components with health monitoring
- [x] 11 Agent Skills (4 Bronze + 7 Silver)
- [x] Secure credential management (.env, session outside vault)
- [x] Human-in-the-loop approval for all external actions

### Gold Tier
- [x] Full cross-domain integration (Personal + Business)
- [x] Odoo Community accounting (self-hosted) + MCP integration (JSON-RPC)
- [x] Odoo client: invoices, journal entries, balances, overdue detection
- [x] Facebook, Instagram, Twitter/X post skills (draft → approval → publish)
- [x] Multi-platform social poster with platform-specific formatting
- [x] Multiple MCP servers: email, social, Odoo (3 servers, 15 tools)
- [x] Weekly Audit + CEO Briefing with Odoo financials, social activity, WoW comparison
- [x] Ralph Wiggum Loop: autonomous cross-domain task completion with retry
- [x] Error recovery: safe_call(), HealthTracker, graceful degradation
- [x] Auto-restart orchestrator (max 3 attempts per component)
- [x] Comprehensive audit logging (JSONL)
- [x] Architecture documentation (ARCHITECTURE.md)
- [x] 14 Agent Skills (4 Bronze + 7 Silver + 3 Gold)
- [x] All AI functionality as Agent Skills
- [x] HITL approval gates for financial, social, and email actions

### Platinum Tier
- [x] Cloud VM: Oracle Cloud Always Free ARM instance (1 OCPU, 6 GB RAM)
- [x] Always-on orchestrator via systemd service (cloud zone)
- [x] Work-zone specialization: Cloud drafts, Local executes
- [x] Zone enforcement decorator blocks unauthorized operations
- [x] Orchestrator `--zone cloud|local` flag
- [x] Domain folders: Needs_Action/EMAIL|SOCIAL|ODOO, Plans, Pending_Approval
- [x] Claim-by-move: atomic task claiming prevents double-processing
- [x] In_Progress/cloud and In_Progress/local directories
- [x] Vault sync: Git push/pull every 2 minutes (systemd timer)
- [x] Syncthing alternative with .syncignore
- [x] Security: .env, credentials.json, token.json excluded from sync
- [x] Odoo cloud deploy: Docker Compose (Odoo 17 + PostgreSQL 16)
- [x] HTTPS via nginx reverse proxy + Let's Encrypt
- [x] Daily backups: pg_dump with 7-day retention
- [x] Health monitoring: process + HTTP + sync freshness checks
- [x] Alert after 3 consecutive failures (ALERT_*.md in Updates/)
- [x] Vault delegation: create → promote → approve → execute workflow
- [x] Local approval service for Cloud-drafted actions
- [x] A2A messaging: HTTP webhook + vault fallback + audit trail
- [x] Cloud writes Updates/, Local reads and merges
- [x] Platinum demo: 46 checkpoints all passing
- [x] Platinum self-test: 31 pytest tests all passing
- [x] All Gold Tier requirements continue to pass (regression)

## Requirements

- Python 3.10+
- watchdog (file system monitoring)
- google-api-python-client (Gmail API)
- google-auth-oauthlib (OAuth 2.0)
- pandas (data analysis)
- playwright (WhatsApp Web automation)
- requests (LinkedIn API + social APIs)
- python-dotenv (environment management)
- mcp (Model Context Protocol SDK for MCP servers)
- Odoo Community 19.0 (self-hosted, for accounting integration)
