"""Gold Tier self-test — verifies all Gold components are importable and wired."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


# ---------------------------------------------------------------------------
# Import checks — every Gold Tier module must be importable
# ---------------------------------------------------------------------------

class TestGoldImports:
    def test_import_odoo_client(self):
        import odoo_client
        assert hasattr(odoo_client, "OdooClient")

    def test_import_social_poster(self):
        import social_poster
        assert hasattr(social_poster, "generate_social_draft")

    def test_import_error_recovery(self):
        import error_recovery
        assert hasattr(error_recovery, "safe_call")
        assert hasattr(error_recovery, "HealthTracker")

    def test_import_reasoning_loop_gold(self):
        from reasoning_loop import (
            DOMAINS,
            detect_cross_domain,
            detect_circular_dependencies,
            execute_step_with_retry,
            ExecutionMetrics,
        )
        assert len(DOMAINS) == 4

    def test_import_orchestrator_gold(self):
        from orchestrator import restart_component, MAX_RESTARTS
        assert MAX_RESTARTS == 3

    def test_import_mcp_odoo_server(self):
        import mcp_odoo_server
        assert hasattr(mcp_odoo_server, "mcp")

    def test_import_mcp_social_server(self):
        import mcp_social_server
        assert hasattr(mcp_social_server, "mcp")

    def test_import_mcp_email_server(self):
        import mcp_email_server
        assert hasattr(mcp_email_server, "mcp")


# ---------------------------------------------------------------------------
# Skill file checks
# ---------------------------------------------------------------------------

class TestGoldSkillFiles:
    SKILL_DIR = Path(__file__).parent.parent / ".claude" / "skills"

    def test_odoo_skill_exists(self):
        assert (self.SKILL_DIR / "odoo-accounting.md").exists()

    def test_social_poster_skill_exists(self):
        assert (self.SKILL_DIR / "social-poster.md").exists()

    def test_ralph_wiggum_skill_exists(self):
        assert (self.SKILL_DIR / "ralph-wiggum-loop.md").exists()

    def test_odoo_draft_invoice_skill_exists(self):
        assert (self.SKILL_DIR / "odoo-draft-invoice.md").exists()

    def test_at_least_14_skills(self):
        skills = list(self.SKILL_DIR.glob("*.md"))
        assert len(skills) >= 14, f"Found {len(skills)} skills, need 14+"


# ---------------------------------------------------------------------------
# Architecture doc
# ---------------------------------------------------------------------------

class TestArchitectureDoc:
    def test_architecture_md_exists(self):
        arch = Path(__file__).parent.parent / "ARCHITECTURE.md"
        assert arch.exists()

    def test_architecture_has_diagram(self):
        arch = Path(__file__).parent.parent / "ARCHITECTURE.md"
        content = arch.read_text(encoding="utf-8")
        assert "ORCHESTRATOR" in content
        assert "Odoo MCP" in content or "mcp_odoo" in content


# ---------------------------------------------------------------------------
# MCP config
# ---------------------------------------------------------------------------

class TestMCPConfig:
    def test_settings_json_exists(self):
        settings = Path(__file__).parent.parent / ".claude" / "settings.json"
        assert settings.exists()

    def test_settings_has_three_servers(self):
        import json
        settings = Path(__file__).parent.parent / ".claude" / "settings.json"
        data = json.loads(settings.read_text(encoding="utf-8"))
        servers = data.get("mcpServers", {})
        assert len(servers) >= 3
        assert "odoo-xmlrpc" in servers
        assert "social" in servers
        assert "email" in servers


# ---------------------------------------------------------------------------
# Gold Tier feature integration
# ---------------------------------------------------------------------------

class TestGoldFeatures:
    def test_weekly_briefing_has_odoo_collector(self):
        from weekly_briefing import collect_odoo_financials
        result = collect_odoo_financials()
        assert "available" in result
        assert "source" in result

    def test_weekly_briefing_has_social_collector(self, vault):
        from weekly_briefing import collect_social_activity
        result = collect_social_activity(vault)
        assert "available" in result

    def test_reasoning_loop_cross_domain(self):
        from reasoning_loop import detect_cross_domain
        result = detect_cross_domain({}, "Send email about overdue invoice and post on linkedin")
        assert result["is_cross_domain"] is True
        assert result["domain_count"] >= 2

    def test_error_recovery_health_tracker(self):
        from error_recovery import HealthTracker, ServiceHealth
        tracker = HealthTracker()
        tracker.record_success("odoo")
        assert tracker.get_status("odoo") == ServiceHealth.OPERATIONAL
        tracker.record_failure("odoo", "timeout")
        assert tracker.get_status("odoo") == ServiceHealth.DEGRADED

    def test_orchestrator_builds_gold_components(self, vault):
        from orchestrator import build_component_list
        components = build_component_list(vault)
        tiers = {c["tier"] for c in components}
        assert "Gold" in tiers
        names = [c["name"] for c in components]
        assert "Odoo MCP Server" in names
        assert "Social MCP Server" in names
