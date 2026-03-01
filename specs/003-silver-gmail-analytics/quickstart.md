# Quickstart: Silver Tier - Gmail Watcher + Data Analytics

**Feature**: 003-silver-gmail-analytics

## Prerequisites

1. Bronze Tier fully operational (file watcher, process_inbox, dashboard updates)
2. Python 3.10+ with pip
3. Google Cloud project with Gmail API enabled
4. OAuth 2.0 Client ID credentials (Desktop application type)

## Setup Steps

### 1. Install Dependencies

```bash
pip install google-api-python-client google-auth-oauthlib pandas python-dotenv
```

### 2. Gmail API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or select existing)
3. Enable the Gmail API
4. Create OAuth 2.0 Client ID (Application type: Desktop)
5. Download `credentials.json` to vault root
6. Add to `.env`:
   ```
   GMAIL_CREDENTIALS_PATH=credentials.json
   GMAIL_TOKEN_PATH=token.json
   GMAIL_POLL_INTERVAL=60
   ```

### 3. First-Time Authorization

```bash
python scripts/gmail_watcher.py --auth-only
```
This opens a browser for Google OAuth consent. After approving, `token.json` is created automatically.

### 4. Create Accounting Folder

```bash
mkdir Accounting
```

Place CSV files with financial data (date, description, amount, category columns).

## End-to-End Test Scenarios

### Test 1: Gmail Watcher Creates Task

1. Start both watchers:
   ```bash
   python scripts/watcher.py &
   python scripts/gmail_watcher.py &
   ```
2. Send a test email to the monitored Gmail account
3. Wait up to 2 minutes
4. Verify:
   - `Needs_Action/EMAIL_*.md` file exists with correct frontmatter
   - Email is marked as read in Gmail
   - Audit log shows `email_processed` entry
   - File watcher picks up the email task and processes it
   - Dashboard pending tasks table includes the email task

### Test 2: Financial Analysis

1. Create a sample CSV:
   ```bash
   cat > Accounting/sample-transactions.csv << 'EOF'
   date,description,amount,category
   2026-01-15,Client A Payment,5000.00,Revenue
   2026-01-16,Office Supplies,-150.00,Operations
   2026-01-20,Software License,-2999.99,Technology
   2026-01-25,Client B Payment,3000.00,Revenue
   2026-02-01,Rent,-1500.00,Operations
   2026-02-05,Contractor Payment,-800.00,Services
   2026-02-10,Client C Payment,7500.00,Revenue
   EOF
   ```
2. Run the analyzer:
   ```bash
   python scripts/data_analyzer.py
   ```
3. Verify:
   - Dashboard shows Business Analytics section
   - Revenue/Expenses/Net Income totals are correct
   - Monthly breakdown groups Jan and Feb
   - Software License flagged as anomaly (2999.99 vs Operations avg)
   - Audit log shows `analytics_completed`

### Test 3: Concurrent Watchers

1. Start both watchers simultaneously
2. Create a file in `Needs_Action/` manually
3. Send an email to Gmail
4. Verify both are processed without conflicts
5. Check no duplicate entries in dashboard

### Test 4: Missing Credentials

1. Rename/remove `credentials.json`
2. Run `python scripts/gmail_watcher.py`
3. Verify clear error message about missing credentials
4. Restore credentials

## Expected Output

### Email Task File
```markdown
---
type: email
from: sender@example.com
subject: "Meeting Tomorrow"
date: 2026-02-21T10:30:00Z
priority: medium
gmail_id: 18d4a5b2c3e4f
status: new
---

# Meeting Tomorrow

**From**: sender@example.com
**Date**: 2026-02-21 10:30 UTC

## Email Snippet

Hi, just wanted to confirm our meeting tomorrow at 2pm...
```

### Dashboard Analytics Section
```markdown
<!-- START_ANALYTICS -->
## Business Analytics

**Last Updated**: 2026-02-21 14:30 UTC | **Files Analyzed**: 1

### Financial Summary

| Metric | Amount |
|--------|--------|
| Total Revenue | $15,500.00 |
| Total Expenses | $5,449.99 |
| Net Income | $10,050.01 |
<!-- END_ANALYTICS -->
```
