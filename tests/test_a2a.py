"""Tests for A2A server and client — Phase 2 optional upgrade."""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from a2a_server import A2AHandler, create_server, validate_message, write_audit
from a2a_client import A2AClient, A2AResult


# ---------------------------------------------------------------------------
# Message validation
# ---------------------------------------------------------------------------

class TestMessageValidation:

    def test_valid_task_message(self):
        valid, error = validate_message({"message_type": "task", "payload": {"domain": "EMAIL"}})
        assert valid is True
        assert error == ""

    def test_missing_message_type(self):
        valid, error = validate_message({"payload": {}})
        assert valid is False
        assert "message_type" in error

    def test_missing_payload(self):
        valid, error = validate_message({"message_type": "task"})
        assert valid is False
        assert "payload" in error

    def test_invalid_message_type(self):
        valid, error = validate_message({"message_type": "invalid", "payload": {}})
        assert valid is False
        assert "invalid" in error

    def test_all_valid_types(self):
        for msg_type in ("task", "status", "alert", "ack"):
            valid, _ = validate_message({"message_type": msg_type, "payload": {}})
            assert valid is True


# ---------------------------------------------------------------------------
# Audit writing
# ---------------------------------------------------------------------------

class TestAuditWriting:

    def test_write_audit_creates_file(self, tmp_path):
        data = {"message_type": "task", "payload": {"domain": "EMAIL"}, "from_zone": "cloud"}
        audit_path = write_audit(tmp_path, "test-id-123", data)
        assert Path(audit_path).exists()
        content = Path(audit_path).read_text()
        assert "test-id-123" in content
        assert "task" in content
        assert "EMAIL" in content

    def test_audit_in_updates_dir(self, tmp_path):
        data = {"message_type": "status", "payload": {}}
        audit_path = write_audit(tmp_path, "test-id-456", data)
        assert "Updates" in audit_path
        assert "A2A_" in Path(audit_path).name


# ---------------------------------------------------------------------------
# A2A Client — vault fallback
# ---------------------------------------------------------------------------

class TestA2AClient:

    def test_client_fallback_when_no_url(self, tmp_path, monkeypatch):
        monkeypatch.setenv("VAULT_PATH", str(tmp_path))
        (tmp_path / "Updates").mkdir()
        (tmp_path / "Needs_Action" / "EMAIL").mkdir(parents=True)

        client = A2AClient(webhook_url="", vault_path=tmp_path)
        result = client.send("task", {"domain": "EMAIL", "action": "draft"})

        assert result.success is True
        assert result.delivery_method == "vault_fallback"
        assert result.message_id

        # Check audit file created
        audit_files = list((tmp_path / "Updates").glob("A2A_*.md"))
        assert len(audit_files) >= 1

        # Check fallback task file created
        fallback_files = list((tmp_path / "Needs_Action" / "EMAIL").glob("A2A_FALLBACK_*.md"))
        assert len(fallback_files) == 1

    def test_client_fallback_when_server_unreachable(self, tmp_path):
        (tmp_path / "Updates").mkdir()
        (tmp_path / "Needs_Action" / "SOCIAL").mkdir(parents=True)

        client = A2AClient(webhook_url="http://127.0.0.1:19999/a2a", vault_path=tmp_path, timeout=1)
        result = client.send("task", {"domain": "SOCIAL", "action": "draft_post"})

        assert result.success is True
        assert result.delivery_method == "vault_fallback"

    def test_client_is_available_false_when_no_url(self):
        client = A2AClient(webhook_url="")
        assert client.is_available() is False

    def test_client_is_available_false_when_unreachable(self):
        client = A2AClient(webhook_url="http://127.0.0.1:19999/a2a")
        assert client.is_available() is False


# ---------------------------------------------------------------------------
# A2A Server + Client integration
# ---------------------------------------------------------------------------

class TestA2AIntegration:

    def test_send_and_receive(self, tmp_path):
        """Full round-trip: client sends, server receives, audit created."""
        (tmp_path / "Updates").mkdir()
        (tmp_path / "Logs").mkdir()

        server = create_server(0, tmp_path)  # port 0 = random available
        port = server.server_address[1]

        thread = threading.Thread(target=server.handle_request, daemon=True)
        thread.start()

        time.sleep(0.1)  # Let server start

        client = A2AClient(
            webhook_url=f"http://127.0.0.1:{port}/a2a",
            vault_path=tmp_path,
            timeout=5,
        )
        result = client.send("task", {"domain": "EMAIL", "action": "triage"})

        thread.join(timeout=5)
        server.server_close()

        assert result.success is True
        assert result.delivery_method == "a2a"
        assert result.message_id

        # Audit files: one from server, one from client
        audit_files = list((tmp_path / "Updates").glob("A2A_*.md"))
        assert len(audit_files) >= 1

    def test_health_endpoint(self, tmp_path):
        """Test /a2a/health returns 200."""
        from urllib.request import urlopen

        server = create_server(0, tmp_path)
        port = server.server_address[1]

        thread = threading.Thread(target=server.handle_request, daemon=True)
        thread.start()

        time.sleep(0.1)

        with urlopen(f"http://127.0.0.1:{port}/a2a/health", timeout=2) as resp:
            assert resp.status == 200
            data = json.loads(resp.read())
            assert data["status"] == "healthy"

        thread.join(timeout=5)
        server.server_close()
