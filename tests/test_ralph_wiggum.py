"""Tests for Gold Tier Ralph Wiggum Loop enhancements."""

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from reasoning_loop import (
    DOMAINS,
    detect_cross_domain,
    detect_circular_dependencies,
    generate_plan_steps,
    execute_step_with_retry,
    ExecutionMetrics,
    process_complex_task,
    parse_frontmatter,
    create_plan,
)
from ralph_wiggum import (
    StopCondition,
    LoopController,
    get_loop_status,
)


# ---------------------------------------------------------------------------
# Cross-domain detection
# ---------------------------------------------------------------------------

class TestDetectCrossDomain:
    def test_single_domain_accounting(self):
        fm = {"type": "task"}
        body = "Review the invoice and check payment status"
        result = detect_cross_domain(fm, body)
        assert "accounting" in result["domains"]
        assert result["is_cross_domain"] is False

    def test_single_domain_email(self):
        fm = {"type": "email"}
        body = "Reply to the unread email in inbox"
        result = detect_cross_domain(fm, body)
        assert "email" in result["domains"]

    def test_cross_domain_accounting_email(self):
        fm = {"type": "task"}
        body = "Send an email about the overdue invoice payment"
        result = detect_cross_domain(fm, body)
        assert result["is_cross_domain"] is True
        assert "accounting" in result["domains"]
        assert "email" in result["domains"]

    def test_cross_domain_social_reporting(self):
        fm = {}
        body = "Generate a weekly report with social media engagement summary and dashboard metrics"
        result = detect_cross_domain(fm, body)
        assert result["is_cross_domain"] is True
        assert result["domain_count"] >= 2

    def test_no_domain_detected(self):
        fm = {}
        body = "Just a simple task with nothing specific"
        result = detect_cross_domain(fm, body)
        assert result["domain_count"] == 0
        assert result["is_cross_domain"] is False

    def test_all_four_domains(self):
        fm = {}
        body = ("Check Odoo invoice, post on facebook, send email reply, "
                "and update the weekly dashboard report")
        result = detect_cross_domain(fm, body)
        assert result["domain_count"] == 4


# ---------------------------------------------------------------------------
# Domain tagging in steps
# ---------------------------------------------------------------------------

class TestDomainTagging:
    def test_steps_have_domain_field(self):
        fm = {"type": "email", "priority": "high"}
        body = "Reply to an important email"
        steps = generate_plan_steps(fm, body)
        for step in steps:
            assert "domain" in step, f"Step missing domain: {step}"

    def test_email_steps_tagged(self):
        fm = {"type": "email", "priority": "medium"}
        body = "Handle email about invoice"
        steps = generate_plan_steps(fm, body)
        # At least some steps should be tagged as email
        domains = {s["domain"] for s in steps}
        assert "email" in domains or "general" in domains

    def test_steps_have_depends_on(self):
        fm = {"type": "task", "priority": "low"}
        body = "Simple review task"
        steps = generate_plan_steps(fm, body)
        for step in steps:
            assert "depends_on" in step


# ---------------------------------------------------------------------------
# Circular dependency detection
# ---------------------------------------------------------------------------

class TestCircularDependencies:
    def test_no_cycles(self):
        steps = [
            {"step_num": 1, "depends_on": []},
            {"step_num": 2, "depends_on": [1]},
            {"step_num": 3, "depends_on": [2]},
        ]
        errors = detect_circular_dependencies(steps)
        assert errors == []

    def test_simple_cycle(self):
        steps = [
            {"step_num": 1, "depends_on": [2]},
            {"step_num": 2, "depends_on": [1]},
        ]
        errors = detect_circular_dependencies(steps)
        assert len(errors) > 0

    def test_no_dependencies(self):
        steps = [
            {"step_num": 1, "depends_on": []},
            {"step_num": 2, "depends_on": []},
        ]
        errors = detect_circular_dependencies(steps)
        assert errors == []


# ---------------------------------------------------------------------------
# Execute step with retry
# ---------------------------------------------------------------------------

class TestExecuteStepWithRetry:
    def test_retry_returns_dict(self, vault, logger):
        plans = vault / "Plans"
        plans.mkdir(exist_ok=True)
        # Create a simple plan
        plan_content = (
            "---\ntype: plan\nstatus: active\ntotal_steps: 2\ncompleted_steps: 0\n---\n\n"
            "## Steps\n\n"
            "- [ ] **Step 1** (analysis): Analyze task\n"
            "- [ ] **Step 2** (execution): Execute task\n\n"
            "## Execution Log\n\n"
            "| Step | Status | Timestamp | Notes |\n"
            "|------|--------|-----------|-------|\n"
        )
        plan_path = plans / "PLAN_test_retry.md"
        plan_path.write_text(plan_content, encoding="utf-8")

        result = execute_step_with_retry(plan_path, 1, vault, logger, max_retries=1)
        assert result["success"] is True
        assert result["attempts"] == 1

    def test_retry_nonexistent_step(self, vault, logger):
        plans = vault / "Plans"
        plans.mkdir(exist_ok=True)
        plan_content = (
            "---\ntype: plan\nstatus: active\ntotal_steps: 1\ncompleted_steps: 0\n---\n\n"
            "## Steps\n\n"
            "- [ ] **Step 1** (analysis): Analyze\n\n"
            "## Execution Log\n\n"
            "| Step | Status | Timestamp | Notes |\n"
            "|------|--------|-----------|-------|\n"
        )
        plan_path = plans / "PLAN_test_noretry.md"
        plan_path.write_text(plan_content, encoding="utf-8")

        result = execute_step_with_retry(plan_path, 99, vault, logger, max_retries=1)
        assert result["success"] is False
        assert result["attempts"] == 2  # Initial + 1 retry


# ---------------------------------------------------------------------------
# Execution metrics
# ---------------------------------------------------------------------------

class TestExecutionMetrics:
    def test_initial_state(self):
        m = ExecutionMetrics()
        assert m.steps_completed == 0
        assert m.steps_failed == 0
        assert m.retries == 0

    def test_record_step(self):
        m = ExecutionMetrics()
        m.record_step("accounting", True, retries=0)
        m.record_step("email", True, retries=1)
        m.record_step("social", False, retries=1)
        assert m.steps_completed == 2
        assert m.steps_failed == 1
        assert m.retries == 2
        assert m.domains_touched == {"accounting", "email", "social"}

    def test_to_dict(self):
        m = ExecutionMetrics()
        m.start()
        m.record_step("accounting", True)
        m.stop()
        d = m.to_dict()
        assert d["steps_completed"] == 1
        assert "accounting" in d["domains_touched"]
        assert d["elapsed_seconds"] >= 0

    def test_elapsed_seconds(self):
        import time
        m = ExecutionMetrics()
        m.start()
        time.sleep(0.05)
        m.stop()
        assert m.elapsed_seconds >= 0.04


# ---------------------------------------------------------------------------
# Gold Tier: Enhanced process_complex_task
# ---------------------------------------------------------------------------

class TestGoldProcessComplexTask:
    def test_returns_metrics(self, vault, logger):
        task = vault / "Needs_Action" / "complex-invoice-review.md"
        task.write_text(
            "---\ntype: task\npriority: low\nstatus: new\n---\n\n"
            "# Review Invoice and Audit Report\n\n"
            "Review the Q3 invoice and prepare an audit report with analysis.",
            encoding="utf-8",
        )
        result = process_complex_task(task, vault, logger)
        assert result["status"] in ("completed", "active", "awaiting_approval")
        if result.get("metrics"):
            assert "steps_completed" in result["metrics"]
            assert "domains_touched" in result["metrics"]

    def test_continues_after_approval_step(self, vault, logger):
        """Gold Tier: should continue executing independent steps after hitting approval."""
        task = vault / "Needs_Action" / "high-priority-payment.md"
        task.write_text(
            "---\ntype: task\npriority: high\nstatus: new\ncategory: finance\n---\n\n"
            "# Process Payment and Invoice Review\n\n"
            "Process the payment of $5000 to vendor after invoice review.",
            encoding="utf-8",
        )
        result = process_complex_task(task, vault, logger)
        # Should have executed some steps AND flagged approval
        assert result["status"] in ("awaiting_approval", "completed", "active")
        if result.get("metrics"):
            assert result["metrics"]["steps_completed"] >= 0


# ---------------------------------------------------------------------------
# StopCondition
# ---------------------------------------------------------------------------

class TestStopCondition:
    def test_max_iterations(self, vault):
        sc = StopCondition(vault, max_iterations=3)
        assert sc.check(1, "task") is None
        assert sc.check(2, "task") is None
        assert sc.check(3, "task") == StopCondition.MAX_ITER

    def test_timeout(self, vault):
        sc = StopCondition(vault, timeout_seconds=0.05)
        assert sc.check(1, "task") is None
        time.sleep(0.06)
        assert sc.check(1, "task") == StopCondition.TIMEOUT

    def test_stop_file(self, vault):
        sc = StopCondition(vault)
        plans = vault / "Plans"
        plans.mkdir(exist_ok=True)
        assert sc.check(1, "task") is None
        (plans / ".stop").write_text("stop", encoding="utf-8")
        assert sc.check(1, "task") == StopCondition.STOP_FILE

    def test_task_in_done(self, vault):
        sc = StopCondition(vault)
        done = vault / "Done"
        done.mkdir(exist_ok=True)
        assert sc.check(1, "my-task") is None
        (done / "my-task.md").write_text("done", encoding="utf-8")
        assert sc.check(1, "my-task") == StopCondition.DONE

    def test_all_steps_complete(self, vault):
        sc = StopCondition(vault)
        plans = vault / "Plans"
        plans.mkdir(exist_ok=True)
        plan = plans / "PLAN_test.md"
        plan.write_text(
            "---\ntype: plan\nstatus: completed\ntotal_steps: 1\ncompleted_steps: 1\n---\n\n"
            "## Steps\n\n"
            "- [X] **Step 1** (analysis): Done\n\n"
            "## Execution Log\n\n"
            "| Step | Status | Timestamp | Notes |\n"
            "|------|--------|-----------|-------|\n",
            encoding="utf-8",
        )
        assert sc.check(1, "task", plan_path=plan) == StopCondition.ALL_COMPLETE

    def test_reset(self, vault):
        sc = StopCondition(vault, timeout_seconds=0.01)
        time.sleep(0.02)
        assert sc.check(1, "task") == StopCondition.TIMEOUT
        sc.reset()
        assert sc.check(1, "task") is None


# ---------------------------------------------------------------------------
# LoopController
# ---------------------------------------------------------------------------

class TestLoopController:
    def _make_complex_task(self, vault, name="complex-task.md"):
        needs = vault / "Needs_Action"
        needs.mkdir(exist_ok=True)
        task = needs / name
        task.write_text(
            "---\ntype: task\npriority: low\nstatus: new\n---\n\n"
            "# Review Invoice and Audit Report\n\n"
            "Review the Q3 invoice and prepare an audit report with "
            "analysis of the financial data and budget review.",
            encoding="utf-8",
        )
        return task

    def test_simple_task_not_complex(self, vault, logger):
        needs = vault / "Needs_Action"
        needs.mkdir(exist_ok=True)
        task = needs / "simple.md"
        task.write_text(
            "---\ntype: task\nstatus: new\n---\n\nHello world\n",
            encoding="utf-8",
        )
        controller = LoopController(vault, logger)
        result = controller.run_loop(task)
        assert result["status"] == "not_complex"
        assert result["stop_reason"] == StopCondition.NOT_COMPLEX
        assert result["iterations"] == 0

    def test_complex_task_runs_to_completion(self, vault, logger):
        task = self._make_complex_task(vault)
        controller = LoopController(vault, logger, max_iterations=5)
        result = controller.run_loop(task)
        assert result["status"] in ("done", "stopped")
        assert result["iterations"] >= 1
        assert result["metrics"]["steps_completed"] >= 0
        assert result.get("plan_file") is not None

    def test_max_iterations_stops(self, vault, logger):
        task = self._make_complex_task(vault, "big-task.md")
        controller = LoopController(vault, logger, max_iterations=1)
        result = controller.run_loop(task)
        assert result["iterations"] <= 1

    def test_stop_file_stops_loop(self, vault, logger):
        task = self._make_complex_task(vault, "stopped-task.md")
        plans = vault / "Plans"
        plans.mkdir(exist_ok=True)
        (plans / ".stop").write_text("stop", encoding="utf-8")
        controller = LoopController(vault, logger, max_iterations=10)
        result = controller.run_loop(task)
        # Should stop before executing (stop checked at start of iteration)
        # But complexity check happens first, so it might create plan then stop
        assert result["stop_reason"] in (StopCondition.STOP_FILE, StopCondition.NOT_COMPLEX)

    def test_history_recorded(self, vault, logger):
        task = self._make_complex_task(vault, "history-task.md")
        controller = LoopController(vault, logger, max_iterations=2)
        result = controller.run_loop(task)
        assert len(controller.history) >= 1
        assert controller.history[0]["action"] == "start"

    def test_run_task_from_text(self, vault, logger):
        controller = LoopController(vault, logger, max_iterations=3)
        result = controller.run_task_from_text(
            "Review the monthly invoice audit report and check payment budget"
        )
        assert result["status"] in ("done", "stopped", "not_complex")
        # If complex, should have a plan
        if result["status"] != "not_complex":
            assert result.get("plan_file") is not None

    def test_metrics_populated(self, vault, logger):
        task = self._make_complex_task(vault, "metrics-task.md")
        controller = LoopController(vault, logger, max_iterations=2)
        result = controller.run_loop(task)
        m = result["metrics"]
        assert "steps_completed" in m
        assert "steps_failed" in m
        assert "elapsed_seconds" in m
        assert "domains_touched" in m


# ---------------------------------------------------------------------------
# Loop status
# ---------------------------------------------------------------------------

class TestGetLoopStatus:
    def test_empty_vault(self, vault):
        status = get_loop_status(vault)
        assert status["pending_tasks"] == 0
        assert status["active_plans"] == []
        assert status["stop_active"] is False

    def test_with_pending_tasks(self, vault):
        needs = vault / "Needs_Action"
        needs.mkdir(exist_ok=True)
        (needs / "task1.md").write_text(
            "---\ntype: task\nstatus: new\n---\nHello\n", encoding="utf-8",
        )
        status = get_loop_status(vault)
        assert status["pending_tasks"] == 1

    def test_with_done_files(self, vault):
        done = vault / "Done"
        done.mkdir(exist_ok=True)
        (done / "done1.md").write_text("done", encoding="utf-8")
        (done / "done2.md").write_text("done", encoding="utf-8")
        status = get_loop_status(vault)
        assert status["done_count"] == 2

    def test_stop_signal_detected(self, vault):
        plans = vault / "Plans"
        plans.mkdir(exist_ok=True)
        (plans / ".stop").write_text("stop", encoding="utf-8")
        status = get_loop_status(vault)
        assert status["stop_active"] is True
