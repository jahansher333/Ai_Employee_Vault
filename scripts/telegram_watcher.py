"""Telegram Bot watcher — monitors for priority messages via Bot API.

Uses simple HTTP polling (getUpdates) to detect incoming messages
with priority keywords and creates task files in Needs_Action/.

Usage:
    python scripts/telegram_watcher.py --check       # One-shot check
    python scripts/telegram_watcher.py --interval 15  # Custom poll interval
    python scripts/telegram_watcher.py                # Continuous poll (30s)
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger

load_dotenv()

PRIORITY_KEYWORDS = [
    kw.strip().lower()
    for kw in os.getenv(
        "TELEGRAM_KEYWORDS", "urgent,invoice,payment,help,deadline,asap"
    ).split(",")
]

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
DEFAULT_INTERVAL = int(os.getenv("TELEGRAM_POLL_INTERVAL", "30"))


# ---------------------------------------------------------------------------
# Ledger (deduplication)
# ---------------------------------------------------------------------------

def load_telegram_ledger(path: Path) -> set[str]:
    """Read ledger file into a set of message hashes."""
    if not path.exists():
        return set()
    try:
        return set(path.read_text(encoding="utf-8").splitlines())
    except Exception:
        return set()


def save_to_telegram_ledger(path: Path, entry: str) -> None:
    """Append an entry to the ledger file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


def compute_message_hash(chat_id: int, message_id: int, text: str) -> str:
    """Create a unique hash for deduplication."""
    raw = f"{chat_id}:{message_id}:{text}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Keyword matching
# ---------------------------------------------------------------------------

def match_keywords(text: str) -> list[str]:
    """Return list of matched priority keywords in text."""
    lower = text.lower()
    return [kw for kw in PRIORITY_KEYWORDS if kw in lower]


# ---------------------------------------------------------------------------
# Telegram API
# ---------------------------------------------------------------------------

def get_updates(offset: int | None = None, timeout: int = 10) -> list[dict]:
    """Poll Telegram Bot API for new updates."""
    if not BOT_TOKEN:
        return []
    params: dict = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    try:
        resp = requests.get(f"{API_BASE}/getUpdates", params=params, timeout=timeout + 5)
        resp.raise_for_status()
        data = resp.json()
        if data.get("ok"):
            return data.get("result", [])
    except Exception as exc:
        print(f"  [ERROR] Telegram API: {exc}")
    return []


def get_bot_info() -> dict | None:
    """Get bot info via getMe endpoint."""
    if not BOT_TOKEN:
        return None
    try:
        resp = requests.get(f"{API_BASE}/getMe", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("ok"):
            return data.get("result")
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Task creation
# ---------------------------------------------------------------------------

def create_telegram_task(
    message: dict,
    matched: list[str],
    vault_path: Path,
) -> Path:
    """Create a task .md file in Needs_Action/ from a Telegram message."""
    msg = message.get("message", message)
    chat = msg.get("chat", {})
    sender = msg.get("from", {})

    sender_name = sender.get("first_name", "Unknown")
    if sender.get("last_name"):
        sender_name += f" {sender['last_name']}"
    username = sender.get("username", "")

    text = msg.get("text", "")
    chat_type = chat.get("type", "private")
    chat_title = chat.get("title", sender_name)
    msg_date = datetime.fromtimestamp(msg.get("date", 0), tz=timezone.utc)

    priority = "high" if matched else "medium"
    timestamp = msg_date.strftime("%H%M%S")
    safe_sender = re.sub(r'[^\w\-]', '-', sender_name)[:30]
    filename = f"TELEGRAM_{timestamp}_{safe_sender}.md"

    needs_action = vault_path / "Needs_Action"
    needs_action.mkdir(parents=True, exist_ok=True)
    filepath = needs_action / filename

    # Avoid overwrite
    if filepath.exists():
        filepath = needs_action / f"TELEGRAM_{timestamp}_{safe_sender}_{msg.get('message_id', 0)}.md"

    content = f"""---
type: telegram
from: "{sender_name}"
username: "{username}"
chat: "{chat_title}"
chat_type: {chat_type}
message_id: {msg.get('message_id', 0)}
date: "{msg_date.isoformat()}"
priority: {priority}
matched_keywords: {matched}
status: new
---

# Telegram Message from {sender_name}

**From**: {sender_name} (@{username})
**Chat**: {chat_title} ({chat_type})
**Date**: {msg_date.strftime('%Y-%m-%d %H:%M:%S UTC')}
**Priority**: {priority}
**Keywords**: {', '.join(matched) if matched else 'none'}

## Message

{text}

## Action Plan

- [ ] Review message content
- [ ] Determine required response
- [ ] Execute response or escalate
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath


# ---------------------------------------------------------------------------
# Watcher
# ---------------------------------------------------------------------------

def process_updates(
    updates: list[dict],
    vault_path: Path,
    logger: AuditLogger,
    ledger_path: Path,
    seen: set[str],
) -> int:
    """Process a batch of updates. Returns count of new tasks created."""
    created = 0
    for update in updates:
        msg = update.get("message", {})
        text = msg.get("text", "")
        if not text:
            continue

        chat_id = msg.get("chat", {}).get("id", 0)
        message_id = msg.get("message_id", 0)
        msg_hash = compute_message_hash(chat_id, message_id, text)

        if msg_hash in seen:
            continue

        matched = match_keywords(text)
        if not matched:
            seen.add(msg_hash)
            save_to_telegram_ledger(ledger_path, msg_hash)
            continue

        filepath = create_telegram_task(update, matched, vault_path)
        seen.add(msg_hash)
        save_to_telegram_ledger(ledger_path, msg_hash)

        sender = msg.get("from", {}).get("first_name", "Unknown")
        logger.log(
            "telegram_message_detected",
            filepath.name,
            "success",
            details={
                "sender": sender,
                "keywords": matched,
                "chat_type": msg.get("chat", {}).get("type", ""),
            },
        )
        print(f"  [TASK] {filepath.name} (keywords: {matched})")
        created += 1

    return created


def start_telegram_watcher(
    vault_path: Path,
    interval: int = 30,
    one_shot: bool = False,
) -> None:
    """Start polling Telegram for new messages."""
    if not BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
        print("Steps:")
        print("  1. Message @BotFather on Telegram")
        print("  2. Create a new bot with /newbot")
        print("  3. Copy the token")
        print("  4. Add TELEGRAM_BOT_TOKEN=your_token to .env")
        sys.exit(1)

    logger = AuditLogger(vault_path)
    ledger_path = vault_path / "Logs" / ".telegram_ledger.txt"
    seen = load_telegram_ledger(ledger_path)

    bot = get_bot_info()
    bot_name = bot.get("username", "unknown") if bot else "unknown"

    print("=== Telegram Watcher ===")
    print(f"Bot: @{bot_name}")
    print(f"Vault: {vault_path}")
    print(f"Interval: {interval}s")
    print(f"Keywords: {PRIORITY_KEYWORDS}")
    print(f"Ledger: {len(seen)} seen")
    if one_shot:
        print("Mode: one-shot check")
    else:
        print("Press Ctrl+C to stop.\n")

    logger.log("telegram_watcher_started", "system", "success",
               details={"bot": bot_name, "vault": str(vault_path)})

    offset = None

    if one_shot:
        updates = get_updates(offset=offset, timeout=5)
        count = process_updates(updates, vault_path, logger, ledger_path, seen)
        print(f"\nChecked {len(updates)} updates, created {count} tasks.")
        return

    try:
        while True:
            updates = get_updates(offset=offset, timeout=10)
            if updates:
                offset = max(u["update_id"] for u in updates) + 1
                process_updates(updates, vault_path, logger, ledger_path, seen)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopping Telegram watcher...")
    finally:
        logger.log("telegram_watcher_stopped", "system", "success")
        print("Telegram watcher stopped.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Telegram Bot message watcher")
    parser.add_argument("--check", action="store_true", help="One-shot check")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="Poll interval seconds")
    parser.add_argument("--vault-path", default=None)
    args = parser.parse_args()

    vault = Path(args.vault_path or os.getenv("VAULT_PATH", str(Path(__file__).parent.parent)))
    start_telegram_watcher(vault, interval=args.interval, one_shot=args.check)


if __name__ == "__main__":
    main()
