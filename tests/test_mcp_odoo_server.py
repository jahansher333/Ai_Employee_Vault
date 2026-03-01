"""Tests for mcp_odoo_server.py — Odoo MCP tool functions."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from mcp_odoo_server import (
    list_invoices,
    get_overdue_invoices,
    get_account_balances,
    get_journal_entries,
    get_financial_summary,
    check_odoo_connection,
)


# ---------------------------------------------------------------------------
# list_invoices
# ---------------------------------------------------------------------------

class TestListInvoices:
    @patch("mcp_odoo_server._get_client")
    def test_success(self, mock_client):
        client = MagicMock()
        client.list_invoices.return_value = [
            {"name": "INV/001", "amount_total": 5000},
        ]
        mock_client.return_value = client
        result = list_invoices(limit=10)
        assert result["success"] is True
        assert result["count"] == 1
        assert result["invoices"][0]["name"] == "INV/001"

    @patch("mcp_odoo_server._get_client")
    def test_connection_error(self, mock_client):
        mock_client.side_effect = Exception("Connection refused")
        result = list_invoices()
        assert result["success"] is False
        assert "Connection refused" in result["error"]


# ---------------------------------------------------------------------------
# get_overdue_invoices
# ---------------------------------------------------------------------------

class TestGetOverdueInvoices:
    @patch("mcp_odoo_server._get_client")
    def test_success(self, mock_client):
        client = MagicMock()
        client.get_overdue_invoices.return_value = [
            {"name": "INV/001", "amount_residual": 3000},
        ]
        mock_client.return_value = client
        result = get_overdue_invoices()
        assert result["success"] is True
        assert result["count"] == 1
        assert result["total_overdue"] == 3000

    @patch("mcp_odoo_server._get_client")
    def test_no_overdue(self, mock_client):
        client = MagicMock()
        client.get_overdue_invoices.return_value = []
        mock_client.return_value = client
        result = get_overdue_invoices()
        assert result["count"] == 0
        assert result["total_overdue"] == 0


# ---------------------------------------------------------------------------
# get_account_balances
# ---------------------------------------------------------------------------

class TestGetAccountBalances:
    @patch("mcp_odoo_server._get_client")
    def test_success(self, mock_client):
        client = MagicMock()
        client.get_account_balances.return_value = [
            {"code": "1100", "name": "Receivable", "balance": 15000},
        ]
        mock_client.return_value = client
        result = get_account_balances()
        assert result["success"] is True
        assert result["count"] == 1

    @patch("mcp_odoo_server._get_client")
    def test_with_filter(self, mock_client):
        client = MagicMock()
        client.get_account_balances.return_value = []
        mock_client.return_value = client
        result = get_account_balances(account_type="asset_receivable")
        client.get_account_balances.assert_called_with(account_type="asset_receivable")


# ---------------------------------------------------------------------------
# get_journal_entries
# ---------------------------------------------------------------------------

class TestGetJournalEntries:
    @patch("mcp_odoo_server._get_client")
    def test_success(self, mock_client):
        client = MagicMock()
        client.list_journal_entries.return_value = [
            {"move_name": "INV/001", "debit": 5000, "credit": 0},
        ]
        mock_client.return_value = client
        result = get_journal_entries(limit=5)
        assert result["success"] is True
        assert result["count"] == 1


# ---------------------------------------------------------------------------
# get_financial_summary
# ---------------------------------------------------------------------------

class TestGetFinancialSummary:
    @patch("mcp_odoo_server._get_client")
    def test_success(self, mock_client):
        client = MagicMock()
        client.get_financial_summary.return_value = {
            "total_revenue": 100000, "total_expenses": 40000,
            "net_income": 60000, "success": True,
        }
        mock_client.return_value = client
        result = get_financial_summary()
        assert result["success"] is True
        assert result["net_income"] == 60000


# ---------------------------------------------------------------------------
# check_odoo_connection
# ---------------------------------------------------------------------------

class TestCheckOdooConnection:
    @patch("mcp_odoo_server._get_client")
    def test_success(self, mock_client):
        client = MagicMock()
        client.check_connection.return_value = {
            "connected": True, "uid": 2, "server_version": "19.0", "success": True,
        }
        mock_client.return_value = client
        result = check_odoo_connection()
        assert result["connected"] is True
        assert result["server_version"] == "19.0"

    @patch("mcp_odoo_server._get_client")
    def test_failure(self, mock_client):
        mock_client.side_effect = Exception("No Odoo")
        result = check_odoo_connection()
        assert result["success"] is False
