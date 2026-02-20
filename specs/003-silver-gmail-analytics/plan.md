# Implementation Plan: Silver Tier - Gmail Watcher + Data Analytics

**Branch**: `003-silver-gmail-analytics` | **Date**: 2026-02-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/003-silver-gmail-analytics/spec.md`

## Summary

Upgrade the AI Employee from Bronze Tier to Silver Tier by adding two capabilities:

1. **Gmail Watcher** (`scripts/gmail_watcher.py`) — Polls Gmail API for unread emails using OAuth 2.0, creates task files (`EMAIL_*.md`) in `Needs_Action/` with YAML frontmatter, marks emails as read, and tracks processed IDs in a ledger file. Uses `google-api-python-client` and `google-auth-oauthlib`.

2. **Data Analyzer Skill** (`scripts/data_analyzer.py`) — Reads CSV files from `Accounting/`, uses pandas to clean data (deduplicate, normalize columns, parse dates), calculates revenue/expenses/net income, groups by month, detects anomalies (>2x category average), and updates Dashboard.md with a Business Analytics section.

Both components integrate with the existing audit logger, dashboard update system, and file watcher pipeline.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: google-api-python-client, google-auth-oauthlib, pandas, python-dotenv, watchdog (existing)
**Storage**: Local filesystem (Markdown files, CSV files, JSON Lines logs, plain text ledgers)
**Testing**: pytest (existing test infrastructure)
**Target Platform**: Windows 10+ (local desktop), also compatible with Linux/macOS
**Project Type**: Single project — scripts-based automation
**Performance Goals**: Email poll cycle < 5s processing time; CSV analysis of 1,000 rows < 10s
**Constraints**: Local-first, no cloud dependencies beyond Gmail API; all credentials in .env
**Scale/Scope**: Single Gmail account, <100 emails/day, <10 CSV files with <10,000 rows each

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Evidence |
|---|-----------|--------|----------|
| I | Clarity of Requirements | PASS | 14 FRs with RFC 2119 MUST, 10 measurable SCs, Given/When/Then acceptance scenarios |
| II | Security and Sensitive Action Approval | PASS | Credentials in .env only (FR-011), .gitignore for credentials.json/token.json, clear error on missing creds (FR-013) |
| III | Logging and Audit Records | PASS | Gmail events logged to audit trail (FR-012), analytics events logged, PHR created |
| IV | Modular Code Organization | PASS | Separate modules: gmail_watcher.py, data_analyzer.py. Each independently testable. No circular deps |
| V | Readable Task and Plan Artifacts | PASS | Plan includes summary, structure, constitution check. Tasks will have phases with file paths |
| VI | Detection Only — No External Automation | DEVIATION | Gmail watcher marks emails as read (write action). Justified: marking as read is essential to prevent duplicate processing. This is a minimal, non-destructive external mutation documented in spec. Silver Tier inherently requires this external interaction |

## Architecture Flow

```
                    Gmail API                    File System
                       |                             |
              [gmail_watcher.py]             [watcher.py]
              polls every 60s                monitors Needs_Action/
                       |                             |
                       v                             v
              EMAIL_*.md created  -------->  on_created fires
              in Needs_Action/               process_inbox.py runs
                                                     |
                                                     v
                                            Dashboard.md updated
                                            (Pending Tasks table)

              Accounting/*.csv
                       |
              [data_analyzer.py]
              reads CSVs with pandas
                       |
                       v
              Dashboard.md updated
              (Business Analytics section)

              All events --> AuditLogger --> Logs/YYYY-MM-DD.audit.jsonl
```

## Project Structure

### Documentation (this feature)

```text
specs/003-silver-gmail-analytics/
├── plan.md              # This file
├── research.md          # Phase 0 output (7 decisions)
├── data-model.md        # Phase 1 output (6 entities)
├── quickstart.md        # Phase 1 output (4 test scenarios)
├── contracts/
│   ├── gmail_watcher.md # Gmail watcher module contract
│   └── data_analyzer.md # Data analyzer module contract
└── tasks.md             # Phase 2 output (created by /sp.tasks)
```

### Source Code (repository root)

```text
Ai_Employee_Vault/
├── scripts/
│   ├── audit_logger.py       # [EXISTING] Shared audit logger
│   ├── watcher.py             # [EXISTING] File system watcher
│   ├── process_inbox.py       # [EXISTING] Task processor + report
│   ├── update_dashboard.py    # [EXISTING] Dashboard updater
│   ├── gmail_watcher.py       # [NEW] Gmail polling watcher
│   └── data_analyzer.py       # [NEW] CSV analytics with pandas
├── tests/
│   ├── conftest.py            # [EXISTING] Shared fixtures
│   ├── test_watcher.py        # [EXISTING]
│   ├── test_process_inbox.py  # [EXISTING]
│   ├── test_update_dashboard.py # [EXISTING]
│   ├── test_gmail_watcher.py  # [NEW] Gmail watcher tests (mocked API)
│   └── test_data_analyzer.py  # [NEW] Data analyzer tests
├── .claude/skills/
│   ├── simple-task-reader.md  # [EXISTING]
│   └── data-analyzer.md      # [NEW] Skill definition
├── Accounting/                # [NEW] Financial data directory
│   └── sample-transactions.csv # [NEW] Sample data for testing
├── Dashboard.md               # [MODIFY] Add analytics section markers
├── README.md                  # [MODIFY] Add Gmail + analytics docs
├── .env.example               # [MODIFY] Add Gmail config vars
├── .gitignore                 # [MODIFY] Add credentials.json, token.json
├── credentials.json           # [USER-PROVIDED] OAuth client credentials
└── token.json                 # [AUTO-GENERATED] OAuth refresh token
```

**Structure Decision**: Flat scripts/ directory (consistent with Bronze Tier). No src/ restructuring needed — the project is a scripts-based automation suite, not a library or web app.

## Key Implementation Details

### Gmail Watcher Flow

1. Load credentials from `.env` (paths to credentials.json and token.json)
2. Build Gmail service using OAuth 2.0 desktop flow
3. Load gmail ledger (processed message IDs)
4. Poll loop:
   a. Call `users.messages.list(q='is:unread', maxResults=10)`
   b. For each message ID not in ledger:
      - Fetch full message with `users.messages.get()`
      - Extract from, subject, snippet, date, importance
      - Create `EMAIL_{HHMMSS}_{subject}.md` in Needs_Action/
      - Mark email as read via `users.messages.modify()`
      - Append message ID to ledger
      - Log to audit trail
   c. Sleep for interval (default 60s)
5. Handle KeyboardInterrupt for graceful shutdown

### Data Analyzer Flow

1. Scan `Accounting/` for `*.csv` files
2. For each CSV:
   a. Read with pandas, map columns flexibly
   b. Clean: remove duplicates, parse amounts, parse dates, fill missing categories
3. Concatenate all DataFrames
4. Calculate: total revenue (positive), total expenses (negative), net income
5. Group by month (YYYY-MM)
6. Detect anomalies: |amount| > 2x category mean
7. Generate Markdown tables
8. Update Dashboard.md between analytics markers
9. Log results to audit trail

### Dashboard.md Changes

Add new markers after the existing Pending Tasks section:

```markdown
## Business Analytics

<!-- START_ANALYTICS -->
No financial data available.
<!-- END_ANALYTICS -->
```

## Complexity Tracking

| Deviation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle VI: Gmail mark-as-read is external write | Essential for dedup — without it, same emails re-process every poll cycle | Read-only mode would require tracking all seen emails permanently with no Gmail-side state, causing unbounded ledger growth and fragile dedup |

## Risks

1. **OAuth token expiry**: Refresh tokens can be revoked by user or expire after 7 days if app is in "testing" status in Google Cloud. Mitigation: detect auth errors, log clear message, document Google Cloud "production" publishing steps.
2. **CSV format variability**: Real-world CSV exports vary wildly. Mitigation: flexible column mapping with fallbacks, skip unrecognizable files with warning.
3. **Windows encoding**: Previous Bronze Tier hit cp1252 issues. Mitigation: all file I/O uses explicit `encoding="utf-8"`, avoid non-ASCII in print statements.
