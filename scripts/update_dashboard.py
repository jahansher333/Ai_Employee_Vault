"""Update Dashboard.md with current vault status and recent activity.

Usage:
    python scripts/update_dashboard.py [--vault-path /path/to/vault]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger


DASHBOARD_TEMPLATE = """\
---
title: AI Employee Dashboard
updated: {date}
status: active
---

# AI Employee Dashboard

## Quick Status

| Folder | Count | Description |
|--------|-------|-------------|
| Needs_Action | {needs_action} | Items waiting for AI processing |
| Plans | {plans} | Active reasoning loop plans |
| Pending_Approval | {pending} | Sensitive actions needing human review |
| Approved | {approved} | LinkedIn posts approved for publishing |
| Done | {done} | Completed items |

## Pending Tasks

<!-- START_PENDING_TASKS -->
| Filename | Preview | Time | Priority |
|----------|---------|------|----------|
{pending_tasks}<!-- END_PENDING_TASKS -->

## Active Plans

<!-- START_PLANS -->
| Plan | Objective | Progress | Priority | Status |
|------|-----------|----------|----------|--------|
{active_plans}<!-- END_PLANS -->

## Recently Completed

<!-- START_DONE_TASKS -->
| Filename | Preview | Completed | Priority |
|----------|---------|-----------|----------|
{done_tasks}<!-- END_DONE_TASKS -->

## Service Health

| Service | Status |
|---------|--------|
{service_health}
## Recent Social Posts

<!-- START_SOCIAL_POSTS -->
| Post | Date | Status | Platform |
|------|------|--------|----------|
{social_posts}<!-- END_SOCIAL_POSTS -->

## Recent Briefings

<!-- START_BRIEFINGS -->
| Briefing | Date | Status |
|----------|------|--------|
{briefings}<!-- END_BRIEFINGS -->

## Business Analytics

<!-- START_ANALYTICS -->
*Run `python scripts/data_analyzer.py` to populate this section.*
<!-- END_ANALYTICS -->

## How It Works

1. **Drop a file** into `Needs_Action/` — any `.md` file with a task or request
2. **Watcher detects it** — the watchdog file system watcher picks up the new file
3. **Claude Code processes it** — reads the file, generates an action plan
4. **Complex tasks** — reasoning loop creates a `PLAN_*.md` in `Plans/` with step-by-step execution
5. **Result appears** — action plan saved, summary appended to this dashboard
6. **Sensitive actions** — flagged items go to `Pending_Approval/` for human review

## Folder Structure

```
Ai_Employee_Vault/
├── Dashboard.md              <- You are here
├── Company_Handbook.md       <- Policies and guidelines
├── Needs_Action/             <- Drop tasks here for AI processing
├── Plans/                    <- Active reasoning loop plans
├── Briefings/                <- Weekly CEO briefing reports
├── Pending_Approval/         <- Human review required (LinkedIn drafts)
├── Approved/                 <- LinkedIn posts approved for publishing
├── Done/                     <- Completed items
├── Logs/                     <- Audit trail (JSON Lines)
├── scripts/                  <- Watcher and utility scripts
│   ├── watcher.py            <- File system monitor (watchdog)
│   ├── gmail_watcher.py      <- Gmail API polling watcher
│   ├── whatsapp_watcher.py   <- WhatsApp Web message monitor
│   ├── linkedin_poster.py    <- LinkedIn draft & publishing
│   ├── reasoning_loop.py     <- Multi-step reasoning & plan execution
│   └── weekly_briefing.py    <- Scheduled CEO briefing generator
├── .claude/skills/           <- Reusable AI agent skills
└── .env                      <- Credentials (never committed)
```

## Recent Activity

{activity}
"""


def count_folder(folder_path: Path) -> int:
    """Count .md files in a folder. Returns 0 if folder doesn't exist."""
    if not folder_path.exists():
        return 0
    return len(list(folder_path.glob("*.md")))


def format_activity(log_entries: list[dict], limit: int = 10) -> str:
    """Format audit log entries as Dashboard activity lines."""
    recent = log_entries[-limit:] if len(log_entries) > limit else log_entries

    if not recent:
        return "_No activity yet. Drop a `.md` file into `Needs_Action/` to get started._"

    lines = []
    for e in reversed(recent):
        ts = e.get("timestamp", "")
        time_part = ts.split("T")[1][:5] if "T" in ts else ts[:5]
        action = e.get("action", "unknown")
        outcome = e.get("outcome", "")
        ref = e.get("input_ref", "")
        lines.append(f"- [{time_part}] {action} -> {outcome} ({ref})")

    return "\n".join(lines)


def build_pending_tasks_table(vault: Path) -> str:
    """Build the pending tasks table rows from Needs_Action/ files."""
    needs_action = vault / "Needs_Action"
    if not needs_action.exists():
        return ""

    rows = []
    for f in sorted(needs_action.glob("*.md")):
        content = f.read_text(encoding="utf-8")
        # Extract first heading as preview
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        preview = title_match.group(1)[:40] if title_match else f.name

        # Extract priority from frontmatter
        priority = "medium"
        prio_match = re.search(r"priority:\s*(\w+)", content)
        if prio_match:
            priority = prio_match.group(1)

        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
        time_str = mtime.strftime("%H:%M")

        rows.append(f"| {f.name} | {preview} | {time_str} | {priority} |")

    return "\n".join(rows) + "\n" if rows else ""


def build_done_tasks_table(vault: Path, limit: int = 20) -> str:
    """Build the recently completed tasks table rows from Done/ files."""
    done_dir = vault / "Done"
    if not done_dir.exists():
        return ""

    files = sorted(done_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    rows = []
    for f in files[:limit]:
        content = f.read_text(encoding="utf-8")
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        preview = title_match.group(1)[:40] if title_match else f.name

        priority = "medium"
        prio_match = re.search(r"priority:\s*(\w+)", content)
        if prio_match:
            priority = prio_match.group(1)

        completed_match = re.search(r"completed_at:\s*(.+)", content)
        if completed_match:
            ts = completed_match.group(1).strip()
            completed = ts[:16].replace("T", " ")
        else:
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            completed = mtime.strftime("%Y-%m-%d %H:%M")

        rows.append(f"| {f.name} | {preview} | {completed} | {priority} |")

    return "\n".join(rows) + "\n" if rows else ""


def build_social_posts_table(vault: Path, limit: int = 10) -> str:
    """Build table rows for social posts (LinkedIn + FB + IG + X) across all folders."""
    posts: list[tuple[str, str, str, str]] = []

    platform_prefixes = {
        "LINKEDIN_": "LinkedIn",
        "FACEBOOK_": "Facebook",
        "INSTAGRAM_": "Instagram",
        "TWITTER_": "Twitter/X",
    }

    for folder, default_status in [
        (vault / "Pending_Approval", "draft"),
        (vault / "Approved", "approved"),
        (vault / "Done", "posted"),
    ]:
        if not folder.exists():
            continue
        for prefix, platform in platform_prefixes.items():
            for f in folder.glob(f"{prefix}*.md"):
                content = f.read_text(encoding="utf-8")
                # Extract topic from frontmatter
                topic_match = re.search(r'topic:\s*"?([^"\n]+)"?', content)
                topic = topic_match.group(1).strip()[:40] if topic_match else f.stem

                status_match = re.search(r"status:\s*(\w+)", content)
                status = status_match.group(1) if status_match else default_status

                date_match = re.search(r"generated_at:\s*\"?([^\"'\n]+)", content)
                if date_match:
                    date_str = date_match.group(1).strip()[:16].replace("T", " ")
                else:
                    mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
                    date_str = mtime.strftime("%Y-%m-%d %H:%M")

                posts.append((topic, date_str, status, platform))

    posts.sort(key=lambda x: x[1], reverse=True)
    posts = posts[:limit]

    if not posts:
        return ""

    rows = [f"| {t} | {d} | {s} | {p} |" for t, d, s, p in posts]
    return "\n".join(rows) + "\n"


def build_briefings_table(vault: Path, limit: int = 5) -> str:
    """Build recent briefings table rows from Briefings/ directory."""
    briefings_dir = vault / "Briefings"
    if not briefings_dir.exists():
        return ""

    rows = []
    for f in sorted(briefings_dir.glob("*_Briefing*.md"),
                    key=lambda p: p.stat().st_mtime, reverse=True):
        content = f.read_text(encoding="utf-8")
        date_match = re.search(r'date:\s*"?([^"\n]+)"?', content)
        date_str = date_match.group(1).strip() if date_match else f.stem[:10]

        status_match = re.search(r"status:\s*(\w+)", content)
        status = status_match.group(1) if status_match else "new"

        rows.append(f"| {f.name} | {date_str} | {status} |")

    return "\n".join(rows[:limit]) + "\n" if rows else ""


def build_plans_table(vault: Path, limit: int = 10) -> str:
    """Build active plans table rows from Plans/ directory."""
    plans_dir = vault / "Plans"
    if not plans_dir.exists():
        return ""

    rows = []
    for f in sorted(plans_dir.glob("PLAN_*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        content = f.read_text(encoding="utf-8")

        # Extract objective
        obj_match = re.search(r'objective:\s*"?([^"\n]+)"?', content)
        objective = obj_match.group(1).strip()[:35] if obj_match else f.stem

        # Extract progress
        total_match = re.search(r"total_steps:\s*(\d+)", content)
        done_match = re.search(r"completed_steps:\s*(\d+)", content)
        total = int(total_match.group(1)) if total_match else 0
        completed = int(done_match.group(1)) if done_match else 0
        progress = f"{completed}/{total}"

        # Extract priority and status
        prio_match = re.search(r"priority:\s*(\w+)", content)
        priority = prio_match.group(1) if prio_match else "medium"

        status_match = re.search(r"status:\s*(\w+)", content)
        status = status_match.group(1) if status_match else "active"

        rows.append(f"| {f.name} | {objective} | {progress} | {priority} | {status} |")

    return "\n".join(rows[:limit]) + "\n" if rows else ""


def build_service_health_table() -> str:
    """Build a service health table for the dashboard."""
    services = {
        "File Watcher": "operational",
        "Gmail Watcher": "operational",
        "WhatsApp Watcher": "operational",
        "Odoo MCP": "operational",
        "Social MCP": "operational",
        "Email MCP": "operational",
    }
    try:
        from error_recovery import HealthTracker
        tracker = HealthTracker()
        tracked = tracker.get_summary()
        if tracked:
            for svc, status in tracked.items():
                services[svc] = status
    except ImportError:
        pass

    rows = [f"| {svc} | {status} |" for svc, status in services.items()]
    return "\n".join(rows) + "\n"


def update_dashboard(vault: Path, logger: AuditLogger) -> None:
    """Regenerate Dashboard.md with current state."""
    dashboard_path = vault / "Dashboard.md"

    needs_action = count_folder(vault / "Needs_Action")
    plans = count_folder(vault / "Plans")
    pending = count_folder(vault / "Pending_Approval")
    approved = count_folder(vault / "Approved")
    done = count_folder(vault / "Done")

    entries = logger.read_log()
    activity = format_activity(entries)
    pending_tasks = build_pending_tasks_table(vault)
    active_plans = build_plans_table(vault)
    done_tasks = build_done_tasks_table(vault)
    social_posts = build_social_posts_table(vault)
    briefings = build_briefings_table(vault)
    service_health = build_service_health_table()
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    content = DASHBOARD_TEMPLATE.format(
        date=date,
        needs_action=needs_action,
        plans=plans,
        pending=pending,
        approved=approved,
        done=done,
        pending_tasks=pending_tasks,
        active_plans=active_plans,
        done_tasks=done_tasks,
        social_posts=social_posts,
        briefings=briefings,
        service_health=service_health,
        activity=activity,
    )

    dashboard_path.write_text(content, encoding="utf-8", newline="")

    logger.log("dashboard_updated", "Dashboard.md", "success",
               details={"needs_action": needs_action, "plans": plans,
                        "pending": pending, "approved": approved, "done": done})
    print(f"Dashboard updated: {needs_action} pending, {plans} plans, "
          f"{pending} approvals, {approved} approved, {done} done")


def main() -> None:
    parser = argparse.ArgumentParser(description="Update Dashboard.md")
    parser.add_argument("--vault-path", default=None)
    args = parser.parse_args()

    vault = Path(args.vault_path or os.getenv("VAULT_PATH",
                 str(Path(__file__).parent.parent)))
    logger = AuditLogger(vault)
    update_dashboard(vault, logger)


if __name__ == "__main__":
    main()
