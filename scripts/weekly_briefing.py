"""Weekly CEO Briefing — generates a structured Monday briefing report.

Gold Tier: Enhanced briefing with Odoo financial data, multi-platform social
activity summary, week-over-week comparison, and system health status.

Usage:
    python scripts/weekly_briefing.py                    # Generate briefing now
    python scripts/weekly_briefing.py --schedule         # Run scheduler loop (Sunday 8 PM PKT)
    python scripts/weekly_briefing.py --vault-path /path # Custom vault path
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger

# Pakistan Standard Time is UTC+5
PKT = timezone(timedelta(hours=5))


# ---------------------------------------------------------------------------
# Data collection helpers
# ---------------------------------------------------------------------------

def collect_financial_summary(vault_path: Path) -> dict:
    """Collect financial summary from data_analyzer if CSV data exists.

    Returns a dict with revenue, expenses, net_income, anomalies, or
    empty values if no data is available.
    """
    try:
        from data_analyzer import run_analysis, HAS_PANDAS
    except ImportError:
        return {"available": False, "reason": "data_analyzer not importable"}

    if not HAS_PANDAS:
        return {"available": False, "reason": "pandas not installed"}

    accounting = vault_path / "Accounting"
    if not accounting.exists() or not list(accounting.glob("*.csv")):
        return {"available": False, "reason": "No CSV files in Accounting/"}

    summary = run_analysis(vault_path)
    if not summary:
        return {"available": False, "reason": "Analysis returned empty"}

    return {
        "available": True,
        "total_revenue": summary.get("total_revenue", 0),
        "total_expenses": summary.get("total_expenses", 0),
        "net_income": summary.get("net_income", 0),
        "anomalies": summary.get("anomalies", []),
        "files_analyzed": summary.get("files_analyzed", []),
        "monthly_breakdown": summary.get("monthly_breakdown", []),
    }


def collect_task_stats(vault_path: Path) -> dict:
    """Count tasks across all vault folders."""
    def count_md(folder: Path) -> int:
        if not folder.exists():
            return 0
        return len(list(folder.glob("*.md")))

    needs_action = count_md(vault_path / "Needs_Action")
    pending = count_md(vault_path / "Pending_Approval")
    plans = count_md(vault_path / "Plans")
    approved = count_md(vault_path / "Approved")
    done = count_md(vault_path / "Done")

    return {
        "needs_action": needs_action,
        "pending_approval": pending,
        "active_plans": plans,
        "approved": approved,
        "done": done,
        "total_open": needs_action + pending + plans,
    }


def collect_bottlenecks(vault_path: Path, logger: AuditLogger) -> list[dict]:
    """Identify bottlenecks: old pending tasks, stale plans, error patterns."""
    bottlenecks: list[dict] = []
    now = datetime.now(timezone.utc)

    # 1. Stale Needs_Action items (>48 hours old)
    needs_action = vault_path / "Needs_Action"
    if needs_action.exists():
        for f in needs_action.glob("*.md"):
            age_hours = (now.timestamp() - f.stat().st_mtime) / 3600
            if age_hours > 48:
                bottlenecks.append({
                    "type": "stale_task",
                    "file": f.name,
                    "age_hours": round(age_hours),
                    "description": f"Task pending for {round(age_hours)}h without processing",
                })

    # 2. Pending approvals waiting >24 hours
    pending = vault_path / "Pending_Approval"
    if pending.exists():
        for f in pending.glob("*.md"):
            age_hours = (now.timestamp() - f.stat().st_mtime) / 3600
            if age_hours > 24:
                bottlenecks.append({
                    "type": "stale_approval",
                    "file": f.name,
                    "age_hours": round(age_hours),
                    "description": f"Approval pending for {round(age_hours)}h",
                })

    # 3. Plans stuck in awaiting_approval
    plans_dir = vault_path / "Plans"
    if plans_dir.exists():
        for f in plans_dir.glob("PLAN_*.md"):
            try:
                content = f.read_text(encoding="utf-8")
                if "status: awaiting_approval" in content:
                    age_hours = (now.timestamp() - f.stat().st_mtime) / 3600
                    bottlenecks.append({
                        "type": "blocked_plan",
                        "file": f.name,
                        "age_hours": round(age_hours),
                        "description": f"Plan blocked awaiting approval for {round(age_hours)}h",
                    })
            except Exception:
                continue

    # 4. Recent errors from audit log
    entries = logger.read_log()
    error_count = sum(1 for e in entries if e.get("outcome") == "error")
    if error_count > 0:
        bottlenecks.append({
            "type": "errors",
            "file": "audit_log",
            "age_hours": 0,
            "description": f"{error_count} error(s) logged today",
        })

    return bottlenecks


def collect_recent_activity(logger: AuditLogger, limit: int = 15) -> list[dict]:
    """Get recent audit log entries for the briefing."""
    entries = logger.read_log()
    return entries[-limit:] if len(entries) > limit else entries


# ---------------------------------------------------------------------------
# Gold Tier data collectors
# ---------------------------------------------------------------------------

def collect_odoo_financials() -> dict:
    """Pull financial data from Odoo. Falls back gracefully if unavailable."""
    try:
        from odoo_client import OdooClient, OdooConnectionError
    except ImportError:
        return {"available": False, "source": "odoo", "reason": "odoo_client not importable"}

    try:
        client = OdooClient()
        summary = client.get_financial_summary()
        overdue = client.get_overdue_invoices()
        return {
            "available": True,
            "source": "odoo",
            "total_revenue": summary.get("total_revenue", 0),
            "total_expenses": summary.get("total_expenses", 0),
            "net_income": summary.get("net_income", 0),
            "outstanding": summary.get("outstanding_invoices", 0),
            "overdue_count": summary.get("overdue_count", 0),
            "overdue_amount": summary.get("overdue_amount", 0),
            "currency": summary.get("currency", "USD"),
            "overdue_invoices": overdue[:10],  # Top 10
        }
    except Exception as exc:
        return {"available": False, "source": "odoo", "reason": str(exc)}


def collect_social_activity(vault_path: Path) -> dict:
    """Collect social media activity across all platforms."""
    try:
        from social_poster import get_social_activity_summary
    except ImportError:
        return {"available": False, "reason": "social_poster not importable"}

    try:
        summary = get_social_activity_summary(vault_path)
        return {
            "available": True,
            "platforms": summary.get("summary", {}),
            "total_posted": summary.get("total_posted", 0),
            "total_pending": summary.get("total_pending", 0),
        }
    except Exception as exc:
        return {"available": False, "reason": str(exc)}


def collect_week_over_week(vault_path: Path) -> dict:
    """Compare current metrics against the most recent previous briefing."""
    briefings_dir = vault_path / "Briefings"
    if not briefings_dir.exists():
        return {"available": False, "reason": "No Briefings/ directory"}

    files = sorted(briefings_dir.glob("*_Briefing*.md"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    if len(files) < 2:
        return {"available": False, "reason": "Need at least 2 briefings for comparison"}

    # Parse previous briefing for key metrics
    prev = files[1]  # Second most recent
    try:
        content = prev.read_text(encoding="utf-8")
        prev_tasks = _extract_metric(content, r"Needs_Action\s*\|\s*(\d+)")
        prev_done = _extract_metric(content, r"Done\s*\|\s*(\d+)")
        prev_pending = _extract_metric(content, r"Pending Approval\s*\|\s*(\d+)")

        return {
            "available": True,
            "previous_file": prev.name,
            "prev_needs_action": prev_tasks,
            "prev_done": prev_done,
            "prev_pending": prev_pending,
        }
    except Exception:
        return {"available": False, "reason": "Could not parse previous briefing"}


def _extract_metric(content: str, pattern: str) -> int:
    """Extract a numeric metric from briefing content."""
    match = re.search(pattern, content)
    return int(match.group(1)) if match else 0


def collect_health_status() -> dict:
    """Collect service health from HealthTracker if available."""
    try:
        from error_recovery import HealthTracker
    except ImportError:
        return {"available": False, "reason": "error_recovery not importable"}

    tracker = HealthTracker()
    return {
        "available": True,
        "services": tracker.get_summary(),
    }


# ---------------------------------------------------------------------------
# Briefing generation
# ---------------------------------------------------------------------------

def _fmt_currency(value: float) -> str:
    """Format a number as currency."""
    return f"${value:,.2f}"


def generate_briefing(vault_path: Path, logger: AuditLogger) -> tuple[str, Path]:
    """Generate the Monday briefing markdown and write it to Briefings/.

    Returns (markdown_content, file_path).
    """
    now_pkt = datetime.now(PKT)
    # The briefing is for Monday (next day if run Sunday, or today)
    monday = now_pkt + timedelta(days=(7 - now_pkt.weekday()) % 7)
    if monday.date() == now_pkt.date() and now_pkt.weekday() != 0:
        monday = now_pkt + timedelta(days=(7 - now_pkt.weekday()))
    briefing_date = monday.strftime("%Y-%m-%d")
    generated_at = now_pkt.strftime("%Y-%m-%d %H:%M PKT")

    # Collect all data
    financials = collect_financial_summary(vault_path)
    tasks = collect_task_stats(vault_path)
    bottlenecks = collect_bottlenecks(vault_path, logger)
    recent = collect_recent_activity(logger)

    # Gold Tier data
    odoo = collect_odoo_financials()
    social = collect_social_activity(vault_path)
    wow = collect_week_over_week(vault_path)
    health = collect_health_status()

    # Build briefing markdown
    lines = [
        "---",
        "type: briefing",
        f"date: \"{briefing_date}\"",
        f"generated_at: \"{now_pkt.isoformat()}\"",
        "status: new",
        "priority: high",
        "---",
        "",
        f"# Monday Briefing — {briefing_date}",
        "",
        f"**Generated**: {generated_at}",
        f"**For**: CEO / Stakeholder Review",
        "",
    ]

    # --- Executive Summary ---
    lines.extend([
        "## Executive Summary",
        "",
    ])

    if odoo.get("available"):
        net = odoo["net_income"]
        trend = "positive" if net > 0 else "negative" if net < 0 else "neutral"
        lines.append(f"- **Financial (Odoo)**: Net income {odoo['currency']} {net:,.2f} ({trend} trend)")
        if odoo["overdue_count"] > 0:
            lines.append(f"- **Overdue**: {odoo['overdue_count']} invoice(s) totaling "
                         f"{odoo['currency']} {odoo['overdue_amount']:,.2f}")
    elif financials.get("available"):
        net = financials["net_income"]
        trend = "positive" if net > 0 else "negative" if net < 0 else "neutral"
        lines.append(f"- **Financial (CSV)**: Net income is {_fmt_currency(net)} ({trend} trend)")
    else:
        lines.append(f"- **Financial**: No financial data available ({financials.get('reason', 'unknown')})")

    lines.append(f"- **Open Items**: {tasks['total_open']} tasks require attention "
                 f"({tasks['needs_action']} pending, {tasks['pending_approval']} approvals, "
                 f"{tasks['active_plans']} active plans)")
    lines.append(f"- **Completed**: {tasks['done']} items in Done/")

    if social.get("available"):
        lines.append(f"- **Social**: {social['total_posted']} posts published, "
                     f"{social['total_pending']} pending")

    if bottlenecks:
        lines.append(f"- **Bottlenecks**: {len(bottlenecks)} issue(s) detected (see below)")
    else:
        lines.append("- **Bottlenecks**: None detected")

    lines.append("")

    # --- Financial Overview ---
    lines.extend([
        "## Financial Overview",
        "",
    ])

    if financials.get("available"):
        lines.extend([
            "| Metric | Amount |",
            "|--------|--------|",
            f"| Total Revenue | {_fmt_currency(financials['total_revenue'])} |",
            f"| Total Expenses | {_fmt_currency(financials['total_expenses'])} |",
            f"| **Net Income** | **{_fmt_currency(financials['net_income'])}** |",
            "",
        ])

        # Anomalies
        anomalies = financials.get("anomalies", [])
        if anomalies:
            lines.extend([
                f"### Anomalies ({len(anomalies)} detected)",
                "",
            ])
            for a in anomalies[:5]:
                lines.append(f"- **{a['description']}**: {_fmt_currency(abs(a['amount']))} "
                             f"({a['category']}, {a['ratio']}x above average)")
            lines.append("")

        # Monthly trend
        monthly = financials.get("monthly_breakdown", [])
        if monthly:
            lines.extend([
                "### Monthly Trend",
                "",
                "| Month | Revenue | Expenses | Net |",
                "|-------|---------|----------|-----|",
            ])
            for m in monthly[-3:]:  # Last 3 months
                lines.append(f"| {m['month']} | {_fmt_currency(m['revenue'])} "
                             f"| {_fmt_currency(m['expenses'])} | {_fmt_currency(m['net'])} |")
            lines.append("")
    else:
        lines.append(f"_No financial data available. {financials.get('reason', '')}_")
        lines.append("")

    # --- Task Pipeline ---
    lines.extend([
        "## Task Pipeline",
        "",
        "| Queue | Count | Action Needed |",
        "|-------|-------|---------------|",
        f"| Needs_Action | {tasks['needs_action']} | Process or delegate |",
        f"| Active Plans | {tasks['active_plans']} | Execute next steps |",
        f"| Pending Approval | {tasks['pending_approval']} | Review and approve/reject |",
        f"| Approved | {tasks['approved']} | Publish/execute |",
        f"| Done | {tasks['done']} | Archive |",
        "",
    ])

    # --- Bottlenecks ---
    lines.extend([
        "## Bottlenecks & Risks",
        "",
    ])

    if bottlenecks:
        lines.extend([
            "| Type | Item | Age | Issue |",
            "|------|------|-----|-------|",
        ])
        for b in bottlenecks:
            age_str = f"{b['age_hours']}h" if b["age_hours"] > 0 else "today"
            lines.append(f"| {b['type']} | {b['file'][:30]} | {age_str} | {b['description']} |")
        lines.append("")
    else:
        lines.append("No bottlenecks detected. All queues are flowing normally.")
        lines.append("")

    # --- Recommended Actions ---
    lines.extend([
        "## Recommended Actions for This Week",
        "",
    ])

    action_num = 1
    if tasks["pending_approval"] > 0:
        lines.append(f"{action_num}. **Review {tasks['pending_approval']} pending approval(s)** — "
                     "items blocked waiting for human decision")
        action_num += 1

    if tasks["needs_action"] > 5:
        lines.append(f"{action_num}. **Clear task backlog** — "
                     f"{tasks['needs_action']} items in Needs_Action/ queue")
        action_num += 1

    stale = [b for b in bottlenecks if b["type"] == "stale_task"]
    if stale:
        lines.append(f"{action_num}. **Address {len(stale)} stale task(s)** — "
                     "tasks waiting >48 hours without processing")
        action_num += 1

    if financials.get("anomalies"):
        lines.append(f"{action_num}. **Investigate {len(financials['anomalies'])} financial anomaly/anomalies** — "
                     "transactions exceeding 2x category average")
        action_num += 1

    if action_num == 1:
        lines.append("All systems nominal. No urgent actions required.")

    lines.append("")

    # --- Odoo Financial Summary (Gold Tier) ---
    if odoo.get("available"):
        lines.extend([
            "## Odoo Financial Summary",
            "",
            f"**Source**: Odoo ({odoo['currency']})",
            "",
            "| Metric | Amount |",
            "|--------|--------|",
            f"| Total Revenue | {odoo['currency']} {odoo['total_revenue']:,.2f} |",
            f"| Total Expenses | {odoo['currency']} {odoo['total_expenses']:,.2f} |",
            f"| **Net Income** | **{odoo['currency']} {odoo['net_income']:,.2f}** |",
            f"| Outstanding | {odoo['currency']} {odoo['outstanding']:,.2f} |",
            f"| Overdue | {odoo['currency']} {odoo['overdue_amount']:,.2f} ({odoo['overdue_count']} invoices) |",
            "",
        ])

        overdue_invoices = odoo.get("overdue_invoices", [])
        if overdue_invoices:
            lines.extend([
                "### Overdue Invoices",
                "",
                "| Invoice | Customer | Amount Due | Due Date |",
                "|---------|----------|------------|----------|",
            ])
            for inv in overdue_invoices[:10]:
                lines.append(
                    f"| {inv.get('name', '')} | {inv.get('partner_name', '')[:25]} "
                    f"| {odoo['currency']} {inv.get('amount_residual', 0):,.2f} "
                    f"| {inv.get('invoice_date_due', '')} |"
                )
            lines.append("")

    # --- Social Media Activity (Gold Tier) ---
    if social.get("available"):
        lines.extend([
            "## Social Media Activity",
            "",
            "| Platform | Drafts | Approved | Posted |",
            "|----------|--------|----------|--------|",
        ])
        for platform, counts in social.get("platforms", {}).items():
            lines.append(
                f"| {platform.title()} | {counts.get('drafts', 0)} "
                f"| {counts.get('approved', 0)} | {counts.get('posted', 0)} |"
            )
        lines.extend([
            "",
            f"**Total Posted**: {social['total_posted']} | **Pending**: {social['total_pending']}",
            "",
        ])

    # --- Week-over-Week Comparison (Gold Tier) ---
    if wow.get("available"):
        current_na = tasks["needs_action"]
        prev_na = wow.get("prev_needs_action", 0)
        current_done = tasks["done"]
        prev_done = wow.get("prev_done", 0)
        current_pa = tasks["pending_approval"]
        prev_pa = wow.get("prev_pending", 0)

        def _delta(curr: int, prev: int) -> str:
            diff = curr - prev
            if diff > 0:
                return f"+{diff}"
            return str(diff)

        lines.extend([
            "## Week-over-Week Comparison",
            "",
            f"_Compared to: {wow.get('previous_file', 'N/A')}_",
            "",
            "| Metric | This Week | Last Week | Change |",
            "|--------|-----------|-----------|--------|",
            f"| Needs Action | {current_na} | {prev_na} | {_delta(current_na, prev_na)} |",
            f"| Pending Approval | {current_pa} | {prev_pa} | {_delta(current_pa, prev_pa)} |",
            f"| Done | {current_done} | {prev_done} | {_delta(current_done, prev_done)} |",
            "",
        ])

    # --- System Health (Gold Tier) ---
    if health.get("available"):
        services = health.get("services", {})
        if services:
            lines.extend([
                "## System Health",
                "",
                "| Service | Status |",
                "|---------|--------|",
            ])
            for svc, status in services.items():
                icon = "operational" if status == "operational" else status
                lines.append(f"| {svc} | {icon} |")
            lines.append("")

    # --- Recent Activity ---
    lines.extend([
        "## Recent Activity (Last 15 Events)",
        "",
    ])

    if recent:
        lines.extend([
            "| Time | Action | File | Outcome |",
            "|------|--------|------|---------|",
        ])
        for e in reversed(recent[-10:]):
            ts = e.get("timestamp", "")
            t = ts.split("T")[1][:5] if "T" in ts else ts[:5]
            lines.append(f"| {t} | {e.get('action', '')} | "
                         f"{e.get('input_ref', '')[:25]} | {e.get('outcome', '')} |")
    else:
        lines.append("_No recent activity logged._")

    lines.append("")

    # --- Footer ---
    lines.extend([
        "---",
        "",
        f"*Generated by AI Employee Weekly Briefing — {generated_at}*",
        "",
    ])

    content = "\n".join(lines)

    # Write to Briefings/
    briefings_dir = vault_path / "Briefings"
    briefings_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{briefing_date}_Monday_Briefing.md"
    filepath = briefings_dir / filename

    # Avoid overwriting
    if filepath.exists():
        suffix = now_pkt.strftime("%H%M%S")
        filename = f"{briefing_date}_Monday_Briefing_{suffix}.md"
        filepath = briefings_dir / filename

    filepath.write_text(content, encoding="utf-8")

    logger.log(
        "briefing_generated", filename, "success",
        details={
            "date": briefing_date,
            "tasks_open": tasks["total_open"],
            "bottlenecks": len(bottlenecks),
            "financials_available": financials.get("available", False),
        },
    )

    return content, filepath


# ---------------------------------------------------------------------------
# Dashboard integration
# ---------------------------------------------------------------------------

def update_dashboard_briefings(vault_path: Path) -> None:
    """Add briefing info to Dashboard.md between markers."""
    dashboard = vault_path / "Dashboard.md"
    if not dashboard.exists():
        return

    content = dashboard.read_text(encoding="utf-8")
    start_marker = "<!-- START_BRIEFINGS -->"
    end_marker = "<!-- END_BRIEFINGS -->"

    # Build briefings table
    briefings_dir = vault_path / "Briefings"
    rows = []
    if briefings_dir.exists():
        for f in sorted(briefings_dir.glob("*_Briefing*.md"),
                        key=lambda p: p.stat().st_mtime, reverse=True)[:5]:
            fc = f.read_text(encoding="utf-8")
            date_match = re.search(r'date:\s*"?([^"\n]+)"?', fc)
            date_str = date_match.group(1).strip() if date_match else f.stem[:10]
            status_match = re.search(r"status:\s*(\w+)", fc)
            status = status_match.group(1) if status_match else "new"
            rows.append(f"| {f.name} | {date_str} | {status} |")

    table = "\n".join(rows) + "\n" if rows else ""

    if start_marker in content and end_marker in content:
        start_idx = content.index(start_marker) + len(start_marker)
        end_idx = content.index(end_marker)
        updated = (content[:start_idx] + "\n"
                   + "| Briefing | Date | Status |\n"
                   + "|----------|------|--------|\n"
                   + table
                   + content[end_idx:])
        dashboard.write_text(updated, encoding="utf-8")


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

def run_scheduler(vault_path: Path) -> None:
    """Run a simple scheduler loop that generates briefings Sunday 8 PM PKT.

    For production use, prefer Windows Task Scheduler or cron instead.
    """
    logger = AuditLogger(vault_path)
    print("Briefing scheduler started.")
    print("Schedule: Every Sunday at 20:00 PKT")
    print("Press Ctrl+C to stop.\n")

    last_run_date: str | None = None

    try:
        while True:
            now = datetime.now(PKT)
            is_sunday = now.weekday() == 6
            is_target_hour = now.hour == 20 and now.minute < 5
            today_str = now.strftime("%Y-%m-%d")

            if is_sunday and is_target_hour and last_run_date != today_str:
                print(f"[{now.strftime('%H:%M')}] Generating weekly briefing...")
                content, filepath = generate_briefing(vault_path, logger)
                update_dashboard_briefings(vault_path)
                print(f"  Briefing created: {filepath.name}")
                last_run_date = today_str

            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\nScheduler stopped.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Weekly CEO Briefing Generator")
    parser.add_argument("--vault-path", default=None,
                        help="Path to vault root")
    parser.add_argument("--schedule", action="store_true",
                        help="Run scheduler loop (Sunday 8 PM PKT)")
    args = parser.parse_args()

    vault = Path(args.vault_path or os.getenv("VAULT_PATH",
                 str(Path(__file__).parent.parent)))
    logger = AuditLogger(vault)

    if args.schedule:
        run_scheduler(vault)
        return

    # One-shot: generate briefing now
    print("Generating CEO briefing...")
    content, filepath = generate_briefing(vault, logger)
    update_dashboard_briefings(vault)
    print(f"\nBriefing saved to: {filepath}")
    print(f"\n{content}")


if __name__ == "__main__":
    main()
