# Contract: Dashboard Updater Module

**File**: `scripts/update_dashboard.py`
**Responsibility**: Regenerate `Dashboard.md` with current folder counts and recent audit activity.

## Public Interface

### `update_dashboard(vault_path: Path, logger: AuditLogger) -> None`

Regenerate Dashboard.md with current state.

- Behavior:
  1. Count `.md` files in `Needs_Action/`, `Pending_Approval/`, `Done/`
  2. Read today's audit log entries (last 10)
  3. Write `Dashboard.md` with:
     - YAML frontmatter (title, updated date, status)
     - Quick Status table (folder counts)
     - How It Works section
     - Folder Structure section
     - Recent Activity section (formatted log entries)
  4. Log `dashboard_updated` event

### `count_folder(folder_path: Path) -> int`

Count `.md` files in a folder. Returns 0 if folder doesn't exist.

### `format_activity(log_entries: list[dict]) -> list[str]`

Format audit log entries as Dashboard activity lines.

- Format: `- [HH:MM] action → outcome (input_ref)`

## Error Handling

- Missing Dashboard.md: create with default content
- Missing folders: count as 0
- No audit entries today: show "No recent activity"

## Dependencies

- `scripts/audit_logger.py` (internal)
- Python stdlib: `pathlib`, `datetime`
