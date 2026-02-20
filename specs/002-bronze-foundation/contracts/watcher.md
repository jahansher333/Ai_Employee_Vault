# Contract: Watcher Module

**File**: `scripts/watcher.py`
**Responsibility**: Monitor `Needs_Action/` for new `.md` files using watchdog, log detections, trigger processing.

## Public Interface

### `TaskFileHandler(PatternMatchingEventHandler)`

Event handler that fires on new `.md` file creation.

**Constructor**:
- `vault_path: Path` — Root vault directory
- `logger: AuditLogger` — Audit logger instance
- `ledger_path: Path` — Path to deduplication ledger file

**Method: `on_created(event)`**:
- Input: `FileCreatedEvent` with `src_path` attribute
- Behavior:
  1. Check if filename is in deduplication ledger → skip if yes
  2. Log `file_detected` event via AuditLogger
  3. Add filename to ledger (memory + disk)
  4. Call `process_file()` from process_inbox module
- Output: None (side effects: log entry, ledger update, file processing)

### `start_watcher(vault_path: Path, interval: float = 5.0) -> None`

Main entry point. Starts watchdog Observer on `Needs_Action/` directory.

- Creates `Needs_Action/` if it doesn't exist
- Loads deduplication ledger into memory
- Schedules `TaskFileHandler` on `Needs_Action/`
- Runs until interrupted (Ctrl+C)
- Cleanup: `observer.stop()` + `observer.join()`

### `load_ledger(path: Path) -> set[str]`

Reads ledger file into a set of filenames. Returns empty set if file missing.

### `save_to_ledger(path: Path, filename: str) -> None`

Appends a single filename to the ledger file.

## Error Handling

- Missing `Needs_Action/` directory: auto-create
- Missing/corrupted ledger file: recreate empty (log warning)
- File detection during processing: log error, continue watching
- Observer crash: log error, attempt restart once

## Dependencies

- `watchdog` (external: `pip install watchdog`)
- `scripts/audit_logger.py` (internal)
- `scripts/process_inbox.py` (internal)
