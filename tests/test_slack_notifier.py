"""Tests for slack_notifier.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.slack_notifier import (
    format_slack_message,
    notify_approval_needed,
    notify_briefing_ready,
    notify_low_stock,
    notify_overdue_invoices,
    notify_task_complete,
    send_notification,
    send_status_summary,
)


@pytest.fixture
def vault(tmp_path):
    for d in ["Needs_Action", "Pending_Approval", "Done", "Logs"]:
        (tmp_path / d).mkdir()
    return tmp_path


class TestFormatMessage:
    def test_basic_message(self):
        msg = format_slack_message("Test Title", text="Hello")
        assert msg["attachments"][0]["title"] == "Test Title"
        assert msg["attachments"][0]["text"] == "Hello"

    def test_with_fields(self):
        fields = [{"title": "Key", "value": "Val"}]
        msg = format_slack_message("Title", fields=fields)
        assert msg["attachments"][0]["fields"][0]["title"] == "Key"

    def test_color(self):
        msg = format_slack_message("Title", color="#ff0000")
        assert msg["attachments"][0]["color"] == "#ff0000"


class TestSimulationMode:
    """All tests run without SLACK_WEBHOOK_URL — simulation mode."""

    @patch("scripts.slack_notifier.WEBHOOK_URL", "")
    def test_send_notification(self, vault):
        result = send_notification("Test message", vault_path=vault)
        assert result["ok"] is True
        assert result["mode"] == "simulate"

    @patch("scripts.slack_notifier.WEBHOOK_URL", "")
    def test_notify_task_complete(self, vault):
        result = notify_task_complete("task.md", "success", vault_path=vault)
        assert result["ok"] is True
        assert result["mode"] == "simulate"

    @patch("scripts.slack_notifier.WEBHOOK_URL", "")
    def test_notify_approval_needed(self, vault):
        result = notify_approval_needed("approve-task.md", vault_path=vault)
        assert result["ok"] is True

    @patch("scripts.slack_notifier.WEBHOOK_URL", "")
    def test_notify_briefing_ready(self, vault):
        result = notify_briefing_ready("Briefings/2026-03-16.md", vault_path=vault)
        assert result["ok"] is True

    @patch("scripts.slack_notifier.WEBHOOK_URL", "")
    def test_notify_low_stock(self, vault):
        products = [{"name": "Widget", "qty_available": 2}]
        result = notify_low_stock(products, vault_path=vault)
        assert result["ok"] is True
        assert "Widget" in str(result["payload"])

    @patch("scripts.slack_notifier.WEBHOOK_URL", "")
    def test_notify_overdue_invoices(self, vault):
        invoices = [{"name": "INV/001", "partner_name": "Acme", "amount_residual": 1000}]
        result = notify_overdue_invoices(invoices, vault_path=vault)
        assert result["ok"] is True

    @patch("scripts.slack_notifier.WEBHOOK_URL", "")
    def test_send_summary(self, vault):
        (vault / "Needs_Action" / "t1.md").write_text("test")
        (vault / "Done" / "t2.md").write_text("test")
        result = send_status_summary(vault)
        assert result["ok"] is True


class TestApiMode:
    @patch("scripts.slack_notifier.WEBHOOK_URL", "https://hooks.slack.com/test")
    @patch("scripts.slack_notifier.requests.post")
    def test_sends_to_webhook(self, mock_post, vault):
        mock_post.return_value.status_code = 200
        result = send_notification("Hello", vault_path=vault)
        assert result["ok"] is True
        assert result["mode"] == "api"
        mock_post.assert_called_once()

    @patch("scripts.slack_notifier.WEBHOOK_URL", "https://hooks.slack.com/test")
    @patch("scripts.slack_notifier.requests.post")
    def test_handles_failure(self, mock_post, vault):
        mock_post.return_value.status_code = 500
        result = send_notification("Fail", vault_path=vault)
        assert result["ok"] is False
