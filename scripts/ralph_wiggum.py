"""Ralph Wiggum Loop — autonomous task iteration until Done.

Gold Tier: Wraps the reasoning loop with an autonomous iteration controller.
Creates plans, executes steps, checks Done/ folder, and re-injects the prompt
until the task is complete or a stop condition is met.

Stop conditions (any of):
    1. Task moved to Done/ folder
    2. Max iterations reached (default: 10)
    3. Timeout exceeded (default: 300s)
    4. Stop file exists: Plans/.stop
    5. All plan steps completed
    6. Plan blocked at approval step (pauses, doesn't terminate)

Usage:
    python scripts/ralph_wiggum.py --task "Process the Q3 invoice audit"
    python scripts/ralph_wiggum.py --file Needs_Action/complex-task.md
    python scripts/ralph_wiggum.py --watch              # Watch for new tasks
    python scripts/ralph_wiggum.py --status              # Show loop status
    python scripts/ralph_wiggum.py --stop                # Create stop signal
    python scripts/ralph_wiggum.py --max-iterations 5 --file Needs_Action/task.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger
from reasoning_loop import (
    detect_complexity,
    detect_cross_domain,
    parse_frontmatter,
    serialize_frontmatter,
    create_plan,
    read_plan,
    execute_step_with_retry,
    complete_plan,
    route_plan_to_approval,
    ExecutionMetrics,
)


# ---------------------------------------------------------------------------
# Stop conditions
# ---------------------------------------------------------------------------

class StopCondition:
    """Evaluates whether the loop should stop."""

    DONE = "task_in_done"
    MAX_ITER = "max_iterations"
    TIMEOUT = "timeout"
    STOP_FILE = "stop_file"
    ALL_COMPLETE = "all_steps_complete"
    NOT_COMPLEX = "not_complex"

    def __init__(
        self,
        vault_path: Path,
        max_iterations: int = 10,
        timeout_seconds: float = 300.0,
    ) -> None:
        self.vault_path = vault_path
        self.max_iterations = max_iterations
        self.timeout_seconds = timeout_seconds
        self.start_time = time.time()

    @property
    def stop_file(self) -> Path:
        return self.vault_path / "Plans" / ".stop"

    def check(self, iteration: int, task_name: str, plan_path: Path | None = None) -> str | None:
        """Check all stop conditions. Returns reason string or None to continue."""
        # 1. Stop file
        if self.stop_file.exists():
            return self.STOP_FILE

        # 2. Max iterations
        if iteration >= self.max_iterations:
            return self.MAX_ITER

        # 3. Timeout
        elapsed = time.time() - self.start_time
        if elapsed >= self.timeout_seconds:
            return self.TIMEOUT

        # 4. Task in Done/
        done_dir = self.vault_path / "Done"
        if done_dir.exists():
            # Check if any file in Done matches the task name
            for f in done_dir.iterdir():
                if task_name and task_name in f.name:
                    return self.DONE

        # 5. All plan steps complete
        if plan_path and plan_path.exists():
            try:
                _, _, steps = read_plan(plan_path)
                if steps and all(s["is_complete"] for s in steps):
                    return self.ALL_COMPLETE
            except Exception:
                pass

        return None  # Continue

    def reset(self) -> None:
        self.start_time = time.time()


# ---------------------------------------------------------------------------
# Loop Controller
# ---------------------------------------------------------------------------

class LoopController:
    """Autonomous loop that iterates until a task reaches Done/.

    Each iteration:
    1. Check stop conditions
    2. If no plan exists: create one via reasoning loop
    3. Execute next batch of steps
    4. Check if plan is complete → move to Done/
    5. If not done, re-inject (next iteration)
    """

    def __init__(
        self,
        vault_path: Path,
        logger: AuditLogger | None = None,
        max_iterations: int = 10,
        timeout_seconds: float = 300.0,
    ) -> None:
        self.vault_path = vault_path
        self.logger = logger or AuditLogger(vault_path)
        self.stop = StopCondition(vault_path, max_iterations, timeout_seconds)
        self.metrics = ExecutionMetrics()
        self.iteration = 0
        self.plan_path: Path | None = None
        self.status = "idle"
        self._history: list[dict] = []

    @property
    def history(self) -> list[dict]:
        return list(self._history)

    def _log_iteration(self, action: str, details: dict | None = None) -> None:
        entry = {
            "iteration": self.iteration,
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(details or {}),
        }
        self._history.append(entry)
        if self.logger:
            self.logger.log(
                f"ralph_wiggum_{action}",
                self.plan_path.name if self.plan_path else "no_plan",
                "info",
                details=entry,
            )

    def run_loop(self, file_path: Path) -> dict:
        """Run the autonomous loop on a task file until Done or stop condition.

        Returns dict with status, iterations, metrics, stop_reason.
        """
        self.status = "running"
        self.metrics.start()
        self.stop.reset()

        content = file_path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(content)
        task_name = file_path.stem

        # Check complexity first
        complexity = detect_complexity(frontmatter, body)
        if not complexity["is_complex"]:
            self.status = "not_complex"
            self._log_iteration("skipped", {"reason": complexity["reason"]})
            return {
                "status": "not_complex",
                "iterations": 0,
                "reason": complexity["reason"],
                "metrics": self.metrics.to_dict(),
                "stop_reason": StopCondition.NOT_COMPLEX,
            }

        # Detect domains for reporting
        domains = detect_cross_domain(frontmatter, body)
        self._log_iteration("start", {
            "task": task_name,
            "domains": domains["domains"],
            "is_cross_domain": domains["is_cross_domain"],
        })

        stop_reason = None

        while True:
            self.iteration += 1

            # Check stop conditions
            stop_reason = self.stop.check(self.iteration, task_name, self.plan_path)
            if stop_reason:
                self._log_iteration("stop", {"reason": stop_reason})
                break

            # Phase 1: Create plan if needed
            if self.plan_path is None or not self.plan_path.exists():
                self.plan_path = create_plan(
                    file_path, frontmatter, body, self.vault_path, self.logger,
                )
                self._log_iteration("plan_created", {"plan": self.plan_path.name})

                # Update source file
                frontmatter["status"] = "plan_created"
                frontmatter["plan_file"] = self.plan_path.name
                updated = serialize_frontmatter(frontmatter, body)
                file_path.write_text(updated, encoding="utf-8")

            # Phase 2: Execute steps
            _, _, steps = read_plan(self.plan_path)
            executed_this_iteration = 0
            blocked_at_approval = False

            for step in steps:
                if step["is_complete"]:
                    continue

                if step["requires_approval"]:
                    route_plan_to_approval(
                        self.plan_path, self.vault_path, step["step_num"], self.logger,
                    )
                    blocked_at_approval = True
                    self.metrics.steps_skipped += 1
                    continue  # Continue with independent steps

                domain = step.get("domain", "general") if isinstance(step, dict) else "general"
                result = execute_step_with_retry(
                    self.plan_path, step["step_num"], self.vault_path, self.logger,
                    notes=f"Loop iter {self.iteration}: {step['description']}",
                    max_retries=1,
                )
                retries = result["attempts"] - 1
                self.metrics.record_step(domain, result["success"], retries)
                if result["success"]:
                    executed_this_iteration += 1

            self._log_iteration("iteration_done", {
                "executed": executed_this_iteration,
                "blocked_at_approval": blocked_at_approval,
            })

            # Phase 3: Check completion
            _, _, updated_steps = read_plan(self.plan_path)
            all_done = updated_steps and all(s["is_complete"] for s in updated_steps)

            if all_done:
                done_path = complete_plan(self.plan_path, self.vault_path, self.logger)
                self._log_iteration("completed", {
                    "done_path": str(done_path) if done_path else None,
                })
                stop_reason = StopCondition.ALL_COMPLETE
                break

            if blocked_at_approval and executed_this_iteration == 0:
                # All remaining steps need approval — pause
                self._log_iteration("paused_for_approval")
                stop_reason = "awaiting_approval"
                break

            # If we executed 0 steps and didn't hit approval, no progress — stop
            if executed_this_iteration == 0 and not blocked_at_approval:
                self._log_iteration("no_progress")
                stop_reason = "no_progress"
                break

        self.metrics.stop()
        self.status = "done" if stop_reason == StopCondition.ALL_COMPLETE else "stopped"

        return {
            "status": self.status,
            "iterations": self.iteration,
            "stop_reason": stop_reason,
            "plan_file": self.plan_path.name if self.plan_path else None,
            "metrics": self.metrics.to_dict(),
            "history": self._history,
        }

    def run_task_from_text(self, description: str) -> dict:
        """Create a task file from text and run the loop on it.

        Returns the same dict as run_loop().
        """
        needs_action = self.vault_path / "Needs_Action"
        needs_action.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%H%M%S")
        safe_desc = description[:50].replace(" ", "-").replace("/", "-")
        filename = f"TASK_{timestamp}_{safe_desc}.md"
        task_path = needs_action / filename

        now = datetime.now(timezone.utc).isoformat()
        content = (
            f"---\n"
            f"type: task\n"
            f"priority: medium\n"
            f"status: new\n"
            f"created_at: \"{now}\"\n"
            f"source: ralph_wiggum\n"
            f"---\n\n"
            f"# {description}\n\n"
            f"{description}\n"
        )
        task_path.write_text(content, encoding="utf-8")
        self._log_iteration("task_created", {"file": filename})

        return self.run_loop(task_path)


def watch_for_tasks(
    vault_path: Path,
    poll_interval: float = 10.0,
    max_iterations: int = 10,
    logger: AuditLogger | None = None,
) -> None:
    """Watch Needs_Action/ for new complex tasks and process them.

    Runs indefinitely until interrupted or stop file created.
    """
    logger = logger or AuditLogger(vault_path)
    needs_action = vault_path / "Needs_Action"
    processed: set[str] = set()
    stop_file = vault_path / "Plans" / ".stop"

    print(f"[Ralph Wiggum] Watching {needs_action} for complex tasks...")
    print(f"  Stop: create {stop_file} or press Ctrl+C")

    while True:
        if stop_file.exists():
            print("[Ralph Wiggum] Stop file detected. Exiting.")
            break

        if not needs_action.exists():
            time.sleep(poll_interval)
            continue

        for task_file in sorted(needs_action.glob("*.md")):
            if task_file.name in processed:
                continue

            content = task_file.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(content)

            # Skip already-processed tasks
            if fm.get("status") in ("planned", "done", "plan_created"):
                processed.add(task_file.name)
                continue

            complexity = detect_complexity(fm, body)
            if not complexity["is_complex"]:
                processed.add(task_file.name)
                continue

            print(f"\n[Ralph Wiggum] Complex task found: {task_file.name}")
            print(f"  Complexity: {complexity['score']} signals")

            controller = LoopController(
                vault_path, logger, max_iterations=max_iterations,
            )
            result = controller.run_loop(task_file)
            processed.add(task_file.name)

            print(f"  Result: {result['status']} ({result['iterations']} iterations)")
            if result.get("plan_file"):
                print(f"  Plan: Plans/{result['plan_file']}")

        time.sleep(poll_interval)


def get_loop_status(vault_path: Path) -> dict:
    """Get current Ralph Wiggum loop status.

    Reports on active plans, pending tasks, and Done counts.
    """
    plans_dir = vault_path / "Plans"
    needs_action = vault_path / "Needs_Action"
    done_dir = vault_path / "Done"

    active_plans = []
    if plans_dir.exists():
        for p in plans_dir.glob("PLAN_*.md"):
            try:
                fm, _, steps = read_plan(p)
                completed = sum(1 for s in steps if s["is_complete"])
                total = len(steps)
                active_plans.append({
                    "file": p.name,
                    "status": fm.get("status", "unknown"),
                    "progress": f"{completed}/{total}",
                    "objective": fm.get("objective", ""),
                })
            except Exception:
                active_plans.append({"file": p.name, "status": "error"})

    pending_count = 0
    complex_count = 0
    if needs_action.exists():
        for f in needs_action.glob("*.md"):
            content = f.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(content)
            if fm.get("status") not in ("planned", "done", "plan_created"):
                pending_count += 1
                if detect_complexity(fm, body)["is_complex"]:
                    complex_count += 1

    done_count = len(list(done_dir.glob("*.md"))) if done_dir.exists() else 0
    stop_active = (plans_dir / ".stop").exists() if plans_dir.exists() else False

    return {
        "active_plans": active_plans,
        "pending_tasks": pending_count,
        "complex_tasks": complex_count,
        "done_count": done_count,
        "stop_active": stop_active,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Ralph Wiggum Loop — Autonomous Task Iteration")
    parser.add_argument("--vault-path", default=None)
    parser.add_argument("--task", default=None, help="Task description text to process")
    parser.add_argument("--file", default=None, help="Task file to process")
    parser.add_argument("--watch", action="store_true", help="Watch for new complex tasks")
    parser.add_argument("--status", action="store_true", help="Show loop status")
    parser.add_argument("--stop", action="store_true", help="Create stop signal")
    parser.add_argument("--clear-stop", action="store_true", help="Remove stop signal")
    parser.add_argument("--max-iterations", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=300.0, help="Timeout in seconds")
    parser.add_argument("--poll-interval", type=float, default=10.0, help="Watch poll interval")
    args = parser.parse_args()

    vault = Path(args.vault_path or os.getenv("VAULT_PATH",
                 str(Path(__file__).parent.parent)))
    logger = AuditLogger(vault)

    if args.stop:
        stop_file = vault / "Plans" / ".stop"
        stop_file.parent.mkdir(parents=True, exist_ok=True)
        stop_file.write_text(
            datetime.now(timezone.utc).isoformat(), encoding="utf-8",
        )
        print(f"[Ralph Wiggum] Stop signal created: {stop_file}")
        return

    if args.clear_stop:
        stop_file = vault / "Plans" / ".stop"
        if stop_file.exists():
            stop_file.unlink()
            print("[Ralph Wiggum] Stop signal removed.")
        else:
            print("[Ralph Wiggum] No stop signal found.")
        return

    if args.status:
        status = get_loop_status(vault)
        print("[Ralph Wiggum] Loop Status")
        print(f"  Stop signal: {'ACTIVE' if status['stop_active'] else 'off'}")
        print(f"  Pending tasks: {status['pending_tasks']} ({status['complex_tasks']} complex)")
        print(f"  Done count: {status['done_count']}")
        if status["active_plans"]:
            print(f"  Active plans: {len(status['active_plans'])}")
            for p in status["active_plans"]:
                print(f"    [{p['status'].upper()}] {p['file']} — {p.get('progress', '?')}")
        else:
            print("  Active plans: none")
        return

    if args.watch:
        try:
            watch_for_tasks(vault, args.poll_interval, args.max_iterations, logger)
        except KeyboardInterrupt:
            print("\n[Ralph Wiggum] Interrupted by user.")
        return

    if args.task:
        controller = LoopController(
            vault, logger, args.max_iterations, args.timeout,
        )
        result = controller.run_task_from_text(args.task)
        print(f"Status: {result['status']}")
        print(f"Iterations: {result['iterations']}")
        print(f"Stop reason: {result['stop_reason']}")
        if result.get("plan_file"):
            print(f"Plan: Plans/{result['plan_file']}")
        if result.get("metrics"):
            m = result["metrics"]
            print(f"Steps: {m['steps_completed']} done, {m['steps_failed']} failed")
            print(f"Domains: {', '.join(m['domains_touched']) or 'none'}")
        return

    if args.file:
        file_path = Path(args.file)
        if not file_path.is_absolute():
            file_path = vault / file_path
        if not file_path.exists():
            print(f"File not found: {file_path}")
            sys.exit(1)

        controller = LoopController(
            vault, logger, args.max_iterations, args.timeout,
        )
        result = controller.run_loop(file_path)
        print(f"Status: {result['status']}")
        print(f"Iterations: {result['iterations']}")
        print(f"Stop reason: {result['stop_reason']}")
        if result.get("plan_file"):
            print(f"Plan: Plans/{result['plan_file']}")
        if result.get("metrics"):
            m = result["metrics"]
            print(f"Steps: {m['steps_completed']} done, {m['steps_failed']} failed")
            print(f"Domains: {', '.join(m['domains_touched']) or 'none'}")
        return

    # Default: show status
    status = get_loop_status(vault)
    print("[Ralph Wiggum] No action specified. Use --task, --file, --watch, or --status")
    print(f"  Pending: {status['pending_tasks']} tasks ({status['complex_tasks']} complex)")
    if status["active_plans"]:
        print(f"  Active plans: {len(status['active_plans'])}")


if __name__ == "__main__":
    main()
