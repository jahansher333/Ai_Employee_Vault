---
id: 008
title: Bronze Foundation Implementation Plan
stage: plan
date: 2026-02-17
surface: agent
model: claude-opus-4-6
feature: bronze-foundation
branch: 002-bronze-foundation
user: user
command: /sp.plan
labels: ["plan", "bronze-foundation", "watchdog", "watcher", "vault", "architecture"]
links:
  spec: specs/002-bronze-foundation/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-bronze-foundation/plan.md
  - specs/002-bronze-foundation/research.md
  - specs/002-bronze-foundation/data-model.md
  - specs/002-bronze-foundation/quickstart.md
  - specs/002-bronze-foundation/contracts/watcher.md
  - specs/002-bronze-foundation/contracts/processor.md
  - specs/002-bronze-foundation/contracts/audit_logger.md
  - specs/002-bronze-foundation/contracts/dashboard.md
tests:
  - Constitution Check: 6/6 PASS
---

## Prompt

Bronze Tier: Foundation (Exact Document Requirements)
Use specs from previous phase.
Success criteria:
- Watcher: watcher.py monitors /Needs_Action using watchdog
- On new .md file: log to /Logs/watcher.log + trigger skill
- Skill: SimpleTaskReaderSkill creates Markdown summary and appends to Dashboard.md
- README.md: setup, run watcher, test steps
- Test: watcher running → drop .md file → log + Dashboard update
Tech stack: Python, watchdog
What the agent does: Output plan.md with flow, skill template, README outline. Ready for /sp.tasks.

## Response snapshot

Created complete implementation plan for Bronze Tier Foundation. Key artifacts: (1) plan.md — architecture flow (watchdog Observer → processor → dashboard), project structure, constitution check 6/6 PASS, agent skill template, README outline; (2) research.md — 7 decisions (watchdog with PatternMatchingEventHandler, text ledger dedup, JSONL audit, template dashboard regen, keyword sensitive detection, Markdown skills); (3) data-model.md — 4 entities (Task File with state machine, Audit Log Entry, Dedup Ledger, Dashboard); (4) quickstart.md — end-to-end test scenario; (5) 4 contracts (watcher, processor, audit_logger, dashboard). Updated CLAUDE.md agent context with Python 3.11+ and watchdog.

## Outcome

- ✅ Impact: Complete implementation plan with architecture, contracts, data model, and quickstart
- 🧪 Tests: Constitution Check 6/6 PASS
- 📁 Files: 8 files created (plan.md, research.md, data-model.md, quickstart.md, 4 contracts)
- 🔁 Next prompts: /sp.tasks to generate task breakdown, then /sp.implement
- 🧠 Reflection: Key upgrade from 001-bronze-tier: using watchdog library for real event-driven file monitoring instead of manual polling loop. Architecture flow diagram clarifies watcher→processor→dashboard pipeline.

## Evaluation notes (flywheel)

- Failure modes observed: None — all scripts ran successfully, all constitution gates pass.
- Graders run and results (PASS/FAIL): Constitution Check 6/6 PASS.
- Prompt variant (if applicable): User explicitly requested watchdog library (replacing polling from previous implementation).
- Next experiment (smallest change to try): Generate tasks.md and validate cross-artifact consistency with /sp.analyze.
