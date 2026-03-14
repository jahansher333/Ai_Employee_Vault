# Telegram Watcher Skill

## Purpose
Monitor Telegram for incoming messages with priority keywords and create task files for AI Employee processing.

## When to Use
- User wants to monitor Telegram for business messages
- Setting up Telegram bot for the first time
- Checking unread Telegram messages

## Prerequisites
- Python 3.10+ with `requests` and `python-dotenv`
- Telegram Bot token from @BotFather

## Commands
```bash
# One-shot check
python scripts/telegram_watcher.py --check

# Continuous monitoring (default 30s)
python scripts/telegram_watcher.py

# Custom interval
python scripts/telegram_watcher.py --interval 15
```

## Configuration
Set in `.env`:
- `TELEGRAM_BOT_TOKEN` — Bot token from @BotFather (required)
- `TELEGRAM_POLL_INTERVAL` — Seconds between polls (default: 30)
- `TELEGRAM_KEYWORDS` — Comma-separated priority keywords

## Setup
1. Message @BotFather on Telegram
2. Send `/newbot` and follow prompts
3. Copy the bot token
4. Add `TELEGRAM_BOT_TOKEN=your_token` to `.env`
5. Message your bot to start receiving updates

## Integration
- Creates files in `Needs_Action/` with prefix `TELEGRAM_`
- Deduplicates via `Logs/.telegram_ledger.txt`
- All events logged to `Logs/*.audit.jsonl`
- Picked up by file watcher and process_inbox.py

## Script
`scripts/telegram_watcher.py`
