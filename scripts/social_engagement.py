"""Social media engagement — check comments & reply across all platforms via Playwright.

Gold Tier: Monitors and replies to comments on Instagram, Facebook, Twitter/X, LinkedIn.
All interactions via Playwright browser automation (no API tokens needed).

Usage:
    python scripts/social_engagement.py --check instagram
    python scripts/social_engagement.py --check facebook
    python scripts/social_engagement.py --check twitter
    python scripts/social_engagement.py --check linkedin
    python scripts/social_engagement.py --check all
    python scripts/social_engagement.py --reply instagram --comment-id 1 --text "Thanks!"
    python scripts/social_engagement.py --tw-setup    # Twitter login
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger

load_dotenv()

# ---------------------------------------------------------------------------
# Session directories
# ---------------------------------------------------------------------------

INSTAGRAM_SESSION_DIR = os.path.expanduser(
    os.getenv("INSTAGRAM_SESSION_DIR", "~/.ai_employee/instagram_session")
)
FACEBOOK_SESSION_DIR = os.path.expanduser(
    os.getenv("FACEBOOK_SESSION_DIR", "~/.ai_employee/facebook_session")
)
TWITTER_SESSION_DIR = os.path.expanduser(
    os.getenv("TWITTER_SESSION_DIR", "~/.ai_employee/twitter_session")
)
LINKEDIN_SESSION_DIR = os.path.expanduser(
    os.getenv("LINKEDIN_SESSION_DIR", "~/.ai_employee/linkedin_session")
)

VAULT_PATH = Path(os.getenv("VAULT_PATH", str(Path(__file__).parent.parent)))


# ---------------------------------------------------------------------------
# Twitter session setup
# ---------------------------------------------------------------------------

def setup_twitter_session(session_dir: str | None = None) -> None:
    """Open a visible browser for manual Twitter/X login, then save session."""
    from playwright.sync_api import sync_playwright

    sdir = session_dir or TWITTER_SESSION_DIR
    Path(sdir).mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=sdir,
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
            no_viewport=True,
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://x.com/login", wait_until="domcontentloaded")
        page.bring_to_front()

        print("\n" + "=" * 50)
        print("  A Chrome browser window should be visible now.")
        print("  Please log in to Twitter/X there.")
        print("=" * 50)
        print("\nWaiting up to 5 minutes for login ...")

        deadline = time.time() + 300
        logged_in = False
        while time.time() < deadline:
            url = page.url
            # Check if we left the login page
            if "login" not in url and "i/flow" not in url:
                # Any x.com page that isn't login means we're in
                if "x.com" in url or "twitter.com" in url:
                    time.sleep(3)
                    logged_in = True
                    break
            time.sleep(3)

        if logged_in:
            print("Login successful!")
        else:
            print("Login timed out.")
            try:
                ctx.close()
            except Exception:
                pass
            return

        print("Saving session (please wait 5 seconds)...")
        time.sleep(5)
        try:
            ctx.close()
        except Exception:
            pass
        print(f"Twitter session saved to {sdir}")


# ---------------------------------------------------------------------------
# Instagram — check comments & reply
# ---------------------------------------------------------------------------

def check_instagram_comments(session_dir: str | None = None) -> dict:
    """Check notifications/comments on Instagram via activity feed."""
    from playwright.sync_api import sync_playwright

    sdir = session_dir or INSTAGRAM_SESSION_DIR
    if not Path(sdir).exists():
        return {"success": False, "error": "No Instagram session. Run --ig-setup first."}

    try:
        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=sdir, headless=False,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 900},
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()

            # Check notifications/activity for comments, likes, follows
            page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
            time.sleep(6)

            # Click Notifications heart icon
            try:
                page.locator('svg[aria-label="Notifications"]').first.click(timeout=5_000)
                time.sleep(4)
            except Exception:
                pass

            # Scrape notification items
            notifications = page.evaluate("""() => {
                const results = [];
                const items = document.querySelectorAll('div, span');
                const seen = new Set();
                for (const el of items) {
                    const text = el.textContent.trim();
                    // Look for notification patterns: "username liked your post", "username commented"
                    if (text && text.length > 10 && text.length < 300) {
                        const patterns = ['liked', 'commented', 'mentioned', 'replied', 'started following'];
                        for (const p of patterns) {
                            if (text.toLowerCase().includes(p) && !seen.has(text)) {
                                seen.add(text);
                                results.push({
                                    text: text,
                                    type: p,
                                    platform: 'instagram'
                                });
                                break;
                            }
                        }
                    }
                }
                return results.slice(0, 20);
            }""")

            # Also check profile posts for comments
            username = os.getenv("INSTAGRAM_USERNAME", "")
            post_comments = []
            if username:
                page.goto(f"https://www.instagram.com/{username}/", wait_until="domcontentloaded")
                time.sleep(8)

                post_links = page.evaluate("""() => {
                    const links = document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]');
                    return Array.from(links).map(a => a.href)
                        .filter((v, i, a) => a.indexOf(v) === i).slice(0, 5);
                }""")

                for post_url in post_links:
                    page.goto(post_url, wait_until="domcontentloaded")
                    time.sleep(5)

                    comments = page.evaluate("""() => {
                        const results = [];
                        const seen = new Set();
                        const spans = document.querySelectorAll('span');
                        for (const el of spans) {
                            const parent = el.closest('li, div');
                            if (!parent) continue;
                            const userLink = parent.querySelector('a[href*="/"]');
                            if (!userLink) continue;
                            const user = userLink.textContent.trim();
                            const text = el.textContent.trim();
                            if (text && user && text !== user && text.length > 1 && text.length < 500) {
                                const key = user + ':' + text;
                                if (!seen.has(key)) {
                                    seen.add(key);
                                    const timeEl = parent.querySelector('time');
                                    results.push({
                                        user: user, text: text,
                                        time: timeEl ? timeEl.getAttribute('datetime') || timeEl.textContent : ''
                                    });
                                }
                            }
                        }
                        return results.slice(0, 20);
                    }""")

                    for c in comments:
                        c["post_url"] = post_url
                        c["platform"] = "instagram"
                        post_comments.append(c)

            ctx.close()
            return {
                "success": True, "platform": "instagram",
                "notifications": notifications,
                "post_comments": post_comments,
                "notification_count": len(notifications),
                "comment_count": len(post_comments),
            }

    except Exception as exc:
        return {"success": False, "error": str(exc)}


def reply_instagram_comment(
    post_url: str, reply_text: str, session_dir: str | None = None
) -> dict:
    """Reply to a comment on an Instagram post."""
    from playwright.sync_api import sync_playwright

    sdir = session_dir or INSTAGRAM_SESSION_DIR
    if not Path(sdir).exists():
        return {"success": False, "error": "No Instagram session."}

    try:
        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=sdir, headless=False,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 900},
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(post_url, wait_until="domcontentloaded")
            time.sleep(6)

            # Type in the comment box
            page.evaluate("""(text) => {
                const textarea = document.querySelector('textarea[aria-label*="comment"], textarea[placeholder*="comment"]');
                if (textarea) {
                    textarea.focus();
                    textarea.value = text;
                    textarea.dispatchEvent(new Event('input', {bubbles: true}));
                    textarea.dispatchEvent(new Event('change', {bubbles: true}));
                }
            }""", reply_text)
            time.sleep(1)

            # Also type via keyboard for React state
            comment_box = page.locator(
                'textarea[aria-label*="comment"], textarea[placeholder*="comment"]'
            ).first
            comment_box.click(timeout=5_000)
            comment_box.fill("")
            page.keyboard.type(reply_text, delay=15)
            time.sleep(2)

            # Click Post
            page.evaluate("""() => {
                const els = document.querySelectorAll('div[role="button"], button');
                for (const el of els) {
                    if (el.textContent.trim() === 'Post' && el.offsetParent !== null) {
                        const rect = el.getBoundingClientRect();
                        if (rect.x > 700) { el.click(); return; }
                    }
                }
            }""")
            time.sleep(5)

            ctx.close()
            return {"success": True, "platform": "instagram", "reply": reply_text,
                    "post_url": post_url}

    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Facebook — check comments & reply
# ---------------------------------------------------------------------------

def check_facebook_comments(session_dir: str | None = None) -> dict:
    """Check comments on recent Facebook posts."""
    from playwright.sync_api import sync_playwright

    sdir = session_dir or FACEBOOK_SESSION_DIR
    if not Path(sdir).exists():
        return {"success": False, "error": "No Facebook session. Run --fb-setup first."}

    try:
        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=sdir, headless=False,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 900},
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto("https://www.facebook.com/me", wait_until="domcontentloaded")
            time.sleep(8)

            # Scrape comments from visible posts
            comments = page.evaluate("""() => {
                const results = [];
                const commentEls = document.querySelectorAll('[role="article"]');
                for (const el of commentEls) {
                    const nameEl = el.querySelector('a[role="link"] span, strong');
                    const textEl = el.querySelector('div[dir="auto"]');
                    if (nameEl && textEl) {
                        const user = nameEl.textContent.trim();
                        const text = textEl.textContent.trim();
                        if (text && user && text.length < 500) {
                            const timeEl = el.querySelector('abbr, a[href*="comment"] span');
                            results.push({
                                user: user,
                                text: text,
                                time: timeEl ? timeEl.textContent : '',
                                platform: 'facebook'
                            });
                        }
                    }
                }
                return results.slice(0, 20);
            }""")

            ctx.close()
            return {"success": True, "platform": "facebook", "comments": comments,
                    "comment_count": len(comments)}

    except Exception as exc:
        return {"success": False, "error": str(exc)}


def reply_facebook_comment(
    reply_text: str, session_dir: str | None = None
) -> dict:
    """Reply to the most recent comment on your latest Facebook post."""
    from playwright.sync_api import sync_playwright

    sdir = session_dir or FACEBOOK_SESSION_DIR
    if not Path(sdir).exists():
        return {"success": False, "error": "No Facebook session."}

    try:
        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=sdir, headless=False,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 900},
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto("https://www.facebook.com/me", wait_until="domcontentloaded")
            time.sleep(8)

            # Find comment box and type
            comment_box = page.locator(
                'div[contenteditable="true"][aria-label*="comment"],'
                'div[contenteditable="true"][aria-label*="Comment"],'
                'div[contenteditable="true"][aria-label*="Reply"]'
            ).first
            comment_box.click(timeout=5_000)
            page.keyboard.type(reply_text, delay=15)
            time.sleep(1)
            page.keyboard.press("Enter")
            time.sleep(5)

            ctx.close()
            return {"success": True, "platform": "facebook", "reply": reply_text}

    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Twitter/X — check comments & reply
# ---------------------------------------------------------------------------

def check_twitter_comments(session_dir: str | None = None) -> dict:
    """Check replies/mentions on Twitter/X."""
    from playwright.sync_api import sync_playwright

    sdir = session_dir or TWITTER_SESSION_DIR
    if not Path(sdir).exists():
        return {"success": False, "error": "No Twitter session. Run --tw-setup first."}

    try:
        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=sdir, headless=False,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 900},
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto("https://x.com/notifications/mentions", wait_until="domcontentloaded")
            time.sleep(8)

            comments = page.evaluate("""() => {
                const results = [];
                const tweets = document.querySelectorAll('[data-testid="tweet"]');
                for (const t of tweets) {
                    const userEl = t.querySelector('[data-testid="User-Name"] a');
                    const textEl = t.querySelector('[data-testid="tweetText"]');
                    const timeEl = t.querySelector('time');
                    if (userEl && textEl) {
                        results.push({
                            user: userEl.textContent.trim(),
                            text: textEl.textContent.trim(),
                            time: timeEl ? timeEl.getAttribute('datetime') : '',
                            tweet_url: userEl.closest('article') ?
                                userEl.closest('article').querySelector('a[href*="/status/"]')?.href : '',
                            platform: 'twitter'
                        });
                    }
                }
                return results.slice(0, 20);
            }""")

            ctx.close()
            return {"success": True, "platform": "twitter", "comments": comments,
                    "comment_count": len(comments)}

    except Exception as exc:
        return {"success": False, "error": str(exc)}


def reply_twitter_comment(
    tweet_url: str, reply_text: str, session_dir: str | None = None
) -> dict:
    """Reply to a tweet on Twitter/X."""
    from playwright.sync_api import sync_playwright

    sdir = session_dir or TWITTER_SESSION_DIR
    if not Path(sdir).exists():
        return {"success": False, "error": "No Twitter session."}

    try:
        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=sdir, headless=False,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 900},
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(tweet_url, wait_until="domcontentloaded")
            time.sleep(6)

            # Click reply box
            reply_box = page.locator(
                '[data-testid="tweetTextarea_0"],'
                'div[role="textbox"][data-testid]'
            ).first
            reply_box.click(timeout=5_000)
            page.keyboard.type(reply_text, delay=15)
            time.sleep(2)

            # Click Reply button
            page.locator('[data-testid="tweetButtonInline"]').first.click(timeout=5_000)
            time.sleep(5)

            ctx.close()
            return {"success": True, "platform": "twitter", "reply": reply_text,
                    "tweet_url": tweet_url}

    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# LinkedIn — check comments & reply
# ---------------------------------------------------------------------------

def check_linkedin_comments(session_dir: str | None = None) -> dict:
    """Check comments on recent LinkedIn posts."""
    from playwright.sync_api import sync_playwright

    sdir = session_dir or LINKEDIN_SESSION_DIR
    if not Path(sdir).exists():
        return {"success": False, "error": "No LinkedIn session. Run linkedin_poster.py --setup first."}

    try:
        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=sdir, headless=False,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 900},
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            time.sleep(8)

            # Go to your posts
            page.goto("https://www.linkedin.com/in/me/recent-activity/all/",
                       wait_until="domcontentloaded")
            time.sleep(6)

            comments = page.evaluate("""() => {
                const results = [];
                const commentEls = document.querySelectorAll('.comments-comment-item, .feed-shared-update-v2');
                for (const el of commentEls) {
                    const nameEl = el.querySelector('.comments-post-meta__name-text, .update-components-actor__name span');
                    const textEl = el.querySelector('.comments-comment-item__main-content, .feed-shared-text span[dir="ltr"]');
                    const timeEl = el.querySelector('time, .comments-comment-item__timestamp');
                    if (nameEl && textEl) {
                        results.push({
                            user: nameEl.textContent.trim(),
                            text: textEl.textContent.trim(),
                            time: timeEl ? timeEl.textContent.trim() : '',
                            platform: 'linkedin'
                        });
                    }
                }
                return results.slice(0, 20);
            }""")

            ctx.close()
            return {"success": True, "platform": "linkedin", "comments": comments,
                    "comment_count": len(comments)}

    except Exception as exc:
        return {"success": False, "error": str(exc)}


def reply_linkedin_comment(
    reply_text: str, session_dir: str | None = None
) -> dict:
    """Reply to the most recent comment on your LinkedIn activity."""
    from playwright.sync_api import sync_playwright

    sdir = session_dir or LINKEDIN_SESSION_DIR
    if not Path(sdir).exists():
        return {"success": False, "error": "No LinkedIn session."}

    try:
        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=sdir, headless=False,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 900},
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto("https://www.linkedin.com/in/me/recent-activity/all/",
                       wait_until="domcontentloaded")
            time.sleep(8)

            # Find and click Reply on the first comment
            reply_btns = page.locator('button:has-text("Reply"), span:has-text("Reply")')
            if reply_btns.count() > 0:
                reply_btns.first.click(timeout=5_000)
                time.sleep(2)

            # Type in comment box
            comment_box = page.locator(
                'div.ql-editor[contenteditable="true"],'
                'div[role="textbox"]'
            ).last
            comment_box.click(timeout=5_000)
            page.keyboard.type(reply_text, delay=15)
            time.sleep(2)

            # Submit
            page.locator('button.comments-comment-box__submit-button,'
                         'button:has-text("Post")').last.click(timeout=5_000)
            time.sleep(5)

            ctx.close()
            return {"success": True, "platform": "linkedin", "reply": reply_text}

    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Unified check & reply
# ---------------------------------------------------------------------------

def check_all_comments() -> dict:
    """Check comments across all platforms."""
    results = {}
    for platform, func in [
        ("instagram", check_instagram_comments),
        ("facebook", check_facebook_comments),
        ("twitter", check_twitter_comments),
        ("linkedin", check_linkedin_comments),
    ]:
        try:
            results[platform] = func()
        except Exception as e:
            results[platform] = {"success": False, "error": str(e)}
    return results


def reply_to_comment(
    platform: str, reply_text: str,
    post_url: str | None = None, tweet_url: str | None = None,
) -> dict:
    """Reply to a comment on any platform."""
    if platform == "instagram":
        if not post_url:
            return {"success": False, "error": "post_url required for Instagram"}
        return reply_instagram_comment(post_url, reply_text)
    elif platform == "facebook":
        return reply_facebook_comment(reply_text)
    elif platform == "twitter":
        if not tweet_url:
            return {"success": False, "error": "tweet_url required for Twitter"}
        return reply_twitter_comment(tweet_url, reply_text)
    elif platform == "linkedin":
        return reply_linkedin_comment(reply_text)
    else:
        return {"success": False, "error": f"Unknown platform: {platform}"}


# ---------------------------------------------------------------------------
# Twitter Playwright post
# ---------------------------------------------------------------------------

def post_to_twitter_playwright(
    content: str, session_dir: str | None = None
) -> dict:
    """Post a tweet via Playwright."""
    from playwright.sync_api import sync_playwright

    sdir = session_dir or TWITTER_SESSION_DIR
    if not Path(sdir).exists():
        return {"success": False, "error": "No Twitter session. Run --tw-setup first."}

    try:
        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=sdir, headless=False,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 900},
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto("https://x.com/compose/post", wait_until="domcontentloaded")
            time.sleep(5)

            # Type tweet
            tweet_box = page.locator(
                '[data-testid="tweetTextarea_0"],'
                'div[role="textbox"]'
            ).first
            tweet_box.click(timeout=5_000)
            page.keyboard.type(content, delay=15)
            time.sleep(2)

            # Click Post
            page.locator('[data-testid="tweetButton"]').first.click(timeout=5_000)
            time.sleep(5)

            ctx.close()
            return {"success": True, "platform": "twitter", "mode": "playwright",
                    "post_id": f"PW-TW-{int(time.time())}"}

    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Social engagement — comments & replies (all platforms)")
    parser.add_argument("--check", choices=["instagram", "facebook", "twitter", "linkedin", "all"],
                        help="Check comments on a platform")
    parser.add_argument("--reply", choices=["instagram", "facebook", "twitter", "linkedin"],
                        help="Reply to a comment")
    parser.add_argument("--text", help="Reply text")
    parser.add_argument("--post-url", help="Post URL (Instagram/Twitter)")
    parser.add_argument("--tw-setup", action="store_true", help="Setup Twitter session")
    parser.add_argument("--tw-post", metavar="TEXT", help="Post a tweet")
    args = parser.parse_args()

    if args.tw_setup:
        setup_twitter_session()
        return

    if args.tw_post:
        result = post_to_twitter_playwright(args.tw_post)
        print(json.dumps(result, indent=2))
        return

    if args.check:
        if args.check == "all":
            results = check_all_comments()
        else:
            funcs = {
                "instagram": check_instagram_comments,
                "facebook": check_facebook_comments,
                "twitter": check_twitter_comments,
                "linkedin": check_linkedin_comments,
            }
            results = funcs[args.check]()
        print(json.dumps(results, indent=2))
        return

    if args.reply:
        if not args.text:
            print("Error: --text required for replies")
            return
        result = reply_to_comment(
            args.reply, args.text,
            post_url=args.post_url, tweet_url=args.post_url,
        )
        print(json.dumps(result, indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
