"""Shared pytest fixtures for Bronze + Silver Tier tests."""

import sys
from pathlib import Path

import pytest

# Allow imports from scripts/
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from audit_logger import AuditLogger


@pytest.fixture
def vault(tmp_path):
    """Create a temporary vault with standard folder structure."""
    (tmp_path / "Needs_Action").mkdir()
    (tmp_path / "Done").mkdir()
    (tmp_path / "Logs").mkdir()
    (tmp_path / "Pending_Approval").mkdir()
    (tmp_path / "Accounting").mkdir()
    return tmp_path


@pytest.fixture
def logger(vault):
    """Create an AuditLogger pointing at the temporary vault."""
    return AuditLogger(vault)


SAMPLE_TASK = """\
---
type: task
priority: high
category: review
status: new
---

# Review Q3 Report

Please review the Q3 financial report and prepare a summary.
"""

SAMPLE_TASK_NO_FRONTMATTER = """\
# Simple Task

Just a plain markdown file with no frontmatter.
"""

SENSITIVE_TASK = """\
---
type: task
priority: high
category: finance
status: new
---

# Process Payment

Please process the payment of $5000 to vendor.
"""
