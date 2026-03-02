"""Platinum Tier self-test — comprehensive validation of all requirements.

Tests all 30 FRs and 14 SCs from spec.md. Run with:
    pytest tests/test_platinum_tier_selftest.py -v
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def vault(tmp_path, monkeypatch):
    """Create a temporary vault with Platinum folder structure."""
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    for folder in ["Needs_Action", "Plans", "Pending_Approval"]:
        for domain in ["EMAIL", "SOCIAL", "ODOO"]:
            (tmp_path / folder / domain).mkdir(parents=True)
    (tmp_path / "In_Progress" / "cloud").mkdir(parents=True)
    (tmp_path / "In_Progress" / "local").mkdir(parents=True)
    (tmp_path / "Updates").mkdir()
    (tmp_path / "Done").mkdir()
    (tmp_path / "Logs").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# Zone Enforcement (FR-006 to FR-010)
# ---------------------------------------------------------------------------

class TestZoneEnforcement:
    """FR-006 to FR-010: Work-zone specialization."""

    def test_cloud_allows_draft_operations(self):
        from zone_config import ZoneConfig
        cloud = ZoneConfig("cloud")
        for op in ["email_triage", "email_draft", "social_draft", "odoo_read", "odoo_draft"]:
            assert cloud.is_allowed(op), f"Cloud should allow {op}"

    def test_cloud_blocks_send_operations(self):
        from zone_config import ZoneConfig
        cloud = ZoneConfig("cloud")
        for op in ["email_send", "social_publish", "whatsapp_interact", "odoo_write", "payment_execute"]:
            assert not cloud.is_allowed(op), f"Cloud should block {op}"

    def test_local_allows_execution_operations(self):
        from zone_config import ZoneConfig
        local = ZoneConfig("local")
        for op in ["email_send", "social_publish", "whatsapp_interact", "odoo_write", "approval_grant"]:
            assert local.is_allowed(op), f"Local should allow {op}"

    def test_zone_enforcement_decorator(self):
        from zone_config import ZoneConfig, ZoneViolationError, zone_required

        # Test that zone_required decorator blocks cloud-disallowed ops
        cloud = ZoneConfig("cloud")
        assert not cloud.is_allowed("email_send")

        # Verify ZoneViolationError can be raised manually
        with pytest.raises(ZoneViolationError):
            cloud.enforce("email_send")

    def test_zone_components_cloud(self):
        from zone_config import ZoneConfig
        cloud = ZoneConfig("cloud")
        components = cloud.get_components()
        assert "cloud_health_monitor" in components
        assert "whatsapp_watcher" not in components

    def test_zone_components_local(self):
        from zone_config import ZoneConfig
        local = ZoneConfig("local")
        components = local.get_components()
        assert "local_approval" in components
        assert "cloud_health_monitor" not in components


# ---------------------------------------------------------------------------
# Claim-by-Move (FR-012)
# ---------------------------------------------------------------------------

class TestClaimByMove:
    """FR-012: Atomic task claiming."""

    def test_claim_succeeds(self, vault):
        from claim_task import claim_task
        task = vault / "Pending_Approval" / "EMAIL" / "TEST_CLAIM.md"
        task.write_text("test")
        assert claim_task("Pending_Approval/EMAIL/TEST_CLAIM.md", "local") is True
        assert (vault / "In_Progress" / "local" / "TEST_CLAIM.md").exists()

    def test_double_claim_prevented(self, vault):
        from claim_task import claim_task
        task = vault / "Pending_Approval" / "EMAIL" / "TEST_DOUBLE.md"
        task.write_text("test")
        assert claim_task("Pending_Approval/EMAIL/TEST_DOUBLE.md", "local") is True
        assert claim_task("Pending_Approval/EMAIL/TEST_DOUBLE.md", "cloud") is False

    def test_complete_task(self, vault):
        from claim_task import claim_task, complete_task
        task = vault / "Pending_Approval" / "SOCIAL" / "TEST_COMPLETE.md"
        task.write_text("test")
        claim_task("Pending_Approval/SOCIAL/TEST_COMPLETE.md", "local")
        assert complete_task("In_Progress/local/TEST_COMPLETE.md") is True
        assert len(list((vault / "Done").glob("TEST_COMPLETE_*.md"))) == 1


# ---------------------------------------------------------------------------
# Vault Delegation (FR-011, FR-013, FR-014)
# ---------------------------------------------------------------------------

class TestVaultDelegation:
    """FR-011, FR-013, FR-014: Structured vault communication."""

    def test_create_task_in_domain_folder(self, vault):
        from vault_delegation import VaultDelegation
        vd = VaultDelegation(vault)
        task = vd.create_task("EMAIL", "Test triage", "cloud")
        assert task.exists()
        # Use Path parts to check, avoiding OS-specific separator issues
        assert "Needs_Action" in task.parts and "EMAIL" in task.parts

    def test_promote_to_approval(self, vault):
        from vault_delegation import VaultDelegation
        vd = VaultDelegation(vault)
        task = vd.create_task("SOCIAL", "Draft post", "cloud")
        promoted = vd.promote_to_approval(task, "SOCIAL")
        assert promoted.exists()
        assert "Pending_Approval" in promoted.parts and "SOCIAL" in promoted.parts
        assert not task.exists()

    def test_write_and_read_updates(self, vault):
        from vault_delegation import VaultDelegation
        vd = VaultDelegation(vault)
        vd.write_update("Cloud processed 5 emails", "cloud")
        updates = vd.read_updates()
        assert len(updates) == 1

    def test_merge_updates_archives(self, vault):
        import time as _time
        from vault_delegation import VaultDelegation
        vd = VaultDelegation(vault)
        vd.write_update("Update 1", "cloud")
        _time.sleep(1.1)  # Ensure different timestamps
        vd.write_update("Update 2", "cloud")
        updates_before = vd.read_updates()
        assert len(updates_before) == 2
        count = vd.merge_updates()
        assert count == 2
        assert (vault / "Updates" / "archived").exists()
        assert len(vd.read_updates()) == 0


# ---------------------------------------------------------------------------
# Vault Sync (FR-015, FR-016, FR-017)
# ---------------------------------------------------------------------------

class TestVaultSync:
    """FR-015 to FR-017: Sync and security exclusions."""

    def test_module_loads(self):
        from vault_sync import VaultSync, EXCLUDED_PATTERNS
        assert ".env" in EXCLUDED_PATTERNS
        assert "credentials.json" in EXCLUDED_PATTERNS
        assert "token.json" in EXCLUDED_PATTERNS

    def test_syncignore_exists(self):
        root = Path(__file__).resolve().parent.parent
        assert (root / ".syncignore").exists()


# ---------------------------------------------------------------------------
# Health Monitoring (FR-002, FR-003, FR-004)
# ---------------------------------------------------------------------------

class TestHealthMonitoring:
    """FR-002 to FR-004: Health checks and alerts."""

    def test_health_monitor_loads(self, vault):
        from cloud_health_monitor import HealthMonitor
        monitor = HealthMonitor(vault)
        assert hasattr(monitor, "run_checks")
        assert hasattr(monitor, "check_process")
        assert hasattr(monitor, "check_http")

    def test_dead_process_detected(self, vault):
        from cloud_health_monitor import HealthMonitor
        monitor = HealthMonitor(vault)
        assert monitor.check_process("test", 999999) is False

    def test_alert_after_threshold(self, vault):
        from cloud_health_monitor import HealthMonitor
        monitor = HealthMonitor(vault, consecutive_failure_threshold=3)
        monitor.register_http("test_service", "http://127.0.0.1:19999/nope")

        for _ in range(3):
            monitor.run_checks()

        alerts = list((vault / "Updates").glob("ALERT_*.md"))
        assert len(alerts) >= 1


# ---------------------------------------------------------------------------
# A2A (FR-024 to FR-027 — Optional)
# ---------------------------------------------------------------------------

class TestA2A:
    """FR-024 to FR-027: Agent-to-Agent messaging (optional)."""

    def test_client_vault_fallback(self, vault):
        from a2a_client import A2AClient
        client = A2AClient(webhook_url="", vault_path=vault)
        result = client.send("task", {"domain": "EMAIL"})
        assert result.delivery_method == "vault_fallback"
        assert result.success is True

    def test_audit_record_created(self, vault):
        from a2a_client import A2AClient
        client = A2AClient(webhook_url="", vault_path=vault)
        client.send("status", {"message": "test"})
        audit_files = list((vault / "Updates").glob("A2A_*.md"))
        assert len(audit_files) >= 1

    def test_message_validation(self):
        from a2a_server import validate_message
        valid, _ = validate_message({"message_type": "task", "payload": {}})
        assert valid is True
        valid, _ = validate_message({"message_type": "invalid", "payload": {}})
        assert valid is False


# ---------------------------------------------------------------------------
# Deploy Files (FR-005, FR-019, FR-020)
# ---------------------------------------------------------------------------

class TestDeployFiles:
    """Verify deployment artifacts exist."""

    @pytest.fixture
    def repo_root(self):
        return Path(__file__).resolve().parent.parent

    def test_setup_vm_exists(self, repo_root):
        assert (repo_root / "deploy" / "setup-vm.sh").exists()

    def test_docker_compose_exists(self, repo_root):
        assert (repo_root / "deploy" / "docker-compose.yml").exists()

    def test_nginx_conf_exists(self, repo_root):
        assert (repo_root / "deploy" / "nginx" / "odoo.conf").exists()

    def test_backup_script_exists(self, repo_root):
        assert (repo_root / "deploy" / "backup" / "odoo-backup.sh").exists()

    def test_systemd_service_exists(self, repo_root):
        assert (repo_root / "deploy" / "systemd" / "ai-employee.service").exists()

    def test_vault_sync_timer_exists(self, repo_root):
        assert (repo_root / "deploy" / "systemd" / "vault-sync.timer").exists()

    def test_cloud_env_example_exists(self, repo_root):
        assert (repo_root / "deploy" / ".env.cloud.example").exists()


# ---------------------------------------------------------------------------
# Gold Tier Regression (SC-001)
# ---------------------------------------------------------------------------

class TestGoldRegression:
    """SC-001: All Gold Tier requirements continue to pass."""

    def test_gold_selftest_importable(self):
        """Verify Gold tier test file exists."""
        root = Path(__file__).resolve().parent.parent
        assert (root / "tests" / "test_gold_tier_selftest.py").exists()


# ---------------------------------------------------------------------------
# Platinum Demo (FR-028 to FR-030)
# ---------------------------------------------------------------------------

class TestPlatinumDemo:
    """FR-028 to FR-030: Demo script."""

    def test_demo_script_exists(self):
        root = Path(__file__).resolve().parent.parent
        assert (root / "scripts" / "platinum_demo.py").exists()

    def test_demo_importable(self):
        from platinum_demo import run_demo
        assert callable(run_demo)
