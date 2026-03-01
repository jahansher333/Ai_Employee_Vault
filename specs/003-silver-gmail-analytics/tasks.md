# Tasks: Silver Tier - Gmail Watcher + Data Analytics

**Input**: Design documents from `specs/003-silver-gmail-analytics/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks grouped by user story. US1 & US4 are P1 (MVP), US2 & US3 are P2, Polish is P3.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1=Gmail Monitoring, US2=Financial Analysis, US3=Dashboard Analytics, US4=Secure Credentials)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Install dependencies, create directories, update config files

- [X] T001 Install new Python dependencies: google-api-python-client, google-auth-oauthlib, pandas in requirements.txt
- [X] T002 [P] Create Accounting/ directory with sample-transactions.csv at Accounting/sample-transactions.csv
- [X] T003 [P] Update .env.example with Gmail config variables (GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH, GMAIL_POLL_INTERVAL, GMAIL_MAX_RESULTS) in .env.example
- [X] T004 [P] Update .gitignore to exclude credentials.json, token.json, and Accounting/*.csv in .gitignore

**Checkpoint**: Dependencies installed, directories created, config updated

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared utilities that multiple user stories depend on

- [X] T005 Add Gmail ledger helper functions (load_gmail_ledger, save_to_gmail_ledger) in scripts/gmail_watcher.py
- [X] T006 [P] Add analytics section markers (START_ANALYTICS/END_ANALYTICS) to Dashboard.md in Dashboard.md
- [X] T007 [P] Update tests/conftest.py with new shared fixtures for Gmail mock data and sample CSV data in tests/conftest.py

**Checkpoint**: Foundation ready - ledger helpers, dashboard markers, and test fixtures available

---

## Phase 3: User Story 4 - Secure Credential Management (Priority: P1)

**Goal**: Gmail credentials loaded securely from .env, clear errors when missing

**Independent Test**: Run gmail_watcher.py without credentials -> verify clear error message

### Implementation for User Story 4

- [X] T008 [US4] Implement build_gmail_service(credentials_path, token_path) with OAuth 2.0 desktop flow in scripts/gmail_watcher.py
- [X] T009 [US4] Add credential validation: check credentials.json exists, handle missing/expired tokens with clear error messages in scripts/gmail_watcher.py
- [X] T010 [US4] Add --auth-only CLI flag for first-time OAuth consent flow in scripts/gmail_watcher.py
- [X] T011 [P] [US4] Write tests for credential validation and error handling (mocked) in tests/test_gmail_watcher.py

**Checkpoint**: OAuth flow works, credentials load from .env, clear error when missing

---

## Phase 4: User Story 1 - Gmail Monitoring Creates Tasks (Priority: P1) MVP

**Goal**: Poll Gmail for unread emails, create EMAIL_*.md task files in Needs_Action/

**Independent Test**: Send email to monitored account -> verify EMAIL_*.md appears in Needs_Action/ with correct frontmatter

### Implementation for User Story 1

- [X] T012 [US1] Implement fetch_unread_emails(service, max_results) to query Gmail API for unread messages in scripts/gmail_watcher.py
- [X] T013 [US1] Implement create_email_task(email_data, vault_path) to generate EMAIL_{HHMMSS}_{subject}.md with YAML frontmatter in scripts/gmail_watcher.py
- [X] T014 [US1] Implement mark_as_read(service, message_id) to remove UNREAD label from processed emails in scripts/gmail_watcher.py
- [X] T015 [US1] Implement start_gmail_watcher(vault_path, interval) main poll loop with ledger dedup and audit logging in scripts/gmail_watcher.py
- [X] T016 [US1] Add CLI argument parsing (--vault-path, --interval, --auth-only) and main() entry point in scripts/gmail_watcher.py
- [X] T017 [P] [US1] Write tests for fetch_unread_emails, create_email_task, mark_as_read (mocked Gmail API) in tests/test_gmail_watcher.py
- [X] T018 [P] [US1] Write tests for start_gmail_watcher poll loop logic and ledger dedup in tests/test_gmail_watcher.py

**Checkpoint**: Gmail watcher polls, creates task files, marks as read, deduplicates via ledger. Existing file watcher picks up EMAIL_*.md files automatically.

---

## Phase 5: User Story 2 - Financial Data Analysis (Priority: P2)

**Goal**: Read CSV files from Accounting/, calculate revenue/expenses/anomalies

**Independent Test**: Place sample CSV in Accounting/ -> run data_analyzer.py -> verify correct totals and anomaly detection

### Implementation for User Story 2

- [X] T019 [US2] Implement map_columns(df, original_columns) for flexible CSV column name matching in scripts/data_analyzer.py
- [X] T020 [US2] Implement read_financial_csv(file_path) to read and normalize CSV data with pandas in scripts/data_analyzer.py
- [X] T021 [US2] Implement clean_data(df) to remove duplicates, parse amounts/dates, fill missing categories in scripts/data_analyzer.py
- [X] T022 [US2] Implement analyze(df) to calculate total revenue, expenses, net income, and monthly breakdown in scripts/data_analyzer.py
- [X] T023 [US2] Implement detect_anomalies(df) to flag transactions where |amount| > 2x category average in scripts/data_analyzer.py
- [X] T024 [P] [US2] Write tests for map_columns and read_financial_csv with various CSV formats in tests/test_data_analyzer.py
- [X] T025 [P] [US2] Write tests for clean_data, analyze, and detect_anomalies with edge cases in tests/test_data_analyzer.py

**Checkpoint**: Data analyzer reads CSVs, calculates accurate totals, detects anomalies. All tests pass.

---

## Phase 6: User Story 3 - Dashboard Analytics Integration (Priority: P2)

**Goal**: Analytics summary appears in Dashboard.md between markers, replaces on each update

**Independent Test**: Run data_analyzer.py -> verify Dashboard.md shows Business Analytics section with tables

### Implementation for User Story 3

- [X] T026 [US3] Implement generate_analytics_markdown(summary) to produce Markdown tables (summary, monthly, top expenses, alerts) in scripts/data_analyzer.py
- [X] T027 [US3] Implement update_dashboard_analytics(vault_path, markdown) to replace content between START_ANALYTICS/END_ANALYTICS markers in scripts/data_analyzer.py
- [X] T028 [US3] Implement run_analysis(vault_path) orchestrator: scan Accounting/, analyze all CSVs, update dashboard, log to audit in scripts/data_analyzer.py
- [X] T029 [US3] Add CLI argument parsing and main() entry point for data_analyzer.py in scripts/data_analyzer.py
- [X] T030 [P] [US3] Write tests for generate_analytics_markdown output format in tests/test_data_analyzer.py
- [X] T031 [P] [US3] Write tests for update_dashboard_analytics marker replacement in tests/test_data_analyzer.py

**Checkpoint**: Running data_analyzer.py updates Dashboard.md with accurate analytics tables. All tests pass.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, skill definition, Bronze folder organization, final validation

- [X] T032 [P] Create DataAnalyzerSkill definition in .claude/skills/data-analyzer.md
- [X] T033 [P] Update README.md with Silver Tier sections: Gmail API setup, running both watchers, analytics instructions in README.md
- [X] T034 [P] Update .env.example with complete Silver Tier configuration in .env.example
- [X] T035 Create Bronze/ folder and move Bronze Tier artifacts (copy existing Bronze scripts as reference) in Bronze/
- [X] T036 Run full test suite: all existing Bronze tests + new Gmail watcher + data analyzer tests
- [X] T037 Run end-to-end validation per quickstart.md: simulate email task file, run analyzer, verify dashboard updates
- [X] T038 Silver Tier check: confirm 2 watchers operational, analytics functional, dashboard updated, README complete

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion
- **US4 Secure Credentials (Phase 3)**: Depends on Phase 2 - BLOCKS US1 (Gmail needs auth)
- **US1 Gmail Monitoring (Phase 4)**: Depends on Phase 3 (needs working auth)
- **US2 Financial Analysis (Phase 5)**: Depends on Phase 2 only - can run parallel with US1/US4
- **US3 Dashboard Analytics (Phase 6)**: Depends on Phase 5 (needs analyzer output)
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

- **US4 (Credentials)** -> **US1 (Gmail)**: Gmail watcher needs authenticated service
- **US2 (Analysis)** -> **US3 (Dashboard)**: Dashboard integration needs analyzer output
- **US2 can run in parallel with US1/US4**: Different files, no shared dependencies

### Parallel Opportunities

- T002, T003, T004 (Phase 1 setup tasks)
- T006, T007 (Phase 2 foundational tasks)
- T011 with T008-T010 (US4 tests parallel with implementation)
- T017, T018 with T024, T025 (US1 tests parallel with US2 tests)
- US1/US4 pipeline parallel with US2/US3 pipeline (different modules)
- T032, T033, T034 (Polish documentation tasks)

---

## Implementation Strategy

### MVP First (US4 + US1)

1. Phase 1: Setup -> install deps, create dirs
2. Phase 2: Foundation -> ledger, markers, fixtures
3. Phase 3: US4 -> OAuth flow, credential management
4. Phase 4: US1 -> Gmail polling, task file creation
5. **STOP & VALIDATE**: Gmail watcher creates task files, file watcher processes them

### Full Silver Tier

6. Phase 5: US2 -> CSV analysis with pandas
7. Phase 6: US3 -> Dashboard analytics integration
8. Phase 7: Polish -> docs, skill def, Bronze folder, final tests

---

## Notes

- All file I/O MUST use `encoding="utf-8"` (Windows cp1252 fix from Bronze Tier)
- All print statements MUST use ASCII characters only (no Unicode arrows)
- Gmail API calls MUST be mocked in tests (no real API calls in CI)
- pandas operations MUST handle empty DataFrames gracefully
- Total tasks: 38
