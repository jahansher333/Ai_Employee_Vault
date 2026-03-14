# Audit Logger Skill

## Purpose
Append-only structured audit logging in JSON Lines format. Records all AI Employee actions for compliance, debugging, and dashboard activity feeds.

## When to Use
- When any script needs to record actions, outcomes, or errors
- When reviewing past activity for a specific date
- When building dashboards or reports from audit data
- User asks to "check logs", "review audit trail", or "what happened today"

## Commands
```python
from audit_logger import AuditLogger

logger = AuditLogger("/path/to/vault")

# Log a single event
logger.log("email_processed", "EMAIL_123.md", "success",
           details={"from": "user@example.com"})

# Log with error
logger.log("odoo_sync", "invoices", "error", error="Connection refused")

# Timed context manager (auto-logs duration)
with logger.timed("reasoning_loop", "PLAN_001.md") as ctx:
    ctx["details"] = {"steps": 5}
    # ... do work ...

# Read today's log entries
entries = logger.read_log()

# Read a specific date, filtered by action
entries = logger.read_log(date="2026-03-15", action_filter="email_processed")
```

## Configuration
No `.env` settings needed. Requires only a vault path.

## Log Format
Each line in `Logs/YYYY-MM-DD.audit.jsonl` is a JSON object:
```json
{
  "timestamp": "2026-03-15T10:30:00+00:00",
  "action": "file_detected",
  "input_ref": "task_001.md",
  "outcome": "success",
  "duration_ms": 0,
  "details": {"file": "task_001.md"},
  "error": null
}
```

## Key Functions
| Function | Purpose |
|----------|---------|
| `log()` | Write one audit entry with action, outcome, details, error |
| `timed()` | Context manager that auto-records duration in ms |
| `read_log()` | Read entries for a date, optionally filtered by action |

## Integration
- Used by every script in the AI Employee system
- Logs written to `Logs/YYYY-MM-DD.audit.jsonl` (one file per day)
- Dashboard activity section reads from audit logs
- API server exposes recent entries via `/api/audit`

## Script
`scripts/audit_logger.py`
