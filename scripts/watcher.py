"""File system watcher — monitors Needs_Action/ for new .md files using watchdog.

Uses watchdog's PatternMatchingEventHandler for event-driven detection.
Logs every detection to Logs/YYYY-MM-DD.audit.jsonl and maintains a
deduplication ledger at Logs/.watcher_ledger.txt.

Usage:
    python scripts/watcher.py [--vault-path /path/to/vault]
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler, FileCreatedEvent

# Allow imports from scripts/
sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger


# ---------------------------------------------------------------------------
# Deduplication ledger
# ---------------------------------------------------------------------------

def load_ledger(path: Path) -> set[str]:
    """Read ledger file into a set of filenames. Returns empty set if missing."""
    if not path.exists():
        return set()
    try:
        return set(path.read_text(encoding="utf-8").splitlines())
    except Exception:
        return set()


def save_to_ledger(path: Path, filename: str) -> None:
    """Append a single filename to the ledger file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(filename + "\n")


# ---------------------------------------------------------------------------
# Watchdog event handler
# ---------------------------------------------------------------------------

class TaskFileHandler(PatternMatchingEventHandler):
    """Handles new .md file creation events in Needs_Action/."""

    def __init__(
        self,
        vault_path: Path,
        logger: AuditLogger,
        ledger_path: Path,
    ) -> None:
        super().__init__(patterns=["*.md"], ignore_directories=True)
        self.vault_path = vault_path
        self.logger = logger
        self.ledger_path = ledger_path
        self._seen: set[str] = load_ledger(ledger_path)

    def on_created(self, event: FileCreatedEvent) -> None:
        """Called when a new .md file is created in Needs_Action/."""
        file_path = Path(event.src_path)
        filename = file_path.name

        # Deduplication check
        if filename in self._seen:
            return

        # Log detection
        self.logger.log(
            "file_detected",
            filename,
            "success",
            details={"file": filename, "path": str(file_path)},
        )
        print(f"  [DETECTED] {filename}")

        # Update ledger (memory + disk)
        self._seen.add(filename)
        save_to_ledger(self.ledger_path, filename)

        # Trigger processing
        try:
            from process_inbox import process_file
            result = process_file(file_path, self.vault_path, self.logger)
            print(f"  [PROCESSED] {filename} -> {result}")
        except Exception as exc:
            self.logger.log(
                "process_error", filename, "error", error=str(exc)
            )
            print(f"  [ERROR] {filename}: {exc}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def start_watcher(vault_path: Path, interval: float = 5.0) -> None:
    """Start watchdog Observer on Needs_Action/ directory."""
    needs_action = vault_path / "Needs_Action"
    needs_action.mkdir(parents=True, exist_ok=True)

    logger = AuditLogger(vault_path)
    ledger_path = vault_path / "Logs" / ".watcher_ledger.txt"

    handler = TaskFileHandler(vault_path, logger, ledger_path)
    observer = Observer()
    observer.schedule(handler, str(needs_action), recursive=False)

    print("=== Bronze Tier AI Employee Watcher ===")
    print(f"Vault: {vault_path}")
    print(f"Watching: {needs_action}/")
    print(f"Ledger: {ledger_path}")
    print(f"Already seen: {len(handler._seen)} files")
    print("Press Ctrl+C to stop.\n")

    logger.log("watcher_started", "system", "success",
               details={"vault": str(vault_path)})

    observer.start()
    try:
        while True:
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopping watcher...")
    finally:
        observer.stop()
        observer.join()
        logger.log("watcher_stopped", "system", "success")
        print("Watcher stopped.")


# Keep scan_needs_action for batch processing and tests
def scan_needs_action(vault: Path) -> list[Path]:
    """Return all .md files in Needs_Action/ folder."""
    folder = vault / "Needs_Action"
    if not folder.exists():
        return []
    return sorted(folder.glob("*.md"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Watch Needs_Action/ for new tasks")
    parser.add_argument("--vault-path", default=None, help="Path to Obsidian vault")
    parser.add_argument("--interval", type=float, default=5.0, help="Check interval seconds")
    args = parser.parse_args()

    vault = Path(args.vault_path or os.getenv("VAULT_PATH",
                 str(Path(__file__).parent.parent)))
    start_watcher(vault, args.interval)
