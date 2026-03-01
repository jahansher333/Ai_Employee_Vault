"""Tests for the AI Employee Orchestrator."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from orchestrator import (
    build_component_list,
    validate_components,
    check_component_health,
    restart_component,
    MAX_RESTARTS,
)


# ---------------------------------------------------------------------------
# Component list building
# ---------------------------------------------------------------------------

class TestBuildComponentList:
    def test_default_includes_watcher(self, vault):
        components = build_component_list(vault)
        names = [c["name"] for c in components]
        assert "File Watcher" in names

    def test_default_includes_whatsapp(self, vault):
        components = build_component_list(vault)
        names = [c["name"] for c in components]
        assert "WhatsApp Watcher" in names

    def test_default_includes_scheduler(self, vault):
        components = build_component_list(vault)
        names = [c["name"] for c in components]
        assert "Weekly Briefing Scheduler" in names

    def test_gmail_skipped_without_credentials(self, vault):
        """Gmail watcher should not appear if credentials.json is missing."""
        components = build_component_list(vault)
        names = [c["name"] for c in components]
        assert "Gmail Watcher" not in names

    def test_gmail_included_with_credentials(self, vault):
        """Gmail watcher should appear when credentials.json exists."""
        (vault / "credentials.json").write_text("{}", encoding="utf-8")
        components = build_component_list(vault)
        names = [c["name"] for c in components]
        assert "Gmail Watcher" in names

    def test_exclude_whatsapp(self, vault):
        components = build_component_list(vault, include_whatsapp=False)
        names = [c["name"] for c in components]
        assert "WhatsApp Watcher" not in names

    def test_exclude_scheduler(self, vault):
        components = build_component_list(vault, include_scheduler=False)
        names = [c["name"] for c in components]
        assert "Weekly Briefing Scheduler" not in names

    def test_file_watcher_is_required(self, vault):
        components = build_component_list(vault)
        watcher = [c for c in components if c["name"] == "File Watcher"][0]
        assert watcher["required"] is True

    def test_optional_components_not_required(self, vault):
        (vault / "credentials.json").write_text("{}", encoding="utf-8")
        components = build_component_list(vault)
        optional = [c for c in components if c["name"] != "File Watcher"]
        for comp in optional:
            assert comp["required"] is False

    def test_vault_path_in_args(self, vault):
        components = build_component_list(vault)
        # Only non-MCP components pass vault path as args
        for comp in components:
            if comp["args"]:  # MCP servers have empty args
                assert str(vault) in comp["args"]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidateComponents:
    def test_all_scripts_exist(self, vault):
        """Real scripts should exist relative to orchestrator.py."""
        components = build_component_list(vault)
        warnings = validate_components(components)
        # All scripts exist in the scripts/ directory
        assert len(warnings) == 0

    def test_missing_script_warns(self, vault):
        components = [{
            "name": "Fake Watcher",
            "script": "nonexistent_script.py",
            "args": [],
            "required": False,
            "tier": "Test",
        }]
        warnings = validate_components(components)
        assert len(warnings) == 1
        assert "Fake Watcher" in warnings[0]


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------

class TestCheckComponentHealth:
    def test_running_process(self):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None  # Still running
        components = [{"name": "Test", "process": mock_proc, "status": "running"}]
        crashed = check_component_health(components)
        assert len(crashed) == 0

    def test_crashed_process(self):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 1  # Exited with error
        components = [{"name": "Test", "process": mock_proc, "status": "running"}]
        crashed = check_component_health(components)
        assert len(crashed) == 1
        assert crashed[0]["name"] == "Test"
        assert crashed[0]["status"] == "crashed"

    def test_no_process(self):
        components = [{"name": "Test", "process": None, "status": "failed"}]
        crashed = check_component_health(components)
        assert len(crashed) == 0

    def test_already_crashed_not_reported_again(self):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 1
        components = [{"name": "Test", "process": mock_proc, "status": "crashed"}]
        crashed = check_component_health(components)
        assert len(crashed) == 0  # Already marked, don't report again


# ---------------------------------------------------------------------------
# Gold Tier: Odoo and Social components
# ---------------------------------------------------------------------------

class TestGoldTierComponents:
    def test_default_includes_odoo(self, vault):
        components = build_component_list(vault)
        names = [c["name"] for c in components]
        assert "Odoo MCP Server" in names

    def test_default_includes_social(self, vault):
        components = build_component_list(vault)
        names = [c["name"] for c in components]
        assert "Social MCP Server" in names

    def test_exclude_odoo(self, vault):
        components = build_component_list(vault, include_odoo=False)
        names = [c["name"] for c in components]
        assert "Odoo MCP Server" not in names

    def test_exclude_social(self, vault):
        components = build_component_list(vault, include_social=False)
        names = [c["name"] for c in components]
        assert "Social MCP Server" not in names

    def test_gold_tier_label(self, vault):
        components = build_component_list(vault)
        odoo = [c for c in components if c["name"] == "Odoo MCP Server"][0]
        assert odoo["tier"] == "Gold"

    def test_gold_components_not_required(self, vault):
        components = build_component_list(vault)
        gold = [c for c in components if c["tier"] == "Gold"]
        for comp in gold:
            assert comp["required"] is False


# ---------------------------------------------------------------------------
# Gold Tier: Auto-restart
# ---------------------------------------------------------------------------

class TestAutoRestart:
    def test_restart_component_success(self, vault, logger):
        comp = {
            "name": "Test Component",
            "script": "watcher.py",  # real script
            "args": ["--vault-path", str(vault)],
            "required": False,
            "tier": "Bronze",
            "status": "crashed",
        }
        with patch("orchestrator.subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.pid = 12345
            mock_popen.return_value = mock_proc
            result = restart_component(comp, logger)

        assert result is True
        assert comp["status"] == "running"
        assert comp["pid"] == 12345
        assert comp["restart_count"] == 1

    def test_restart_increments_count(self, vault, logger):
        comp = {
            "name": "Test",
            "script": "watcher.py",
            "args": [],
            "status": "crashed",
            "restart_count": 2,
        }
        with patch("orchestrator.subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.pid = 99
            mock_popen.return_value = mock_proc
            restart_component(comp, logger)

        assert comp["restart_count"] == 3

    def test_restart_failure(self, vault, logger):
        comp = {
            "name": "Bad",
            "script": "watcher.py",
            "args": [],
            "status": "crashed",
        }
        with patch("orchestrator.subprocess.Popen", side_effect=OSError("fail")):
            result = restart_component(comp, logger)

        assert result is False

    def test_max_restarts_constant(self):
        assert MAX_RESTARTS == 3
