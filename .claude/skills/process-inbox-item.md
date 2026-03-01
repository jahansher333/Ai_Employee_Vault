# Skill: Process Inbox Item

## Purpose
Read a task file from `Needs_Action/`, analyze its content, generate an
action plan, and move the processed item to `Done/`.

## Trigger
Called when the watcher detects a new file in `Needs_Action/`.

## Steps

1. **Read the task file** from `Needs_Action/<filename>.md`
2. **Parse frontmatter** — extract type, priority, category, status
3. **Analyze the content** — understand what is being asked
4. **Check for sensitive actions** — if found, route to `Pending_Approval/`
5. **Generate action plan** — structured steps to address the task
6. **Write action plan** — save to the same file or create a companion plan file
7. **Update status** — change frontmatter status to "planned"
8. **Log the action** — write audit entry to `Logs/`

## Input Format
```markdown
---
type: task
priority: high | medium | low
category: research | draft | review | organize | analyze
status: new
---

# Task Title

Description of what needs to be done.
```

## Output Format
The processed file gets an action plan appended:
```markdown
---
type: task
priority: high
category: research
status: planned
processed_at: 2026-02-17T10:30:00Z
---

# Task Title

Description of what needs to be done.

## Action Plan

1. Step one
2. Step two
3. Step three

## Estimated Effort
30 minutes

## Dependencies
- None identified
```

## Sensitive Action Detection
If the task contains keywords like "payment", "send email", "delete",
"external api", or "credentials", the item is routed to `Pending_Approval/`
instead of being processed directly.

## Audit Log Entry
```json
{
  "action": "inbox_processed",
  "input_ref": "filename.md",
  "outcome": "success",
  "details": {"priority": "high", "category": "research"}
}
```
