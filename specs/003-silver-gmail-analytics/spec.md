# Feature Specification: Silver Tier - Gmail Watcher + Data Analytics

**Feature Branch**: `003-silver-gmail-analytics`
**Created**: 2026-02-17
**Status**: Draft
**Input**: Silver Tier upgrade adding Gmail monitoring and CSV data analytics to existing Bronze Tier vault

## Overview

The AI Employee currently operates at Bronze Tier with a file system watcher that detects new tasks in `Needs_Action/` and processes them. Silver Tier upgrades the assistant to a **Functional Assistant** by adding two major capabilities:

1. **Gmail Watcher** - A second watcher that monitors a Gmail inbox for unread/important emails and converts them into actionable task files in `Needs_Action/`
2. **Data Analyzer Skill** - A new skill that reads financial data from CSV and Markdown files in `Accounting/`, performs analysis (revenue, expenses, anomalies), and updates the Dashboard with analytics summaries

Together these deliver the Silver Tier requirement of 2+ watchers and enhanced data processing.

## User Scenarios & Testing

### User Story 1 - Gmail Monitoring Creates Tasks (Priority: P1)

As a busy professional, I want my AI Employee to monitor my Gmail inbox so that important emails automatically become tasks in my vault without manual effort.

**Why this priority**: This is the core Silver Tier differentiator - adding a second watcher source. Without Gmail integration, the system remains Bronze Tier.

**Independent Test**: Can be fully tested by sending an email to the monitored Gmail account and verifying a corresponding `.md` task file appears in `Needs_Action/` within 2 minutes, containing sender, subject, snippet, and priority.

**Acceptance Scenarios**:

1. **Given** the Gmail watcher is running and connected, **When** a new unread email arrives in the inbox, **Then** a `.md` file is created in `Needs_Action/` with YAML frontmatter (type: email, from, subject, priority) and body containing the email snippet
2. **Given** an email is marked as important in Gmail, **When** the watcher processes it, **Then** the created task file has `priority: high`
3. **Given** a regular unread email arrives, **When** the watcher processes it, **Then** the created task file has `priority: medium`
4. **Given** the Gmail watcher processes an email, **When** the file is created, **Then** the email is marked as read in Gmail to prevent duplicate processing
5. **Given** the Gmail watcher loses connection, **When** connectivity is restored, **Then** processing resumes from where it left off without duplicating previously processed emails

---

### User Story 2 - Financial Data Analysis (Priority: P2)

As a business owner, I want my AI Employee to analyze financial data from CSV files so that I can see revenue, expenses, and anomalies summarized on my dashboard without manual spreadsheet work.

**Why this priority**: Data analytics is the second major Silver Tier capability, transforming the assistant from a task tracker into a functional analyst.

**Independent Test**: Can be fully tested by placing a CSV file with financial records in `Accounting/` and verifying the dashboard updates with a revenue/expense summary table and any detected anomalies.

**Acceptance Scenarios**:

1. **Given** a CSV file with columns for date, description, amount, and category exists in `Accounting/`, **When** the Data Analyzer runs, **Then** it produces a Markdown summary with total revenue, total expenses, and net income
2. **Given** financial data spanning multiple months, **When** the analyzer runs, **Then** it groups results by month and shows trends
3. **Given** a transaction amount exceeds 2x the category average, **When** the analyzer runs, **Then** it flags that transaction as an anomaly with an alert
4. **Given** a CSV file with missing or malformed data, **When** the analyzer runs, **Then** it skips invalid rows, logs warnings, and processes valid rows normally

---

### User Story 3 - Dashboard Analytics Integration (Priority: P2)

As a user reviewing my dashboard, I want to see a financial analytics summary alongside my pending tasks so that I have a single-pane view of both tasks and finances.

**Why this priority**: Ties the analytics output into the existing Dashboard, making the data actionable and visible without opening separate files.

**Independent Test**: Can be tested by running the analyzer on sample financial data and confirming the Dashboard's analytics section shows revenue, top expenses, and alerts.

**Acceptance Scenarios**:

1. **Given** the Data Analyzer has completed analysis, **When** the dashboard is updated, **Then** an Analytics Summary section appears with revenue, expenses, net income, and anomaly alerts
2. **Given** multiple analysis runs occur, **When** the dashboard updates, **Then** only the most recent analytics summary is shown (not appended cumulatively)
3. **Given** no financial data exists in `Accounting/`, **When** the dashboard updates, **Then** the analytics section displays "No financial data available"

---

### User Story 4 - Secure Credential Management (Priority: P1)

As a security-conscious user, I want Gmail credentials stored securely and never committed to version control so that my account is protected.

**Why this priority**: Security is a non-negotiable requirement. Gmail OAuth credentials must be handled safely before any Gmail integration can be deployed.

**Independent Test**: Can be tested by verifying credentials are loaded from environment variables, the `.env` file is in `.gitignore`, and the system fails gracefully with a clear message when credentials are missing.

**Acceptance Scenarios**:

1. **Given** valid Gmail credentials are configured in `.env`, **When** the Gmail watcher starts, **Then** it connects successfully and begins monitoring
2. **Given** no credentials are configured, **When** the Gmail watcher attempts to start, **Then** it displays a clear error message explaining what credentials are needed and how to set them up
3. **Given** credentials are expired or revoked, **When** the Gmail watcher attempts to connect, **Then** it logs the authentication failure and exits with a helpful error message

---

### Edge Cases

- What happens when an email has no subject? System uses "(No Subject)" as the task title
- What happens when an email body is empty? System creates the task with subject only and notes "No email body"
- What happens when the `Accounting/` folder contains non-CSV files? System ignores non-CSV files and only processes `.csv` and `.md` files
- What happens when a CSV has unexpected column names? System attempts to map common financial column patterns (amount, value, total, debit, credit) and logs a warning if no recognizable columns are found
- What happens when the Gmail watcher and file watcher both create tasks simultaneously? Each watcher operates independently; the existing file watcher processes Gmail-created task files just like any other
- What happens when a very large CSV (10,000+ rows) is analyzed? System processes it within 30 seconds and warns if analysis takes longer than expected
- What happens when Gmail API rate limits are hit? System backs off exponentially and resumes polling after the rate limit window passes

## Requirements

### Functional Requirements

- **FR-001**: System MUST poll Gmail for unread emails at a configurable interval (default: every 60 seconds)
- **FR-002**: System MUST create a `.md` file in `Needs_Action/` for each new unread email, containing YAML frontmatter with type, from, subject, date, and priority fields
- **FR-003**: System MUST assign `priority: high` to emails marked as important in Gmail and `priority: medium` to all others
- **FR-004**: System MUST mark processed emails as read in Gmail to prevent duplicate task creation
- **FR-005**: System MUST track processed email IDs in a persistent ledger to prevent duplicates across restarts
- **FR-006**: System MUST read CSV files from `Accounting/` and calculate total revenue, total expenses, and net income
- **FR-007**: System MUST group financial data by month when date information is available
- **FR-008**: System MUST detect anomalous transactions (amount exceeding 2x the category average) and flag them as alerts
- **FR-009**: System MUST update Dashboard.md with an analytics summary section between `<!-- START_ANALYTICS -->` and `<!-- END_ANALYTICS -->` markers
- **FR-010**: System MUST handle malformed CSV rows gracefully by skipping them and logging warnings
- **FR-011**: System MUST load Gmail credentials exclusively from environment variables or `.env` file, never from hardcoded values
- **FR-012**: System MUST log all Gmail watcher events (connection, email processed, errors) to the existing audit log system
- **FR-013**: System MUST provide a clear startup error when required Gmail credentials are missing
- **FR-014**: System MUST coexist with the existing file system watcher without conflicts

### Key Entities

- **Email Task**: A task file created from a Gmail email, containing sender address, subject line, email snippet (first 500 characters), received date, and priority level
- **Financial Record**: A row from a CSV file representing a transaction with date, description, amount, and category
- **Analytics Summary**: An aggregated view of financial data including totals by category, monthly trends, and anomaly alerts
- **Gmail Ledger**: A persistent record of processed email IDs to prevent duplicate processing across watcher restarts

## Success Criteria

### Measurable Outcomes

- **SC-001**: New unread emails appear as task files in `Needs_Action/` within 2 minutes of arrival
- **SC-002**: Zero duplicate task files are created for the same email, even across watcher restarts
- **SC-003**: Financial analysis of a 1,000-row CSV completes within 10 seconds
- **SC-004**: Dashboard analytics section accurately reflects the sum of all transaction amounts (revenue and expense totals match manual calculation)
- **SC-005**: 100% of anomalous transactions (>2x category average) are detected and flagged
- **SC-006**: System operates with 2 concurrent watchers (file + Gmail) without resource conflicts or crashes
- **SC-007**: Gmail credentials are never present in any committed file (verified by repository scan)
- **SC-008**: All Gmail watcher events are logged to the audit trail with timestamps
- **SC-009**: System provides clear, actionable error messages for all credential and connection failures
- **SC-010**: Existing Bronze Tier functionality (file watcher, SimpleTaskReaderSkill, dashboard pending tasks) continues to work unchanged

## Scope

### In Scope

- Gmail inbox monitoring for unread/important emails
- Email-to-task file conversion with priority assignment
- CSV financial data reading and analysis
- Revenue, expense, and net income calculations
- Anomaly detection based on category averages
- Dashboard analytics section updates
- Gmail credential management via `.env`
- Audit logging for all new components
- README updates with Gmail setup and analytics instructions

### Out of Scope

- Sending emails or replying to emails
- Gmail label/folder management beyond marking as read
- Real-time charting or graphical visualizations (Markdown tables only)
- Multi-account Gmail support (single account only)
- Historical email backfill (only processes emails arriving after watcher starts)
- Automated financial report generation (e.g., PDF exports)
- Integration with accounting software (QuickBooks, Xero, etc.)

## Assumptions

- User has a Google Cloud project with Gmail API enabled and OAuth 2.0 credentials configured
- Gmail API read-only scope is sufficient for the watcher's needs (plus modify scope for marking as read)
- CSV files in `Accounting/` follow a consistent format: columns include at minimum a description and amount; date and category are optional but recommended
- Positive amounts represent revenue/income; negative amounts represent expenses (or a separate type/category column distinguishes them)
- The existing Bronze Tier vault structure, file watcher, and audit logger remain unchanged and available
- The system runs on a single machine with Python 3.10+ available
- Internet connectivity is available for Gmail API access

## Dependencies

- Bronze Tier vault structure and file watcher (must be operational)
- Google Cloud project with Gmail API enabled
- OAuth 2.0 client credentials (client_id, client_secret)
- User authorization (OAuth consent) for Gmail read/modify access
