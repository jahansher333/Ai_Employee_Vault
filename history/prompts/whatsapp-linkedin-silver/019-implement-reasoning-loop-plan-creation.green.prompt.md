---
id: 019
title: Implement reasoning loop plan creation
stage: green
date: 2026-02-24
surface: agent
model: claude-opus-4-6
feature: 004-whatsapp-linkedin-silver
branch: 004-whatsapp-linkedin-silver
user: jansher
command: /sp.implement
labels: ["reasoning-loop", "plan-creation", "silver-tier", "multi-step"]
links:
  spec: specs/004-whatsapp-linkedin-silver/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - scripts/reasoning_loop.py
  - .claude/skills/reasoning-loop.md
  - scripts/process_inbox.py
  - scripts/update_dashboard.py
  - tests/test_reasoning_loop.py
  - tests/conftest.py
  - tests/test_process_inbox.py
tests:
  - tests/test_reasoning_loop.py (31 tests - all pass)
  - tests/ (165 total tests - all pass)
---

## Prompt

Silver Tier: Add Claude Reasoning Loop for Plan.md Creation
Target: Add reasoning loop that creates Plan.md files (Silver Tier requirement)
Focus: Claude multi-step reasoning with Plan.md
Success criteria:
- ReasoningLoopSkill: when task is complex (e.g., "handle invoice request"), creates /Plans/PLAN_*.md
- File content: objective, steps (checkboxes), dependencies, estimated time
- Claude reads Plan.md -> executes steps -> updates to Done or Pending_Approval
- Integrates with existing watchers + approval workflow
- Update Dashboard.md with "Active Plans" section
- Test: Simulate complex task -> Plan.md created -> loop executes steps
Constraints:
- All as Agent Skill
- Local-first, no external calls in loop
What the agent does: Generate ReasoningLoopSkill.yaml + update to orchestrator/watcher. End with test commands.

## Response snapshot

Implemented the Claude Reasoning Loop as a complete feature with 5 files created/modified:

1. **scripts/reasoning_loop.py** (core engine): Complexity detection (20 keywords, multi-action verbs, priority, content length, numbered steps, cross-references — threshold of 2 signals), Plan.md creation in Plans/ with checkboxed steps, step execution with completion tracking, approval routing for sensitive steps, plan completion moving to Done/.

2. **.claude/skills/reasoning-loop.md**: Agent skill definition with CLI commands, trigger conditions, step-by-step procedure, I/O formats, and audit log entries.

3. **scripts/process_inbox.py** (modified): Added import of reasoning_loop, complexity check after sensitivity gate — complex tasks routed to reasoning loop instead of simple action plans. Added "plan_created" to skip statuses and results counter.

4. **scripts/update_dashboard.py** (modified): Added Active Plans section with START_PLANS/END_PLANS markers, build_plans_table() function, Plans folder count in Quick Status, updated folder structure and How It Works sections.

5. **tests/test_reasoning_loop.py** (31 tests): Coverage for complexity detection (7), plan creation (6), step execution (5), plan reading (2), plan completion (3), approval routing (2), full orchestrator (3), helpers (3).

All 165 tests pass across the full suite.

## Outcome

- Impact: Silver Tier reasoning loop complete — complex tasks auto-generate structured plans with step-by-step execution
- Tests: 165/165 pass (31 new reasoning loop tests)
- Files: 3 new, 4 modified
- Next prompts: End-to-end integration test with real complex task, MCP server implementation
- Reflection: Clean integration with existing process_inbox pipeline via complexity gating; one existing test needed updating due to new routing behavior

## Evaluation notes (flywheel)

- Failure modes observed: One existing test assumed high-priority review task would get simple plan; now correctly routed to reasoning loop
- Graders run and results (PASS/FAIL): pytest 165/165 PASS
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Add configurable complexity threshold via env var
