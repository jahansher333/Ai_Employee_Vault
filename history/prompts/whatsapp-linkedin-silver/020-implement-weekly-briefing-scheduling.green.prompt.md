---
id: 020
title: Implement weekly briefing scheduling
stage: green
date: 2026-02-24
surface: agent
model: claude-opus-4-6
feature: 004-whatsapp-linkedin-silver
branch: 004-whatsapp-linkedin-silver
user: jansher
command: /sp.implement
labels: ["weekly-briefing", "ceo-briefing", "scheduling", "silver-tier"]
links:
  spec: specs/004-whatsapp-linkedin-silver/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - scripts/weekly_briefing.py
  - .claude/skills/ceo-briefing.md
  - scripts/update_dashboard.py
  - tests/test_weekly_briefing.py
  - README.md
tests:
  - tests/test_weekly_briefing.py
---

## Prompt

Silver Tier: Add Basic Scheduling via Cron or Task Scheduler
Target: Add basic scheduling (Silver Tier requirement)
Focus: Cron/Task Scheduler for periodic tasks
Success criteria:
- Scheduling script: schedule_weekly_briefing.py or cron setup
- Runs every Sunday 8 PM PKT: triggers CEOBriefingSkill (revenue summary, bottlenecks)
- Creates /Briefings/YYYY-MM-DD_Monday_Briefing.md
- Integrates with existing analytics skill + Dashboard update
- Instructions for Windows Task Scheduler or cron (Linux/Mac)
- Update README.md with scheduling setup
- Test: Manual run → briefing file created → Dashboard updated
Constraints:
- Python + schedule library or system cron
- Local-first
What the agent does: Generate schedule_weekly_briefing.py + README scheduling section. End with test commands.

## Response snapshot

Implemented the Weekly CEO Briefing system with full scheduling support:

1. **`scripts/weekly_briefing.py`** (~300 lines) — Core briefing generator with:
   - `collect_financial_summary()` — Integrates with data_analyzer for revenue/expenses/anomalies
   - `collect_task_stats()` — Counts across all vault folders
   - `collect_bottlenecks()` — Detects stale tasks >48h, pending approvals >24h, blocked plans, errors
   - `generate_briefing()` — Creates `Briefings/YYYY-MM-DD_Monday_Briefing.md` with Executive Summary, Financial Overview, Task Pipeline, Bottlenecks & Risks, Recommended Actions
   - `run_scheduler()` — Built-in loop checking every 60s for Sunday 8 PM PKT
   - `_fmt_currency()` — Helper for financial formatting
   - CLI: `--schedule` for continuous loop, default for one-shot

2. **`.claude/skills/ceo-briefing.md`** — Agent skill with Windows Task Scheduler and cron setup instructions

3. **`scripts/update_dashboard.py`** — Added Recent Briefings section with `build_briefings_table()` and `<!-- START_BRIEFINGS -->` markers

4. **`README.md`** — Added Weekly CEO Briefing feature description, Section 7 with scheduling setup (Windows Task Scheduler + cron), Test 6, updated vault structure/scripts/skills tables

5. **`tests/test_weekly_briefing.py`** — 18 tests covering task stats, bottleneck detection, briefing generation, dashboard integration, currency formatting

All 183 tests pass (165 existing + 18 new).

## Outcome

- ✅ Impact: Weekly CEO Briefing system fully operational with one-shot and scheduled modes
- 🧪 Tests: 18 new tests, 183 total — all PASS
- 📁 Files: 2 created, 3 modified
- 🔁 Next prompts: MCP server implementation (from earlier plan)
- 🧠 Reflection: Reused existing patterns (frontmatter, audit logging, dashboard markers) for consistency. Built-in scheduler avoids external dependency while documenting Task Scheduler/cron for production use.

## Evaluation notes (flywheel)

- Failure modes observed: None — clean implementation building on established patterns
- Graders run and results (PASS/FAIL): pytest 183/183 PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Add email delivery of briefing PDF
