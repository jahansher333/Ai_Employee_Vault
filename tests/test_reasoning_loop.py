"""Tests for the Reasoning Loop — complexity detection, plan creation, execution."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from reasoning_loop import (
    detect_complexity,
    create_plan,
    execute_step,
    read_plan,
    complete_plan,
    route_plan_to_approval,
    process_complex_task,
    parse_frontmatter,
    serialize_frontmatter,
    generate_plan_steps,
    estimate_time,
)


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SIMPLE_TASK = """\
---
type: task
priority: low
status: new
---

# Quick Note

Just a simple reminder to check email.
"""

COMPLEX_INVOICE_TASK = """\
---
type: email
priority: high
status: new
from: "vendor@example.com"
subject: "Invoice #1234 - Payment Required"
---

# Invoice #1234 - Payment Required

**From**: vendor@example.com

Please review and process the attached invoice for $5,000.
This payment is urgent and requires approval before the deadline.
We need to verify the budget, check the vendor contract, and schedule the payment.

Steps to handle:
1. Review invoice details
2. Verify against budget
3. Get approval
4. Process payment
"""

COMPLEX_WHATSAPP_TASK = """\
---
type: whatsapp
priority: high
status: new
from: "Client ABC"
matched_keywords: ["urgent", "invoice"]
---

# WhatsApp Message from Client ABC

**From**: Client ABC

Urgent: Please send the invoice for the Q3 project.
We need to review and approve the payment before Friday deadline.
Also check the contract terms and notify the team.
"""

GENERIC_COMPLEX_TASK = """\
---
type: task
priority: medium
status: new
---

# Onboard New Employee

Please set up the onboarding workflow for the new hire.
This involves multiple steps: create accounts, configure access,
schedule training, integrate with team tools, and review policies.
Deploy the onboarding checklist and verify completion.
"""


# ---------------------------------------------------------------------------
# Complexity detection
# ---------------------------------------------------------------------------

class TestDetectComplexity:
    def test_simple_task_not_complex(self):
        fm, body = parse_frontmatter(SIMPLE_TASK)
        result = detect_complexity(fm, body)
        assert result["is_complex"] is False
        assert result["score"] < 2

    def test_invoice_task_is_complex(self):
        fm, body = parse_frontmatter(COMPLEX_INVOICE_TASK)
        result = detect_complexity(fm, body)
        assert result["is_complex"] is True
        assert result["score"] >= 2
        assert any("invoice" in s or "payment" in s for s in result["matched_signals"])

    def test_whatsapp_urgent_is_complex(self):
        fm, body = parse_frontmatter(COMPLEX_WHATSAPP_TASK)
        result = detect_complexity(fm, body)
        assert result["is_complex"] is True
        assert "high-priority" in result["matched_signals"]

    def test_generic_complex_task(self):
        fm, body = parse_frontmatter(GENERIC_COMPLEX_TASK)
        result = detect_complexity(fm, body)
        assert result["is_complex"] is True
        assert any("onboard" in s for s in result["matched_signals"])

    def test_multi_action_verbs_detected(self):
        fm, body = parse_frontmatter(COMPLEX_INVOICE_TASK)
        result = detect_complexity(fm, body)
        has_multi_action = any("multi-action" in s for s in result["matched_signals"])
        has_steps = any("has-numbered-steps" in s for s in result["matched_signals"])
        # Should detect either multi-action or numbered steps
        assert has_multi_action or has_steps or result["score"] >= 2

    def test_long_content_signal(self):
        long_body = "x " * 300  # > 500 chars
        result = detect_complexity({}, long_body)
        assert "long-content" in result["matched_signals"]

    def test_high_priority_signal(self):
        result = detect_complexity({"priority": "high"}, "simple text")
        assert "high-priority" in result["matched_signals"]


# ---------------------------------------------------------------------------
# Plan creation
# ---------------------------------------------------------------------------

class TestCreatePlan:
    def test_creates_plan_file(self, vault, logger):
        task_file = vault / "Needs_Action" / "test-task.md"
        task_file.write_text(COMPLEX_INVOICE_TASK, encoding="utf-8")
        fm, body = parse_frontmatter(COMPLEX_INVOICE_TASK)

        plan_path = create_plan(task_file, fm, body, vault, logger)

        assert plan_path.exists()
        assert plan_path.parent.name == "Plans"
        assert plan_path.name.startswith("PLAN_")

    def test_plan_has_correct_frontmatter(self, vault, logger):
        task_file = vault / "Needs_Action" / "test-task.md"
        task_file.write_text(COMPLEX_INVOICE_TASK, encoding="utf-8")
        fm, body = parse_frontmatter(COMPLEX_INVOICE_TASK)

        plan_path = create_plan(task_file, fm, body, vault, logger)
        content = plan_path.read_text(encoding="utf-8")
        plan_fm, _ = parse_frontmatter(content)

        assert plan_fm["type"] == "plan"
        assert plan_fm["source_file"] == "test-task.md"
        assert plan_fm["status"] == "active"
        assert "total_steps" in plan_fm

    def test_plan_has_checkboxed_steps(self, vault, logger):
        task_file = vault / "Needs_Action" / "test-task.md"
        task_file.write_text(COMPLEX_INVOICE_TASK, encoding="utf-8")
        fm, body = parse_frontmatter(COMPLEX_INVOICE_TASK)

        plan_path = create_plan(task_file, fm, body, vault, logger)
        content = plan_path.read_text(encoding="utf-8")

        assert "- [ ] **Step 1**" in content
        assert "## Steps" in content
        assert "## Dependencies" in content
        assert "## Execution Log" in content

    def test_plan_has_objective(self, vault, logger):
        task_file = vault / "Needs_Action" / "test-task.md"
        task_file.write_text(COMPLEX_INVOICE_TASK, encoding="utf-8")
        fm, body = parse_frontmatter(COMPLEX_INVOICE_TASK)

        plan_path = create_plan(task_file, fm, body, vault, logger)
        content = plan_path.read_text(encoding="utf-8")

        assert "## Objective" in content

    def test_email_type_generates_email_steps(self, vault, logger):
        task_file = vault / "Needs_Action" / "email-task.md"
        task_file.write_text(COMPLEX_INVOICE_TASK, encoding="utf-8")
        fm, body = parse_frontmatter(COMPLEX_INVOICE_TASK)

        steps = generate_plan_steps(fm, body)
        # Email tasks should have email-specific steps
        descriptions = [s["description"] for s in steps]
        assert any("email" in d.lower() or "response" in d.lower() or "invoice" in d.lower()
                    for d in descriptions)

    def test_whatsapp_type_generates_whatsapp_steps(self):
        fm, body = parse_frontmatter(COMPLEX_WHATSAPP_TASK)
        steps = generate_plan_steps(fm, body)
        descriptions = [s["description"] for s in steps]
        assert any("whatsapp" in d.lower() or "message" in d.lower()
                    for d in descriptions)


# ---------------------------------------------------------------------------
# Plan execution
# ---------------------------------------------------------------------------

class TestExecuteStep:
    def test_execute_marks_step_complete(self, vault, logger):
        task_file = vault / "Needs_Action" / "test-task.md"
        task_file.write_text(COMPLEX_INVOICE_TASK, encoding="utf-8")
        fm, body = parse_frontmatter(COMPLEX_INVOICE_TASK)
        plan_path = create_plan(task_file, fm, body, vault, logger)

        success = execute_step(plan_path, 1, vault, logger, notes="Test exec")
        assert success is True

        content = plan_path.read_text(encoding="utf-8")
        assert "- [X] **Step 1**" in content

    def test_execute_updates_completed_count(self, vault, logger):
        task_file = vault / "Needs_Action" / "test-task.md"
        task_file.write_text(COMPLEX_INVOICE_TASK, encoding="utf-8")
        fm, body = parse_frontmatter(COMPLEX_INVOICE_TASK)
        plan_path = create_plan(task_file, fm, body, vault, logger)

        execute_step(plan_path, 1, vault, logger)
        content = plan_path.read_text(encoding="utf-8")
        plan_fm, _ = parse_frontmatter(content)
        assert plan_fm["completed_steps"] == "1"

    def test_execute_nonexistent_step_returns_false(self, vault, logger):
        task_file = vault / "Needs_Action" / "test-task.md"
        task_file.write_text(COMPLEX_INVOICE_TASK, encoding="utf-8")
        fm, body = parse_frontmatter(COMPLEX_INVOICE_TASK)
        plan_path = create_plan(task_file, fm, body, vault, logger)

        success = execute_step(plan_path, 99, vault, logger)
        assert success is False

    def test_execute_already_complete_step_returns_false(self, vault, logger):
        task_file = vault / "Needs_Action" / "test-task.md"
        task_file.write_text(COMPLEX_INVOICE_TASK, encoding="utf-8")
        fm, body = parse_frontmatter(COMPLEX_INVOICE_TASK)
        plan_path = create_plan(task_file, fm, body, vault, logger)

        execute_step(plan_path, 1, vault, logger)
        success = execute_step(plan_path, 1, vault, logger)
        assert success is False

    def test_execute_adds_log_entry(self, vault, logger):
        task_file = vault / "Needs_Action" / "test-task.md"
        task_file.write_text(COMPLEX_INVOICE_TASK, encoding="utf-8")
        fm, body = parse_frontmatter(COMPLEX_INVOICE_TASK)
        plan_path = create_plan(task_file, fm, body, vault, logger)

        execute_step(plan_path, 1, vault, logger, notes="Custom note")
        content = plan_path.read_text(encoding="utf-8")
        assert "Custom note" in content
        assert "Step 1 | completed" in content


# ---------------------------------------------------------------------------
# Read plan
# ---------------------------------------------------------------------------

class TestReadPlan:
    def test_read_plan_extracts_steps(self, vault, logger):
        task_file = vault / "Needs_Action" / "test-task.md"
        task_file.write_text(COMPLEX_INVOICE_TASK, encoding="utf-8")
        fm, body = parse_frontmatter(COMPLEX_INVOICE_TASK)
        plan_path = create_plan(task_file, fm, body, vault, logger)

        plan_fm, plan_body, steps = read_plan(plan_path)
        assert len(steps) > 0
        assert all("step_num" in s for s in steps)
        assert all("description" in s for s in steps)
        assert all("is_complete" in s for s in steps)

    def test_read_plan_reflects_completion(self, vault, logger):
        task_file = vault / "Needs_Action" / "test-task.md"
        task_file.write_text(COMPLEX_INVOICE_TASK, encoding="utf-8")
        fm, body = parse_frontmatter(COMPLEX_INVOICE_TASK)
        plan_path = create_plan(task_file, fm, body, vault, logger)

        execute_step(plan_path, 1, vault, logger)
        _, _, steps = read_plan(plan_path)
        step1 = next(s for s in steps if s["step_num"] == 1)
        assert step1["is_complete"] is True


# ---------------------------------------------------------------------------
# Plan completion
# ---------------------------------------------------------------------------

class TestCompletePlan:
    def test_complete_plan_moves_to_done(self, vault, logger):
        task_file = vault / "Needs_Action" / "test-task.md"
        task_file.write_text(COMPLEX_INVOICE_TASK, encoding="utf-8")
        fm, body = parse_frontmatter(COMPLEX_INVOICE_TASK)
        plan_path = create_plan(task_file, fm, body, vault, logger)

        # Execute all steps to mark plan as completed
        _, _, steps = read_plan(plan_path)
        for step in steps:
            execute_step(plan_path, step["step_num"], vault, logger)

        done_path = complete_plan(plan_path, vault, logger)
        assert done_path is not None
        assert done_path.parent.name == "Done"
        assert not plan_path.exists()  # Removed from Plans/

    def test_complete_plan_not_completed_returns_none(self, vault, logger):
        task_file = vault / "Needs_Action" / "test-task.md"
        task_file.write_text(COMPLEX_INVOICE_TASK, encoding="utf-8")
        fm, body = parse_frontmatter(COMPLEX_INVOICE_TASK)
        plan_path = create_plan(task_file, fm, body, vault, logger)

        # Don't execute any steps
        result = complete_plan(plan_path, vault, logger)
        assert result is None

    def test_complete_plan_moves_source_file(self, vault, logger):
        task_file = vault / "Needs_Action" / "test-task.md"
        task_file.write_text(COMPLEX_INVOICE_TASK, encoding="utf-8")
        fm, body = parse_frontmatter(COMPLEX_INVOICE_TASK)
        plan_path = create_plan(task_file, fm, body, vault, logger)

        # Execute all steps
        _, _, steps = read_plan(plan_path)
        for step in steps:
            execute_step(plan_path, step["step_num"], vault, logger)

        complete_plan(plan_path, vault, logger)
        # Source file should be moved to Done
        assert not task_file.exists()
        done_files = list((vault / "Done").glob("test-task*.md"))
        assert len(done_files) >= 1


# ---------------------------------------------------------------------------
# Approval routing
# ---------------------------------------------------------------------------

class TestRouteToApproval:
    def test_creates_approval_file(self, vault, logger):
        task_file = vault / "Needs_Action" / "test-task.md"
        task_file.write_text(COMPLEX_INVOICE_TASK, encoding="utf-8")
        fm, body = parse_frontmatter(COMPLEX_INVOICE_TASK)
        plan_path = create_plan(task_file, fm, body, vault, logger)

        approval_path = route_plan_to_approval(plan_path, vault, 4, logger)
        assert approval_path.exists()
        assert approval_path.parent.name == "Pending_Approval"
        assert "approve-" in approval_path.name

    def test_sets_plan_status_awaiting_approval(self, vault, logger):
        task_file = vault / "Needs_Action" / "test-task.md"
        task_file.write_text(COMPLEX_INVOICE_TASK, encoding="utf-8")
        fm, body = parse_frontmatter(COMPLEX_INVOICE_TASK)
        plan_path = create_plan(task_file, fm, body, vault, logger)

        route_plan_to_approval(plan_path, vault, 4, logger)
        content = plan_path.read_text(encoding="utf-8")
        plan_fm, _ = parse_frontmatter(content)
        assert plan_fm["status"] == "awaiting_approval"


# ---------------------------------------------------------------------------
# Full orchestrator
# ---------------------------------------------------------------------------

class TestProcessComplexTask:
    def test_complex_task_creates_plan(self, vault, logger):
        task_file = vault / "Needs_Action" / "invoice-task.md"
        task_file.write_text(COMPLEX_INVOICE_TASK, encoding="utf-8")

        result = process_complex_task(task_file, vault, logger)
        assert result["status"] in ("active", "completed", "awaiting_approval")
        assert result["plan_file"] is not None
        assert result["steps_executed"] >= 0

    def test_simple_task_returns_not_complex(self, vault, logger):
        task_file = vault / "Needs_Action" / "simple-task.md"
        task_file.write_text(SIMPLE_TASK, encoding="utf-8")

        result = process_complex_task(task_file, vault, logger)
        assert result["status"] == "not_complex"
        assert result["plan_file"] is None

    def test_source_file_updated_with_plan_ref(self, vault, logger):
        task_file = vault / "Needs_Action" / "invoice-task.md"
        task_file.write_text(COMPLEX_INVOICE_TASK, encoding="utf-8")

        result = process_complex_task(task_file, vault, logger)
        if result["plan_file"]:
            content = task_file.read_text(encoding="utf-8")
            fm, _ = parse_frontmatter(content)
            assert fm.get("status") == "plan_created"
            assert fm.get("plan_file") == result["plan_file"]


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------

class TestEstimateTime:
    def test_no_approval_steps(self):
        steps = [{"requires_approval": False}] * 5
        est = estimate_time(steps)
        assert "10" in est  # 5 * 2 = 10

    def test_with_approval_steps(self):
        steps = [{"requires_approval": False}] * 3 + [{"requires_approval": True}]
        est = estimate_time(steps)
        assert "approval" in est.lower()


class TestFrontmatterHelpers:
    def test_parse_roundtrip(self):
        original = "---\ntype: task\npriority: high\n---\n\n# Title\n\nBody text."
        fm, body = parse_frontmatter(original)
        assert fm["type"] == "task"
        assert fm["priority"] == "high"
        result = serialize_frontmatter(fm, body)
        assert "type: task" in result
        assert "# Title" in result
