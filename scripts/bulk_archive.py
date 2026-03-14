"""Bulk archive stale tasks from Needs_Action/ to Archive/.

Moves .md files older than a configurable age threshold (default 48h)
to Archive/, updates frontmatter with archived status, and logs actions.

Usage:
    python scripts/bulk_archive.py                # Dry run (preview)
    python scripts/bulk_archive.py --execute      # Actually move files
    python scripts/bulk_archive.py --age 72       # Custom age in hours
    python scripts/bulk_archive.py --execute --age 24
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger

load_dotenv()


def get_file_age_hours(filepath: Path) -> float:
    """Return age of file in hours based on modification time."""
    mtime = datetime.fromtimestamp(os.path.getmtime(filepath), tz=timezone.utc)
    now = datetime.now(timezone.utc)
    return (now - mtime).total_seconds() / 3600


def update_frontmatter(content: str) -> str:
    """Add archived status and timestamp to YAML frontmatter."""
    now_iso = datetime.now(timezone.utc).isoformat()

    # Match existing frontmatter
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if fm_match:
        fm_body = fm_match.group(1)
        # Replace status if exists, otherwise add it
        if re.search(r'^status:', fm_body, re.MULTILINE):
            fm_body = re.sub(r'^status:.*$', 'status: archived', fm_body, flags=re.MULTILINE)
        else:
            fm_body += '\nstatus: archived'
        fm_body += f'\narchived_at: "{now_iso}"'
        return f'---\n{fm_body}\n---\n' + content[fm_match.end():]
    else:
        # No frontmatter — add one
        return f'---\nstatus: archived\narchived_at: "{now_iso}"\n---\n\n{content}'


def scan_stale_files(needs_action: Path, age_threshold: float) -> list[tuple[Path, float]]:
    """Return list of (filepath, age_hours) for files older than threshold."""
    if not needs_action.exists():
        return []
    stale = []
    for f in sorted(needs_action.glob("*.md")):
        age = get_file_age_hours(f)
        if age > age_threshold:
            stale.append((f, age))
    return stale


def archive_files(
    vault_path: Path,
    age_threshold: float = 48.0,
    execute: bool = False,
) -> dict:
    """Archive stale files from Needs_Action/ to Archive/.

    Returns summary dict with counts and file lists.
    """
    needs_action = vault_path / "Needs_Action"
    archive_dir = vault_path / "Archive"
    ledger_path = vault_path / "Logs" / ".watcher_ledger.txt"

    stale = scan_stale_files(needs_action, age_threshold)
    recent_count = len(list(needs_action.glob("*.md"))) - len(stale)

    result = {
        "stale_count": len(stale),
        "recent_count": recent_count,
        "archived": [],
        "errors": [],
        "dry_run": not execute,
    }

    if not execute:
        result["archived"] = [f.name for f, _ in stale]
        return result

    # Create archive dir
    archive_dir.mkdir(parents=True, exist_ok=True)

    logger = AuditLogger(vault_path)

    for filepath, age in stale:
        try:
            # Read and update content
            content = filepath.read_text(encoding="utf-8")
            updated = update_frontmatter(content)

            # Handle filename conflicts
            dest = archive_dir / filepath.name
            if dest.exists():
                stem = filepath.stem
                ts = datetime.now().strftime("%H%M%S")
                dest = archive_dir / f"{stem}_{ts}.md"

            # Write to Archive/ first, then delete original
            dest.write_text(updated, encoding="utf-8")
            filepath.unlink()

            result["archived"].append(filepath.name)

            logger.log(
                "task_archived",
                filepath.name,
                "success",
                details={"age_hours": round(age, 1), "destination": str(dest)},
            )
        except Exception as exc:
            result["errors"].append({"file": filepath.name, "error": str(exc)})
            logger.log(
                "archive_error",
                filepath.name,
                "error",
                error=str(exc),
            )

    # Update watcher ledger with archived filenames
    if result["archived"] and ledger_path.exists():
        existing = set(ledger_path.read_text(encoding="utf-8").splitlines())
        new_entries = [name for name in result["archived"] if name not in existing]
        if new_entries:
            with open(ledger_path, "a", encoding="utf-8") as f:
                for name in new_entries:
                    f.write(name + "\n")

    logger.log(
        "bulk_archive_complete",
        "system",
        "success",
        details={
            "archived_count": len(result["archived"]),
            "error_count": len(result["errors"]),
            "age_threshold": age_threshold,
        },
    )

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk archive stale tasks from Needs_Action/")
    parser.add_argument("--execute", action="store_true", help="Actually move files (default: dry run)")
    parser.add_argument("--age", type=float, default=48.0, help="Age threshold in hours (default: 48)")
    parser.add_argument("--vault-path", default=None, help="Path to vault")
    args = parser.parse_args()

    vault = Path(args.vault_path or os.getenv("VAULT_PATH", str(Path(__file__).parent.parent)))

    print(f"{'EXECUTE' if args.execute else 'DRY RUN'} — Archive tasks older than {args.age}h")
    print(f"Vault: {vault}")
    print()

    result = archive_files(vault, age_threshold=args.age, execute=args.execute)

    print(f"Stale files (>{args.age}h): {result['stale_count']}")
    print(f"Recent files (kept):        {result['recent_count']}")
    print(f"Archived:                   {len(result['archived'])}")

    if result["errors"]:
        print(f"Errors:                     {len(result['errors'])}")
        for err in result["errors"][:5]:
            print(f"  ERROR: {err['file']} — {err['error']}")

    if not args.execute and result["stale_count"] > 0:
        print(f"\nRun with --execute to archive {result['stale_count']} files.")


if __name__ == "__main__":
    main()
