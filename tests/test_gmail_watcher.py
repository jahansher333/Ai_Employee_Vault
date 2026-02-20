"""Tests for scripts/gmail_watcher.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from gmail_watcher import (
    _extract_header,
    _sanitize_filename,
    create_email_task,
    load_gmail_ledger,
    save_to_gmail_ledger,
)


# ---------------------------------------------------------------------------
# Ledger tests
# ---------------------------------------------------------------------------

class TestGmailLedger:
    def test_load_empty_ledger(self, tmp_path):
        path = tmp_path / "ledger.txt"
        assert load_gmail_ledger(path) == set()

    def test_save_and_load_roundtrip(self, tmp_path):
        path = tmp_path / "Logs" / ".gmail_ledger.txt"
        save_to_gmail_ledger(path, "msg_001")
        save_to_gmail_ledger(path, "msg_002")
        result = load_gmail_ledger(path)
        assert result == {"msg_001", "msg_002"}

    def test_incremental_append(self, tmp_path):
        path = tmp_path / "ledger.txt"
        save_to_gmail_ledger(path, "a")
        save_to_gmail_ledger(path, "b")
        save_to_gmail_ledger(path, "c")
        assert len(load_gmail_ledger(path)) == 3


# ---------------------------------------------------------------------------
# Header extraction tests
# ---------------------------------------------------------------------------

class TestExtractHeader:
    def test_extracts_existing_header(self):
        headers = [
            {"name": "From", "value": "alice@example.com"},
            {"name": "Subject", "value": "Hello"},
        ]
        assert _extract_header(headers, "From") == "alice@example.com"
        assert _extract_header(headers, "Subject") == "Hello"

    def test_case_insensitive(self):
        headers = [{"name": "FROM", "value": "bob@test.com"}]
        assert _extract_header(headers, "from") == "bob@test.com"

    def test_missing_header(self):
        headers = [{"name": "From", "value": "x@y.com"}]
        assert _extract_header(headers, "Date") == ""


# ---------------------------------------------------------------------------
# Filename sanitization tests
# ---------------------------------------------------------------------------

class TestSanitizeFilename:
    def test_basic(self):
        assert _sanitize_filename("Hello World") == "Hello-World"

    def test_special_chars(self):
        result = _sanitize_filename("Re: Invoice #123 [URGENT]")
        assert "#" not in result
        assert "[" not in result

    def test_empty_string(self):
        assert _sanitize_filename("") == "no-subject"

    def test_max_length(self):
        long = "A" * 100
        assert len(_sanitize_filename(long, max_len=50)) == 50


# ---------------------------------------------------------------------------
# Email task creation tests
# ---------------------------------------------------------------------------

class TestCreateEmailTask:
    def test_creates_task_file(self, tmp_path):
        needs_action = tmp_path / "Needs_Action"
        email_data = {
            "id": "msg_test_001",
            "from": "sender@example.com",
            "subject": "Meeting Tomorrow",
            "snippet": "Hi, let us discuss the project tomorrow.",
            "date": "2026-02-21T10:30:00Z",
            "is_important": False,
        }
        path = create_email_task(email_data, tmp_path)
        assert path.exists()
        assert path.name.startswith("EMAIL_")
        assert path.name.endswith(".md")

        content = path.read_text(encoding="utf-8")
        assert "type: email" in content
        assert "sender@example.com" in content
        assert "Meeting Tomorrow" in content
        assert "priority: medium" in content
        assert "gmail_id: msg_test_001" in content
        assert "status: new" in content

    def test_important_email_gets_high_priority(self, tmp_path):
        email_data = {
            "id": "msg_important",
            "from": "boss@company.com",
            "subject": "Urgent Action Required",
            "snippet": "Please review ASAP.",
            "date": "2026-02-21T14:00:00Z",
            "is_important": True,
        }
        path = create_email_task(email_data, tmp_path)
        content = path.read_text(encoding="utf-8")
        assert "priority: high" in content

    def test_no_subject_email(self, tmp_path):
        email_data = {
            "id": "msg_nosub",
            "from": "anon@test.com",
            "subject": "(No Subject)",
            "snippet": "",
            "date": "2026-02-21",
            "is_important": False,
        }
        path = create_email_task(email_data, tmp_path)
        content = path.read_text(encoding="utf-8")
        assert "(No Subject)" in content
        assert "(No email body)" in content

    def test_creates_needs_action_dir(self, tmp_path):
        vault = tmp_path / "vault"
        email_data = {
            "id": "msg_mkdir",
            "from": "a@b.com",
            "subject": "Test",
            "snippet": "body",
            "date": "2026-02-21",
            "is_important": False,
        }
        path = create_email_task(email_data, vault)
        assert (vault / "Needs_Action").is_dir()
        assert path.exists()
