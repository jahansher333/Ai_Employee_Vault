"""Tests for error_recovery module — safe_call and HealthTracker."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from error_recovery import ServiceHealth, HealthTracker, safe_call


# ---------------------------------------------------------------------------
# ServiceHealth constants
# ---------------------------------------------------------------------------

class TestServiceHealth:
    def test_status_constants(self):
        assert ServiceHealth.OPERATIONAL == "operational"
        assert ServiceHealth.DEGRADED == "degraded"
        assert ServiceHealth.UNAVAILABLE == "unavailable"

    def test_threshold(self):
        assert ServiceHealth.CONSECUTIVE_FAILURE_THRESHOLD == 3


# ---------------------------------------------------------------------------
# HealthTracker
# ---------------------------------------------------------------------------

class TestHealthTracker:
    def test_new_service_is_operational(self):
        tracker = HealthTracker()
        assert tracker.get_status("odoo") == ServiceHealth.OPERATIONAL

    def test_record_success_stays_operational(self):
        tracker = HealthTracker()
        tracker.record_success("odoo")
        assert tracker.get_status("odoo") == ServiceHealth.OPERATIONAL

    def test_one_failure_degrades(self):
        tracker = HealthTracker()
        tracker.record_failure("odoo", "Connection refused")
        assert tracker.get_status("odoo") == ServiceHealth.DEGRADED

    def test_three_failures_unavailable(self):
        tracker = HealthTracker()
        tracker.record_failure("odoo", "Error 1")
        tracker.record_failure("odoo", "Error 2")
        tracker.record_failure("odoo", "Error 3")
        assert tracker.get_status("odoo") == ServiceHealth.UNAVAILABLE

    def test_success_resets_to_operational(self):
        tracker = HealthTracker()
        tracker.record_failure("odoo", "Error 1")
        tracker.record_failure("odoo", "Error 2")
        assert tracker.get_status("odoo") == ServiceHealth.DEGRADED
        tracker.record_success("odoo")
        assert tracker.get_status("odoo") == ServiceHealth.OPERATIONAL

    def test_get_all_returns_all_services(self):
        tracker = HealthTracker()
        tracker.record_success("odoo")
        tracker.record_failure("facebook", "Rate limit")
        all_data = tracker.get_all()
        assert "odoo" in all_data
        assert "facebook" in all_data

    def test_get_summary(self):
        tracker = HealthTracker()
        tracker.record_success("odoo")
        tracker.record_failure("facebook", "Error")
        summary = tracker.get_summary()
        assert summary["odoo"] == ServiceHealth.OPERATIONAL
        assert summary["facebook"] == ServiceHealth.DEGRADED

    def test_error_count_increments(self):
        tracker = HealthTracker()
        tracker.record_failure("odoo", "Error 1")
        tracker.record_failure("odoo", "Error 2")
        assert tracker.get_all()["odoo"]["error_count"] == 2

    def test_last_error_stored(self):
        tracker = HealthTracker()
        tracker.record_failure("odoo", "Connection refused")
        assert tracker.get_all()["odoo"]["last_error"] == "Connection refused"


# ---------------------------------------------------------------------------
# safe_call
# ---------------------------------------------------------------------------

class TestSafeCall:
    def test_successful_call(self):
        def good_func():
            return {"data": [1, 2, 3], "success": True}

        result = safe_call(good_func, service_name="test")
        assert result["success"] is True
        assert result["data"] == [1, 2, 3]

    def test_failed_call_returns_error_dict(self):
        def bad_func():
            raise ConnectionError("Connection refused")

        result = safe_call(bad_func, service_name="odoo", max_retries=0)
        assert result["success"] is False
        assert "Connection refused" in result["error"]
        assert result["service"] == "odoo"

    def test_retry_on_failure(self):
        call_count = 0

        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Transient error")
            return {"success": True}

        result = safe_call(flaky_func, service_name="test", max_retries=1)
        assert result["success"] is True
        assert call_count == 2

    def test_max_retries_exceeded(self):
        def always_fails():
            raise ConnectionError("Permanent error")

        result = safe_call(always_fails, service_name="test", max_retries=2)
        assert result["success"] is False
        assert result["attempts"] == 3

    def test_passes_args_and_kwargs(self):
        def add(a, b, extra=0):
            return {"result": a + b + extra, "success": True}

        result = safe_call(add, 3, 4, service_name="math", extra=10)
        assert result["result"] == 17

    def test_with_logger(self, vault, logger):
        def fails():
            raise ValueError("Test error")

        safe_call(fails, service_name="test_svc", logger=logger, max_retries=0)
        entries = logger.read_log()
        error_entries = [e for e in entries if "test_svc_error" in e.get("action", "")]
        assert len(error_entries) >= 1
