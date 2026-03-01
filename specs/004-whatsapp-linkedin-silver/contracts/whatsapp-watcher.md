# Contract: WhatsApp Watcher (`whatsapp_watcher.py`)

**Module**: `scripts/whatsapp_watcher.py`
**Date**: 2026-02-22

## Public Interface

### Functions

#### `load_whatsapp_ledger(path: Path) -> set[str]`
Load deduplication ledger from disk.
- **Input**: Path to ledger file (`Logs/.whatsapp_ledger.txt`)
- **Output**: Set of message hash strings
- **Errors**: Returns empty set if file doesn't exist

#### `save_to_whatsapp_ledger(path: Path, message_hash: str) -> None`
Append a message hash to the ledger file.
- **Input**: Path to ledger file, hash string
- **Output**: None (side effect: appends line to file)
- **Errors**: Raises `OSError` if file not writable

#### `compute_message_hash(sender: str, timestamp: str, text: str) -> str`
Generate a deduplication hash for a message.
- **Input**: Sender name, ISO timestamp, message text
- **Output**: SHA-256 hex digest of `f"{sender}|{timestamp}|{text[:50]}"`

#### `match_keywords(text: str, keywords: list[str] | None = None) -> list[str]`
Find priority keywords in message text (case-insensitive).
- **Input**: Message text, optional keyword list (default: `PRIORITY_KEYWORDS`)
- **Output**: List of matched keywords (empty if none)
- **Default keywords**: `["urgent", "invoice", "payment", "help", "deadline", "asap"]`

#### `create_whatsapp_task(message_data: dict, vault_path: Path) -> Path`
Create a task file in `Needs_Action/` from parsed message data.
- **Input**: Dict with keys `sender`, `text`, `timestamp`, `chat_type`, `group_name` (optional), `matched_keywords`
- **Output**: Path to created file
- **Side effects**: Writes file, appends to ledger, logs `whatsapp_task_created`
- **File format**: YAML frontmatter + markdown body (see data-model.md)

#### `check_session_valid(page: Page) -> bool`
Verify WhatsApp Web session is still authenticated.
- **Input**: Playwright Page object
- **Output**: `True` if chat list is visible, `False` if QR code page shown
- **Errors**: Returns `False` on timeout

#### `scrape_unread_messages(page: Page) -> list[dict]`
Extract unread messages from WhatsApp Web DOM.
- **Input**: Playwright Page object (authenticated)
- **Output**: List of dicts with keys: `sender`, `text`, `timestamp`, `chat_type`, `group_name`
- **Errors**: Returns empty list if scraping fails, logs warning

#### `start_whatsapp_watcher(vault_path: Path, setup: bool = False, check: bool = False, interval: float = 30.0) -> None`
Main entry point — launches browser and polling loop.
- **Input**: Vault path, setup mode flag, check mode flag, poll interval
- **Output**: None (runs indefinitely until Ctrl+C)
- **Modes**:
  - `setup=True`: Opens visible browser for QR code scanning, exits after auth
  - `check=True`: Scrapes once, prints results, exits
  - Default: Headless polling loop

### Constants

```python
PRIORITY_KEYWORDS: list[str] = ["urgent", "invoice", "payment", "help", "deadline", "asap"]

SELECTORS: dict[str, str] = {
    "chat_list": '...',
    "unread_chat": '...',
    "chat_item": '...',
    "sender_name": '...',
    "message_text": '...',
    "timestamp": '...',
    "qr_code": '...',
}
```

### CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--vault-path` | str | `$VAULT_PATH` or parent dir | Vault root directory |
| `--setup` | flag | False | Run in setup mode (visible browser for QR) |
| `--check` | flag | False | One-shot check, print results, exit |
| `--interval` | float | 30.0 | Seconds between polls (env: `WHATSAPP_POLL_INTERVAL`) |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WHATSAPP_POLL_INTERVAL` | `30` | Poll interval in seconds |
| `WHATSAPP_SESSION_DIR` | `~/.ai_employee/whatsapp_session` | Browser session storage |
| `WHATSAPP_KEYWORDS` | `urgent,invoice,payment,help,deadline,asap` | Comma-separated keywords |

### Audit Log Events

| Action | Input Ref | Outcome | Details |
|--------|-----------|---------|---------|
| `whatsapp_watcher_started` | `system` | success | `{mode, interval}` |
| `whatsapp_watcher_stopped` | `system` | success | `{reason}` |
| `whatsapp_message_detected` | sender name | success | `{keywords, chat_type}` |
| `whatsapp_task_created` | filename | success | `{sender, priority}` |
| `whatsapp_session_expired` | `system` | error | `{error: "Session expired"}` |
| `whatsapp_scrape_error` | `system` | error | `{error: message}` |
| `whatsapp_poll_cycle` | `system` | success | `{messages_found, tasks_created}` |

### Dependencies

- `playwright` (async browser automation)
- `audit_logger.AuditLogger` (internal)
- `python-dotenv` (env loading)
- `hashlib` (stdlib — dedup hashing)
- `pathlib`, `argparse`, `re`, `datetime`, `time` (stdlib)
