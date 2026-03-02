"""Vault delegation — structured file-based communication between Cloud and Local.

Platinum Tier: Cloud creates tasks in domain folders, Local picks up and executes.
Uses structured YAML frontmatter for metadata.

Usage:
    from vault_delegation import VaultDelegation

    vd = VaultDelegation(vault_path)
    vd.create_task("EMAIL", "Triage: invoice from vendor", "cloud")
    vd.promote_to_approval(task_path, "EMAIL")
    vd.write_update("Cloud processed 5 emails", "cloud")
"""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path


class VaultDelegation:
    """Structured vault-based communication between Cloud and Local agents."""

    def __init__(self, vault_path: str | Path | None = None):
        self.vault_path = Path(vault_path or os.environ.get("VAULT_PATH", "."))

    def _ensure_dir(self, *parts: str) -> Path:
        d = self.vault_path / Path(*parts)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def create_task(self, domain: str, content: str, created_by: str = "cloud") -> Path:
        """Create a new task file in Needs_Action/<domain>/.

        Returns the path to the created file.
        """
        task_dir = self._ensure_dir("Needs_Action", domain)
        ts = time.strftime("%Y%m%d_%H%M%S")
        task_file = task_dir / f"TASK_{ts}.md"

        frontmatter = f"""---
domain: {domain}
created_by: {created_by}
created_at: {time.strftime('%Y-%m-%d %H:%M:%S')}
status: needs_action
---

"""
        task_file.write_text(frontmatter + content, encoding="utf-8")
        return task_file

    def create_plan(self, domain: str, content: str, created_by: str = "cloud") -> Path:
        """Create a plan file in Plans/<domain>/."""
        plan_dir = self._ensure_dir("Plans", domain)
        ts = time.strftime("%Y%m%d_%H%M%S")
        plan_file = plan_dir / f"PLAN_{ts}.md"

        frontmatter = f"""---
domain: {domain}
created_by: {created_by}
created_at: {time.strftime('%Y-%m-%d %H:%M:%S')}
status: planned
---

"""
        plan_file.write_text(frontmatter + content, encoding="utf-8")
        return plan_file

    def promote_to_approval(self, task_path: str | Path, domain: str) -> Path:
        """Move a task from Needs_Action/ or Plans/ to Pending_Approval/<domain>/."""
        src = Path(task_path)
        if not src.is_absolute():
            src = self.vault_path / src
        dest_dir = self._ensure_dir("Pending_Approval", domain)
        dest = dest_dir / src.name

        shutil.move(str(src), str(dest))
        return dest

    def write_update(self, content: str, zone: str = "cloud") -> Path:
        """Write a status update to Updates/."""
        updates_dir = self._ensure_dir("Updates")
        ts = time.strftime("%Y%m%d_%H%M%S")
        update_file = updates_dir / f"UPDATE_{zone}_{ts}.md"

        frontmatter = f"""---
type: status_update
zone: {zone}
created_at: {time.strftime('%Y-%m-%d %H:%M:%S')}
---

"""
        update_file.write_text(frontmatter + content, encoding="utf-8")
        return update_file

    def read_updates(self) -> list[Path]:
        """List all unarchived update files in Updates/."""
        updates_dir = self.vault_path / "Updates"
        if not updates_dir.exists():
            return []
        return sorted(
            f for f in updates_dir.iterdir()
            if f.is_file() and f.name.startswith("UPDATE_") and f.suffix == ".md"
        )

    def merge_updates(self) -> int:
        """Process updates and archive them. Returns count of processed updates."""
        updates = self.read_updates()
        if not updates:
            return 0

        archive_dir = self._ensure_dir("Updates", "archived")
        count = 0
        for f in updates:
            dest = archive_dir / f.name
            shutil.move(str(f), str(dest))
            count += 1
        return count
