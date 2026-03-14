# MCP Email Server Skill

## Purpose
MCP (Model Context Protocol) server that exposes Gmail operations as tools callable from Claude Code. Wraps gmail_watcher.py with no logic duplication.

## When to Use
- When Claude Code needs to fetch, send, or reply to emails via MCP
- When creating email-based tasks from within Claude Code
- User asks to "check email via MCP" or "send email through Claude"

## Commands
```bash
# Start MCP server (stdio transport)
python scripts/mcp_email_server.py
```

Add to `.claude/mcp.json` for auto-discovery by Claude Code.

## Configuration
Set in `.env`:
- `VAULT_PATH` — Path to vault root
- `GMAIL_CREDENTIALS_PATH` — OAuth credentials.json
- `GMAIL_TOKEN_PATH` — Saved token.json

## MCP Tools
| Tool | Description |
|------|-------------|
| `fetch_unread_emails` | Fetch unread emails from Gmail (max_results param) |
| `send_email` | Send a new email (to, subject, body_text) |
| `reply_to_email` | Reply to an existing thread (message_id, body_text) |
| `mark_email_read` | Mark a message as read by Gmail ID |
| `create_email_task` | Create a task file in Needs_Action/ from email data |

## Response Format
All tools return a dict with `success: bool` and either the result data or `error: str`.

## Integration
- Lazy-initializes Gmail API service on first tool call
- Delegates all logic to `gmail_watcher.py` functions
- Task creation logged via AuditLogger
- Server name: `email`

## Script
`scripts/mcp_email_server.py`
