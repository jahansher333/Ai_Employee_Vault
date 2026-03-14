"""FastAPI server for the AI Employee Dashboard.

Exposes vault status, Odoo data, task pipeline, and briefings
as JSON endpoints for the Next.js frontend.

Usage:
    python scripts/api_server.py              # Start on port 5000
    python scripts/api_server.py --port 8080  # Custom port
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger

load_dotenv()

app = FastAPI(title="AI Employee API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

VAULT = Path(os.getenv("VAULT_PATH", str(Path(__file__).parent.parent)))


def _count_md(folder: Path) -> int:
    return len(list(folder.glob("*.md"))) if folder.exists() else 0


def _read_frontmatter(filepath: Path) -> dict:
    """Parse YAML frontmatter from a .md file."""
    content = filepath.read_text(encoding="utf-8", errors="replace")
    fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not fm_match:
        return {"_body": content[:200]}
    fm = {}
    for line in fm_match.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip().strip('"').strip("'")
    fm["_body"] = content[fm_match.end():fm_match.end() + 300]
    return fm


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.get("/api/status")
def api_status():
    """Vault status overview."""
    return {
        "needs_action": _count_md(VAULT / "Needs_Action"),
        "plans": _count_md(VAULT / "Plans"),
        "pending_approval": _count_md(VAULT / "Pending_Approval"),
        "approved": _count_md(VAULT / "Approved"),
        "done": _count_md(VAULT / "Done"),
        "archive": _count_md(VAULT / "Archive"),
        "briefings": _count_md(VAULT / "Briefings"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/tasks")
def api_tasks(limit: int = Query(50)):
    """List tasks from Needs_Action/."""
    folder = VAULT / "Needs_Action"
    tasks = []
    if folder.exists():
        for f in sorted(folder.glob("*.md"))[:limit]:
            fm = _read_frontmatter(f)
            tasks.append({
                "filename": f.name,
                "type": fm.get("type", "task"),
                "priority": fm.get("priority", "medium"),
                "status": fm.get("status", "new"),
                "preview": fm.get("_body", "")[:150],
                "modified": datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat(),
            })
    return {"tasks": tasks, "count": len(tasks)}


@app.get("/api/approvals")
def api_approvals():
    """List items in Pending_Approval/."""
    folder = VAULT / "Pending_Approval"
    items = []
    if folder.exists():
        for f in sorted(folder.glob("*.md")):
            fm = _read_frontmatter(f)
            items.append({
                "filename": f.name,
                "type": fm.get("type", "unknown"),
                "status": fm.get("status", "pending"),
                "preview": fm.get("_body", "")[:150],
            })
    return {"approvals": items, "count": len(items)}


@app.get("/api/done")
def api_done(limit: int = Query(20)):
    """List completed items."""
    folder = VAULT / "Done"
    items = []
    if folder.exists():
        for f in sorted(folder.glob("*.md"), reverse=True)[:limit]:
            fm = _read_frontmatter(f)
            items.append({
                "filename": f.name,
                "type": fm.get("type", "task"),
                "completed_at": fm.get("completed_at", ""),
            })
    return {"done": items, "count": len(items)}


@app.get("/api/financial")
def api_financial():
    """Financial summary from Odoo + CSV analysis."""
    result: dict = {"source": "none", "success": False}

    try:
        from odoo_client import OdooClient
        client = OdooClient()
        summary = client.get_financial_summary()
        overdue = client.get_overdue_invoices()
        result = {
            "source": "odoo",
            "success": True,
            **summary,
            "overdue_invoices": [
                {"name": i["name"], "partner": i["partner_name"],
                 "amount": i["amount_residual"], "due": i["invoice_date_due"]}
                for i in overdue[:10]
            ],
        }
    except Exception:
        try:
            from data_analyzer import analyze_csv_files
            report = analyze_csv_files(VAULT)
            if report:
                result = {"source": "csv", "success": True, "report": report[:2000]}
        except Exception:
            pass

    return result


@app.get("/api/inventory")
def api_inventory():
    """Inventory data from Odoo."""
    try:
        from odoo_client import OdooClient
        client = OdooClient()
        summary = client.get_inventory_summary()
        products = client.list_products(limit=20)
        low_stock = client.get_low_stock_products()
        return {
            "success": True,
            "summary": summary,
            "products": products[:20],
            "low_stock": low_stock[:10],
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@app.get("/api/social")
def api_social():
    """Social media post summary."""
    platforms = {}
    for prefix in ["FACEBOOK", "INSTAGRAM", "TWITTER", "LINKEDIN"]:
        drafts = len(list((VAULT / "Pending_Approval").glob(f"{prefix}_*.md"))) if (VAULT / "Pending_Approval").exists() else 0
        posted = len(list((VAULT / "Done").glob(f"{prefix}_*.md"))) if (VAULT / "Done").exists() else 0
        platforms[prefix.lower()] = {"drafts": drafts, "posted": posted}
    return {"platforms": platforms}


@app.get("/api/briefings")
def api_briefings():
    """List available briefings."""
    folder = VAULT / "Briefings"
    briefings = []
    if folder.exists():
        for f in sorted(folder.glob("*.md"), reverse=True)[:10]:
            fm = _read_frontmatter(f)
            briefings.append({
                "filename": f.name,
                "date": fm.get("date", ""),
                "status": fm.get("status", "new"),
            })
    return {"briefings": briefings}


@app.get("/api/audit")
def api_audit():
    """Recent audit log entries."""
    logger = AuditLogger(VAULT)
    entries = logger.read_log()[-20:]
    return {"entries": entries, "count": len(entries)}


@app.get("/api/health")
def api_health():
    """API health check."""
    return {"status": "ok", "vault": str(VAULT), "timestamp": datetime.now(timezone.utc).isoformat()}


def main():
    import uvicorn
    parser = argparse.ArgumentParser(description="AI Employee API Server")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    print(f"AI Employee API starting on http://{args.host}:{args.port}")
    print(f"Vault: {VAULT}")
    print(f"Docs: http://{args.host}:{args.port}/docs")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
