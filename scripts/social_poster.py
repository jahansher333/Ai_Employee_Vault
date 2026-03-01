"""Multi-platform social media poster — Facebook, Instagram, Twitter/X.

Gold Tier: Generates platform-appropriate drafts, saves to Pending_Approval/
with platform-specific prefixes, publishes approved posts (simulation default).
Supports Playwright browser automation for Facebook & Instagram posting.

Usage:
    python scripts/social_poster.py --draft "AI Update" --platform facebook
    python scripts/social_poster.py --draft "New Feature" --platform twitter
    python scripts/social_poster.py --draft "Business Tips" --platform instagram
    python scripts/social_poster.py --publish           # Process all approved posts
    python scripts/social_poster.py --summary           # Social activity summary
    python scripts/social_poster.py --dashboard         # Update Dashboard social section
    python scripts/social_poster.py --fb-setup          # Browser login for Facebook Playwright
    python scripts/social_poster.py --ig-setup          # Browser login for Instagram Playwright
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from textwrap import wrap

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger

load_dotenv()

# ---------------------------------------------------------------------------
# Playwright session directories & URLs
# ---------------------------------------------------------------------------

FACEBOOK_SESSION_DIR = os.path.expanduser(
    os.getenv("FACEBOOK_SESSION_DIR", "~/.ai_employee/facebook_session")
)
INSTAGRAM_SESSION_DIR = os.path.expanduser(
    os.getenv("INSTAGRAM_SESSION_DIR", "~/.ai_employee/instagram_session")
)

FACEBOOK_URL = "https://www.facebook.com/"
INSTAGRAM_URL = "https://www.instagram.com/"

# ---------------------------------------------------------------------------
# Facebook Playwright selectors
# ---------------------------------------------------------------------------

FACEBOOK_START_POST_SELECTORS = [
    '[aria-label="What\'s on your mind?"]',
    'div[role="button"]:has-text("What\'s on your mind")',
    'span:has-text("What\'s on your mind")',
    '[aria-label="Create a post"]',
]

FACEBOOK_EDITOR_SELECTORS = [
    'div[contenteditable="true"][role="textbox"]',
    'div[contenteditable="true"][aria-label="What\'s on your mind?"]',
    'div[contenteditable="true"][data-lexical-editor="true"]',
    'div.notranslate[contenteditable="true"]',
]

FACEBOOK_POST_BUTTON_SELECTORS = [
    '[aria-label="Post"]',
    'div[role="button"]:has-text("Post")',
    'span:has-text("Post")',
]

# ---------------------------------------------------------------------------
# Instagram Playwright selectors
# ---------------------------------------------------------------------------

INSTAGRAM_CREATE_SELECTORS = [
    '[aria-label="New post"]',
    'svg[aria-label="New post"]',
    '[aria-label="Create"]',
    'a[href="/create/style/"]',
    'svg[aria-label="New Photo or Video"]',
]

INSTAGRAM_CAPTION_SELECTORS = [
    'div[aria-label="Write a caption..."]',
    'textarea[aria-label="Write a caption..."]',
    'div[contenteditable="true"][role="textbox"]',
    'textarea[placeholder="Write a caption..."]',
]

INSTAGRAM_SHARE_SELECTORS = [
    'button:has-text("Share")',
    '[role="button"]:has-text("Share")',
    'div[role="button"]:has-text("Share")',
]

# Default placeholder image for Instagram (text-only posts need an image)
INSTAGRAM_PLACEHOLDER_IMAGE = os.getenv(
    "INSTAGRAM_PLACEHOLDER_IMAGE",
    str(Path(__file__).parent / "assets" / "ig_placeholder.png"),
)

# ---------------------------------------------------------------------------
# Instagram image generation from text
# ---------------------------------------------------------------------------


def generate_instagram_image(
    text: str,
    output_path: str | Path | None = None,
    size: tuple[int, int] = (1080, 1080),
    bg_color: str = "#1a1a2e",
    text_color: str = "#ffffff",
    accent_color: str = "#e94560",
) -> Path:
    """Generate a branded quote-card image for Instagram from text content.

    Creates a 1080x1080 image with the post text rendered as a quote card,
    suitable for Instagram posting since IG requires an image.

    Returns the path to the generated PNG file.
    """
    from PIL import Image, ImageDraw, ImageFont

    width, height = size
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Try to load a nice font, fall back to default
    font_size = 42
    small_font_size = 24
    title_font_size = 56
    font = ImageFont.load_default(size=font_size)
    small_font = ImageFont.load_default(size=small_font_size)
    title_font = ImageFont.load_default(size=title_font_size)

    # Draw accent bar at top
    draw.rectangle([(0, 0), (width, 8)], fill=accent_color)

    # Draw accent bar at bottom
    draw.rectangle([(0, height - 8), (width, height)], fill=accent_color)

    # Draw decorative quote mark
    quote_font = ImageFont.load_default(size=120)
    draw.text((60, 80), "\u201c", fill=accent_color, font=quote_font)

    # Wrap and draw main text
    max_chars = 38
    lines = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if paragraph:
            lines.extend(wrap(paragraph, width=max_chars))
        else:
            lines.append("")

    # Limit to ~12 lines to fit the image
    if len(lines) > 12:
        lines = lines[:11] + ["..."]

    y_start = 220
    line_height = 60
    for i, line in enumerate(lines):
        y = y_start + i * line_height
        if y > height - 180:
            break
        draw.text((80, y), line, fill=text_color, font=font)

    # Draw branding footer
    footer_y = height - 120
    draw.line([(80, footer_y), (width - 80, footer_y)], fill=accent_color, width=2)
    draw.text((80, footer_y + 20), "AI Employee", fill=accent_color, font=small_font)
    draw.text(
        (80, footer_y + 50),
        "Powered by Automation",
        fill="#888888",
        font=ImageFont.load_default(size=18),
    )

    # Determine output path
    if output_path is None:
        assets_dir = Path(__file__).parent / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        output_path = assets_dir / "ig_placeholder.png"
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG")
    return output_path


# ---------------------------------------------------------------------------
# Platform configuration
# ---------------------------------------------------------------------------

PLATFORMS = {
    "facebook": {
        "prefix": "FACEBOOK",
        "char_limit": None,  # No strict limit, optimize ~500
        "optimal_length": 500,
        "hashtag_style": "inline",  # Hashtags mixed in text
    },
    "instagram": {
        "prefix": "INSTAGRAM",
        "char_limit": 2200,
        "optimal_length": 300,
        "hashtag_style": "block",  # Hashtags at end in a block
    },
    "twitter": {
        "prefix": "TWITTER",
        "char_limit": 280,
        "optimal_length": 250,
        "hashtag_style": "minimal",  # 2-3 hashtags max
    },
}


# ---------------------------------------------------------------------------
# Draft generation
# ---------------------------------------------------------------------------

def _generate_hashtags(topic: str, defaults: list[str], limit: int = 5) -> list[str]:
    """Generate hashtags from topic + defaults."""
    words = re.sub(r"[^a-zA-Z0-9\s]", "", topic).split()
    topic_tag = "".join(w.capitalize() for w in words[:3])
    tags = ([topic_tag] if topic_tag else []) + defaults
    return tags[:limit]


def _sanitize_topic(topic: str, max_len: int = 50) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", topic).strip("-")
    return slug[:max_len]


def generate_facebook_draft(topic: str, template: str = "service_promotion") -> dict:
    """Generate a Facebook post draft optimized for engagement."""
    body = (
        f"Exciting update on {topic}!\n\n"
        f"We've been working hard to bring you better solutions. "
        f"Here's what's new:\n\n"
        f"- Smarter automation that saves you hours every week\n"
        f"- Better insights powered by real business data\n"
        f"- Seamless integration across all your tools\n\n"
        f"The best part? Everything stays under your control with "
        f"human-in-the-loop approval for every action.\n\n"
        f"What feature would help your business the most? "
        f"Drop a comment below!\n"
    )
    hashtags = _generate_hashtags(topic, [
        "BusinessAutomation", "AIForBusiness", "Productivity", "Innovation",
    ])

    return {
        "platform": "facebook",
        "topic": topic,
        "template": template,
        "body": body,
        "hashtags": hashtags,
        "char_count": len(body),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_instagram_draft(topic: str, template: str = "service_promotion") -> dict:
    """Generate an Instagram caption-focused draft with hashtag block."""
    caption = (
        f"Transforming the way businesses handle {topic.lower()} "
        f"with AI-powered automation.\n\n"
        f"No more drowning in manual tasks. No more missed deadlines.\n\n"
        f"Just smart, efficient workflows that keep you in control.\n\n"
        f"Swipe to learn more about how AI can work FOR you, "
        f"not replace you.\n"
    )
    hashtags = _generate_hashtags(topic, [
        "AIAutomation", "BusinessGrowth", "TechForBusiness",
        "Productivity", "SmartBusiness", "FutureOfWork",
        "Innovation", "Entrepreneurship",
    ], limit=10)

    return {
        "platform": "instagram",
        "topic": topic,
        "template": template,
        "body": caption,
        "hashtags": hashtags,
        "char_count": len(caption),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_twitter_draft(topic: str, template: str = "service_promotion") -> dict:
    """Generate a Twitter/X draft within 280 characters."""
    hashtags = _generate_hashtags(topic, ["AI", "Automation"], limit=2)
    hashtag_str = " ".join(f"#{t}" for t in hashtags)

    # Build tweet within limit
    base = (
        f"Automating {topic.lower()} with AI that keeps you in control. "
        f"Every action requires your approval — no surprises.\n\n"
    )

    # Check limit with hashtags
    full_tweet = base + hashtag_str
    if len(full_tweet) > 280:
        # Truncate base to fit
        max_base = 280 - len(hashtag_str) - 5  # 5 for ellipsis + space
        base = base[:max_base].rstrip() + "... "
        full_tweet = base + hashtag_str

    return {
        "platform": "twitter",
        "topic": topic,
        "template": template,
        "body": base.rstrip(),
        "hashtags": hashtags,
        "char_count": len(full_tweet),
        "within_limit": len(full_tweet) <= 280,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_social_draft(
    topic: str,
    platform: str,
    template: str = "service_promotion",
) -> dict:
    """Generate a draft for any supported platform."""
    generators = {
        "facebook": generate_facebook_draft,
        "instagram": generate_instagram_draft,
        "twitter": generate_twitter_draft,
    }
    if platform not in generators:
        raise ValueError(f"Unknown platform '{platform}'. Choose from: {', '.join(generators)}")
    return generators[platform](topic, template)


# ---------------------------------------------------------------------------
# Save draft to Pending_Approval/
# ---------------------------------------------------------------------------

def save_social_draft(
    draft: dict,
    vault_path: Path,
    logger: AuditLogger | None = None,
) -> Path:
    """Save a social media draft as a Markdown file in Pending_Approval/."""
    approval = vault_path / "Pending_Approval"
    approval.mkdir(parents=True, exist_ok=True)

    platform_cfg = PLATFORMS[draft["platform"]]
    prefix = platform_cfg["prefix"]
    ts = datetime.now(timezone.utc).strftime("%H%M%S")
    safe_topic = _sanitize_topic(draft["topic"])
    filename = f"{prefix}_{ts}_{safe_topic}.md"
    dest = approval / filename

    if dest.exists():
        filename = f"{prefix}_{ts}_{safe_topic}-{int(time.time()) % 10000}.md"
        dest = approval / filename

    hashtags_yaml = ", ".join(f'"{t}"' for t in draft["hashtags"])
    hashtag_str = " ".join(f"#{t}" for t in draft["hashtags"])

    char_limit_info = ""
    limit = platform_cfg["char_limit"]
    if limit:
        char_limit_info = f'char_limit: {limit}\nwithin_limit: {draft.get("within_limit", draft["char_count"] <= limit)}\n'

    content = (
        f'---\n'
        f'type: social_post\n'
        f'platform: {draft["platform"]}\n'
        f'topic: "{draft["topic"]}"\n'
        f'template: {draft["template"]}\n'
        f'status: draft\n'
        f'char_count: {draft["char_count"]}\n'
        f'{char_limit_info}'
        f'generated_at: "{draft["generated_at"]}"\n'
        f'hashtags: [{hashtags_yaml}]\n'
        f'---\n\n'
        f'# {draft["platform"].title()} Post Draft: {draft["topic"]}\n\n'
        f'## Post Content\n\n'
        f'{draft["body"]}\n'
        f'{hashtag_str}\n'
    )

    dest.write_text(content, encoding="utf-8")

    if logger:
        logger.log(
            f"{draft['platform']}_draft_created", filename, "success",
            details={"topic": draft["topic"], "platform": draft["platform"],
                     "char_count": draft["char_count"]},
        )
    return dest


# ---------------------------------------------------------------------------
# Publish approved posts
# ---------------------------------------------------------------------------

def _parse_frontmatter(content: str) -> tuple[dict, str]:
    if not content.startswith("---"):
        return {}, content
    end = content.find("---", 3)
    if end == -1:
        return {}, content
    fm_text = content[3:end].strip()
    body = content[end + 3:].strip()
    fm: dict = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm, body


def _serialize_fm(fm: dict, body: str) -> str:
    lines = ["---"]
    for k, v in fm.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    lines.append(body)
    return "\n".join(lines)


def _extract_post_content(body: str) -> str:
    match = re.search(r"## Post Content\s*\n(.*?)(?=\n## |\Z)", body, re.DOTALL)
    return match.group(1).strip() if match else body


def simulate_social_post(content: str, platform: str, title: str,
                         logger: AuditLogger | None = None) -> dict:
    """Simulate posting and return result."""
    sim_id = f"SIM-{platform.upper()}-{int(time.time())}"
    print(f"  [SIMULATE] {platform.title()} post '{title}' -> {sim_id}")
    if logger:
        logger.log(f"{platform}_post_simulated", title, "success",
                   details={"platform": platform, "sim_id": sim_id})
    return {"success": True, "post_id": sim_id, "mode": "simulate"}


def _post_to_facebook_api(content: str) -> dict:
    """Post to Facebook via Graph API (requires FACEBOOK_PAGE_ACCESS_TOKEN)."""
    page_id = os.getenv("FACEBOOK_PAGE_ID", "")
    token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")
    if not page_id or not token:
        return {"success": False, "error": "Facebook credentials not configured"}
    try:
        import requests
        resp = requests.post(
            f"https://graph.facebook.com/v18.0/{page_id}/feed",
            data={"message": content, "access_token": token},
            timeout=30,
        )
        if resp.status_code in (200, 201):
            return {"success": True, "post_id": resp.json().get("id", ""), "mode": "api"}
        return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}", "mode": "api"}
    except Exception as exc:
        return {"success": False, "error": str(exc), "mode": "api"}


def _post_to_twitter_api(content: str) -> dict:
    """Post a tweet via Twitter API v2."""
    bearer = os.getenv("TWITTER_BEARER_TOKEN", "")
    if not bearer:
        return {"success": False, "error": "Twitter credentials not configured"}
    try:
        import requests
        resp = requests.post(
            "https://api.twitter.com/2/tweets",
            json={"text": content},
            headers={"Authorization": f"Bearer {bearer}",
                     "Content-Type": "application/json"},
            timeout=30,
        )
        if resp.status_code in (200, 201):
            data = resp.json().get("data", {})
            return {"success": True, "post_id": data.get("id", ""), "mode": "api"}
        return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}", "mode": "api"}
    except Exception as exc:
        return {"success": False, "error": str(exc), "mode": "api"}


def _post_to_instagram_api(content: str) -> dict:
    """Post to Instagram via Graph API (requires image URL)."""
    user_id = os.getenv("INSTAGRAM_USER_ID", "")
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    image_url = os.getenv("INSTAGRAM_DEFAULT_IMAGE_URL", "")
    if not user_id or not token or not image_url:
        return {"success": False, "error": "Instagram credentials or image URL not configured"}
    try:
        import requests
        # Step 1: Create media container
        container = requests.post(
            f"https://graph.facebook.com/v18.0/{user_id}/media",
            data={"image_url": image_url, "caption": content, "access_token": token},
            timeout=30,
        )
        if container.status_code not in (200, 201):
            return {"success": False, "error": f"Container creation failed: {container.text[:200]}", "mode": "api"}
        container_id = container.json().get("id")
        # Step 2: Publish
        publish = requests.post(
            f"https://graph.facebook.com/v18.0/{user_id}/media_publish",
            data={"creation_id": container_id, "access_token": token},
            timeout=30,
        )
        if publish.status_code in (200, 201):
            return {"success": True, "post_id": publish.json().get("id", ""), "mode": "api"}
        return {"success": False, "error": f"Publish failed: {publish.text[:200]}", "mode": "api"}
    except Exception as exc:
        return {"success": False, "error": str(exc), "mode": "api"}


# ---------------------------------------------------------------------------
# Playwright session helpers
# ---------------------------------------------------------------------------


def _try_selectors(page, selectors, timeout=10_000):
    """Try multiple selectors, return the first one that matches."""
    for sel in selectors:
        try:
            page.wait_for_selector(sel, timeout=timeout)
            return sel
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# Facebook Playwright
# ---------------------------------------------------------------------------


def check_facebook_session(page) -> bool:
    """Return True if Facebook shows the feed (authenticated).

    Uses a combination of URL checks and DOM selectors. The login page
    has 'Facebook' in its title too, so URL-only checks are insufficient.
    """
    time.sleep(3)
    url = page.url
    title = page.title()
    # Definite non-logged-in URLs
    if any(k in url for k in ("login", "checkpoint", "/accounts/", "/recover")):
        return False
    # If URL contains /feed or profile.php, likely authenticated
    if any(k in url for k in ("/feed", "profile.php", "/groups/", "/marketplace")):
        return True
    # Check for authenticated-only DOM elements (broad set)
    auth_selectors = [
        'div[role="feed"]',
        'div[role="navigation"]',
        'input[aria-label="Search Facebook"]',
        '[aria-label="Your profile"]',
        '[aria-label="Messenger"]',
        '[aria-label="Notifications"]',
        '[aria-label="Account"]',
        '[aria-label="Menu"]',
        'div[data-pagelet="Stories"]',
        'div[data-pagelet="RightRail"]',
        # Generic: if there's a compose box, we're logged in
        '[aria-label="Create a post"]',
        '[aria-label="What\'s on your mind"]',
        # Profile picture in nav
        'image[data-visualcompletion]',
        'svg[aria-label="Your profile"]',
    ]
    for sel in auth_selectors:
        try:
            page.wait_for_selector(sel, timeout=3_000)
            return True
        except Exception:
            continue
    # Last resort: if the page title is "Facebook" and we're not on
    # a login URL, check if there's any role="banner" nav element
    if "Facebook" in title and "login" not in url.lower():
        try:
            page.wait_for_selector('[role="banner"]', timeout=5_000)
            return True
        except Exception:
            pass
    return False


def setup_facebook_session(session_dir: str | None = None) -> None:
    """Open a visible browser for manual Facebook login, then save session."""
    from playwright.sync_api import sync_playwright

    sdir = session_dir or FACEBOOK_SESSION_DIR
    Path(sdir).mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=sdir,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(FACEBOOK_URL, wait_until="domcontentloaded")

        if check_facebook_session(page):
            print("Facebook session already valid — no login needed.")
        else:
            print("\n" + "=" * 50)
            print("  A Chrome browser window has opened.")
            print("  Please log in to Facebook there.")
            print("  (This is a SEPARATE browser, not your regular one)")
            print("=" * 50)
            print("\nWaiting up to 5 minutes for login ...")
            deadline = time.time() + 300
            logged_in = False
            while time.time() < deadline:
                if check_facebook_session(page):
                    logged_in = True
                    break
                time.sleep(3)
            if logged_in:
                print("Login successful!")
            else:
                print("Login timed out. Please try again and log in faster.")
                ctx.close()
                return

        print("Saving session (please wait 5 seconds)...")
        time.sleep(5)
        ctx.close()
        print(f"Facebook session saved to {sdir}")


def post_to_facebook_playwright(
    content: str,
    session_dir: str | None = None,
    logger: AuditLogger | None = None,
) -> dict:
    """Publish a text post to Facebook via Playwright browser automation."""
    from playwright.sync_api import sync_playwright

    sdir = session_dir or FACEBOOK_SESSION_DIR

    if not Path(sdir).exists():
        return {
            "success": False, "post_id": None, "mode": "playwright",
            "error": f"Session directory not found: {sdir}. Run --fb-setup first.",
        }

    try:
        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=sdir,
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(FACEBOOK_URL, wait_until="domcontentloaded")
            time.sleep(5)

            if not check_facebook_session(page):
                ctx.close()
                return {
                    "success": False, "post_id": None, "mode": "playwright",
                    "error": "Session expired — run --fb-setup to re-authenticate.",
                }

            # Click "What's on your mind?"
            start_sel = _try_selectors(page, FACEBOOK_START_POST_SELECTORS, timeout=15_000)
            if not start_sel:
                ctx.close()
                return {"success": False, "post_id": None, "mode": "playwright",
                        "error": "Could not find 'What's on your mind?' button"}
            page.locator(start_sel).first.click(force=True, timeout=15_000)
            time.sleep(3)

            # Find editor
            editor_sel = _try_selectors(page, FACEBOOK_EDITOR_SELECTORS, timeout=10_000)
            if not editor_sel:
                ctx.close()
                return {"success": False, "post_id": None, "mode": "playwright",
                        "error": "Could not find post editor"}

            editor = page.locator(editor_sel).first
            editor.click(force=True)
            # Use keyboard typing for better compatibility with Facebook's JS
            editor.press_sequentially(content, delay=10)
            time.sleep(2)

            # Click "Post" — use force=True to bypass overlay elements
            post_btn_sel = _try_selectors(page, FACEBOOK_POST_BUTTON_SELECTORS, timeout=10_000)
            if not post_btn_sel:
                ctx.close()
                return {"success": False, "post_id": None, "mode": "playwright",
                        "error": "Could not find Post button"}
            post_btn = page.locator(post_btn_sel).first
            try:
                post_btn.click(force=True, timeout=10_000)
            except Exception:
                # Fallback: JavaScript click to bypass any overlay
                post_btn.evaluate("el => el.click()")

            # Wait for composer to close
            try:
                page.wait_for_selector(editor_sel, state="hidden", timeout=15_000)
            except Exception:
                pass

            post_url = page.url
            time.sleep(3)
            ctx.close()

            post_id = f"PW-FB-{int(time.time())}"
            if logger:
                logger.log("facebook_playwright_posted", "system", "success",
                           details={"post_id": post_id, "url": post_url})

            return {"success": True, "post_id": post_id, "mode": "playwright", "url": post_url}

    except Exception as exc:
        return {"success": False, "post_id": None, "mode": "playwright", "error": str(exc)}


# ---------------------------------------------------------------------------
# Instagram Playwright
# ---------------------------------------------------------------------------


def check_instagram_session(page) -> bool:
    """Return True if Instagram shows the feed (authenticated).

    Uses URL checks and broad DOM selector matching.
    """
    time.sleep(3)
    url = page.url
    title = page.title()
    # Definite non-logged-in URLs
    if any(k in url for k in ("/accounts/login", "/accounts/emailsignup", "challenge")):
        return False
    # If URL shows direct/inbox or explore, we're logged in
    if any(k in url for k in ("/direct/", "/explore/", "/reels/")):
        return True
    # Broad set of authenticated-only selectors
    auth_selectors = [
        '[aria-label="New post"]',
        'svg[aria-label="New post"]',
        '[aria-label="Home"]',
        'svg[aria-label="Home"]',
        '[aria-label="Search"]',
        'svg[aria-label="Search"]',
        'a[href="/direct/inbox/"]',
        '[aria-label="Notifications"]',
        'svg[aria-label="Notifications"]',
        'nav a[href="/"]',
        '[role="navigation"]',
        # Profile link in sidebar
        'a[href*="/direct/"]',
        'span[role="link"]',
    ]
    for sel in auth_selectors:
        try:
            page.wait_for_selector(sel, timeout=3_000)
            return True
        except Exception:
            continue
    # Last resort: if title is "Instagram" and not login URL
    if "Instagram" in title and "login" not in url.lower():
        try:
            page.wait_for_selector('nav', timeout=5_000)
            return True
        except Exception:
            pass
    return False


def setup_instagram_session(session_dir: str | None = None) -> None:
    """Open a visible browser for manual Instagram login, then save session."""
    from playwright.sync_api import sync_playwright

    sdir = session_dir or INSTAGRAM_SESSION_DIR
    Path(sdir).mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=sdir,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(INSTAGRAM_URL, wait_until="domcontentloaded")

        if check_instagram_session(page):
            print("Instagram session already valid — no login needed.")
        else:
            print("\n" + "=" * 50)
            print("  A Chrome browser window has opened.")
            print("  Please log in to Instagram there.")
            print("  (This is a SEPARATE browser, not your regular one)")
            print("=" * 50)
            print("\nWaiting up to 5 minutes for login ...")
            deadline = time.time() + 300
            logged_in = False
            while time.time() < deadline:
                if check_instagram_session(page):
                    logged_in = True
                    break
                time.sleep(3)
            if logged_in:
                print("Login successful!")
            else:
                print("Login timed out. Please try again and log in faster.")
                ctx.close()
                return

        print("Saving session (please wait 5 seconds)...")
        time.sleep(5)
        ctx.close()
        print(f"Instagram session saved to {sdir}")


def post_to_instagram_playwright(
    content: str,
    session_dir: str | None = None,
    logger: AuditLogger | None = None,
) -> dict:
    """Publish a post to Instagram via Playwright browser automation.

    Instagram web requires an image. This function generates a branded
    quote-card image from the post text and uploads it via the
    Create > Post flow.
    """
    from playwright.sync_api import sync_playwright

    sdir = session_dir or INSTAGRAM_SESSION_DIR

    if not Path(sdir).exists():
        return {
            "success": False, "post_id": None, "mode": "playwright",
            "error": f"Session directory not found: {sdir}. Run --ig-setup first.",
        }

    try:
        # Generate branded quote-card image from post text
        img_path = generate_instagram_image(
            content,
            output_path=Path(sdir) / "_post_image.png",
        )

        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=sdir,
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 900},
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(INSTAGRAM_URL, wait_until="domcontentloaded")
            time.sleep(8)

            if not check_instagram_session(page):
                ctx.close()
                return {
                    "success": False, "post_id": None, "mode": "playwright",
                    "error": "Session expired — run --ig-setup to re-authenticate.",
                }

            # Step 1: Click Create (+) SVG in sidebar
            svg = page.locator('svg[aria-label="New post"]').first
            bbox = svg.bounding_box()
            if not bbox:
                ctx.close()
                return {"success": False, "post_id": None, "mode": "playwright",
                        "error": "Could not find New post button"}
            page.mouse.click(bbox["x"] + bbox["width"] / 2,
                             bbox["y"] + bbox["height"] / 2)
            time.sleep(3)

            # Step 2: Click 'Post' from the Create submenu
            post_clicked = False
            for item in page.locator("span").all():
                try:
                    if item.inner_text().strip() == "Post" and item.is_visible():
                        item_box = item.bounding_box()
                        if item_box and item_box["y"] > bbox["y"]:
                            page.mouse.click(
                                item_box["x"] + item_box["width"] / 2,
                                item_box["y"] + item_box["height"] / 2,
                            )
                            post_clicked = True
                            time.sleep(4)
                            break
                except Exception:
                    continue

            if not post_clicked:
                ctx.close()
                return {"success": False, "post_id": None, "mode": "playwright",
                        "error": "Could not find Post submenu item"}

            # Step 3: Upload image via file input
            file_input = page.locator('input[type="file"]')
            if file_input.count() > 0:
                file_input.first.set_input_files(str(img_path))
                time.sleep(5)
            else:
                ctx.close()
                return {"success": False, "post_id": None, "mode": "playwright",
                        "error": "No file input found in create dialog"}

            # Step 4: Click Next twice (crop -> filter)
            for _ in range(2):
                try:
                    page.locator('div[role="button"]:has-text("Next")').first.click(
                        timeout=8_000)
                    time.sleep(3)
                except Exception:
                    pass

            # Step 5: Type caption
            caption_sel = _try_selectors(page, INSTAGRAM_CAPTION_SELECTORS, timeout=10_000)
            if caption_sel:
                cap_el = page.locator(caption_sel).first
                cap_el.click(force=True)
                page.keyboard.type(content, delay=10)
                time.sleep(2)

            # Step 6: Click Share (top-right header link inside dialog)
            time.sleep(1)
            page.evaluate("""() => {
                const dialog = document.querySelector('[role="dialog"]');
                if (!dialog) return;
                const els = dialog.querySelectorAll('div[role="button"], a, span, button');
                for (const el of els) {
                    if (el.textContent.trim() === 'Share' && el.offsetParent !== null) {
                        const rect = el.getBoundingClientRect();
                        if (rect.y < 150) { el.click(); return; }
                    }
                }
            }""")
            time.sleep(12)

            post_url = page.url
            ctx.close()

            post_id = f"PW-IG-{int(time.time())}"
            if logger:
                logger.log("instagram_playwright_posted", "system", "success",
                           details={"post_id": post_id, "url": post_url})

            return {"success": True, "post_id": post_id, "mode": "playwright", "url": post_url}

    except Exception as exc:
        return {"success": False, "post_id": None, "mode": "playwright", "error": str(exc)}


def publish_social_post(
    file_path: Path,
    vault_path: Path,
    logger: AuditLogger | None = None,
) -> str:
    """Publish an approved social post and move to Done/.

    Returns 'posted' | 'simulated' | 'error'.
    """
    content = file_path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(content)
    post_text = _extract_post_content(body)
    platform = fm.get("platform", "unknown")
    title = fm.get("topic", file_path.stem)

    # Determine mode
    mode_env = f"{platform.upper()}_POST_MODE"
    mode = os.getenv(mode_env, "simulate")

    if logger:
        logger.log(f"{platform}_approval_detected", file_path.name, "success")

    # Publish
    if mode == "playwright":
        pw_funcs = {
            "facebook": post_to_facebook_playwright,
            "instagram": post_to_instagram_playwright,
        }
        pw_func = pw_funcs.get(platform)
        if pw_func:
            result = pw_func(post_text, logger=logger)
            if not result["success"]:
                if logger:
                    logger.log(f"{platform}_post_failed", file_path.name, "error",
                               error=result.get("error"))
                print(f"  [WARN] {platform} Playwright failed: {result.get('error')}"
                      " — falling back to simulation")
                result = simulate_social_post(post_text, platform, title, logger)
        else:
            print(f"  [WARN] Playwright mode not supported for {platform} — falling back to simulation")
            result = simulate_social_post(post_text, platform, title, logger)
    elif mode == "api":
        api_funcs = {
            "facebook": _post_to_facebook_api,
            "twitter": _post_to_twitter_api,
            "instagram": _post_to_instagram_api,
        }
        api_func = api_funcs.get(platform)
        if api_func:
            result = api_func(post_text)
            if not result["success"]:
                if logger:
                    logger.log(f"{platform}_post_failed", file_path.name, "error",
                               error=result.get("error"))
                print(f"  [WARN] {platform} API failed: {result.get('error')} — falling back to simulation")
                result = simulate_social_post(post_text, platform, title, logger)
        else:
            result = simulate_social_post(post_text, platform, title, logger)
    else:
        result = simulate_social_post(post_text, platform, title, logger)

    # Update frontmatter & move to Done/
    fm["status"] = "posted"
    fm["posted_at"] = datetime.now(timezone.utc).isoformat()
    fm["post_mode"] = result.get("mode", mode)
    updated = _serialize_fm(fm, body)

    done = vault_path / "Done"
    done.mkdir(parents=True, exist_ok=True)
    dest = done / file_path.name
    if dest.exists():
        dest = done / f"{file_path.stem}-{int(time.time()) % 10000}.md"

    dest.write_text(updated, encoding="utf-8")
    if dest.exists() and dest.stat().st_size > 0:
        file_path.unlink()

    if logger:
        logger.log(f"{platform}_post_published", file_path.name, "success",
                   details={"mode": result.get("mode"), "post_id": result.get("post_id")})

    return "simulated" if result.get("mode") == "simulate" else "posted"


# ---------------------------------------------------------------------------
# Social activity summary
# ---------------------------------------------------------------------------

def get_social_activity_summary(vault_path: Path) -> dict:
    """Count posts per platform across all vault folders."""
    platforms_summary = {}
    for platform, cfg in PLATFORMS.items():
        prefix = cfg["prefix"]
        drafts = len(list((vault_path / "Pending_Approval").glob(f"{prefix}_*.md"))) if (vault_path / "Pending_Approval").exists() else 0
        approved = len(list((vault_path / "Approved").glob(f"{prefix}_*.md"))) if (vault_path / "Approved").exists() else 0
        posted = len(list((vault_path / "Done").glob(f"{prefix}_*.md"))) if (vault_path / "Done").exists() else 0
        platforms_summary[platform] = {"drafts": drafts, "approved": approved, "posted": posted}

    # Also count LinkedIn
    li_drafts = len(list((vault_path / "Pending_Approval").glob("LINKEDIN_*.md"))) if (vault_path / "Pending_Approval").exists() else 0
    li_approved = len(list((vault_path / "Approved").glob("LINKEDIN_*.md"))) if (vault_path / "Approved").exists() else 0
    li_posted = len(list((vault_path / "Done").glob("LINKEDIN_*.md"))) if (vault_path / "Done").exists() else 0
    platforms_summary["linkedin"] = {"drafts": li_drafts, "approved": li_approved, "posted": li_posted}

    total_posted = sum(p["posted"] for p in platforms_summary.values())
    total_pending = sum(p["drafts"] + p["approved"] for p in platforms_summary.values())

    return {
        "summary": platforms_summary,
        "total_posted": total_posted,
        "total_pending": total_pending,
        "success": True,
    }


def scan_approved_social_posts(vault_path: Path) -> list[Path]:
    """Return all approved social posts across all platforms."""
    approved = vault_path / "Approved"
    if not approved.exists():
        return []
    posts = []
    for prefix in ["FACEBOOK", "INSTAGRAM", "TWITTER"]:
        posts.extend(approved.glob(f"{prefix}_*.md"))
    return sorted(posts)


# ---------------------------------------------------------------------------
# Dashboard: Multi-platform social table
# ---------------------------------------------------------------------------

def build_multi_platform_social_table(vault_path: Path) -> str:
    """Build a markdown table of social media activity for the Dashboard.

    Returns a markdown string with platform rows showing drafts, approved,
    posted counts and totals.
    """
    summary = get_social_activity_summary(vault_path)
    platforms = summary.get("summary", {})

    lines = [
        "| Platform | Drafts | Approved | Posted | Total |",
        "|----------|--------|----------|--------|-------|",
    ]

    grand_total = 0
    for platform in ["facebook", "instagram", "twitter", "linkedin"]:
        data = platforms.get(platform, {"drafts": 0, "approved": 0, "posted": 0})
        total = data["drafts"] + data["approved"] + data["posted"]
        grand_total += total
        icon = {"facebook": "FB", "instagram": "IG", "twitter": "X", "linkedin": "LI"}.get(platform, platform)
        lines.append(
            f"| {icon} ({platform.title()}) | {data['drafts']} | {data['approved']} | {data['posted']} | {total} |"
        )

    lines.append(f"| **Total** | | | **{summary.get('total_posted', 0)}** | **{grand_total}** |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-platform social poster (Gold Tier)")
    parser.add_argument("--vault-path", default=None)
    parser.add_argument("--draft", metavar="TOPIC", help="Generate a draft")
    parser.add_argument("--platform", choices=list(PLATFORMS), default="facebook",
                        help="Target platform")
    parser.add_argument("--template", default="service_promotion")
    parser.add_argument("--publish", action="store_true", help="Publish all approved posts")
    parser.add_argument("--summary", action="store_true", help="Social activity summary")
    parser.add_argument("--dashboard", action="store_true", help="Update Dashboard social section")
    parser.add_argument("--fb-setup", action="store_true",
                        help="Open browser for Facebook login (Playwright mode)")
    parser.add_argument("--ig-setup", action="store_true",
                        help="Open browser for Instagram login (Playwright mode)")
    parser.add_argument("--generate-image", metavar="TEXT",
                        help="Generate an Instagram quote-card image from text")
    args = parser.parse_args()

    vault = Path(args.vault_path or os.getenv("VAULT_PATH",
                 str(Path(__file__).parent.parent)))
    logger = AuditLogger(vault)

    if args.fb_setup:
        setup_facebook_session()
        return

    if args.ig_setup:
        setup_instagram_session()
        return

    if args.generate_image:
        img_path = generate_instagram_image(args.generate_image)
        print(f"Image generated: {img_path}")
        return

    if args.draft:
        draft = generate_social_draft(args.draft, args.platform, args.template)
        path = save_social_draft(draft, vault, logger)
        limit = PLATFORMS[args.platform]["char_limit"]
        limit_info = f" ({draft['char_count']}/{limit} chars)" if limit else ""
        print(f"Draft saved: {path}{limit_info}")
        return

    if args.publish:
        approved = scan_approved_social_posts(vault)
        if not approved:
            print("No approved social posts found.")
            return
        for f in approved:
            status = publish_social_post(f, vault, logger)
            print(f"  [{status.upper()}] {f.name}")
        return

    if args.summary:
        summary = get_social_activity_summary(vault)
        for platform, counts in summary["summary"].items():
            print(f"  {platform.title():12s} | drafts: {counts['drafts']} | "
                  f"approved: {counts['approved']} | posted: {counts['posted']}")
        print(f"\n  Total posted: {summary['total_posted']} | Pending: {summary['total_pending']}")
        return

    if args.dashboard:
        table = build_multi_platform_social_table(vault)
        print(table)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
