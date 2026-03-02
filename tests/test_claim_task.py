"""Tests for claim_task.py — claim-by-move protocol."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from claim_task import claim_task, complete_task, list_pending, list_in_progress, reject_task


@pytest.fixture
def vault(tmp_path, monkeypatch):
    """Create a temporary vault structure."""
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    # Create domain folders
    for domain in ("EMAIL", "SOCIAL", "ODOO"):
        (tmp_path / "Pending_Approval" / domain).mkdir(parents=True)
        (tmp_path / "Needs_Action" / domain).mkdir(parents=True)
    (tmp_path / "In_Progress" / "cloud").mkdir(parents=True)
    (tmp_path / "In_Progress" / "local").mkdir(parents=True)
    (tmp_path / "Done").mkdir(parents=True)
    return tmp_path


class TestClaimTask:
    """Test atomic claim-by-move."""

    def test_successful_claim(self, vault):
        task = vault / "Pending_Approval" / "EMAIL" / "TASK_001.md"
        task.write_text("Test task content")

        result = claim_task("Pending_Approval/EMAIL/TASK_001.md", "local")
        assert result is True
        assert not task.exists()  # Removed from source
        assert (vault / "In_Progress" / "local" / "TASK_001.md").exists()

    def test_double_claim_fails(self, vault):
        task = vault / "Pending_Approval" / "EMAIL" / "TASK_002.md"
        task.write_text("Test task")

        # First claim succeeds
        assert claim_task("Pending_Approval/EMAIL/TASK_002.md", "local") is True
        # Second claim fails (file already moved)
        assert claim_task("Pending_Approval/EMAIL/TASK_002.md", "cloud") is False

    def test_claim_nonexistent_file(self, vault):
        result = claim_task("Pending_Approval/EMAIL/NONEXISTENT.md", "local")
        assert result is False

    def test_claim_creates_agent_dir(self, vault):
        task = vault / "Pending_Approval" / "SOCIAL" / "TASK_003.md"
        task.write_text("Social task")

        # Remove the agent dir to test auto-creation
        agent_dir = vault / "In_Progress" / "test_agent"
        assert not agent_dir.exists()

        result = claim_task("Pending_Approval/SOCIAL/TASK_003.md", "test_agent")
        assert result is True
        assert agent_dir.exists()


class TestCompleteTask:
    """Test completing a claimed task."""

    def test_complete_moves_to_done(self, vault):
        task = vault / "In_Progress" / "local" / "TASK_004.md"
        task.write_text("Completed task")

        result = complete_task("In_Progress/local/TASK_004.md")
        assert result is True
        assert not task.exists()
        # Should be in Done/ with timestamp suffix
        done_files = list((vault / "Done").glob("TASK_004_*.md"))
        assert len(done_files) == 1

    def test_complete_nonexistent(self, vault):
        result = complete_task("In_Progress/local/NONEXISTENT.md")
        assert result is False


class TestRejectTask:
    """Test rejecting a task."""

    def test_reject_appends_status(self, vault):
        task = vault / "Pending_Approval" / "EMAIL" / "TASK_005.md"
        task.write_text("Draft email")

        # Claim first
        claim_task("Pending_Approval/EMAIL/TASK_005.md", "local")
        claimed = vault / "In_Progress" / "local" / "TASK_005.md"

        result = reject_task(str(claimed))
        assert result is True
        # Check Done/ for rejected file
        done_files = list((vault / "Done").glob("TASK_005_*.md"))
        assert len(done_files) == 1
        content = done_files[0].read_text()
        assert "REJECTED" in content


class TestListPending:
    """Test listing pending tasks."""

    def test_list_specific_domain(self, vault):
        (vault / "Pending_Approval" / "EMAIL" / "TASK_A.md").write_text("a")
        (vault / "Pending_Approval" / "EMAIL" / "TASK_B.md").write_text("b")
        (vault / "Pending_Approval" / "SOCIAL" / "TASK_C.md").write_text("c")

        email_tasks = list_pending("EMAIL")
        assert len(email_tasks) == 2

        social_tasks = list_pending("SOCIAL")
        assert len(social_tasks) == 1

    def test_list_all_domains(self, vault):
        (vault / "Pending_Approval" / "EMAIL" / "TASK_A.md").write_text("a")
        (vault / "Pending_Approval" / "ODOO" / "TASK_B.md").write_text("b")

        all_tasks = list_pending()
        assert len(all_tasks) == 2

    def test_list_empty(self, vault):
        assert list_pending("EMAIL") == []

    def test_list_ignores_gitkeep(self, vault):
        (vault / "Pending_Approval" / "EMAIL" / ".gitkeep").write_text("")
        assert list_pending("EMAIL") == []


class TestListInProgress:
    """Test listing in-progress tasks."""

    def test_list_by_agent(self, vault):
        (vault / "In_Progress" / "cloud" / "TASK_X.md").write_text("x")
        (vault / "In_Progress" / "local" / "TASK_Y.md").write_text("y")

        cloud_tasks = list_in_progress("cloud")
        assert len(cloud_tasks) == 1
        assert cloud_tasks[0].name == "TASK_X.md"

    def test_list_all_agents(self, vault):
        (vault / "In_Progress" / "cloud" / "TASK_X.md").write_text("x")
        (vault / "In_Progress" / "local" / "TASK_Y.md").write_text("y")

        all_tasks = list_in_progress()
        assert len(all_tasks) == 2
