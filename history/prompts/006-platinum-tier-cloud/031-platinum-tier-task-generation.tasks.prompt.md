---
id: 031
title: Platinum Tier Task Generation
stage: tasks
date: 2026-03-01
surface: agent
model: claude-opus-4-6
feature: 006-platinum-tier-cloud
branch: 006-platinum-tier-cloud
user: CEO
command: /sp.tasks
labels: ["platinum", "tasks", "cloud", "zone-config", "vault-sync", "odoo", "a2a", "demo"]
links:
  spec: specs/006-platinum-tier-cloud/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/006-platinum-tier-cloud/tasks.md
tests:
  - none
---

## Prompt

Platinum Tier: Always-On Cloud + Local Executive
Generate prioritized task list from plan.
Format: Markdown checkboxes with [P1], [P2] labels.
Include:
- [P1] Oracle Cloud Free  VM not money and not card check free in internet setup + deploy watchers/orchestrator
- [P1] Work-Zone Specialization: Cloud drafts + Local execution config
- [P2] Synced Vault: Git setup (push/pull cron), /domain/ folders, claim-by-move rule
- [P2] Odoo Cloud Deploy: VM install, HTTPS nginx, backups pg_dump cron, health watchdog
- [P3] Cloud MCP for Odoo drafts + Local approval integration
- [P3] Optional A2A Phase 2: direct messages (socket API, vault audit)
- [P4] Platinum demo test script + README update
End with /sp.check confirming all Platinum requirements met.

## Response snapshot

Generated 51 tasks across 10 phases covering all 7 user stories. Key phases: Setup (8 tasks), Foundation/Zone Config (4 tasks), Work-Zone Specialization (7 tasks), Vault Sync (6 tasks), Cloud Deployment (5 tasks), Vault Delegation (3 tasks), Odoo Cloud (6 tasks), Local Approval (3 tasks), A2A Optional (4 tasks), Demo+Self-Test (5 tasks). 31 of 51 tasks are parallelizable. Dependency graph ensures Foundation blocks all user stories. MVP path covers Phases 1-5. Each phase has checkpoint criteria.

## Outcome

- ✅ Impact: Complete task list ready for /sp.implement execution
- 🧪 Tests: Test tasks included in Phases 2, 4, 5, 9, 10
- 📁 Files: 1 file created (tasks.md)
- 🔁 Next prompts: /sp.implement to begin execution, or /sp.analyze for cross-artifact consistency check
- 🧠 Reflection: 51 tasks is substantial but each is specific with exact file paths. Parallel opportunities (31 tasks) significantly reduce wall-clock time. MVP at Phase 5 delivers core Platinum value.

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): Format validation PASS — all tasks have checkbox, ID, labels, file paths
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Proceed to implementation
