"""WhatsApp Web watcher — monitors for urgent messages via Playwright.

Polls WhatsApp Web for unread messages containing priority keywords,
creates task files in Needs_Action/ for the AI Employee pipeline.

Usage:
    python scripts/whatsapp_watcher.py --setup          # First-time QR auth
    python scripts/whatsapp_watcher.py --check          # One-shot scan
    python scripts/whatsapp_watcher.py                  # Continuous polling
    python scripts/whatsapp_watcher.py --interval 15    # Custom interval
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

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRIORITY_KEYWORDS: list[str] = [
    kw.strip().lower()
    for kw in os.getenv(
        "WHATSAPP_KEYWORDS", "urgent,invoice,payment,help,deadline,asap"
    ).split(",")
]

WHATSAPP_WEB_URL = "https://web.whatsapp.com"

# Selectors are externalised here so they can be updated easily if WhatsApp
# changes their DOM.  Each value is a CSS selector string.
SELECTORS: dict[str, str] = {
    "qr_canvas": 'canvas[aria-label="Scan this QR code to link a device!"]',
    "qr_container": "div._akau",                       # QR code wrapper
    "search_bar": 'div[contenteditable="true"][data-tab="3"]',
    "chat_list": '#pane-side',
    "unread_badge": 'span[aria-label*="unread message"]',
    "chat_row": 'div[role="listitem"]',
    "chat_title": 'span[dir="auto"][title]',
    "last_message": 'span[dir="ltr"].ggj6brxn',        # last message preview
    "message_time": 'div._ak8i',                        # timestamp element
    "active_chat_messages": 'div.message-in',           # incoming messages
    "message_text": 'span.selectable-text',
    "message_data_attr": 'div[data-pre-plain-text]',
}

DEFAULT_SESSION_DIR = os.path.expanduser(
    os.getenv("WHATSAPP_SESSION_DIR", "~/.ai_employee/whatsapp_session")
)


# ---------------------------------------------------------------------------
# Ledger helpers (same pattern as gmail_watcher)
# ---------------------------------------------------------------------------

def load_whatsapp_ledger(path: Path) -> set[str]:
    """Load processed-message hashes from the ledger file."""
    if not path.exists():
        return set()
    return set(path.read_text(encoding="utf-8").splitlines())


def save_to_whatsapp_ledger(path: Path, message_hash: str) -> None:
    """Append *message_hash* to the ledger (one hash per line)."""
    with path.open("a", encoding="utf-8") as fh:
        fh.write(message_hash + "\n")


def compute_message_hash(sender: str, timestamp: str, text: str) -> str:
    """SHA-256 dedup key: ``sender|timestamp|text[:50]``."""
    raw = f"{sender}|{timestamp}|{text[:50]}"
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Keyword matching
# ---------------------------------------------------------------------------

def match_keywords(text: str, keywords: list[str] | None = None) -> list[str]:
    """Return a list of matched priority keywords (case-insensitive)."""
    kws = keywords or PRIORITY_KEYWORDS
    lower = text.lower()
    return [kw for kw in kws if kw in lower]


# ---------------------------------------------------------------------------
# Sanitisation helpers
# ---------------------------------------------------------------------------

def _sanitize(name: str, max_len: int = 50) -> str:
    """Replace non-alphanumeric chars with dashes, truncate."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-")
    return slug[:max_len]


# ---------------------------------------------------------------------------
# Task-file creation
# ---------------------------------------------------------------------------

def create_whatsapp_task(
    message_data: dict,
    vault_path: Path,
    logger: AuditLogger | None = None,
) -> Path:
    """Create a ``WHATSAPP_*.md`` task file in ``Needs_Action/``.

    *message_data* must contain keys:
        sender, text, timestamp, chat_type,
        (optional) group_name, matched_keywords
    """
    sender = message_data["sender"]
    text = message_data["text"]
    ts = message_data.get("timestamp", datetime.now(timezone.utc).isoformat())
    chat_type = message_data.get("chat_type", "individual")
    group_name = message_data.get("group_name", "")
    matched = message_data.get("matched_keywords", [])
    priority = "high" if matched else "medium"

    time_part = datetime.now(timezone.utc).strftime("%H%M%S")
    safe_sender = _sanitize(sender)
    filename = f"WHATSAPP_{time_part}_{safe_sender}.md"

    needs = vault_path / "Needs_Action"
    needs.mkdir(parents=True, exist_ok=True)
    dest = needs / filename

    # Avoid overwriting
    if dest.exists():
        filename = f"WHATSAPP_{time_part}_{safe_sender}-{int(time.time()) % 10000}.md"
        dest = needs / filename

    keywords_yaml = ", ".join(f'"{k}"' for k in matched)
    group_line = f'\ngroup_name: "{group_name}"' if group_name else ""

    content = (
        f'---\n'
        f'type: whatsapp\n'
        f'from: "{sender}"\n'
        f'message: "{text[:200]}"\n'
        f'date: "{ts}"\n'
        f'priority: {priority}\n'
        f'matched_keywords: [{keywords_yaml}]\n'
        f'chat_type: {chat_type}{group_line}\n'
        f'status: new\n'
        f'---\n\n'
        f'# WhatsApp Message from {sender}\n\n'
        f'**From**: {sender}\n'
        f'**Time**: {ts}\n'
        f'**Chat**: {chat_type.title()}'
        f'{f" ({group_name})" if group_name else ""}\n'
        f'**Priority**: {priority.upper()}'
        f'{f" (matched: {", ".join(matched)})" if matched else ""}\n\n'
        f'## Message\n\n{text}\n\n'
        f'## Action Plan\n\n'
        f'*Pending processing by AI Employee*\n'
    )

    dest.write_text(content, encoding="utf-8")

    if logger:
        logger.log(
            "whatsapp_task_created", filename, "success",
            details={"sender": sender, "priority": priority,
                     "keywords": matched, "chat_type": chat_type},
        )
    return dest


# ---------------------------------------------------------------------------
# Browser / Playwright helpers
# ---------------------------------------------------------------------------

def check_session_valid(page) -> bool:
    """Return ``True`` if WhatsApp Web shows the chat list (authenticated)."""
    try:
        page.wait_for_selector(SELECTORS["chat_list"], timeout=45_000)
        return True
    except Exception:
        return False


def _wait_for_qr_scan(page, timeout_s: int = 120) -> bool:
    """Wait for the user to scan the QR code.  Returns True on success."""
    print("Waiting for QR code scan ...")
    try:
        page.wait_for_selector(SELECTORS["chat_list"], timeout=timeout_s * 1000)
        print("Authenticated successfully!")
        return True
    except Exception:
        print("QR scan timed out.")
        return False


def scrape_unread_messages(page) -> list[dict]:
    """Scrape unread chats from WhatsApp Web's sidebar.

    Returns a list of dicts with keys: sender, text, timestamp, chat_type, group_name.
    """
    messages: list[dict] = []
    try:
        # Find chat rows with unread badges
        unread_badges = page.query_selector_all(SELECTORS["unread_badge"])
        if not unread_badges:
            return messages

        for badge in unread_badges:
            try:
                # Navigate up to the chat row
                chat_row = badge.evaluate_handle(
                    "el => el.closest('[role=\"listitem\"]') || el.closest('[data-testid=\"cell-frame-container\"]')"
                )
                if not chat_row:
                    continue

                # Extract sender / chat title
                title_el = chat_row.as_element().query_selector(SELECTORS["chat_title"])
                sender = title_el.get_attribute("title") if title_el else "Unknown"

                # Extract last message preview
                msg_el = chat_row.as_element().query_selector("span[dir='ltr']")
                text = msg_el.inner_text() if msg_el else ""

                # Determine chat type (groups usually have ':' in preview)
                chat_type = "group" if ": " in text else "individual"
                group_name = sender if chat_type == "group" else ""

                # Use current time as timestamp (DOM doesn't always expose per-message times easily)
                ts = datetime.now(timezone.utc).isoformat()

                messages.append({
                    "sender": sender,
                    "text": text,
                    "timestamp": ts,
                    "chat_type": chat_type,
                    "group_name": group_name,
                })
            except Exception:
                continue

    except Exception:
        pass

    return messages


# ---------------------------------------------------------------------------
# Main watcher loop
# ---------------------------------------------------------------------------

def start_whatsapp_watcher(
    vault_path: Path,
    setup: bool = False,
    check: bool = False,
    interval: float = 30.0,
) -> None:
    """Launch the WhatsApp Web watcher.

    Modes:
        setup  — visible browser, wait for QR scan, save session, exit
        check  — headless, scrape once, print results, exit
        (default) — headless polling loop
    """
    # Lazy import so tests that mock Playwright don't need it installed.
    from playwright.sync_api import sync_playwright

    session_dir = os.path.expanduser(
        os.getenv("WHATSAPP_SESSION_DIR", DEFAULT_SESSION_DIR)
    )
    Path(session_dir).mkdir(parents=True, exist_ok=True)

    logger = AuditLogger(vault_path)
    ledger_path = vault_path / "Logs" / ".whatsapp_ledger.txt"
    ledger = load_whatsapp_ledger(ledger_path)

    # check runs visible by default; set WHATSAPP_HEADLESS=1 to override
    force_headless = os.getenv("WHATSAPP_HEADLESS", "").strip() == "1"
    headless = False if setup else (force_headless if check else True)
    mode_label = "setup" if setup else ("check" if check else "poll")

    logger.log(
        "whatsapp_watcher_started", "system", "success",
        details={"mode": mode_label, "interval": interval},
    )
    print(f"WhatsApp Watcher starting (mode={mode_label}, interval={interval}s)")

    with sync_playwright() as pw:
        browser_context = pw.chromium.launch_persistent_context(
            user_data_dir=session_dir,
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = browser_context.pages[0] if browser_context.pages else browser_context.new_page()
        page.goto(WHATSAPP_WEB_URL, wait_until="domcontentloaded")
        # Allow extra time for WhatsApp Web JS to initialise
        page.wait_for_load_state("networkidle")

        # ---- Setup mode ----
        if setup:
            if check_session_valid(page):
                print("Session already valid — no QR scan needed.")
            else:
                if not _wait_for_qr_scan(page, timeout_s=120):
                    browser_context.close()
                    logger.log("whatsapp_watcher_stopped", "system", "error",
                               error="QR scan timed out")
                    return
            # Give time for session storage to flush
            time.sleep(3)
            browser_context.close()
            logger.log("whatsapp_watcher_stopped", "system", "success",
                       details={"reason": "setup complete"})
            print(f"Session saved to {session_dir}")
            return

        # ---- Verify session ----
        if not check_session_valid(page):
            # Debug: show page title and URL for troubleshooting
            print(f"  [DEBUG] Page title: {page.title()}")
            print(f"  [DEBUG] Page URL: {page.url}")
            logger.log("whatsapp_session_expired", "system", "error",
                       error="Session expired — run with --setup to re-authenticate")
            print("ERROR: Session expired. Run with --setup to scan QR code.")
            browser_context.close()
            return

        print("Session valid. Monitoring for messages ...")

        # ---- Check mode (one-shot) ----
        if check:
            msgs = scrape_unread_messages(page)
            print(f"Found {len(msgs)} unread chat(s):")
            for m in msgs:
                kws = match_keywords(m["text"])
                flag = " [KEYWORD MATCH]" if kws else ""
                print(f"  - {m['sender']}: {m['text'][:80]}{flag}")
            browser_context.close()
            logger.log("whatsapp_watcher_stopped", "system", "success",
                       details={"reason": "check complete", "found": len(msgs)})
            return

        # ---- Polling loop ----
        try:
            while True:
                try:
                    msgs = scrape_unread_messages(page)
                    tasks_created = 0

                    for m in msgs:
                        matched = match_keywords(m["text"])
                        if not matched:
                            continue

                        msg_hash = compute_message_hash(
                            m["sender"], m["timestamp"], m["text"]
                        )
                        if msg_hash in ledger:
                            continue

                        m["matched_keywords"] = matched
                        create_whatsapp_task(m, vault_path, logger)
                        ledger.add(msg_hash)
                        save_to_whatsapp_ledger(ledger_path, msg_hash)
                        tasks_created += 1
                        print(f"  [NEW] {m['sender']}: {m['text'][:60]} (keywords: {matched})")

                    logger.log(
                        "whatsapp_poll_cycle", "system", "success",
                        details={"messages_found": len(msgs),
                                 "tasks_created": tasks_created},
                    )

                except Exception as exc:
                    logger.log("whatsapp_scrape_error", "system", "error",
                               error=str(exc))
                    print(f"  [SCRAPE ERROR] {exc}")

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\nStopping WhatsApp watcher ...")
        finally:
            browser_context.close()
            logger.log("whatsapp_watcher_stopped", "system", "success",
                       details={"reason": "user_interrupt"})


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="WhatsApp Web message watcher")
    parser.add_argument("--vault-path", default=None,
                        help="Path to vault root")
    parser.add_argument("--setup", action="store_true",
                        help="Open browser for QR code authentication")
    parser.add_argument("--check", action="store_true",
                        help="One-shot: scrape and print, then exit")
    parser.add_argument("--interval", type=float, default=None,
                        help="Seconds between polls (default: 30)")
    args = parser.parse_args()

    vault = Path(args.vault_path or os.getenv("VAULT_PATH",
                 str(Path(__file__).parent.parent)))
    interval = args.interval or float(os.getenv("WHATSAPP_POLL_INTERVAL", "30"))

    start_whatsapp_watcher(vault, setup=args.setup, check=args.check,
                           interval=interval)


if __name__ == "__main__":
    main()
