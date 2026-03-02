"""Vault sync — Git-based sync between Cloud and Local with security exclusions.

Platinum Tier: Keeps the Obsidian vault synchronized between Cloud VM and
Local machine. Validates that secrets are never synced.

Usage:
    python scripts/vault_sync.py --once          # Single sync cycle
    python scripts/vault_sync.py --daemon         # Continuous sync
    python scripts/vault_sync.py --check          # Check sync status
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger


# ---------------------------------------------------------------------------
# Security exclusions — files that MUST NEVER be synced
# ---------------------------------------------------------------------------

EXCLUDED_PATTERNS = [
    ".env",
    ".env.*",
    "credentials.json",
    "token.json",
    "token.json.bak",
    "*.session",
]


@dataclass
class SyncResult:
    """Result of a sync operation."""
    files_changed: int = 0
    conflicts: list[str] = field(default_factory=list)
    status: str = "success"  # success | conflict | error | no_changes
    error: str | None = None


class VaultSync:
    """Git-based vault sync with security exclusions."""

    def __init__(
        self,
        vault_path: str | Path | None = None,
        remote: str = "origin",
        branch: str = "vault-sync",
    ):
        self.vault_path = Path(vault_path or os.environ.get("VAULT_PATH", "."))
        self.remote = remote
        self.branch = branch
        self.zone = os.environ.get("ZONE_MODE", "unknown")

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command in the vault directory."""
        cmd = ["git"] + list(args)
        return subprocess.run(
            cmd,
            cwd=str(self.vault_path),
            capture_output=True,
            text=True,
            check=check,
        )

    def validate_exclusions(self) -> list[str]:
        """Check staged files for secrets and unstage them.

        Returns list of files that were unstaged.
        """
        result = self._git("diff", "--cached", "--name-only", check=False)
        if result.returncode != 0:
            return []

        staged = result.stdout.strip().splitlines()
        unstaged = []

        for f in staged:
            fname = Path(f).name
            for pattern in EXCLUDED_PATTERNS:
                if pattern.startswith("*"):
                    if fname.endswith(pattern[1:]):
                        self._git("reset", "HEAD", "--", f, check=False)
                        unstaged.append(f)
                        break
                elif pattern.endswith("*"):
                    if fname.startswith(pattern[:-1]):
                        self._git("reset", "HEAD", "--", f, check=False)
                        unstaged.append(f)
                        break
                elif fname == pattern or f == pattern:
                    self._git("reset", "HEAD", "--", f, check=False)
                    unstaged.append(f)
                    break

        return unstaged

    def sync(self) -> SyncResult:
        """Run a full sync cycle: add, validate, commit, pull, push."""
        result = SyncResult()

        try:
            # Stage all changes
            self._git("add", "-A")

            # Validate security exclusions
            unstaged = self.validate_exclusions()
            if unstaged:
                print(f"  [SECURITY] Unstaged {len(unstaged)} secret files: {unstaged}")

            # Check if there are changes to commit
            status = self._git("status", "--porcelain", check=False)
            if not status.stdout.strip():
                result.status = "no_changes"
                return result

            # Commit
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            msg = f"auto-sync {self.zone} {ts}"
            self._git("commit", "-m", msg, check=False)

            # Pull with rebase
            pull = self._git(
                "pull", "--rebase", self.remote, self.branch,
                check=False,
            )

            if pull.returncode != 0:
                # Check for conflicts
                if "CONFLICT" in pull.stdout or "CONFLICT" in pull.stderr:
                    conflicts = self._extract_conflicts(pull.stdout + pull.stderr)
                    result.conflicts = conflicts
                    result.status = "conflict"
                    self._write_conflict_alert(conflicts)
                    # Abort rebase to recover
                    self._git("rebase", "--abort", check=False)
                    return result
                # Other pull error — try push anyway
                result.error = pull.stderr.strip()

            # Push
            push = self._git("push", self.remote, self.branch, check=False)
            if push.returncode != 0:
                result.error = push.stderr.strip()
                result.status = "error"
                return result

            # Count changes
            log = self._git("log", "--oneline", "-1", "--stat", check=False)
            if log.stdout:
                lines = log.stdout.strip().splitlines()
                for line in lines:
                    if "file" in line and "changed" in line:
                        parts = line.strip().split()
                        if parts[0].isdigit():
                            result.files_changed = int(parts[0])

            result.status = "success"

        except subprocess.CalledProcessError as e:
            result.status = "error"
            result.error = str(e)
        except Exception as e:
            result.status = "error"
            result.error = str(e)

        return result

    def _extract_conflicts(self, output: str) -> list[str]:
        """Extract conflicting file paths from git output."""
        conflicts = []
        for line in output.splitlines():
            if "CONFLICT" in line and ":" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    conflicts.append(parts[-1].strip())
        return conflicts

    def _write_conflict_alert(self, conflicts: list[str]) -> None:
        """Write a conflict alert to Updates/."""
        updates_dir = self.vault_path / "Updates"
        updates_dir.mkdir(parents=True, exist_ok=True)

        ts = time.strftime("%Y%m%d_%H%M%S")
        alert_file = updates_dir / f"SYNC_CONFLICT_{ts}.md"
        content = f"""---
type: sync_conflict
zone: {self.zone}
detected_at: {time.strftime('%Y-%m-%d %H:%M:%S')}
---

## Sync Conflict Detected

**Zone**: {self.zone}
**Files with conflicts**:

"""
        for c in conflicts:
            content += f"- `{c}`\n"

        content += "\n**Action required**: Resolve conflicts manually and re-sync.\n"
        alert_file.write_text(content, encoding="utf-8")

    def check_status(self) -> dict:
        """Check current sync status."""
        status = self._git("status", "--porcelain", check=False)
        log = self._git("log", "--oneline", "-1", check=False)

        return {
            "has_changes": bool(status.stdout.strip()),
            "last_commit": log.stdout.strip() if log.returncode == 0 else "none",
            "branch": self.branch,
            "remote": self.remote,
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Vault sync (Git-based)")
    parser.add_argument("--once", action="store_true", help="Single sync cycle")
    parser.add_argument("--daemon", action="store_true", help="Continuous sync loop")
    parser.add_argument("--check", action="store_true", help="Check sync status")
    parser.add_argument("--vault-path", default=None)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", default=os.environ.get("SYNC_BRANCH", "vault-sync"))
    parser.add_argument("--interval", type=int,
                        default=int(os.environ.get("SYNC_INTERVAL", "120")))
    args = parser.parse_args()

    vault = args.vault_path or os.environ.get("VAULT_PATH", ".")
    syncer = VaultSync(vault, args.remote, args.branch)

    if args.check:
        status = syncer.check_status()
        print(f"Branch: {status['branch']}")
        print(f"Remote: {status['remote']}")
        print(f"Pending changes: {status['has_changes']}")
        print(f"Last commit: {status['last_commit']}")
        return

    if args.once:
        result = syncer.sync()
        print(f"Sync result: {result.status} ({result.files_changed} files)")
        if result.conflicts:
            print(f"Conflicts: {result.conflicts}")
        if result.error:
            print(f"Error: {result.error}")
        return

    if args.daemon:
        print(f"Vault sync daemon — every {args.interval}s")
        while True:
            result = syncer.sync()
            ts = time.strftime("%H:%M:%S")
            print(f"[{ts}] Sync: {result.status} ({result.files_changed} files)")
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
