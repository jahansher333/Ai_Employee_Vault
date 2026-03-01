"""Tests for LinkedIn poster — drafts, templates, publishing, dashboard."""

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from linkedin_poster import (
    LINKEDIN_SELECTORS,
    LINKEDIN_SESSION_DIR,
    POST_TEMPLATES,
    build_social_posts_table,
    check_linkedin_session,
    generate_post_draft,
    post_to_linkedin_playwright,
    publish_approved_post,
    save_draft,
    scan_approved_posts,
    simulate_post,
    update_dashboard_social,
)


# ---------------------------------------------------------------------------
# Draft generation tests
# ---------------------------------------------------------------------------


class TestGenerateDraft:
    def test_service_promotion(self):
        draft = generate_post_draft("AI Automation", "service_promotion")
        assert draft["topic"] == "AI Automation"
        assert draft["template"] == "service_promotion"
        assert len(draft["body"]) > 50
        assert len(draft["hashtags"]) >= 3
        assert "generated_at" in draft

    def test_case_study(self):
        draft = generate_post_draft("Client Success", "case_study")
        assert draft["template"] == "case_study"
        assert "client success" in draft["body"].lower()

    def test_thought_leadership(self):
        draft = generate_post_draft("Future of AI", "thought_leadership")
        assert draft["template"] == "thought_leadership"
        assert "future of ai" in draft["body"].lower()

    def test_invalid_template(self):
        with pytest.raises(ValueError, match="Unknown template"):
            generate_post_draft("Topic", "nonexistent")

    def test_default_template(self):
        draft = generate_post_draft("Test Topic")
        assert draft["template"] == "service_promotion"

    def test_all_templates_exist(self):
        for name in POST_TEMPLATES:
            draft = generate_post_draft("Test", name)
            assert draft["body"]
            assert draft["hashtags"]


# ---------------------------------------------------------------------------
# Save draft tests
# ---------------------------------------------------------------------------


class TestSaveDraft:
    def test_creates_file(self, vault, logger):
        draft = generate_post_draft("Test Topic")
        path = save_draft(draft, vault, logger)
        assert path.exists()
        assert path.parent.name == "Pending_Approval"
        assert path.name.startswith("LINKEDIN_")
        assert path.name.endswith(".md")

    def test_file_content(self, vault, logger):
        draft = generate_post_draft("AI Services", "service_promotion")
        path = save_draft(draft, vault, logger)
        content = path.read_text(encoding="utf-8")

        assert "type: linkedin_post" in content
        assert 'topic: "AI Services"' in content
        assert "template: service_promotion" in content
        assert "platform: linkedin" in content
        assert "status: draft" in content
        assert "# LinkedIn Post Draft: AI Services" in content
        assert "## Post Content" in content

    def test_audit_log(self, vault, logger):
        draft = generate_post_draft("Logged Topic")
        save_draft(draft, vault, logger)
        entries = logger.read_log()
        actions = [e["action"] for e in entries]
        assert "linkedin_draft_created" in actions


# ---------------------------------------------------------------------------
# Scan approved posts
# ---------------------------------------------------------------------------


class TestScanApproved:
    def test_empty(self, vault):
        assert scan_approved_posts(vault) == []

    def test_finds_linkedin_files(self, vault):
        (vault / "Approved" / "LINKEDIN_120000_topic.md").write_text(
            "---\ntype: linkedin_post\n---\n", encoding="utf-8"
        )
        (vault / "Approved" / "other.md").write_text("nope", encoding="utf-8")
        result = scan_approved_posts(vault)
        assert len(result) == 1
        assert result[0].name == "LINKEDIN_120000_topic.md"

    def test_no_approved_dir(self, tmp_path):
        assert scan_approved_posts(tmp_path) == []


# ---------------------------------------------------------------------------
# Simulate post
# ---------------------------------------------------------------------------


class TestSimulatePost:
    def test_returns_success(self):
        result = simulate_post("content", "Test Title")
        assert result["success"] is True
        assert result["mode"] == "simulate"
        assert result["post_id"].startswith("SIM-")


# ---------------------------------------------------------------------------
# Publish approved post
# ---------------------------------------------------------------------------


class TestPublishApproved:
    def _make_approved_file(self, vault):
        content = (
            '---\n'
            'type: linkedin_post\n'
            'topic: "Test Post"\n'
            'template: service_promotion\n'
            'platform: linkedin\n'
            'status: approved\n'
            'generated_at: "2026-02-22T10:00:00Z"\n'
            'hashtags: ["Test"]\n'
            '---\n\n'
            '# LinkedIn Post Draft: Test Post\n\n'
            '## Post Content\n\n'
            'This is test content.\n'
        )
        path = vault / "Approved" / "LINKEDIN_100000_Test-Post.md"
        path.write_text(content, encoding="utf-8")
        return path

    def test_simulate_moves_to_done(self, vault, logger):
        path = self._make_approved_file(vault)
        status = publish_approved_post(path, vault, mode="simulate", logger=logger)
        assert status == "simulated"
        assert not path.exists()
        done_files = list((vault / "Done").glob("LINKEDIN_*.md"))
        assert len(done_files) == 1

    def test_done_file_has_posted_status(self, vault, logger):
        path = self._make_approved_file(vault)
        publish_approved_post(path, vault, mode="simulate", logger=logger)
        done_file = list((vault / "Done").glob("LINKEDIN_*.md"))[0]
        content = done_file.read_text(encoding="utf-8")
        assert "status: posted" in content
        assert "post_mode: simulate" in content
        assert "posted_at:" in content


# ---------------------------------------------------------------------------
# Dashboard social posts
# ---------------------------------------------------------------------------


class TestDashboard:
    def test_build_table_empty(self, vault):
        table = build_social_posts_table(vault)
        assert table == ""

    def test_build_table_with_posts(self, vault):
        (vault / "Pending_Approval" / "LINKEDIN_100000_topic-a.md").write_text(
            '---\ntype: linkedin_post\ntopic: "Topic A"\nstatus: draft\n'
            'generated_at: "2026-02-22T10:00:00Z"\n---\n',
            encoding="utf-8",
        )
        table = build_social_posts_table(vault)
        assert "Topic A" in table
        assert "draft" in table
        assert "linkedin" in table

    def test_update_dashboard_creates_section(self, vault, logger):
        # Create a minimal dashboard
        dashboard = vault / "Dashboard.md"
        dashboard.write_text(
            "# Dashboard\n\n## How It Works\n\nSome content.\n",
            encoding="utf-8",
        )
        # Create a post
        (vault / "Pending_Approval" / "LINKEDIN_100000_test.md").write_text(
            '---\ntype: linkedin_post\ntopic: "Test"\nstatus: draft\n'
            'generated_at: "2026-02-22T10:00:00Z"\n---\n',
            encoding="utf-8",
        )
        update_dashboard_social(vault, logger)
        content = dashboard.read_text(encoding="utf-8")
        assert "<!-- START_SOCIAL_POSTS -->" in content
        assert "<!-- END_SOCIAL_POSTS -->" in content
        assert "Test" in content

    def test_update_replaces_existing_section(self, vault, logger):
        dashboard = vault / "Dashboard.md"
        dashboard.write_text(
            "# Dashboard\n\n"
            "## Recent Social Posts\n\n"
            "<!-- START_SOCIAL_POSTS -->\n"
            "old data\n"
            "<!-- END_SOCIAL_POSTS -->\n\n"
            "## How It Works\n",
            encoding="utf-8",
        )
        update_dashboard_social(vault, logger)
        content = dashboard.read_text(encoding="utf-8")
        assert "old data" not in content


# ---------------------------------------------------------------------------
# Playwright constants & session check
# ---------------------------------------------------------------------------


class TestPlaywrightConstants:
    def test_selectors_keys(self):
        expected = {"feed", "start_post_button", "post_editor", "post_button"}
        assert expected == set(LINKEDIN_SELECTORS.keys())

    def test_session_dir_default(self):
        assert "linkedin_session" in LINKEDIN_SESSION_DIR


class TestCheckLinkedinSession:
    def test_returns_true_when_feed_found(self):
        page = MagicMock()
        page.url = "https://www.linkedin.com/feed/"
        page.title.return_value = "Feed | LinkedIn"
        # Fast-path: URL contains "feed" → returns True without wait_for_selector
        assert check_linkedin_session(page) is True

    def test_returns_true_via_selector_fallback(self):
        page = MagicMock()
        page.url = "https://www.linkedin.com/"
        page.title.return_value = "LinkedIn"
        page.wait_for_selector.return_value = True
        assert check_linkedin_session(page) is True
        page.wait_for_selector.assert_called_once_with(
            LINKEDIN_SELECTORS["feed"], timeout=3_000
        )

    def test_returns_false_on_timeout(self):
        page = MagicMock()
        page.url = "https://www.linkedin.com/login"
        page.title.return_value = "Login"
        assert check_linkedin_session(page) is False


# ---------------------------------------------------------------------------
# Playwright posting
# ---------------------------------------------------------------------------


class TestPostToLinkedinPlaywright:
    def test_missing_session_dir(self, tmp_path):
        missing = str(tmp_path / "nonexistent")
        result = post_to_linkedin_playwright("Hello", session_dir=missing)
        assert result["success"] is False
        assert result["mode"] == "playwright"
        assert "not found" in result["error"]

    def test_successful_post(self, tmp_path):
        session_dir = str(tmp_path / "li_session")
        Path(session_dir).mkdir()

        mock_page = MagicMock()
        mock_page.url = "https://www.linkedin.com/feed/"

        mock_ctx = MagicMock()
        mock_ctx.pages = [mock_page]

        mock_pw = MagicMock()
        mock_pw.chromium.launch_persistent_context.return_value = mock_ctx

        mock_sync = MagicMock()
        mock_sync.__enter__ = MagicMock(return_value=mock_pw)
        mock_sync.__exit__ = MagicMock(return_value=False)

        with patch(
            "playwright.sync_api.sync_playwright",
            return_value=mock_sync,
        ):
            result = post_to_linkedin_playwright(
                "Test post content", session_dir=session_dir
            )

        assert result["success"] is True
        assert result["mode"] == "playwright"
        assert result["post_id"].startswith("PW-")

    def test_expired_session_returns_error(self, tmp_path):
        session_dir = str(tmp_path / "li_session")
        Path(session_dir).mkdir()

        mock_page = MagicMock()
        # Simulate session check failure
        mock_page.wait_for_selector.side_effect = Exception("timeout")

        mock_ctx = MagicMock()
        mock_ctx.pages = [mock_page]

        mock_pw = MagicMock()
        mock_pw.chromium.launch_persistent_context.return_value = mock_ctx

        mock_sync = MagicMock()
        mock_sync.__enter__ = MagicMock(return_value=mock_pw)
        mock_sync.__exit__ = MagicMock(return_value=False)

        with patch(
            "playwright.sync_api.sync_playwright",
            return_value=mock_sync,
        ):
            result = post_to_linkedin_playwright(
                "Test post", session_dir=session_dir
            )

        assert result["success"] is False
        assert "expired" in result["error"].lower()


# ---------------------------------------------------------------------------
# Publish approved post — playwright mode
# ---------------------------------------------------------------------------


class TestPublishApprovedPlaywright:
    def _make_approved_file(self, vault):
        content = (
            '---\n'
            'type: linkedin_post\n'
            'topic: "Playwright Test"\n'
            'template: service_promotion\n'
            'platform: linkedin\n'
            'status: approved\n'
            'generated_at: "2026-02-22T10:00:00Z"\n'
            'hashtags: ["Test"]\n'
            '---\n\n'
            '# LinkedIn Post Draft: Playwright Test\n\n'
            '## Post Content\n\n'
            'This is playwright test content.\n'
        )
        path = vault / "Approved" / "LINKEDIN_100000_Playwright-Test.md"
        path.write_text(content, encoding="utf-8")
        return path

    @patch("linkedin_poster.post_to_linkedin_playwright")
    def test_playwright_mode_success(self, mock_pw_post, vault, logger):
        mock_pw_post.return_value = {
            "success": True, "post_id": "PW-123", "mode": "playwright",
        }
        path = self._make_approved_file(vault)
        status = publish_approved_post(path, vault, mode="playwright",
                                        logger=logger)
        assert status == "posted"
        assert not path.exists()
        done_files = list((vault / "Done").glob("LINKEDIN_*.md"))
        assert len(done_files) == 1

    @patch("linkedin_poster.post_to_linkedin_playwright")
    def test_playwright_fallback_to_simulate(self, mock_pw_post, vault,
                                              logger):
        mock_pw_post.return_value = {
            "success": False, "post_id": None, "mode": "playwright",
            "error": "Session expired",
        }
        path = self._make_approved_file(vault)
        status = publish_approved_post(path, vault, mode="playwright",
                                        logger=logger)
        assert status == "simulated"
        done_files = list((vault / "Done").glob("LINKEDIN_*.md"))
        assert len(done_files) == 1
