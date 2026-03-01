"""Orchestrator — single entry point to launch all AI Employee components.

Gold Tier: Launches all watchers, MCP servers, and Gold Tier components
with health status tracking, optional auto-restart, and graceful degradation.

Usage:
    python scripts/orchestrator.py                    # Launch all components
    python scripts/orchestrator.py --no-gmail         # Skip Gmail watcher
    python scripts/orchestrator.py --no-whatsapp      # Skip WhatsApp watcher
    python scripts/orchestrator.py --no-scheduler     # Skip briefing scheduler
    python scripts/orchestrator.py --no-odoo          # Skip Odoo sync
    python scripts/orchestrator.py --no-social        # Skip social poster
    python scripts/orchestrator.py --auto-restart     # Auto-restart crashed components
    python scripts/orchestrator.py --dry-run          # Show what would launch
    python scripts/orchestrator.py --vault-path /path # Custom vault path
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger


# ---------------------------------------------------------------------------
# Component definitions
# ---------------------------------------------------------------------------

def build_component_list(
    vault_path: Path,
    *,
    include_gmail: bool = True,
    include_whatsapp: bool = True,
    include_scheduler: bool = True,
    include_odoo: bool = True,
    include_social: bool = True,
) -> list[dict]:
    """Build the list of components to launch.

    Each component is a dict with:
        name: str           — human-readable name
        script: str         — script filename in scripts/
        args: list[str]     — extra CLI arguments
        required: bool      — if True, failure to start is fatal
        tier: str           — Bronze or Silver
    """
    scripts_dir = str(Path(__file__).parent)

    components = [
        {
            "name": "File Watcher",
            "script": "watcher.py",
            "args": ["--vault-path", str(vault_path)],
            "required": True,
            "tier": "Bronze",
        },
    ]

    if include_gmail:
        # Only include if credentials exist
        creds = vault_path / "credentials.json"
        token = vault_path / "token.json"
        if creds.exists() or token.exists():
            components.append({
                "name": "Gmail Watcher",
                "script": "gmail_watcher.py",
                "args": ["--vault-path", str(vault_path)],
                "required": False,
                "tier": "Silver",
            })

    if include_whatsapp:
        components.append({
            "name": "WhatsApp Watcher",
            "script": "whatsapp_watcher.py",
            "args": ["--vault-path", str(vault_path)],
            "required": False,
            "tier": "Silver",
        })

    if include_scheduler:
        components.append({
            "name": "Weekly Briefing Scheduler",
            "script": "weekly_briefing.py",
            "args": ["--vault-path", str(vault_path), "--schedule"],
            "required": False,
            "tier": "Silver",
        })

    # Gold Tier components
    if include_odoo:
        components.append({
            "name": "Odoo MCP Server",
            "script": "mcp_odoo_server.py",
            "args": [],
            "required": False,
            "tier": "Gold",
        })

    if include_social:
        components.append({
            "name": "Social MCP Server",
            "script": "mcp_social_server.py",
            "args": [],
            "required": False,
            "tier": "Gold",
        })

    return components


def validate_components(components: list[dict]) -> list[str]:
    """Check that all component scripts exist. Returns list of warnings."""
    scripts_dir = Path(__file__).parent
    warnings = []
    for comp in components:
        script_path = scripts_dir / comp["script"]
        if not script_path.exists():
            warnings.append(f"{comp['name']}: script not found at {script_path}")
    return warnings


# ---------------------------------------------------------------------------
# Process management
# ---------------------------------------------------------------------------

def launch_components(
    components: list[dict],
    logger: AuditLogger,
) -> list[dict]:
    """Launch each component as a subprocess.

    Returns the components list with 'process' key added for each launched one.
    """
    scripts_dir = Path(__file__).parent
    python = sys.executable
    launched = []

    for comp in components:
        script_path = scripts_dir / comp["script"]
        cmd = [python, str(script_path)] + comp["args"]

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            comp["process"] = proc
            comp["pid"] = proc.pid
            comp["status"] = "running"
            launched.append(comp)

            logger.log(
                "orchestrator_launch", comp["name"], "success",
                details={"script": comp["script"], "pid": proc.pid},
            )
            print(f"  [{comp['tier']}] {comp['name']} started (PID {proc.pid})")

        except Exception as exc:
            comp["process"] = None
            comp["pid"] = None
            comp["status"] = "failed"
            launched.append(comp)

            logger.log(
                "orchestrator_launch", comp["name"], "error",
                error=str(exc),
            )
            print(f"  [{comp['tier']}] {comp['name']} FAILED: {exc}")

            if comp["required"]:
                raise RuntimeError(
                    f"Required component {comp['name']} failed to start: {exc}"
                )

    return launched


def shutdown_components(components: list[dict], logger: AuditLogger) -> None:
    """Gracefully terminate all running subprocesses."""
    for comp in components:
        proc = comp.get("process")
        if proc is None or proc.poll() is not None:
            continue

        try:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)

            logger.log(
                "orchestrator_stop", comp["name"], "success",
                details={"pid": comp.get("pid")},
            )
            print(f"  Stopped {comp['name']} (PID {comp.get('pid')})")
        except Exception as exc:
            logger.log(
                "orchestrator_stop", comp["name"], "error",
                error=str(exc),
            )
            print(f"  Error stopping {comp['name']}: {exc}")


def check_component_health(components: list[dict]) -> list[dict]:
    """Check if any component has exited unexpectedly. Returns crashed list."""
    crashed = []
    for comp in components:
        proc = comp.get("process")
        if proc is None:
            continue
        rc = proc.poll()
        if rc is not None and comp.get("status") == "running":
            comp["status"] = "crashed"
            comp["exit_code"] = rc
            crashed.append(comp)
    return crashed


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def restart_component(comp: dict, logger: AuditLogger) -> bool:
    """Attempt to restart a crashed component. Returns True on success."""
    scripts_dir = Path(__file__).parent
    script_path = scripts_dir / comp["script"]
    cmd = [sys.executable, str(script_path)] + comp["args"]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        comp["process"] = proc
        comp["pid"] = proc.pid
        comp["status"] = "running"
        comp["restart_count"] = comp.get("restart_count", 0) + 1

        logger.log(
            "orchestrator_restart", comp["name"], "success",
            details={"pid": proc.pid, "restart_count": comp["restart_count"]},
        )
        print(f"  [RESTART] {comp['name']} restarted (PID {proc.pid}, "
              f"attempt {comp['restart_count']})")
        return True

    except Exception as exc:
        logger.log(
            "orchestrator_restart", comp["name"], "error",
            error=str(exc),
        )
        print(f"  [RESTART FAILED] {comp['name']}: {exc}")
        return False


MAX_RESTARTS = 3


def run_orchestrator(
    vault_path: Path,
    *,
    include_gmail: bool = True,
    include_whatsapp: bool = True,
    include_scheduler: bool = True,
    include_odoo: bool = True,
    include_social: bool = True,
    auto_restart: bool = False,
    dry_run: bool = False,
) -> None:
    """Launch and manage all AI Employee components."""
    logger = AuditLogger(vault_path)

    # Ensure vault directories exist
    for d in ["Needs_Action", "Plans", "Pending_Approval", "Approved",
              "Done", "Logs", "Briefings"]:
        (vault_path / d).mkdir(parents=True, exist_ok=True)

    components = build_component_list(
        vault_path,
        include_gmail=include_gmail,
        include_whatsapp=include_whatsapp,
        include_scheduler=include_scheduler,
        include_odoo=include_odoo,
        include_social=include_social,
    )

    # Validate
    warnings = validate_components(components)
    if warnings:
        for w in warnings:
            print(f"  [WARNING] {w}")

    print("=" * 60)
    print("  AI Employee Orchestrator — Gold Tier")
    print("=" * 60)
    print(f"\n  Vault: {vault_path}")
    print(f"  Components: {len(components)}")
    print()

    for comp in components:
        status = "SKIP" if comp["script"] in [w.split(":")[0] for w in warnings] else "READY"
        print(f"  [{comp['tier']}] {comp['name']} ({comp['script']}) — {status}")
    print()

    if dry_run:
        print("  DRY RUN — no processes launched.")
        return

    # Launch
    print("Launching components...\n")
    logger.log("orchestrator_started", "system", "success",
               details={"vault": str(vault_path), "components": len(components)})

    launched = launch_components(components, logger)
    running = [c for c in launched if c.get("status") == "running"]
    failed = [c for c in launched if c.get("status") == "failed"]

    print(f"\n  {len(running)} running, {len(failed)} failed")
    print("  Press Ctrl+C to stop all components.\n")

    # Monitor loop
    try:
        while True:
            crashed = check_component_health(launched)
            for c in crashed:
                print(f"  [CRASHED] {c['name']} exited with code {c.get('exit_code')}")
                logger.log("orchestrator_crash", c["name"], "error",
                           details={"exit_code": c.get("exit_code")})

                # Auto-restart if enabled and under limit
                if auto_restart and c.get("restart_count", 0) < MAX_RESTARTS:
                    restart_component(c, logger)

            # Check if all required components are still running
            required_alive = any(
                c.get("status") == "running"
                for c in launched if c["required"]
            )
            if not required_alive:
                print("\n  All required components have stopped. Shutting down.")
                break

            time.sleep(10)

    except KeyboardInterrupt:
        print("\n\nShutting down all components...")

    finally:
        shutdown_components(launched, logger)
        logger.log("orchestrator_stopped", "system", "success")
        print("\nOrchestrator stopped.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Employee Orchestrator — launch all components"
    )
    parser.add_argument("--vault-path", default=None,
                        help="Path to vault root")
    parser.add_argument("--no-gmail", action="store_true",
                        help="Skip Gmail watcher")
    parser.add_argument("--no-whatsapp", action="store_true",
                        help="Skip WhatsApp watcher")
    parser.add_argument("--no-scheduler", action="store_true",
                        help="Skip weekly briefing scheduler")
    parser.add_argument("--no-odoo", action="store_true",
                        help="Skip Odoo MCP server")
    parser.add_argument("--no-social", action="store_true",
                        help="Skip Social MCP server")
    parser.add_argument("--auto-restart", action="store_true",
                        help="Auto-restart crashed components")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would launch without starting")
    args = parser.parse_args()

    vault = Path(args.vault_path or os.getenv("VAULT_PATH",
                 str(Path(__file__).parent.parent)))

    run_orchestrator(
        vault,
        include_gmail=not args.no_gmail,
        include_whatsapp=not args.no_whatsapp,
        include_scheduler=not args.no_scheduler,
        include_odoo=not args.no_odoo,
        include_social=not args.no_social,
        auto_restart=args.auto_restart,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
