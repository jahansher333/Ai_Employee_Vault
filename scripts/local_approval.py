"""Local approval — picks up Cloud-created drafts for CEO approval and execution.

Platinum Tier: Scans Pending_Approval/ folders, presents drafts for review,
executes approved actions, moves completed items to Done/.

Usage:
    python scripts/local_approval.py --vault-path /path   # Interactive mode
    python scripts/local_approval.py --scan-interval 30    # Auto-scan
    python scripts/local_approval.py --auto-approve         # Testing mode
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger
from claim_task import claim_task, complete_task, reject_task, list_pending
from vault_delegation import VaultDelegation


DOMAINS = ["EMAIL", "SOCIAL", "ODOO"]


class LocalApprovalService:
    """Scans for cloud-created drafts and presents for CEO approval."""

    def __init__(self, vault_path: Path, auto_approve: bool = False):
        self.vault_path = vault_path
        self.auto_approve = auto_approve
        self.logger = AuditLogger(vault_path / "Logs")
        self.delegation = VaultDelegation(vault_path)

    def scan_pending(self) -> list[tuple[str, Path]]:
        """Scan all domain folders for pending approvals.

        Returns list of (domain, file_path) tuples.
        """
        results = []
        for domain in DOMAINS:
            for task in list_pending(domain):
                results.append((domain, task))
        return results

    def present_for_approval(self, domain: str, task_path: Path) -> str:
        """Present a task for CEO review.

        Returns: "approve", "reject", or "skip"
        """
        print(f"\n{'=' * 50}")
        print(f"  Domain: {domain}")
        print(f"  File: {task_path.name}")
        print(f"{'=' * 50}")

        try:
            content = task_path.read_text(encoding="utf-8")
            # Show first 20 lines
            lines = content.splitlines()[:20]
            for line in lines:
                print(f"  {line}")
            if len(content.splitlines()) > 20:
                print(f"  ... ({len(content.splitlines()) - 20} more lines)")
        except OSError as e:
            print(f"  Error reading file: {e}")
            return "skip"

        if self.auto_approve:
            print("  [AUTO-APPROVE] Approved")
            return "approve"

        print()
        while True:
            choice = input("  Action [a]pprove / [r]eject / [s]kip: ").strip().lower()
            if choice in ("a", "approve"):
                return "approve"
            if choice in ("r", "reject"):
                return "reject"
            if choice in ("s", "skip", ""):
                return "skip"
            print("  Invalid choice. Enter a, r, or s.")

    def execute_approved(self, domain: str, task_path: Path) -> bool:
        """Execute an approved task based on domain.

        Returns True on successful execution.
        """
        self.logger.log(
            "local_approval_execute", domain, "success",
            details={"file": task_path.name},
        )
        print(f"  [EXECUTE] {domain}: {task_path.name}")

        # Domain-specific execution would go here
        # For now, log the approval and move to done
        if domain == "EMAIL":
            print(f"  → Would send email draft from {task_path.name}")
        elif domain == "SOCIAL":
            print(f"  → Would publish social post from {task_path.name}")
        elif domain == "ODOO":
            print(f"  → Would execute Odoo action from {task_path.name}")

        return True

    def process_pending(self) -> dict[str, int]:
        """Process all pending tasks. Returns counts by action."""
        counts = {"approved": 0, "rejected": 0, "skipped": 0, "errors": 0}
        pending = self.scan_pending()

        if not pending:
            return counts

        print(f"\n  Found {len(pending)} pending task(s)")

        for domain, task_path in pending:
            action = self.present_for_approval(domain, task_path)

            if action == "approve":
                # Claim the task
                rel_path = task_path.relative_to(self.vault_path)
                if claim_task(str(rel_path), "local"):
                    claimed_path = self.vault_path / "In_Progress" / "local" / task_path.name
                    try:
                        self.execute_approved(domain, claimed_path)
                        complete_task(str(claimed_path.relative_to(self.vault_path)))
                        counts["approved"] += 1
                        self.logger.log(
                            "local_approval", task_path.name, "approved",
                            details={"domain": domain},
                        )
                    except Exception as e:
                        counts["errors"] += 1
                        print(f"  [ERROR] Execution failed: {e}")
                else:
                    print(f"  [CONFLICT] Task already claimed by another agent")
                    counts["errors"] += 1

            elif action == "reject":
                rel_path = task_path.relative_to(self.vault_path)
                if claim_task(str(rel_path), "local"):
                    claimed_path = self.vault_path / "In_Progress" / "local" / task_path.name
                    reject_task(str(claimed_path))
                    counts["rejected"] += 1
                    self.logger.log(
                        "local_approval", task_path.name, "rejected",
                        details={"domain": domain},
                    )
                else:
                    counts["errors"] += 1

            else:
                counts["skipped"] += 1

        return counts

    def merge_cloud_updates(self) -> int:
        """Merge status updates from Cloud."""
        count = self.delegation.merge_updates()
        if count > 0:
            print(f"  Merged {count} cloud update(s)")
        return count

    def run_loop(self, scan_interval: int = 30) -> None:
        """Continuous scan loop."""
        print(f"Local approval service started (scan every {scan_interval}s)")
        try:
            while True:
                self.merge_cloud_updates()
                counts = self.process_pending()
                if any(v > 0 for v in counts.values()):
                    print(f"  Results: {counts}")
                time.sleep(scan_interval)
        except KeyboardInterrupt:
            print("\nLocal approval service stopped.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Local approval workflow")
    parser.add_argument("--vault-path", default=os.environ.get("VAULT_PATH", "."))
    parser.add_argument("--scan-interval", type=int, default=30)
    parser.add_argument("--auto-approve", action="store_true", help="Auto-approve all (testing)")
    parser.add_argument("--once", action="store_true", help="Process once and exit")
    args = parser.parse_args()

    vault = Path(args.vault_path)
    service = LocalApprovalService(vault, auto_approve=args.auto_approve)

    if args.once:
        service.merge_cloud_updates()
        counts = service.process_pending()
        print(f"\nResults: {counts}")
        return

    service.run_loop(args.scan_interval)


if __name__ == "__main__":
    main()
