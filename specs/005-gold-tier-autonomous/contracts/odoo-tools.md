# MCP Tool Contracts: Odoo Server

**Server**: `mcp_odoo_server.py`
**Transport**: stdio (FastMCP)

## Tools

### `list_invoices`

**Description**: List invoices from Odoo with optional filters.

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| limit | int | no | 50 | Maximum invoices to return |
| state | str | no | "posted" | Invoice state filter (`draft`, `posted`, `cancel`, `all`) |
| payment_state | str | no | null | Payment state filter (`not_paid`, `partial`, `paid`, `all`) |
| overdue_only | bool | no | false | Only return overdue invoices |

**Returns** (success):
```json
{
  "invoices": [
    {
      "id": 42,
      "name": "INV/2026/0001",
      "partner_name": "Acme Corp",
      "amount_total": 5000.00,
      "amount_residual": 5000.00,
      "currency": "USD",
      "invoice_date": "2026-01-15",
      "invoice_date_due": "2026-02-15",
      "payment_state": "not_paid",
      "is_overdue": true
    }
  ],
  "count": 1,
  "success": true
}
```

**Returns** (error):
```json
{
  "error": "Odoo connection failed: Connection refused",
  "success": false
}
```

---

### `get_account_balances`

**Description**: Get current account balances from Odoo chart of accounts.

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| account_type | str | no | null | Filter by account type (e.g., `asset_receivable`, `liability_payable`) |

**Returns** (success):
```json
{
  "accounts": [
    {
      "id": 1,
      "code": "1100",
      "name": "Accounts Receivable",
      "balance": 15000.00,
      "account_type": "asset_receivable"
    }
  ],
  "count": 5,
  "success": true
}
```

---

### `get_journal_entries`

**Description**: Get recent journal entries from Odoo.

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| limit | int | no | 50 | Maximum entries to return |
| date_from | str | no | null | Start date filter (YYYY-MM-DD) |
| date_to | str | no | null | End date filter (YYYY-MM-DD) |

**Returns** (success):
```json
{
  "entries": [
    {
      "id": 100,
      "move_name": "INV/2026/0001",
      "account_name": "Revenue",
      "debit": 0.0,
      "credit": 5000.0,
      "date": "2026-01-15",
      "partner_name": "Acme Corp"
    }
  ],
  "count": 10,
  "success": true
}
```

---

### `get_financial_summary`

**Description**: Get a high-level financial summary (revenue, expenses, outstanding, overdue).

**Parameters**: None

**Returns** (success):
```json
{
  "total_revenue": 50000.00,
  "total_expenses": 35000.00,
  "net_income": 15000.00,
  "outstanding_invoices": 12000.00,
  "overdue_amount": 5000.00,
  "overdue_count": 3,
  "currency": "USD",
  "success": true
}
```

---

### `check_odoo_connection`

**Description**: Test Odoo connectivity and authentication.

**Parameters**: None

**Returns**:
```json
{
  "connected": true,
  "uid": 2,
  "server_version": "17.0",
  "database": "mycompany",
  "success": true
}
```
