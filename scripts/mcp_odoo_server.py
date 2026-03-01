"""MCP Server for Odoo JSON-RPC integration.

Gold Tier: Exposes Odoo financial data as MCP tools callable from Claude Code.
Wraps odoo_client.py — no logic duplication.

Start: python scripts/mcp_odoo_server.py (stdio transport)
"""

from __future__ import annotations

import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).parent))

mcp = FastMCP("odoo", instructions="Odoo Community accounting — invoices, balances, journal entries, financial summaries")


def _get_client():
    """Lazy-import and instantiate OdooClient."""
    from odoo_client import OdooClient
    return OdooClient()


@mcp.tool()
def list_invoices(limit: int = 20, state: str = "posted") -> dict:
    """List invoices from Odoo (account.move).

    Args:
        limit: Max invoices to return (default 20)
        state: Invoice state filter — 'posted', 'draft', or 'all'
    """
    try:
        client = _get_client()
        invoices = client.list_invoices(limit=limit, state=state)
        return {"success": True, "invoices": invoices, "count": len(invoices)}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def get_overdue_invoices() -> dict:
    """List all overdue (unpaid, past due date) invoices from Odoo."""
    try:
        client = _get_client()
        overdue = client.get_overdue_invoices()
        total = sum(i["amount_residual"] for i in overdue)
        return {"success": True, "invoices": overdue, "count": len(overdue),
                "total_overdue": total}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def get_account_balances(account_type: str | None = None) -> dict:
    """Get chart of accounts with current balances.

    Args:
        account_type: Optional filter (e.g., 'asset_receivable', 'liability_payable')
    """
    try:
        client = _get_client()
        balances = client.get_account_balances(account_type=account_type)
        return {"success": True, "accounts": balances, "count": len(balances)}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def get_journal_entries(limit: int = 20) -> dict:
    """Get recent journal entry lines from Odoo.

    Args:
        limit: Max entries to return (default 20)
    """
    try:
        client = _get_client()
        entries = client.list_journal_entries(limit=limit)
        return {"success": True, "entries": entries, "count": len(entries)}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def get_financial_summary() -> dict:
    """High-level financial summary: revenue, expenses, net income, overdue amounts."""
    try:
        client = _get_client()
        return client.get_financial_summary()
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def check_odoo_connection() -> dict:
    """Test Odoo connectivity and authentication."""
    try:
        client = _get_client()
        return client.check_connection()
    except Exception as exc:
        return {"success": False, "error": str(exc)}


if __name__ == "__main__":
    mcp.run()
