"""Odoo Community JSON-RPC client — read-only integration.

Gold Tier: Connects to a self-hosted Odoo Community 17.0+ instance via
JSON-RPC to read invoices, journal entries, account balances, and customers.
Detects overdue invoices and produces financial summaries for the CEO briefing.

Usage:
    python scripts/odoo_client.py --test          # Test connection
    python scripts/odoo_client.py --invoices      # List invoices
    python scripts/odoo_client.py --overdue       # Overdue invoices only
    python scripts/odoo_client.py --balances      # Account balances
    python scripts/odoo_client.py --summary       # Financial summary
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger

load_dotenv()


class OdooConnectionError(Exception):
    """Raised when Odoo is unreachable or authentication fails."""


class OdooClient:
    """Read-only JSON-RPC client for Odoo Community."""

    def __init__(
        self,
        url: str | None = None,
        db: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        self.url = (url or os.getenv("ODOO_URL", "")).rstrip("/")
        self.db = db or os.getenv("ODOO_DB", "")
        self.user = user or os.getenv("ODOO_USER", "")
        self.password = password or os.getenv("ODOO_PASSWORD", "")
        self.uid: int | None = None
        self._request_id = 0

    # ------------------------------------------------------------------
    # JSON-RPC transport
    # ------------------------------------------------------------------

    def _jsonrpc(self, service: str, method: str, args: list) -> dict:
        """Send a JSON-RPC call to Odoo."""
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "call",
            "params": {
                "service": service,
                "method": method,
                "args": args,
            },
        }
        endpoint = f"{self.url}/jsonrpc"
        try:
            resp = requests.post(endpoint, json=payload, timeout=15)
            resp.raise_for_status()
        except requests.ConnectionError:
            raise OdooConnectionError(
                f"Cannot connect to Odoo at {self.url}. Is the server running?"
            )
        except requests.Timeout:
            raise OdooConnectionError(f"Odoo request timed out ({endpoint})")
        except requests.HTTPError as exc:
            raise OdooConnectionError(f"Odoo HTTP error: {exc}")

        data = resp.json()
        if "error" in data:
            err = data["error"]
            msg = err.get("data", {}).get("message", err.get("message", str(err)))
            raise OdooConnectionError(f"Odoo RPC error: {msg}")
        return data.get("result")

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self) -> int:
        """Authenticate with Odoo. Returns uid on success.

        Raises OdooConnectionError on failure.
        """
        if not self.url or not self.db or not self.user or not self.password:
            raise OdooConnectionError(
                "Odoo credentials not configured. Set ODOO_URL, ODOO_DB, "
                "ODOO_USER, ODOO_PASSWORD in .env"
            )

        result = self._jsonrpc("common", "login", [self.db, self.user, self.password])

        if not result or result is False:
            raise OdooConnectionError(
                f"Odoo authentication failed for user '{self.user}' on db '{self.db}'"
            )

        self.uid = int(result)
        return self.uid

    def _ensure_auth(self) -> None:
        """Authenticate if not already authenticated."""
        if self.uid is None:
            self.authenticate()

    # ------------------------------------------------------------------
    # Generic read operations
    # ------------------------------------------------------------------

    def search_read(
        self,
        model: str,
        domain: list | None = None,
        fields: list[str] | None = None,
        limit: int = 100,
        order: str | None = None,
    ) -> list[dict]:
        """Search and read records from Odoo.

        Handles session expiry by re-authenticating once.
        """
        self._ensure_auth()
        kwargs: dict = {}
        if fields:
            kwargs["fields"] = fields
        if limit:
            kwargs["limit"] = limit
        if order:
            kwargs["order"] = order

        try:
            return self._jsonrpc("object", "execute_kw", [
                self.db, self.uid, self.password,
                model, "search_read",
                [domain or []],
                kwargs,
            ])
        except OdooConnectionError as exc:
            # Retry once with re-auth (session may have expired)
            if "session" in str(exc).lower() or "access" in str(exc).lower():
                self.uid = None
                self._ensure_auth()
                return self._jsonrpc("object", "execute_kw", [
                    self.db, self.uid, self.password,
                    model, "search_read",
                    [domain or []],
                    kwargs,
                ])
            raise

    # ------------------------------------------------------------------
    # Domain-specific queries
    # ------------------------------------------------------------------

    def list_invoices(
        self,
        limit: int = 50,
        state: str = "posted",
        payment_state: str | None = None,
    ) -> list[dict]:
        """List invoices from account.move."""
        domain: list = []
        if state != "all":
            domain.append(["state", "=", state])
        domain.append(["move_type", "in", ["out_invoice", "in_invoice"]])
        if payment_state and payment_state != "all":
            domain.append(["payment_state", "=", payment_state])

        fields = [
            "name", "partner_id", "move_type", "amount_total",
            "amount_residual", "currency_id", "invoice_date",
            "invoice_date_due", "payment_state", "state",
        ]

        records = self.search_read("account.move", domain, fields, limit,
                                   order="invoice_date desc")
        today = date.today().isoformat()
        result = []
        for r in records:
            partner = r.get("partner_id")
            inv = {
                "id": r["id"],
                "name": r.get("name", ""),
                "partner_name": partner[1] if isinstance(partner, (list, tuple)) else str(partner or ""),
                "partner_id": partner[0] if isinstance(partner, (list, tuple)) else None,
                "move_type": r.get("move_type", ""),
                "amount_total": r.get("amount_total", 0.0),
                "amount_residual": r.get("amount_residual", 0.0),
                "currency": _extract_name(r.get("currency_id")),
                "invoice_date": r.get("invoice_date") or "",
                "invoice_date_due": r.get("invoice_date_due") or "",
                "payment_state": r.get("payment_state", ""),
                "state": r.get("state", ""),
            }
            due = inv["invoice_date_due"]
            inv["is_overdue"] = bool(
                due and due < today and inv["payment_state"] != "paid"
            )
            result.append(inv)
        return result

    def get_overdue_invoices(self) -> list[dict]:
        """Return only overdue invoices."""
        all_invoices = self.list_invoices(limit=200, state="posted")
        return [inv for inv in all_invoices if inv["is_overdue"]]

    def list_journal_entries(
        self,
        limit: int = 50,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict]:
        """List journal entry lines from account.move.line."""
        domain: list = []
        if date_from:
            domain.append(["date", ">=", date_from])
        if date_to:
            domain.append(["date", "<=", date_to])

        fields = [
            "move_name", "account_id", "name", "debit", "credit",
            "date", "partner_id",
        ]

        records = self.search_read("account.move.line", domain, fields, limit,
                                   order="date desc")
        result = []
        for r in records:
            result.append({
                "id": r["id"],
                "move_name": r.get("move_name", ""),
                "account_name": _extract_name(r.get("account_id")),
                "description": r.get("name", ""),
                "debit": r.get("debit", 0.0),
                "credit": r.get("credit", 0.0),
                "date": r.get("date", ""),
                "partner_name": _extract_name(r.get("partner_id")),
            })
        return result

    def get_account_balances(self, account_type: str | None = None) -> list[dict]:
        """Get account balances from chart of accounts."""
        domain: list = []
        if account_type:
            domain.append(["account_type", "=", account_type])

        fields = ["code", "name", "current_balance", "account_type"]
        records = self.search_read("account.account", domain, fields, limit=200)
        result = []
        for r in records:
            result.append({
                "id": r["id"],
                "code": r.get("code", ""),
                "name": r.get("name", ""),
                "balance": r.get("current_balance", 0.0),
                "account_type": r.get("account_type", ""),
            })
        return result

    def get_financial_summary(self) -> dict:
        """Compute a high-level financial summary."""
        invoices = self.list_invoices(limit=500, state="posted")
        out_invoices = [i for i in invoices if i["move_type"] == "out_invoice"]
        in_invoices = [i for i in invoices if i["move_type"] == "in_invoice"]
        overdue = [i for i in invoices if i["is_overdue"]]

        total_revenue = sum(i["amount_total"] for i in out_invoices)
        total_expenses = sum(i["amount_total"] for i in in_invoices)
        outstanding = sum(i["amount_residual"] for i in invoices if i["payment_state"] != "paid")

        currencies = set(i["currency"] for i in invoices if i["currency"])
        currency = currencies.pop() if len(currencies) == 1 else "mixed"

        return {
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "net_income": total_revenue - total_expenses,
            "outstanding_invoices": outstanding,
            "overdue_amount": sum(i["amount_residual"] for i in overdue),
            "overdue_count": len(overdue),
            "invoice_count": len(invoices),
            "currency": currency,
            "success": True,
        }

    # ------------------------------------------------------------------
    # Inventory operations
    # ------------------------------------------------------------------

    def list_products(
        self,
        limit: int = 50,
        category: str | None = None,
    ) -> list[dict]:
        """List products with stock information."""
        domain: list = []
        if category:
            domain.append(["categ_id.name", "ilike", category])

        # Core fields always available
        fields = ["name", "default_code", "list_price", "categ_id", "type"]

        # Try stock fields (only if Inventory module installed)
        stock_fields = ["qty_available", "virtual_available"]
        has_stock = False
        try:
            test = self.search_read("product.product", [], fields + stock_fields, limit=1)
            if test is not None:
                has_stock = True
                fields += stock_fields
        except Exception:
            pass

        records = self.search_read("product.product", domain, fields, limit,
                                   order="name asc")
        result = []
        for r in records:
            result.append({
                "id": r["id"],
                "name": r.get("name", ""),
                "sku": r.get("default_code", "") or "",
                "price": r.get("list_price", 0.0),
                "qty_available": r.get("qty_available", 0.0) if has_stock else 0.0,
                "qty_forecast": r.get("virtual_available", 0.0) if has_stock else 0.0,
                "category": _extract_name(r.get("categ_id")),
                "type": r.get("type", ""),
                "has_stock_tracking": has_stock,
            })
        return result

    def get_low_stock_products(self, threshold: float = 5.0) -> list[dict]:
        """Return products where qty_available < threshold."""
        products = self.list_products(limit=500)
        return [p for p in products if p["qty_available"] < threshold]

    def get_inventory_summary(self) -> dict:
        """High-level inventory summary."""
        products = self.list_products(limit=1000)
        total_value = sum(p["price"] * max(p["qty_available"], 0) for p in products)
        low_stock = [p for p in products if p["qty_available"] < 5]
        out_of_stock = [p for p in products if p["qty_available"] <= 0]
        return {
            "total_products": len(products),
            "total_value": round(total_value, 2),
            "low_stock_count": len(low_stock),
            "out_of_stock_count": len(out_of_stock),
            "success": True,
        }

    def get_stock_moves(self, limit: int = 20) -> list[dict]:
        """Recent stock movements from stock.move."""
        fields = [
            "product_id", "product_uom_qty", "state", "date",
            "location_id", "location_dest_id",
        ]
        records = self.search_read("stock.move", [], fields, limit,
                                   order="date desc")
        result = []
        for r in records:
            result.append({
                "id": r["id"],
                "product": _extract_name(r.get("product_id")),
                "quantity": r.get("product_uom_qty", 0.0),
                "state": r.get("state", ""),
                "date": r.get("date", ""),
                "location_from": _extract_name(r.get("location_id")),
                "location_to": _extract_name(r.get("location_dest_id")),
            })
        return result

    def check_connection(self) -> dict:
        """Test Odoo connectivity and authentication."""
        try:
            uid = self.authenticate()
            version = self._jsonrpc("common", "version", [])
            return {
                "connected": True,
                "uid": uid,
                "server_version": version.get("server_version", "unknown") if isinstance(version, dict) else str(version),
                "database": self.db,
                "success": True,
            }
        except OdooConnectionError as exc:
            return {
                "connected": False,
                "error": str(exc),
                "success": False,
            }


def _extract_name(field_value) -> str:
    """Extract display name from Odoo many2one field [id, name]."""
    if isinstance(field_value, (list, tuple)) and len(field_value) >= 2:
        return str(field_value[1])
    if field_value is False or field_value is None:
        return ""
    return str(field_value)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Odoo Community JSON-RPC Client")
    parser.add_argument("--test", action="store_true", help="Test Odoo connection")
    parser.add_argument("--invoices", action="store_true", help="List invoices")
    parser.add_argument("--overdue", action="store_true", help="List overdue invoices")
    parser.add_argument("--balances", action="store_true", help="Show account balances")
    parser.add_argument("--journal", action="store_true", help="List journal entries")
    parser.add_argument("--summary", action="store_true", help="Financial summary")
    parser.add_argument("--products", action="store_true", help="List products with stock")
    parser.add_argument("--low-stock", action="store_true", help="Show low stock alerts")
    parser.add_argument("--inventory-summary", action="store_true", help="Inventory overview")
    parser.add_argument("--stock-moves", action="store_true", help="Recent stock movements")
    parser.add_argument("--limit", type=int, default=20, help="Limit results")
    args = parser.parse_args()

    client = OdooClient()

    if args.test:
        result = client.check_connection()
        if result["connected"]:
            print(f"Connected to Odoo (uid={result['uid']}, "
                  f"version={result['server_version']}, db={result['database']})")
        else:
            print(f"Connection failed: {result.get('error')}")
        return

    if args.invoices:
        invoices = client.list_invoices(limit=args.limit)
        for inv in invoices:
            overdue = " [OVERDUE]" if inv["is_overdue"] else ""
            print(f"  {inv['name']} | {inv['partner_name'][:25]} | "
                  f"{inv['currency']} {inv['amount_total']:,.2f} | "
                  f"Due: {inv['invoice_date_due']} | {inv['payment_state']}{overdue}")
        print(f"\nTotal: {len(invoices)} invoice(s)")
        return

    if args.overdue:
        overdue = client.get_overdue_invoices()
        if not overdue:
            print("No overdue invoices.")
            return
        for inv in overdue:
            print(f"  {inv['name']} | {inv['partner_name'][:25]} | "
                  f"{inv['currency']} {inv['amount_residual']:,.2f} | "
                  f"Due: {inv['invoice_date_due']}")
        print(f"\nTotal overdue: {len(overdue)} ({sum(i['amount_residual'] for i in overdue):,.2f})")
        return

    if args.balances:
        balances = client.get_account_balances()
        for acc in balances:
            if acc["balance"] != 0:
                print(f"  {acc['code']} {acc['name'][:30]} | {acc['balance']:,.2f}")
        return

    if args.journal:
        entries = client.list_journal_entries(limit=args.limit)
        for e in entries:
            print(f"  {e['date']} | {e['move_name']} | {e['account_name'][:20]} | "
                  f"D:{e['debit']:,.2f} C:{e['credit']:,.2f}")
        return

    if args.summary:
        summary = client.get_financial_summary()
        print(f"Revenue:     {summary['currency']} {summary['total_revenue']:,.2f}")
        print(f"Expenses:    {summary['currency']} {summary['total_expenses']:,.2f}")
        print(f"Net Income:  {summary['currency']} {summary['net_income']:,.2f}")
        print(f"Outstanding: {summary['currency']} {summary['outstanding_invoices']:,.2f}")
        print(f"Overdue:     {summary['overdue_count']} invoices "
              f"({summary['currency']} {summary['overdue_amount']:,.2f})")
        return

    if args.products:
        products = client.list_products(limit=args.limit)
        for p in products:
            sku = f" [{p['sku']}]" if p['sku'] else ""
            print(f"  {p['name']}{sku} | ${p['price']:,.2f} | "
                  f"Stock: {p['qty_available']:.0f} | Forecast: {p['qty_forecast']:.0f}")
        print(f"\nTotal: {len(products)} product(s)")
        return

    if args.low_stock:
        low = client.get_low_stock_products()
        if not low:
            print("No low stock products.")
            return
        for p in low:
            status = "OUT OF STOCK" if p['qty_available'] <= 0 else f"{p['qty_available']:.0f} remaining"
            print(f"  [ALERT] {p['name']} | {status} | ${p['price']:,.2f}")
        print(f"\nLow stock: {len(low)} product(s)")
        return

    if args.inventory_summary:
        s = client.get_inventory_summary()
        print(f"Total Products:  {s['total_products']}")
        print(f"Total Value:     ${s['total_value']:,.2f}")
        print(f"Low Stock:       {s['low_stock_count']}")
        print(f"Out of Stock:    {s['out_of_stock_count']}")
        return

    if args.stock_moves:
        moves = client.get_stock_moves(limit=args.limit)
        for m in moves:
            print(f"  {m['date'][:16]} | {m['product'][:25]} | "
                  f"Qty: {m['quantity']:.0f} | {m['state']} | "
                  f"{m['location_from'][:15]} -> {m['location_to'][:15]}")
        print(f"\nTotal: {len(moves)} move(s)")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
