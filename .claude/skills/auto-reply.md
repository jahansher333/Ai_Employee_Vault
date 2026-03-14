# Auto Email Reply Skill

## Purpose
Generate email reply drafts using templates. All replies go to Pending_Approval/ for human review before sending.

## When to Use
- User asks to "reply to emails" or "generate email responses"
- Batch processing incoming emails that need standard replies
- Setting up auto-acknowledgment for common email types

## IMPORTANT: Human Approval Required
Replies are NEVER auto-sent. Flow:
1. AI generates draft -> Pending_Approval/
2. Human reviews and approves
3. Approved replies sent via Gmail API

## Commands
```bash
# Generate reply drafts for unprocessed emails
python scripts/auto_reply.py --draft

# List available templates
python scripts/auto_reply.py --templates

# Send approved replies via Gmail
python scripts/auto_reply.py --send
```

## Templates
| Template | Use Case |
|----------|----------|
| `acknowledgment` | General "thank you, will respond in 24h" |
| `invoice_received` | Invoice/payment emails |
| `meeting_confirm` | Meeting invitations |
| `out_of_office` | OOO auto-response |
| `custom` | User-provided text |

## Auto-Detection
The system detects reply type from email keywords:
- Invoice/bill/payment -> `invoice_received`
- Meeting/calendar/invite -> `meeting_confirm`
- Default -> `acknowledgment`

## Configuration
Uses same Gmail OAuth as `gmail_watcher.py`:
- `GMAIL_CREDENTIALS_PATH`, `GMAIL_TOKEN_PATH` in `.env`

## Script
`scripts/auto_reply.py`
