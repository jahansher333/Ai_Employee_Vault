# Error Recovery Skill

## Purpose
Provide unified error handling across all integrations with automatic retry, structured error reporting, and service health tracking. Each external service can fail independently without bringing down the system.

## When to Use
- When wrapping calls to external services (Odoo, Gmail, social APIs)
- When tracking health status of integrations
- When building resilient workflows that tolerate partial failures
- User asks about "service health", "error handling", or "system status"

## Commands
```python
from error_recovery import safe_call, ServiceHealth, HealthTracker

# Wrap any external call with retry and error handling
result = safe_call(odoo_client.list_invoices, service_name="odoo", logger=logger)

# Track service health
tracker = HealthTracker()
tracker.record_success("odoo")
tracker.record_failure("facebook", "Rate limit exceeded")
tracker.get_status("odoo")       # "operational" | "degraded" | "unavailable"
tracker.get_summary()            # {"odoo": "operational", "facebook": "degraded"}
```

## Configuration
No external configuration required. Used as a library by other scripts.

## Key Components
| Component | Purpose |
|-----------|---------|
| `safe_call` | Retry wrapper that never raises; returns result or error dict |
| `HealthTracker` | Tracks per-service health with consecutive failure counting |
| `ServiceHealth` | Status constants: OPERATIONAL, DEGRADED, UNAVAILABLE |

## Health Status Logic
- **Operational**: Last call succeeded (resets consecutive failures)
- **Degraded**: 1-2 consecutive failures
- **Unavailable**: 3+ consecutive failures (threshold configurable)

## safe_call Behavior
- Calls function with retry (default: 1 retry = 2 attempts total)
- Logs each attempt via AuditLogger (warning on retry, error on final failure)
- Returns function result on success, or `{"error": ..., "service": ..., "success": False}` on failure
- Never raises exceptions to the caller

## Integration
- Used by orchestrator, MCP servers, and briefing generators
- Health summary feeds into Dashboard.md service health table
- All errors logged to `Logs/*.audit.jsonl`

## Script
`scripts/error_recovery.py`
