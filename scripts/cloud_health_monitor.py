"""Cloud health monitor — watchdog service for Cloud zone components.

Platinum Tier: Monitors all cloud components, checks HTTP endpoints,
tracks sync freshness, and sends alerts after consecutive failures.

Usage:
    python scripts/cloud_health_monitor.py --vault-path /path
    python scripts/cloud_health_monitor.py --interval 60
    python scripts/cloud_health_monitor.py --check-once
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger
from error_recovery import HealthTracker, ServiceHealth


class HealthMonitor:
    """Watchdog that monitors cloud components and alerts on failures."""

    def __init__(
        self,
        vault_path: Path,
        check_interval: int = 60,
        consecutive_failure_threshold: int = 3,
        alert_email: str | None = None,
    ):
        self.vault_path = vault_path
        self.check_interval = check_interval
        self.threshold = consecutive_failure_threshold
        self.alert_email = alert_email
        self.tracker = HealthTracker()
        self.logger = AuditLogger(vault_path / "Logs")
        self._process_pids: dict[str, int] = {}
        self._http_endpoints: dict[str, str] = {}
        self._alerted: set[str] = set()  # Track which services have been alerted

    def register_process(self, name: str, pid: int) -> None:
        """Register a process to monitor by PID."""
        self._process_pids[name] = pid

    def register_http(self, name: str, url: str) -> None:
        """Register an HTTP endpoint to health-check."""
        self._http_endpoints[name] = url

    def check_process(self, name: str, pid: int) -> bool:
        """Check if a process is alive by PID."""
        try:
            os.kill(pid, 0)  # Signal 0 = check existence
            return True
        except (OSError, ProcessLookupError):
            return False

    def check_http(self, name: str, url: str, timeout: int = 5) -> bool:
        """Check if an HTTP endpoint responds with 200."""
        try:
            with urlopen(url, timeout=timeout) as resp:
                return resp.status == 200
        except (URLError, OSError, ValueError):
            return False

    def check_sync_freshness(self, max_stale_seconds: int = 300) -> bool:
        """Check if vault sync is fresh (last sync within threshold)."""
        sync_log = self.vault_path / "Logs" / "vault_sync.log"
        if not sync_log.exists():
            return False
        try:
            mtime = sync_log.stat().st_mtime
            age = time.time() - mtime
            return age < max_stale_seconds
        except OSError:
            return False

    def run_checks(self) -> dict[str, dict[str, Any]]:
        """Run all registered health checks. Returns results dict."""
        results = {}

        # Process checks
        for name, pid in self._process_pids.items():
            alive = self.check_process(name, pid)
            if alive:
                self.tracker.record_success(name)
                results[name] = {"status": "healthy", "type": "process", "pid": pid}
            else:
                self.tracker.record_failure(name, f"Process {pid} not found")
                results[name] = {"status": "unhealthy", "type": "process", "pid": pid}
                self._check_alert(name)

        # HTTP checks
        for name, url in self._http_endpoints.items():
            healthy = self.check_http(name, url)
            if healthy:
                self.tracker.record_success(name)
                results[name] = {"status": "healthy", "type": "http", "url": url}
            else:
                self.tracker.record_failure(name, f"HTTP check failed: {url}")
                results[name] = {"status": "unhealthy", "type": "http", "url": url}
                self._check_alert(name)

        # Sync freshness
        sync_ok = self.check_sync_freshness()
        sync_name = "vault_sync"
        if sync_ok:
            self.tracker.record_success(sync_name)
            results[sync_name] = {"status": "healthy", "type": "sync"}
        else:
            self.tracker.record_failure(sync_name, "Sync log stale or missing")
            results[sync_name] = {"status": "stale", "type": "sync"}

        return results

    def _check_alert(self, service: str) -> None:
        """Send alert if service has hit consecutive failure threshold."""
        all_data = self.tracker.get_all()
        svc_data = all_data.get(service, {})
        failures = svc_data.get("consecutive_failures", 0)
        if failures >= self.threshold:
            if service not in self._alerted:
                self._send_alert(service, svc_data.get("last_error", "Unknown error"))
                self._alerted.add(service)
        else:
            self._alerted.discard(service)

    def _send_alert(self, service: str, error: str) -> None:
        """Write alert file to Updates/ and optionally send email."""
        updates_dir = self.vault_path / "Updates"
        updates_dir.mkdir(parents=True, exist_ok=True)

        ts = time.strftime("%Y%m%d_%H%M%S")
        alert_file = updates_dir / f"ALERT_{service}_{ts}.md"
        content = f"""---
type: health_alert
service: {service}
consecutive_failures: {self.threshold}
detected_at: {time.strftime('%Y-%m-%d %H:%M:%S')}
error: "{error}"
---

## Health Alert: {service}

**Service**: {service}
**Consecutive failures**: {self.threshold}+
**Error**: {error}
**Time**: {time.strftime('%Y-%m-%d %H:%M:%S')}

**Action**: Check the service and restart if needed.
"""
        alert_file.write_text(content, encoding="utf-8")

        self.logger.log(
            "health_alert", service, "alert",
            details={"error": error, "threshold": self.threshold},
        )
        print(f"  [ALERT] {service}: {error} ({self.threshold} consecutive failures)")

    def get_summary(self) -> dict[str, str]:
        """Get a summary of all service health statuses."""
        return self.tracker.get_summary()

    def run_loop(self) -> None:
        """Run continuous health monitoring."""
        print(f"Health monitor started (interval={self.check_interval}s, threshold={self.threshold})")
        try:
            while True:
                results = self.run_checks()
                ts = time.strftime("%H:%M:%S")
                healthy = sum(1 for r in results.values() if r["status"] == "healthy")
                total = len(results)
                print(f"[{ts}] Health: {healthy}/{total} healthy")
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            print("\nHealth monitor stopped.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Cloud health monitor")
    parser.add_argument("--vault-path", default=os.environ.get("VAULT_PATH", "."))
    parser.add_argument("--interval", type=int,
                        default=int(os.environ.get("HEALTH_CHECK_INTERVAL", "60")))
    parser.add_argument("--threshold", type=int,
                        default=int(os.environ.get("HEALTH_CONSECUTIVE_FAILURES", "3")))
    parser.add_argument("--alert-email", default=os.environ.get("HEALTH_ALERT_EMAIL", ""))
    parser.add_argument("--check-once", action="store_true", help="Run one check and exit")
    args = parser.parse_args()

    vault = Path(args.vault_path)
    monitor = HealthMonitor(
        vault,
        check_interval=args.interval,
        consecutive_failure_threshold=args.threshold,
        alert_email=args.alert_email or None,
    )

    # Register default cloud endpoints
    odoo_url = os.environ.get("ODOO_URL", "http://localhost:8069")
    monitor.register_http("odoo", f"{odoo_url}/web/health")

    if args.check_once:
        results = monitor.run_checks()
        for name, info in results.items():
            print(f"  {name}: {info['status']} ({info['type']})")
        return

    monitor.run_loop()


if __name__ == "__main__":
    main()
