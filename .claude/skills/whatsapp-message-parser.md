# WhatsAppMessageParserSkill

## Description

Monitors WhatsApp Web for incoming messages and creates task files for urgent items. The watcher detects messages containing priority keywords (urgent, invoice, payment, help, deadline, ASAP) and generates structured Markdown task files in `Needs_Action/` for AI Employee processing.

## When to Use

- When the user wants to monitor WhatsApp for business-critical messages
- When setting up the WhatsApp watcher for the first time (QR code auth)
- When checking current unread WhatsApp messages

## Prerequisites

- Python 3.10+ with `playwright` and `python-dotenv` installed
- Chromium browser installed via `playwright install chromium`
- WhatsApp account linked to a phone with active internet

## Input

- **Setup mode**: No input needed — opens browser for QR code scanning
- **Check mode**: No input — displays current unread messages
- **Poll mode**: No input — runs continuously in the background

## Output

Task files in `Needs_Action/` with format `WHATSAPP_{HHMMSS}_{sender}.md`:
- YAML frontmatter: type, from, message, date, priority, matched_keywords, chat_type, status
- Markdown body: sender info, message text, pending action plan

## Usage

```bash
# First-time setup (scan QR code)
python scripts/whatsapp_watcher.py --setup

# One-shot check
python scripts/whatsapp_watcher.py --check

# Continuous monitoring (default 30s interval)
python scripts/whatsapp_watcher.py

# Custom interval
python scripts/whatsapp_watcher.py --interval 15
```

## Configuration

Environment variables in `.env`:
- `WHATSAPP_POLL_INTERVAL` — seconds between polls (default: 30)
- `WHATSAPP_SESSION_DIR` — browser session path (default: ~/.ai_employee/whatsapp_session)
- `WHATSAPP_KEYWORDS` — comma-separated priority keywords

## Integration

- Creates files in `Needs_Action/` → picked up by file watcher → processed by `process_inbox.py`
- Deduplicates via `Logs/.whatsapp_ledger.txt`
- All events logged to `Logs/YYYY-MM-DD.audit.jsonl`
- Dashboard updated with WhatsApp message tasks

## Script

`scripts/whatsapp_watcher.py`
