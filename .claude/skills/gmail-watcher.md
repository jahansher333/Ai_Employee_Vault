# Gmail Watcher Skill

## Purpose
Poll Gmail for unread emails via OAuth, create task files in Needs_Action/, mark emails as read, and support sending/replying to emails.

## When to Use
- When you need to monitor Gmail for incoming emails
- When creating tasks from email messages
- When replying to or sending emails programmatically
- User asks to "check email", "process inbox", or "reply to email"

## Commands
```bash
# Start polling loop (default 60s interval)
python scripts/gmail_watcher.py

# Custom vault path and interval
python scripts/gmail_watcher.py --vault-path /path/to/vault --interval 30

# Authenticate only (first-time OAuth setup)
python scripts/gmail_watcher.py --auth-only

# Check unread emails without processing
python scripts/gmail_watcher.py --check

# Reply to an email by Gmail ID
python scripts/gmail_watcher.py --reply GMAIL_ID "Reply message here"

# Send a new email
python scripts/gmail_watcher.py --send to@email.com "Subject" "Body text"
```

## Configuration
Set in `.env`:
- `GMAIL_CREDENTIALS_PATH` — Path to OAuth credentials.json (required)
- `GMAIL_TOKEN_PATH` — Path to saved token.json (default: token.json)
- `GMAIL_POLL_INTERVAL` — Polling interval in seconds (default: 60)
- `GMAIL_MAX_RESULTS` — Max emails per poll (default: 10)
- `VAULT_PATH` — Path to vault root

Requires Google API libraries: `pip install google-api-python-client google-auth-oauthlib`

## Key Functions
| Function | Purpose |
|----------|---------|
| `build_gmail_service` | OAuth authentication, token refresh |
| `fetch_unread_emails` | Poll for unread messages |
| `mark_as_read` | Remove UNREAD label from a message |
| `reply_to_email` | Compose and send a threaded reply |
| `send_email` | Send a new email |
| `create_email_task` | Create EMAIL_*.md task in Needs_Action/ |
| `move_email_to_done` | Move processed email task to Done/ |

## Integration
- Creates `EMAIL_{HHMMSS}_{subject}.md` files in `Needs_Action/`
- Deduplication via ledger at `Logs/.gmail_ledger.txt`
- All events logged to `Logs/*.audit.jsonl` via AuditLogger
- After reply, moves task to Done/ and updates Dashboard

## Script
`scripts/gmail_watcher.py`
