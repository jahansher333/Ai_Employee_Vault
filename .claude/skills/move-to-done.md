# Skill: Move to Done

## Purpose
Move a completed task from `Needs_Action/` to `Done/` with a completion
timestamp added to the frontmatter.

## Steps

1. **Read the file** from `Needs_Action/<filename>.md`
2. **Add completion metadata** to frontmatter:
   - `status: done`
   - `completed_at: <ISO 8601 timestamp>`
3. **Write to Done/** — save the updated file in the `Done/` folder
4. **Delete the original** from `Needs_Action/`
5. **Log the action** — write audit entry

## Safety
- Always write to `Done/` FIRST, then verify, then delete from `Needs_Action/`
- If the write fails, do NOT delete the original
- If filename conflict in Done/, append a timestamp suffix

## Audit Log Entry
```json
{
  "action": "item_moved_done",
  "input_ref": "filename.md",
  "outcome": "success",
  "details": {"source": "Needs_Action/", "destination": "Done/"}
}
```
