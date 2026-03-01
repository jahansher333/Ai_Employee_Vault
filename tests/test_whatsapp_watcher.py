"""Tests for WhatsApp watcher — ledger, hashing, keywords, task creation."""

from pathlib import Path

import pytest

from whatsapp_watcher import (
    compute_message_hash,
    create_whatsapp_task,
    load_whatsapp_ledger,
    match_keywords,
    save_to_whatsapp_ledger,
)


# ---------------------------------------------------------------------------
# Ledger tests
# ---------------------------------------------------------------------------


class TestLedger:
    def test_load_empty(self, vault):
        ledger_path = vault / "Logs" / ".whatsapp_ledger.txt"
        assert load_whatsapp_ledger(ledger_path) == set()

    def test_load_missing_file(self, tmp_path):
        assert load_whatsapp_ledger(tmp_path / "nope.txt") == set()

    def test_save_and_load(self, vault):
        ledger_path = vault / "Logs" / ".whatsapp_ledger.txt"
        save_to_whatsapp_ledger(ledger_path, "abc123")
        save_to_whatsapp_ledger(ledger_path, "def456")
        loaded = load_whatsapp_ledger(ledger_path)
        assert loaded == {"abc123", "def456"}

    def test_no_duplicates_on_load(self, vault):
        ledger_path = vault / "Logs" / ".whatsapp_ledger.txt"
        save_to_whatsapp_ledger(ledger_path, "same")
        save_to_whatsapp_ledger(ledger_path, "same")
        loaded = load_whatsapp_ledger(ledger_path)
        assert loaded == {"same"}


# ---------------------------------------------------------------------------
# Hashing tests
# ---------------------------------------------------------------------------


class TestHashing:
    def test_deterministic(self):
        h1 = compute_message_hash("Alice", "2026-01-01T00:00:00Z", "hello")
        h2 = compute_message_hash("Alice", "2026-01-01T00:00:00Z", "hello")
        assert h1 == h2

    def test_different_sender(self):
        h1 = compute_message_hash("Alice", "2026-01-01T00:00:00Z", "hello")
        h2 = compute_message_hash("Bob", "2026-01-01T00:00:00Z", "hello")
        assert h1 != h2

    def test_truncates_text(self):
        long_text = "x" * 200
        h1 = compute_message_hash("A", "ts", long_text)
        h2 = compute_message_hash("A", "ts", long_text[:50])
        assert h1 == h2

    def test_hex_format(self):
        h = compute_message_hash("A", "B", "C")
        assert len(h) == 64  # SHA-256 hex


# ---------------------------------------------------------------------------
# Keyword matching tests
# ---------------------------------------------------------------------------


class TestKeywords:
    def test_match_urgent(self):
        assert match_keywords("This is URGENT please help") == ["urgent", "help"]

    def test_no_match(self):
        assert match_keywords("Just a regular message") == []

    def test_case_insensitive(self):
        assert match_keywords("INVOICE due tomorrow") == ["invoice"]

    def test_custom_keywords(self):
        assert match_keywords("foo bar baz", keywords=["bar"]) == ["bar"]

    def test_asap_match(self):
        assert match_keywords("Need this ASAP") == ["asap"]

    def test_multiple_keywords(self):
        result = match_keywords("Urgent payment deadline approaching")
        assert "urgent" in result
        assert "payment" in result
        assert "deadline" in result


# ---------------------------------------------------------------------------
# Task file creation tests
# ---------------------------------------------------------------------------


class TestCreateTask:
    def test_creates_file(self, vault, logger):
        msg = {
            "sender": "Ahmed Client",
            "text": "Urgent - need invoice by EOD",
            "timestamp": "2026-02-22T14:30:00+05:00",
            "chat_type": "individual",
            "matched_keywords": ["urgent", "invoice"],
        }
        path = create_whatsapp_task(msg, vault, logger)
        assert path.exists()
        assert path.parent.name == "Needs_Action"
        assert path.name.startswith("WHATSAPP_")
        assert path.name.endswith(".md")

    def test_file_content(self, vault, logger):
        msg = {
            "sender": "Bob",
            "text": "Help me with this",
            "timestamp": "2026-02-22T10:00:00Z",
            "chat_type": "individual",
            "matched_keywords": ["help"],
        }
        path = create_whatsapp_task(msg, vault, logger)
        content = path.read_text(encoding="utf-8")

        assert "type: whatsapp" in content
        assert 'from: "Bob"' in content
        assert "priority: high" in content
        assert "status: new" in content
        assert "# WhatsApp Message from Bob" in content
        assert "Help me with this" in content

    def test_group_message(self, vault, logger):
        msg = {
            "sender": "Work Group",
            "text": "Urgent update on project",
            "timestamp": "2026-02-22T10:00:00Z",
            "chat_type": "group",
            "group_name": "Work Group",
            "matched_keywords": ["urgent"],
        }
        path = create_whatsapp_task(msg, vault, logger)
        content = path.read_text(encoding="utf-8")
        assert "chat_type: group" in content
        assert 'group_name: "Work Group"' in content

    def test_no_keywords_medium_priority(self, vault, logger):
        msg = {
            "sender": "Friend",
            "text": "Hey how are you",
            "timestamp": "2026-02-22T10:00:00Z",
            "chat_type": "individual",
            "matched_keywords": [],
        }
        path = create_whatsapp_task(msg, vault, logger)
        content = path.read_text(encoding="utf-8")
        assert "priority: medium" in content

    def test_audit_log_created(self, vault, logger):
        msg = {
            "sender": "Test",
            "text": "urgent test",
            "timestamp": "2026-02-22T10:00:00Z",
            "chat_type": "individual",
            "matched_keywords": ["urgent"],
        }
        create_whatsapp_task(msg, vault, logger)
        entries = logger.read_log()
        actions = [e["action"] for e in entries]
        assert "whatsapp_task_created" in actions

    def test_long_sender_name_truncated(self, vault, logger):
        msg = {
            "sender": "A" * 100,
            "text": "urgent",
            "timestamp": "2026-02-22T10:00:00Z",
            "chat_type": "individual",
            "matched_keywords": ["urgent"],
        }
        path = create_whatsapp_task(msg, vault, logger)
        # Filename should not be excessively long
        assert len(path.name) < 120
