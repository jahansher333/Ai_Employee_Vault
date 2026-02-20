# Skill: Generate Status Report

## Purpose
Read the current state of all vault folders and update `Dashboard.md`
with current counts and recent activity.

## Steps

1. **Count files** in each folder:
   - `Needs_Action/*.md` — pending tasks
   - `Pending_Approval/*.md` — awaiting human review
   - `Done/*.md` — completed items
2. **Read recent audit logs** from `Logs/` (today's file)
3. **Update Dashboard.md** — replace the Quick Status table and
   Recent Activity section with current data
4. **Log the action** — write audit entry

## Dashboard Update Format
Replace the Quick Status table:
```markdown
| Folder | Count | Description |
|--------|-------|-------------|
| Needs_Action | 3 | Items waiting for AI processing |
| Pending_Approval | 1 | Sensitive actions needing human review |
| Done | 12 | Completed items |
```

Replace the Recent Activity section with last 5 log entries:
```markdown
## Recent Activity

- [10:30] inbox_processed → success (task-review-report.md)
- [10:28] file_detected → success (task-review-report.md)
- [09:15] item_moved_done → success (task-draft-email.md)
```

## Audit Log Entry
```json
{
  "action": "dashboard_updated",
  "input_ref": "Dashboard.md",
  "outcome": "success"
}
```
