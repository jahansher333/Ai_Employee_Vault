# Research: Bronze Tier Foundation

**Feature**: 002-bronze-foundation
**Date**: 2026-02-17

## Decision 1: File System Monitoring Library

**Decision**: Use `watchdog` library with `PatternMatchingEventHandler`
**Rationale**: watchdog provides native OS-level file system events (inotify on Linux, FSEvents on macOS, ReadDirectoryChangesW on Windows) which are more efficient and responsive than manual polling. The `PatternMatchingEventHandler` natively filters for `*.md` patterns without custom code.
**Alternatives considered**:
- Manual polling with `os.listdir()` — simpler but slower, misses rapid file creation, wastes CPU cycles
- `inotify` directly — Linux-only, not cross-platform
- `aiofiles` / `asyncio` — adds complexity without benefit for this use case

## Decision 2: Watcher Architecture Pattern

**Decision**: Subclass `PatternMatchingEventHandler`, override `on_created()`, run `Observer` with try/finally cleanup
**Rationale**: This is the canonical watchdog pattern. `on_created()` fires only for new files (not modifications), which matches FR-001 exactly. The Observer handles threading internally.
**Alternatives considered**:
- `RegexMatchingEventHandler` — more powerful but unnecessary for simple `*.md` filtering
- Polling fallback (`PollingObserver`) — only needed if native events fail; can be a configurable option

## Decision 3: Deduplication Strategy

**Decision**: Plain text ledger file (`Logs/.watcher_ledger.txt`), one filename per line, loaded into a `set` at startup
**Rationale**: Simplest possible persistence. No dependencies. Easy to inspect and debug. Survives watcher restarts.
**Alternatives considered**:
- SQLite database — overkill for a list of filenames
- JSON file — adds parsing complexity for no benefit
- In-memory only — loses state on restart (violates FR-002)

## Decision 4: Audit Logging Format

**Decision**: JSON Lines (`.jsonl`), one file per day (`YYYY-MM-DD.audit.jsonl`), append-only via Python `json` + file open with `'a'` mode
**Rationale**: JSON Lines is human-readable, machine-parseable, and append-only by design. Daily rotation keeps files manageable. No external dependencies.
**Alternatives considered**:
- Python `logging` module — structured logging requires extra config; JSONL is simpler
- SQLite — queryable but violates "no external dependencies" simplicity goal
- CSV — less flexible for nested data in `details` field

## Decision 5: Dashboard Update Strategy

**Decision**: Template-based regeneration — read current Dashboard.md, update status table counts by scanning folders, append recent activity from audit log
**Rationale**: Full regeneration ensures dashboard always reflects actual filesystem state. No drift from incremental updates.
**Alternatives considered**:
- Incremental append-only — simpler but can drift from actual state
- Obsidian Dataview plugin — adds dependency on Obsidian plugin ecosystem

## Decision 6: Sensitive Content Detection

**Decision**: Case-insensitive substring matching against a fixed keyword list: payment, password, credential, delete, remove, api key
**Rationale**: Simple, predictable, zero false negatives for known keywords. Easy to extend. Matches FR-005 exactly.
**Alternatives considered**:
- Regex patterns — more flexible but harder to maintain and debug
- NLP-based classification — overkill for Bronze Tier; no external API calls allowed (Principle VI)

## Decision 7: Agent Skill Format

**Decision**: Markdown files in `.claude/skills/` with structured sections: Purpose, Trigger, Input, Steps, Output, Error Handling
**Rationale**: Markdown is native to Obsidian and Claude Code. Structured sections make skills machine-readable and human-readable. Matches FR-009.
**Alternatives considered**:
- YAML files — less readable in Obsidian
- Python modules — couples skills to implementation language
- JSON — poor readability
