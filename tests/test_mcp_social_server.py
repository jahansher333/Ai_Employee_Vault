"""Tests for mcp_social_server.py — Social MCP tool functions."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from mcp_social_server import (
    draft_social_post,
    list_social_drafts,
    publish_approved_posts,
    get_social_activity_summary,
)


class TestDraftSocialPost:
    @patch("mcp_social_server.VAULT_PATH")
    def test_facebook_draft(self, mock_vault, vault):
        mock_vault.__class__ = type(vault)
        # Use the actual function with a real vault
        with patch("mcp_social_server.VAULT_PATH", vault):
            result = draft_social_post("AI News", "facebook")
            assert result["success"] is True
            assert result["platform"] == "facebook"
            assert "file" in result

    @patch("mcp_social_server.VAULT_PATH")
    def test_twitter_draft(self, mock_vault, vault):
        with patch("mcp_social_server.VAULT_PATH", vault):
            result = draft_social_post("Update", "twitter")
            assert result["success"] is True
            assert result["char_limit"] == 280

    @patch("mcp_social_server.VAULT_PATH")
    def test_unknown_platform(self, mock_vault, vault):
        with patch("mcp_social_server.VAULT_PATH", vault):
            result = draft_social_post("Test", "tiktok")
            assert result["success"] is False
            assert "Unknown platform" in result["error"]


class TestListSocialDrafts:
    @patch("mcp_social_server.VAULT_PATH")
    def test_empty(self, mock_vault, vault):
        with patch("mcp_social_server.VAULT_PATH", vault):
            result = list_social_drafts()
            assert result["success"] is True
            assert result["count"] == 0

    @patch("mcp_social_server.VAULT_PATH")
    def test_with_drafts(self, mock_vault, vault):
        pa = vault / "Pending_Approval"
        (pa / "FACEBOOK_001_test.md").write_text("test", encoding="utf-8")
        (pa / "TWITTER_001_test.md").write_text("test", encoding="utf-8")
        with patch("mcp_social_server.VAULT_PATH", vault):
            result = list_social_drafts()
            assert result["success"] is True
            assert result["count"] == 2


class TestPublishApprovedPosts:
    @patch("mcp_social_server.VAULT_PATH")
    def test_no_approved(self, mock_vault, vault):
        with patch("mcp_social_server.VAULT_PATH", vault):
            result = publish_approved_posts()
            assert result["success"] is True
            assert result["count"] == 0


class TestGetSocialActivitySummary:
    @patch("mcp_social_server.VAULT_PATH")
    def test_summary(self, mock_vault, vault):
        with patch("mcp_social_server.VAULT_PATH", vault):
            result = get_social_activity_summary()
            assert result["success"] is True
            assert "summary" in result
