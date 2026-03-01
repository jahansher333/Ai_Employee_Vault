"""MCP Server for Gmail email integration.

Gold Tier: Exposes Gmail operations as MCP tools callable from Claude Code.
Wraps gmail_watcher.py — no logic duplication.

Start: python scripts/mcp_email_server.py (stdio transport)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).parent))

mcp = FastMCP("email", instructions="Gmail integration — fetch, send, reply, mark read, create tasks from emails")

VAULT_PATH = Path(os.getenv("VAULT_PATH", str(Path(__file__).parent.parent)))

_gmail_service = None


def _get_service():
    """Lazy-init Gmail API service."""
    global _gmail_service
    if _gmail_service is not None:
        return _gmail_service
    try:
        from gmail_watcher import build_gmail_service
        _gmail_service = build_gmail_service()
        return _gmail_service
    except Exception as exc:
        raise RuntimeError(f"Gmail service unavailable: {exc}")


@mcp.tool()
def fetch_unread_emails(max_results: int = 10) -> dict:
    """Fetch unread emails from Gmail inbox.

    Args:
        max_results: Maximum emails to return (default 10)
    """
    try:
        from gmail_watcher import fetch_unread_emails as _fetch
        service = _get_service()
        emails = _fetch(service, max_results=max_results)
        return {"success": True, "emails": emails, "count": len(emails)}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def send_email(to: str, subject: str, body_text: str) -> dict:
    """Send a new email via Gmail.

    Args:
        to: Recipient email address
        subject: Email subject line
        body_text: Plain text body of the email
    """
    try:
        from gmail_watcher import send_email as _send
        service = _get_service()
        result = _send(service, to, subject, body_text)
        return {"success": True, "message_id": result.get("id", ""),
                "thread_id": result.get("threadId", "")}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def reply_to_email(message_id: str, body_text: str) -> dict:
    """Reply to an existing email thread.

    Args:
        message_id: Gmail message ID to reply to
        body_text: Reply body text
    """
    try:
        from gmail_watcher import reply_to_email as _reply
        service = _get_service()
        result = _reply(service, message_id, body_text)
        if result:
            return {"success": True, "message_id": result.get("id", ""),
                    "thread_id": result.get("threadId", "")}
        return {"success": False, "error": "Reply failed — could not find original email"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def mark_email_read(message_id: str) -> dict:
    """Mark a Gmail message as read.

    Args:
        message_id: Gmail message ID to mark as read
    """
    try:
        from gmail_watcher import mark_as_read
        service = _get_service()
        success = mark_as_read(service, message_id)
        return {"success": success}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def create_email_task(subject: str, sender: str, body_preview: str = "",
                      gmail_id: str = "") -> dict:
    """Create a task file in Needs_Action/ from email data.

    Args:
        subject: Email subject
        sender: Sender email address
        body_preview: First ~500 chars of email body
        gmail_id: Gmail message ID for reference
    """
    try:
        from gmail_watcher import create_email_task as _create
        from audit_logger import AuditLogger
        email_data = {
            "subject": subject,
            "from": sender,
            "snippet": body_preview,
            "id": gmail_id,
            "date": "",
        }
        path = _create(email_data, VAULT_PATH)
        logger = AuditLogger(VAULT_PATH)
        logger.log("email_task_created", path.name, "success",
                   details={"gmail_id": gmail_id, "subject": subject})
        return {"success": True, "file": str(path)}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


if __name__ == "__main__":
    mcp.run()
