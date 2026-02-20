# Quickstart: Bronze Tier Foundation

## Prerequisites

- Python 3.11+
- pip

## Setup

```bash
# 1. Clone and enter vault
cd Ai_Employee_Vault

# 2. Install watchdog
pip install watchdog

# 3. Configure environment
cp .env.example .env
# Edit .env: set VAULT_PATH to your vault root (default: current directory)
```

## End-to-End Test Scenario

```bash
# Terminal 1: Start the watcher
python scripts/watcher.py

# Terminal 2: Drop a test task
cat > Needs_Action/test-task.md << 'EOF'
---
type: task
priority: high
category: review
status: new
---

# Test Task

This is a test task to verify the Bronze Tier pipeline.
EOF

# Expected: Watcher detects file, logs to Logs/YYYY-MM-DD.audit.jsonl

# Terminal 2: Process inbox
python scripts/process_inbox.py

# Expected: test-task.md gets action plan, status → planned, summary in Dashboard.md

# Terminal 2: Update dashboard
python scripts/update_dashboard.py

# Expected: Dashboard.md shows Needs_Action: 1, recent activity entries

# Terminal 2: Move to done
python scripts/process_inbox.py --move-done

# Expected: test-task.md moved to Done/, Dashboard counts update
```

## Verification Checklist

- [ ] Watcher starts without errors
- [ ] New `.md` file detected and logged
- [ ] Non-`.md` files ignored
- [ ] Audit log entry created in `Logs/`
- [ ] Task file gets action plan section
- [ ] Dashboard.md updated with summary
- [ ] Sensitive task routed to `Pending_Approval/`
- [ ] All tests pass: `python -m pytest tests/ -v`

## Running Tests

```bash
python -m pytest tests/ -v
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| VAULT_PATH | `.` (current directory) | Path to Obsidian vault root |
| WATCH_INTERVAL | `5` | Polling interval in seconds |
| LOG_RETENTION_DAYS | `30` | Days to keep audit logs |
