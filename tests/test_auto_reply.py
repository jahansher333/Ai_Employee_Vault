"""Tests for auto_reply.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.auto_reply import (
    create_reply_draft,
    detect_reply_type,
    generate_reply,
    list_templates,
    scan_emails_for_replies,
)


@pytest.fixture
def vault(tmp_path):
    for d in ["Needs_Action", "Pending_Approval", "Approved", "Done", "Logs"]:
        (tmp_path / d).mkdir()
    return tmp_path


SAMPLE_EMAIL = {
    "id": "EMAIL_001",
    "from": "client@example.com",
    "subject": "Project Update",
    "snippet": "Please review the latest changes.",
}


class TestTemplates:
    def test_list_templates(self):
        templates = list_templates()
        assert "acknowledgment" in templates
        assert "invoice_received" in templates
        assert "meeting_confirm" in templates
        assert "out_of_office" in templates
        assert "custom" in templates


class TestDetectReplyType:
    def test_invoice_email(self):
        assert detect_reply_type("Invoice #123", "Payment due") == "invoice_received"

    def test_meeting_email(self):
        assert detect_reply_type("Meeting Invite", "calendar link") == "meeting_confirm"

    def test_default_acknowledgment(self):
        assert detect_reply_type("Hello", "How are you?") == "acknowledgment"

    def test_case_insensitive(self):
        assert detect_reply_type("INVOICE attached", "") == "invoice_received"


class TestGenerateReply:
    def test_acknowledgment(self):
        reply = generate_reply(SAMPLE_EMAIL, "acknowledgment")
        assert "Thank you" in reply
        assert "24 hours" in reply

    def test_invoice(self):
        reply = generate_reply(SAMPLE_EMAIL, "invoice_received")
        assert "invoice" in reply.lower()
        assert "accounting" in reply.lower()

    def test_meeting(self):
        reply = generate_reply(SAMPLE_EMAIL, "meeting_confirm")
        assert "confirm" in reply.lower()

    def test_out_of_office(self):
        reply = generate_reply(SAMPLE_EMAIL, "out_of_office", return_date="2026-03-20")
        assert "2026-03-20" in reply

    def test_custom(self):
        reply = generate_reply(SAMPLE_EMAIL, "custom", custom_text="Custom message here.")
        assert "Custom message here" in reply


class TestCreateDraft:
    def test_creates_file(self, vault):
        path = create_reply_draft(SAMPLE_EMAIL, "acknowledgment", vault)
        assert path.exists()
        assert "REPLY_" in path.name
        assert path.parent.name == "Pending_Approval"

    def test_file_content(self, vault):
        path = create_reply_draft(SAMPLE_EMAIL, "acknowledgment", vault)
        content = path.read_text(encoding="utf-8")
        assert "type: email_reply" in content
        assert 'to: "client@example.com"' in content
        assert "status: pending" in content
        assert "Thank you" in content

    def test_invoice_template(self, vault):
        email = {**SAMPLE_EMAIL, "subject": "Invoice #99"}
        path = create_reply_draft(email, "invoice_received", vault)
        content = path.read_text(encoding="utf-8")
        assert "template: invoice_received" in content


class TestScanEmails:
    def test_finds_email_files(self, vault):
        (vault / "Needs_Action" / "EMAIL_001_Test.md").write_text(
            "---\ntype: email\nfrom: test@test.com\nsubject: Hello\nstatus: new\n---\n\n# Hello\n"
        )
        emails = scan_emails_for_replies(vault)
        assert len(emails) == 1
        assert emails[0]["from"] == "test@test.com"

    def test_skips_processed(self, vault):
        (vault / "Needs_Action" / "EMAIL_002_Done.md").write_text(
            "---\ntype: email\nfrom: a@b.com\nsubject: Done\nstatus: done\n---\n\n# Done\n"
        )
        emails = scan_emails_for_replies(vault)
        assert len(emails) == 0

    def test_empty_folder(self, vault):
        assert scan_emails_for_replies(vault) == []
