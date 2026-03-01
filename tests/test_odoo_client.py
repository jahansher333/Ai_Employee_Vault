"""Tests for odoo_client.py — mocked JSON-RPC responses."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from odoo_client import OdooClient, OdooConnectionError, _extract_name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_jsonrpc_response(result):
    """Build a mock requests.Response for JSON-RPC."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": result}
    resp.raise_for_status = MagicMock()
    return resp


def _make_client(**overrides):
    defaults = {"url": "http://localhost:8069", "db": "test",
                "user": "admin", "password": "admin"}
    defaults.update(overrides)
    return OdooClient(**defaults)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class TestAuthentication:
    @patch("odoo_client.requests.post")
    def test_authenticate_success(self, mock_post):
        mock_post.return_value = _mock_jsonrpc_response(2)
        client = _make_client()
        uid = client.authenticate()
        assert uid == 2
        assert client.uid == 2

    @patch("odoo_client.requests.post")
    def test_authenticate_failure(self, mock_post):
        mock_post.return_value = _mock_jsonrpc_response(False)
        client = _make_client()
        with pytest.raises(OdooConnectionError, match="authentication failed"):
            client.authenticate()

    def test_missing_credentials_raises(self, monkeypatch):
        monkeypatch.delenv("ODOO_URL", raising=False)
        monkeypatch.delenv("ODOO_DB", raising=False)
        monkeypatch.delenv("ODOO_USER", raising=False)
        monkeypatch.delenv("ODOO_PASSWORD", raising=False)
        client = OdooClient(url="", db="", user="", password="")
        with pytest.raises(OdooConnectionError, match="not configured"):
            client.authenticate()

    @patch("odoo_client.requests.post")
    def test_connection_refused(self, mock_post):
        import requests as req
        mock_post.side_effect = req.ConnectionError("Connection refused")
        client = _make_client()
        with pytest.raises(OdooConnectionError, match="Cannot connect"):
            client.authenticate()


# ---------------------------------------------------------------------------
# Invoice operations
# ---------------------------------------------------------------------------

class TestListInvoices:
    @patch("odoo_client.requests.post")
    def test_list_invoices(self, mock_post):
        auth_resp = _mock_jsonrpc_response(2)
        invoice_resp = _mock_jsonrpc_response([
            {
                "id": 1, "name": "INV/2026/0001",
                "partner_id": [10, "Acme Corp"],
                "move_type": "out_invoice",
                "amount_total": 5000.0, "amount_residual": 5000.0,
                "currency_id": [1, "USD"],
                "invoice_date": "2026-01-15",
                "invoice_date_due": "2026-02-15",
                "payment_state": "not_paid", "state": "posted",
            },
        ])
        mock_post.side_effect = [auth_resp, invoice_resp]

        client = _make_client()
        invoices = client.list_invoices(limit=10)
        assert len(invoices) == 1
        inv = invoices[0]
        assert inv["name"] == "INV/2026/0001"
        assert inv["partner_name"] == "Acme Corp"
        assert inv["amount_total"] == 5000.0
        assert inv["currency"] == "USD"

    @patch("odoo_client.requests.post")
    def test_overdue_detection(self, mock_post):
        auth_resp = _mock_jsonrpc_response(2)
        invoice_resp = _mock_jsonrpc_response([
            {
                "id": 1, "name": "INV/2026/0001",
                "partner_id": [10, "Acme Corp"],
                "move_type": "out_invoice",
                "amount_total": 5000.0, "amount_residual": 5000.0,
                "currency_id": [1, "USD"],
                "invoice_date": "2025-01-01",
                "invoice_date_due": "2025-02-01",  # Past due
                "payment_state": "not_paid", "state": "posted",
            },
            {
                "id": 2, "name": "INV/2026/0002",
                "partner_id": [11, "Beta LLC"],
                "move_type": "out_invoice",
                "amount_total": 3000.0, "amount_residual": 0.0,
                "currency_id": [1, "USD"],
                "invoice_date": "2025-01-01",
                "invoice_date_due": "2025-02-01",
                "payment_state": "paid", "state": "posted",
            },
        ])
        mock_post.side_effect = [auth_resp, invoice_resp]

        client = _make_client()
        invoices = client.list_invoices()
        overdue = [i for i in invoices if i["is_overdue"]]
        assert len(overdue) == 1
        assert overdue[0]["name"] == "INV/2026/0001"

    @patch("odoo_client.requests.post")
    def test_get_overdue_invoices(self, mock_post):
        auth_resp = _mock_jsonrpc_response(2)
        invoice_resp = _mock_jsonrpc_response([
            {
                "id": 1, "name": "INV/2025/0001",
                "partner_id": [10, "Acme Corp"],
                "move_type": "out_invoice",
                "amount_total": 5000.0, "amount_residual": 5000.0,
                "currency_id": [1, "USD"],
                "invoice_date": "2025-01-01",
                "invoice_date_due": "2025-02-01",
                "payment_state": "not_paid", "state": "posted",
            },
        ])
        mock_post.side_effect = [auth_resp, invoice_resp]

        client = _make_client()
        overdue = client.get_overdue_invoices()
        assert len(overdue) == 1


# ---------------------------------------------------------------------------
# Journal entries and balances
# ---------------------------------------------------------------------------

class TestJournalAndBalances:
    @patch("odoo_client.requests.post")
    def test_list_journal_entries(self, mock_post):
        auth_resp = _mock_jsonrpc_response(2)
        entries_resp = _mock_jsonrpc_response([
            {
                "id": 100, "move_name": "INV/2026/0001",
                "account_id": [1, "Revenue"],
                "name": "Product sale",
                "debit": 0.0, "credit": 5000.0,
                "date": "2026-01-15",
                "partner_id": [10, "Acme Corp"],
            },
        ])
        mock_post.side_effect = [auth_resp, entries_resp]

        client = _make_client()
        entries = client.list_journal_entries(limit=10)
        assert len(entries) == 1
        assert entries[0]["account_name"] == "Revenue"
        assert entries[0]["credit"] == 5000.0

    @patch("odoo_client.requests.post")
    def test_get_account_balances(self, mock_post):
        auth_resp = _mock_jsonrpc_response(2)
        balances_resp = _mock_jsonrpc_response([
            {"id": 1, "code": "1100", "name": "Accounts Receivable",
             "current_balance": 15000.0, "account_type": "asset_receivable"},
        ])
        mock_post.side_effect = [auth_resp, balances_resp]

        client = _make_client()
        balances = client.get_account_balances()
        assert len(balances) == 1
        assert balances[0]["code"] == "1100"
        assert balances[0]["balance"] == 15000.0


# ---------------------------------------------------------------------------
# Financial summary
# ---------------------------------------------------------------------------

class TestFinancialSummary:
    @patch("odoo_client.requests.post")
    def test_financial_summary(self, mock_post):
        auth_resp = _mock_jsonrpc_response(2)
        invoice_resp = _mock_jsonrpc_response([
            {"id": 1, "name": "INV/2026/0001", "partner_id": [10, "Acme"],
             "move_type": "out_invoice", "amount_total": 10000.0,
             "amount_residual": 5000.0, "currency_id": [1, "USD"],
             "invoice_date": "2026-01-01", "invoice_date_due": "2026-03-01",
             "payment_state": "partial", "state": "posted"},
            {"id": 2, "name": "BILL/2026/0001", "partner_id": [11, "Vendor"],
             "move_type": "in_invoice", "amount_total": 3000.0,
             "amount_residual": 3000.0, "currency_id": [1, "USD"],
             "invoice_date": "2026-01-15", "invoice_date_due": "2026-02-15",
             "payment_state": "not_paid", "state": "posted"},
        ])
        mock_post.side_effect = [auth_resp, invoice_resp]

        client = _make_client()
        summary = client.get_financial_summary()
        assert summary["success"] is True
        assert summary["total_revenue"] == 10000.0
        assert summary["total_expenses"] == 3000.0
        assert summary["net_income"] == 7000.0
        assert summary["currency"] == "USD"


# ---------------------------------------------------------------------------
# Connection check
# ---------------------------------------------------------------------------

class TestCheckConnection:
    @patch("odoo_client.requests.post")
    def test_check_connection_success(self, mock_post):
        auth_resp = _mock_jsonrpc_response(2)
        version_resp = _mock_jsonrpc_response({"server_version": "17.0"})
        mock_post.side_effect = [auth_resp, version_resp]

        client = _make_client()
        result = client.check_connection()
        assert result["connected"] is True
        assert result["uid"] == 2
        assert result["server_version"] == "17.0"

    @patch("odoo_client.requests.post")
    def test_check_connection_failure(self, mock_post):
        import requests as req
        mock_post.side_effect = req.ConnectionError("Refused")

        client = _make_client()
        result = client.check_connection()
        assert result["connected"] is False
        assert "success" in result and result["success"] is False


# ---------------------------------------------------------------------------
# Session re-auth
# ---------------------------------------------------------------------------

class TestSessionReAuth:
    @patch("odoo_client.requests.post")
    def test_session_expiry_reauth(self, mock_post):
        auth_resp = _mock_jsonrpc_response(2)
        # First search_read fails with session error
        error_resp = MagicMock()
        error_resp.status_code = 200
        error_resp.json.return_value = {
            "jsonrpc": "2.0", "id": 2,
            "error": {"message": "session expired", "data": {"message": "Odoo Session Expired"}},
        }
        error_resp.raise_for_status = MagicMock()
        # Re-auth + retry succeeds
        reauth_resp = _mock_jsonrpc_response(2)
        retry_resp = _mock_jsonrpc_response([
            {"id": 1, "name": "INV/2026/0001", "partner_id": [10, "A"],
             "move_type": "out_invoice", "amount_total": 100.0,
             "amount_residual": 100.0, "currency_id": [1, "USD"],
             "invoice_date": "2026-01-01", "invoice_date_due": "2026-03-01",
             "payment_state": "not_paid", "state": "posted"},
        ])
        mock_post.side_effect = [auth_resp, error_resp, reauth_resp, retry_resp]

        client = _make_client()
        invoices = client.list_invoices()
        assert len(invoices) == 1


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

class TestExtractName:
    def test_list_format(self):
        assert _extract_name([10, "Acme Corp"]) == "Acme Corp"

    def test_false_value(self):
        assert _extract_name(False) == ""

    def test_none_value(self):
        assert _extract_name(None) == ""

    def test_string_passthrough(self):
        assert _extract_name("Direct") == "Direct"
