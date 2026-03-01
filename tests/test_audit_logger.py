"""Tests for the audit logger."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from audit_logger import AuditLogger


@pytest.fixture
def logger(tmp_path):
    return AuditLogger(tmp_path)


class TestAuditLogger:
    def test_log_creates_jsonl_file(self, logger, tmp_path):
        logger.log("test_action", "test_ref", "success")
        logs = list((tmp_path / "Logs").glob("*.audit.jsonl"))
        assert len(logs) == 1

    def test_log_entry_is_valid_json(self, logger, tmp_path):
        logger.log("test_action", "test_ref", "success", details={"key": "val"})
        log_file = list((tmp_path / "Logs").glob("*.audit.jsonl"))[0]
        line = log_file.read_text().strip()
        entry = json.loads(line)
        assert entry["action"] == "test_action"
        assert entry["input_ref"] == "test_ref"
        assert entry["outcome"] == "success"
        assert entry["details"] == {"key": "val"}

    def test_log_is_append_only(self, logger):
        logger.log("action_1", "ref_1", "success")
        logger.log("action_2", "ref_2", "error", error="Something broke")
        entries = logger.read_log()
        assert len(entries) == 2
        assert entries[0]["action"] == "action_1"
        assert entries[1]["action"] == "action_2"
        assert entries[1]["error"] == "Something broke"

    def test_timed_context_manager_success(self, logger):
        with logger.timed("timed_action", "ref") as ctx:
            ctx["details"] = {"note": "worked"}
        entries = logger.read_log()
        assert len(entries) == 1
        assert entries[0]["outcome"] == "success"
        assert entries[0]["duration_ms"] >= 0

    def test_timed_context_manager_error(self, logger):
        with pytest.raises(ValueError):
            with logger.timed("timed_fail", "ref"):
                raise ValueError("boom")
        entries = logger.read_log()
        assert len(entries) == 1
        assert entries[0]["outcome"] == "error"
        assert entries[0]["error"] == "boom"

    def test_read_log_with_filter(self, logger):
        logger.log("action_a", "ref", "success")
        logger.log("action_b", "ref", "success")
        logger.log("action_a", "ref", "success")
        filtered = logger.read_log(action_filter="action_a")
        assert len(filtered) == 2

    def test_read_log_empty_date(self, logger):
        entries = logger.read_log(date="2000-01-01")
        assert entries == []
