---
id: 025
title: Gold tier task generation
stage: tasks
date: 2026-02-24
surface: agent
model: claude-opus-4-6
feature: 005-gold-tier-autonomous
branch: 005-gold-tier-autonomous
user: jansher
command: /sp.tasks
labels: ["gold-tier", "tasks", "task-breakdown", "implementation-plan"]
links:
  spec: specs/005-gold-tier-autonomous/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/005-gold-tier-autonomous/tasks.md
tests:
  - null
---

## Prompt

Gold Tier: Autonomous Employee – Full Requirements
Generate prioritized task list from plan.
Format: Markdown checkboxes with [P1], [P2] labels.
Include:
- [P1] Install Odoo Community locally (self-hosted) + setup MCP for JSON-RPC
- [P1] Create OdooIntegrationSkill (draft invoices/expenses via MCP)
- [P2] Add Facebook + Instagram + Twitter (X) post skills (draft → approval → MCP)
- [P2] Implement Weekly Audit + CEOBriefingSkill (revenue, bottlenecks, suggestions)
- [P3] Full Ralph Wiggum Loop: autonomous task iteration until Done
- [P3] Multiple MCP servers: email + social + Odoo
- [P3] Error recovery + graceful degradation + audit logging
- [P4] Update README.md + architecture diagram (text/ASCII)
End with /sp.check confirming all Gold requirements met.

## Response snapshot

Generated `specs/005-gold-tier-autonomous/tasks.md` with 54 tasks across 10 phases:

- **Phase 1 (Setup)**: 3 tasks — dependencies, .env, .gitignore
- **Phase 2 (Foundational)**: 2 tasks — error recovery module + tests
- **Phase 3 (US1 Odoo)**: 5 tasks — OdooClient class, session handling, CLI, tests, skill
- **Phase 4 (US2 Social)**: 8 tasks — Facebook/Instagram/Twitter adapters, char limits, API stubs, Dashboard table, tests, skill
- **Phase 5 (US3 Weekly Audit)**: 7 tasks — Odoo financials, social activity, WoW comparison, health status, overdue invoices, tests
- **Phase 6 (US4 MCP Servers)**: 8 tasks — 3 MCP servers (odoo, social, email), error responses, 3 test files, settings.json
- **Phase 7 (US5 Ralph Wiggum)**: 8 tasks — cross-domain detection, domain tags, retry logic, circular deps, metrics, tests, skill
- **Phase 8 (US6 Error Recovery)**: 5 tasks — orchestrator Gold components, health tracking, auto-restart, tests
- **Phase 9 (US7 Architecture)**: 2 tasks — ARCHITECTURE.md with ASCII diagram
- **Phase 10 (Polish)**: 6 tasks — Dashboard, README, self-test, full suite verification

Key metrics: 20 parallel-eligible tasks, 8 new test files, 6 new scripts, 3 new agent skills, target 250+ total tests.

## Outcome

- ✅ Impact: Complete task breakdown for Gold Tier — 54 tasks organized by user story with dependencies and parallel opportunities
- 🧪 Tests: No tests (task generation phase)
- 📁 Files: 1 created (tasks.md)
- 🔁 Next prompts: `/sp.implement` to begin execution starting with Phase 1 Setup
- 🧠 Reflection: Tasks organized by user story enable MVP delivery (Odoo client alone is valuable) and parallel execution of independent stories (US1, US2, US5 can run in parallel).

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): Format validation — all 54 tasks follow [ID] [P?] [Story?] Description pattern
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Execute Phase 1 + Phase 2, then Phase 3 (US1 Odoo) as MVP
