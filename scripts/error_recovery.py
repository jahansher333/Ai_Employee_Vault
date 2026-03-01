"""Error recovery utilities — safe_call wrapper and service health tracking.

Gold Tier: Unified error handling across all integrations. Each external
service can fail independently; the system continues with reduced capabilities.

Usage:
    from error_recovery import safe_call, ServiceHealth, HealthTracker

    result = safe_call(odoo_client.list_invoices, service_name="odoo", logger=logger)
    tracker = HealthTracker()
    tracker.record_success("odoo")
    tracker.record_failure("facebook", "Rate limit exceeded")
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Service health model
# ---------------------------------------------------------------------------

class ServiceHealth:
    """Health status constants for external services."""

    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"

    CONSECUTIVE_FAILURE_THRESHOLD = 3  # failures before unavailable


class HealthTracker:
    """Track health status of external services."""

    def __init__(self) -> None:
        self._services: dict[str, dict[str, Any]] = {}

    def _ensure(self, service: str) -> dict:
        if service not in self._services:
            self._services[service] = {
                "status": ServiceHealth.OPERATIONAL,
                "last_checked": None,
                "last_error": None,
                "error_count": 0,
                "consecutive_failures": 0,
            }
        return self._services[service]

    def record_success(self, service: str) -> None:
        """Record a successful operation — resets to operational."""
        entry = self._ensure(service)
        entry["status"] = ServiceHealth.OPERATIONAL
        entry["last_checked"] = datetime.now(timezone.utc).isoformat()
        entry["consecutive_failures"] = 0

    def record_failure(self, service: str, error: str) -> None:
        """Record a failed operation — may degrade status."""
        entry = self._ensure(service)
        entry["last_checked"] = datetime.now(timezone.utc).isoformat()
        entry["last_error"] = error
        entry["error_count"] += 1
        entry["consecutive_failures"] += 1

        if entry["consecutive_failures"] >= ServiceHealth.CONSECUTIVE_FAILURE_THRESHOLD:
            entry["status"] = ServiceHealth.UNAVAILABLE
        elif entry["consecutive_failures"] >= 1:
            entry["status"] = ServiceHealth.DEGRADED

    def get_status(self, service: str) -> str:
        """Return current health status for a service."""
        return self._ensure(service)["status"]

    def get_all(self) -> dict[str, dict]:
        """Return health data for all tracked services."""
        return dict(self._services)

    def get_summary(self) -> dict[str, str]:
        """Return a service -> status mapping for briefing."""
        return {svc: data["status"] for svc, data in self._services.items()}


# ---------------------------------------------------------------------------
# safe_call wrapper
# ---------------------------------------------------------------------------

def safe_call(
    func: Callable,
    *args: Any,
    service_name: str = "unknown",
    logger: Any | None = None,
    max_retries: int = 1,
    **kwargs: Any,
) -> dict:
    """Call *func* with retry and structured error handling.

    Returns the function result on success, or a structured error dict on
    failure. Never raises an exception to the caller.

    Parameters
    ----------
    func : callable
        The function to call.
    service_name : str
        Name of the external service (for logging).
    logger : AuditLogger | None
        Optional audit logger.
    max_retries : int
        Number of retries on failure (default 1 = try twice total).
    """
    last_error: str | None = None

    for attempt in range(max_retries + 1):
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as exc:
            last_error = str(exc)
            if logger:
                logger.log(
                    f"{service_name}_error",
                    f"attempt_{attempt + 1}",
                    "error" if attempt == max_retries else "warning",
                    error=last_error,
                    details={"attempt": attempt + 1, "max_retries": max_retries},
                )
            if attempt < max_retries:
                time.sleep(1)  # Brief pause before retry

    return {
        "error": last_error,
        "service": service_name,
        "success": False,
        "attempts": max_retries + 1,
    }
