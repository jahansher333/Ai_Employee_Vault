# Skill: Check Pending Approvals

## Purpose
Scan `Pending_Approval/` for items that have been approved or rejected
by the human operator, and take the appropriate action.

## Steps

1. **List all files** in `Pending_Approval/`
2. **Read each file** and parse the `status` field from frontmatter
3. **For approved items**:
   - Execute the originally requested action (within Bronze Tier limits)
   - Move the approval file to `Done/`
   - Log: `approval_executed`
4. **For rejected items**:
   - Move the approval file to `Done/` with `status: rejected`
   - Log: `approval_rejected`
5. **For pending items**:
   - Skip (still waiting for human review)
   - Log: `approval_pending` (only on verbose runs)

## Frontmatter Status Values
- `pending` — waiting for human review (default)
- `approved` — human approved the action
- `rejected` — human rejected the action

## Audit Log Entry
```json
{
  "action": "approval_checked",
  "input_ref": "approve-filename.md",
  "outcome": "success",
  "details": {"decision": "approved", "original_task": "filename.md"}
}
```
