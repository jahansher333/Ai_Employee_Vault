"""Tests for the watchdog-based file system watcher."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from watcher import (
    TaskFileHandler,
    load_ledger,
    save_to_ledger,
    scan_needs_action,
)
from audit_logger import AuditLogger


@pytest.fixture
def vault(tmp_path):
    (tmp_path / "Needs_Action").mkdir()
    (tmp_path / "Done").mkdir()
    (tmp_path / "Logs").mkdir()
    (tmp_path / "Pending_Approval").mkdir()
    return tmp_path


class TestScanNeedsAction:
    def test_empty_folder(self, vault):
        files = scan_needs_action(vault)
        assert files == []

    def test_finds_md_files(self, vault):
        (vault / "Needs_Action" / "task1.md").write_text("# Task 1")
        (vault / "Needs_Action" / "task2.md").write_text("# Task 2")
        files = scan_needs_action(vault)
        assert len(files) == 2

    def test_ignores_non_md_files(self, vault):
        (vault / "Needs_Action" / "notes.txt").write_text("not markdown")
        (vault / "Needs_Action" / "task.md").write_text("# Task")
        files = scan_needs_action(vault)
        assert len(files) == 1
        assert files[0].name == "task.md"

    def test_missing_folder(self, tmp_path):
        files = scan_needs_action(tmp_path / "nonexistent")
        assert files == []


class TestLedger:
    def test_load_empty_ledger(self, vault):
        ledger_path = vault / "Logs" / ".watcher_ledger.txt"
        result = load_ledger(ledger_path)
        assert result == set()

    def test_save_and_load_roundtrip(self, vault):
        ledger_path = vault / "Logs" / ".watcher_ledger.txt"
        save_to_ledger(ledger_path, "file1.md")
        save_to_ledger(ledger_path, "file2.md")
        loaded = load_ledger(ledger_path)
        assert loaded == {"file1.md", "file2.md"}

    def test_incremental_append(self, vault):
        ledger_path = vault / "Logs" / ".watcher_ledger.txt"
        save_to_ledger(ledger_path, "file1.md")
        save_to_ledger(ledger_path, "file2.md")
        loaded = load_ledger(ledger_path)
        assert "file1.md" in loaded
        assert "file2.md" in loaded


class TestTaskFileHandler:
    def test_on_created_detects_new_file(self, vault):
        logger = AuditLogger(vault)
        ledger_path = vault / "Logs" / ".watcher_ledger.txt"
        handler = TaskFileHandler(vault, logger, ledger_path)

        # Create a task file for the handler to process
        task_file = vault / "Needs_Action" / "test-task.md"
        task_file.write_text(
            "---\ntype: task\npriority: high\nstatus: new\n---\n\n# Test\n\nBody\n"
        )

        # Simulate on_created event
        event = MagicMock()
        event.src_path = str(task_file)
        event.is_directory = False

        handler.on_created(event)

        # Verify: logged, in ledger, processed
        entries = logger.read_log()
        actions = [e["action"] for e in entries]
        assert "file_detected" in actions
        assert "test-task.md" in handler._seen

    def test_on_created_skips_duplicate(self, vault):
        logger = AuditLogger(vault)
        ledger_path = vault / "Logs" / ".watcher_ledger.txt"
        # Pre-populate ledger
        save_to_ledger(ledger_path, "already-seen.md")

        handler = TaskFileHandler(vault, logger, ledger_path)

        task_file = vault / "Needs_Action" / "already-seen.md"
        task_file.write_text("# Already seen")

        event = MagicMock()
        event.src_path = str(task_file)
        event.is_directory = False

        handler.on_created(event)

        # Should NOT log file_detected (it's in ledger)
        entries = logger.read_log()
        assert len(entries) == 0

    def test_handler_creates_missing_ledger_dir(self, tmp_path):
        vault = tmp_path / "new_vault"
        vault.mkdir()
        (vault / "Needs_Action").mkdir()
        (vault / "Logs").mkdir()

        logger = AuditLogger(vault)
        ledger_path = vault / "Logs" / ".watcher_ledger.txt"

        handler = TaskFileHandler(vault, logger, ledger_path)
        assert handler._seen == set()
