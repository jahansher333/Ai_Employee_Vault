"""A2A Client — Agent-to-Agent webhook sender for Cloud zone.

Platinum Tier Phase 2: Sends direct messages to Local agent via HTTP POST.
Falls back to file-based vault handoff if A2A is unavailable.
Every message is also written to vault /Updates/ as audit trail.

Usage:
    from a2a_client import A2AClient

    client = A2AClient("http://local-ip:8765/a2a", vault_path)
    result = client.send("task", {"domain": "EMAIL", "action": "draft_reply"})
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError


class A2AResult:
    """Result of an A2A send attempt."""

    def __init__(
        self,
        success: bool,
        message_id: str,
        delivery_method: str,
        error: str | None = None,
        audit_path: str | None = None,
    ):
        self.success = success
        self.message_id = message_id
        self.delivery_method = delivery_method  # "a2a" or "vault_fallback"
        self.error = error
        self.audit_path = audit_path

    def __repr__(self) -> str:
        return (
            f"A2AResult(success={self.success}, method={self.delivery_method}, "
            f"id={self.message_id[:8]})"
        )


class A2AClient:
    """Sends A2A messages to the Local agent with vault fallback."""

    def __init__(
        self,
        webhook_url: str | None = None,
        vault_path: str | Path | None = None,
        timeout: int = 5,
    ):
        self.webhook_url = webhook_url or os.environ.get("A2A_LOCAL_WEBHOOK_URL", "")
        self.vault_path = Path(vault_path or os.environ.get("VAULT_PATH", "."))
        self.timeout = timeout

    def is_available(self) -> bool:
        """Check if the A2A server is reachable."""
        if not self.webhook_url:
            return False
        health_url = self.webhook_url.rstrip("/").rsplit("/", 1)[0] + "/a2a/health"
        try:
            req = Request(health_url, method="GET")
            with urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except (URLError, OSError, ValueError):
            return False

    def send(self, message_type: str, payload: dict) -> A2AResult:
        """Send a message to the Local agent.

        Tries A2A first; falls back to vault file if unavailable.
        Always writes audit record to vault.
        """
        message_id = str(uuid.uuid4())
        message = {
            "id": message_id,
            "from_zone": "cloud",
            "to_zone": "local",
            "message_type": message_type,
            "payload": payload,
        }

        # Try A2A delivery
        if self.webhook_url:
            try:
                result = self._send_webhook(message)
                # Also write local audit
                audit_path = self._write_audit(message_id, message, "a2a")
                return A2AResult(
                    success=True,
                    message_id=message_id,
                    delivery_method="a2a",
                    audit_path=audit_path,
                )
            except (URLError, OSError, ValueError) as e:
                # Fall through to vault fallback
                error_msg = str(e)
        else:
            error_msg = "No webhook URL configured"

        # Vault fallback
        audit_path = self._write_audit(message_id, message, "vault_fallback")
        self._vault_fallback(message_id, message)

        return A2AResult(
            success=True,
            message_id=message_id,
            delivery_method="vault_fallback",
            error=f"A2A unavailable ({error_msg}), used vault fallback",
            audit_path=audit_path,
        )

    def _send_webhook(self, message: dict) -> dict:
        """Send message via HTTP POST."""
        data = json.dumps(message).encode("utf-8")
        req = Request(
            self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _write_audit(self, message_id: str, message: dict, method: str) -> str:
        """Write audit record to vault Updates/."""
        updates_dir = self.vault_path / "Updates"
        updates_dir.mkdir(parents=True, exist_ok=True)

        ts = time.strftime("%Y%m%d_%H%M%S")
        audit_file = updates_dir / f"A2A_{ts}_{message_id[:8]}.md"
        content = f"""---
type: a2a_audit
id: {message_id}
from_zone: cloud
to_zone: local
message_type: {message['message_type']}
sent_at: {time.strftime('%Y-%m-%d %H:%M:%S')}
delivery_method: {method}
---

## A2A Audit Record

**Delivery**: {method}
**Type**: {message['message_type']}

### Payload

```json
{json.dumps(message.get('payload', {}), indent=2)}
```
"""
        audit_file.write_text(content, encoding="utf-8")
        return str(audit_file)

    def _vault_fallback(self, message_id: str, message: dict) -> None:
        """Write task to vault for file-based handoff."""
        domain = message.get("payload", {}).get("domain", "GENERAL")
        needs_dir = self.vault_path / "Needs_Action" / domain
        needs_dir.mkdir(parents=True, exist_ok=True)

        ts = time.strftime("%Y%m%d_%H%M%S")
        task_file = needs_dir / f"A2A_FALLBACK_{ts}_{message_id[:8]}.md"
        content = f"""---
type: a2a_fallback
id: {message_id}
domain: {domain}
message_type: {message['message_type']}
created_at: {time.strftime('%Y-%m-%d %H:%M:%S')}
fallback_reason: a2a_unavailable
---

## Task (A2A Fallback)

This task was created via vault fallback because A2A messaging was unavailable.

### Original Payload

```json
{json.dumps(message.get('payload', {}), indent=2)}
```
"""
        task_file.write_text(content, encoding="utf-8")
