# Bulk Archive Skill

## Purpose
Archive stale task files from Needs_Action/ to Archive/. Moves .md files older than a configurable age threshold, updates frontmatter with archived status, and logs all actions.

## When to Use
- When Needs_Action/ has accumulated old unprocessed tasks
- When performing periodic vault maintenance
- User asks to "clean up tasks", "archive old items", or "bulk archive"

## Commands
```bash
# Dry run — preview what would be archived (default)
python scripts/bulk_archive.py

# Actually move files (48h threshold)
python scripts/bulk_archive.py --execute

# Custom age threshold (e.g., 24 hours)
python scripts/bulk_archive.py --execute --age 24

# Custom vault path
python scripts/bulk_archive.py --execute --vault-path /path/to/vault
```

## Configuration
Set in `.env`:
- `VAULT_PATH` — Path to vault root (default: parent of scripts/)

## Key Functions
| Function | Purpose |
|----------|---------|
| `archive_files` | Main archival logic; returns summary dict |
| `scan_stale_files` | Find files older than threshold |
| `update_frontmatter` | Add `status: archived` and `archived_at` timestamp |
| `get_file_age_hours` | Calculate file age from modification time |

## Behavior
1. Scans `Needs_Action/` for `.md` files older than threshold (default 48h)
2. In dry-run mode (default), lists files that would be archived
3. With `--execute`, moves files to `Archive/`:
   - Updates YAML frontmatter with `status: archived` and `archived_at` timestamp
   - Handles filename conflicts by appending a timestamp
   - Writes to Archive/ first, then deletes original (safe write)
4. Updates watcher ledger with archived filenames
5. Logs each archival and final summary to audit trail

## Integration
- Reads from `Needs_Action/`, writes to `Archive/`
- Updates `Logs/.watcher_ledger.txt` to prevent re-processing
- All actions logged to `Logs/*.audit.jsonl`

## Script
`scripts/bulk_archive.py`
