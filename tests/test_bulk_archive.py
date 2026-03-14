"""Tests for bulk_archive.py — stale task archival."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from scripts.bulk_archive import (
    archive_files,
    get_file_age_hours,
    scan_stale_files,
    update_frontmatter,
)


@pytest.fixture
def vault(tmp_path):
    """Create a minimal vault structure."""
    (tmp_path / "Needs_Action").mkdir()
    (tmp_path / "Logs").mkdir()
    (tmp_path / "Logs" / ".watcher_ledger.txt").write_text("", encoding="utf-8")
    return tmp_path


def _create_task(vault: Path, name: str, age_seconds: float = 0) -> Path:
    """Create a task file, optionally backdated."""
    content = f"---\ntype: task\nstatus: new\npriority: medium\n---\n\n# {name}\n\nTest task.\n"
    fp = vault / "Needs_Action" / f"{name}.md"
    fp.write_text(content, encoding="utf-8")
    if age_seconds > 0:
        old_time = time.time() - age_seconds
        os.utime(fp, (old_time, old_time))
    return fp


class TestUpdateFrontmatter:
    def test_adds_archived_status(self):
        content = "---\ntype: task\nstatus: new\n---\n\n# Hello\n"
        result = update_frontmatter(content)
        assert "status: archived" in result
        assert "archived_at:" in result
        assert "status: new" not in result

    def test_no_frontmatter(self):
        content = "# Just a heading\n\nSome text.\n"
        result = update_frontmatter(content)
        assert "status: archived" in result
        assert "archived_at:" in result
        assert "# Just a heading" in result

    def test_preserves_other_fields(self):
        content = "---\ntype: email\npriority: high\nstatus: planned\n---\n\n# Task\n"
        result = update_frontmatter(content)
        assert "type: email" in result
        assert "priority: high" in result
        assert "status: archived" in result


class TestScanStaleFiles:
    def test_finds_stale_files(self, vault):
        _create_task(vault, "old-task", age_seconds=72 * 3600)  # 72h old
        _create_task(vault, "new-task", age_seconds=0)  # just created

        stale = scan_stale_files(vault / "Needs_Action", age_threshold=48.0)
        names = [f.name for f, _ in stale]
        assert "old-task.md" in names
        assert "new-task.md" not in names

    def test_empty_folder(self, vault):
        stale = scan_stale_files(vault / "Needs_Action", age_threshold=48.0)
        assert stale == []

    def test_missing_folder(self, tmp_path):
        stale = scan_stale_files(tmp_path / "nonexistent", age_threshold=48.0)
        assert stale == []


class TestArchiveFiles:
    def test_dry_run_does_not_move(self, vault):
        _create_task(vault, "stale-task", age_seconds=72 * 3600)

        result = archive_files(vault, age_threshold=48.0, execute=False)
        assert result["dry_run"] is True
        assert result["stale_count"] == 1
        assert (vault / "Needs_Action" / "stale-task.md").exists()
        assert not (vault / "Archive").exists()

    def test_execute_moves_old_files(self, vault):
        _create_task(vault, "old-email", age_seconds=72 * 3600)
        _create_task(vault, "fresh-task", age_seconds=0)

        result = archive_files(vault, age_threshold=48.0, execute=True)
        assert result["dry_run"] is False
        assert len(result["archived"]) == 1
        assert "old-email.md" in result["archived"]

        # Old file moved
        assert not (vault / "Needs_Action" / "old-email.md").exists()
        assert (vault / "Archive" / "old-email.md").exists()

        # Fresh file kept
        assert (vault / "Needs_Action" / "fresh-task.md").exists()

    def test_archive_folder_created(self, vault):
        _create_task(vault, "task1", age_seconds=72 * 3600)
        assert not (vault / "Archive").exists()

        archive_files(vault, age_threshold=48.0, execute=True)
        assert (vault / "Archive").is_dir()

    def test_frontmatter_updated_in_archive(self, vault):
        _create_task(vault, "archived-task", age_seconds=72 * 3600)

        archive_files(vault, age_threshold=48.0, execute=True)
        content = (vault / "Archive" / "archived-task.md").read_text(encoding="utf-8")
        assert "status: archived" in content
        assert "archived_at:" in content

    def test_recent_files_kept(self, vault):
        _create_task(vault, "keep-me", age_seconds=1 * 3600)  # 1h old

        result = archive_files(vault, age_threshold=48.0, execute=True)
        assert result["stale_count"] == 0
        assert (vault / "Needs_Action" / "keep-me.md").exists()

    def test_custom_age_threshold(self, vault):
        _create_task(vault, "medium-age", age_seconds=25 * 3600)  # 25h old

        # Not stale at 48h threshold
        result = archive_files(vault, age_threshold=48.0, execute=False)
        assert result["stale_count"] == 0

        # Stale at 24h threshold
        result = archive_files(vault, age_threshold=24.0, execute=False)
        assert result["stale_count"] == 1

    def test_ledger_updated(self, vault):
        _create_task(vault, "ledger-test", age_seconds=72 * 3600)
        ledger = vault / "Logs" / ".watcher_ledger.txt"

        archive_files(vault, age_threshold=48.0, execute=True)
        content = ledger.read_text(encoding="utf-8")
        assert "ledger-test.md" in content
