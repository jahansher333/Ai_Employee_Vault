"""Zone configuration — Cloud vs Local work-zone enforcement.

Platinum Tier: Controls which operations are permitted in each zone.
Cloud zone = read-only + draft-creation. Local zone = approvals + execution.

Usage:
    from zone_config import zone_config, zone_required, ZoneViolationError

    # Check if operation is allowed
    if zone_config.is_allowed("email_send"):
        send_email(...)

    # Decorator enforcement
    @zone_required("email_send")
    def send_email(...):
        ...
"""

from __future__ import annotations

import functools
import os
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Zone operation mappings
# ---------------------------------------------------------------------------

CLOUD_ALLOWED = frozenset({
    "email_triage",
    "email_draft",
    "social_draft",
    "odoo_read",
    "odoo_draft",
    "dashboard_write",
    "updates_write",
    "health_check",
    "vault_sync",
})

CLOUD_BLOCKED = frozenset({
    "email_send",
    "social_publish",
    "whatsapp_interact",
    "odoo_write",
    "payment_execute",
    "approval_grant",
})

LOCAL_ALLOWED = frozenset({
    "email_send",
    "email_triage",
    "email_draft",
    "social_publish",
    "social_draft",
    "whatsapp_interact",
    "odoo_read",
    "odoo_write",
    "payment_execute",
    "approval_grant",
    "dashboard_read",
    "updates_read",
    "vault_sync",
})

LOCAL_BLOCKED = frozenset({
    "dashboard_write",  # Cloud owns Dashboard.md writes
})

# Components per zone
CLOUD_COMPONENTS = [
    "watcher",
    "gmail_watcher",
    "process_inbox",
    "social_poster",
    "mcp_odoo_server",
    "update_dashboard",
    "cloud_health_monitor",
    "vault_sync",
]

LOCAL_COMPONENTS = [
    "watcher",
    "whatsapp_watcher",
    "local_approval",
    "gmail_watcher",
    "social_poster",
    "linkedin_poster",
    "mcp_email_server",
    "mcp_social_server",
    "vault_sync",
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ZoneViolationError(PermissionError):
    """Raised when an operation is attempted in the wrong zone."""

    def __init__(self, operation: str, zone: str) -> None:
        self.operation = operation
        self.zone = zone
        super().__init__(
            f"Operation '{operation}' is not allowed in zone '{zone}'. "
            f"This operation requires the {'local' if zone == 'cloud' else 'cloud'} zone."
        )


# ---------------------------------------------------------------------------
# Zone configuration
# ---------------------------------------------------------------------------

class ZoneConfig:
    """Reads ZONE_MODE and enforces operation permissions."""

    def __init__(self, zone_mode: str | None = None) -> None:
        self.zone_mode = (zone_mode or os.environ.get("ZONE_MODE", "local")).lower()
        if self.zone_mode not in ("cloud", "local"):
            raise ValueError(f"Invalid ZONE_MODE: {self.zone_mode!r}. Must be 'cloud' or 'local'.")

    @property
    def is_cloud(self) -> bool:
        return self.zone_mode == "cloud"

    @property
    def is_local(self) -> bool:
        return self.zone_mode == "local"

    def is_allowed(self, operation: str) -> bool:
        """Check if an operation is permitted in the current zone."""
        if self.is_cloud:
            return operation in CLOUD_ALLOWED and operation not in CLOUD_BLOCKED
        return operation in LOCAL_ALLOWED and operation not in LOCAL_BLOCKED

    def is_blocked(self, operation: str) -> bool:
        """Check if an operation is explicitly blocked in the current zone."""
        if self.is_cloud:
            return operation in CLOUD_BLOCKED
        return operation in LOCAL_BLOCKED

    def get_components(self) -> list[str]:
        """Return the list of components to launch in the current zone."""
        if self.is_cloud:
            return list(CLOUD_COMPONENTS)
        return list(LOCAL_COMPONENTS)

    def enforce(self, operation: str) -> None:
        """Raise ZoneViolationError if operation is not allowed."""
        if not self.is_allowed(operation):
            raise ZoneViolationError(operation, self.zone_mode)


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

def zone_required(operation: str) -> Callable:
    """Decorator that enforces zone permissions before executing a function.

    Usage:
        @zone_required("email_send")
        def send_email(to, subject, body):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            zone_config.enforce(operation)
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Module-level singleton (lazy init)
# ---------------------------------------------------------------------------

zone_config = ZoneConfig()
