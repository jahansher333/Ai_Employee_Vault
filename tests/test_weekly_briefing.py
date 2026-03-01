"""Tests for the Weekly CEO Briefing generator (Silver + Gold Tier)."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from weekly_briefing import (
    collect_task_stats,
    collect_bottlenecks,
    collect_odoo_financials,
    collect_social_activity,
    collect_week_over_week,
    collect_health_status,
    generate_briefing,
    update_dashboard_briefings,
    _fmt_currency,
    _extract_metric,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def briefing_vault(vault):
    """Vault with Briefings/ directory and sample files."""
    (vault / "Briefings").mkdir()
    # Add some task files of various ages
    (vault / "Needs_Action" / "task1.md").write_text(
        "---\ntype: task\nstatus: new\n---\n\n# Task 1\n", encoding="utf-8"
    )
    (vault / "Needs_Action" / "task2.md").write_text(
        "---\ntype: email\npriority: high\nstatus: new\n---\n\n# Email Task\n", encoding="utf-8"
    )
    (vault / "Pending_Approval" / "approve-sensitive.md").write_text(
        "---\ntype: approval\nstatus: pending\n---\n\n# Approval\n", encoding="utf-8"
    )
    (vault / "Done" / "done-task.md").write_text(
        "---\nstatus: done\n---\n\n# Done Task\n", encoding="utf-8"
    )
    return vault


# ---------------------------------------------------------------------------
# Task stats
# ---------------------------------------------------------------------------

class TestCollectTaskStats:
    def test_counts_all_folders(self, briefing_vault):
        stats = collect_task_stats(briefing_vault)
        assert stats["needs_action"] == 2
        assert stats["pending_approval"] == 1
        assert stats["done"] == 1
        assert stats["total_open"] == 2 + 1 + 0  # needs + pending + plans

    def test_empty_vault(self, vault):
        stats = collect_task_stats(vault)
        assert stats["needs_action"] == 0
        assert stats["total_open"] == 0

    def test_plans_counted(self, briefing_vault):
        (briefing_vault / "Plans" / "PLAN_123_test.md").write_text(
            "---\ntype: plan\nstatus: active\n---\n", encoding="utf-8"
        )
        stats = collect_task_stats(briefing_vault)
        assert stats["active_plans"] == 1


# ---------------------------------------------------------------------------
# Bottleneck detection
# ---------------------------------------------------------------------------

class TestCollectBottlenecks:
    def test_no_bottlenecks_fresh_vault(self, briefing_vault, logger):
        bottlenecks = collect_bottlenecks(briefing_vault, logger)
        # Fresh files shouldn't be stale
        stale = [b for b in bottlenecks if b["type"] == "stale_task"]
        assert len(stale) == 0

    def test_detects_errors_in_log(self, briefing_vault, logger):
        logger.log("test_action", "test.md", "error", error="Something broke")
        bottlenecks = collect_bottlenecks(briefing_vault, logger)
        error_bottlenecks = [b for b in bottlenecks if b["type"] == "errors"]
        assert len(error_bottlenecks) == 1
        assert "1 error" in error_bottlenecks[0]["description"]

    def test_detects_blocked_plan(self, briefing_vault, logger):
        (briefing_vault / "Plans" / "PLAN_test.md").write_text(
            "---\ntype: plan\nstatus: awaiting_approval\n---\n", encoding="utf-8"
        )
        bottlenecks = collect_bottlenecks(briefing_vault, logger)
        blocked = [b for b in bottlenecks if b["type"] == "blocked_plan"]
        assert len(blocked) == 1


# ---------------------------------------------------------------------------
# Briefing generation
# ---------------------------------------------------------------------------

class TestGenerateBriefing:
    def test_creates_briefing_file(self, briefing_vault, logger):
        content, filepath = generate_briefing(briefing_vault, logger)
        assert filepath.exists()
        assert filepath.parent.name == "Briefings"
        assert "Monday_Briefing" in filepath.name

    def test_briefing_has_sections(self, briefing_vault, logger):
        content, _ = generate_briefing(briefing_vault, logger)
        assert "## Executive Summary" in content
        assert "## Financial Overview" in content
        assert "## Task Pipeline" in content
        assert "## Bottlenecks & Risks" in content
        assert "## Recommended Actions" in content

    def test_briefing_has_frontmatter(self, briefing_vault, logger):
        content, _ = generate_briefing(briefing_vault, logger)
        assert "type: briefing" in content
        assert "priority: high" in content

    def test_briefing_shows_task_counts(self, briefing_vault, logger):
        content, _ = generate_briefing(briefing_vault, logger)
        assert "Needs_Action" in content
        assert "Pending Approval" in content

    def test_briefing_logs_generation(self, briefing_vault, logger):
        generate_briefing(briefing_vault, logger)
        entries = logger.read_log()
        briefing_entries = [e for e in entries if e["action"] == "briefing_generated"]
        assert len(briefing_entries) == 1

    def test_no_overwrite_existing(self, briefing_vault, logger):
        _, path1 = generate_briefing(briefing_vault, logger)
        _, path2 = generate_briefing(briefing_vault, logger)
        assert path1 != path2  # Second gets a timestamp suffix
        assert path1.exists()
        assert path2.exists()


# ---------------------------------------------------------------------------
# Dashboard integration
# ---------------------------------------------------------------------------

class TestDashboardBriefings:
    def test_updates_dashboard_markers(self, briefing_vault, logger):
        # Create a dashboard with markers
        dashboard = briefing_vault / "Dashboard.md"
        dashboard.write_text(
            "# Dashboard\n\n"
            "<!-- START_BRIEFINGS -->\n"
            "<!-- END_BRIEFINGS -->\n",
            encoding="utf-8",
        )

        # Generate a briefing first
        generate_briefing(briefing_vault, logger)

        # Update dashboard
        update_dashboard_briefings(briefing_vault)

        content = dashboard.read_text(encoding="utf-8")
        assert "Briefing" in content
        assert "Monday_Briefing" in content

    def test_no_dashboard_does_not_crash(self, vault):
        # Should not raise even without Dashboard.md
        update_dashboard_briefings(vault)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TestFmtCurrency:
    def test_positive(self):
        assert _fmt_currency(1500.50) == "$1,500.50"

    def test_negative(self):
        assert _fmt_currency(-300.0) == "$-300.00"

    def test_zero(self):
        assert _fmt_currency(0) == "$0.00"

    def test_large(self):
        assert _fmt_currency(1234567.89) == "$1,234,567.89"


# ---------------------------------------------------------------------------
# Gold Tier: Odoo financials
# ---------------------------------------------------------------------------

class TestCollectOdooFinancials:
    @patch("odoo_client.OdooClient")
    def test_odoo_available(self, MockClient):
        client = MockClient.return_value
        client.get_financial_summary.return_value = {
            "total_revenue": 50000, "total_expenses": 20000,
            "net_income": 30000, "outstanding_invoices": 5000,
            "overdue_count": 2, "overdue_amount": 3000, "currency": "USD",
        }
        client.get_overdue_invoices.return_value = [
            {"name": "INV/001", "partner_name": "Acme", "amount_residual": 1500,
             "invoice_date_due": "2026-01-01"},
        ]
        result = collect_odoo_financials()
        assert result["available"] is True
        assert result["source"] == "odoo"
        assert result["net_income"] == 30000
        assert len(result["overdue_invoices"]) == 1

    def test_odoo_import_failure(self):
        # When odoo_client is not importable, the function handles it
        with patch.dict("sys.modules", {"odoo_client": None}):
            result = collect_odoo_financials()
            assert isinstance(result, dict)

    @patch("odoo_client.OdooClient")
    def test_odoo_connection_error(self, MockClient):
        from odoo_client import OdooConnectionError
        client = MockClient.return_value
        client.get_financial_summary.side_effect = OdooConnectionError("Connection refused")
        result = collect_odoo_financials()
        assert result["available"] is False
        assert "Connection refused" in result["reason"]


# ---------------------------------------------------------------------------
# Gold Tier: Social activity
# ---------------------------------------------------------------------------

class TestCollectSocialActivity:
    def test_social_summary(self, vault):
        # Create some social files
        pa = vault / "Pending_Approval"
        (pa / "FACEBOOK_001_test.md").write_text("test", encoding="utf-8")
        (pa / "TWITTER_001_test.md").write_text("test", encoding="utf-8")
        done = vault / "Done"
        (done / "INSTAGRAM_001_test.md").write_text("test", encoding="utf-8")

        result = collect_social_activity(vault)
        assert result["available"] is True
        assert result["platforms"]["facebook"]["drafts"] == 1
        assert result["platforms"]["twitter"]["drafts"] == 1
        assert result["platforms"]["instagram"]["posted"] == 1
        assert result["total_posted"] == 1
        assert result["total_pending"] == 2

    def test_empty_vault(self, vault):
        result = collect_social_activity(vault)
        assert result["available"] is True
        assert result["total_posted"] == 0


# ---------------------------------------------------------------------------
# Gold Tier: Week-over-Week
# ---------------------------------------------------------------------------

class TestCollectWeekOverWeek:
    def test_no_briefings(self, vault):
        result = collect_week_over_week(vault)
        assert result["available"] is False

    def test_single_briefing(self, vault):
        briefings = vault / "Briefings"
        briefings.mkdir()
        (briefings / "2026-02-17_Monday_Briefing.md").write_text(
            "| Needs_Action | 5 |\n| Done | 10 |\n| Pending Approval | 3 |",
            encoding="utf-8",
        )
        result = collect_week_over_week(vault)
        assert result["available"] is False  # Need at least 2

    def test_two_briefings(self, vault):
        import time
        briefings = vault / "Briefings"
        briefings.mkdir()
        older = briefings / "2026-02-10_Monday_Briefing.md"
        older.write_text(
            "| Needs_Action | 5 |\n| Done | 10 |\n| Pending Approval | 3 |",
            encoding="utf-8",
        )
        time.sleep(0.05)  # Ensure different mtime
        newer = briefings / "2026-02-17_Monday_Briefing.md"
        newer.write_text(
            "| Needs_Action | 8 |\n| Done | 15 |\n| Pending Approval | 2 |",
            encoding="utf-8",
        )
        result = collect_week_over_week(vault)
        assert result["available"] is True
        assert result["prev_needs_action"] == 5
        assert result["prev_done"] == 10


# ---------------------------------------------------------------------------
# Gold Tier: Health status
# ---------------------------------------------------------------------------

class TestCollectHealthStatus:
    def test_health_returns_dict(self):
        result = collect_health_status()
        assert isinstance(result, dict)
        assert result["available"] is True
        assert "services" in result


# ---------------------------------------------------------------------------
# Gold Tier: Extract metric helper
# ---------------------------------------------------------------------------

class TestExtractMetric:
    def test_extracts_number(self):
        content = "| Needs_Action | 42 |"
        assert _extract_metric(content, r"Needs_Action\s*\|\s*(\d+)") == 42

    def test_no_match(self):
        assert _extract_metric("no data here", r"Needs_Action\s*\|\s*(\d+)") == 0


# ---------------------------------------------------------------------------
# Gold Tier: Enhanced briefing
# ---------------------------------------------------------------------------

class TestGoldBriefing:
    def test_briefing_has_social_section(self, briefing_vault, logger):
        # Create social files so section appears
        pa = briefing_vault / "Pending_Approval"
        (pa / "FACEBOOK_001_test.md").write_text("test", encoding="utf-8")
        content, _ = generate_briefing(briefing_vault, logger)
        assert "Social Media Activity" in content

    def test_briefing_has_social_summary_in_exec(self, briefing_vault, logger):
        content, _ = generate_briefing(briefing_vault, logger)
        assert "Social" in content

    @patch("weekly_briefing.collect_odoo_financials")
    def test_briefing_with_odoo(self, mock_odoo, briefing_vault, logger):
        mock_odoo.return_value = {
            "available": True, "source": "odoo",
            "total_revenue": 100000, "total_expenses": 40000,
            "net_income": 60000, "outstanding": 10000,
            "overdue_count": 3, "overdue_amount": 5000,
            "currency": "USD",
            "overdue_invoices": [
                {"name": "INV/001", "partner_name": "Test Co",
                 "amount_residual": 2500, "invoice_date_due": "2026-01-15"},
            ],
        }
        content, _ = generate_briefing(briefing_vault, logger)
        assert "Odoo Financial Summary" in content
        assert "Overdue Invoices" in content
        assert "INV/001" in content

    @patch("weekly_briefing.collect_health_status")
    def test_briefing_with_health(self, mock_health, briefing_vault, logger):
        mock_health.return_value = {
            "available": True,
            "services": {"odoo": "operational", "gmail": "degraded"},
        }
        content, _ = generate_briefing(briefing_vault, logger)
        assert "System Health" in content
        assert "odoo" in content
        assert "degraded" in content
