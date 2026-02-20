"""Gmail Watcher -- polls Gmail for unread emails and creates task files.

Silver Tier: Second watcher source. Monitors a Gmail inbox via the
Gmail API, creates Markdown task files in Needs_Action/ for each new
unread email, marks them as read, and tracks processed IDs in a ledger.

Usage:
    python scripts/gmail_watcher.py [--vault-path /path] [--interval 60]
    python scripts/gmail_watcher.py --auth-only
"""

from __future__ import annotations

import argparse
import base64
from email.mime.text import MIMEText
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore[assignment]

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger

# Gmail API scopes: read emails + modify (mark as read) + send
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


# ---------------------------------------------------------------------------
# Ledger helpers (same pattern as watcher.py)
# ---------------------------------------------------------------------------

def load_gmail_ledger(path: Path) -> set[str]:
    """Load processed Gmail message IDs from ledger file."""
    if not path.exists():
        return set()
    try:
        return set(path.read_text(encoding="utf-8").splitlines())
    except Exception:
        return set()


def save_to_gmail_ledger(path: Path, message_id: str) -> None:
    """Append a single message ID to the Gmail ledger."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(message_id + "\n")


# ---------------------------------------------------------------------------
# Gmail authentication
# ---------------------------------------------------------------------------

def build_gmail_service(
    credentials_path: str | Path,
    token_path: str | Path,
) -> object:
    """Build an authenticated Gmail API service.

    On first run, opens a browser for OAuth consent and saves the
    refresh token to *token_path*.  On subsequent runs the saved
    token is reused automatically.

    Returns a googleapiclient Resource or raises on failure.
    """
    if not HAS_GOOGLE:
        print(
            "ERROR: Google API libraries not installed.\n"
            "Run: pip install google-api-python-client google-auth-oauthlib"
        )
        sys.exit(1)

    credentials_path = Path(credentials_path)
    token_path = Path(token_path)

    if not credentials_path.exists():
        print(
            f"ERROR: Gmail credentials file not found: {credentials_path}\n"
            "Steps to fix:\n"
            "  1. Go to https://console.cloud.google.com/\n"
            "  2. Enable the Gmail API\n"
            "  3. Create OAuth 2.0 Client ID (Desktop application)\n"
            "  4. Download credentials.json to your vault root\n"
            "  5. Set GMAIL_CREDENTIALS_PATH in .env"
        )
        sys.exit(1)

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), SCOPES
            )
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=creds)


# ---------------------------------------------------------------------------
# Gmail operations
# ---------------------------------------------------------------------------

def _extract_header(headers: list[dict], name: str) -> str:
    """Extract a header value from Gmail message headers."""
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def fetch_unread_emails(
    service: object, max_results: int = 10
) -> list[dict]:
    """Fetch unread emails from Gmail.

    Returns a list of dicts with keys:
        id, from, subject, snippet, date, is_important
    """
    try:
        results = (
            service.users()
            .messages()
            .list(userId="me", q="is:unread", maxResults=max_results)
            .execute()
        )
    except HttpError as e:
        print(f"  [ERROR] Gmail API list failed: {e}")
        return []

    messages = results.get("messages", [])
    if not messages:
        return []

    emails = []
    for msg_stub in messages:
        try:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_stub["id"], format="full")
                .execute()
            )
        except HttpError as e:
            print(f"  [ERROR] Gmail API get failed for {msg_stub['id']}: {e}")
            continue

        headers = msg.get("payload", {}).get("headers", [])
        label_ids = msg.get("labelIds", [])

        emails.append(
            {
                "id": msg["id"],
                "from": _extract_header(headers, "From"),
                "subject": _extract_header(headers, "Subject") or "(No Subject)",
                "snippet": msg.get("snippet", "")[:500],
                "date": _extract_header(headers, "Date"),
                "is_important": "IMPORTANT" in label_ids,
            }
        )

    return emails


def mark_as_read(service: object, message_id: str) -> bool:
    """Mark a Gmail message as read by removing the UNREAD label."""
    try:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["UNREAD"]},
        ).execute()
        return True
    except HttpError as e:
        print(f"  [ERROR] Failed to mark {message_id} as read: {e}")
        return False


def get_email_for_reply(service: object, message_id: str) -> dict | None:
    """Fetch full email details needed to compose a reply."""
    try:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
    except HttpError as e:
        print(f"  [ERROR] Failed to fetch message {message_id}: {e}")
        return None

    headers = msg.get("payload", {}).get("headers", [])
    return {
        "id": msg["id"],
        "threadId": msg.get("threadId", ""),
        "from": _extract_header(headers, "From"),
        "to": _extract_header(headers, "To"),
        "subject": _extract_header(headers, "Subject"),
        "message_id": _extract_header(headers, "Message-ID"),
        "references": _extract_header(headers, "References"),
        "snippet": msg.get("snippet", "")[:500],
    }


def reply_to_email(
    service: object, message_id: str, body_text: str
) -> bool:
    """Reply to a Gmail message by ID.

    Constructs a proper reply with In-Reply-To and References headers,
    keeps the same thread, and sends via Gmail API.
    Returns True on success, False on failure.
    """
    original = get_email_for_reply(service, message_id)
    if not original:
        return False

    # Build reply-to address (reply to sender)
    reply_to = original["from"]

    # Build subject with Re: prefix
    subject = original["subject"]
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    # Create MIME message
    mime_msg = MIMEText(body_text)
    mime_msg["to"] = reply_to
    mime_msg["subject"] = subject
    mime_msg["In-Reply-To"] = original["message_id"]
    # Chain references for proper threading
    refs = original["references"]
    if refs:
        mime_msg["References"] = f"{refs} {original['message_id']}"
    else:
        mime_msg["References"] = original["message_id"]

    raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()

    try:
        service.users().messages().send(
            userId="me",
            body={"raw": raw, "threadId": original["threadId"]},
        ).execute()
        return True
    except HttpError as e:
        print(f"  [ERROR] Failed to send reply to {message_id}: {e}")
        return False


def send_email(
    service: object, to: str, subject: str, body_text: str
) -> bool:
    """Send a new email (not a reply).

    Returns True on success, False on failure.
    """
    mime_msg = MIMEText(body_text)
    mime_msg["to"] = to
    mime_msg["subject"] = subject

    raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()

    try:
        service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        return True
    except HttpError as e:
        print(f"  [ERROR] Failed to send email: {e}")
        return False


# ---------------------------------------------------------------------------
# Task file creation
# ---------------------------------------------------------------------------

def _sanitize_filename(text: str, max_len: int = 50) -> str:
    """Sanitize a string for use in a filename."""
    clean = re.sub(r"[^\w\s-]", "", text)
    clean = re.sub(r"[\s]+", "-", clean).strip("-")
    return clean[:max_len] if clean else "no-subject"


def create_email_task(email_data: dict, vault_path: Path) -> Path:
    """Create a Markdown task file from an email dict.

    File is placed in Needs_Action/ with naming pattern:
        EMAIL_{HHMMSS}_{sanitized_subject}.md
    """
    needs_action = vault_path / "Needs_Action"
    needs_action.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%H%M%S")
    safe_subject = _sanitize_filename(email_data["subject"])
    filename = f"EMAIL_{timestamp}_{safe_subject}.md"

    priority = "high" if email_data.get("is_important") else "medium"

    content = (
        f"---\n"
        f"type: email\n"
        f'from: "{email_data["from"]}"\n'
        f'subject: "{email_data["subject"]}"\n'
        f'date: "{email_data["date"]}"\n'
        f"priority: {priority}\n"
        f"gmail_id: {email_data['id']}\n"
        f"status: new\n"
        f"---\n\n"
        f"# {email_data['subject']}\n\n"
        f"**From**: {email_data['from']}\n"
        f"**Date**: {email_data['date']}\n\n"
        f"## Email Snippet\n\n"
        f"{email_data['snippet'] or '(No email body)'}\n"
    )

    file_path = needs_action / filename
    file_path.write_text(content, encoding="utf-8")
    return file_path


# ---------------------------------------------------------------------------
# Main watcher loop
# ---------------------------------------------------------------------------

def start_gmail_watcher(
    vault_path: Path,
    interval: float = 60.0,
    credentials_path: str = "credentials.json",
    token_path: str = "token.json",
    max_results: int = 10,
) -> None:
    """Start the Gmail polling loop.

    Polls for unread emails every *interval* seconds, creates task
    files, marks emails as read, and logs all events.
    """
    logger = AuditLogger(vault_path)
    ledger_path = vault_path / "Logs" / ".gmail_ledger.txt"

    # Build authenticated service
    service = build_gmail_service(credentials_path, token_path)

    logger.log(
        "gmail_watcher_started",
        "system",
        "success",
        details={"vault": str(vault_path), "interval": interval},
    )
    print(f"Gmail Watcher started (polling every {interval}s)")
    print(f"Vault: {vault_path}")
    print("Press Ctrl+C to stop.\n")

    seen = load_gmail_ledger(ledger_path)

    try:
        while True:
            emails = fetch_unread_emails(service, max_results)
            logger.log(
                "gmail_poll",
                "system",
                "success",
                details={"emails_found": len(emails)},
            )

            for email_data in emails:
                msg_id = email_data["id"]
                if msg_id in seen:
                    continue

                try:
                    file_path = create_email_task(email_data, vault_path)
                    mark_as_read(service, msg_id)

                    seen.add(msg_id)
                    save_to_gmail_ledger(ledger_path, msg_id)

                    logger.log(
                        "email_processed",
                        file_path.name,
                        "success",
                        details={
                            "from": email_data["from"],
                            "subject": email_data["subject"],
                            "priority": "high"
                            if email_data.get("is_important")
                            else "medium",
                        },
                    )
                    subj = email_data['subject'][:60].encode('ascii', 'replace').decode()
                    print(f"  [EMAIL] {subj} -> {file_path.name}")
                except Exception as exc:
                    logger.log(
                        "email_processed",
                        email_data.get("subject", "unknown"),
                        "error",
                        error=str(exc),
                    )
                    subj = email_data.get('subject', '?').encode('ascii', 'replace').decode()
                    err = str(exc).encode('ascii', 'replace').decode()
                    print(f"  [ERROR] {subj}: {err}")

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nGmail Watcher stopped.")
    finally:
        logger.log("gmail_watcher_stopped", "system", "success")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Gmail Watcher for AI Employee")
    parser.add_argument("--vault-path", default=None)
    parser.add_argument("--interval", type=float, default=None)
    parser.add_argument("--max-results", type=int, default=None)
    parser.add_argument(
        "--auth-only",
        action="store_true",
        help="Authenticate only (no polling loop)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check for unread emails and display them (no processing)",
    )
    parser.add_argument(
        "--reply",
        nargs=2,
        metavar=("GMAIL_ID", "MESSAGE"),
        help="Reply to an email by Gmail ID with a message",
    )
    parser.add_argument(
        "--send",
        nargs=3,
        metavar=("TO", "SUBJECT", "MESSAGE"),
        help="Send a new email: --send to@email.com 'Subject' 'Body'",
    )
    args = parser.parse_args()

    # Load .env
    if load_dotenv:
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(str(env_path))

    vault = Path(
        args.vault_path
        or os.getenv("VAULT_PATH", str(Path(__file__).parent.parent))
    )
    creds_path = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
    token_path = os.getenv("GMAIL_TOKEN_PATH", "token.json")
    interval = args.interval or float(os.getenv("GMAIL_POLL_INTERVAL", "60"))
    max_results = args.max_results or int(os.getenv("GMAIL_MAX_RESULTS", "10"))

    if args.auth_only:
        print("Authenticating with Gmail API...")
        build_gmail_service(creds_path, token_path)
        print("Authentication successful! token.json has been created.")
        return

    if args.check:
        service = build_gmail_service(creds_path, token_path)
        emails = fetch_unread_emails(service, max_results)
        if not emails:
            print("No unread emails found.")
            return
        print(f"Found {len(emails)} unread email(s):\n")
        for i, e in enumerate(emails, 1):
            subj = e["subject"].encode("ascii", "replace").decode()
            frm = e["from"].encode("ascii", "replace").decode()
            snip = e["snippet"][:150].encode("ascii", "replace").decode()
            print(f"  {i}. [{e['id']}]")
            print(f"     From: {frm}")
            print(f"     Subject: {subj}")
            print(f"     Date: {e['date']}")
            print(f"     Snippet: {snip}")
            print()
        return

    if args.reply:
        gmail_id, message = args.reply
        service = build_gmail_service(creds_path, token_path)
        print(f"Replying to {gmail_id}...")
        if reply_to_email(service, gmail_id, message):
            print("Reply sent successfully!")
        else:
            print("Failed to send reply.")
        return

    if args.send:
        to_addr, subject, message = args.send
        service = build_gmail_service(creds_path, token_path)
        print(f"Sending email to {to_addr}...")
        if send_email(service, to_addr, subject, message):
            print("Email sent successfully!")
        else:
            print("Failed to send email.")
        return

    start_gmail_watcher(vault, interval, creds_path, token_path, max_results)


if __name__ == "__main__":
    main()
