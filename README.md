# AI Employee - Silver Tier

A local-first, privacy-focused Digital FTE built with Claude Code + Obsidian + watchdog + Gmail API + pandas.

## Tier Status

| Tier | Status | Features |
|------|--------|----------|
| Bronze | COMPLETE | File watcher, task processing, audit logging, dashboard |
| Silver | IN PROGRESS | Gmail watcher, CSV data analytics, dual watchers |

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
```

### 2. Set Up Environment

```bash
cp .env.example .env
# Edit .env with your vault path
```

### 3. Start File Watcher (Bronze)

```bash
python scripts/watcher.py
```

### 4. Gmail Setup (Silver)

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

### 5. Run Data Analytics

```bash
# Place CSV files in Accounting/ then run:
python scripts/data_analyzer.py

# Or analyze a specific file:
python scripts/data_analyzer.py --file Accounting/q1-report.csv
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

### Test 3: Data Analytics

```bash
# Run analyzer on sample data
python scripts/data_analyzer.py

# Verify: Dashboard.md shows Business Analytics section with:
# - Financial Summary (revenue, expenses, net income)
# - Monthly Breakdown
# - Top 5 Expenses
# - Anomaly Alerts
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Vault Structure

```
Ai_Employee_Vault/
├── Dashboard.md              # Live dashboard (tasks + analytics)
├── Company_Handbook.md       # Operating principles
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
├── Needs_Action/             # Drop tasks here / Gmail creates EMAIL_*.md
├── Pending_Approval/         # Sensitive actions awaiting human review
├── Done/                     # Completed items
├── Accounting/               # CSV financial data for analytics
│   └── sample-transactions.csv
├── Logs/                     # Audit trail (JSON Lines)
│   ├── YYYY-MM-DD.audit.jsonl
│   ├── .watcher_ledger.txt   # File watcher dedup
│   └── .gmail_ledger.txt     # Gmail watcher dedup
├── Bronze/                   # Bronze Tier reference docs
├── scripts/
│   ├── watcher.py            # File system watcher (watchdog)
│   ├── gmail_watcher.py      # Gmail API polling watcher
│   ├── process_inbox.py      # Task processor + report
│   ├── data_analyzer.py      # CSV analytics (pandas)
│   ├── update_dashboard.py   # Dashboard regenerator
│   └── audit_logger.py       # Shared logging module
├── .claude/skills/
│   ├── simple-task-reader.md # Read task -> summarize -> Dashboard
│   └── data-analyzer.md      # CSV analysis -> Dashboard analytics
└── tests/
    ├── conftest.py
    ├── test_watcher.py
    ├── test_process_inbox.py
    ├── test_update_dashboard.py
    ├── test_gmail_watcher.py
    └── test_data_analyzer.py
```

## Scripts

| Script | Purpose | Tier |
|--------|---------|------|
| `watcher.py` | Monitors `Needs_Action/` for new `.md` files | Bronze |
| `gmail_watcher.py` | Polls Gmail for unread emails, creates task files | Silver |
| `process_inbox.py` | Processes tasks, generates plans, routes sensitive items | Bronze |
| `data_analyzer.py` | Reads CSVs, calculates financials, updates Dashboard | Silver |
| `update_dashboard.py` | Regenerates Dashboard.md with counts and activity | Bronze |
| `audit_logger.py` | Shared logging module (JSON Lines, append-only) | Bronze |

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
- [x] 2 concurrent watchers (file + Gmail)
- [x] Secure credential management (.env)

## Requirements

- Python 3.10+
- watchdog (file system monitoring)
- google-api-python-client (Gmail API)
- google-auth-oauthlib (OAuth 2.0)
- pandas (data analysis)
- python-dotenv (environment management)
