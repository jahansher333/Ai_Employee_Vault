# Research: Silver Tier - Gmail Watcher + Data Analytics

**Date**: 2026-02-21
**Feature**: 003-silver-gmail-analytics

## Decision 1: Gmail API Authentication Flow

**Decision**: Use OAuth 2.0 with installed application (desktop) flow via `google-auth-oauthlib`.

**Rationale**: The Gmail API requires OAuth 2.0 for user data access. The "installed app" flow is designed for local desktop applications — it opens a browser for consent, then stores a refresh token locally. This matches our local-first constraint.

**Key Details**:
- Scopes needed: `gmail.readonly` (list/read emails) + `gmail.modify` (mark as read)
- `credentials.json` — downloaded from Google Cloud Console (OAuth 2.0 Client ID for Desktop)
- `token.json` — auto-generated after first OAuth consent, contains refresh token
- On subsequent runs, the refresh token is used automatically (no browser needed)
- Both files go in vault root, both in `.gitignore`

**Alternatives Considered**:
- Service account: Not suitable for user Gmail access (requires domain-wide delegation)
- API key: Not supported for Gmail user data
- App passwords: Deprecated by Google for most accounts

## Decision 2: Gmail Polling Strategy

**Decision**: Poll using `users.messages.list` with `q=is:unread` query, default interval 60 seconds.

**Rationale**: The Gmail API does not support push notifications without a public webhook endpoint. Polling is the only option for local-first apps. 60-second interval balances responsiveness with API quota (250 quota units per list call, daily limit 1 billion units).

**Key Details**:
- `service.users().messages().list(userId='me', q='is:unread')` returns message IDs
- For each message ID, `service.users().messages().get(userId='me', id=msg_id)` gets full content
- After processing, `service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']})` marks as read
- Rate limit: 250 units/user/second. List = 5 units, Get = 5 units, Modify = 5 units
- At 60s intervals processing 10 emails/cycle: ~150 units/minute, well within limits

**Alternatives Considered**:
- Gmail Push (Pub/Sub): Requires public HTTPS endpoint and Google Cloud Pub/Sub subscription — violates local-first constraint
- IMAP: Lower-level, harder to filter, no built-in label support
- historyId tracking: More efficient for incremental sync but adds complexity; ledger-based dedup is simpler for MVP

## Decision 3: Email Deduplication

**Decision**: Track processed email IDs in a plain text ledger file at `Logs/.gmail_ledger.txt`, one message ID per line.

**Rationale**: Consistent with the Bronze Tier file watcher's ledger pattern (`Logs/.watcher_ledger.txt`). Simple, reliable, survives restarts. Combined with marking as read, provides double protection against duplicates.

**Key Details**:
- Before processing an email, check if its message ID is in the ledger set
- After successful processing (file created + marked as read), append ID to ledger
- Load ledger into a Python `set()` on startup for O(1) lookups
- Same pattern as `watcher.py` `load_ledger()` / `save_to_ledger()` functions

**Alternatives Considered**:
- SQLite database: Overkill for a simple ID set
- Gmail labels: Would work but adds external state mutation complexity
- In-memory only: Lost on restart, would cause duplicates

## Decision 4: Email Task File Format

**Decision**: Create files named `EMAIL_{timestamp}_{sanitized_subject}.md` with standard YAML frontmatter.

**Rationale**: Naming convention makes email-sourced tasks easily identifiable. Timestamp prefix ensures uniqueness. Sanitized subject gives human-readable filenames.

**Key Details**:
```yaml
---
type: email
from: sender@example.com
subject: "Original Subject Line"
date: 2026-02-21T10:30:00Z
priority: high
gmail_id: 18d4a5b2c3e4f
status: new
---

# Original Subject Line

**From**: sender@example.com
**Date**: 2026-02-21 10:30 UTC

## Email Snippet

First 500 characters of the email body...
```

**Alternatives Considered**:
- JSON format: Not compatible with existing Markdown-based pipeline
- Full email body: Could be very large; snippet (500 chars) is sufficient for task creation

## Decision 5: CSV Financial Data Format

**Decision**: Use pandas to read CSV with flexible column mapping. Expect `date`, `description`, `amount`, `category` columns. Support common alternatives via column name matching.

**Rationale**: pandas handles CSV parsing, missing values, date parsing, and aggregation natively. Flexible column mapping accommodates different CSV exports from banks/accounting tools.

**Key Details**:
- Column mapping priority: exact match first, then case-insensitive, then common synonyms
  - amount: `amount`, `value`, `total`, `sum`; if both `debit` and `credit` columns exist, compute amount = credit - debit
  - date: `date`, `transaction_date`, `trans_date`, `posted_date`
  - category: `category`, `type`, `class`, `department`
  - description: `description`, `memo`, `note`, `details`, `payee`
- Positive amounts = revenue/income, negative = expenses
- Missing dates: group under "Unknown" month
- Missing categories: group under "Uncategorized"

**Alternatives Considered**:
- Strict column names: Too rigid for real-world CSV exports
- AI-based column detection: Over-engineered for Silver Tier
- Manual column mapping config: Good for future but unnecessary for MVP

## Decision 6: Anomaly Detection Method

**Decision**: Flag transactions where |amount| > 2x the category average as anomalies.

**Rationale**: Simple, deterministic, easy to explain to users. Matches the spec requirement exactly. More sophisticated methods (z-score, IQR) can be added later.

**Key Details**:
- For each category, compute mean of |amount|
- Any transaction with |amount| > 2 * category_mean is flagged
- Anomalies presented as a separate alerts table in the analytics section
- If a category has only 1 transaction, skip anomaly check for that category

**Alternatives Considered**:
- Z-score (>2 std deviations): Better statistically but harder to explain
- IQR method: More robust to outliers but more complex
- Fixed threshold: Not adaptive to different spending categories

## Decision 7: Dashboard Analytics Section

**Decision**: Use `<!-- START_ANALYTICS -->` / `<!-- END_ANALYTICS -->` markers in Dashboard.md, replacing content between markers on each update.

**Rationale**: Consistent with Bronze Tier's `<!-- START_PENDING_TASKS -->` / `<!-- END_PENDING_TASKS -->` pattern. Replace (not append) ensures only the latest analytics are shown.

**Key Details**:
- Section includes: Revenue/Expense summary table, Monthly breakdown, Top 5 expenses, Anomaly alerts
- If no data, show "No financial data available"
- Markers must be added to Dashboard.md template

**Alternatives Considered**:
- Separate analytics file: Loses single-pane dashboard benefit
- Append mode: Would create unbounded growth
- Obsidian embed: Adds unnecessary complexity
