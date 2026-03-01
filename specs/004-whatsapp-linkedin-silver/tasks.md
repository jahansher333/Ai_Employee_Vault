# Tasks: Silver Tier Final Lock — WhatsApp Watcher + LinkedIn Post Skill

**Feature**: 004-whatsapp-linkedin-silver
**Branch**: `004-whatsapp-linkedin-silver`
**Generated**: 2026-02-22

## Phase 1: Setup & Configuration

- [x] **T-001**: Update `requirements.txt` — add `playwright>=1.40.0` and `requests>=2.31.0`
- [x] **T-002**: Update `.env.example` — add WhatsApp + LinkedIn environment variables
- [x] **T-003**: Update `.gitignore` — add Python patterns, session dirs, playwright artifacts
- [x] **T-004**: Create `Approved/` directory for LinkedIn posting workflow
- [x] **T-005**: Update `tests/conftest.py` — add `Approved/` to vault fixture, add WhatsApp/LinkedIn sample data

**Checkpoint**: All config files updated, test fixtures ready.

## Phase 2: Core Scripts

- [x] **T-006**: Create `scripts/whatsapp_watcher.py` — WhatsApp Web monitor with Playwright, ledger dedup, keyword matching, task file creation, CLI args, audit logging
- [x] **T-007**: Create `scripts/linkedin_poster.py` — Draft generation with 3 templates, save to Pending_Approval, approval watcher, simulate/API posting, move to Done, Dashboard social section update, CLI args, audit logging

**Checkpoint**: Both scripts importable, functions match contracts.

## Phase 3: Agent Skills

- [x] **T-008**: Create `.claude/skills/whatsapp-message-parser.md` — Skill definition for WhatsApp message parsing
- [x] **T-009**: Create `.claude/skills/linkedin-poster.md` — Skill definition for LinkedIn post drafting

**Checkpoint**: Skills readable, reference correct scripts and functions.

## Phase 4: Integration Updates

- [x] **T-010**: Update `scripts/update_dashboard.py` — add `build_social_posts_table()`, social posts markers, Approved folder count, WhatsApp watcher status
- [x] **T-011**: Update `scripts/process_inbox.py` — add `whatsapp` type handling in action plan generation

**Checkpoint**: Dashboard shows social posts section, process_inbox handles whatsapp type.

## Phase 5: Tests

- [x] **T-012**: Create `tests/test_whatsapp_watcher.py` — unit tests for ledger, hashing, keyword matching, task file creation
- [x] **T-013**: Create `tests/test_linkedin_poster.py` — unit tests for draft generation, template validation, save/publish, dashboard update

**Checkpoint**: All tests pass with `pytest tests/ -v`.

## Phase 6: Documentation & Polish

- [x] **T-014**: Update `README.md` — add WhatsApp + LinkedIn sections, updated tier status, test steps, vault structure

## Phase 7: Reasoning Loop + Scheduling Integration

- [x] **T-015**: Create `scripts/reasoning_loop.py` — complexity detection, Plan.md creation, step execution, approval routing
- [x] **T-016**: Create `.claude/skills/reasoning-loop.md` — Agent skill definition
- [x] **T-017**: Update `scripts/process_inbox.py` — route complex tasks to reasoning loop
- [x] **T-018**: Update `scripts/update_dashboard.py` — add Active Plans section
- [x] **T-019**: Create `tests/test_reasoning_loop.py` — 31 tests for reasoning loop

**Checkpoint**: Complex tasks create Plan.md, simple tasks use direct planning. 165 tests pass.

## Phase 8: Weekly CEO Briefing + Scheduling

- [x] **T-020**: Create `scripts/weekly_briefing.py` — financial summary, task stats, bottleneck detection, briefing generation, scheduler loop
- [x] **T-021**: Create `.claude/skills/ceo-briefing.md` — Agent skill definition
- [x] **T-022**: Update `scripts/update_dashboard.py` — add Recent Briefings section
- [x] **T-023**: Create `tests/test_weekly_briefing.py` — 18 tests for weekly briefing

**Checkpoint**: Briefings generated with Executive Summary, Financial Overview, Task Pipeline, Bottlenecks. 183 tests pass.

## Phase 9: Orchestrator + Final Integration

- [x] **T-024**: Create `scripts/orchestrator.py` — single entry point for all components with health monitoring
- [x] **T-025**: Create `.claude/skills/orchestrator.md` — Agent skill definition
- [x] **T-026**: Create `tests/test_orchestrator.py` — component list, validation, health check tests
- [x] **T-027**: Update `README.md` — orchestrator docs, updated tier status, vault structure, scripts/skills tables

**Checkpoint**: All Silver Tier features complete. 11 Agent Skills. Full test suite passes.
