# Odoo Accounting Integration Skill

## Purpose
Connect to a self-hosted Odoo Community instance and read financial data (invoices, journal entries, account balances) for the CEO briefing and business analysis.

## When to Use
- User asks about invoices, payments, or financial data
- Weekly audit needs Odoo financial data
- User asks "What invoices are overdue?"
- User asks for a financial summary or report

## Commands
```bash
# Test Odoo connection
python scripts/odoo_client.py --test

# List recent invoices
python scripts/odoo_client.py --invoices --limit 20

# List overdue invoices only
python scripts/odoo_client.py --overdue

# Show account balances
python scripts/odoo_client.py --balances

# Show journal entries
python scripts/odoo_client.py --journal --limit 20

# Financial summary (revenue, expenses, net income)
python scripts/odoo_client.py --summary
```

## MCP Tools (via Odoo MCP Server)
- `list_invoices` — Query invoices with filters (state, payment_state, overdue_only)
- `get_account_balances` — Chart of accounts with current balances
- `get_journal_entries` — Recent journal entry lines
- `get_financial_summary` — Revenue, expenses, net income, overdue amounts
- `check_odoo_connection` — Test connectivity and authentication

## Configuration
Set in `.env`:
- `ODOO_URL` — Odoo server URL (e.g., `http://localhost:8069`)
- `ODOO_DB` — Database name
- `ODOO_USER` — Login username
- `ODOO_PASSWORD` — Login password

## Audit Trail
All Odoo operations are logged to `Logs/*.audit.jsonl` with action type `odoo_*`.

## Error Handling
- Connection refused → Log warning, fall back to CSV analysis
- Session expired → Automatic re-authentication
- Invalid credentials → Clear error message with setup instructions
