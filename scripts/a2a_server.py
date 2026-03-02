"""A2A Server — Agent-to-Agent webhook receiver for Local zone.

Platinum Tier Phase 2: Receives direct messages from Cloud agent via HTTP POST.
Each message is logged to vault /Updates/ as audit trail.

Usage:
    python scripts/a2a_server.py --port 8765 --vault-path /path
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger


# ---------------------------------------------------------------------------
# Message schema
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = {"message_type", "payload"}
VALID_TYPES = {"task", "status", "alert", "ack"}


def validate_message(data: dict) -> tuple[bool, str]:
    """Validate incoming A2A message schema."""
    for field in REQUIRED_FIELDS:
        if field not in data:
            return False, f"Missing required field: {field}"
    if data["message_type"] not in VALID_TYPES:
        return False, f"Invalid message_type: {data['message_type']}. Must be one of {VALID_TYPES}"
    return True, ""


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------

def write_audit(vault_path: Path, message_id: str, data: dict) -> str:
    """Write A2A message to vault as audit record."""
    updates_dir = vault_path / "Updates"
    updates_dir.mkdir(parents=True, exist_ok=True)

    ts = time.strftime("%Y%m%d_%H%M%S")
    audit_file = updates_dir / f"A2A_{ts}_{message_id[:8]}.md"
    content = f"""---
type: a2a_message
id: {message_id}
from_zone: {data.get('from_zone', 'cloud')}
to_zone: local
message_type: {data['message_type']}
received_at: {time.strftime('%Y-%m-%d %H:%M:%S')}
delivery_method: a2a
---

## A2A Message

**Type**: {data['message_type']}
**From**: {data.get('from_zone', 'cloud')}

### Payload

```json
{json.dumps(data.get('payload', {}), indent=2)}
```
"""
    audit_file.write_text(content, encoding="utf-8")
    return str(audit_file)


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class A2AHandler(BaseHTTPRequestHandler):
    """HTTP request handler for A2A messages."""

    vault_path: Path = Path(".")
    logger: AuditLogger | None = None

    def do_POST(self):
        if self.path == "/a2a":
            self._handle_a2a()
        else:
            self.send_error(404, "Not Found")

    def do_GET(self):
        if self.path == "/a2a/health":
            self._handle_health()
        else:
            self.send_error(404, "Not Found")

    def _handle_a2a(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body)
        except (json.JSONDecodeError, ValueError) as e:
            self._respond(400, {"error": f"Invalid JSON: {e}"})
            return

        valid, error = validate_message(data)
        if not valid:
            self._respond(400, {"error": error})
            return

        message_id = data.get("id", str(uuid.uuid4()))
        data["id"] = message_id

        # Write audit trail
        audit_path = write_audit(self.vault_path, message_id, data)

        # Log
        if self.logger:
            self.logger.log(
                "a2a_receive", data["message_type"], "success",
                details={"id": message_id, "audit_path": audit_path},
            )

        self._respond(200, {"status": "received", "id": message_id, "audit_path": audit_path})

    def _handle_health(self):
        self._respond(200, {"status": "healthy", "zone": "local", "service": "a2a_server"})

    def _respond(self, code: int, body: dict):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode("utf-8"))

    def log_message(self, format, *args):
        """Suppress default HTTP logging."""
        pass


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

def create_server(port: int, vault_path: Path, logger: AuditLogger | None = None) -> HTTPServer:
    """Create and configure the A2A HTTP server."""
    A2AHandler.vault_path = vault_path
    A2AHandler.logger = logger
    server = HTTPServer(("0.0.0.0", port), A2AHandler)
    return server


def main():
    parser = argparse.ArgumentParser(description="A2A webhook receiver (Local zone)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("A2A_LISTEN_PORT", "8765")))
    parser.add_argument("--vault-path", default=os.environ.get("VAULT_PATH", "."))
    args = parser.parse_args()

    vault_path = Path(args.vault_path)
    logger = AuditLogger(vault_path / "Logs")
    server = create_server(args.port, vault_path, logger)

    print(f"A2A server listening on port {args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nA2A server stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
