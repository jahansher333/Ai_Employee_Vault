"""Tests for odoo_mcp.py — XML-RPC client with draft invoice creation."""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock
import xmlrpc.client

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from odoo_mcp import OdooXmlRpcClient, OdooXmlRpcError, _extract_name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(**overrides):
    defaults = {"url": "http://localhost:8069", "db": "testdb",
                "user": "admin", "password": "admin"}
    defaults.update(overrides)
    return OdooXmlRpcClient(**defaults)


# ---------------------------------------------------------------------------
# Authentication & uid=None fix
# ---------------------------------------------------------------------------

class TestAuthentication:
    @patch.dict("os.environ", {"ODOO_URL": ""}, clear=False)
    def test_missing_url_raises(self):
        client = OdooXmlRpcClient(url="", db="testdb", user="admin", password="admin")
        # Force the attribute in case constructor fell back
        client.url = ""
        with pytest.raises(OdooXmlRpcError, match="ODOO_URL not set"):
            client.authenticate()

    @patch.dict("os.environ", {"ODOO_DB": ""}, clear=False)
    def test_missing_db_raises(self):
        client = OdooXmlRpcClient(url="http://localhost:8069", db="", user="admin", password="admin")
        client.db = ""
        with pytest.raises(OdooXmlRpcError, match="ODOO_DB not set"):
            client.authenticate()

    @patch.dict("os.environ", {"ODOO_USER": ""}, clear=False)
    def test_missing_user_raises(self):
        client = OdooXmlRpcClient(url="http://localhost:8069", db="testdb", user="", password="admin")
        client.user = ""
        with pytest.raises(OdooXmlRpcError, match="ODOO_USER or ODOO_PASSWORD"):
            client.authenticate()

    @patch.dict("os.environ", {"ODOO_PASSWORD": ""}, clear=False)
    def test_missing_password_raises(self):
        client = OdooXmlRpcClient(url="http://localhost:8069", db="testdb", user="admin", password="")
        client.password = ""
        with pytest.raises(OdooXmlRpcError, match="ODOO_USER or ODOO_PASSWORD"):
            client.authenticate()

    @patch.object(OdooXmlRpcClient, "check_db_exists", return_value=False)
    @patch.object(OdooXmlRpcClient, "list_databases", return_value=["other_db"])
    def test_db_not_found_raises(self, mock_list, mock_check):
        client = _make_client()
        with pytest.raises(OdooXmlRpcError, match="not found"):
            client.authenticate()

    @patch.object(OdooXmlRpcClient, "check_db_exists", return_value=True)
    def test_uid_none_raises(self, mock_check):
        client = _make_client()
        mock_common = MagicMock()
        mock_common.authenticate.return_value = None
        client._common = mock_common
        with pytest.raises(OdooXmlRpcError, match="uid is None"):
            client.authenticate()

    @patch.object(OdooXmlRpcClient, "check_db_exists", return_value=True)
    def test_uid_false_raises(self, mock_check):
        client = _make_client()
        mock_common = MagicMock()
        mock_common.authenticate.return_value = False
        client._common = mock_common
        with pytest.raises(OdooXmlRpcError, match="uid is False"):
            client.authenticate()

    @patch.object(OdooXmlRpcClient, "check_db_exists", return_value=True)
    def test_authenticate_success(self, mock_check):
        client = _make_client()
        mock_common = MagicMock()
        mock_common.authenticate.return_value = 2
        client._common = mock_common
        uid = client.authenticate()
        assert uid == 2
        assert client.uid == 2

    @patch.object(OdooXmlRpcClient, "check_db_exists", return_value=True)
    def test_connection_refused(self, mock_check):
        client = _make_client()
        mock_common = MagicMock()
        mock_common.authenticate.side_effect = ConnectionRefusedError()
        client._common = mock_common
        with pytest.raises(OdooXmlRpcError, match="Connection refused"):
            client.authenticate()


# ---------------------------------------------------------------------------
# Database listing
# ---------------------------------------------------------------------------

class TestDatabaseListing:
    def test_list_databases(self):
        client = _make_client()
        mock_db = MagicMock()
        mock_db.list.return_value = ["testdb", "production"]
        with patch("xmlrpc.client.ServerProxy", return_value=mock_db):
            dbs = client.list_databases()
        assert "testdb" in dbs
        assert "production" in dbs

    def test_check_db_exists_true(self):
        client = _make_client()
        with patch.object(client, "list_databases", return_value=["testdb", "other"]):
            assert client.check_db_exists() is True

    def test_check_db_exists_false(self):
        client = _make_client()
        with patch.object(client, "list_databases", return_value=["other"]):
            assert client.check_db_exists() is False

    def test_db_listing_disabled(self):
        client = _make_client()
        mock_db = MagicMock()
        mock_db.list.side_effect = xmlrpc.client.Fault(
            1, "Access Denied: security"
        )
        with patch("xmlrpc.client.ServerProxy", return_value=mock_db):
            dbs = client.list_databases()
        assert len(dbs) == 1
        assert "disabled" in dbs[0].lower()


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

class TestReadOperations:
    def _authed_client(self):
        client = _make_client()
        client.uid = 2
        client._object = MagicMock()
        return client

    def test_list_invoices(self):
        client = self._authed_client()
        client._object.execute_kw.return_value = [
            {
                "id": 1, "name": "INV/2026/0001",
                "partner_id": [10, "Acme Corp"],
                "move_type": "out_invoice",
                "amount_total": 1500.0, "amount_residual": 1500.0,
                "currency_id": [1, "USD"],
                "invoice_date": "2026-01-15",
                "invoice_date_due": "2026-02-15",
                "payment_state": "not_paid",
                "state": "posted",
            }
        ]
        invoices = client.list_invoices(limit=10)
        assert len(invoices) == 1
        assert invoices[0]["name"] == "INV/2026/0001"
        assert invoices[0]["partner_name"] == "Acme Corp"
        assert invoices[0]["amount_total"] == 1500.0
        assert invoices[0]["currency"] == "USD"

    def test_overdue_detection(self):
        client = self._authed_client()
        client._object.execute_kw.return_value = [
            {
                "id": 1, "name": "INV/2026/0001",
                "partner_id": [10, "Acme"], "move_type": "out_invoice",
                "amount_total": 500.0, "amount_residual": 500.0,
                "currency_id": [1, "USD"],
                "invoice_date": "2025-01-01",
                "invoice_date_due": "2025-06-01",  # Past due
                "payment_state": "not_paid",
                "state": "posted",
            },
            {
                "id": 2, "name": "INV/2026/0002",
                "partner_id": [11, "Beta"], "move_type": "out_invoice",
                "amount_total": 300.0, "amount_residual": 0.0,
                "currency_id": [1, "USD"],
                "invoice_date": "2025-01-01",
                "invoice_date_due": "2025-06-01",
                "payment_state": "paid",
                "state": "posted",
            },
        ]
        invoices = client.list_invoices(limit=10)
        assert invoices[0]["is_overdue"] is True
        assert invoices[1]["is_overdue"] is False

    def test_get_account_balances(self):
        client = self._authed_client()
        client._object.execute_kw.return_value = [
            {"id": 1, "code": "1100", "name": "Receivable",
             "current_balance": 5000.0, "account_type": "asset_receivable"},
        ]
        balances = client.get_account_balances()
        assert len(balances) == 1
        assert balances[0]["code"] == "1100"
        assert balances[0]["balance"] == 5000.0

    def test_financial_summary(self):
        client = self._authed_client()
        client._object.execute_kw.return_value = [
            {"id": 1, "name": "INV/001", "partner_id": [1, "A"],
             "move_type": "out_invoice", "amount_total": 1000.0,
             "amount_residual": 500.0, "currency_id": [1, "USD"],
             "invoice_date": "2026-01-01", "invoice_date_due": "2026-03-01",
             "payment_state": "partial", "state": "posted"},
            {"id": 2, "name": "BILL/001", "partner_id": [2, "B"],
             "move_type": "in_invoice", "amount_total": 400.0,
             "amount_residual": 400.0, "currency_id": [1, "USD"],
             "invoice_date": "2026-01-01", "invoice_date_due": "2026-03-01",
             "payment_state": "not_paid", "state": "posted"},
        ]
        summary = client.get_financial_summary()
        assert summary["success"] is True
        assert summary["total_revenue"] == 1000.0
        assert summary["total_expenses"] == 400.0
        assert summary["net_income"] == 600.0
        assert summary["currency"] == "USD"

    def test_session_expiry_reauth(self):
        """Verify that execute_kw retries on access errors."""
        client = self._authed_client()
        fault = xmlrpc.client.Fault(2, "Access denied: session expired")
        client._object.execute_kw.side_effect = [fault, []]

        with patch.object(client, "_ensure_auth"):
            result = client.search_read("account.move", [], ["name"], limit=5)
        # Should have called execute_kw twice (first fail, then retry)
        assert client._object.execute_kw.call_count == 2


# ---------------------------------------------------------------------------
# Draft invoice creation
# ---------------------------------------------------------------------------

class TestDraftInvoice:
    def _authed_client(self):
        client = _make_client()
        client.uid = 2
        client._object = MagicMock()
        return client

    def test_create_draft_invoice(self):
        client = self._authed_client()
        # Mock: find partner returns existing
        # Mock: create returns invoice ID
        # Mock: search_read returns created invoice
        client._object.execute_kw.side_effect = [
            [{"id": 10, "name": "Acme Corp"}],  # search_read for partner
            42,  # create invoice
            [{"id": 42, "name": "INV/2026/0042", "amount_total": 1500.0,
              "state": "draft", "partner_id": [10, "Acme Corp"]}],  # read back
        ]

        result = client.create_draft_invoice(
            partner_name="Acme Corp",
            lines=[{"name": "Consulting", "quantity": 10, "price_unit": 150.0}],
        )
        assert result["success"] is True
        assert result["invoice_id"] == 42
        assert result["state"] == "draft"
        assert "DRAFT" in result["message"]

    def test_create_draft_new_partner(self):
        """When partner doesn't exist, create a new one."""
        client = self._authed_client()
        client._object.execute_kw.side_effect = [
            [],  # search_read: partner not found
            99,  # create partner
            55,  # create invoice
            [{"id": 55, "name": "INV/2026/0055", "amount_total": 500.0,
              "state": "draft", "partner_id": [99, "New Corp"]}],
        ]

        result = client.create_draft_invoice(
            partner_name="New Corp",
            lines=[{"name": "Service", "quantity": 1, "price_unit": 500.0}],
        )
        assert result["success"] is True
        assert result["invoice_id"] == 55

    def test_create_draft_expense(self):
        client = self._authed_client()
        client._object.execute_kw.side_effect = [
            [{"id": 5, "name": "General Expense"}],  # find partner
            60,  # create
            [{"id": 60, "name": "BILL/2026/0001", "amount_total": 250.0,
              "state": "draft", "partner_id": [5, "General Expense"]}],
        ]

        result = client.create_draft_expense(
            description="Office Supplies",
            amount=250.0,
        )
        assert result["success"] is True
        assert result["invoice_id"] == 60

    def test_create_draft_fails(self):
        client = self._authed_client()
        client._object.execute_kw.side_effect = [
            [{"id": 10, "name": "Acme"}],  # find partner
            Exception("Odoo server error"),  # create fails
        ]

        result = client.create_draft_invoice(
            partner_name="Acme",
            lines=[{"name": "Item", "quantity": 1, "price_unit": 100.0}],
        )
        assert result["success"] is False
        assert "error" in result


# ---------------------------------------------------------------------------
# Check connection (diagnostic)
# ---------------------------------------------------------------------------

class TestCheckConnection:
    def test_success(self):
        client = _make_client()
        mock_common = MagicMock()
        mock_common.version.return_value = {"server_version": "17.0"}
        mock_common.authenticate.return_value = 2
        client._common = mock_common
        with patch.object(client, "check_db_exists", return_value=True):
            result = client.check_connection()
        assert result["success"] is True
        assert result["uid"] == 2
        assert result["server_version"] == "17.0"

    def test_db_not_found(self):
        client = _make_client()
        mock_common = MagicMock()
        mock_common.version.return_value = {"server_version": "17.0"}
        client._common = mock_common
        with patch.object(client, "check_db_exists", return_value=False):
            with patch.object(client, "list_databases", return_value=["other_db"]):
                result = client.check_connection()
        assert result["success"] is False
        assert "not found" in result["error"]
        assert "other_db" in result["available_databases"]

    def test_connection_refused(self):
        client = _make_client()
        client._common = None
        with patch("xmlrpc.client.ServerProxy") as mock_proxy:
            mock_instance = MagicMock()
            mock_instance.version.side_effect = ConnectionRefusedError()
            mock_proxy.return_value = mock_instance
            result = client.check_connection()
        assert result["success"] is False
        assert "refused" in result["error"].lower()


# ---------------------------------------------------------------------------
# Helper: _extract_name
# ---------------------------------------------------------------------------

class TestExtractName:
    def test_tuple_field(self):
        assert _extract_name([10, "Acme Corp"]) == "Acme Corp"

    def test_false_field(self):
        assert _extract_name(False) == ""

    def test_none_field(self):
        assert _extract_name(None) == ""

    def test_string_field(self):
        assert _extract_name("Direct") == "Direct"


# ---------------------------------------------------------------------------
# MCP Tools (if fastmcp available)
# ---------------------------------------------------------------------------

class TestMCPTools:
    """Test MCP tool wrappers return structured dicts."""

    def test_mcp_tools_importable(self):
        """Verify the MCP tools module can be imported."""
        try:
            from odoo_mcp import _HAS_MCP
            # Either fastmcp is available or not — both are valid
            assert isinstance(_HAS_MCP, bool)
        except ImportError:
            pytest.skip("odoo_mcp not importable")

    @patch("odoo_mcp._get_client")
    def test_list_invoices_tool(self, mock_get):
        try:
            from odoo_mcp import list_invoices as tool_list_invoices, _HAS_MCP
            if not _HAS_MCP:
                pytest.skip("fastmcp not installed")
        except ImportError:
            pytest.skip("MCP tools not available")

        mock_client = MagicMock()
        mock_client.list_invoices.return_value = [
            {"id": 1, "name": "INV/001", "amount_total": 100.0}
        ]
        mock_get.return_value = mock_client

        result = tool_list_invoices(limit=5, state="posted")
        assert result["success"] is True
        assert result["count"] == 1

    @patch("odoo_mcp._get_client")
    def test_create_draft_tool(self, mock_get):
        try:
            from odoo_mcp import create_draft_invoice as tool_create, _HAS_MCP
            if not _HAS_MCP:
                pytest.skip("fastmcp not installed")
        except ImportError:
            pytest.skip("MCP tools not available")

        mock_client = MagicMock()
        mock_client.create_draft_invoice.return_value = {
            "success": True, "invoice_id": 42, "state": "draft",
        }
        mock_get.return_value = mock_client

        result = tool_create(
            partner_name="Test",
            lines=[{"name": "Item", "quantity": 1, "price_unit": 100}],
        )
        assert result["success"] is True
        assert result["invoice_id"] == 42

    @patch("odoo_mcp._get_client")
    def test_tool_error_handling(self, mock_get):
        try:
            from odoo_mcp import check_odoo_connection as tool_check, _HAS_MCP
            if not _HAS_MCP:
                pytest.skip("fastmcp not installed")
        except ImportError:
            pytest.skip("MCP tools not available")

        mock_get.side_effect = Exception("Connection failed")
        result = tool_check()
        assert result["success"] is False
        assert "Connection failed" in result["error"]
