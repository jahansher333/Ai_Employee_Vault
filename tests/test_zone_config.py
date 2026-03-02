"""Tests for zone_config.py — Cloud vs Local zone enforcement."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from zone_config import ZoneConfig, ZoneViolationError, zone_required


# ---------------------------------------------------------------------------
# Cloud mode tests
# ---------------------------------------------------------------------------

class TestCloudMode:
    """Test that cloud mode only allows draft/read operations."""

    def setup_method(self):
        self.config = ZoneConfig("cloud")

    def test_cloud_allows_email_triage(self):
        assert self.config.is_allowed("email_triage") is True

    def test_cloud_allows_email_draft(self):
        assert self.config.is_allowed("email_draft") is True

    def test_cloud_allows_social_draft(self):
        assert self.config.is_allowed("social_draft") is True

    def test_cloud_allows_odoo_read(self):
        assert self.config.is_allowed("odoo_read") is True

    def test_cloud_allows_dashboard_write(self):
        assert self.config.is_allowed("dashboard_write") is True

    def test_cloud_allows_health_check(self):
        assert self.config.is_allowed("health_check") is True

    def test_cloud_blocks_email_send(self):
        assert self.config.is_allowed("email_send") is False
        assert self.config.is_blocked("email_send") is True

    def test_cloud_blocks_social_publish(self):
        assert self.config.is_allowed("social_publish") is False

    def test_cloud_blocks_whatsapp(self):
        assert self.config.is_allowed("whatsapp_interact") is False

    def test_cloud_blocks_odoo_write(self):
        assert self.config.is_allowed("odoo_write") is False

    def test_cloud_blocks_payment(self):
        assert self.config.is_allowed("payment_execute") is False

    def test_cloud_blocks_approval(self):
        assert self.config.is_allowed("approval_grant") is False

    def test_cloud_enforce_raises(self):
        with pytest.raises(ZoneViolationError) as exc_info:
            self.config.enforce("email_send")
        assert "email_send" in str(exc_info.value)
        assert "cloud" in str(exc_info.value)

    def test_cloud_components(self):
        components = self.config.get_components()
        assert "cloud_health_monitor" in components
        assert "vault_sync" in components
        assert "whatsapp_watcher" not in components
        assert "local_approval" not in components


# ---------------------------------------------------------------------------
# Local mode tests
# ---------------------------------------------------------------------------

class TestLocalMode:
    """Test that local mode allows execution operations."""

    def setup_method(self):
        self.config = ZoneConfig("local")

    def test_local_allows_email_send(self):
        assert self.config.is_allowed("email_send") is True

    def test_local_allows_social_publish(self):
        assert self.config.is_allowed("social_publish") is True

    def test_local_allows_whatsapp(self):
        assert self.config.is_allowed("whatsapp_interact") is True

    def test_local_allows_odoo_write(self):
        assert self.config.is_allowed("odoo_write") is True

    def test_local_allows_approval(self):
        assert self.config.is_allowed("approval_grant") is True

    def test_local_blocks_dashboard_write(self):
        assert self.config.is_allowed("dashboard_write") is False

    def test_local_components(self):
        components = self.config.get_components()
        assert "whatsapp_watcher" in components
        assert "local_approval" in components
        assert "cloud_health_monitor" not in components


# ---------------------------------------------------------------------------
# Default and edge cases
# ---------------------------------------------------------------------------

class TestDefaults:
    """Test default behavior and edge cases."""

    def test_default_is_local(self):
        old = os.environ.pop("ZONE_MODE", None)
        try:
            config = ZoneConfig()
            assert config.is_local is True
        finally:
            if old:
                os.environ["ZONE_MODE"] = old

    def test_invalid_zone_raises(self):
        with pytest.raises(ValueError, match="Invalid ZONE_MODE"):
            ZoneConfig("invalid")

    def test_is_cloud_property(self):
        assert ZoneConfig("cloud").is_cloud is True
        assert ZoneConfig("cloud").is_local is False

    def test_is_local_property(self):
        assert ZoneConfig("local").is_local is True
        assert ZoneConfig("local").is_cloud is False

    def test_case_insensitive(self):
        config = ZoneConfig("CLOUD")
        assert config.is_cloud is True


# ---------------------------------------------------------------------------
# Decorator tests
# ---------------------------------------------------------------------------

class TestDecorator:
    """Test the @zone_required decorator."""

    def test_decorator_allows_permitted_operation(self, monkeypatch):
        monkeypatch.setenv("ZONE_MODE", "local")
        # Reimport to pick up new env
        import importlib
        import zone_config as zc
        importlib.reload(zc)

        @zc.zone_required("email_send")
        def send_email():
            return "sent"

        assert send_email() == "sent"

    def test_decorator_blocks_unpermitted_operation(self, monkeypatch):
        monkeypatch.setenv("ZONE_MODE", "cloud")
        import importlib
        import zone_config as zc
        importlib.reload(zc)

        @zc.zone_required("email_send")
        def send_email():
            return "sent"

        with pytest.raises(zc.ZoneViolationError):
            send_email()
