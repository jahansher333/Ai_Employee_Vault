"""Process all new items in Needs_Action/ — reads, analyzes, generates plans.

This script is designed to be called by Claude Code or run standalone.
It reads .md files from Needs_Action/, generates action plans, and
updates file status. Sensitive items are routed to Pending_Approval/.

Usage:
    python scripts/process_inbox.py [--vault-path /path/to/vault]
    python scripts/process_inbox.py --file Needs_Action/specific-task.md
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger


SENSITIVE_KEYWORDS = [
    "payment", "password", "credential", "delete", "remove", "api key",
]


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}, content

    end = content.find("---", 3)
    if end == -1:
        return {}, content

    fm_text = content[3:end].strip()
    body = content[end + 3:].strip()

    frontmatter = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            frontmatter[key.strip()] = value.strip().strip('"').strip("'")

    return frontmatter, body


def serialize_frontmatter(fm: dict, body: str) -> str:
    """Serialize frontmatter dict and body back to markdown."""
    lines = ["---"]
    for key, value in fm.items():
        lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append("")
    lines.append(body)
    return "\n".join(lines)


def is_sensitive(content: str) -> bool:
    """Check if content contains sensitive action keywords."""
    lower = content.lower()
    return any(kw in lower for kw in SENSITIVE_KEYWORDS)


def route_to_approval(file_path: Path, content: str, vault: Path, logger: AuditLogger) -> None:
    """Route a sensitive item to Pending_Approval/."""
    approval_dir = vault / "Pending_Approval"
    approval_dir.mkdir(parents=True, exist_ok=True)

    approval_content = (
        f"---\n"
        f"type: approval_request\n"
        f"source: {file_path.name}\n"
        f"detected: {datetime.now(timezone.utc).isoformat()}\n"
        f"status: pending\n"
        f"---\n\n"
        f"# Approval Required: {file_path.name}\n\n"
        f"The AI detected potentially sensitive content in this task.\n"
        f"Review the original content below and change status to "
        f"`approved` or `rejected`.\n\n"
        f"## Original Content\n\n{content}\n"
    )

    approval_path = approval_dir / f"approve-{file_path.name}"
    approval_path.write_text(approval_content, encoding="utf-8")

    logger.log("sensitive_routed", file_path.name, "success",
               details={"approval_file": approval_path.name})
    print(f"  [SENSITIVE] {file_path.name} -> Pending_Approval/")


def generate_action_plan(frontmatter: dict, body: str) -> str:
    """Generate a simple action plan based on task content.

    In the full implementation, this would invoke Claude Code.
    For Bronze Tier MVP, we generate a structured placeholder
    that Claude Code can later enhance.
    """
    priority = frontmatter.get("priority", "medium")
    category = frontmatter.get("category", "general")

    # Extract the title (first # heading)
    title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    title = title_match.group(1) if title_match else "Untitled Task"

    plan = (
        f"\n\n## Action Plan\n\n"
        f"**Generated**: {datetime.now(timezone.utc).isoformat()}\n"
        f"**Priority**: {priority}\n"
        f"**Category**: {category}\n\n"
        f"### Recommended Steps\n\n"
        f"1. Review the task requirements above\n"
        f"2. Gather necessary context and resources\n"
        f"3. Execute the {category} task: \"{title}\"\n"
        f"4. Validate output meets expected criteria\n"
        f"5. Move to Done when complete\n\n"
        f"### Estimated Effort\n\n"
        f"To be determined by human review.\n\n"
        f"### Dependencies\n\n"
        f"- None identified at Bronze Tier\n"
    )
    return plan


def append_summary_to_dashboard(file_path: Path, frontmatter: dict, vault: Path) -> None:
    """Append a task summary line to Dashboard.md's pending tasks section."""
    dashboard = vault / "Dashboard.md"
    if not dashboard.exists():
        return

    filename = file_path.name
    # Extract first heading as preview
    body_text = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
    title_match = re.search(r"^#\s+(.+)$", body_text, re.MULTILINE)
    preview = title_match.group(1)[:40] if title_match else filename
    timestamp = datetime.now(timezone.utc).strftime("%H:%M")
    priority = frontmatter.get("priority", "medium")

    summary_line = f"| {filename} | {preview} | {timestamp} | {priority} |"

    content = dashboard.read_text(encoding="utf-8")
    marker = "<!-- END_PENDING_TASKS -->"
    if marker in content:
        content = content.replace(marker, summary_line + "\n" + marker)
        dashboard.write_text(content, encoding="utf-8")


def process_file(file_path: Path, vault: Path, logger: AuditLogger) -> str:
    """Process a single Needs_Action file. Returns status."""
    content = file_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)

    # Skip already-processed files
    status = frontmatter.get("status", "new")
    if status in ("planned", "done"):
        logger.log("file_skipped", file_path.name, "skipped",
                    details={"reason": f"status={status}"})
        return "skipped"

    # Check for sensitive content
    if is_sensitive(content):
        route_to_approval(file_path, content, vault, logger)
        frontmatter["status"] = "pending_approval"
        updated = serialize_frontmatter(frontmatter, body)
        file_path.write_text(updated, encoding="utf-8")
        return "pending_approval"

    # Generate action plan
    with logger.timed("inbox_processed", file_path.name) as ctx:
        plan = generate_action_plan(frontmatter, body)
        frontmatter["status"] = "planned"
        frontmatter["processed_at"] = datetime.now(timezone.utc).isoformat()
        updated_body = body + plan
        updated = serialize_frontmatter(frontmatter, updated_body)
        file_path.write_text(updated, encoding="utf-8")
        ctx["details"] = {
            "priority": frontmatter.get("priority", "unknown"),
            "category": frontmatter.get("category", "unknown"),
        }

    # Append summary to Dashboard.md
    append_summary_to_dashboard(file_path, frontmatter, vault)

    print(f"  [PLANNED] {file_path.name}")
    return "planned"


def move_to_done(file_path: Path, vault: Path, logger: AuditLogger) -> None:
    """Move a file from Needs_Action/ to Done/ with completion timestamp."""
    content = file_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)

    frontmatter["status"] = "done"
    frontmatter["completed_at"] = datetime.now(timezone.utc).isoformat()
    updated = serialize_frontmatter(frontmatter, body)

    done_dir = vault / "Done"
    done_dir.mkdir(parents=True, exist_ok=True)
    dest = done_dir / file_path.name

    # Avoid overwriting
    if dest.exists():
        stem = file_path.stem
        suffix = datetime.now().strftime("%H%M%S")
        dest = done_dir / f"{stem}-{suffix}.md"

    dest.write_text(updated, encoding="utf-8")

    # Verify write succeeded before deleting source
    if dest.exists() and dest.stat().st_size > 0:
        file_path.unlink()
        logger.log("item_moved_done", file_path.name, "success",
                    details={"destination": dest.name})
        print(f"  [DONE] {file_path.name} -> Done/{dest.name}")
    else:
        logger.log("item_moved_done", file_path.name, "error",
                    error="Destination file verification failed")
        print(f"  [ERROR] Failed to move {file_path.name}")


def print_report(results: dict, processed_files: list[dict], vault: Path, logger: AuditLogger) -> None:
    """Print a full Markdown report of what the skill did."""
    print("\n" + "=" * 60)
    print("# SimpleTaskReaderSkill Report")
    print("=" * 60)

    # Summary table
    print("\n## Summary\n")
    print(f"| Metric          | Count |")
    print(f"|-----------------|-------|")
    print(f"| Planned         | {results.get('planned', 0)}     |")
    print(f"| Pending Approval| {results.get('pending_approval', 0)}     |")
    print(f"| Skipped         | {results.get('skipped', 0)}     |")
    print(f"| Errors          | {results.get('error', 0)}     |")

    # Processed files detail
    if processed_files:
        print("\n## Processed Files\n")
        print("| Filename | Priority | Category | Status | Time |")
        print("|----------|----------|----------|--------|------|")
        for pf in processed_files:
            line = f"| {pf['name']} | {pf['priority']} | {pf['category']} | {pf['status']} | {pf['time']} |"
            print(line.encode("ascii", "replace").decode())

    # Dashboard update
    dashboard = vault / "Dashboard.md"
    if dashboard.exists():
        content = dashboard.read_text(encoding="utf-8")
        start = content.find("<!-- START_PENDING_TASKS -->")
        end = content.find("<!-- END_PENDING_TASKS -->")
        if start != -1 and end != -1:
            table = content[start:end + len("<!-- END_PENDING_TASKS -->")]
            print("\n## Dashboard Pending Tasks\n")
            print(table.encode("ascii", "replace").decode())

    # Recent audit logs
    entries = logger.read_log()
    if entries:
        recent = entries[-5:]
        print("\n## Audit Log (last 5 entries)\n")
        print("| Time  | Action           | File              | Outcome |")
        print("|-------|------------------|-------------------|---------|")
        for e in reversed(recent):
            ts = e.get("timestamp", "")
            t = ts.split("T")[1][:8] if "T" in ts else ts[:8]
            print(f"| {t} | {e.get('action', '')} | {e.get('input_ref', '')} | {e.get('outcome', '')} |")

    print("\n" + "=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process Needs_Action/ items")
    parser.add_argument("--vault-path", default=None)
    parser.add_argument("--file", default=None, help="Process a specific file")
    parser.add_argument("--move-done", action="store_true",
                        help="Move planned items to Done/")
    args = parser.parse_args()

    vault = Path(args.vault_path or os.getenv("VAULT_PATH",
                 str(Path(__file__).parent.parent)))
    logger = AuditLogger(vault)

    if args.move_done:
        # Move all planned items to Done
        needs_action = vault / "Needs_Action"
        for f in sorted(needs_action.glob("*.md")):
            content = f.read_text(encoding="utf-8")
            fm, _ = parse_frontmatter(content)
            if fm.get("status") == "done":
                move_to_done(f, vault, logger)
        return

    if args.file:
        file_path = Path(args.file)
        if not file_path.is_absolute():
            file_path = vault / file_path
        if not file_path.exists():
            print(f"File not found: {file_path}")
            sys.exit(1)
        result = process_file(file_path, vault, logger)
        print(f"Result: {result}")
        return

    # Process all files in Needs_Action/
    needs_action = vault / "Needs_Action"
    if not needs_action.exists():
        print("No Needs_Action/ folder found.")
        return

    files = sorted(needs_action.glob("*.md"))
    if not files:
        print("No .md files in Needs_Action/.")
        return

    print(f"Processing {len(files)} file(s) from Needs_Action/...\n")
    results = {"planned": 0, "pending_approval": 0, "skipped": 0, "error": 0}
    processed_files = []
    for f in files:
        try:
            content = f.read_text(encoding="utf-8")
            fm, _ = parse_frontmatter(content)
            status = process_file(f, vault, logger)
            results[status] = results.get(status, 0) + 1
            processed_files.append({
                "name": f.name,
                "priority": fm.get("priority", "medium"),
                "category": fm.get("category", "general"),
                "status": status,
                "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            })
        except Exception as exc:
            results["error"] += 1
            logger.log("inbox_processed", f.name, "error", error=str(exc))
            print(f"  [ERROR] {f.name}: {exc}")

    print_report(results, processed_files, vault, logger)


if __name__ == "__main__":
    main()
