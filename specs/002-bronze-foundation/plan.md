# Implementation Plan: Bronze Tier Foundation

**Branch**: `002-bronze-foundation` | **Date**: 2026-02-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/002-bronze-foundation/spec.md`

## Summary

Build a local-first AI Employee vault with a `watchdog`-based file system watcher that monitors `Needs_Action/` for new `.md` task files, processes them via a SimpleTaskReaderSkill (parse frontmatter, generate action plan, detect sensitive content), logs all actions to JSON Lines audit trail, and updates a live `Dashboard.md`. All AI logic is defined as reusable Agent Skills in `.claude/skills/`. Zero external dependencies beyond `watchdog`.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `watchdog` (file system monitoring)
**Storage**: Local filesystem (Markdown files, JSON Lines logs, plain text ledger)
**Testing**: `pytest`
**Target Platform**: Cross-platform (Windows, macOS, Linux) — local machine
**Project Type**: Single project — scripts + Obsidian vault
**Performance Goals**: File detection within one watchdog event cycle (~1-5 seconds)
**Constraints**: No external API calls, no cloud services, detection-only (Principle VI)
**Scale/Scope**: Single-user local vault, <1000 files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Clarity of Requirements | **PASS** | spec.md has 10 FRs with RFC 2119 MUST, 4 Given/When/Then user stories, 8 measurable SCs |
| II. Security & Approval | **PASS** | FR-005 routes sensitive content to Pending_Approval/; .env for secrets; no external execution |
| III. Logging & Audit | **PASS** | FR-008 mandates JSON Lines audit logging; append-only; daily rotation |
| IV. Modular Code | **PASS** | 4 separate scripts (watcher, processor, dashboard, logger); each independently testable |
| V. Readable Artifacts | **PASS** | This plan.md, research.md, data-model.md, contracts/ all follow template structure |
| VI. Detection Only | **PASS** | Watcher detects and logs; processor generates plans and summaries; no external API calls |

**Gate result**: ALL PASS — proceed to implementation.

## Project Structure

### Documentation (this feature)

```text
specs/002-bronze-foundation/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Technology decisions
├── data-model.md        # Entity definitions
├── quickstart.md        # End-to-end test scenario
├── contracts/
│   ├── watcher.md       # Watcher module contract
│   ├── processor.md     # Inbox processor contract
│   ├── audit_logger.md  # Audit logger contract
│   └── dashboard.md     # Dashboard updater contract
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Task breakdown (created by /sp.tasks)
```

### Source Code (repository root)

```text
Ai_Employee_Vault/
├── Dashboard.md                    # Live status dashboard (FR-006, FR-007)
├── Company_Handbook.md             # Operating principles & task format
├── README.md                       # Setup, run, test instructions (FR-010)
├── .env.example                    # Environment variable template
├── .gitignore                      # Python + vault patterns
├── Needs_Action/                   # Drop tasks here (monitored by watcher)
│   └── sample-task.md              # Example task file
├── Pending_Approval/               # Sensitive tasks awaiting human review
├── Done/                           # Completed tasks
├── Logs/                           # Audit trail
│   ├── YYYY-MM-DD.audit.jsonl      # Daily audit log (FR-008)
│   └── .watcher_ledger.txt         # Deduplication ledger (FR-002)
├── scripts/
│   ├── watcher.py                  # Watchdog-based file monitor (FR-001)
│   ├── process_inbox.py            # Task processor with frontmatter (FR-003-005)
│   ├── update_dashboard.py         # Dashboard regenerator (FR-006, FR-007)
│   └── audit_logger.py             # Shared logging module (FR-008)
├── .claude/skills/
│   ├── simple-task-reader.md       # Core skill: read task, summarize, update dashboard (FR-009)
│   ├── move-to-done.md             # Skill: move completed items
│   ├── check-pending-approvals.md  # Skill: review sensitive items
│   └── generate-status-report.md   # Skill: update Dashboard.md
└── tests/
    ├── conftest.py                 # Shared fixtures
    ├── test_audit_logger.py        # Logger tests
    ├── test_watcher.py             # Watcher tests
    ├── test_process_inbox.py       # Processor tests
    └── test_update_dashboard.py    # Dashboard updater tests
```

**Structure Decision**: Flat `scripts/` layout with shared `audit_logger.py` module. No package structure needed — Bronze Tier is 4 scripts with a shared logger. Agent Skills are Markdown definitions in `.claude/skills/`, not Python code.

## Architecture Flow

```
User drops .md file into Needs_Action/
        │
        ▼
┌──────────────────────┐
│   watcher.py         │  (watchdog Observer + PatternMatchingEventHandler)
│   on_created()       │
│   ├── Check ledger   │  → Skip if already seen
│   ├── Log detection  │  → Logs/YYYY-MM-DD.audit.jsonl
│   ├── Update ledger  │  → Logs/.watcher_ledger.txt
│   └── Call processor │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  process_inbox.py    │
│  process_file()      │
│  ├── Parse frontmatter│ → type, priority, category, status
│  ├── Check sensitive  │ → 6 keywords (case-insensitive)
│  │   ├── YES → move to Pending_Approval/ + log
│  │   └── NO  → continue
│  ├── Generate plan    │ → Append ## Action Plan to file
│  ├── Update status    │ → status: new → planned
│  ├── Append summary   │ → Dashboard.md Recent Activity
│  └── Log action       │ → Logs/YYYY-MM-DD.audit.jsonl
└──────────────────────┘
           │
           ▼
┌──────────────────────┐
│ update_dashboard.py  │  (can also run standalone)
│ ├── Count folders    │  → Needs_Action, Pending_Approval, Done
│ ├── Read audit log   │  → Last 10 entries
│ └── Write Dashboard  │  → Dashboard.md with counts + activity
└──────────────────────┘
```

## Agent Skill Template

Each skill in `.claude/skills/` follows this structure:

```markdown
# Skill: [Name]

## Purpose
[One-line description of what this skill does]

## Trigger
[When this skill should be invoked]

## Input
[What files/data this skill reads]

## Steps
1. [Step 1]
2. [Step 2]
...

## Output
[What files/data this skill writes or modifies]

## Error Handling
[How to handle failures]
```

## README Outline

The `README.md` MUST include:

1. **Title and description** — "Bronze Tier AI Employee"
2. **What It Does** — 5-step workflow (detect → analyze → plan → flag → log)
3. **Quick Start** — numbered steps: .env setup, install watchdog, start watcher, drop task, process, update dashboard
4. **Vault Structure** — ASCII tree matching project structure above
5. **Task Format** — YAML frontmatter template with valid values
6. **Core Principles** — local-first, human-in-the-loop, audit everything, detection only
7. **Running Tests** — `python -m pytest tests/ -v`
8. **Scripts table** — script name, purpose, one row per script

## Key Implementation Notes

1. **watchdog vs polling**: Use `watchdog.observers.Observer` with `PatternMatchingEventHandler(patterns=["*.md"], ignore_directories=True)`. This replaces the manual polling loop from the previous implementation.

2. **Watcher-processor integration**: The watcher's `on_created()` handler directly calls `process_file()` from `process_inbox.py`. This means detection + processing happen in one flow (no separate manual `process_inbox.py` run needed when watcher is active).

3. **Standalone mode**: `process_inbox.py` can still be run standalone to batch-process all files in `Needs_Action/` (useful for catch-up after watcher was stopped).

4. **Dashboard updates**: `update_dashboard.py` runs after processing to refresh counts. The watcher can optionally call it after each file, or it can be run on-demand.

5. **Testing**: Tests use `tmp_path` fixtures to create isolated vault structures. Watcher tests mock the Observer to avoid real filesystem events in CI.

## Complexity Tracking

No constitution violations to justify. All principles pass cleanly.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | - | - |
