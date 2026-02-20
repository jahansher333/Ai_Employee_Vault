# Tasks: Bronze Tier Foundation

**Input**: Design documents from `specs/002-bronze-foundation/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Included — spec requires test suite (SC-007) and user explicitly requests end-to-end test.

**Organization**: Tasks grouped by user story (US1=Watcher P1, US2=Processor P2, US3=Vault P3, US4=Logging P4).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Exact file paths included in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, folder structure, configuration files

- [X] T001 Create vault folder structure: Needs_Action/, Done/, Pending_Approval/, Logs/, scripts/, tests/, .claude/skills/
- [X] T002 [P] Create .env.example with VAULT_PATH, WATCH_INTERVAL, LOG_RETENTION_DAYS in .env.example
- [X] T003 [P] Create .gitignore with Python patterns, .env, .obsidian/, Logs/*.jsonl, Logs/.watcher_ledger.txt in .gitignore
- [X] T004 [P] Create tests/conftest.py with shared pytest fixtures (tmp_path vault, sample frontmatter, AuditLogger factory) in tests/conftest.py

**Checkpoint**: Folder structure exists, config files in place, test fixtures ready.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core modules that ALL user stories depend on — AuditLogger shared by watcher, processor, and dashboard

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Implement AuditLogger class with log(), timed(), read_log() methods per contracts/audit_logger.md in scripts/audit_logger.py
- [X] T006 Write tests for AuditLogger (creates jsonl, valid json, append-only, timed context success+error, filter, empty date) in tests/test_audit_logger.py

**Checkpoint**: `python -m pytest tests/test_audit_logger.py -v` — all tests PASS. AuditLogger ready for use by all stories.

---

## Phase 3: User Story 1 — File System Watcher Detects New Tasks (Priority: P1) MVP

**Goal**: watchdog-based watcher monitors `Needs_Action/` for new `.md` files, logs detection events, maintains dedup ledger.

**Independent Test**: Start watcher, drop a `.md` file into `Needs_Action/`, verify `file_detected` event appears in `Logs/YYYY-MM-DD.audit.jsonl` and filename is added to `Logs/.watcher_ledger.txt`.

### Tests for User Story 1

- [X] T007 [P] [US1] Write tests for watcher: detects new .md, ignores non-.md, dedup ledger load/save, missing folder auto-create, no re-detect after restart in tests/test_watcher.py

### Implementation for User Story 1

- [X] T008 [US1] Implement TaskFileHandler(PatternMatchingEventHandler) with on_created() per contracts/watcher.md in scripts/watcher.py
- [X] T009 [US1] Implement load_ledger() and save_to_ledger() functions for dedup persistence in scripts/watcher.py
- [X] T010 [US1] Implement start_watcher() main entry point with Observer setup, Ctrl+C handling, cleanup in scripts/watcher.py
- [X] T011 [US1] Verify watcher.py is monitoring Needs_Action/ by running end-to-end: start watcher → drop test.md → check audit log entry

**Checkpoint**: `python -m pytest tests/test_watcher.py -v` — all tests PASS. Watcher detects `.md` files and logs events.

---

## Phase 4: User Story 2 — SimpleTaskReaderSkill Processes Tasks (Priority: P2)

**Goal**: Processor reads task files, parses frontmatter, generates action plan, detects sensitive content, appends clean Markdown summary to Dashboard.md.

**Independent Test**: Place a sample task in `Needs_Action/`, run `python scripts/process_inbox.py`, verify task status is `planned`, action plan is appended, and summary line appears in Dashboard.md.

### Tests for User Story 2

- [X] T012 [P] [US2] Write tests for processor: parse frontmatter (valid, missing, defaults), is_sensitive (6 keywords + case-insensitive + normal), process_file (new→planned, skip planned, sensitive→pending_approval), move_to_done (preserves content, name conflict), generate_action_plan in tests/test_process_inbox.py

### Implementation for User Story 2

- [X] T013 [US2] Implement parse_frontmatter() and serialize_frontmatter() per contracts/processor.md in scripts/process_inbox.py
- [X] T014 [US2] Implement is_sensitive() with 6 keywords (payment, password, credential, delete, remove, api key) case-insensitive in scripts/process_inbox.py
- [X] T015 [US2] Implement generate_action_plan() producing clean Markdown with timestamp, priority, category, recommended steps in scripts/process_inbox.py
- [X] T016 [US2] Implement process_file() orchestrating parse→sensitive check→plan→status update→dashboard summary per contracts/processor.md in scripts/process_inbox.py
- [X] T017 [US2] Implement move_to_done() with name conflict handling (numeric suffix) in scripts/process_inbox.py
- [X] T018 [US2] Create SimpleTaskReaderSkill definition (Purpose, Trigger, Input, Steps, Output, Error Handling) in .claude/skills/simple-task-reader.md
- [X] T019 [US2] Wire watcher on_created() to call process_file() after detection in scripts/watcher.py

**Checkpoint**: `python -m pytest tests/test_process_inbox.py -v` — all tests PASS. Processor generates plans and routes sensitive content.

---

## Phase 5: User Story 3 — Vault Structure and Core Documents (Priority: P3)

**Goal**: Dashboard.md with dynamic Pending Tasks section and folder counts, Company_Handbook.md with operating principles, README.md with setup/run/test instructions.

**Independent Test**: Run `python scripts/update_dashboard.py`, verify Dashboard.md shows correct folder counts and recent activity. Open in Obsidian to confirm rendering.

### Tests for User Story 3

- [X] T020 [P] [US3] Write tests for dashboard updater: count_folder (empty, with files, missing), format_activity, update_dashboard (creates if missing, accurate counts, recent activity) in tests/test_update_dashboard.py

### Implementation for User Story 3

- [X] T021 [US3] Implement count_folder() and format_activity() per contracts/dashboard.md in scripts/update_dashboard.py
- [X] T022 [US3] Implement update_dashboard() with Quick Status table (dynamic counts), Pending Tasks section, Recent Activity from audit log in scripts/update_dashboard.py
- [X] T023 [P] [US3] Create Dashboard.md with YAML frontmatter, Quick Status table, How It Works, Folder Structure, Recent Activity in Dashboard.md
- [X] T024 [P] [US3] Create Company_Handbook.md with operating principles, task format template, approval workflow, folder descriptions in Company_Handbook.md
- [X] T025 [US3] Create README.md with: title, What It Does (5-step), Quick Start (numbered), Vault Structure (ASCII tree), Task Format, Core Principles, Running Tests, Scripts table in README.md

**Checkpoint**: `python -m pytest tests/test_update_dashboard.py -v` — all tests PASS. Dashboard renders correctly in Obsidian. README provides complete setup guide.

---

## Phase 6: User Story 4 — Audit Logging (Priority: P4)

**Goal**: Ensure all actions across watcher, processor, and dashboard produce audit log entries. Verify append-only integrity.

**Independent Test**: Run any action (watcher detect, process inbox, update dashboard) and verify corresponding JSON line in `Logs/YYYY-MM-DD.audit.jsonl`.

- [X] T026 [US4] Wire dashboard updater to log `dashboard_updated` event with folder counts in scripts/update_dashboard.py
- [X] T027 [US4] Verify all 5 action types produce correct audit entries: file_detected, inbox_processed, pending_approval, move_to_done, dashboard_updated

**Checkpoint**: Every system action produces exactly one valid JSON log entry.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Agent skills, sample data, integration wiring, end-to-end validation

- [X] T028 [P] Create move-to-done.md skill definition in .claude/skills/move-to-done.md
- [X] T029 [P] Create check-pending-approvals.md skill definition in .claude/skills/check-pending-approvals.md
- [X] T030 [P] Create generate-status-report.md skill definition in .claude/skills/generate-status-report.md
- [X] T031 Create sample task file for testing in Needs_Action/sample-task.md
- [X] T032 Add __main__ entry points with argparse to scripts/watcher.py, scripts/process_inbox.py, scripts/update_dashboard.py
- [X] T033 End-to-end integration test: start watcher → drop test.md into Needs_Action/ → verify audit log entry + Dashboard.md updated + task status planned
- [X] T034 Run full test suite: `python -m pytest tests/ -v` — all tests PASS (SC-007)
- [X] T035 Run quickstart.md scenario end-to-end and verify all checklist items pass

**Checkpoint**: All tests pass. End-to-end flow verified. Bronze Tier Foundation complete.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (T001 for folders, T004 for fixtures)
- **US1 Watcher (Phase 3)**: Depends on Phase 2 (needs AuditLogger)
- **US2 Processor (Phase 4)**: Depends on Phase 2 (needs AuditLogger) + Phase 3 T008 (watcher integration at T019)
- **US3 Vault Docs (Phase 5)**: Depends on Phase 2 (needs AuditLogger for dashboard)
- **US4 Logging Verify (Phase 6)**: Depends on Phases 3, 4, 5 (all actions exist)
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (Watcher)**: Independent after Phase 2 — **MVP candidate**
- **US2 (Processor)**: Independent after Phase 2, wires into US1 at T019
- **US3 (Vault Docs)**: Independent after Phase 2
- **US4 (Logging)**: Verification phase, depends on US1+US2+US3

### Parallel Opportunities

- T002, T003, T004 can run in parallel (Phase 1, different files)
- T007 (watcher tests) can start while T005-T006 complete
- T012 (processor tests) can start while US1 implementation proceeds
- T020, T023, T024 can run in parallel (Phase 5, different files)
- T028, T029, T030 can run in parallel (Phase 7, different skill files)

---

## Parallel Example: User Story 1

```bash
# Write test first:
Task: "Write watcher tests in tests/test_watcher.py" (T007)

# Then implement in parallel where possible:
Task: "Implement TaskFileHandler in scripts/watcher.py" (T008)
Task: "Implement ledger functions in scripts/watcher.py" (T009) — same file, sequential with T008
Task: "Implement start_watcher in scripts/watcher.py" (T010) — same file, sequential
```

---

## Implementation Strategy

### MVP First (US1: Watcher Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: AuditLogger (T005-T006)
3. Complete Phase 3: Watcher (T007-T011)
4. **STOP and VALIDATE**: Watcher detects files and logs events
5. Demo: "Drop a file, see it detected and logged"

### Full Bronze Tier (Sequential)

1. Setup → Foundational → US1 Watcher → US2 Processor → US3 Vault Docs → US4 Logging → Polish
2. Each phase checkpoint validates before proceeding
3. Total: 35 tasks across 7 phases

---

## Notes

- [P] tasks = different files, no dependencies — safe to parallelize
- [US*] label maps task to specific user story for traceability
- All scripts use `if __name__ == "__main__"` entry points for standalone execution
- Watcher integrates with processor at T019 (last task before checkpoint)
- Test suite target: SC-007 requires 100% pass rate
- No external dependencies beyond `watchdog` and Python stdlib (SC-006)
