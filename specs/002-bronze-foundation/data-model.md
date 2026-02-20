# Data Model: Bronze Tier Foundation

**Feature**: 002-bronze-foundation
**Date**: 2026-02-17

## Entities

### 1. Task File

A Markdown document representing a unit of work for the AI Employee.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| type | string | No | "task" | Task classification (task, request, note) |
| priority | string | No | "medium" | Urgency level (high, medium, low) |
| category | string | No | "general" | Domain (research, draft, review, organize, analyze, general) |
| status | string | No | "new" | Lifecycle state (new, planned, pending_approval, done) |
| processed_at | ISO 8601 datetime | No | null | Timestamp when processed |
| body | Markdown text | Yes | - | Task description and context |

**State Transitions**:
```
new → planned (processed normally)
new → pending_approval (sensitive content detected)
planned → done (moved to Done/)
pending_approval → planned (approved by human)
pending_approval → done (approved and completed)
```

**Location by State**:
- `new`, `planned` → `Needs_Action/`
- `pending_approval` → `Pending_Approval/`
- `done` → `Done/`

### 2. Audit Log Entry

A single JSON object representing one system action.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| timestamp | ISO 8601 datetime | Yes | When the action occurred (UTC) |
| action | string | Yes | Action name (file_detected, inbox_processed, dashboard_updated, pending_approval, move_to_done) |
| input_ref | string | Yes | File or resource that triggered the action |
| outcome | string | Yes | Result (success, error, skipped) |
| duration_ms | integer | Yes | Execution time in milliseconds |
| details | object | No | Additional context (priority, category, counts, etc.) |
| error | string | No | Error message if outcome is "error" |

**Storage**: `Logs/YYYY-MM-DD.audit.jsonl` (one JSON object per line, append-only)

### 3. Deduplication Ledger

A plain text file tracking which files have been processed by the watcher.

| Field | Type | Description |
|-------|------|-------------|
| filename | string | One filename per line (basename only, no path) |

**Storage**: `Logs/.watcher_ledger.txt`
**Behavior**: Loaded into memory `set` at startup. Appended on each new detection. Recreated if missing/corrupted.

### 4. Dashboard

A Markdown document providing at-a-glance vault status.

**Sections**:
- **Quick Status table**: Folder name, count, description (3 rows: Needs_Action, Pending_Approval, Done)
- **Recent Activity**: Last N entries from audit log formatted as `- [HH:MM] action → outcome (input_ref)`

**Storage**: `Dashboard.md` (vault root)

## Relationships

```
Task File --[detected by]--> Watcher --[creates]--> Audit Log Entry
Task File --[processed by]--> Processor --[creates]--> Audit Log Entry
Task File --[summarized in]--> Dashboard
Audit Log Entry --[displayed in]--> Dashboard (Recent Activity)
Deduplication Ledger --[prevents re-detection of]--> Task File
```
