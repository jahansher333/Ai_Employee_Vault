"""Auto Email Reply — generates reply drafts for common email types.

All replies go to Pending_Approval/ first. Human must approve before sending.

Usage:
    python scripts/auto_reply.py --draft          # Generate drafts for unprocessed emails
    python scripts/auto_reply.py --templates       # List available templates
    python scripts/auto_reply.py --send            # Process approved replies via Gmail
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger

load_dotenv()

# ---------------------------------------------------------------------------
# Reply templates
# ---------------------------------------------------------------------------

TEMPLATES = {
    "acknowledgment": (
        "Thank you for your email. We have received your message and "
        "will respond within 24 hours.\n\nBest regards"
    ),
    "out_of_office": (
        "Thank you for reaching out. I am currently out of office "
        "and will return on {return_date}. I will respond to your "
        "email upon my return.\n\nBest regards"
    ),
    "invoice_received": (
        "Thank you for sending the invoice. We have received it and "
        "it is being processed by our accounting team. Payment will "
        "be made according to the agreed terms.\n\nBest regards"
    ),
    "meeting_confirm": (
        "Thank you for the meeting invitation. I confirm my attendance "
        "and look forward to the discussion.\n\nBest regards"
    ),
    "custom": "{custom_text}",
}

# Keyword → template mapping for auto-detection
DETECTION_RULES = [
    (["invoice", "bill", "payment due", "amount due"], "invoice_received"),
    (["meeting", "calendar", "invite", "schedule", "call"], "meeting_confirm"),
    (["out of office", "ooo", "vacation", "leave"], "out_of_office"),
]


def list_templates() -> dict[str, str]:
    """Return available templates."""
    return {k: v[:80] + "..." if len(v) > 80 else v for k, v in TEMPLATES.items()}


def detect_reply_type(subject: str, body: str) -> str:
    """Auto-detect which template fits based on keywords."""
    text = f"{subject} {body}".lower()
    for keywords, template in DETECTION_RULES:
        if any(kw in text for kw in keywords):
            return template
    return "acknowledgment"


def generate_reply(
    email_data: dict,
    template_name: str,
    custom_text: str = "",
    return_date: str = "",
) -> str:
    """Generate reply text from a template.

    Parameters
    ----------
    email_data : dict
        Keys: from, subject, snippet, id
    template_name : str
        One of TEMPLATES keys
    """
    template = TEMPLATES.get(template_name, TEMPLATES["acknowledgment"])
    reply = template.format(
        return_date=return_date or "TBD",
        custom_text=custom_text or "Thank you for your email.",
    )
    return reply


def create_reply_draft(
    email_data: dict,
    template_name: str,
    vault_path: Path,
    custom_text: str = "",
    return_date: str = "",
) -> Path:
    """Save reply draft to Pending_Approval/. NEVER auto-sends.

    Returns path to the draft file.
    """
    reply_text = generate_reply(email_data, template_name, custom_text, return_date)

    sender = email_data.get("from", "Unknown")
    subject = email_data.get("subject", "No Subject")
    email_id = email_data.get("id", "unknown")
    now = datetime.now(timezone.utc)

    safe_subject = re.sub(r'[^\w\-]', '-', subject)[:40]
    timestamp = now.strftime("%H%M%S")
    filename = f"REPLY_{timestamp}_{safe_subject}.md"

    pending = vault_path / "Pending_Approval"
    pending.mkdir(parents=True, exist_ok=True)
    filepath = pending / filename

    content = f"""---
type: email_reply
to: "{sender}"
subject: "Re: {subject}"
original_email_id: "{email_id}"
template: {template_name}
status: pending
created_at: "{now.isoformat()}"
---

# Reply Draft

**To**: {sender}
**Subject**: Re: {subject}
**Template**: {template_name}
**Original Email ID**: {email_id}

## Reply Text

{reply_text}

## Instructions

- Review this reply before approving
- To approve: change `status: pending` to `status: approved` and move to `Approved/`
- To reject: delete this file or move to `Done/` with `status: rejected`
"""
    filepath.write_text(content, encoding="utf-8")

    logger = AuditLogger(vault_path)
    logger.log(
        "reply_draft_created",
        filepath.name,
        "success",
        details={"to": sender, "template": template_name},
    )

    return filepath


def scan_emails_for_replies(vault_path: Path) -> list[dict]:
    """Scan Needs_Action/ for EMAIL_ files that need replies."""
    needs_action = vault_path / "Needs_Action"
    if not needs_action.exists():
        return []

    emails = []
    for f in sorted(needs_action.glob("EMAIL_*.md")):
        content = f.read_text(encoding="utf-8")

        # Parse frontmatter
        fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if not fm_match:
            continue

        fm = fm_match.group(1)

        # Extract fields
        subject_m = re.search(r'^subject:\s*["\']?(.+?)["\']?\s*$', fm, re.MULTILINE)
        from_m = re.search(r'^from:\s*["\']?(.+?)["\']?\s*$', fm, re.MULTILINE)
        status_m = re.search(r'^status:\s*(\w+)', fm, re.MULTILINE)

        status = status_m.group(1) if status_m else "new"
        if status not in ("new", "planned"):
            continue

        emails.append({
            "file": f,
            "from": from_m.group(1) if from_m else "Unknown",
            "subject": subject_m.group(1) if subject_m else f.stem,
            "snippet": content[fm_match.end():fm_match.end() + 200],
            "id": f.stem,
        })

    return emails


def generate_drafts(vault_path: Path) -> list[Path]:
    """Generate reply drafts for all unprocessed emails."""
    emails = scan_emails_for_replies(vault_path)
    if not emails:
        print("No emails found that need replies.")
        return []

    paths = []
    for email in emails:
        template = detect_reply_type(email["subject"], email["snippet"])
        path = create_reply_draft(email, template, vault_path)
        print(f"  [DRAFT] {path.name} (template: {template})")
        paths.append(path)

    return paths


def process_approved_replies(vault_path: Path) -> list[str]:
    """Check Approved/ for reply files and attempt to send via Gmail.

    Returns list of sent reply filenames.
    """
    approved = vault_path / "Approved"
    if not approved.exists():
        return []

    sent = []
    logger = AuditLogger(vault_path)

    for f in sorted(approved.glob("REPLY_*.md")):
        content = f.read_text(encoding="utf-8")

        # Extract reply details from frontmatter
        to_m = re.search(r'^to:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
        subject_m = re.search(r'^subject:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)

        if not to_m:
            continue

        # Extract reply text
        text_match = re.search(r'## Reply Text\s*\n\n(.+?)(?:\n## |\Z)', content, re.DOTALL)
        reply_text = text_match.group(1).strip() if text_match else ""

        to_addr = to_m.group(1)
        subject = subject_m.group(1) if subject_m else "Re: (no subject)"

        # Try to send via Gmail
        try:
            _send_via_gmail(to_addr, subject, reply_text)
            sent.append(f.name)
            print(f"  [SENT] {f.name} -> {to_addr}")

            # Move to Done/
            done = vault_path / "Done"
            done.mkdir(parents=True, exist_ok=True)
            dest = done / f.name
            dest.write_text(
                content.replace("status: approved", "status: sent"),
                encoding="utf-8",
            )
            f.unlink()

            logger.log("reply_sent", f.name, "success",
                       details={"to": to_addr, "subject": subject})
        except Exception as exc:
            print(f"  [ERROR] {f.name}: {exc}")
            logger.log("reply_send_failed", f.name, "error", error=str(exc))

    return sent


def _send_via_gmail(to: str, subject: str, body: str) -> None:
    """Send email via Gmail API. Raises on failure."""
    try:
        from gmail_watcher import build_gmail_service
        import base64
        from email.mime.text import MIMEText

        creds_path = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
        token_path = os.getenv("GMAIL_TOKEN_PATH", "token.json")
        service = build_gmail_service(creds_path, token_path)

        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
    except ImportError:
        # Simulation mode
        print(f"  [SIMULATED] Reply to {to}: {subject}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto Email Reply System")
    parser.add_argument("--draft", action="store_true", help="Generate reply drafts")
    parser.add_argument("--send", action="store_true", help="Process approved replies")
    parser.add_argument("--templates", action="store_true", help="List templates")
    parser.add_argument("--vault-path", default=None)
    args = parser.parse_args()

    vault = Path(args.vault_path or os.getenv("VAULT_PATH", str(Path(__file__).parent.parent)))

    if args.templates:
        print("Available reply templates:")
        for name, preview in list_templates().items():
            print(f"  {name}: {preview}")
        return

    if args.draft:
        paths = generate_drafts(vault)
        print(f"\nGenerated {len(paths)} reply drafts in Pending_Approval/")
        return

    if args.send:
        sent = process_approved_replies(vault)
        print(f"\nSent {len(sent)} approved replies.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
