"""MCP Server for multi-platform social media — post, check comments, reply.

Gold Tier: Exposes social posting + engagement tools (Facebook, Instagram,
Twitter/X, LinkedIn) as MCP tools callable from Claude Code.
All via Playwright browser automation — no API tokens needed.

Start: python scripts/mcp_social_server.py (stdio transport)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).parent))

mcp = FastMCP("social", instructions="Social media posting & engagement — draft, publish, check comments, reply across Facebook, Instagram, Twitter/X, LinkedIn. All via Playwright.")

VAULT_PATH = Path(os.getenv("VAULT_PATH", str(Path(__file__).parent.parent)))


@mcp.tool()
def draft_social_post(topic: str, platform: str = "facebook", template: str = "service_promotion") -> dict:
    """Generate a social media draft and save to Pending_Approval/.

    Args:
        topic: The topic or subject of the post
        platform: Target platform — 'facebook', 'instagram', 'twitter', or 'linkedin'
        template: Post template style (default: 'service_promotion')
    """
    try:
        if platform == "linkedin":
            from linkedin_poster import generate_linkedin_draft, save_linkedin_draft
            from audit_logger import AuditLogger
            logger = AuditLogger(VAULT_PATH)
            draft = generate_linkedin_draft(topic, template)
            path = save_linkedin_draft(draft, VAULT_PATH, logger)
            return {"success": True, "file": str(path), "platform": "linkedin",
                    "char_count": draft["char_count"]}

        from social_poster import generate_social_draft, save_social_draft, PLATFORMS
        from audit_logger import AuditLogger

        if platform not in PLATFORMS:
            return {"success": False, "error": f"Unknown platform '{platform}'. "
                    "Choose from: facebook, instagram, twitter, linkedin"}

        logger = AuditLogger(VAULT_PATH)
        draft = generate_social_draft(topic, platform, template)
        path = save_social_draft(draft, VAULT_PATH, logger)
        limit = PLATFORMS[platform]["char_limit"]
        return {
            "success": True,
            "file": str(path),
            "platform": platform,
            "char_count": draft["char_count"],
            "char_limit": limit,
            "within_limit": draft.get("within_limit", True),
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def list_social_drafts() -> dict:
    """List all pending social media drafts across all platforms."""
    try:
        from social_poster import get_social_activity_summary
        summary = get_social_activity_summary(VAULT_PATH)
        # Also list actual files
        pa = VAULT_PATH / "Pending_Approval"
        files = []
        if pa.exists():
            for prefix in ["FACEBOOK", "INSTAGRAM", "TWITTER", "LINKEDIN"]:
                for f in pa.glob(f"{prefix}_*.md"):
                    files.append({"file": f.name, "platform": prefix.lower()})
        return {"success": True, "drafts": files, "count": len(files),
                "summary": summary.get("summary", {})}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def publish_approved_posts() -> dict:
    """Publish all approved social posts (moves from Approved/ to Done/)."""
    try:
        from social_poster import scan_approved_social_posts, publish_social_post
        from audit_logger import AuditLogger
        logger = AuditLogger(VAULT_PATH)
        approved = scan_approved_social_posts(VAULT_PATH)
        results = []
        for f in approved:
            status = publish_social_post(f, VAULT_PATH, logger)
            results.append({"file": f.name, "status": status})
        return {"success": True, "published": results, "count": len(results)}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def get_social_activity_summary() -> dict:
    """Get social media activity summary across all platforms."""
    try:
        from social_poster import get_social_activity_summary
        return get_social_activity_summary(VAULT_PATH)
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Engagement tools — check comments & reply (all via Playwright)
# ---------------------------------------------------------------------------


@mcp.tool()
def check_comments(platform: str = "all") -> dict:
    """Check comments/replies on your posts across social platforms.

    Args:
        platform: 'instagram', 'facebook', 'twitter', 'linkedin', or 'all'
    """
    try:
        from social_engagement import (
            check_instagram_comments,
            check_facebook_comments,
            check_twitter_comments,
            check_linkedin_comments,
            check_all_comments,
        )
        if platform == "all":
            return check_all_comments()
        funcs = {
            "instagram": check_instagram_comments,
            "facebook": check_facebook_comments,
            "twitter": check_twitter_comments,
            "linkedin": check_linkedin_comments,
        }
        if platform not in funcs:
            return {"success": False, "error": f"Unknown platform '{platform}'"}
        return funcs[platform]()
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def reply_to_comment(
    platform: str, reply_text: str,
    post_url: str = "",
) -> dict:
    """Reply to a comment on a social media post via Playwright.

    Args:
        platform: 'instagram', 'facebook', 'twitter', or 'linkedin'
        reply_text: The reply message to post
        post_url: URL of the post (required for instagram and twitter)
    """
    try:
        from social_engagement import reply_to_comment as _reply
        return _reply(
            platform, reply_text,
            post_url=post_url or None,
            tweet_url=post_url or None,
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def post_to_instagram(content: str) -> dict:
    """Post to Instagram with auto-generated quote-card image via Playwright.

    Args:
        content: The post text/caption. An image is auto-generated from the text.
    """
    try:
        from social_poster import post_to_instagram_playwright
        return post_to_instagram_playwright(content)
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def post_to_facebook(content: str) -> dict:
    """Post to Facebook via Playwright browser automation.

    Args:
        content: The post text.
    """
    try:
        from social_poster import post_to_facebook_playwright
        return post_to_facebook_playwright(content)
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def post_to_twitter(content: str) -> dict:
    """Post a tweet to Twitter/X via Playwright browser automation.

    Args:
        content: The tweet text (max 280 chars).
    """
    try:
        from social_engagement import post_to_twitter_playwright
        return post_to_twitter_playwright(content)
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
def post_to_linkedin(content: str) -> dict:
    """Post to LinkedIn via Playwright browser automation.

    Args:
        content: The post text.
    """
    try:
        from linkedin_poster import post_to_linkedin_playwright
        return post_to_linkedin_playwright(content)
    except Exception as exc:
        return {"success": False, "error": str(exc)}


if __name__ == "__main__":
    mcp.run()
