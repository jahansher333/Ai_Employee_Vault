"""Claim-by-move protocol — atomic task claiming between Cloud and Local agents.

Platinum Tier: Prevents double-processing by using atomic os.rename() to claim
tasks. If two agents try to claim the same file, exactly one succeeds.

Usage:
    from claim_task import claim_task, complete_task, list_pending

    # Claim a task
    if claim_task("Pending_Approval/EMAIL/TASK_20260301.md", "local"):
        process(...)
        complete_task("In_Progress/local/TASK_20260301.md")
"""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path


def _vault_path() -> Path:
    """Get the vault root path from env or default to cwd."""
    return Path(os.environ.get("VAULT_PATH", "."))


def claim_task(file_path: str | Path, agent_id: str) -> bool:
    """Atomically claim a task by moving it to In_Progress/<agent_id>/.

    Args:
        file_path: Path to the task file (relative to vault or absolute).
        agent_id: The agent claiming the task ("cloud" or "local").

    Returns:
        True if claim succeeded, False if another agent claimed it first.
    """
    vault = _vault_path()
    src = vault / file_path if not Path(file_path).is_absolute() else Path(file_path)
    dest_dir = vault / "In_Progress" / agent_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name

    try:
        os.rename(str(src), str(dest))
        return True
    except (FileNotFoundError, OSError):
        # File was already claimed by another agent or doesn't exist
        return False


def complete_task(file_path: str | Path) -> bool:
    """Move a claimed task from In_Progress/ to Done/.

    Args:
        file_path: Path to the task file in In_Progress/ (relative or absolute).

    Returns:
        True if move succeeded, False otherwise.
    """
    vault = _vault_path()
    src = vault / file_path if not Path(file_path).is_absolute() else Path(file_path)
    done_dir = vault / "Done"
    done_dir.mkdir(parents=True, exist_ok=True)

    # Add timestamp suffix to avoid name collisions in Done/
    stem = src.stem
    suffix = src.suffix
    ts = time.strftime("%Y%m%d_%H%M%S")
    dest = done_dir / f"{stem}_{ts}{suffix}"

    try:
        shutil.move(str(src), str(dest))
        return True
    except (FileNotFoundError, OSError):
        return False


def reject_task(file_path: str | Path) -> bool:
    """Move a task to Done/ with rejected status.

    Args:
        file_path: Path to the task file (relative or absolute).

    Returns:
        True if move succeeded, False otherwise.
    """
    vault = _vault_path()
    src = vault / file_path if not Path(file_path).is_absolute() else Path(file_path)

    # Append rejection note before moving
    try:
        with open(src, "a", encoding="utf-8") as f:
            f.write(f"\n\n---\n**Status**: REJECTED\n**Rejected at**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    except OSError:
        pass

    return complete_task(file_path)


def list_pending(domain: str | None = None) -> list[Path]:
    """List task files in Pending_Approval/ folders.

    Args:
        domain: Optional domain filter ("EMAIL", "SOCIAL", "ODOO").
                 If None, lists all domains.

    Returns:
        List of Path objects for pending task files.
    """
    vault = _vault_path()
    pending_root = vault / "Pending_Approval"

    if domain:
        search_dirs = [pending_root / domain]
    else:
        search_dirs = [d for d in pending_root.iterdir() if d.is_dir()] if pending_root.exists() else []

    results = []
    for d in search_dirs:
        if d.exists():
            results.extend(
                f for f in sorted(d.iterdir())
                if f.is_file() and f.name != ".gitkeep"
            )
    return results


def list_in_progress(agent_id: str | None = None) -> list[Path]:
    """List task files currently claimed by an agent.

    Args:
        agent_id: Optional agent filter ("cloud" or "local").
                   If None, lists all agents.

    Returns:
        List of Path objects for in-progress task files.
    """
    vault = _vault_path()
    ip_root = vault / "In_Progress"

    if agent_id:
        search_dirs = [ip_root / agent_id]
    else:
        search_dirs = [d for d in ip_root.iterdir() if d.is_dir()] if ip_root.exists() else []

    results = []
    for d in search_dirs:
        if d.exists():
            results.extend(
                f for f in sorted(d.iterdir())
                if f.is_file() and f.name != ".gitkeep"
            )
    return results
