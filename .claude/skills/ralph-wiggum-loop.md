# Ralph Wiggum Loop Skill

## Purpose
Autonomous multi-step task execution with cross-domain detection, retry logic, and execution metrics. Creates structured Plan.md files, iterates until tasks reach Done/, and tracks progress.

## When to Use
- Complex task needs structured breakdown into steps
- Task spans multiple domains (accounting, social, email, reporting)
- User says "create a plan for..." or "process this complex task"
- Need autonomous iteration until a task is complete
- Need to resume execution of active plans
- Need to watch for new complex tasks

## Commands

### Autonomous Loop (ralph_wiggum.py)
```bash
# Run autonomous loop on a task description
python scripts/ralph_wiggum.py --task "Process the Q3 invoice audit"

# Run autonomous loop on a file
python scripts/ralph_wiggum.py --file Needs_Action/complex-task.md

# Watch for new complex tasks (runs continuously)
python scripts/ralph_wiggum.py --watch

# Set max iterations and timeout
python scripts/ralph_wiggum.py --file Needs_Action/task.md --max-iterations 5 --timeout 120

# Show loop status (active plans, pending tasks, Done count)
python scripts/ralph_wiggum.py --status

# Create stop signal (stops all running loops)
python scripts/ralph_wiggum.py --stop

# Clear stop signal
python scripts/ralph_wiggum.py --clear-stop
```

### Reasoning Loop (reasoning_loop.py)
```bash
# Check if a task is complex enough for planning
python scripts/reasoning_loop.py --check Needs_Action/task.md

# Process a task through the reasoning loop (single pass)
python scripts/reasoning_loop.py --file Needs_Action/complex-task.md

# Execute steps in an existing plan
python scripts/reasoning_loop.py --execute Plans/PLAN_123456_task.md

# Execute a specific step
python scripts/reasoning_loop.py --execute Plans/PLAN_123456_task.md --step 3

# Resume all active plans
python scripts/reasoning_loop.py --run-plans
```

## Gold Tier Features
- **Autonomous iteration**: Loop continues until task reaches Done/ or stop condition
- **Stop conditions**: Max iterations, timeout, stop file, all steps complete, task in Done/
- **Cross-domain detection**: Identifies tasks spanning accounting, social, email, reporting
- **Domain-tagged steps**: Each step tagged with its domain for isolation
- **Per-step retry**: Failed steps get one automatic retry before marking failed
- **Circular dependency detection**: Validates no cycles at plan creation time
- **Execution metrics**: Tracks steps_completed, steps_failed, retries, elapsed_seconds, domains_touched
- **Independent step continuation**: When a step fails, independent steps still execute
- **Watch mode**: Monitors Needs_Action/ for new complex tasks
- **History tracking**: Full iteration history for debugging

## Stop Conditions
| Condition | Trigger |
|-----------|---------|
| `task_in_done` | Task file found in Done/ folder |
| `all_steps_complete` | All plan steps marked [X] |
| `max_iterations` | Iteration count >= max (default: 10) |
| `timeout` | Elapsed time >= timeout (default: 300s) |
| `stop_file` | Plans/.stop file exists |
| `awaiting_approval` | All remaining steps need human approval |
| `no_progress` | Iteration executed 0 steps (stuck) |

## Supported Domains
| Domain | Keywords |
|--------|----------|
| Accounting | invoice, payment, expense, revenue, odoo, financial |
| Social | facebook, instagram, twitter, linkedin, post, publish |
| Email | email, gmail, inbox, reply, send, unread |
| Reporting | report, briefing, dashboard, summary, audit, weekly |

## Workflow
1. **Detect** complexity (score >= 2 signals)
2. **Create** Plan.md with domain-tagged steps
3. **Execute** steps with retry logic
4. **Pause** at approval-required steps (HITL)
5. **Continue** with independent steps
6. **Check** Done/ folder — if task moved there, stop
7. **Re-inject** — if not done, iterate again (go to step 3)
8. **Complete** when all steps done → move to Done/

## Audit Trail
All operations logged to `Logs/*.audit.jsonl` with actions:
- `ralph_wiggum_start` — loop started
- `ralph_wiggum_plan_created` — plan file generated
- `ralph_wiggum_iteration_done` — iteration completed
- `ralph_wiggum_stop` — loop stopped with reason
- `ralph_wiggum_completed` — task moved to Done/
- `plan_step_executed` — individual step executed
- `plan_step_retry` — step retried after failure
