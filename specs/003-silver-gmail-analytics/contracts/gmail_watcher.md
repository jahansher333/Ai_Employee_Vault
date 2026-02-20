# Contract: Gmail Watcher

**Module**: `scripts/gmail_watcher.py`
**Purpose**: Poll Gmail for unread emails and create task files in Needs_Action/

## Public Interface

### `build_gmail_service(credentials_path, token_path) -> Resource`
- **Input**: Path to credentials.json, path to token.json
- **Output**: Authenticated Gmail API service object
- **Errors**: `FileNotFoundError` if credentials.json missing, `AuthenticationError` if token invalid/expired
- **Side effects**: Creates/updates token.json on first auth or token refresh

### `fetch_unread_emails(service, max_results=10) -> list[dict]`
- **Input**: Gmail service, optional max results per poll
- **Output**: List of dicts with keys: `id`, `from`, `subject`, `snippet`, `date`, `is_important`
- **Errors**: `HttpError` on API failure (logged, returns empty list)
- **Side effects**: None (read-only)

### `create_email_task(email_data, vault_path) -> Path`
- **Input**: Email dict from `fetch_unread_emails`, vault root path
- **Output**: Path to created .md file in Needs_Action/
- **Errors**: `IOError` on write failure
- **Side effects**: Creates file `EMAIL_{HHMMSS}_{subject}.md`

### `mark_as_read(service, message_id) -> bool`
- **Input**: Gmail service, message ID
- **Output**: True if successful, False if failed
- **Errors**: Logs error on failure, does not raise
- **Side effects**: Removes UNREAD label from email in Gmail

### `start_gmail_watcher(vault_path, interval=60) -> None`
- **Input**: Vault root path, poll interval in seconds
- **Output**: None (runs indefinitely until KeyboardInterrupt)
- **Errors**: Exits with error message if credentials missing
- **Side effects**: Creates files, modifies Gmail labels, writes ledger and audit log

## Ledger Functions

### `load_gmail_ledger(path) -> set[str]`
- **Input**: Path to ledger file
- **Output**: Set of processed message IDs

### `save_to_gmail_ledger(path, message_id) -> None`
- **Input**: Path to ledger file, message ID to append
- **Side effects**: Appends one line to ledger file

## Configuration

| Variable | Source | Default | Description |
|----------|--------|---------|-------------|
| GMAIL_CREDENTIALS_PATH | .env | credentials.json | Path to OAuth client credentials |
| GMAIL_TOKEN_PATH | .env | token.json | Path to stored OAuth token |
| GMAIL_POLL_INTERVAL | .env | 60 | Seconds between polls |
| GMAIL_MAX_RESULTS | .env | 10 | Max emails per poll cycle |

## Audit Events

| Action | Outcome | Details |
|--------|---------|---------|
| gmail_watcher_started | success | vault path, interval |
| gmail_connected | success | user email |
| gmail_poll | success | emails_found count |
| email_processed | success | from, subject, file created |
| email_processed | error | error message |
| gmail_auth_error | error | error message |
