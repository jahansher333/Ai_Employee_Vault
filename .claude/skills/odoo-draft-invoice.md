# Odoo Draft Invoice Skill

## Purpose
Create draft invoices and expenses in Odoo Community via XML-RPC. All entries stay in DRAFT state until a human reviews and posts them in the Odoo web UI.

## When to Use
- User asks to "create an invoice for [customer]"
- User asks to "log an expense" or "record a bill"
- User asks to "invoice [customer] for [service/amount]"
- A cross-domain task (Ralph Wiggum loop) needs to create accounting entries

## IMPORTANT: Human Approval Required
Draft invoices are NEVER auto-posted. The flow is:
1. AI creates draft invoice via MCP tool
2. AI reports the draft details to the user
3. User reviews in Odoo web UI
4. User manually posts the invoice (or deletes it)

## Commands (CLI)
```bash
# Test Odoo connection (diagnose uid=None errors)
python scripts/odoo_mcp.py --setup-check

# List available databases (fix "DB not found")
python scripts/odoo_mcp.py --list-dbs

# Test connection
python scripts/odoo_mcp.py --test

# Create a test draft invoice
python scripts/odoo_mcp.py --create-draft

# List invoices (including drafts)
python scripts/odoo_mcp.py --invoices
```

## MCP Tools (via odoo-xmlrpc server)
- `check_odoo_connection` — Diagnose connectivity, DB, and auth issues
- `list_odoo_databases` — List all databases (find the right DB name)
- `list_invoices` — Query invoices by state and payment status
- `get_overdue_invoices` — Unpaid invoices past due date
- `get_account_balances` — Chart of accounts with balances
- `get_financial_summary` — Revenue, expenses, net income
- `create_draft_invoice` — Create a DRAFT customer invoice or vendor bill
- `create_draft_expense` — Create a DRAFT vendor bill for an expense

## Example: Create Draft Invoice
```
User: "Invoice Acme Corp for 10 hours consulting at $150/hr"

AI uses create_draft_invoice tool:
  partner_name: "Acme Corp"
  lines: [{"name": "Consulting Services", "quantity": 10, "price_unit": 150.0}]
  move_type: "out_invoice"

Result: Draft invoice INV/2026/0042 created ($1,500.00)
        Review at: http://localhost:8069/web#id=42&model=account.move
```

## Fixing "NoneType uid" Error
This is the most common Odoo setup issue. Run:
```bash
python scripts/odoo_mcp.py --setup-check
```

Common causes:
1. **Database doesn't exist**: Go to `http://localhost:8069/web/database/manager` and create it
2. **Wrong DB name**: Run `--list-dbs` to see available databases, update `ODOO_DB` in `.env`
3. **Wrong credentials**: Check `ODOO_USER` and `ODOO_PASSWORD` in `.env`
4. **Odoo not running**: Start with `python odoo-bin -c odoo.conf`

## Configuration
Set in `.env`:
- `ODOO_URL` — Server URL (default: `http://localhost:8069`)
- `ODOO_DB` — Database name (MUST match an existing database)
- `ODOO_USER` — Login username (default: `admin`)
- `ODOO_PASSWORD` — Login password (NEVER commit to git)

## Error Handling
- Connection refused -> Clear message with startup command
- DB not found -> Lists available databases, gives creation steps
- uid=None -> Full diagnostic with `--setup-check`
- Session expired -> Auto re-authentication
- Create fails -> Returns structured error, no partial state
