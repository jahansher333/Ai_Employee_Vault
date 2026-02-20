# Data Model: Silver Tier - Gmail Watcher + Data Analytics

**Date**: 2026-02-21
**Feature**: 003-silver-gmail-analytics

## Entities

### 1. EmailTask

A Markdown file created from a Gmail email, placed in `Needs_Action/`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | string | yes | Always "email" |
| from | string | yes | Sender email address |
| subject | string | yes | Email subject line (or "(No Subject)") |
| date | ISO 8601 datetime | yes | Email received timestamp |
| priority | enum: high, medium | yes | "high" if Gmail-important, else "medium" |
| gmail_id | string | yes | Gmail message ID for dedup |
| status | enum: new, planned, done | yes | Processing status (starts as "new") |

**Body content**: Markdown with sender info and first 500 characters of email body.

**Filename pattern**: `EMAIL_{HHMMSS}_{sanitized_subject}.md`

**Lifecycle**: new -> (processed by SimpleTaskReaderSkill) -> planned -> done

### 2. FinancialRecord

A single row from a CSV file in `Accounting/`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| date | date or null | no | Transaction date |
| description | string | yes | Transaction description/memo |
| amount | float | yes | Positive = revenue, negative = expense |
| category | string | no | Transaction category (default: "Uncategorized") |

**Source**: Parsed from CSV columns with flexible name matching.

**Validation rules**:
- Rows with no parseable amount are skipped (logged as warning)
- Empty description defaults to "(No description)"
- Invalid dates default to null (grouped under "Unknown" month)

### 3. AnalyticsSummary

Computed output from analyzing all FinancialRecords.

| Field | Type | Description |
|-------|------|-------------|
| total_revenue | float | Sum of all positive amounts |
| total_expenses | float | Sum of all negative amounts (absolute value) |
| net_income | float | total_revenue - total_expenses |
| monthly_breakdown | list[MonthSummary] | Per-month revenue/expense |
| top_expenses | list[FinancialRecord] | Top 5 expenses by absolute amount |
| anomalies | list[Anomaly] | Transactions flagged as anomalous |
| generated_at | ISO 8601 datetime | When analysis was performed |
| files_analyzed | list[string] | Source CSV filenames |

### 4. MonthSummary

| Field | Type | Description |
|-------|------|-------------|
| month | string | "YYYY-MM" format or "Unknown" |
| revenue | float | Sum of positive amounts for the month |
| expenses | float | Sum of negative amounts (absolute) for the month |
| net | float | revenue - expenses |
| transaction_count | int | Number of transactions in the month |

### 5. Anomaly

| Field | Type | Description |
|-------|------|-------------|
| date | date or null | Transaction date |
| description | string | Transaction description |
| amount | float | Transaction amount |
| category | string | Transaction category |
| category_avg | float | Average |amount| for this category |
| ratio | float | |amount| / category_avg (always > 2.0) |

### 6. GmailLedger

A plain text file tracking processed Gmail message IDs.

| Field | Type | Description |
|-------|------|-------------|
| message_ids | set[string] | One Gmail message ID per line |

**Location**: `Logs/.gmail_ledger.txt`
**Operations**: Load on startup (into set), append after each processed email.

## Relationships

```
Gmail Inbox --[poll]--> EmailTask --[file in Needs_Action/]--> SimpleTaskReaderSkill
                                                                     |
CSV files in Accounting/ --[read]--> FinancialRecord[] --[analyze]--> AnalyticsSummary
                                                                     |
                                                              Dashboard.md
                                                        (Pending Tasks + Analytics)
```

## State Transitions

### EmailTask Lifecycle
```
[Gmail Unread] --gmail_watcher--> [Needs_Action/EMAIL_*.md status:new]
                                        |
                              [SimpleTaskReaderSkill processes]
                                        |
                                  [status:planned]
                                        |
                              [User marks as done]
                                        |
                                  [Done/EMAIL_*.md status:done]
```

### Gmail Message States
```
[Unread in Inbox] --watcher reads--> [File created + marked as read] --ledger updated--> [Tracked]
```
