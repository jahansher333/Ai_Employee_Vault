# Reasoning Loop Skill

## Purpose

When a task in `Needs_Action/` is complex (multi-step, high-priority, involves invoices/payments/workflows), create a structured `PLAN_*.md` in `Plans/` with checkboxed steps, then execute the plan step by step.

## Trigger

- Claude detects a complex task (2+ complexity signals: keywords, multiple action verbs, high priority, long content, numbered steps, cross-references)
- User explicitly requests: "create a plan for this task"
- `process_inbox.py` routes complex tasks here automatically

## Steps

1. **Read the task file** from `Needs_Action/` — parse frontmatter and body
2. **Assess complexity** using `reasoning_loop.detect_complexity()`:
   - Checks for complexity keywords (invoice, payment, deploy, integrate, etc.)
   - Counts unique action verbs (3+ = multi-step)
   - Checks priority level, content length, numbered steps, cross-references
   - Threshold: 2+ signals = complex
3. **Create Plan** in `Plans/PLAN_{HHMMSS}_{title-slug}.md`:
   - Frontmatter: type, source_file, objective, priority, status, timestamps, step counts
   - Body: objective, checkboxed steps, dependencies, execution log table
   - Steps are type-aware (email, whatsapp, invoice, generic)
4. **Execute non-approval steps** automatically:
   - Mark each step `[X]` as completed
   - Add execution log entry with timestamp
5. **Route to approval** when an approval-requiring step is reached:
   - Create `approve-PLAN_*.md` in `Pending_Approval/`
   - Set plan status to `awaiting_approval`
   - Stop execution until human approves
6. **Complete plan** when all steps are done:
   - Move plan to `Done/`
   - Move source task to `Done/`
   - Log completion

## Input Format

Task file in `Needs_Action/` with YAML frontmatter:

```yaml
---
type: email|whatsapp|task
priority: high|medium|low
status: new
---
```

## Output Format

Plan file in `Plans/`:

```yaml
---
type: plan
source_file: "TASK_123.md"
objective: "Handle invoice request"
priority: high
status: active|awaiting_approval|completed|done
total_steps: 7
completed_steps: 3
---
```

## CLI Commands

```bash
# Check complexity without creating a plan
python scripts/reasoning_loop.py --check Needs_Action/task.md

# Process a specific task through the reasoning loop
python scripts/reasoning_loop.py --file Needs_Action/task.md

# Execute steps in an existing plan
python scripts/reasoning_loop.py --execute Plans/PLAN_123_task.md

# Execute a specific step
python scripts/reasoning_loop.py --execute Plans/PLAN_123_task.md --step 3

# Resume all active plans
python scripts/reasoning_loop.py --run-plans
```

## Audit Log Entries

- `plan_created` — New plan file generated
- `plan_step_executed` — Individual step completed
- `plan_approval_requested` — Approval-requiring step reached
- `plan_completed` — All steps done, moved to Done

## Integration Points

- **process_inbox.py**: Complex tasks are automatically routed to reasoning loop
- **update_dashboard.py**: Active Plans section shows current plan status
- **Pending_Approval/**: Approval-requiring steps create approval files here
- **Done/**: Completed plans and their source tasks are moved here
