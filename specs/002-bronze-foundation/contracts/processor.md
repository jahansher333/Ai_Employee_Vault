# Contract: Inbox Processor Module

**File**: `scripts/process_inbox.py`
**Responsibility**: Parse task files, generate action plans, detect sensitive content, update task status, route to appropriate folder.

## Public Interface

### `process_file(file_path: Path, vault_path: Path, logger: AuditLogger) -> str`

Process a single task file from `Needs_Action/`.

- Input: Path to `.md` file, vault root, logger
- Behavior:
  1. Read file content
  2. Parse YAML frontmatter → `(dict, str)` tuple
  3. Skip if `status` != `new` → return `"skipped"`
  4. Check `is_sensitive(body)` → if True, move to `Pending_Approval/`, return `"pending_approval"`
  5. Generate action plan from frontmatter + body
  6. Update frontmatter: `status: planned`, `processed_at: <now>`
  7. Append action plan section to file body
  8. Write updated file back
  9. Update Dashboard.md with summary line
  10. Log `inbox_processed` event
- Output: `"planned"` | `"pending_approval"` | `"skipped"`

### `parse_frontmatter(content: str) -> tuple[dict, str]`

Extract YAML frontmatter and body from Markdown content.

- Input: Raw file content (may or may not have `---` delimiters)
- Output: `(frontmatter_dict, body_string)`
- Default values if no frontmatter: `{type: "task", priority: "medium", category: "general", status: "new"}`

### `is_sensitive(content: str) -> bool`

Check if content contains sensitive keywords.

- Input: Full file content (case-insensitive check)
- Keywords: `payment`, `password`, `credential`, `delete`, `remove`, `api key`
- Output: `True` if any keyword found

### `generate_action_plan(frontmatter: dict, body: str) -> str`

Generate a Markdown action plan section.

- Input: Parsed frontmatter dict and body text
- Output: Markdown string with `## Action Plan` heading, timestamp, recommended steps

### `move_to_done(file_path: Path, vault_path: Path, logger: AuditLogger) -> None`

Move a processed file from `Needs_Action/` to `Done/`.

- Handles name conflicts with numeric suffix
- Logs `move_to_done` event

## Dependencies

- `scripts/audit_logger.py` (internal)
- Python stdlib: `json`, `datetime`, `pathlib`, `re`
