"""Tests for social_poster.py — multi-platform social media posting."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from unittest.mock import MagicMock, patch

from social_poster import (
    PLATFORMS,
    generate_facebook_draft,
    generate_instagram_draft,
    generate_twitter_draft,
    generate_social_draft,
    save_social_draft,
    publish_social_post,
    get_social_activity_summary,
    scan_approved_social_posts,
    simulate_social_post,
    post_to_facebook_playwright,
    post_to_instagram_playwright,
    check_facebook_session,
    check_instagram_session,
    _generate_hashtags,
    _sanitize_topic,
    _parse_frontmatter,
    _extract_post_content,
    build_multi_platform_social_table,
)


# ---------------------------------------------------------------------------
# Platform configuration
# ---------------------------------------------------------------------------

class TestPlatformConfig:
    def test_three_platforms_defined(self):
        assert set(PLATFORMS) == {"facebook", "instagram", "twitter"}

    def test_twitter_char_limit(self):
        assert PLATFORMS["twitter"]["char_limit"] == 280

    def test_instagram_char_limit(self):
        assert PLATFORMS["instagram"]["char_limit"] == 2200

    def test_facebook_no_strict_limit(self):
        assert PLATFORMS["facebook"]["char_limit"] is None

    def test_prefixes(self):
        assert PLATFORMS["facebook"]["prefix"] == "FACEBOOK"
        assert PLATFORMS["instagram"]["prefix"] == "INSTAGRAM"
        assert PLATFORMS["twitter"]["prefix"] == "TWITTER"


# ---------------------------------------------------------------------------
# Hashtag generation
# ---------------------------------------------------------------------------

class TestHashtags:
    def test_generates_topic_tag(self):
        tags = _generate_hashtags("AI Update", ["Default"], limit=5)
        assert "AiUpdate" in tags

    def test_includes_defaults(self):
        tags = _generate_hashtags("Test", ["Alpha", "Beta"], limit=5)
        assert "Alpha" in tags
        assert "Beta" in tags

    def test_respects_limit(self):
        tags = _generate_hashtags("Big Topic", ["A", "B", "C", "D", "E"], limit=3)
        assert len(tags) <= 3


# ---------------------------------------------------------------------------
# Topic sanitization
# ---------------------------------------------------------------------------

class TestSanitizeTopic:
    def test_basic_sanitize(self):
        assert _sanitize_topic("Hello World!") == "Hello-World"

    def test_truncates(self):
        result = _sanitize_topic("A" * 100, max_len=10)
        assert len(result) <= 10

    def test_strips_special_chars(self):
        result = _sanitize_topic("AI & ML: The Future!")
        assert "&" not in result
        assert ":" not in result


# ---------------------------------------------------------------------------
# Draft generation — Facebook
# ---------------------------------------------------------------------------

class TestFacebookDraft:
    def test_returns_dict(self):
        draft = generate_facebook_draft("AI Tools")
        assert isinstance(draft, dict)

    def test_platform_set(self):
        draft = generate_facebook_draft("AI Tools")
        assert draft["platform"] == "facebook"

    def test_body_contains_topic(self):
        draft = generate_facebook_draft("AI Tools")
        assert "AI Tools" in draft["body"]

    def test_has_hashtags(self):
        draft = generate_facebook_draft("AI Tools")
        assert len(draft["hashtags"]) > 0

    def test_has_char_count(self):
        draft = generate_facebook_draft("AI Tools")
        assert draft["char_count"] == len(draft["body"])

    def test_has_generated_at(self):
        draft = generate_facebook_draft("AI Tools")
        assert "generated_at" in draft


# ---------------------------------------------------------------------------
# Draft generation — Instagram
# ---------------------------------------------------------------------------

class TestInstagramDraft:
    def test_platform_set(self):
        draft = generate_instagram_draft("Business")
        assert draft["platform"] == "instagram"

    def test_body_contains_topic(self):
        draft = generate_instagram_draft("Business Growth")
        assert "business growth" in draft["body"].lower()

    def test_more_hashtags_than_twitter(self):
        ig = generate_instagram_draft("Test")
        tw = generate_twitter_draft("Test")
        assert len(ig["hashtags"]) > len(tw["hashtags"])


# ---------------------------------------------------------------------------
# Draft generation — Twitter
# ---------------------------------------------------------------------------

class TestTwitterDraft:
    def test_platform_set(self):
        draft = generate_twitter_draft("News")
        assert draft["platform"] == "twitter"

    def test_within_char_limit(self):
        draft = generate_twitter_draft("Short Update")
        assert draft["within_limit"] is True
        assert draft["char_count"] <= 280

    def test_long_topic_still_within_limit(self):
        long_topic = "A very long topic that goes on and on about many things"
        draft = generate_twitter_draft(long_topic)
        assert draft["within_limit"] is True
        assert draft["char_count"] <= 280

    def test_has_hashtags(self):
        draft = generate_twitter_draft("Test")
        assert len(draft["hashtags"]) <= 3  # minimal style


# ---------------------------------------------------------------------------
# Generic draft dispatcher
# ---------------------------------------------------------------------------

class TestGenerateSocialDraft:
    def test_facebook_dispatch(self):
        draft = generate_social_draft("Test", "facebook")
        assert draft["platform"] == "facebook"

    def test_twitter_dispatch(self):
        draft = generate_social_draft("Test", "twitter")
        assert draft["platform"] == "twitter"

    def test_instagram_dispatch(self):
        draft = generate_social_draft("Test", "instagram")
        assert draft["platform"] == "instagram"

    def test_unknown_platform_raises(self):
        with pytest.raises(ValueError, match="Unknown platform"):
            generate_social_draft("Test", "tiktok")


# ---------------------------------------------------------------------------
# Save draft to Pending_Approval/
# ---------------------------------------------------------------------------

class TestSaveSocialDraft:
    def test_creates_file(self, vault):
        draft = generate_facebook_draft("Launch Day")
        path = save_social_draft(draft, vault)
        assert path.exists()
        assert path.suffix == ".md"

    def test_file_in_pending_approval(self, vault):
        draft = generate_facebook_draft("Launch Day")
        path = save_social_draft(draft, vault)
        assert path.parent.name == "Pending_Approval"

    def test_facebook_prefix(self, vault):
        draft = generate_facebook_draft("Update")
        path = save_social_draft(draft, vault)
        assert path.name.startswith("FACEBOOK_")

    def test_twitter_prefix(self, vault):
        draft = generate_twitter_draft("News")
        path = save_social_draft(draft, vault)
        assert path.name.startswith("TWITTER_")

    def test_instagram_prefix(self, vault):
        draft = generate_instagram_draft("Tips")
        path = save_social_draft(draft, vault)
        assert path.name.startswith("INSTAGRAM_")

    def test_frontmatter_contains_platform(self, vault):
        draft = generate_twitter_draft("Tech")
        path = save_social_draft(draft, vault)
        content = path.read_text(encoding="utf-8")
        assert "platform: twitter" in content

    def test_frontmatter_contains_status(self, vault):
        draft = generate_facebook_draft("Test")
        path = save_social_draft(draft, vault)
        content = path.read_text(encoding="utf-8")
        assert "status: draft" in content

    def test_with_logger(self, vault, logger):
        draft = generate_facebook_draft("Logged Post")
        save_social_draft(draft, vault, logger)
        entries = logger.read_log()
        draft_entries = [e for e in entries if "draft_created" in e.get("action", "")]
        assert len(draft_entries) >= 1


# ---------------------------------------------------------------------------
# Publish (simulation mode)
# ---------------------------------------------------------------------------

class TestPublishSocialPost:
    def _create_approved_post(self, vault, platform="facebook"):
        """Helper: create a draft, move to Approved/."""
        draft = generate_social_draft("Test Publish", platform)
        path = save_social_draft(draft, vault)
        # Move to Approved/
        approved = vault / "Approved"
        approved.mkdir(exist_ok=True)
        dest = approved / path.name
        path.rename(dest)
        return dest

    def test_publish_moves_to_done(self, vault, monkeypatch):
        monkeypatch.setenv("FACEBOOK_POST_MODE", "simulate")
        approved_path = self._create_approved_post(vault, "facebook")
        result = publish_social_post(approved_path, vault)
        assert result == "simulated"
        # File should be in Done/
        assert not approved_path.exists()
        done_files = list((vault / "Done").glob("FACEBOOK_*.md"))
        assert len(done_files) == 1

    def test_publish_updates_status(self, vault, monkeypatch):
        monkeypatch.setenv("TWITTER_POST_MODE", "simulate")
        approved_path = self._create_approved_post(vault, "twitter")
        publish_social_post(approved_path, vault)
        done_file = list((vault / "Done").glob("TWITTER_*.md"))[0]
        content = done_file.read_text(encoding="utf-8")
        assert "status: posted" in content

    def test_publish_with_logger(self, vault, logger, monkeypatch):
        monkeypatch.setenv("INSTAGRAM_POST_MODE", "simulate")
        approved_path = self._create_approved_post(vault, "instagram")
        publish_social_post(approved_path, vault, logger)
        entries = logger.read_log()
        published = [e for e in entries if "published" in e.get("action", "")]
        assert len(published) >= 1


# ---------------------------------------------------------------------------
# Simulate social post
# ---------------------------------------------------------------------------

class TestSimulateSocialPost:
    def test_returns_success(self):
        result = simulate_social_post("Hello!", "facebook", "Test Post")
        assert result["success"] is True
        assert result["mode"] == "simulate"
        assert result["post_id"].startswith("SIM-FACEBOOK-")


# ---------------------------------------------------------------------------
# Social activity summary
# ---------------------------------------------------------------------------

class TestSocialActivitySummary:
    def test_empty_vault(self, vault):
        summary = get_social_activity_summary(vault)
        assert summary["success"] is True
        assert summary["total_posted"] == 0
        assert summary["total_pending"] == 0

    def test_counts_drafts(self, vault):
        # Create drafts for different platforms
        save_social_draft(generate_facebook_draft("A"), vault)
        save_social_draft(generate_twitter_draft("B"), vault)
        save_social_draft(generate_instagram_draft("C"), vault)

        summary = get_social_activity_summary(vault)
        assert summary["summary"]["facebook"]["drafts"] == 1
        assert summary["summary"]["twitter"]["drafts"] == 1
        assert summary["summary"]["instagram"]["drafts"] == 1
        assert summary["total_pending"] == 3

    def test_counts_linkedin(self, vault):
        # Create a LinkedIn draft manually
        pa = vault / "Pending_Approval"
        (pa / "LINKEDIN_001_test.md").write_text("test", encoding="utf-8")
        summary = get_social_activity_summary(vault)
        assert summary["summary"]["linkedin"]["drafts"] == 1

    def test_includes_all_platforms(self, vault):
        summary = get_social_activity_summary(vault)
        assert "facebook" in summary["summary"]
        assert "instagram" in summary["summary"]
        assert "twitter" in summary["summary"]
        assert "linkedin" in summary["summary"]


# ---------------------------------------------------------------------------
# Scan approved posts
# ---------------------------------------------------------------------------

class TestScanApprovedPosts:
    def test_empty_approved(self, vault):
        posts = scan_approved_social_posts(vault)
        assert posts == []

    def test_finds_approved_posts(self, vault):
        approved = vault / "Approved"
        (approved / "FACEBOOK_001_test.md").write_text("fb", encoding="utf-8")
        (approved / "TWITTER_001_test.md").write_text("tw", encoding="utf-8")
        (approved / "INSTAGRAM_001_test.md").write_text("ig", encoding="utf-8")
        posts = scan_approved_social_posts(vault)
        assert len(posts) == 3

    def test_ignores_linkedin(self, vault):
        approved = vault / "Approved"
        (approved / "LINKEDIN_001_test.md").write_text("li", encoding="utf-8")
        posts = scan_approved_social_posts(vault)
        assert len(posts) == 0


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        content = "---\nplatform: twitter\nstatus: draft\n---\n\n# Body"
        fm, body = _parse_frontmatter(content)
        assert fm["platform"] == "twitter"
        assert fm["status"] == "draft"
        assert "# Body" in body

    def test_no_frontmatter(self):
        fm, body = _parse_frontmatter("Just text")
        assert fm == {}
        assert body == "Just text"


# ---------------------------------------------------------------------------
# Extract post content
# ---------------------------------------------------------------------------

class TestExtractPostContent:
    def test_extracts_section(self):
        body = "# Title\n\n## Post Content\n\nHello world!\n\n## Other"
        result = _extract_post_content(body)
        assert "Hello world!" in result

    def test_no_section(self):
        body = "Just plain text"
        result = _extract_post_content(body)
        assert result == "Just plain text"


# ---------------------------------------------------------------------------
# Facebook Playwright
# ---------------------------------------------------------------------------

class TestFacebookPlaywright:
    def test_missing_session_dir(self):
        result = post_to_facebook_playwright(
            "Hello!", session_dir="/nonexistent/path/fb_session"
        )
        assert result["success"] is False
        assert "Session directory not found" in result["error"]
        assert result["mode"] == "playwright"

    def test_successful_post_mock(self, tmp_path):
        """Mock Playwright to simulate a successful Facebook post."""
        session_dir = tmp_path / "fb_session"
        session_dir.mkdir()

        mock_page = MagicMock()
        mock_page.url = "https://www.facebook.com/"
        mock_page.title.return_value = "Facebook"
        # check_facebook_session needs wait_for_selector to succeed
        mock_page.wait_for_selector.return_value = True
        mock_page.locator.return_value = MagicMock()

        mock_ctx = MagicMock()
        mock_ctx.pages = [mock_page]

        mock_pw_instance = MagicMock()
        mock_pw_instance.chromium.launch_persistent_context.return_value = mock_ctx

        mock_pw = MagicMock()
        mock_pw.__enter__ = MagicMock(return_value=mock_pw_instance)
        mock_pw.__exit__ = MagicMock(return_value=False)

        with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
            with patch("social_poster.check_facebook_session", return_value=True):
                with patch("social_poster._try_selectors", side_effect=[
                    '[aria-label="What\'s on your mind?"]',  # start post
                    'div[contenteditable="true"][role="textbox"]',  # editor
                    '[aria-label="Post"]',  # post button
                ]):
                    result = post_to_facebook_playwright(
                        "Test post!", session_dir=str(session_dir)
                    )

        assert result["success"] is True
        assert result["mode"] == "playwright"
        assert result["post_id"].startswith("PW-FB-")

    def test_session_expired(self, tmp_path):
        """Playwright returns error when session is expired."""
        session_dir = tmp_path / "fb_session"
        session_dir.mkdir()

        mock_page = MagicMock()
        mock_page.url = "https://www.facebook.com/login"
        mock_page.title.return_value = "Log in to Facebook"
        mock_page.wait_for_selector.side_effect = Exception("timeout")

        mock_ctx = MagicMock()
        mock_ctx.pages = [mock_page]

        mock_pw_instance = MagicMock()
        mock_pw_instance.chromium.launch_persistent_context.return_value = mock_ctx

        mock_pw = MagicMock()
        mock_pw.__enter__ = MagicMock(return_value=mock_pw_instance)
        mock_pw.__exit__ = MagicMock(return_value=False)

        with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
            with patch("social_poster.check_facebook_session", return_value=False):
                result = post_to_facebook_playwright(
                    "Test post!", session_dir=str(session_dir)
                )

        assert result["success"] is False
        assert "expired" in result["error"].lower() or "re-authenticate" in result["error"].lower()

    def test_playwright_fallback_to_simulate(self, vault, monkeypatch):
        """When playwright mode fails, publish_social_post falls back to simulate."""
        monkeypatch.setenv("FACEBOOK_POST_MODE", "playwright")

        # Create an approved Facebook post
        draft = generate_facebook_draft("Test Fallback")
        path = save_social_draft(draft, vault)
        approved = vault / "Approved"
        approved.mkdir(exist_ok=True)
        dest = approved / path.name
        path.rename(dest)

        with patch("social_poster.post_to_facebook_playwright", return_value={
            "success": False, "post_id": None, "mode": "playwright",
            "error": "Session not found",
        }):
            result = publish_social_post(dest, vault)

        assert result == "simulated"
        done_files = list((vault / "Done").glob("FACEBOOK_*.md"))
        assert len(done_files) == 1


# ---------------------------------------------------------------------------
# Instagram Playwright
# ---------------------------------------------------------------------------

class TestInstagramPlaywright:
    def test_missing_session_dir(self):
        result = post_to_instagram_playwright(
            "Hello!", session_dir="/nonexistent/path/ig_session"
        )
        assert result["success"] is False
        assert "Session directory not found" in result["error"]
        assert result["mode"] == "playwright"

    def test_successful_post_mock(self, tmp_path):
        """Mock Playwright to simulate a successful Instagram post."""
        session_dir = tmp_path / "ig_session"
        session_dir.mkdir()

        # Mock SVG locator with bounding_box for the Create button
        mock_svg = MagicMock()
        mock_svg.bounding_box.return_value = {"x": 10, "y": 200, "width": 24, "height": 24}

        # Mock span locators for submenu — one "Post" item below the button
        mock_post_span = MagicMock()
        mock_post_span.inner_text.return_value = "Post"
        mock_post_span.is_visible.return_value = True
        mock_post_span.bounding_box.return_value = {"x": 10, "y": 250, "width": 50, "height": 20}

        # Mock file input
        mock_file_input = MagicMock()
        mock_file_input.count.return_value = 1

        # Mock Next button
        mock_next_btn = MagicMock()

        # Mock page
        mock_page = MagicMock()
        mock_page.url = "https://www.instagram.com/"
        mock_page.title.return_value = "Instagram"
        mock_page.wait_for_selector.return_value = True

        def locator_dispatch(selector):
            if selector == 'svg[aria-label="New post"]':
                loc = MagicMock()
                loc.first = mock_svg
                return loc
            elif selector == 'input[type="file"]':
                loc = MagicMock()
                loc.count.return_value = 1
                loc.first = mock_file_input
                return loc
            elif 'Next' in selector:
                loc = MagicMock()
                loc.first = mock_next_btn
                return loc
            elif selector == "span":
                loc = MagicMock()
                loc.all.return_value = [mock_post_span]
                return loc
            else:
                return MagicMock()

        mock_page.locator = locator_dispatch

        mock_ctx = MagicMock()
        mock_ctx.pages = [mock_page]

        mock_pw_instance = MagicMock()
        mock_pw_instance.chromium.launch_persistent_context.return_value = mock_ctx

        mock_pw = MagicMock()
        mock_pw.__enter__ = MagicMock(return_value=mock_pw_instance)
        mock_pw.__exit__ = MagicMock(return_value=False)

        with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
            with patch("social_poster.check_instagram_session", return_value=True):
                with patch("social_poster.generate_instagram_image", return_value=tmp_path / "test.png"):
                    with patch("social_poster._try_selectors", return_value='div[aria-label="Write a caption..."]'):
                        result = post_to_instagram_playwright(
                            "Test caption!", session_dir=str(session_dir)
                        )

        assert result["success"] is True
        assert result["mode"] == "playwright"
        assert result["post_id"].startswith("PW-IG-")

    def test_session_expired(self, tmp_path):
        """Playwright returns error when session is expired."""
        session_dir = tmp_path / "ig_session"
        session_dir.mkdir()

        mock_page = MagicMock()
        mock_page.url = "https://www.instagram.com/accounts/login/"
        mock_page.title.return_value = "Login"
        mock_page.wait_for_selector.side_effect = Exception("timeout")

        mock_ctx = MagicMock()
        mock_ctx.pages = [mock_page]

        mock_pw_instance = MagicMock()
        mock_pw_instance.chromium.launch_persistent_context.return_value = mock_ctx

        mock_pw = MagicMock()
        mock_pw.__enter__ = MagicMock(return_value=mock_pw_instance)
        mock_pw.__exit__ = MagicMock(return_value=False)

        with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
            with patch("social_poster.check_instagram_session", return_value=False):
                result = post_to_instagram_playwright(
                    "Test caption!", session_dir=str(session_dir)
                )

        assert result["success"] is False
        assert "expired" in result["error"].lower() or "re-authenticate" in result["error"].lower()

    def test_playwright_fallback_to_simulate(self, vault, monkeypatch):
        """When playwright mode fails, publish_social_post falls back to simulate."""
        monkeypatch.setenv("INSTAGRAM_POST_MODE", "playwright")

        # Create an approved Instagram post
        draft = generate_instagram_draft("Test Fallback")
        path = save_social_draft(draft, vault)
        approved = vault / "Approved"
        approved.mkdir(exist_ok=True)
        dest = approved / path.name
        path.rename(dest)

        with patch("social_poster.post_to_instagram_playwright", return_value={
            "success": False, "post_id": None, "mode": "playwright",
            "error": "Session not found",
        }):
            result = publish_social_post(dest, vault)

        assert result == "simulated"
        done_files = list((vault / "Done").glob("INSTAGRAM_*.md"))
        assert len(done_files) == 1


# ---------------------------------------------------------------------------
# Session check functions
# ---------------------------------------------------------------------------

class TestCheckFacebookSession:
    def test_login_url_returns_false(self):
        page = MagicMock()
        page.url = "https://www.facebook.com/login"
        page.title.return_value = "Log In"
        assert check_facebook_session(page) is False

    def test_checkpoint_url_returns_false(self):
        page = MagicMock()
        page.url = "https://www.facebook.com/checkpoint/123"
        page.title.return_value = "Facebook"
        assert check_facebook_session(page) is False

    def test_feed_with_auth_selector_returns_true(self):
        page = MagicMock()
        page.url = "https://www.facebook.com/"
        page.title.return_value = "Facebook"
        # Simulate finding an authenticated selector
        page.wait_for_selector.return_value = True
        assert check_facebook_session(page) is True

    def test_feed_no_auth_selectors_returns_false(self):
        page = MagicMock()
        page.url = "https://www.facebook.com/"
        page.title.return_value = "Facebook"
        page.wait_for_selector.side_effect = Exception("timeout")
        assert check_facebook_session(page) is False


class TestCheckInstagramSession:
    def test_login_url_returns_false(self):
        page = MagicMock()
        page.url = "https://www.instagram.com/accounts/login/"
        page.title.return_value = "Login"
        assert check_instagram_session(page) is False

    def test_challenge_url_returns_false(self):
        page = MagicMock()
        page.url = "https://www.instagram.com/challenge/123"
        page.title.return_value = "Instagram"
        assert check_instagram_session(page) is False

    def test_feed_with_auth_selector_returns_true(self):
        page = MagicMock()
        page.url = "https://www.instagram.com/"
        page.title.return_value = "Instagram"
        page.wait_for_selector.return_value = True
        assert check_instagram_session(page) is True

    def test_feed_no_auth_selectors_returns_false(self):
        page = MagicMock()
        page.url = "https://www.instagram.com/"
        page.title.return_value = "Instagram"
        page.wait_for_selector.side_effect = Exception("timeout")
        assert check_instagram_session(page) is False


# ---------------------------------------------------------------------------
# Multi-platform social table for Dashboard
# ---------------------------------------------------------------------------

class TestBuildMultiPlatformSocialTable:
    def test_empty_vault(self, vault):
        table = build_multi_platform_social_table(vault)
        assert "Platform" in table
        assert "FB (Facebook)" in table
        assert "IG (Instagram)" in table
        assert "X (Twitter)" in table
        assert "LI (Linkedin)" in table

    def test_counts_posts(self, vault):
        # Create some files in various folders
        pa = vault / "Pending_Approval"
        pa.mkdir(exist_ok=True)
        (pa / "FACEBOOK_001_test.md").write_text("draft", encoding="utf-8")
        (pa / "INSTAGRAM_001_test.md").write_text("draft", encoding="utf-8")
        done = vault / "Done"
        done.mkdir(exist_ok=True)
        (done / "TWITTER_001_test.md").write_text("done", encoding="utf-8")
        (done / "LINKEDIN_001_test.md").write_text("done", encoding="utf-8")
        (done / "FACEBOOK_002_test.md").write_text("done", encoding="utf-8")

        table = build_multi_platform_social_table(vault)
        # Table should have rows with correct counts
        assert "| FB (Facebook)" in table
        # Total posted should be 3
        assert "**3**" in table

    def test_returns_markdown_table(self, vault):
        table = build_multi_platform_social_table(vault)
        lines = table.strip().split("\n")
        assert len(lines) >= 6  # header + separator + 4 platforms + total
        assert lines[0].startswith("| Platform")
        assert lines[1].startswith("|---")
