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
| Pending_Approval | {pending} | Sensitive actions needing human review |
| Done | {done} | Completed items |

## Pending Tasks

<!-- START_PENDING_TASKS -->
| Filename | Preview | Time | Priority |
|----------|---------|------|----------|
{pending_tasks}<!-- END_PENDING_TASKS -->

## How It Works

1. **Drop a file** into `Needs_Action/` — any `.md` file with a task or request
2. **Watcher detects it** — the watchdog file system watcher picks up the new file
3. **Claude Code processes it** — reads the file, generates an action plan
4. **Result appears** — action plan saved, summary appended to this dashboard
5. **Sensitive actions** — flagged items go to `Pending_Approval/` for human review

## Folder Structure

```
Ai_Employee_Vault/
├── Dashboard.md              <- You are here
├── Company_Handbook.md       <- Policies and guidelines
├── Needs_Action/             <- Drop tasks here for AI processing
├── Pending_Approval/         <- Human review required
├── Done/                     <- Completed items
├── Logs/                     <- Audit trail (JSON Lines)
├── scripts/                  <- Watcher and utility scripts
│   └── watcher.py            <- File system monitor (watchdog)
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


def update_dashboard(vault: Path, logger: AuditLogger) -> None:
    """Regenerate Dashboard.md with current state."""
    dashboard_path = vault / "Dashboard.md"

    needs_action = count_folder(vault / "Needs_Action")
    pending = count_folder(vault / "Pending_Approval")
    done = count_folder(vault / "Done")

    entries = logger.read_log()
    activity = format_activity(entries)
    pending_tasks = build_pending_tasks_table(vault)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    content = DASHBOARD_TEMPLATE.format(
        date=date,
        needs_action=needs_action,
        pending=pending,
        done=done,
        pending_tasks=pending_tasks,
        activity=activity,
    )

    dashboard_path.write_text(content, encoding="utf-8", newline="")

    logger.log("dashboard_updated", "Dashboard.md", "success",
               details={"needs_action": needs_action, "pending": pending, "done": done})
    print(f"Dashboard updated: {needs_action} pending, {pending} approvals, {done} done")


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
