# File Watcher Skill

## Purpose
Monitor the Needs_Action/ directory for new .md files using watchdog, automatically trigger processing on detection, and maintain a deduplication ledger.

## When to Use
- When starting the AI Employee's file monitoring loop
- When you need event-driven detection of new task files
- When batch-scanning Needs_Action/ for pending files
- User asks to "start watcher", "watch for tasks", or "monitor inbox"

## Commands
```bash
# Start watchdog observer (default 5s check interval)
python scripts/watcher.py

# Custom vault path and interval
python scripts/watcher.py --vault-path /path/to/vault --interval 2
```

## Configuration
Set in `.env`:
- `VAULT_PATH` — Path to vault root (default: parent of scripts/)

Requires: `pip install watchdog`

## Key Functions
| Function | Purpose |
|----------|---------|
| `start_watcher` | Start watchdog Observer on Needs_Action/ |
| `scan_needs_action` | Batch list all .md files (no watchdog needed) |
| `TaskFileHandler` | Watchdog handler for .md file creation events |
| `load_ledger` / `save_to_ledger` | Deduplication ledger I/O |

## How It Works
1. Watchdog Observer monitors `Needs_Action/` for new `.md` files
2. On file creation, checks deduplication ledger to skip already-seen files
3. Logs detection to audit trail
4. Triggers `process_inbox.process_file()` for automatic processing
5. Updates ledger on disk

## Integration
- Deduplication ledger at `Logs/.watcher_ledger.txt`
- All events logged to `Logs/*.audit.jsonl` via AuditLogger
- Triggers `process_inbox.py` for each new file detected
- Used by the Bronze Tier AI Employee pipeline

## Script
`scripts/watcher.py`
