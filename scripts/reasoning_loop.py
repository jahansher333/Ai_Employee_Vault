"""Reasoning Loop (Ralph Wiggum) — creates and executes Plan.md files.

Gold Tier: Enhanced with cross-domain detection (accounting, social, email,
reporting), domain-tagged steps, per-step retry logic, circular dependency
detection, and execution metrics tracking.

Usage:
    python scripts/reasoning_loop.py [--vault-path /path]
    python scripts/reasoning_loop.py --file Needs_Action/complex-task.md
    python scripts/reasoning_loop.py --execute Plans/PLAN_123456_handle-invoice.md
    python scripts/reasoning_loop.py --run-plans   # Execute all active plans
    python scripts/reasoning_loop.py --metrics      # Show execution metrics
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

# ---------------------------------------------------------------------------
# Complexity detection
# ---------------------------------------------------------------------------

COMPLEXITY_KEYWORDS: list[str] = [
    "invoice", "payment", "refund", "onboard", "migrate",
    "integrate", "deploy", "setup", "configure", "analyze",
    "review", "audit", "report", "escalate", "schedule",
    "multi-step", "workflow", "approval", "budget", "contract",
]

# ---------------------------------------------------------------------------
# Gold Tier: Domain definitions for cross-domain detection
# ---------------------------------------------------------------------------

DOMAINS = {
    "accounting": ["invoice", "payment", "expense", "revenue", "balance", "journal",
                   "odoo", "financial", "budget", "ledger", "overdue"],
    "social": ["facebook", "instagram", "twitter", "linkedin", "post", "hashtag",
               "social media", "engagement", "publish"],
    "email": ["email", "gmail", "inbox", "reply", "send", "unread", "message",
              "forward", "cc", "bcc"],
    "reporting": ["report", "briefing", "dashboard", "summary", "audit", "weekly",
                  "analysis", "metrics", "trend", "anomaly"],
}


def detect_cross_domain(frontmatter: dict, body: str) -> dict:
    """Detect which domains a task spans.

    Returns dict with domains list and is_cross_domain flag.
    """
    combined = f"{' '.join(str(v) for v in frontmatter.values())} {body}".lower()
    matched_domains: dict[str, list[str]] = {}

    for domain, keywords in DOMAINS.items():
        hits = [kw for kw in keywords if kw in combined]
        if hits:
            matched_domains[domain] = hits

    return {
        "domains": list(matched_domains.keys()),
        "domain_keywords": matched_domains,
        "is_cross_domain": len(matched_domains) >= 2,
        "domain_count": len(matched_domains),
    }


def detect_circular_dependencies(steps: list[dict]) -> list[str]:
    """Check for circular dependencies in step list.

    Steps can have a 'depends_on' field listing step numbers they depend on.
    Returns list of error messages if cycles detected.
    """
    errors = []
    step_map = {s.get("step_num", i + 1): s for i, s in enumerate(steps)}

    def _visit(num: int, visited: set, path: set) -> bool:
        if num in path:
            return True  # Cycle found
        if num in visited:
            return False
        visited.add(num)
        path.add(num)
        step = step_map.get(num, {})
        for dep in step.get("depends_on", []):
            if _visit(dep, visited, path):
                errors.append(f"Circular dependency: step {num} <-> step {dep}")
                return True
        path.discard(num)
        return False

    visited: set = set()
    for num in step_map:
        _visit(num, visited, set())

    return errors

COMPLEXITY_THRESHOLD = 2  # Minimum keyword matches to trigger reasoning loop


def detect_complexity(frontmatter: dict, body: str) -> dict:
    """Assess whether a task is complex enough for the reasoning loop.

    Returns a dict with:
        is_complex: bool — True if task should get a Plan.md
        score: int — number of complexity signals found
        matched_signals: list[str] — which signals triggered
        reason: str — human-readable explanation
    """
    signals: list[str] = []
    content = body.lower()
    fm_text = " ".join(str(v) for v in frontmatter.values()).lower()
    combined = f"{fm_text} {content}"

    # 1. Keyword matching
    for kw in COMPLEXITY_KEYWORDS:
        if kw in combined:
            signals.append(f"keyword:{kw}")

    # 2. Multiple action verbs suggest multi-step work
    action_verbs = re.findall(
        r"\b(review|send|create|update|check|verify|draft|approve|notify|move|respond|forward)\b",
        combined,
    )
    unique_verbs = set(action_verbs)
    if len(unique_verbs) >= 3:
        signals.append(f"multi-action:{len(unique_verbs)}-verbs")

    # 3. Priority is high
    if frontmatter.get("priority", "").lower() == "high":
        signals.append("high-priority")

    # 4. Content length (long body = likely complex)
    if len(body) > 500:
        signals.append("long-content")

    # 5. Explicit multi-step markers
    if re.search(r"(step\s*\d|phase\s*\d|\d\.\s+\w)", body, re.IGNORECASE):
        signals.append("has-numbered-steps")

    # 6. References to other files or systems
    if re.search(r"(see\s+\w+\.md|refer\s+to|attached|linked)", body, re.IGNORECASE):
        signals.append("cross-reference")

    score = len(signals)
    is_complex = score >= COMPLEXITY_THRESHOLD

    if is_complex:
        reason = f"Task has {score} complexity signals: {', '.join(signals[:5])}"
    else:
        reason = f"Task is simple ({score} signal(s) — threshold is {COMPLEXITY_THRESHOLD})"

    return {
        "is_complex": is_complex,
        "score": score,
        "matched_signals": signals,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# Frontmatter helpers (reuse pattern from process_inbox.py)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Plan creation
# ---------------------------------------------------------------------------

def _sanitize(name: str, max_len: int = 50) -> str:
    """Replace non-alphanumeric chars with dashes, truncate."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-")
    return slug[:max_len]


def generate_plan_steps(frontmatter: dict, body: str) -> list[dict]:
    """Generate structured steps based on task type and content.

    Each step is a dict with: description, category, requires_approval, domain.
    Gold Tier adds domain tagging to each step.
    """
    task_type = frontmatter.get("type", "task")
    priority = frontmatter.get("priority", "medium")

    steps: list[dict] = []

    if task_type == "email":
        steps = [
            {"description": "Read and comprehend the email content", "category": "analysis", "requires_approval": False},
            {"description": "Identify required actions and recipients", "category": "analysis", "requires_approval": False},
            {"description": "Check for sensitive content (payments, credentials)", "category": "security", "requires_approval": False},
            {"description": "Draft response or execute requested action", "category": "execution", "requires_approval": priority == "high"},
            {"description": "Review draft for accuracy and tone", "category": "review", "requires_approval": False},
            {"description": "Send response or complete action", "category": "execution", "requires_approval": True},
            {"description": "Update task status and move to Done", "category": "cleanup", "requires_approval": False},
        ]
    elif task_type == "whatsapp":
        steps = [
            {"description": "Read the WhatsApp message and context", "category": "analysis", "requires_approval": False},
            {"description": "Assess urgency and determine response priority", "category": "analysis", "requires_approval": False},
            {"description": "Check if message contains sensitive requests", "category": "security", "requires_approval": False},
            {"description": "Draft response to sender", "category": "execution", "requires_approval": True},
            {"description": "Send response via WhatsApp", "category": "execution", "requires_approval": True},
            {"description": "Update task status and move to Done", "category": "cleanup", "requires_approval": False},
        ]
    elif "invoice" in body.lower() or "payment" in body.lower():
        steps = [
            {"description": "Extract invoice/payment details (amount, vendor, date)", "category": "analysis", "requires_approval": False},
            {"description": "Verify against known vendors and budget", "category": "verification", "requires_approval": False},
            {"description": "Flag any anomalies or discrepancies", "category": "security", "requires_approval": False},
            {"description": "Prepare payment approval request", "category": "execution", "requires_approval": True},
            {"description": "Route to Pending_Approval for human review", "category": "routing", "requires_approval": False},
            {"description": "After approval, process payment action", "category": "execution", "requires_approval": True},
            {"description": "Log completion and move to Done", "category": "cleanup", "requires_approval": False},
        ]
    else:
        # Generic complex task steps
        steps = [
            {"description": "Analyze task requirements and context", "category": "analysis", "requires_approval": False},
            {"description": "Identify dependencies and prerequisites", "category": "analysis", "requires_approval": False},
            {"description": "Plan execution approach", "category": "planning", "requires_approval": False},
            {"description": "Execute primary action", "category": "execution", "requires_approval": priority == "high"},
            {"description": "Validate results against requirements", "category": "review", "requires_approval": False},
            {"description": "Update task status and move to Done", "category": "cleanup", "requires_approval": False},
        ]

    # Gold Tier: Tag each step with its domain
    cross_domain = detect_cross_domain(frontmatter, body)
    for step in steps:
        desc_lower = step["description"].lower()
        step_domain = "general"
        for domain, keywords in DOMAINS.items():
            if any(kw in desc_lower for kw in keywords):
                step_domain = domain
                break
        # If task is in a specific domain, tag analysis/cleanup steps too
        if step_domain == "general" and len(cross_domain["domains"]) == 1:
            step_domain = cross_domain["domains"][0]
        step["domain"] = step_domain
        step["depends_on"] = []  # For circular dep detection

    return steps


def estimate_time(steps: list[dict]) -> str:
    """Estimate completion time based on step count and types."""
    base_minutes = len(steps) * 2
    approval_steps = sum(1 for s in steps if s["requires_approval"])
    # Approval steps add wait time
    if approval_steps > 0:
        return f"{base_minutes}-{base_minutes + approval_steps * 30} minutes (includes approval wait)"
    return f"~{base_minutes} minutes"


def create_plan(
    source_file: Path,
    frontmatter: dict,
    body: str,
    vault_path: Path,
    logger: AuditLogger | None = None,
) -> Path:
    """Create a PLAN_*.md file in Plans/ from a complex task.

    Returns the Path to the created plan file.
    """
    plans_dir = vault_path / "Plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    timestamp = datetime.now(timezone.utc).strftime("%H%M%S")
    title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    title = title_match.group(1) if title_match else source_file.stem
    safe_title = _sanitize(title)
    filename = f"PLAN_{timestamp}_{safe_title}.md"
    plan_path = plans_dir / filename

    # Generate steps
    steps = generate_plan_steps(frontmatter, body)
    time_estimate = estimate_time(steps)

    # Determine dependencies
    deps: list[str] = []
    if any(s["requires_approval"] for s in steps):
        deps.append("Human approval required for sensitive steps")
    if frontmatter.get("type") == "email":
        deps.append("Gmail API access (credentials.json + token.json)")
    if frontmatter.get("type") == "whatsapp":
        deps.append("WhatsApp Web session (run --setup if expired)")

    deps_yaml = "\n".join(f'  - "{d}"' for d in deps) if deps else '  - "none"'

    # Build step checkboxes
    step_lines = []
    for i, step in enumerate(steps, 1):
        approval_tag = " **[NEEDS APPROVAL]**" if step["requires_approval"] else ""
        step_lines.append(
            f"- [ ] **Step {i}** ({step['category']}): "
            f"{step['description']}{approval_tag}"
        )

    steps_md = "\n".join(step_lines)

    # Build plan content
    now = datetime.now(timezone.utc).isoformat()
    source_type = frontmatter.get("type", "task")
    priority = frontmatter.get("priority", "medium")

    plan_content = (
        f"---\n"
        f"type: plan\n"
        f"source_file: \"{source_file.name}\"\n"
        f"source_type: {source_type}\n"
        f"objective: \"{title}\"\n"
        f"priority: {priority}\n"
        f"status: active\n"
        f"created_at: \"{now}\"\n"
        f"estimated_time: \"{time_estimate}\"\n"
        f"total_steps: {len(steps)}\n"
        f"completed_steps: 0\n"
        f"dependencies:\n"
        f"{deps_yaml}\n"
        f"---\n\n"
        f"# Plan: {title}\n\n"
        f"**Source**: `{source_file.name}`\n"
        f"**Priority**: {priority.upper()}\n"
        f"**Estimated Time**: {time_estimate}\n"
        f"**Created**: {now}\n\n"
        f"## Objective\n\n"
        f"{title}\n\n"
        f"## Steps\n\n"
        f"{steps_md}\n\n"
        f"## Dependencies\n\n"
    )

    for d in deps:
        plan_content += f"- {d}\n"
    if not deps:
        plan_content += "- None\n"

    plan_content += (
        f"\n## Execution Log\n\n"
        f"| Step | Status | Timestamp | Notes |\n"
        f"|------|--------|-----------|-------|\n"
        f"| Plan created | active | {now} | Source: {source_file.name} |\n"
    )

    plan_path.write_text(plan_content, encoding="utf-8")

    if logger:
        logger.log(
            "plan_created", filename, "success",
            details={
                "source": source_file.name,
                "steps": len(steps),
                "priority": priority,
                "has_approval_steps": any(s["requires_approval"] for s in steps),
            },
        )

    return plan_path


# ---------------------------------------------------------------------------
# Plan execution
# ---------------------------------------------------------------------------

def read_plan(plan_path: Path) -> tuple[dict, str, list[dict]]:
    """Read a plan file and extract frontmatter, body, and parsed steps.

    Returns (frontmatter, body, steps) where steps is a list of dicts:
        step_num, description, category, is_complete, requires_approval
    """
    content = plan_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)

    # Parse step checkboxes from body
    steps = []
    step_pattern = re.compile(
        r"- \[([ Xx])\] \*\*Step (\d+)\*\* \((\w+)\): (.+?)(?:\s*\*\*\[NEEDS APPROVAL\]\*\*)?$",
        re.MULTILINE,
    )
    for match in step_pattern.finditer(body):
        checkbox, num, category, desc = match.groups()
        steps.append({
            "step_num": int(num),
            "description": desc.strip(),
            "category": category,
            "is_complete": checkbox.lower() == "x",
            "requires_approval": "NEEDS APPROVAL" in match.group(0),
        })

    return frontmatter, body, steps


def execute_step(
    plan_path: Path,
    step_num: int,
    vault_path: Path,
    logger: AuditLogger | None = None,
    notes: str = "",
) -> bool:
    """Mark a step as complete in the plan file and update execution log.

    Returns True on success, False if step not found or already complete.
    """
    content = plan_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)

    # Find and check off the step
    pattern = re.compile(
        rf"- \[ \] \*\*Step {step_num}\*\*",
    )
    if not pattern.search(body):
        return False  # Step not found or already complete

    # Mark step complete
    body = pattern.sub(f"- [X] **Step {step_num}**", body, count=1)

    # Count completed steps
    completed = len(re.findall(r"- \[[Xx]\] \*\*Step \d+\*\*", body))
    total = int(frontmatter.get("total_steps", 0))
    frontmatter["completed_steps"] = str(completed)

    # Add execution log entry
    now = datetime.now(timezone.utc).isoformat()
    log_line = f"| Step {step_num} | completed | {now} | {notes or 'Auto-executed'} |"
    body = body.rstrip() + "\n" + log_line + "\n"

    # Check if all steps are done
    if completed >= total:
        frontmatter["status"] = "completed"
        frontmatter["completed_at"] = now
        body = body.rstrip() + "\n" + f"| Plan complete | done | {now} | All {total} steps finished |\n"

    updated = serialize_frontmatter(frontmatter, body)
    plan_path.write_text(updated, encoding="utf-8")

    if logger:
        logger.log(
            "plan_step_executed", plan_path.name, "success",
            details={
                "step": step_num,
                "completed": completed,
                "total": total,
                "notes": notes,
            },
        )

    return True


def complete_plan(
    plan_path: Path,
    vault_path: Path,
    logger: AuditLogger | None = None,
) -> Path | None:
    """Move a completed plan and its source task to Done/.

    Returns the Done/ path for the plan, or None on failure.
    """
    content = plan_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)

    if frontmatter.get("status") != "completed":
        return None

    done_dir = vault_path / "Done"
    done_dir.mkdir(parents=True, exist_ok=True)

    # Move plan to Done
    now = datetime.now(timezone.utc).isoformat()
    frontmatter["status"] = "done"
    frontmatter["moved_to_done_at"] = now
    updated = serialize_frontmatter(frontmatter, body)

    dest = done_dir / plan_path.name
    if dest.exists():
        stem = plan_path.stem
        suffix = datetime.now().strftime("%H%M%S")
        dest = done_dir / f"{stem}-{suffix}.md"

    dest.write_text(updated, encoding="utf-8")

    if dest.exists() and dest.stat().st_size > 0:
        plan_path.unlink()

        # Also move source file to Done if it exists in Needs_Action
        source_name = frontmatter.get("source_file", "")
        if source_name:
            source_path = vault_path / "Needs_Action" / source_name
            if source_path.exists():
                source_content = source_path.read_text(encoding="utf-8")
                src_fm, src_body = parse_frontmatter(source_content)
                src_fm["status"] = "done"
                src_fm["completed_at"] = now
                src_fm["completed_by_plan"] = plan_path.name
                src_dest = done_dir / source_name
                if src_dest.exists():
                    src_dest = done_dir / f"{source_path.stem}-{datetime.now().strftime('%H%M%S')}.md"
                src_dest.write_text(serialize_frontmatter(src_fm, src_body), encoding="utf-8")
                if src_dest.exists() and src_dest.stat().st_size > 0:
                    source_path.unlink()

        if logger:
            logger.log(
                "plan_completed", plan_path.name, "success",
                details={"destination": dest.name, "source": source_name},
            )
        return dest

    return None


def route_plan_to_approval(
    plan_path: Path,
    vault_path: Path,
    step_num: int,
    logger: AuditLogger | None = None,
) -> Path:
    """Route a plan to Pending_Approval when an approval step is reached.

    Creates an approval-request file in Pending_Approval/ referencing the plan.
    """
    approval_dir = vault_path / "Pending_Approval"
    approval_dir.mkdir(parents=True, exist_ok=True)

    content = plan_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)

    now = datetime.now(timezone.utc).isoformat()

    # Update plan status
    frontmatter["status"] = "awaiting_approval"
    frontmatter["approval_requested_at"] = now
    frontmatter["approval_for_step"] = str(step_num)
    updated = serialize_frontmatter(frontmatter, body)
    plan_path.write_text(updated, encoding="utf-8")

    # Create approval file
    approval_content = (
        f"---\n"
        f"type: plan_approval\n"
        f"plan_file: \"{plan_path.name}\"\n"
        f"step_requiring_approval: {step_num}\n"
        f"detected: \"{now}\"\n"
        f"status: pending\n"
        f"---\n\n"
        f"# Approval Required: Plan Step {step_num}\n\n"
        f"**Plan**: `{plan_path.name}`\n"
        f"**Objective**: {frontmatter.get('objective', 'Unknown')}\n\n"
        f"The reasoning loop has reached a step requiring human approval.\n"
        f"Review the plan and change status to `approved` or `rejected`.\n\n"
        f"## Plan Context\n\n"
        f"{body[:1000]}\n"
    )

    approval_path = approval_dir / f"approve-{plan_path.name}"
    approval_path.write_text(approval_content, encoding="utf-8")

    if logger:
        logger.log(
            "plan_approval_requested", plan_path.name, "success",
            details={"step": step_num},
        )

    return approval_path


# ---------------------------------------------------------------------------
# Gold Tier: Step retry and metrics
# ---------------------------------------------------------------------------

def execute_step_with_retry(
    plan_path: Path,
    step_num: int,
    vault_path: Path,
    logger: AuditLogger | None = None,
    notes: str = "",
    max_retries: int = 1,
) -> dict:
    """Execute a step with retry logic.

    Returns dict with success, attempts, and any error.
    """
    attempts = 0
    last_error = None

    for attempt in range(max_retries + 1):
        attempts += 1
        try:
            success = execute_step(plan_path, step_num, vault_path, logger, notes)
            if success:
                return {"success": True, "attempts": attempts, "error": None}
            last_error = "Step not found or already complete"
        except Exception as exc:
            last_error = str(exc)
            if logger:
                logger.log(
                    "plan_step_retry", plan_path.name, "warning",
                    details={"step": step_num, "attempt": attempts, "error": last_error},
                )

    return {"success": False, "attempts": attempts, "error": last_error}


class ExecutionMetrics:
    """Track plan execution metrics for Gold Tier reporting."""

    def __init__(self) -> None:
        self.steps_completed = 0
        self.steps_failed = 0
        self.steps_skipped = 0
        self.retries = 0
        self.domains_touched: set[str] = set()
        self.start_time: float | None = None
        self.end_time: float | None = None

    def start(self) -> None:
        import time
        self.start_time = time.time()

    def stop(self) -> None:
        import time
        self.end_time = time.time()

    @property
    def elapsed_seconds(self) -> float:
        if self.start_time is None:
            return 0.0
        end = self.end_time or __import__("time").time()
        return end - self.start_time

    def record_step(self, domain: str, success: bool, retries: int = 0) -> None:
        self.domains_touched.add(domain)
        self.retries += retries
        if success:
            self.steps_completed += 1
        else:
            self.steps_failed += 1

    def to_dict(self) -> dict:
        return {
            "steps_completed": self.steps_completed,
            "steps_failed": self.steps_failed,
            "steps_skipped": self.steps_skipped,
            "retries": self.retries,
            "domains_touched": sorted(self.domains_touched),
            "elapsed_seconds": round(self.elapsed_seconds, 2),
        }


# ---------------------------------------------------------------------------
# Orchestrator: process a task through the reasoning loop
# ---------------------------------------------------------------------------

def process_complex_task(
    file_path: Path,
    vault_path: Path,
    logger: AuditLogger,
) -> dict:
    """Full reasoning loop: detect complexity → create plan → execute steps.

    Returns a result dict with plan_file, steps_executed, status.
    """
    content = file_path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)

    # Step 1: Detect complexity
    complexity = detect_complexity(frontmatter, body)
    if not complexity["is_complex"]:
        return {
            "plan_file": None,
            "steps_executed": 0,
            "status": "not_complex",
            "reason": complexity["reason"],
        }

    # Step 2: Create plan
    plan_path = create_plan(file_path, frontmatter, body, vault_path, logger)

    # Step 3: Update source file with plan reference
    frontmatter["status"] = "plan_created"
    frontmatter["plan_file"] = plan_path.name
    frontmatter["plan_created_at"] = datetime.now(timezone.utc).isoformat()
    updated = serialize_frontmatter(frontmatter, body)
    file_path.write_text(updated, encoding="utf-8")

    # Step 4: Execute steps with retry and metrics (Gold Tier)
    _, _, steps = read_plan(plan_path)
    metrics = ExecutionMetrics()
    metrics.start()
    approval_blocked = False

    for step in steps:
        domain = step.get("domain", "general") if isinstance(step, dict) and "domain" in step else "general"

        if step["requires_approval"]:
            route_plan_to_approval(
                plan_path, vault_path, step["step_num"], logger,
            )
            approval_blocked = True
            metrics.steps_skipped += 1
            continue  # Gold Tier: continue with independent steps

        # Gold Tier: Execute with retry
        result = execute_step_with_retry(
            plan_path, step["step_num"], vault_path, logger,
            notes=f"Auto-executed: {step['description']}",
            max_retries=1,
        )
        metrics.record_step(domain, result["success"], result["attempts"] - 1)

    metrics.stop()

    # Step 5: If all steps done, complete the plan
    _, _, remaining = read_plan(plan_path)
    all_done = all(s["is_complete"] for s in remaining)

    if all_done:
        done_path = complete_plan(plan_path, vault_path, logger)
        return {
            "plan_file": plan_path.name,
            "steps_executed": metrics.steps_completed,
            "status": "completed",
            "done_path": str(done_path) if done_path else None,
            "metrics": metrics.to_dict(),
        }

    status = "awaiting_approval" if approval_blocked else "active"
    result_dict: dict = {
        "plan_file": plan_path.name,
        "steps_executed": metrics.steps_completed,
        "status": status,
        "metrics": metrics.to_dict(),
    }
    if approval_blocked:
        result_dict["blocked_at_step"] = next(
            (s["step_num"] for s in steps if s["requires_approval"]), None
        )
    return result_dict


def run_active_plans(vault_path: Path) -> list[dict]:
    """Resume execution of all active plans in Plans/."""
    plans_dir = vault_path / "Plans"
    if not plans_dir.exists():
        return []

    logger = AuditLogger(vault_path)
    results = []

    for plan_file in sorted(plans_dir.glob("PLAN_*.md")):
        frontmatter, body, steps = read_plan(plan_file)
        status = frontmatter.get("status", "unknown")

        if status not in ("active", "completed"):
            results.append({"file": plan_file.name, "status": status, "action": "skipped"})
            continue

        # Execute remaining steps
        executed = 0
        for step in steps:
            if step["is_complete"]:
                continue

            if step["requires_approval"]:
                route_plan_to_approval(
                    plan_file, vault_path, step["step_num"], logger,
                )
                results.append({
                    "file": plan_file.name,
                    "status": "awaiting_approval",
                    "action": f"blocked at step {step['step_num']}",
                    "steps_executed": executed,
                })
                break

            success = execute_step(
                plan_file, step["step_num"], vault_path, logger,
                notes=f"Resumed: {step['description']}",
            )
            if success:
                executed += 1
        else:
            # All steps done — complete the plan
            if all(s["is_complete"] for s in steps) or executed > 0:
                _, _, updated_steps = read_plan(plan_file)
                if all(s["is_complete"] for s in updated_steps):
                    complete_plan(plan_file, vault_path, logger)
                    results.append({
                        "file": plan_file.name,
                        "status": "completed",
                        "action": "moved to Done",
                        "steps_executed": executed,
                    })
                else:
                    results.append({
                        "file": plan_file.name,
                        "status": "active",
                        "action": f"executed {executed} steps",
                        "steps_executed": executed,
                    })

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Reasoning Loop for Complex Tasks")
    parser.add_argument("--vault-path", default=None)
    parser.add_argument("--file", default=None,
                        help="Process a specific task file through reasoning loop")
    parser.add_argument("--execute", default=None,
                        help="Execute steps in a specific plan file")
    parser.add_argument("--step", type=int, default=None,
                        help="Execute a specific step number (with --execute)")
    parser.add_argument("--run-plans", action="store_true",
                        help="Resume execution of all active plans")
    parser.add_argument("--check", default=None,
                        help="Check complexity of a file without creating a plan")
    args = parser.parse_args()

    vault = Path(args.vault_path or os.getenv("VAULT_PATH",
                 str(Path(__file__).parent.parent)))
    logger = AuditLogger(vault)

    if args.check:
        file_path = Path(args.check)
        if not file_path.is_absolute():
            file_path = vault / file_path
        content = file_path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(content)
        result = detect_complexity(fm, body)
        print(f"Complexity: {'COMPLEX' if result['is_complex'] else 'SIMPLE'}")
        print(f"Score: {result['score']}")
        print(f"Signals: {', '.join(result['matched_signals'])}")
        print(f"Reason: {result['reason']}")
        return

    if args.run_plans:
        results = run_active_plans(vault)
        if not results:
            print("No active plans found in Plans/.")
            return
        print(f"Processed {len(results)} plan(s):\n")
        for r in results:
            print(f"  [{r['status'].upper()}] {r['file']} — {r['action']}")
        return

    if args.execute:
        plan_path = Path(args.execute)
        if not plan_path.is_absolute():
            plan_path = vault / plan_path
        if not plan_path.exists():
            print(f"Plan not found: {plan_path}")
            sys.exit(1)

        if args.step:
            success = execute_step(plan_path, args.step, vault, logger)
            print(f"Step {args.step}: {'completed' if success else 'failed (not found or already done)'}")
        else:
            # Execute all remaining steps
            _, _, steps = read_plan(plan_path)
            executed = 0
            for step in steps:
                if step["is_complete"]:
                    continue
                if step["requires_approval"]:
                    print(f"  [BLOCKED] Step {step['step_num']} requires approval")
                    route_plan_to_approval(plan_path, vault, step["step_num"], logger)
                    break
                if execute_step(plan_path, step["step_num"], vault, logger):
                    executed += 1
                    print(f"  [DONE] Step {step['step_num']}: {step['description']}")
            print(f"\nExecuted {executed} step(s)")
        return

    if args.file:
        file_path = Path(args.file)
        if not file_path.is_absolute():
            file_path = vault / file_path
        if not file_path.exists():
            print(f"File not found: {file_path}")
            sys.exit(1)
        result = process_complex_task(file_path, vault, logger)
        print(f"Status: {result['status']}")
        if result.get("plan_file"):
            print(f"Plan: Plans/{result['plan_file']}")
        print(f"Steps executed: {result['steps_executed']}")
        return

    # Default: process all unplanned files in Needs_Action
    needs_action = vault / "Needs_Action"
    if not needs_action.exists():
        print("No Needs_Action/ folder found.")
        return

    files = sorted(needs_action.glob("*.md"))
    if not files:
        print("No .md files in Needs_Action/.")
        return

    complex_count = 0
    simple_count = 0
    for f in files:
        content = f.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(content)
        if fm.get("status") in ("planned", "done", "plan_created"):
            continue
        complexity = detect_complexity(fm, body)
        if complexity["is_complex"]:
            result = process_complex_task(f, vault, logger)
            print(f"  [PLAN] {f.name} -> Plans/{result.get('plan_file', '?')}")
            complex_count += 1
        else:
            simple_count += 1

    print(f"\nProcessed: {complex_count} complex (plans created), {simple_count} simple (skipped)")


if __name__ == "__main__":
    main()
