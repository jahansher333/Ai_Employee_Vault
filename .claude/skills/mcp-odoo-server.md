# MCP Odoo Server Skill

## Purpose
MCP (Model Context Protocol) server that exposes Odoo ERP financial data as tools callable from Claude Code. Wraps odoo_client.py via JSON-RPC with no logic duplication.

## When to Use
- When Claude Code needs to query invoices, balances, or financial summaries
- When checking Odoo connectivity or overdue invoices
- User asks to "check invoices", "financial summary", or "Odoo status"

## Commands
```bash
# Start MCP server (stdio transport)
python scripts/mcp_odoo_server.py
```

Add to `.claude/mcp.json` for auto-discovery by Claude Code.

## Configuration
Set in `.env` (used by odoo_client.py):
- `ODOO_URL` — Odoo instance URL
- `ODOO_DB` — Database name
- `ODOO_USERNAME` — Login username
- `ODOO_PASSWORD` — API key or password

## MCP Tools
| Tool | Description |
|------|-------------|
| `list_invoices` | List invoices (limit, state filter: posted/draft/all) |
| `get_overdue_invoices` | List unpaid invoices past due date with total |
| `get_account_balances` | Chart of accounts with balances (optional type filter) |
| `get_journal_entries` | Recent journal entry lines (limit param) |
| `get_financial_summary` | High-level revenue, expenses, net income, overdue |
| `check_odoo_connection` | Test connectivity and authentication |

## Response Format
All tools return a dict with `success: bool` and either the result data or `error: str`.

## Integration
- Lazy-imports and instantiates OdooClient on each call
- Delegates all logic to `odoo_client.py`
- Server name: `odoo`

## Script
`scripts/mcp_odoo_server.py`
