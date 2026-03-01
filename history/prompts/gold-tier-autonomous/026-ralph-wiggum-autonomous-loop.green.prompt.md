---
id: 026
title: Ralph Wiggum Autonomous Loop Implementation
stage: green
date: 2026-02-28
surface: agent
model: claude-opus-4-6
feature: gold-tier-autonomous
branch: 005-gold-tier-autonomous
user: jansher
command: /sp.implement
labels: ["ralph-wiggum", "autonomous-loop", "gold-tier", "reasoning-loop"]
links:
  spec: specs/005-gold-tier-autonomous/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - scripts/ralph_wiggum.py
  - scripts/reasoning_loop.py
  - tests/test_ralph_wiggum.py
  - .claude/skills/ralph-wiggum-loop.md
  - specs/005-gold-tier-autonomous/tasks.md
tests:
  - tests/test_ralph_wiggum.py (37 tests — all pass)
  - tests/test_odoo_mcp.py (33 tests — all pass)
  - tests/test_reasoning_loop.py (31 tests — all pass)
---

## Prompt

Gold Tier: Full Ralph Wiggum Loop for Autonomous Tasks
Target: Add Ralph Wiggum loop for multi-step task completion (Gold Tier requirement)
Focus: Autonomous iteration until Done
Success criteria:
- ralph_wiggum.py: stop hook + re-inject prompt until task complete
- Uses Plan.md + Done folder check
- Integrates with watchers + skills
- Test: Complex task → loop iterates → Done
Constraints:
- Python
- Local-first
What the agent does: Generate ralph_wiggum.py + orchestrator update. End with test commands.

## Response snapshot

Created `scripts/ralph_wiggum.py` with autonomous loop controller. Key components:
- **StopCondition** class: evaluates 7 stop conditions (Done folder, max iterations, timeout, stop file, all steps complete, approval blocked, no progress)
- **LoopController** class: autonomous iteration — create plan → execute steps → check Done → re-inject if not done
- **watch_for_tasks()**: continuous monitoring of Needs_Action/ for new complex tasks
- **get_loop_status()**: reports active plans, pending tasks, Done count
- CLI with --task, --file, --watch, --status, --stop, --clear-stop

Updated test_ralph_wiggum.py from 20 to 37 tests. All 101 tests pass across ralph_wiggum + odoo_mcp + reasoning_loop.

## Outcome

- ✅ Impact: Full autonomous loop implemented — tasks iterate until Done/ or stop condition
- 🧪 Tests: 37/37 pass (17 new tests for StopCondition, LoopController, get_loop_status)
- 📁 Files: 1 created (ralph_wiggum.py), 2 modified (test_ralph_wiggum.py, ralph-wiggum-loop.md skill), 1 updated (tasks.md T034-T041 marked complete)
- 🔁 Next prompts: Orchestrator integration (T042-T046), weekly briefing enhancements (T019-T025)
- 🧠 Reflection: The reasoning_loop.py already had all building blocks — the missing piece was the outer iteration wrapper with stop conditions

## Evaluation notes (flywheel)

- Failure modes observed: None — existing reasoning_loop infrastructure was solid
- Graders run and results (PASS/FAIL): 101/101 PASS
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Add watch mode integration test with mock file creation
