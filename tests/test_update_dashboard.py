"""Tests for the dashboard updater."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from update_dashboard import count_folder, format_activity, update_dashboard
from audit_logger import AuditLogger


@pytest.fixture
def vault(tmp_path):
    (tmp_path / "Needs_Action").mkdir()
    (tmp_path / "Done").mkdir()
    (tmp_path / "Logs").mkdir()
    (tmp_path / "Pending_Approval").mkdir()
    return tmp_path


@pytest.fixture
def logger(vault):
    return AuditLogger(vault)


class TestCountFolder:
    def test_empty_folder(self, vault):
        assert count_folder(vault / "Needs_Action") == 0

    def test_with_md_files(self, vault):
        (vault / "Needs_Action" / "task1.md").write_text("# Task 1")
        (vault / "Needs_Action" / "task2.md").write_text("# Task 2")
        assert count_folder(vault / "Needs_Action") == 2

    def test_missing_folder(self, tmp_path):
        assert count_folder(tmp_path / "nonexistent") == 0

    def test_ignores_non_md(self, vault):
        (vault / "Needs_Action" / "task.md").write_text("# Task")
        (vault / "Needs_Action" / "notes.txt").write_text("text")
        assert count_folder(vault / "Needs_Action") == 1


class TestFormatActivity:
    def test_empty_entries(self):
        result = format_activity([])
        assert "No activity yet" in result

    def test_formats_entries(self):
        entries = [
            {
                "timestamp": "2026-02-17T14:30:00+00:00",
                "action": "file_detected",
                "outcome": "success",
                "input_ref": "task.md",
            }
        ]
        result = format_activity(entries)
        assert "[14:30]" in result
        assert "file_detected" in result
        assert "task.md" in result

    def test_limits_entries(self):
        entries = [
            {
                "timestamp": f"2026-02-17T14:{i:02d}:00+00:00",
                "action": "test",
                "outcome": "success",
                "input_ref": f"file{i}.md",
            }
            for i in range(20)
        ]
        result = format_activity(entries, limit=5)
        lines = [l for l in result.strip().split("\n") if l.startswith("-")]
        assert len(lines) == 5


class TestUpdateDashboard:
    def test_creates_dashboard(self, vault, logger):
        (vault / "Needs_Action" / "task.md").write_text("# Task")
        update_dashboard(vault, logger)
        dashboard = vault / "Dashboard.md"
        assert dashboard.exists()
        content = dashboard.read_text()
        assert "Needs_Action | 1" in content
        assert "<!-- START_PENDING_TASKS -->" in content
        assert "<!-- END_PENDING_TASKS -->" in content

    def test_accurate_counts(self, vault, logger):
        (vault / "Needs_Action" / "t1.md").write_text("# T1")
        (vault / "Needs_Action" / "t2.md").write_text("# T2")
        (vault / "Done" / "d1.md").write_text("# D1")
        update_dashboard(vault, logger)
        content = (vault / "Dashboard.md").read_text(encoding="utf-8")
        assert "Needs_Action | 2" in content
        assert "Done | 1" in content

    def test_pending_tasks_table(self, vault, logger):
        (vault / "Needs_Action" / "review.md").write_text(
            "---\npriority: high\n---\n\n# Review Report\n"
        )
        update_dashboard(vault, logger)
        content = (vault / "Dashboard.md").read_text(encoding="utf-8")
        assert "review.md" in content
        assert "Review Report" in content

    def test_logs_dashboard_updated(self, vault, logger):
        update_dashboard(vault, logger)
        entries = logger.read_log(action_filter="dashboard_updated")
        assert len(entries) == 1
        assert entries[0]["outcome"] == "success"
