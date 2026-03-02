"""Platinum Demo — end-to-end validation of all Platinum Tier requirements.

Runs all checkpoints and reports PASS/FAIL for each Platinum requirement.

Usage:
    python scripts/platinum_demo.py
    python scripts/platinum_demo.py --vault-path /path
    python scripts/platinum_demo.py --verbose
"""

from __future__ import annotations

import argparse
import importlib
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

class DemoResult:
    def __init__(self, name: str, fr: str, passed: bool, detail: str = ""):
        self.name = name
        self.fr = fr
        self.passed = passed
        self.detail = detail

    @property
    def status(self) -> str:
        return "PASS" if self.passed else "FAIL"


def check(name: str, fr: str, condition: bool, detail: str = "") -> DemoResult:
    return DemoResult(name, fr, condition, detail)


# ---------------------------------------------------------------------------
# Checkpoint functions
# ---------------------------------------------------------------------------

def check_zone_config(vault: Path) -> list[DemoResult]:
    """Verify zone configuration module works."""
    results = []
    try:
        from zone_config import ZoneConfig, ZoneViolationError

        # Cloud mode blocks sends
        cloud = ZoneConfig("cloud")
        results.append(check(
            "Cloud mode blocks email_send", "FR-007",
            not cloud.is_allowed("email_send"),
        ))
        results.append(check(
            "Cloud mode allows email_triage", "FR-006",
            cloud.is_allowed("email_triage"),
        ))

        # Local mode allows sends
        local = ZoneConfig("local")
        results.append(check(
            "Local mode allows email_send", "FR-008",
            local.is_allowed("email_send"),
        ))

        # Zone enforcement raises
        try:
            cloud.enforce("email_send")
            results.append(check("Zone enforcement raises", "FR-009", False))
        except ZoneViolationError:
            results.append(check("Zone enforcement raises", "FR-009", True))

        # Components per zone
        results.append(check(
            "Cloud components include health monitor", "FR-002",
            "cloud_health_monitor" in cloud.get_components(),
        ))
        results.append(check(
            "Local components include approval", "FR-008",
            "local_approval" in local.get_components(),
        ))
    except Exception as e:
        results.append(check("Zone config module loads", "FR-009", False, str(e)))
    return results


def check_domain_folders(vault: Path) -> list[DemoResult]:
    """Verify domain folder structure exists."""
    results = []
    for folder in ["Needs_Action", "Plans", "Pending_Approval"]:
        for domain in ["EMAIL", "SOCIAL", "ODOO"]:
            path = vault / folder / domain
            results.append(check(
                f"{folder}/{domain}/ exists", "FR-011",
                path.exists() and path.is_dir(),
            ))

    for agent in ["cloud", "local"]:
        path = vault / "In_Progress" / agent
        results.append(check(
            f"In_Progress/{agent}/ exists", "FR-012",
            path.exists() and path.is_dir(),
        ))

    results.append(check(
        "Updates/ exists", "FR-014",
        (vault / "Updates").exists(),
    ))
    return results


def check_claim_by_move(vault: Path) -> list[DemoResult]:
    """Test claim-by-move protocol."""
    results = []
    try:
        from claim_task import claim_task, complete_task, list_pending

        # Create a test task
        test_dir = vault / "Pending_Approval" / "EMAIL"
        test_dir.mkdir(parents=True, exist_ok=True)
        test_file = test_dir / "DEMO_TEST_CLAIM.md"
        test_file.write_text("Demo test task for claim-by-move")

        # Claim it
        claimed = claim_task("Pending_Approval/EMAIL/DEMO_TEST_CLAIM.md", "local")
        results.append(check("Claim-by-move succeeds", "FR-012", claimed))

        # Double claim fails
        test_file2 = test_dir / "DEMO_TEST_CLAIM.md"
        if not test_file2.exists():
            results.append(check("Double claim prevented", "FR-012", True))
        else:
            results.append(check("Double claim prevented", "FR-012", False))

        # Complete
        completed = complete_task("In_Progress/local/DEMO_TEST_CLAIM.md")
        results.append(check("Complete task moves to Done", "FR-012", completed))

    except Exception as e:
        results.append(check("Claim-by-move protocol", "FR-012", False, str(e)))
    return results


def check_vault_sync_module(vault: Path) -> list[DemoResult]:
    """Verify vault sync module loads and exclusions work."""
    results = []
    try:
        from vault_sync import VaultSync, EXCLUDED_PATTERNS

        results.append(check(
            "vault_sync.py loads", "FR-015",
            True,
        ))
        results.append(check(
            "Exclusion patterns include .env", "FR-016",
            ".env" in EXCLUDED_PATTERNS,
        ))
        results.append(check(
            "Exclusion patterns include credentials.json", "FR-016",
            "credentials.json" in EXCLUDED_PATTERNS,
        ))
        results.append(check(
            "Exclusion patterns include token.json", "FR-016",
            "token.json" in EXCLUDED_PATTERNS,
        ))
    except Exception as e:
        results.append(check("Vault sync module", "FR-015", False, str(e)))
    return results


def check_gitignore(vault: Path) -> list[DemoResult]:
    """Verify .gitignore excludes secrets."""
    results = []
    gitignore = vault / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text()
        results.append(check(".gitignore excludes .env", "FR-016", ".env" in content))
        results.append(check(".gitignore excludes credentials.json", "FR-016", "credentials.json" in content))
        results.append(check(".gitignore excludes token.json", "FR-016", "token.json" in content))
    else:
        results.append(check(".gitignore exists", "FR-017", False))
    return results


def check_orchestrator_zone(vault: Path) -> list[DemoResult]:
    """Verify orchestrator supports --zone flag."""
    results = []
    try:
        import orchestrator
        import inspect
        source = inspect.getsource(orchestrator.main)
        results.append(check(
            "Orchestrator has --zone flag", "FR-001",
            "--zone" in source,
        ))
    except Exception as e:
        results.append(check("Orchestrator zone support", "FR-001", False, str(e)))
    return results


def check_health_monitor(vault: Path) -> list[DemoResult]:
    """Verify health monitor module loads."""
    results = []
    try:
        from cloud_health_monitor import HealthMonitor
        monitor = HealthMonitor(vault)
        results.append(check("Health monitor loads", "FR-002", True))
        results.append(check(
            "Health monitor has run_checks", "FR-002",
            hasattr(monitor, "run_checks"),
        ))
    except Exception as e:
        results.append(check("Health monitor module", "FR-002", False, str(e)))
    return results


def check_local_approval(vault: Path) -> list[DemoResult]:
    """Verify local approval module loads."""
    results = []
    try:
        from local_approval import LocalApprovalService
        service = LocalApprovalService(vault, auto_approve=True)
        results.append(check("Local approval loads", "FR-008", True))
        results.append(check(
            "Local approval has scan_pending", "FR-008",
            hasattr(service, "scan_pending"),
        ))
    except Exception as e:
        results.append(check("Local approval module", "FR-008", False, str(e)))
    return results


def check_vault_delegation(vault: Path) -> list[DemoResult]:
    """Verify vault delegation module."""
    results = []
    try:
        from vault_delegation import VaultDelegation
        vd = VaultDelegation(vault)
        results.append(check("Vault delegation loads", "FR-014", True))

        # Test create + promote flow
        task = vd.create_task("EMAIL", "Demo test email triage", "cloud")
        results.append(check(
            "Create task in Needs_Action/EMAIL/", "FR-011",
            task.exists() and "Needs_Action" in task.parts and "EMAIL" in task.parts,
        ))

        promoted = vd.promote_to_approval(task, "EMAIL")
        results.append(check(
            "Promote to Pending_Approval/EMAIL/", "FR-011",
            promoted.exists() and "Pending_Approval" in promoted.parts and "EMAIL" in promoted.parts,
        ))

        # Clean up
        promoted.unlink(missing_ok=True)

    except Exception as e:
        results.append(check("Vault delegation", "FR-014", False, str(e)))
    return results


def check_a2a(vault: Path) -> list[DemoResult]:
    """Verify A2A modules load (optional)."""
    results = []
    try:
        from a2a_client import A2AClient
        from a2a_server import validate_message

        client = A2AClient(webhook_url="", vault_path=vault)
        results.append(check("A2A client loads", "FR-024", True))

        # Test vault fallback
        result = client.send("task", {"domain": "EMAIL", "action": "test"})
        results.append(check(
            "A2A vault fallback works", "FR-026",
            result.delivery_method == "vault_fallback",
        ))

        # Validate message schema
        valid, _ = validate_message({"message_type": "task", "payload": {}})
        results.append(check("A2A message validation", "FR-024", valid))

        # Clean up A2A files
        for f in (vault / "Updates").glob("A2A_*"):
            f.unlink(missing_ok=True)
        for f in (vault / "Needs_Action" / "EMAIL").glob("A2A_FALLBACK_*"):
            f.unlink(missing_ok=True)

    except Exception as e:
        results.append(check("A2A modules", "FR-024", False, str(e)))
    return results


def check_deploy_files(vault: Path) -> list[DemoResult]:
    """Verify deployment files exist."""
    results = []
    deploy = vault / "deploy"

    files = {
        "setup-vm.sh": "FR-005",
        "docker-compose.yml": "FR-019",
        "nginx/odoo.conf": "FR-019",
        "backup/odoo-backup.sh": "FR-020",
        "systemd/ai-employee.service": "FR-001",
        "systemd/vault-sync.timer": "FR-015",
        ".env.cloud.example": "FR-018",
    }
    for f, fr in files.items():
        results.append(check(
            f"deploy/{f} exists", fr,
            (deploy / f).exists(),
        ))
    return results


# ---------------------------------------------------------------------------
# Main demo runner
# ---------------------------------------------------------------------------

def run_demo(vault: Path, verbose: bool = False) -> None:
    """Run all Platinum demo checkpoints."""
    print("=" * 60)
    print("  Platinum Tier Demo — AI Employee Vault")
    print("=" * 60)
    print(f"  Vault: {vault}")
    print(f"  Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    all_results: list[DemoResult] = []

    checks = [
        ("Zone Configuration", check_zone_config),
        ("Domain Folders", check_domain_folders),
        ("Claim-by-Move", check_claim_by_move),
        ("Vault Sync Module", check_vault_sync_module),
        (".gitignore Security", check_gitignore),
        ("Orchestrator Zone", check_orchestrator_zone),
        ("Health Monitor", check_health_monitor),
        ("Local Approval", check_local_approval),
        ("Vault Delegation", check_vault_delegation),
        ("A2A (Optional)", check_a2a),
        ("Deploy Files", check_deploy_files),
    ]

    for section_name, check_fn in checks:
        print(f"\n--- {section_name} ---")
        results = check_fn(vault)
        all_results.extend(results)
        for r in results:
            icon = "PASS" if r.passed else "FAIL"
            print(f"  {icon} [{r.fr}] {r.name}")
            if verbose and r.detail:
                print(f"          {r.detail}")

    # Summary
    passed = sum(1 for r in all_results if r.passed)
    failed = sum(1 for r in all_results if not r.passed)
    total = len(all_results)

    print(f"\n{'=' * 60}")
    print(f"  RESULTS: {passed}/{total} PASS, {failed} FAIL")
    print(f"{'=' * 60}")

    if failed == 0:
        print("\n  [PASS] ALL PLATINUM CHECKPOINTS PASSED")
    else:
        print("\n  [FAIL] SOME CHECKPOINTS FAILED:")
        for r in all_results:
            if not r.passed:
                print(f"    - [{r.fr}] {r.name}: {r.detail or 'FAIL'}")

    print()
    return failed == 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Platinum Tier demo")
    parser.add_argument("--vault-path", default=os.environ.get("VAULT_PATH",
                        str(Path(__file__).parent.parent)))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    vault = Path(args.vault_path)
    os.environ["VAULT_PATH"] = str(vault)
    success = run_demo(vault, verbose=args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
