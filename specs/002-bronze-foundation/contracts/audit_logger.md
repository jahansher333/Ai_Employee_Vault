# Contract: Audit Logger Module

**File**: `scripts/audit_logger.py`
**Responsibility**: Append-only JSON Lines logging for all system actions.

## Public Interface

### `AuditLogger(vault_path: str | Path)`

**Constructor**: Creates `Logs/` directory if missing.

### `log(action: str, input_ref: str, outcome: str = "success", duration_ms: int = 0, details: dict | None = None, error: str | None = None) -> None`

Append a single log entry to today's JSONL file.

- Output file: `Logs/YYYY-MM-DD.audit.jsonl`
- Entry format: Single JSON object with fields: timestamp, action, input_ref, outcome, duration_ms, details, error

### `timed(action: str, input_ref: str) -> ContextManager`

Context manager that measures execution time and logs on exit.

- On success: logs with `outcome: "success"` and measured `duration_ms`
- On exception: logs with `outcome: "error"` and error message, then re-raises

### `read_log(date: str | None = None, action_filter: str | None = None) -> list[dict]`

Read and optionally filter log entries.

- `date`: ISO date string (default: today)
- `action_filter`: Filter entries by action name
- Returns: List of parsed JSON dicts

## Error Handling

- Missing `Logs/` directory: auto-create in constructor
- I/O error on write: raise (caller handles)
- Malformed JSON on read: skip line, continue

## Dependencies

- Python stdlib only: `json`, `datetime`, `pathlib`, `contextlib`
