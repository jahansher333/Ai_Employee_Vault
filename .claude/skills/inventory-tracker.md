# Inventory Tracker Skill

## Purpose
Track products, stock levels, and movements in Odoo. Alert on low stock and out-of-stock items.

## When to Use
- User asks about product stock levels
- User asks "What's running low?"
- Weekly briefing needs inventory data
- User asks for inventory summary

## Commands
```bash
# List products with stock
python scripts/odoo_client.py --products

# Show low stock alerts (qty < 5)
python scripts/odoo_client.py --low-stock

# Inventory overview (totals, value, alerts)
python scripts/odoo_client.py --inventory-summary

# Recent stock movements
python scripts/odoo_client.py --stock-moves

# Limit results
python scripts/odoo_client.py --products --limit 50
```

## MCP Tools (via Odoo MCP Server)
- `list_products` — Query products with stock info
- `get_low_stock_alerts` — Products below threshold
- `get_inventory_summary` — Total products, value, alerts

## Configuration
Uses same Odoo credentials from `.env`:
- `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_PASSWORD`

## Prerequisites
- Odoo Inventory module installed and configured
- Products with "Storable Product" type for stock tracking

## Integration
- Low stock alerts can trigger Slack notifications via `slack_notifier.py`
- Inventory data included in CEO briefing
- All operations logged to audit trail

## Script
`scripts/odoo_client.py` (inventory methods added to OdooClient class)
