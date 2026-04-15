"""FastAPI server for the AI Employee Dashboard.

Exposes vault status, Odoo data, task pipeline, and briefings
as JSON endpoints for the Next.js frontend.

Usage:
    python scripts/api_server.py              # Start on port 5000
    python scripts/api_server.py --port 8080  # Custom port
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger

load_dotenv()

app = FastAPI(title="AI Employee API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

VAULT = Path(os.getenv("VAULT_PATH", str(Path(__file__).parent.parent)))
SCRIPTS = Path(__file__).parent

# Track orchestrator subprocess
_orchestrator_proc: subprocess.Popen | None = None


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


# ---------------------------------------------------------------------------
# Pydantic models for POST endpoints
# ---------------------------------------------------------------------------

class SocialPostRequest(BaseModel):
    platform: str  # facebook, twitter, linkedin, instagram
    content: str
    mode: str = "draft"  # draft or publish

class EmailRequest(BaseModel):
    to: str
    subject: str
    body: str

class WhatsAppRequest(BaseModel):
    phone: str
    message: str

class ApprovalAction(BaseModel):
    filename: str
    action: str  # approve or reject


# ---------------------------------------------------------------------------
# Social Media Posting
# ---------------------------------------------------------------------------

@app.post("/api/social/post")
def api_social_post(req: SocialPostRequest):
    """Create a social media draft or publish directly."""
    platform = req.platform.upper()
    ts = datetime.now().strftime("%H%M%S")
    slug = re.sub(r'[^a-zA-Z0-9]', '-', req.content[:50]).strip('-')

    if req.mode == "draft":
        folder = VAULT / "Pending_Approval"
        folder.mkdir(exist_ok=True)
        filename = f"{platform}_{ts}_{slug}.md"
        filepath = folder / filename
        filepath.write_text(
            f"---\ntype: social_post\nplatform: {req.platform}\nstatus: pending\ncreated: {datetime.now(timezone.utc).isoformat()}\n---\n\n{req.content}\n",
            encoding="utf-8",
        )
        logger = AuditLogger(VAULT)
        logger.log("social_draft", f"dashboard", filename, "success")
        return {"success": True, "mode": "draft", "filename": filename, "message": f"Draft saved to Pending_Approval/"}
    else:
        # Direct publish via social_poster.py
        try:
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "social_poster.py"),
                 "--draft", req.content, "--platform", req.platform],
                capture_output=True, text=True, timeout=30, cwd=str(VAULT),
            )
            logger = AuditLogger(VAULT)
            logger.log("social_publish", "dashboard", req.platform, "success" if result.returncode == 0 else "error")
            return {
                "success": result.returncode == 0,
                "mode": "publish",
                "output": result.stdout[-500:] if result.stdout else "",
                "error": result.stderr[-300:] if result.stderr else "",
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Email Sending
# ---------------------------------------------------------------------------

@app.post("/api/email/send")
def api_email_send(req: EmailRequest):
    """Send email via Gmail API or create task file."""
    try:
        from mcp_email_server import send_email
        result = send_email(req.to, req.subject, req.body)
        logger = AuditLogger(VAULT)
        logger.log("email_send", "dashboard", req.to, "success")
        return {"success": True, "message": f"Email sent to {req.to}"}
    except ImportError:
        # Fallback: create email task in Needs_Action
        folder = VAULT / "Needs_Action"
        folder.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%H%M%S")
        filename = f"EMAIL_SEND_{ts}_{re.sub(r'[^a-zA-Z0-9]', '-', req.to[:30])}.md"
        filepath = folder / filename
        filepath.write_text(
            f"---\ntype: email_send\nto: {req.to}\nsubject: {req.subject}\nstatus: pending\ncreated: {datetime.now(timezone.utc).isoformat()}\n---\n\n{req.body}\n",
            encoding="utf-8",
        )
        logger = AuditLogger(VAULT)
        logger.log("email_queued", "dashboard", filename, "success")
        return {"success": True, "message": f"Email queued as task: {filename}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# WhatsApp Sending
# ---------------------------------------------------------------------------

@app.post("/api/whatsapp/send")
def api_whatsapp_send(req: WhatsAppRequest):
    """Send WhatsApp message or create task file."""
    folder = VAULT / "Needs_Action"
    folder.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%H%M%S")
    phone_slug = re.sub(r'[^0-9]', '', req.phone)
    filename = f"WHATSAPP_SEND_{ts}_{phone_slug}.md"
    filepath = folder / filename
    filepath.write_text(
        f"---\ntype: whatsapp_send\nphone: {req.phone}\nstatus: pending\ncreated: {datetime.now(timezone.utc).isoformat()}\n---\n\n{req.message}\n",
        encoding="utf-8",
    )
    logger = AuditLogger(VAULT)
    logger.log("whatsapp_queued", "dashboard", filename, "success")
    return {"success": True, "message": f"WhatsApp message queued: {filename}"}


# ---------------------------------------------------------------------------
# Approval Actions
# ---------------------------------------------------------------------------

@app.post("/api/approvals/action")
def api_approval_action(req: ApprovalAction):
    """Approve or reject a pending item."""
    src = VAULT / "Pending_Approval" / req.filename
    if not src.exists():
        return {"success": False, "error": "File not found"}

    if req.action == "approve":
        dest_folder = VAULT / "Approved"
        dest_folder.mkdir(exist_ok=True)
        dest = dest_folder / req.filename
        src.rename(dest)
        logger = AuditLogger(VAULT)
        logger.log("approved", "dashboard", req.filename, "success")
        return {"success": True, "message": f"Approved: {req.filename}"}
    elif req.action == "reject":
        dest_folder = VAULT / "Archive"
        dest_folder.mkdir(exist_ok=True)
        dest = dest_folder / req.filename
        src.rename(dest)
        logger = AuditLogger(VAULT)
        logger.log("rejected", "dashboard", req.filename, "success")
        return {"success": True, "message": f"Rejected: {req.filename}"}
    else:
        return {"success": False, "error": "Invalid action. Use 'approve' or 'reject'."}


# ---------------------------------------------------------------------------
# Error Recovery & System Health
# ---------------------------------------------------------------------------

@app.get("/api/errors")
def api_errors():
    """Get error recovery status and recent errors from logs."""
    errors = []
    log_dir = VAULT / "Logs"
    if log_dir.exists():
        for logfile in sorted(log_dir.glob("*.audit.jsonl"), reverse=True)[:3]:
            try:
                lines = logfile.read_text(encoding="utf-8", errors="replace").strip().splitlines()
                for line in reversed(lines[-100:]):
                    try:
                        entry = json.loads(line)
                        if entry.get("outcome") in ("error", "failure", "failed"):
                            errors.append(entry)
                    except json.JSONDecodeError:
                        pass
            except Exception:
                pass

    # Check health tracker state if available
    health = {}
    try:
        from error_recovery import HealthTracker
        tracker = HealthTracker()
        health = {
            svc: {"status": s.status, "failures": s.consecutive_failures}
            for svc, s in tracker._services.items()
        }
    except Exception:
        pass

    return {
        "recent_errors": errors[:20],
        "error_count": len(errors),
        "health": health,
    }


# ---------------------------------------------------------------------------
# Orchestrator Control
# ---------------------------------------------------------------------------

@app.post("/api/orchestrator/start")
def api_orchestrator_start():
    """Start the orchestrator."""
    global _orchestrator_proc
    if _orchestrator_proc and _orchestrator_proc.poll() is None:
        return {"success": True, "message": "Orchestrator already running", "pid": _orchestrator_proc.pid}

    try:
        _orchestrator_proc = subprocess.Popen(
            [sys.executable, str(SCRIPTS / "orchestrator.py"), "--auto-restart"],
            cwd=str(VAULT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        logger = AuditLogger(VAULT)
        logger.log("orchestrator_start", "dashboard", str(_orchestrator_proc.pid), "success")
        return {"success": True, "message": "Orchestrator started", "pid": _orchestrator_proc.pid}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@app.post("/api/orchestrator/stop")
def api_orchestrator_stop():
    """Stop the orchestrator."""
    global _orchestrator_proc
    if not _orchestrator_proc or _orchestrator_proc.poll() is not None:
        _orchestrator_proc = None
        return {"success": True, "message": "Orchestrator not running"}

    try:
        _orchestrator_proc.terminate()
        _orchestrator_proc.wait(timeout=10)
        pid = _orchestrator_proc.pid
        _orchestrator_proc = None
        logger = AuditLogger(VAULT)
        logger.log("orchestrator_stop", "dashboard", str(pid), "success")
        return {"success": True, "message": "Orchestrator stopped"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@app.get("/api/orchestrator/status")
def api_orchestrator_status():
    """Get orchestrator status."""
    global _orchestrator_proc
    running = _orchestrator_proc is not None and _orchestrator_proc.poll() is None
    return {
        "running": running,
        "pid": _orchestrator_proc.pid if running else None,
    }


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
