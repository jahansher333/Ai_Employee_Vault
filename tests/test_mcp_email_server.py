"""Tests for mcp_email_server.py — Email MCP tool functions."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from mcp_email_server import (
    fetch_unread_emails,
    send_email,
    reply_to_email,
    mark_email_read,
    create_email_task,
)


class TestFetchUnreadEmails:
    @patch("mcp_email_server._get_service")
    @patch("mcp_email_server._get_service")
    def test_success(self, mock_svc1, mock_svc2):
        with patch("gmail_watcher.fetch_unread_emails") as mock_fetch:
            mock_fetch.return_value = [
                {"id": "abc123", "subject": "Test", "from": "a@b.com", "snippet": "Hello"},
            ]
            result = fetch_unread_emails(max_results=5)
            assert result["success"] is True
            assert result["count"] == 1

    @patch("mcp_email_server._get_service")
    def test_service_error(self, mock_svc):
        mock_svc.side_effect = RuntimeError("Gmail unavailable")
        result = fetch_unread_emails()
        assert result["success"] is False
        assert "Gmail unavailable" in result["error"]


class TestSendEmail:
    @patch("mcp_email_server._get_service")
    def test_service_error(self, mock_svc):
        mock_svc.side_effect = RuntimeError("No Gmail")
        result = send_email("to@test.com", "Subject", "Body")
        assert result["success"] is False


class TestReplyToEmail:
    @patch("mcp_email_server._get_service")
    def test_service_error(self, mock_svc):
        mock_svc.side_effect = RuntimeError("No Gmail")
        result = reply_to_email("msg123", "Reply body")
        assert result["success"] is False


class TestMarkEmailRead:
    @patch("mcp_email_server._get_service")
    def test_service_error(self, mock_svc):
        mock_svc.side_effect = RuntimeError("No Gmail")
        result = mark_email_read("msg123")
        assert result["success"] is False


class TestCreateEmailTask:
    @patch("mcp_email_server.VAULT_PATH")
    def test_creates_task(self, mock_vault, vault):
        with patch("mcp_email_server.VAULT_PATH", vault):
            result = create_email_task(
                subject="Test Subject",
                sender="sender@example.com",
                body_preview="Hello world",
                gmail_id="abc123",
            )
            assert result["success"] is True
            assert "file" in result
            # Verify file was created
            assert Path(result["file"]).exists()
