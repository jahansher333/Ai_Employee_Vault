# Tasks: Gold Tier — Autonomous Employee

**Input**: Design documents from `specs/005-gold-tier-autonomous/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/
**Silver Tier**: 233 tests passing, 11 scripts, 11 agent skills

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1–US7) from spec.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Update dependencies, environment configuration, and shared utilities

- [x] T001 Add Gold Tier dependencies to requirements.txt (tweepy, facebook-sdk — optional)
- [x] T002 [P] Update .env.example with Odoo + social platform environment variables
- [x] T003 [P] Update .gitignore with Gold Tier patterns (odoo session files, social tokens)

**Checkpoint**: Dependencies installable, .env.example documents all Gold Tier variables

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core utilities that multiple Gold Tier features depend on

**⚠️ CRITICAL**: US1–US7 depend on these completing first

- [x] T004 Create error recovery utility `safe_call()` and `ServiceHealth` class in scripts/error_recovery.py
- [x] T005 [P] Create tests/test_error_recovery.py with tests for safe_call, health status transitions, fallback chains

**Checkpoint**: Error recovery module tested and importable by all Gold Tier scripts

---

## Phase 3: User Story 1 — Odoo Accounting Integration (Priority: P1) 🎯 MVP

**Goal**: Connect to self-hosted Odoo Community, read invoices/journal entries/account balances, detect overdue invoices, CSV fallback when Odoo unavailable

**Independent Test**: Configure Odoo credentials → run `python scripts/odoo_client.py --test` → verify invoice data returned (or mock data in tests)

### Implementation for User Story 1

- [x] T006 [US1] Create scripts/odoo_mcp.py with OdooXmlRpcClient class: authenticate(), search_read(), list_invoices(), get_account_balances(), get_overdue_invoices(), get_financial_summary(), create_draft_invoice(), create_draft_expense() — XML-RPC via xmlrpc.client
- [x] T007 [US1] Add Odoo session expiry detection and automatic re-authentication in scripts/odoo_mcp.py
- [x] T008 [US1] Add CLI to scripts/odoo_mcp.py (--test, --setup-check, --list-dbs, --invoices, --overdue, --summary, --create-draft)
- [x] T009 [P] [US1] Create tests/test_odoo_mcp.py with mocked XML-RPC responses: auth success/failure, uid=None/False, list invoices, overdue detection, session expiry re-auth, connection refused, draft invoice creation (33 tests)
- [x] T010 [P] [US1] Create .claude/skills/odoo-draft-invoice.md agent skill definition with HITL approval flow

**Checkpoint**: `python -m pytest tests/test_odoo_client.py -v` passes. OdooClient can authenticate, read invoices, detect overdue, and handle connection errors.

---

## Phase 4: User Story 2 — Social Media Posting (Priority: P1)

**Goal**: Generate platform-appropriate drafts for Facebook, Instagram, Twitter/X. Save to Pending_Approval/ with platform prefixes. Publish approved posts. Social activity summary for briefing.

**Independent Test**: Run `--draft` per platform → verify files in Pending_Approval/ → move to Approved/ → run `--publish` → verify in Done/

### Implementation for User Story 2

- [x] T011 [US2] scripts/social_poster.py with platform adapters: generate_facebook_draft(), generate_instagram_draft(), generate_twitter_draft(), save_social_draft(), publish_social_post() + Playwright posting
- [x] T012 [US2] Twitter 280-char limit enforcement at draft time with truncation warning
- [x] T013 [US2] Instagram caption-focused drafts with hashtag suggestions
- [x] T014 [US2] Real API mode stubs for Facebook (Graph API), Instagram (Graph API), Twitter (API v2) + Playwright mode for FB/IG
- [x] T015 [US2] CLI: --draft, --platform, --publish, --summary, --dashboard, --fb-setup, --ig-setup
- [x] T016 [US2] build_multi_platform_social_table() for Dashboard multi-platform social section
- [x] T017 [P] [US2] tests/test_social_poster.py — 70 tests: drafts, char limits, naming, publish, summary, Playwright, session checks, social table
- [x] T018 [P] [US2] .claude/skills/social-poster.md agent skill definition

**Checkpoint**: `python -m pytest tests/test_social_poster.py -v` passes. Drafts generated for all 3 platforms with correct prefixes and limits.

---

## Phase 5: User Story 3 — Weekly Business and Accounting Audit (Priority: P1)

**Goal**: Enhanced weekly audit with Odoo financial data, social media activity summary, week-over-week comparison, and health status

**Independent Test**: Run `python scripts/weekly_briefing.py` → verify briefing contains Odoo section, social section, WoW comparison, health status

### Implementation for User Story 3

- [x] T019 [US3] Add collect_odoo_financials() to scripts/weekly_briefing.py — pulls from OdooClient, falls back to CSV
- [x] T020 [US3] Add collect_social_activity() to scripts/weekly_briefing.py — counts posts per platform from vault folders (LinkedIn + Facebook + Instagram + Twitter)
- [x] T021 [US3] Add collect_week_over_week() to scripts/weekly_briefing.py — compares current metrics against previous briefing file
- [x] T022 [US3] Add collect_health_status() to scripts/weekly_briefing.py — reads service health from orchestrator
- [x] T023 [US3] Update generate_briefing() in scripts/weekly_briefing.py — add Odoo Financial Summary, Social Media Activity, Week-over-Week, System Health sections
- [x] T024 [US3] Add overdue invoice table in briefing with customer names and amounts in scripts/weekly_briefing.py
- [x] T025 [P] [US3] Update tests/test_weekly_briefing.py with tests: Odoo section present when available, CSV fallback, social summary, WoW comparison, health status section, overdue invoice flagging

**Checkpoint**: `python -m pytest tests/test_weekly_briefing.py -v` passes. Enhanced briefing contains all Gold Tier sections.

---

## Phase 6: User Story 4 — MCP Servers (Priority: P2)

**Goal**: Three MCP servers (email, social, Odoo) callable from Claude Code via fastmcp stdio transport

**Independent Test**: Start each MCP server → call tools via fastmcp dev inspector → verify structured responses

### Implementation for User Story 4

- [x] T026 [P] [US4] Create scripts/odoo_mcp.py MCP server with 8 tools: check_odoo_connection, list_odoo_databases, list_invoices, get_overdue_invoices, get_account_balances, get_financial_summary, create_draft_invoice, create_draft_expense — using OdooXmlRpcClient directly
- [x] T027 [P] [US4] scripts/mcp_social_server.py with 4 tools: draft_social_post, list_social_drafts, publish_approved_posts, get_social_activity_summary
- [x] T028 [P] [US4] scripts/mcp_email_server.py with 5 tools: fetch_unread_emails, send_email, reply_to_email, mark_email_read, create_email_task
- [x] T029 [US4] All MCP servers return structured dicts with success/error — no unhandled exceptions
- [x] T030 [P] [US4] Tests for Odoo MCP tools included in tests/test_odoo_mcp.py (TestMCPTools class — 4 tests for tool wrappers and error handling)
- [x] T031 [P] [US4] tests/test_mcp_social_server.py — 5 tests for tool functions
- [x] T032 [P] [US4] tests/test_mcp_email_server.py — 6 tests for tool functions
- [x] T033 [US4] .claude/settings.json with MCP server config for odoo-xmlrpc, social, email

**Checkpoint**: `python -m pytest tests/test_mcp_*.py -v` passes. All 14 MCP tools return structured responses.

---

## Phase 7: User Story 5 — Ralph Wiggum Loop (Priority: P2)

**Goal**: Cross-domain autonomous task execution with domain-tagged steps, retry logic, dependency validation, metrics tracking

**Independent Test**: Create a multi-domain task → verify plan has cross-domain steps → execute with simulated failures → verify retry and independent step continuation

### Implementation for User Story 5

- [x] T034 [US5] detect_cross_domain() in scripts/reasoning_loop.py — identifies tasks spanning accounting, social, email, reporting domains
- [x] T035 [US5] Domain-tagged steps in generate_plan_steps() in scripts/reasoning_loop.py — each step gets a `domain` field
- [x] T036 [US5] execute_step_with_retry() in scripts/reasoning_loop.py — retry once per step, log retries, mark failed after max retries
- [x] T037 [US5] Circular dependency detection via detect_circular_dependencies() in scripts/reasoning_loop.py
- [x] T038 [US5] ExecutionMetrics class in scripts/reasoning_loop.py (steps_completed, steps_failed, retries, elapsed_seconds, domains_touched)
- [x] T039 [US5] process_complex_task() + LoopController in scripts/ralph_wiggum.py — autonomous iteration with stop conditions, Done/ check, re-inject until complete
- [x] T040 [P] [US5] tests/test_ralph_wiggum.py — 37 tests: cross-domain, domain tagging, retry, circular deps, metrics, loop controller, stop conditions, status
- [x] T041 [P] [US5] .claude/skills/ralph-wiggum-loop.md agent skill definition with autonomous loop commands

**Checkpoint**: `python -m pytest tests/test_ralph_wiggum.py -v` passes. Cross-domain tasks create domain-tagged plans with retry logic and metrics.

---

## Phase 8: User Story 6 — Error Recovery and Graceful Degradation (Priority: P2)

**Goal**: System continues operating when any external service is unavailable. Health monitoring, crash detection, partial briefings.

**Independent Test**: Start orchestrator with Odoo intentionally unavailable → verify system continues, logs warnings, produces partial briefing

### Implementation for User Story 6

- [x] T042 [US6] Update scripts/orchestrator.py — add Gold Tier components (Odoo sync, social poster) to component list, add `--no-odoo`, `--no-social` flags
- [x] T043 [US6] Add health status tracking dict to scripts/orchestrator.py — per-service status (operational/degraded/unavailable), error counts, last checked timestamp
- [x] T044 [US6] Add optional component restart on crash to scripts/orchestrator.py (configurable via `--auto-restart`)
- [x] T045 [US6] Update banner in scripts/orchestrator.py from "Silver Tier" to "Gold Tier"
- [x] T046 [P] [US6] Update tests/test_orchestrator.py with tests: Gold Tier component list, health status tracking, auto-restart logic, graceful degradation

**Checkpoint**: `python -m pytest tests/test_orchestrator.py -v` passes. Orchestrator launches Gold Tier components with health monitoring.

---

## Phase 9: User Story 7 — Architecture Documentation (Priority: P3)

**Goal**: ARCHITECTURE.md documenting all components, data flows, integration patterns, and lessons learned

**Independent Test**: Verify file exists, covers all components, referenced from README

### Implementation for User Story 7

- [x] T047 [US7] Create ARCHITECTURE.md with sections: System Overview, Component Architecture (all scripts), Data Flow (vault workflow), Integration Patterns (Odoo JSON-RPC, social APIs, MCP stdio), Error Recovery Strategy, Lessons Learned
- [x] T048 [US7] Add ASCII architecture diagram to ARCHITECTURE.md showing data flow between components

**Checkpoint**: ARCHITECTURE.md exists with complete component documentation and architecture diagram.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, Dashboard updates, README, self-test

- [x] T049 Update scripts/update_dashboard.py — add multi-platform social posts table (LinkedIn + Facebook + Instagram + Twitter), Odoo status indicator
- [x] T050 Update README.md — add Gold Tier sections: Odoo setup, social posting, MCP servers, Ralph Wiggum loop, architecture reference, updated tier status
- [x] T051 Update .env.example with all Gold Tier environment variables consolidated
- [x] T052 [P] Create tests/test_gold_tier_selftest.py — comprehensive self-test verifying all Gold Tier requirements (Odoo, social x3, MCP x3, Ralph Wiggum, weekly audit, error recovery, 14+ skills, ARCHITECTURE.md)
- [x] T053 Run full test suite — verify 250+ tests pass across all tiers (Bronze + Silver + Gold)
- [x] T054 Update Dashboard.md with Gold Tier status and service health section

**Checkpoint**: Full test suite 250+ tests pass. README, Dashboard, and ARCHITECTURE.md are complete. Gold Tier 100% verified.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ──────────────► Phase 2 (Foundational)
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
              Phase 3 (US1)     Phase 4 (US2)      Phase 5 (US3)
              Odoo Client       Social Poster       Weekly Audit
                    │                  │                  │
                    └──────────────────┼──────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
              Phase 6 (US4)     Phase 7 (US5)      Phase 8 (US6)
              MCP Servers       Ralph Wiggum       Error Recovery
                    │                  │                  │
                    └──────────────────┼──────────────────┘
                                       │
                                       ▼
                                 Phase 9 (US7)
                                 Architecture Doc
                                       │
                                       ▼
                                 Phase 10 (Polish)
                                 Self-Test + README
```

### User Story Dependencies

- **US1 (Odoo)**: Depends on Phase 2 only — can start first
- **US2 (Social)**: Depends on Phase 2 only — can run parallel with US1
- **US3 (Weekly Audit)**: Depends on US1 (Odoo data) and US2 (social summary) — must follow
- **US4 (MCP Servers)**: Depends on US1 (Odoo MCP wraps odoo_client) and US2 (Social MCP wraps social_poster)
- **US5 (Ralph Wiggum)**: Depends on Phase 2 only — can run parallel with US1/US2 (extends existing reasoning_loop.py)
- **US6 (Error Recovery)**: Depends on US1, US2 (needs Gold components in orchestrator)
- **US7 (Architecture)**: Depends on all other stories (documents them)

### Parallel Opportunities

```bash
# After Phase 2, these can run in parallel:
Phase 3 (US1 Odoo) ║ Phase 4 (US2 Social) ║ Phase 7 (US5 Ralph Wiggum)

# Within each story, test files can be created in parallel:
T009 (test_odoo_client.py) ║ T010 (odoo-accounting.md skill)
T017 (test_social_poster.py) ║ T018 (social-poster.md skill)
T030 (test_mcp_odoo) ║ T031 (test_mcp_social) ║ T032 (test_mcp_email)
```

---

## Implementation Strategy

### MVP First (US1 Only — Odoo Integration)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T005)
3. Complete Phase 3: US1 Odoo Client (T006–T010)
4. **VALIDATE**: Odoo client reads invoices, handles errors, tests pass

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 (Odoo) → **Test independently** → Odoo data accessible
3. US2 (Social) → **Test independently** → 3 new platforms posting
4. US3 (Weekly Audit) → **Test independently** → Enhanced CEO briefing
5. US4 (MCP Servers) → **Test independently** → Claude Code can query systems
6. US5 (Ralph Wiggum) → **Test independently** → Cross-domain autonomy
7. US6 (Error Recovery) → **Test independently** → Production resilience
8. US7 (Architecture) + Polish → **Full Gold Tier complete**

---

## Summary

| Metric | Count |
|--------|-------|
| Total Tasks | 54 |
| Phase 1 (Setup) | 3 |
| Phase 2 (Foundational) | 2 |
| US1 (Odoo) | 5 |
| US2 (Social) | 8 |
| US3 (Weekly Audit) | 7 |
| US4 (MCP Servers) | 8 |
| US5 (Ralph Wiggum) | 8 |
| US6 (Error Recovery) | 5 |
| US7 (Architecture) | 2 |
| Phase 10 (Polish) | 6 |
| Parallel-eligible [P] | 20 |
| New test files | 8 |
| New scripts | 6 |
| New skills | 3 |
| Target total tests | 250+ |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- All social APIs default to simulation mode — no API keys needed for development/testing
- Odoo client uses mocked JSON-RPC in tests — no running Odoo instance needed for CI
- Existing Silver Tier tests (233) must continue passing throughout
- Commit after each phase or logical group
