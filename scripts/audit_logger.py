"""Structured audit logger — JSON Lines format, append-only.

Writes to <vault>/Logs/YYYY-MM-DD.audit.jsonl.
Each line is a self-contained JSON object.
"""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator


class AuditLogger:
    """Append-only JSON Lines audit logger."""

    def __init__(self, vault_path: str | Path) -> None:
        self._logs_dir = Path(vault_path) / "Logs"
        self._logs_dir.mkdir(parents=True, exist_ok=True)

    def _log_file(self) -> Path:
        name = datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".audit.jsonl"
        return self._logs_dir / name

    def log(
        self,
        action: str,
        input_ref: str,
        outcome: str = "success",
        duration_ms: int = 0,
        details: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """Write one audit log entry."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "input_ref": input_ref,
            "outcome": outcome,
            "duration_ms": duration_ms,
            "details": details,
            "error": error,
        }
        with open(self._log_file(), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    @contextmanager
    def timed(
        self, action: str, input_ref: str
    ) -> Generator[dict[str, Any], None, None]:
        """Context manager that times an action and logs on exit."""
        ctx: dict[str, Any] = {"details": {}}
        start = time.monotonic()
        try:
            yield ctx
            ms = int((time.monotonic() - start) * 1000)
            self.log(action, input_ref, "success", ms, ctx.get("details"))
        except Exception as exc:
            ms = int((time.monotonic() - start) * 1000)
            self.log(action, input_ref, "error", ms, ctx.get("details"), str(exc))
            raise

    def read_log(
        self, date: str | None = None, action_filter: str | None = None
    ) -> list[dict]:
        """Read log entries for a date, optionally filtered by action."""
        if date:
            path = self._logs_dir / f"{date}.audit.jsonl"
        else:
            path = self._log_file()
        if not path.exists():
            return []
        entries = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            if action_filter and entry.get("action") != action_filter:
                continue
            entries.append(entry)
        return entries
