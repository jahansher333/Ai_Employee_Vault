# Skill: SimpleTaskReaderSkill

## Purpose
Read a task file from Needs_Action/, parse its frontmatter, generate a clean Markdown summary table row, and append it to Dashboard.md.

## Trigger
When a new `.md` file is detected in `Needs_Action/` by the watcher, or when manually invoked on a specific file.

## Input
- File path to a `.md` task file in `Needs_Action/`
- The file should contain YAML frontmatter with: type, priority, category, status
- The file body should contain a Markdown heading as the task title

## Steps
1. Read the task file from `Needs_Action/`
2. Parse YAML frontmatter to extract type, priority, category, status
3. Extract the first `# Heading` as the task title (preview)
4. Generate a summary table row: `| Filename | Preview | Time | Priority |`
5. Append the row to Dashboard.md between `<!-- START_PENDING_TASKS -->` and `<!-- END_PENDING_TASKS -->` markers
6. If the task contains sensitive keywords (payment, password, credential, delete, remove, api key), route to `Pending_Approval/` instead
7. Otherwise, generate an action plan and update the file status to `planned`
8. Log the action to `Logs/YYYY-MM-DD.audit.jsonl`

## Output
- Dashboard.md updated with new summary row in the Pending Tasks table
- Task file updated with status `planned` and an appended Action Plan section
- Audit log entry created

## Summary Table Format

```markdown
| Filename | Preview | Time | Priority |
|----------|---------|------|----------|
| task-file.md | Review Q3 Report | 14:30 | high |
```

## Error Handling
- Missing frontmatter: Use defaults (type: task, priority: medium, category: general, status: new)
- Missing Dashboard.md: Skip dashboard update, log warning
- File already processed (status != new): Skip silently
- Sensitive content detected: Route to Pending_Approval/, do not process
