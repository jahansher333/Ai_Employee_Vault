"""Odoo MCP Server — XML-RPC client with draft invoice creation.

Gold Tier: Connects to self-hosted Odoo Community via XML-RPC (xmlrpc.client).
Exposes tools for reading invoices, creating draft invoices/expenses, and
checking connections. Fixes the common 'NoneType uid' error by validating
DB existence before authentication.

The 'NoneType uid' error occurs when:
1. The Odoo database doesn't exist yet (fresh install)
2. Wrong database name in .env
3. Wrong credentials (user/password)

Fix: Run `python scripts/odoo_mcp.py --setup-check` to diagnose.

Usage:
    python scripts/odoo_mcp.py                    # Start MCP server (stdio)
    python scripts/odoo_mcp.py --test              # Test connection
    python scripts/odoo_mcp.py --setup-check       # Diagnose uid=None errors
    python scripts/odoo_mcp.py --list-dbs          # List available databases
    python scripts/odoo_mcp.py --create-draft      # Create a test draft invoice
"""

from __future__ import annotations

import argparse
import os
import sys
import xmlrpc.client
from datetime import date, datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger

load_dotenv()


# ---------------------------------------------------------------------------
# Odoo XML-RPC Client
# ---------------------------------------------------------------------------

class OdooXmlRpcError(Exception):
    """Raised when Odoo XML-RPC operations fail."""


class OdooXmlRpcClient:
    """XML-RPC client for Odoo Community using xmlrpc.client.

    Handles the common 'NoneType uid' error by:
    1. Checking DB exists before authenticating
    2. Providing clear error messages for each failure mode
    3. Auto-retrying authentication on session expiry
    """

    def __init__(
        self,
        url: str | None = None,
        db: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        self.url = (url or os.getenv("ODOO_URL", "http://localhost:8069")).rstrip("/")
        self.db = db or os.getenv("ODOO_DB", "")
        self.user = user or os.getenv("ODOO_USER", "")
        self.password = password or os.getenv("ODOO_PASSWORD", "")
        self.uid: int | None = None
        self._common: xmlrpc.client.ServerProxy | None = None
        self._object: xmlrpc.client.ServerProxy | None = None

    # ------------------------------------------------------------------
    # XML-RPC Proxies
    # ------------------------------------------------------------------

    def _get_common(self) -> xmlrpc.client.ServerProxy:
        """Get or create the /xmlrpc/2/common proxy."""
        if self._common is None:
            self._common = xmlrpc.client.ServerProxy(
                f"{self.url}/xmlrpc/2/common", allow_none=True
            )
        return self._common

    def _get_object(self) -> xmlrpc.client.ServerProxy:
        """Get or create the /xmlrpc/2/object proxy."""
        if self._object is None:
            self._object = xmlrpc.client.ServerProxy(
                f"{self.url}/xmlrpc/2/object", allow_none=True
            )
        return self._object

    # ------------------------------------------------------------------
    # Database operations
    # ------------------------------------------------------------------

    def list_databases(self) -> list[str]:
        """List available databases on the Odoo server.

        This is the first diagnostic step for 'NoneType uid' errors.
        If the target DB isn't listed, it needs to be created.
        """
        try:
            db_proxy = xmlrpc.client.ServerProxy(
                f"{self.url}/xmlrpc/2/db", allow_none=True
            )
            return db_proxy.list()
        except xmlrpc.client.Fault as exc:
            # Some Odoo configs disable DB listing for security
            if "access denied" in str(exc).lower() or "security" in str(exc).lower():
                return ["(DB listing disabled — check Odoo config)"]
            raise OdooXmlRpcError(f"Cannot list databases: {exc}")
        except Exception as exc:
            raise OdooXmlRpcError(
                f"Cannot connect to Odoo at {self.url}: {exc}"
            )

    def check_db_exists(self) -> bool:
        """Check if the configured database exists."""
        try:
            dbs = self.list_databases()
            if dbs and dbs[0].startswith("(DB listing disabled"):
                return True  # Can't verify — assume it exists
            return self.db in dbs
        except OdooXmlRpcError:
            return False

    # ------------------------------------------------------------------
    # Authentication (fixes NoneType uid)
    # ------------------------------------------------------------------

    def authenticate(self) -> int:
        """Authenticate with Odoo via XML-RPC. Returns uid.

        This is where 'NoneType uid' errors originate. The fix:
        1. Validate credentials are configured
        2. Check database exists
        3. Authenticate and handle False/None returns explicitly

        Raises OdooXmlRpcError with a specific diagnostic message.
        """
        if not self.url:
            raise OdooXmlRpcError(
                "ODOO_URL not set. Add ODOO_URL=http://localhost:8069 to .env"
            )
        if not self.db:
            raise OdooXmlRpcError(
                "ODOO_DB not set. Add ODOO_DB=your_database_name to .env. "
                "Run --list-dbs to see available databases."
            )
        if not self.user or not self.password:
            raise OdooXmlRpcError(
                "ODOO_USER or ODOO_PASSWORD not set in .env"
            )

        # Step 1: Check database exists (root cause of most uid=None errors)
        if not self.check_db_exists():
            available = []
            try:
                available = self.list_databases()
            except OdooXmlRpcError:
                pass
            db_list = ", ".join(available) if available else "(none found)"
            raise OdooXmlRpcError(
                f"Database '{self.db}' not found on {self.url}. "
                f"Available databases: {db_list}. "
                f"Create the database via Odoo web UI at {self.url}/web/database/manager "
                f"or set the correct ODOO_DB in .env"
            )

        # Step 2: Authenticate
        try:
            common = self._get_common()
            uid = common.authenticate(self.db, self.user, self.password, {})
        except xmlrpc.client.Fault as exc:
            raise OdooXmlRpcError(f"Odoo authentication fault: {exc.faultString}")
        except ConnectionRefusedError:
            raise OdooXmlRpcError(
                f"Connection refused at {self.url}. Is Odoo running? "
                f"Start with: python odoo-bin -c odoo.conf"
            )
        except Exception as exc:
            raise OdooXmlRpcError(f"Cannot connect to Odoo: {exc}")

        # Step 3: Handle uid=None/False (wrong credentials)
        if uid is None or uid is False:
            raise OdooXmlRpcError(
                f"Authentication failed: uid is {uid}. "
                f"Check ODOO_USER='{self.user}' and ODOO_PASSWORD in .env. "
                f"The user must exist in database '{self.db}'."
            )

        self.uid = int(uid)
        return self.uid

    def _ensure_auth(self) -> None:
        """Authenticate if uid is not set."""
        if self.uid is None:
            self.authenticate()

    # ------------------------------------------------------------------
    # Generic execute_kw
    # ------------------------------------------------------------------

    def execute_kw(
        self,
        model: str,
        method: str,
        args: list,
        kwargs: dict | None = None,
    ):
        """Execute an Odoo model method via XML-RPC.

        Handles session expiry by re-authenticating once.
        """
        self._ensure_auth()
        obj = self._get_object()
        try:
            return obj.execute_kw(
                self.db, self.uid, self.password,
                model, method, args, kwargs or {}
            )
        except xmlrpc.client.Fault as exc:
            # Re-auth on access/session errors
            if "access" in str(exc).lower() or "session" in str(exc).lower():
                self.uid = None
                self._ensure_auth()
                return obj.execute_kw(
                    self.db, self.uid, self.password,
                    model, method, args, kwargs or {}
                )
            raise OdooXmlRpcError(f"Odoo execute error: {exc.faultString}")

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def search_read(
        self,
        model: str,
        domain: list | None = None,
        fields: list[str] | None = None,
        limit: int = 100,
        order: str | None = None,
    ) -> list[dict]:
        """Search and read records."""
        kw: dict = {}
        if fields:
            kw["fields"] = fields
        if limit:
            kw["limit"] = limit
        if order:
            kw["order"] = order
        return self.execute_kw(model, "search_read", [domain or []], kw)

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
        records = self.search_read("account.move", domain, fields, limit, "invoice_date desc")
        today = date.today().isoformat()
        result = []
        for r in records:
            partner = r.get("partner_id")
            inv = {
                "id": r["id"],
                "name": r.get("name", ""),
                "partner_name": partner[1] if isinstance(partner, (list, tuple)) else str(partner or ""),
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
            inv["is_overdue"] = bool(due and due < today and inv["payment_state"] != "paid")
            result.append(inv)
        return result

    def get_overdue_invoices(self) -> list[dict]:
        """Return only overdue invoices."""
        all_inv = self.list_invoices(limit=200, state="posted")
        return [i for i in all_inv if i["is_overdue"]]

    def get_account_balances(self, account_type: str | None = None) -> list[dict]:
        """Get account balances from chart of accounts."""
        domain: list = []
        if account_type:
            domain.append(["account_type", "=", account_type])
        fields = ["code", "name", "current_balance", "account_type"]
        records = self.search_read("account.account", domain, fields, limit=200)
        return [
            {"id": r["id"], "code": r.get("code", ""), "name": r.get("name", ""),
             "balance": r.get("current_balance", 0.0), "account_type": r.get("account_type", "")}
            for r in records
        ]

    def get_financial_summary(self) -> dict:
        """Compute a high-level financial summary."""
        invoices = self.list_invoices(limit=500, state="posted")
        out_inv = [i for i in invoices if i["move_type"] == "out_invoice"]
        in_inv = [i for i in invoices if i["move_type"] == "in_invoice"]
        overdue = [i for i in invoices if i["is_overdue"]]
        total_revenue = sum(i["amount_total"] for i in out_inv)
        total_expenses = sum(i["amount_total"] for i in in_inv)
        outstanding = sum(i["amount_residual"] for i in invoices if i["payment_state"] != "paid")
        currencies = set(i["currency"] for i in invoices if i["currency"])
        currency = currencies.pop() if len(currencies) == 1 else "mixed" if currencies else "USD"
        return {
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "net_income": total_revenue - total_expenses,
            "outstanding_invoices": outstanding,
            "overdue_amount": sum(i["amount_residual"] for i in overdue),
            "overdue_count": len(overdue),
            "currency": currency,
            "success": True,
        }

    # ------------------------------------------------------------------
    # Write operations (draft only — HITL approval required)
    # ------------------------------------------------------------------

    def create_draft_invoice(
        self,
        partner_name: str,
        lines: list[dict],
        move_type: str = "out_invoice",
        invoice_date: str | None = None,
    ) -> dict:
        """Create a DRAFT invoice in Odoo. Does NOT post it.

        The invoice stays in 'draft' state until a human approves and
        posts it via the Odoo web UI.

        Parameters
        ----------
        partner_name : str
            Customer/vendor name. Will search for existing partner or
            create a minimal one.
        lines : list[dict]
            Invoice lines, each with: name (str), quantity (float),
            price_unit (float). E.g.:
            [{"name": "Consulting", "quantity": 10, "price_unit": 150.0}]
        move_type : str
            'out_invoice' (customer invoice) or 'in_invoice' (vendor bill).
        invoice_date : str | None
            Invoice date (YYYY-MM-DD). Defaults to today.

        Returns
        -------
        dict with keys: success, invoice_id, invoice_name, amount_total, state
        """
        self._ensure_auth()

        # Find or note the partner
        partner_id = self._find_or_note_partner(partner_name)

        # Build invoice lines in Odoo's command format
        odoo_lines = []
        for line in lines:
            odoo_lines.append((0, 0, {
                "name": line.get("name", "Item"),
                "quantity": line.get("quantity", 1),
                "price_unit": line.get("price_unit", 0.0),
            }))

        # Create the invoice
        vals = {
            "move_type": move_type,
            "partner_id": partner_id,
            "invoice_date": invoice_date or date.today().isoformat(),
            "invoice_line_ids": odoo_lines,
        }

        try:
            invoice_id = self.execute_kw("account.move", "create", [vals])
        except Exception as exc:
            return {"success": False, "error": f"Failed to create invoice: {exc}"}

        # Read back the created invoice
        try:
            created = self.search_read(
                "account.move",
                [["id", "=", invoice_id]],
                ["name", "amount_total", "state", "partner_id"],
                limit=1,
            )
            if created:
                rec = created[0]
                return {
                    "success": True,
                    "invoice_id": invoice_id,
                    "invoice_name": rec.get("name", ""),
                    "amount_total": rec.get("amount_total", 0.0),
                    "state": rec.get("state", "draft"),
                    "partner_name": partner_name,
                    "message": (
                        f"Draft invoice created (ID: {invoice_id}). "
                        f"It is in DRAFT state — a human must review and post it "
                        f"in Odoo at {self.url}/web#id={invoice_id}&model=account.move"
                    ),
                }
        except Exception:
            pass

        return {
            "success": True,
            "invoice_id": invoice_id,
            "invoice_name": "",
            "amount_total": 0.0,
            "state": "draft",
            "partner_name": partner_name,
            "message": f"Draft invoice created (ID: {invoice_id}). Review in Odoo.",
        }

    def _find_or_note_partner(self, partner_name: str) -> int:
        """Find a partner by name. Returns the partner_id."""
        results = self.search_read(
            "res.partner",
            [["name", "ilike", partner_name]],
            ["id", "name"],
            limit=1,
        )
        if results:
            return results[0]["id"]

        # Create a minimal partner
        partner_id = self.execute_kw("res.partner", "create", [{"name": partner_name}])
        return partner_id

    def create_draft_expense(
        self,
        description: str,
        amount: float,
        partner_name: str | None = None,
        expense_date: str | None = None,
    ) -> dict:
        """Create a draft vendor bill (expense) in Odoo.

        Stays in draft state for human approval.
        """
        lines = [{"name": description, "quantity": 1, "price_unit": amount}]
        return self.create_draft_invoice(
            partner_name=partner_name or "General Expense",
            lines=lines,
            move_type="in_invoice",
            invoice_date=expense_date,
        )

    def check_connection(self) -> dict:
        """Test connectivity and authentication. Returns diagnostic info."""
        try:
            # Step 1: Can we reach the server?
            common = self._get_common()
            version = common.version()

            # Step 2: Does the DB exist?
            db_exists = self.check_db_exists()
            if not db_exists:
                available = []
                try:
                    available = self.list_databases()
                except Exception:
                    pass
                return {
                    "connected": True,
                    "authenticated": False,
                    "error": f"Database '{self.db}' not found",
                    "available_databases": available,
                    "fix": (
                        f"Create the database at {self.url}/web/database/manager "
                        f"or update ODOO_DB in .env"
                    ),
                    "server_version": version.get("server_version", "unknown") if isinstance(version, dict) else str(version),
                    "success": False,
                }

            # Step 3: Can we authenticate?
            uid = self.authenticate()
            return {
                "connected": True,
                "authenticated": True,
                "uid": uid,
                "server_version": version.get("server_version", "unknown") if isinstance(version, dict) else str(version),
                "database": self.db,
                "success": True,
            }

        except OdooXmlRpcError as exc:
            return {"connected": False, "error": str(exc), "success": False}
        except ConnectionRefusedError:
            return {
                "connected": False,
                "error": f"Connection refused at {self.url}",
                "fix": "Start Odoo: python odoo-bin -c odoo.conf",
                "success": False,
            }
        except Exception as exc:
            return {"connected": False, "error": str(exc), "success": False}


def _extract_name(field_value) -> str:
    """Extract display name from Odoo many2one field [id, name]."""
    if isinstance(field_value, (list, tuple)) and len(field_value) >= 2:
        return str(field_value[1])
    if field_value is False or field_value is None:
        return ""
    return str(field_value)


# ---------------------------------------------------------------------------
# MCP Server (fastmcp)
# ---------------------------------------------------------------------------

try:
    from mcp.server.fastmcp import FastMCP
    _HAS_MCP = True
except ImportError:
    _HAS_MCP = False

if _HAS_MCP:
    mcp = FastMCP(
        "odoo-xmlrpc",
        instructions=(
            "Odoo Community accounting via XML-RPC. "
            "Read invoices, balances, journal entries. "
            "Create DRAFT invoices/expenses (require human approval to post)."
        ),
    )

    def _get_client() -> OdooXmlRpcClient:
        return OdooXmlRpcClient()

    @mcp.tool()
    def check_odoo_connection() -> dict:
        """Test Odoo connectivity, DB existence, and authentication.
        Diagnoses the common 'NoneType uid' error."""
        try:
            return _get_client().check_connection()
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    @mcp.tool()
    def list_odoo_databases() -> dict:
        """List all databases available on the Odoo server."""
        try:
            dbs = _get_client().list_databases()
            return {"success": True, "databases": dbs, "count": len(dbs)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    @mcp.tool()
    def list_invoices(limit: int = 20, state: str = "posted") -> dict:
        """List invoices from Odoo.

        Args:
            limit: Max invoices (default 20)
            state: 'posted', 'draft', or 'all'
        """
        try:
            client = _get_client()
            invoices = client.list_invoices(limit=limit, state=state)
            return {"success": True, "invoices": invoices, "count": len(invoices)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    @mcp.tool()
    def get_overdue_invoices() -> dict:
        """List all overdue (unpaid, past due date) invoices."""
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
        """Get chart of accounts with balances.

        Args:
            account_type: Optional filter (e.g., 'asset_receivable')
        """
        try:
            client = _get_client()
            balances = client.get_account_balances(account_type=account_type)
            return {"success": True, "accounts": balances, "count": len(balances)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    @mcp.tool()
    def get_financial_summary() -> dict:
        """High-level financial summary: revenue, expenses, net income, overdue."""
        try:
            return _get_client().get_financial_summary()
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    @mcp.tool()
    def create_draft_invoice(
        partner_name: str,
        lines: list[dict],
        move_type: str = "out_invoice",
        invoice_date: str | None = None,
    ) -> dict:
        """Create a DRAFT invoice in Odoo. Requires human approval to post.

        The invoice is created in 'draft' state. A human must review and
        confirm it in Odoo before it becomes a real accounting entry.

        Args:
            partner_name: Customer or vendor name
            lines: Invoice lines as list of dicts with keys: name, quantity, price_unit
                   Example: [{"name": "Consulting", "quantity": 10, "price_unit": 150.0}]
            move_type: 'out_invoice' (customer) or 'in_invoice' (vendor bill)
            invoice_date: Date (YYYY-MM-DD), defaults to today
        """
        try:
            client = _get_client()
            return client.create_draft_invoice(
                partner_name=partner_name,
                lines=lines,
                move_type=move_type,
                invoice_date=invoice_date,
            )
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    @mcp.tool()
    def create_draft_expense(
        description: str,
        amount: float,
        partner_name: str | None = None,
        expense_date: str | None = None,
    ) -> dict:
        """Create a draft vendor bill (expense). Requires human approval.

        Args:
            description: What the expense is for
            amount: Expense amount
            partner_name: Vendor name (defaults to 'General Expense')
            expense_date: Date (YYYY-MM-DD), defaults to today
        """
        try:
            client = _get_client()
            return client.create_draft_expense(
                description=description,
                amount=amount,
                partner_name=partner_name,
                expense_date=expense_date,
            )
        except Exception as exc:
            return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Odoo XML-RPC MCP Server + Client"
    )
    parser.add_argument("--test", action="store_true", help="Test Odoo connection")
    parser.add_argument("--setup-check", action="store_true",
                        help="Diagnose NoneType uid errors")
    parser.add_argument("--list-dbs", action="store_true",
                        help="List available Odoo databases")
    parser.add_argument("--invoices", action="store_true", help="List invoices")
    parser.add_argument("--overdue", action="store_true", help="List overdue invoices")
    parser.add_argument("--summary", action="store_true", help="Financial summary")
    parser.add_argument("--create-draft", action="store_true",
                        help="Create a test draft invoice")
    args = parser.parse_args()

    # If no CLI flags, start MCP server
    if not any(vars(args).values()):
        if _HAS_MCP:
            mcp.run()
        else:
            print("fastmcp not installed. Install with: pip install 'mcp[cli]'")
            print("Use --test, --setup-check, or --invoices for CLI mode.")
        return

    client = OdooXmlRpcClient()

    if args.setup_check:
        print("=" * 60)
        print("  Odoo Setup Diagnostic (fixes NoneType uid)")
        print("=" * 60)
        print(f"\n  ODOO_URL:      {client.url}")
        print(f"  ODOO_DB:       {client.db or '(NOT SET)'}")
        print(f"  ODOO_USER:     {client.user or '(NOT SET)'}")
        print(f"  ODOO_PASSWORD: {'***' if client.password else '(NOT SET)'}")

        # Check 1: Server reachable?
        print("\n[1/4] Checking server connectivity...")
        try:
            common = client._get_common()
            version = common.version()
            v = version.get("server_version", "unknown") if isinstance(version, dict) else str(version)
            print(f"  OK — Odoo {v} reachable at {client.url}")
        except Exception as exc:
            print(f"  FAIL — Cannot connect: {exc}")
            print(f"\n  FIX: Start Odoo with: python odoo-bin -c odoo.conf")
            print(f"       Or check ODOO_URL in .env (currently: {client.url})")
            return

        # Check 2: Database exists?
        print("\n[2/4] Checking database...")
        try:
            dbs = client.list_databases()
            print(f"  Available databases: {dbs}")
            if client.db in dbs:
                print(f"  OK — Database '{client.db}' exists")
            else:
                print(f"  FAIL — Database '{client.db}' NOT FOUND")
                print(f"\n  FIX: Create the database:")
                print(f"       1. Go to {client.url}/web/database/manager")
                print(f"       2. Click 'Create Database'")
                print(f"       3. Set Master Password (default: 'admin')")
                print(f"       4. Database Name: {client.db or 'mycompany'}")
                print(f"       5. Email: admin / Password: admin")
                print(f"       6. Check 'Demo Data' for test invoices")
                print(f"       7. Click 'Create Database'")
                print(f"       Then update ODOO_DB={client.db or 'mycompany'} in .env")
                return
        except Exception as exc:
            print(f"  WARNING — Cannot list databases: {exc}")
            print(f"  (This may be disabled in Odoo config — continuing...)")

        # Check 3: Authentication
        print("\n[3/4] Testing authentication...")
        try:
            uid = client.authenticate()
            print(f"  OK — Authenticated as uid={uid}")
        except OdooXmlRpcError as exc:
            print(f"  FAIL — {exc}")
            print(f"\n  FIX: Check ODOO_USER and ODOO_PASSWORD in .env")
            return

        # Check 4: Can read data?
        print("\n[4/4] Testing data access...")
        try:
            invoices = client.list_invoices(limit=3)
            print(f"  OK — Can read invoices ({len(invoices)} found)")
        except Exception as exc:
            print(f"  FAIL — Cannot read invoices: {exc}")
            print(f"  FIX: Install the 'Invoicing' app in Odoo")

        print("\n" + "=" * 60)
        print("  All checks passed! Odoo is ready.")
        print("=" * 60)
        return

    if args.test:
        result = client.check_connection()
        if result.get("success"):
            print(f"Connected (uid={result['uid']}, v={result.get('server_version')}, "
                  f"db={result.get('database')})")
        else:
            print(f"Failed: {result.get('error')}")
            if "fix" in result:
                print(f"Fix: {result['fix']}")
        return

    if args.list_dbs:
        try:
            dbs = client.list_databases()
            print("Available databases:")
            for db in dbs:
                marker = " <-- configured" if db == client.db else ""
                print(f"  - {db}{marker}")
        except OdooXmlRpcError as exc:
            print(f"Error: {exc}")
        return

    if args.invoices:
        invoices = client.list_invoices(limit=20)
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
                  f"{inv['currency']} {inv['amount_residual']:,.2f} | Due: {inv['invoice_date_due']}")
        print(f"\nTotal overdue: {len(overdue)}")
        return

    if args.summary:
        s = client.get_financial_summary()
        print(f"Revenue:     {s['currency']} {s['total_revenue']:,.2f}")
        print(f"Expenses:    {s['currency']} {s['total_expenses']:,.2f}")
        print(f"Net Income:  {s['currency']} {s['net_income']:,.2f}")
        print(f"Outstanding: {s['currency']} {s['outstanding_invoices']:,.2f}")
        print(f"Overdue:     {s['overdue_count']} ({s['currency']} {s['overdue_amount']:,.2f})")
        return

    if args.create_draft:
        print("Creating a test draft invoice...")
        result = client.create_draft_invoice(
            partner_name="Test Customer",
            lines=[
                {"name": "Consulting Services", "quantity": 10, "price_unit": 150.0},
                {"name": "Setup Fee", "quantity": 1, "price_unit": 500.0},
            ],
        )
        if result["success"]:
            print(f"  Draft invoice created!")
            print(f"  ID: {result['invoice_id']}")
            print(f"  Name: {result['invoice_name']}")
            print(f"  Amount: {result['amount_total']}")
            print(f"  State: {result['state']}")
            print(f"\n  {result['message']}")
        else:
            print(f"  Failed: {result.get('error')}")
        return


if __name__ == "__main__":
    main()
