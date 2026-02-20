"""Tests for the inbox processor."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from process_inbox import (
    parse_frontmatter,
    serialize_frontmatter,
    is_sensitive,
    process_file,
    move_to_done,
    generate_action_plan,
)
from audit_logger import AuditLogger


@pytest.fixture
def vault(tmp_path):
    (tmp_path / "Needs_Action").mkdir()
    (tmp_path / "Done").mkdir()
    (tmp_path / "Logs").mkdir()
    (tmp_path / "Pending_Approval").mkdir()
    # Create Dashboard.md with markers
    dashboard = tmp_path / "Dashboard.md"
    dashboard.write_text(
        "# Dashboard\n\n"
        "<!-- START_PENDING_TASKS -->\n"
        "| Filename | Preview | Time | Priority |\n"
        "|----------|---------|------|----------|\n"
        "<!-- END_PENDING_TASKS -->\n"
    )
    return tmp_path


@pytest.fixture
def logger(vault):
    return AuditLogger(vault)


class TestParseFrontmatter:
    def test_with_frontmatter(self):
        content = "---\ntype: task\npriority: high\n---\n\n# Title\n\nBody text"
        fm, body = parse_frontmatter(content)
        assert fm["type"] == "task"
        assert fm["priority"] == "high"
        assert "# Title" in body

    def test_without_frontmatter(self):
        content = "# Just a heading\n\nSome text"
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_serialize_roundtrip(self):
        fm = {"type": "task", "priority": "high", "status": "new"}
        body = "# Title\n\nBody"
        result = serialize_frontmatter(fm, body)
        assert result.startswith("---\n")
        assert "type: task" in result
        assert "# Title" in result


class TestSensitiveDetection:
    def test_payment_is_sensitive(self):
        assert is_sensitive("Please process the payment for $500")

    def test_password_is_sensitive(self):
        assert is_sensitive("Reset the password for the admin account")

    def test_credential_is_sensitive(self):
        assert is_sensitive("Update the credential for the API service")

    def test_delete_is_sensitive(self):
        assert is_sensitive("Delete all old records from the database")

    def test_remove_is_sensitive(self):
        assert is_sensitive("Remove the user account from the system")

    def test_api_key_is_sensitive(self):
        assert is_sensitive("Rotate the API key for production")

    def test_normal_task_is_not_sensitive(self):
        assert not is_sensitive("Review the Q3 report and summarize findings")

    def test_case_insensitive(self):
        assert is_sensitive("PAYMENT required for vendor")
        assert is_sensitive("Delete the old backups")


class TestGenerateActionPlan:
    def test_generates_plan(self):
        fm = {"priority": "high", "category": "review"}
        body = "# Review Q3 Report\n\nPlease review."
        plan = generate_action_plan(fm, body)
        assert "## Action Plan" in plan
        assert "high" in plan
        assert "review" in plan
        assert "Review Q3 Report" in plan


class TestProcessFile:
    def test_process_new_task(self, vault, logger):
        task = vault / "Needs_Action" / "test-task.md"
        task.write_text(
            "---\ntype: task\npriority: high\ncategory: review\nstatus: new\n---\n\n"
            "# Review Q3 Report\n\nPlease review and summarize.\n"
        )
        result = process_file(task, vault, logger)
        assert result == "planned"
        content = task.read_text()
        assert "status: planned" in content
        assert "## Action Plan" in content

    def test_skip_already_planned(self, vault, logger):
        task = vault / "Needs_Action" / "planned-task.md"
        task.write_text(
            "---\nstatus: planned\n---\n\n# Already planned\n"
        )
        result = process_file(task, vault, logger)
        assert result == "skipped"

    def test_sensitive_routes_to_approval(self, vault, logger):
        task = vault / "Needs_Action" / "sensitive-task.md"
        task.write_text(
            "---\ntype: task\nstatus: new\n---\n\n"
            "# Process Payment\n\nProcess the payment of $5000.\n"
        )
        result = process_file(task, vault, logger)
        assert result == "pending_approval"
        approvals = list((vault / "Pending_Approval").glob("*.md"))
        assert len(approvals) == 1

    def test_appends_summary_to_dashboard(self, vault, logger):
        task = vault / "Needs_Action" / "summary-task.md"
        task.write_text(
            "---\ntype: task\npriority: medium\nstatus: new\n---\n\n"
            "# Write Report\n\nWrite the annual report.\n"
        )
        process_file(task, vault, logger)
        dashboard_content = (vault / "Dashboard.md").read_text()
        assert "summary-task.md" in dashboard_content
        assert "Write Report" in dashboard_content


class TestMoveToDone:
    def test_move_preserves_content(self, vault, logger):
        task = vault / "Needs_Action" / "done-task.md"
        task.write_text(
            "---\ntype: task\nstatus: planned\n---\n\n# Task\n\nBody\n"
        )
        move_to_done(task, vault, logger)
        assert not task.exists()
        done_files = list((vault / "Done").glob("*.md"))
        assert len(done_files) == 1
        content = done_files[0].read_text()
        assert "status: done" in content
        assert "completed_at:" in content
        assert "# Task" in content

    def test_move_handles_name_conflict(self, vault, logger):
        (vault / "Done" / "existing.md").write_text("old")
        task = vault / "Needs_Action" / "existing.md"
        task.write_text("---\nstatus: planned\n---\n\n# Task\n")
        move_to_done(task, vault, logger)
        assert not task.exists()
        done_files = list((vault / "Done").glob("*.md"))
        assert len(done_files) == 2
