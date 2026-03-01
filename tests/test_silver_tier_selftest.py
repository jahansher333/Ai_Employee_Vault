"""Silver Tier Self-Test — verifies all Silver Tier requirements are met.

This is the final validation test that exercises the complete pipeline:
  task → complexity detection → Plan.md → watcher processing → approval routing
  → briefing generation → Dashboard update → orchestrator configuration

Run:  python -m pytest tests/test_silver_tier_selftest.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from audit_logger import AuditLogger
from reasoning_loop import detect_complexity, create_plan, execute_step, read_plan, complete_plan
from weekly_briefing import collect_task_stats, collect_bottlenecks, generate_briefing, _fmt_currency
from update_dashboard import update_dashboard, build_plans_table, build_briefings_table
from process_inbox import process_file, parse_frontmatter, is_sensitive
from orchestrator import build_component_list, validate_components
from data_analyzer import HAS_PANDAS


# ---------------------------------------------------------------------------
# REQ-1: Gmail Watcher — monitors unread/important emails
# ---------------------------------------------------------------------------

class TestReq1GmailWatcher:
    def test_gmail_watcher_script_exists(self):
        assert (Path(__file__).parent.parent / "scripts" / "gmail_watcher.py").exists()

    def test_gmail_watcher_creates_email_tasks(self, vault):
        from gmail_watcher import create_email_task
        email_data = {
            "id": "selftest_001",
            "from": "test@example.com",
            "subject": "Self-Test Email",
            "snippet": "This is a self-test email for Silver Tier validation.",
            "date": "2026-02-24",
            "is_important": True,
        }
        task_path = create_email_task(email_data, vault)
        assert task_path.exists()
        content = task_path.read_text(encoding="utf-8")
        assert "type: email" in content
        assert "priority: high" in content


# ---------------------------------------------------------------------------
# REQ-2: DataAnalyzerSkill — CSV analysis with pandas
# ---------------------------------------------------------------------------

class TestReq2DataAnalyzer:
    def test_data_analyzer_script_exists(self):
        assert (Path(__file__).parent.parent / "scripts" / "data_analyzer.py").exists()

    def test_data_analyzer_skill_exists(self):
        assert (Path(__file__).parent.parent / ".claude" / "skills" / "data-analyzer.md").exists()

    @pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")
    def test_csv_analysis_pipeline(self, vault):
        import pandas as pd
        from data_analyzer import read_financial_csv, clean_data, analyze, detect_anomalies

        # Create sample CSV
        accounting = vault / "Accounting"
        accounting.mkdir(exist_ok=True)
        csv_path = accounting / "selftest.csv"
        csv_path.write_text(
            "date,description,amount,category\n"
            "2026-01-01,Revenue A,5000,Revenue\n"
            "2026-01-02,Expense B,-200,Operations\n"
            "2026-02-01,Revenue C,3000,Revenue\n",
            encoding="utf-8",
        )

        df = read_financial_csv(csv_path)
        assert df is not None
        df = clean_data(df)
        result = analyze(df)
        assert result["total_revenue"] > 0
        assert result["total_expenses"] > 0  # abs value, always positive


# ---------------------------------------------------------------------------
# REQ-3: WhatsApp Watcher — monitors urgent messages
# ---------------------------------------------------------------------------

class TestReq3WhatsAppWatcher:
    def test_whatsapp_watcher_script_exists(self):
        assert (Path(__file__).parent.parent / "scripts" / "whatsapp_watcher.py").exists()

    def test_whatsapp_skill_exists(self):
        assert (Path(__file__).parent.parent / ".claude" / "skills" / "whatsapp-message-parser.md").exists()

    def test_whatsapp_keyword_matching(self):
        from whatsapp_watcher import match_keywords
        matched = match_keywords("Please help with urgent invoice payment")
        assert len(matched) >= 2  # "urgent", "invoice", "payment", "help"

    def test_whatsapp_task_creation(self, vault, logger):
        from whatsapp_watcher import create_whatsapp_task
        msg_data = {
            "sender": "Self-Test Sender",
            "text": "Urgent: please review the invoice",
            "timestamp": "2026-02-24T12:00:00",
            "chat_type": "individual",
            "matched_keywords": ["urgent", "invoice"],
        }
        task_path = create_whatsapp_task(msg_data, vault, logger)
        assert task_path.exists()
        content = task_path.read_text(encoding="utf-8")
        assert "type: whatsapp" in content
        assert "priority: high" in content


# ---------------------------------------------------------------------------
# REQ-4: LinkedIn Poster — draft + approval + publish
# ---------------------------------------------------------------------------

class TestReq4LinkedInPoster:
    def test_linkedin_poster_script_exists(self):
        assert (Path(__file__).parent.parent / "scripts" / "linkedin_poster.py").exists()

    def test_linkedin_skill_exists(self):
        assert (Path(__file__).parent.parent / ".claude" / "skills" / "linkedin-poster.md").exists()

    def test_draft_generate_save_approve_publish(self, vault, logger):
        from linkedin_poster import generate_post_draft, save_draft, publish_approved_post

        # Generate
        draft = generate_post_draft("AI Self-Test", "service_promotion")
        assert draft["topic"] == "AI Self-Test"
        assert "body" in draft

        # Save to Pending_Approval
        draft_path = save_draft(draft, vault, logger)
        assert draft_path.exists()
        assert draft_path.parent.name == "Pending_Approval"

        # Approve (move to Approved/)
        approved_path = vault / "Approved" / draft_path.name
        draft_path.rename(approved_path)
        assert approved_path.exists()

        # Publish (simulate mode)
        result = publish_approved_post(approved_path, vault, mode="simulate", logger=logger)
        assert result in ("posted", "simulated")

        # Verify it moved to Done/
        done_files = list((vault / "Done").glob("LINKEDIN_*.md"))
        assert len(done_files) >= 1


# ---------------------------------------------------------------------------
# REQ-5: Reasoning Loop — complexity detection + Plan.md
# ---------------------------------------------------------------------------

class TestReq5ReasoningLoop:
    def test_reasoning_loop_script_exists(self):
        assert (Path(__file__).parent.parent / "scripts" / "reasoning_loop.py").exists()

    def test_reasoning_loop_skill_exists(self):
        assert (Path(__file__).parent.parent / ".claude" / "skills" / "reasoning-loop.md").exists()

    def test_complex_task_creates_plan(self, vault, logger):
        # Create a complex task
        task_file = vault / "Needs_Action" / "selftest-complex.md"
        task_file.write_text(
            "---\ntype: task\npriority: high\ncategory: finance\nstatus: new\n---\n\n"
            "# Process Client Invoice and Schedule Payment\n\n"
            "Review the invoice from Acme Corp, verify amounts, "
            "schedule the payment, and send confirmation.\n",
            encoding="utf-8",
        )

        fm, body = parse_frontmatter(task_file.read_text(encoding="utf-8"))
        complexity = detect_complexity(fm, body)
        assert complexity["is_complex"], f"Expected complex, got signals: {complexity['signals']}"

        # Create plan
        plan_path = create_plan(task_file, fm, body, vault, logger)
        assert plan_path.exists()
        assert plan_path.parent.name == "Plans"

        # Read plan and verify structure
        plan_fm, plan_body, steps = read_plan(plan_path)
        assert len(steps) >= 3
        assert plan_fm.get("type") == "plan"

    def test_simple_task_stays_simple(self):
        fm = {"type": "task", "priority": "low", "category": "general"}
        body = "Water the plants."
        complexity = detect_complexity(fm, body)
        assert not complexity["is_complex"]

    def test_step_execution(self, vault, logger):
        task_file = vault / "Needs_Action" / "selftest-exec.md"
        task_file.write_text(
            "---\ntype: task\npriority: high\nstatus: new\n---\n\n"
            "# Multi-step review and analyze quarterly report\n\n"
            "Review the document, analyze findings, and summarize.\n",
            encoding="utf-8",
        )

        fm, body = parse_frontmatter(task_file.read_text(encoding="utf-8"))
        plan_path = create_plan(task_file, fm, body, vault, logger)
        _, _, steps = read_plan(plan_path)

        # Execute first step
        success = execute_step(plan_path, 1, logger)
        assert success

        # Verify step is marked complete
        _, _, updated_steps = read_plan(plan_path)
        assert updated_steps[0]["is_complete"]


# ---------------------------------------------------------------------------
# REQ-6: Weekly CEO Briefing + Scheduling
# ---------------------------------------------------------------------------

class TestReq6WeeklyBriefing:
    def test_weekly_briefing_script_exists(self):
        assert (Path(__file__).parent.parent / "scripts" / "weekly_briefing.py").exists()

    def test_ceo_briefing_skill_exists(self):
        assert (Path(__file__).parent.parent / ".claude" / "skills" / "ceo-briefing.md").exists()

    def test_briefing_generation(self, vault, logger):
        # Add some tasks for the briefing to report on
        (vault / "Needs_Action" / "selftest-briefing-task.md").write_text(
            "---\ntype: task\nstatus: new\n---\n\n# Test Task\n", encoding="utf-8",
        )

        content, filepath = generate_briefing(vault, logger)
        assert filepath.exists()
        assert "## Executive Summary" in content
        assert "## Task Pipeline" in content
        assert "## Bottlenecks & Risks" in content
        assert "## Recommended Actions" in content

    def test_task_stats(self, vault):
        (vault / "Needs_Action" / "st1.md").write_text("test", encoding="utf-8")
        stats = collect_task_stats(vault)
        assert stats["needs_action"] >= 1
        assert "total_open" in stats

    def test_bottleneck_detection(self, vault, logger):
        bottlenecks = collect_bottlenecks(vault, logger)
        assert isinstance(bottlenecks, list)


# ---------------------------------------------------------------------------
# REQ-7: Orchestrator — single entry point
# ---------------------------------------------------------------------------

class TestReq7Orchestrator:
    def test_orchestrator_script_exists(self):
        assert (Path(__file__).parent.parent / "scripts" / "orchestrator.py").exists()

    def test_orchestrator_skill_exists(self):
        assert (Path(__file__).parent.parent / ".claude" / "skills" / "orchestrator.md").exists()

    def test_all_component_scripts_exist(self, vault):
        components = build_component_list(vault)
        warnings = validate_components(components)
        assert len(warnings) == 0, f"Missing scripts: {warnings}"

    def test_watcher_is_required(self, vault):
        components = build_component_list(vault)
        watcher = [c for c in components if c["name"] == "File Watcher"][0]
        assert watcher["required"] is True


# ---------------------------------------------------------------------------
# REQ-8: 11 Agent Skills (4 Bronze + 7 Silver)
# ---------------------------------------------------------------------------

class TestReq8AgentSkills:
    EXPECTED_SKILLS = [
        # Bronze (4)
        "simple-task-reader.md",
        "process-inbox-item.md",
        "move-to-done.md",
        "check-pending-approvals.md",
        # Silver (7)
        "data-analyzer.md",
        "generate-status-report.md",
        "whatsapp-message-parser.md",
        "linkedin-poster.md",
        "reasoning-loop.md",
        "ceo-briefing.md",
        "orchestrator.md",
    ]

    def test_all_skills_exist(self):
        skills_dir = Path(__file__).parent.parent / ".claude" / "skills"
        for skill in self.EXPECTED_SKILLS:
            assert (skills_dir / skill).exists(), f"Missing skill: {skill}"

    def test_skill_count(self):
        skills_dir = Path(__file__).parent.parent / ".claude" / "skills"
        skills = list(skills_dir.glob("*.md"))
        assert len(skills) >= 11, f"Expected at least 11 skills, found {len(skills)}: {[s.name for s in skills]}"


# ---------------------------------------------------------------------------
# INTEGRATION: End-to-end pipeline test
# ---------------------------------------------------------------------------

class TestEndToEndPipeline:
    """Simulate the full Silver Tier pipeline:
    complex task → Plan.md → processing → briefing → Dashboard
    """

    def test_full_pipeline(self, vault, logger):
        # 1. Create a complex task (simulates watcher output)
        task_file = vault / "Needs_Action" / "selftest-e2e.md"
        task_file.write_text(
            "---\ntype: whatsapp\nfrom: \"Client\"\npriority: high\n"
            "matched_keywords: [\"urgent\", \"invoice\"]\nstatus: new\n---\n\n"
            "# Urgent: Process Invoice and Send Confirmation\n\n"
            "Client sent an urgent request to process invoice #1234 "
            "and confirm payment schedule.\n",
            encoding="utf-8",
        )

        # 2. Process through inbox (triggers reasoning loop)
        result = process_file(task_file, vault, logger)
        assert result in ("plan_created", "planned", "pending_approval")

        # 3. Check Plans/ has a plan (if complex)
        plans = list((vault / "Plans").glob("PLAN_*.md"))
        if result == "plan_created":
            assert len(plans) >= 1
            plan_path = plans[0]
            _, _, steps = read_plan(plan_path)
            assert len(steps) >= 2

        # 4. Generate a briefing
        content, brief_path = generate_briefing(vault, logger)
        assert brief_path.exists()
        assert "Task Pipeline" in content

        # 5. Update Dashboard
        update_dashboard(vault, logger)
        dashboard = vault / "Dashboard.md"
        assert dashboard.exists()
        dash_content = dashboard.read_text(encoding="utf-8")
        assert "Quick Status" in dash_content

        # 6. Verify audit trail
        entries = logger.read_log()
        actions = [e["action"] for e in entries]
        assert "briefing_generated" in actions
        assert "dashboard_updated" in actions


# ---------------------------------------------------------------------------
# INFRASTRUCTURE: Verify test coverage and file structure
# ---------------------------------------------------------------------------

class TestInfrastructure:
    def test_all_scripts_have_tests(self):
        scripts_dir = Path(__file__).parent.parent / "scripts"
        tests_dir = Path(__file__).parent
        # Scripts that should have test files
        testable_scripts = [
            "watcher.py", "process_inbox.py", "update_dashboard.py",
            "gmail_watcher.py", "data_analyzer.py", "whatsapp_watcher.py",
            "linkedin_poster.py", "reasoning_loop.py", "weekly_briefing.py",
            "orchestrator.py",
        ]
        for script in testable_scripts:
            test_file = tests_dir / f"test_{script}"
            assert test_file.exists(), f"Missing test file for {script}"

    def test_readme_exists(self):
        assert (Path(__file__).parent.parent / "README.md").exists()

    def test_env_example_exists(self):
        assert (Path(__file__).parent.parent / ".env.example").exists()

    def test_gitignore_exists(self):
        assert (Path(__file__).parent.parent / ".gitignore").exists()

    def test_requirements_txt_exists(self):
        req = Path(__file__).parent.parent / "requirements.txt"
        assert req.exists()
        content = req.read_text(encoding="utf-8")
        assert "watchdog" in content
        assert "playwright" in content
        assert "pandas" in content
