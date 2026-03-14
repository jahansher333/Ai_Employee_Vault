"""Tests for telegram_watcher.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.telegram_watcher import (
    compute_message_hash,
    create_telegram_task,
    load_telegram_ledger,
    match_keywords,
    process_updates,
    save_to_telegram_ledger,
)


@pytest.fixture
def vault(tmp_path):
    (tmp_path / "Needs_Action").mkdir()
    (tmp_path / "Logs").mkdir()
    return tmp_path


def _make_update(text="Hello", chat_id=123, msg_id=1, sender="TestUser"):
    return {
        "update_id": 1000 + msg_id,
        "message": {
            "message_id": msg_id,
            "from": {"id": 42, "first_name": sender, "username": sender.lower()},
            "chat": {"id": chat_id, "type": "private", "title": ""},
            "date": 1700000000,
            "text": text,
        },
    }


class TestKeywordMatching:
    def test_matches_urgent(self):
        assert "urgent" in match_keywords("This is URGENT please help")

    def test_matches_multiple(self):
        matched = match_keywords("urgent invoice payment needed")
        assert "urgent" in matched
        assert "invoice" in matched
        assert "payment" in matched

    def test_no_match(self):
        assert match_keywords("Hello, how are you?") == []

    def test_case_insensitive(self):
        assert "asap" in match_keywords("Need this ASAP")


class TestMessageHash:
    def test_deterministic(self):
        h1 = compute_message_hash(123, 1, "Hello")
        h2 = compute_message_hash(123, 1, "Hello")
        assert h1 == h2

    def test_different_for_different_messages(self):
        h1 = compute_message_hash(123, 1, "Hello")
        h2 = compute_message_hash(123, 2, "World")
        assert h1 != h2

    def test_returns_string(self):
        h = compute_message_hash(1, 1, "test")
        assert isinstance(h, str)
        assert len(h) == 16


class TestLedger:
    def test_load_empty(self, vault):
        ledger = vault / "Logs" / ".telegram_ledger.txt"
        assert load_telegram_ledger(ledger) == set()

    def test_save_and_load(self, vault):
        ledger = vault / "Logs" / ".telegram_ledger.txt"
        save_to_telegram_ledger(ledger, "abc123")
        save_to_telegram_ledger(ledger, "def456")
        loaded = load_telegram_ledger(ledger)
        assert "abc123" in loaded
        assert "def456" in loaded

    def test_deduplication(self, vault):
        ledger = vault / "Logs" / ".telegram_ledger.txt"
        save_to_telegram_ledger(ledger, "same")
        save_to_telegram_ledger(ledger, "same")
        loaded = load_telegram_ledger(ledger)
        assert "same" in loaded


class TestTaskCreation:
    def test_creates_file(self, vault):
        update = _make_update("urgent help needed", sender="Alice")
        path = create_telegram_task(update, ["urgent", "help"], vault)
        assert path.exists()
        assert "TELEGRAM_" in path.name
        assert "Alice" in path.name

    def test_file_content(self, vault):
        update = _make_update("Invoice #123 payment urgent", sender="Bob")
        path = create_telegram_task(update, ["invoice", "payment", "urgent"], vault)
        content = path.read_text(encoding="utf-8")
        assert "type: telegram" in content
        assert 'from: "Bob"' in content
        assert "priority: high" in content
        assert "Invoice #123 payment urgent" in content

    def test_no_keywords_medium_priority(self, vault):
        update = _make_update("Just a message", sender="Carol")
        path = create_telegram_task(update, [], vault)
        content = path.read_text(encoding="utf-8")
        assert "priority: medium" in content


class TestProcessUpdates:
    def test_creates_tasks_for_keyword_messages(self, vault):
        from scripts.audit_logger import AuditLogger
        logger = AuditLogger(vault)
        ledger = vault / "Logs" / ".telegram_ledger.txt"
        seen = set()

        updates = [
            _make_update("urgent help!", msg_id=1),
            _make_update("casual hello", msg_id=2),
        ]
        count = process_updates(updates, vault, logger, ledger, seen)
        assert count == 1  # only urgent matched

    def test_deduplication(self, vault):
        from scripts.audit_logger import AuditLogger
        logger = AuditLogger(vault)
        ledger = vault / "Logs" / ".telegram_ledger.txt"
        seen = set()

        updates = [_make_update("urgent!", msg_id=1)]
        process_updates(updates, vault, logger, ledger, seen)
        # Process same again
        count = process_updates(updates, vault, logger, ledger, seen)
        assert count == 0  # already seen
