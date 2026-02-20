# Bronze Tier Reference

This folder contains reference documentation for the Bronze Tier implementation.
The actual Bronze Tier scripts remain in `scripts/` as they are still actively used
by the Silver Tier (file watcher, process_inbox, audit_logger, dashboard updater).

## Bronze Tier Components

| Component | Location | Status |
|-----------|----------|--------|
| File Watcher | `scripts/watcher.py` | Active (Silver reuses) |
| Task Processor | `scripts/process_inbox.py` | Active (Silver reuses) |
| Audit Logger | `scripts/audit_logger.py` | Active (Silver reuses) |
| Dashboard Updater | `scripts/update_dashboard.py` | Active (Silver reuses) |
| SimpleTaskReaderSkill | `.claude/skills/simple-task-reader.md` | Active |

## Bronze Tier Specs

Full Bronze Tier specification artifacts are in `specs/002-bronze-foundation/`.

## What Bronze Tier Delivered

- Watchdog-based file system watcher monitoring `Needs_Action/`
- Task processing with action plan generation
- Sensitive content detection and routing to `Pending_Approval/`
- Append-only JSON Lines audit logging
- Dashboard.md with pending tasks table
- 46 passing tests
