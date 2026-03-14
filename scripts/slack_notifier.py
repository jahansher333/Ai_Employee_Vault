"""Slack notification system for AI Employee events.

Sends alerts via Slack Incoming Webhooks for task completions,
approval requests, briefings, low stock, and overdue invoices.

Usage:
    python scripts/slack_notifier.py --test "Hello from AI Employee"
    python scripts/slack_notifier.py --summary
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger

load_dotenv()

WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "")


def format_slack_message(
    title: str,
    fields: list[dict] | None = None,
    color: str = "#36a64f",
    text: str = "",
) -> dict:
    """Build a Slack attachment message payload."""
    attachment = {"title": title, "color": color, "ts": datetime.now(timezone.utc).timestamp()}
    if text:
        attachment["text"] = text
    if fields:
        attachment["fields"] = [
            {"title": f.get("title", ""), "value": f.get("value", ""), "short": f.get("short", True)}
            for f in fields
        ]
    payload: dict = {"attachments": [attachment]}
    if SLACK_CHANNEL:
        payload["channel"] = SLACK_CHANNEL
    return payload


def send_notification(
    message: str,
    channel: str | None = None,
    priority: str = "normal",
    vault_path: Path | None = None,
) -> dict:
    """Send a text message to Slack.

    If SLACK_WEBHOOK_URL is not set, runs in simulation mode.
    """
    color = {"high": "#ff0000", "normal": "#36a64f", "low": "#cccccc"}.get(priority, "#36a64f")
    payload = format_slack_message("AI Employee", text=message, color=color)
    if channel:
        payload["channel"] = channel

    return _send(payload, vault_path)


def notify_task_complete(filename: str, result: str, vault_path: Path | None = None) -> dict:
    """Notify when a task moves to Done/."""
    payload = format_slack_message(
        "Task Completed",
        fields=[
            {"title": "File", "value": filename},
            {"title": "Result", "value": result},
        ],
        color="#36a64f",
    )
    return _send(payload, vault_path)


def notify_approval_needed(filename: str, vault_path: Path | None = None) -> dict:
    """Notify when an item needs human approval."""
    payload = format_slack_message(
        "Approval Needed",
        fields=[{"title": "File", "value": filename, "short": False}],
        color="#ff9900",
        text="A task requires human review in Pending_Approval/",
    )
    return _send(payload, vault_path)


def notify_briefing_ready(briefing_path: str, vault_path: Path | None = None) -> dict:
    """Notify when CEO briefing is generated."""
    payload = format_slack_message(
        "CEO Briefing Ready",
        text=f"New briefing generated: {briefing_path}",
        color="#0066cc",
    )
    return _send(payload, vault_path)


def notify_low_stock(products: list[dict], vault_path: Path | None = None) -> dict:
    """Notify when products are low on stock."""
    lines = [f"- {p.get('name', '?')}: {p.get('qty_available', 0)} units" for p in products[:10]]
    payload = format_slack_message(
        f"Low Stock Alert ({len(products)} products)",
        text="\n".join(lines),
        color="#ff0000",
    )
    return _send(payload, vault_path)


def notify_overdue_invoices(invoices: list[dict], vault_path: Path | None = None) -> dict:
    """Notify when overdue invoices are found."""
    total = sum(i.get("amount_residual", 0) for i in invoices)
    lines = [
        f"- {i.get('name', '?')} | {i.get('partner_name', '?')} | ${i.get('amount_residual', 0):,.2f}"
        for i in invoices[:10]
    ]
    payload = format_slack_message(
        f"Overdue Invoices ({len(invoices)}) — ${total:,.2f}",
        text="\n".join(lines),
        color="#ff0000",
    )
    return _send(payload, vault_path)


def _send(payload: dict, vault_path: Path | None = None) -> dict:
    """Send payload to Slack or simulate."""
    logger = AuditLogger(vault_path or Path("."))

    if not WEBHOOK_URL:
        # Simulation mode
        logger.log(
            "slack_simulated",
            "slack",
            "success",
            details={"payload_title": payload.get("attachments", [{}])[0].get("title", "")},
        )
        return {"ok": True, "mode": "simulate", "payload": payload}

    try:
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        success = resp.status_code == 200
        logger.log(
            "slack_sent" if success else "slack_failed",
            "slack",
            "success" if success else "error",
            details={"status_code": resp.status_code},
        )
        return {"ok": success, "mode": "api", "status_code": resp.status_code}
    except Exception as exc:
        logger.log("slack_error", "slack", "error", error=str(exc))
        return {"ok": False, "mode": "api", "error": str(exc)}


def send_status_summary(vault_path: Path) -> dict:
    """Send current vault status summary to Slack."""
    counts = {}
    for folder in ["Needs_Action", "Pending_Approval", "Approved", "Done", "Plans", "Archive"]:
        p = vault_path / folder
        counts[folder] = len(list(p.glob("*.md"))) if p.exists() else 0

    text = "\n".join(f"- **{k}**: {v} items" for k, v in counts.items())
    payload = format_slack_message(
        "AI Employee Status",
        text=text,
        color="#0066cc",
    )
    return _send(payload, vault_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Slack notifications for AI Employee")
    parser.add_argument("--test", type=str, help="Send a test message")
    parser.add_argument("--summary", action="store_true", help="Send vault status summary")
    parser.add_argument("--vault-path", default=None)
    args = parser.parse_args()

    vault = Path(args.vault_path or os.getenv("VAULT_PATH", str(Path(__file__).parent.parent)))

    if args.test:
        result = send_notification(args.test, vault_path=vault)
        mode = result.get("mode", "unknown")
        print(f"Sent ({mode}): {args.test}")
        return

    if args.summary:
        result = send_status_summary(vault)
        print(f"Summary sent ({result.get('mode', 'unknown')})")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
