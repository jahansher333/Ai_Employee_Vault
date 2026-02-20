# Feature Specification: Bronze Tier Foundation

**Feature Branch**: `002-bronze-foundation`
**Created**: 2026-02-17
**Status**: Draft
**Input**: Bronze Tier: Foundation (Exact Document Requirements) — Complete Bronze Tier per hackathon document with one file system watcher, Agent Skills, and vault read/write.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - File System Watcher Detects New Tasks (Priority: P1)

A user drops a `.md` file into the `Needs_Action/` folder. The file system watcher detects the new file within one polling cycle, logs the detection event to `Logs/`, and marks it as ready for processing. The watcher MUST NOT process the same file twice across restarts (deduplication via ledger file).

**Why this priority**: The watcher is the entry point for the entire AI Employee pipeline. Without detection, nothing downstream can function.

**Independent Test**: Can be fully tested by starting the watcher, dropping a `.md` file into `Needs_Action/`, and verifying a detection event appears in the audit log within one polling interval.

**Acceptance Scenarios**:

1. **Given** the watcher is running and `Needs_Action/` is empty, **When** a new `.md` file is placed in the folder, **Then** the watcher logs a `file_detected` event within one polling cycle.
2. **Given** a file was already detected in a prior run, **When** the watcher restarts, **Then** the file is NOT re-detected (deduplication ledger persists).
3. **Given** a non-`.md` file is placed in `Needs_Action/`, **When** the watcher polls, **Then** the file is ignored and no event is logged.

---

### User Story 2 - SimpleTaskReaderSkill Processes Tasks (Priority: P2)

An Agent Skill reads a task file from `Needs_Action/`, parses its YAML frontmatter (type, priority, category, status), generates a summary, and appends that summary to `Dashboard.md`. If the task contains sensitive content (payment, credentials, deletion), it is routed to `Pending_Approval/` instead of being processed.

**Why this priority**: This is the core AI functionality — reading vault files and writing structured output back to the vault. It demonstrates Claude Code's ability to operate as an autonomous employee.

**Independent Test**: Can be tested by placing a sample task in `Needs_Action/`, running the processor, and verifying the summary appears in `Dashboard.md` and the task status is updated.

**Acceptance Scenarios**:

1. **Given** a `.md` file with valid frontmatter exists in `Needs_Action/`, **When** the processor runs, **Then** the file's status is updated to `planned`, an action plan section is appended to the file, and a summary line is added to `Dashboard.md`.
2. **Given** a task containing the word "payment" in its body, **When** the processor runs, **Then** the file is moved to `Pending_Approval/` and a `pending_approval` event is logged.
3. **Given** a task with `status: planned` (already processed), **When** the processor runs again, **Then** the file is skipped and no duplicate entry appears.

---

### User Story 3 - Vault Structure and Core Documents (Priority: P3)

The vault contains a working Obsidian-compatible folder structure with `Dashboard.md` (live status counts and recent activity), `Company_Handbook.md` (operating principles and task format), and `README.md` (setup and test instructions). The folder structure includes `Needs_Action/`, `Done/`, `Logs/`, and `Pending_Approval/`.

**Why this priority**: The vault structure is the foundation that all other components depend on. Without it, the watcher has nothing to monitor and the skill has nowhere to write.

**Independent Test**: Can be tested by verifying all folders and core documents exist, `Dashboard.md` renders correctly in Obsidian, and `README.md` contains complete setup instructions.

**Acceptance Scenarios**:

1. **Given** the vault is initialized, **When** a user opens it in Obsidian, **Then** `Dashboard.md`, `Company_Handbook.md`, and `README.md` are visible and properly formatted.
2. **Given** the dashboard updater runs, **When** files exist in `Needs_Action/` and `Done/`, **Then** `Dashboard.md` shows accurate counts for each folder.
3. **Given** a new user clones the repository, **When** they follow `README.md` instructions, **Then** they can run the watcher and process a sample task end-to-end.

---

### User Story 4 - Audit Logging (Priority: P4)

Every action taken by the AI Employee is logged to `Logs/` in JSON Lines format (one `.jsonl` file per day). Each log entry includes timestamp, action name, input reference, outcome, duration, and optional details. The log is append-only and supports filtered reads.

**Why this priority**: Audit logging provides transparency and accountability. It is required by the constitution but is not on the critical path for basic task processing.

**Independent Test**: Can be tested by triggering any action (file detection, inbox processing, dashboard update) and verifying a corresponding JSON line appears in the day's log file.

**Acceptance Scenarios**:

1. **Given** any system action occurs, **When** the action completes, **Then** a JSON line is appended to `Logs/YYYY-MM-DD.audit.jsonl` with all required fields.
2. **Given** multiple actions occur on the same day, **When** the log file is read, **Then** entries appear in chronological order and each is valid JSON.
3. **Given** an action fails, **When** the error is logged, **Then** the entry includes `outcome: "error"` and the `error` field contains the error message.

---

### Edge Cases

- What happens when `Needs_Action/` does not exist at watcher startup? The watcher MUST create the folder automatically.
- What happens when a `.md` file has no YAML frontmatter? The processor MUST handle it gracefully with default values (type: task, priority: medium, category: general, status: new).
- What happens when `Dashboard.md` does not exist when the updater runs? The updater MUST create it with default content.
- What happens when the ledger file is corrupted or missing? The watcher MUST recreate it (accepting one-time re-processing of existing files).
- What happens when two files with the same name exist in `Needs_Action/` and `Done/`? The move-to-done operation MUST rename the file with a numeric suffix to avoid overwriting.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST monitor `Needs_Action/` for new `.md` files using a polling-based file system watcher.
- **FR-002**: System MUST maintain a deduplication ledger that persists across watcher restarts to prevent re-processing.
- **FR-003**: System MUST parse YAML frontmatter from task files, extracting type, priority, category, and status fields.
- **FR-004**: System MUST generate an action plan section for each new task and update the file's status to `planned`.
- **FR-005**: System MUST detect sensitive content (keywords: payment, password, credential, delete, remove, API key) and route those tasks to `Pending_Approval/`.
- **FR-006**: System MUST append task summaries to `Dashboard.md` including timestamp, action, outcome, and file reference.
- **FR-007**: System MUST update `Dashboard.md` with current item counts for `Needs_Action/`, `Pending_Approval/`, and `Done/` folders.
- **FR-008**: System MUST log every action to `Logs/YYYY-MM-DD.audit.jsonl` in JSON Lines format with timestamp, action, input_ref, outcome, duration_ms, details, and error fields.
- **FR-009**: All AI functionality MUST be defined as reusable Agent Skills in `.claude/skills/` directory.
- **FR-010**: System MUST provide a `README.md` with setup instructions, vault structure, task format, and test commands.

### Key Entities

- **Task File**: A Markdown file with YAML frontmatter (type, priority, category, status) and a body describing the work to be done. Lives in `Needs_Action/`, `Pending_Approval/`, or `Done/`.
- **Audit Log Entry**: A JSON object with fields: timestamp, action, input_ref, outcome, duration_ms, details, error. Stored as one line per entry in daily `.jsonl` files.
- **Deduplication Ledger**: A plain text file listing filenames already processed by the watcher, one per line.
- **Dashboard**: A Markdown file (`Dashboard.md`) containing a status table with folder counts and a recent activity section.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Watcher detects new `.md` files within one polling cycle (configurable, default 5 seconds) with zero missed files across 10 consecutive test runs.
- **SC-002**: Processor correctly parses frontmatter and generates action plans for 100% of well-formed task files.
- **SC-003**: Sensitive content detection correctly routes files containing any of the 6 defined keywords to `Pending_Approval/` with zero false negatives.
- **SC-004**: Dashboard displays accurate folder counts matching actual file system state after each update.
- **SC-005**: Every system action produces exactly one audit log entry with all required fields populated and valid JSON.
- **SC-006**: All core functionality runs with zero external dependencies beyond Python 3.11+ standard library.
- **SC-007**: Test suite achieves 100% pass rate covering watcher, processor, logger, and dashboard updater.
- **SC-008**: A new user can follow README.md to set up and run the system end-to-end (watcher start, task drop, process, dashboard update) in under 5 minutes.

## Assumptions

- The vault runs on a local filesystem (no network/cloud storage).
- Python 3.11+ is available on the host machine.
- Obsidian is used for viewing but is not required for the system to function.
- The watcher uses polling (not OS-level filesystem events) for maximum cross-platform compatibility.
- Bronze Tier is detection and recommendation only — no external API calls or automated execution.
- `.env` file is used for configuration (vault path, poll interval) and is never committed to version control.
