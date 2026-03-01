"""LinkedIn post drafting, approval watching, and publishing.

Generates LinkedIn post drafts from templates, saves them to
Pending_Approval/ for human review, monitors Approved/ for approved
posts, publishes (simulated, via LinkedIn API, or via Playwright
browser automation), and moves to Done/.

Usage:
    python scripts/linkedin_poster.py --draft "AI Automation"
    python scripts/linkedin_poster.py --draft "Case Study" --template case_study
    python scripts/linkedin_poster.py --publish           # process approved
    python scripts/linkedin_poster.py --watch             # continuous watch
    python scripts/linkedin_poster.py --dashboard         # update Dashboard
    python scripts/linkedin_poster.py --li-setup          # browser login for Playwright mode
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from audit_logger import AuditLogger

load_dotenv()

# ---------------------------------------------------------------------------
# Playwright session & selectors
# ---------------------------------------------------------------------------

LINKEDIN_SESSION_DIR = os.path.expanduser(
    os.getenv("LINKEDIN_SESSION_DIR", "~/.ai_employee/linkedin_session")
)

LINKEDIN_SELECTORS: dict[str, str] = {
    "feed": "div.scaffold-layout__main",
    "start_post_button": "button.share-box-feed-entry__trigger",
    "post_editor": 'div.ql-editor[contenteditable="true"]',
    "post_button": "button.share-actions__primary-action",
}

# Fallback selectors for different LinkedIn versions
LINKEDIN_START_POST_SELECTORS = [
    '[aria-label="Start a post"]',
    "div[aria-label='Start a post']",
    "button.share-box-feed-entry__trigger",
    "button:has-text('Start a post')",
    "div.share-box-feed-entry__trigger",
]

LINKEDIN_EDITOR_SELECTORS = [
    'div.ql-editor[contenteditable="true"]',
    'div[contenteditable="true"][role="textbox"]',
    'div[data-placeholder="What do you want to talk about?"]',
    'div.editor-content[contenteditable="true"]',
]

LINKEDIN_POST_BUTTON_SELECTORS = [
    "button.share-actions__primary-action",
    "button:has-text('Post')",
    "button[aria-label='Post']",
]

LINKEDIN_URL = "https://www.linkedin.com/feed/"


# ---------------------------------------------------------------------------
# Post templates
# ---------------------------------------------------------------------------

POST_TEMPLATES: dict[str, dict] = {
    "service_promotion": {
        "name": "Service Promotion",
        "tone": "Professional, confident",
        "hashtag_count": 4,
        "generate": lambda topic: (
            f"Are you still spending hours on {topic.lower()}?\n\n"
            f"Most businesses waste countless hours on repetitive tasks "
            f"that could be automated in minutes.\n\n"
            f"Here's what smart automation looks like:\n\n"
            f"- Intelligent email triage that prioritises what matters\n"
            f"- Instant document processing with zero manual data entry\n"
            f"- Smart alerts that notify you only when action is needed\n"
            f"- Full audit trail so nothing falls through the cracks\n\n"
            f"The best part? You stay in control. Every action requires "
            f"your explicit approval before it executes.\n\n"
            f"Ready to reclaim your time? Let's talk about what "
            f"AI-powered automation can do for your business.\n"
        ),
        "hashtags": lambda topic: _generate_hashtags(topic, [
            "AIAutomation", "BusinessEfficiency", "Productivity",
            "DigitalTransformation",
        ]),
    },
    "case_study": {
        "name": "Case Study Highlight",
        "tone": "Evidence-based, credible",
        "hashtag_count": 3,
        "generate": lambda topic: (
            f"We helped a client transform their {topic.lower()} workflow "
            f"— here's what happened.\n\n"
            f"THE PROBLEM:\n"
            f"They were drowning in manual processes. Important messages "
            f"got buried. Deadlines were missed. Team morale was dropping.\n\n"
            f"THE SOLUTION:\n"
            f"We deployed an AI Employee that monitors incoming "
            f"communications, flags urgent items, and drafts responses "
            f"— all with human approval at every step.\n\n"
            f"THE RESULT:\n"
            f"- 60% reduction in response time to urgent requests\n"
            f"- Zero missed deadlines in the first quarter\n"
            f"- Team now focuses on high-value work instead of triage\n\n"
            f"Want similar results for your business?\n"
        ),
        "hashtags": lambda topic: _generate_hashtags(topic, [
            "CaseStudy", "BusinessResults", "AIInAction",
        ]),
    },
    "thought_leadership": {
        "name": "Thought Leadership Tip",
        "tone": "Conversational, authentic",
        "hashtag_count": 3,
        "generate": lambda topic: (
            f"Hot take: most businesses don't need more tools. "
            f"They need fewer tools that actually work together.\n\n"
            f"I've been thinking a lot about {topic.lower()} lately.\n\n"
            f"Here's what I've learned after building AI-powered "
            f"workflows for real businesses:\n\n"
            f"1. Start with the pain, not the tech. Ask \"what's "
            f"costing us time?\" before \"what AI should we use?\"\n\n"
            f"2. Keep humans in the loop. The best AI systems augment "
            f"human judgment — they don't replace it.\n\n"
            f"3. Measure what matters. If your automation doesn't save "
            f"measurable time or money, it's just a demo.\n\n"
            f"What's your take? Are you seeing AI actually deliver ROI, "
            f"or is it still mostly hype in your industry?\n"
        ),
        "hashtags": lambda topic: _generate_hashtags(topic, [
            "ThoughtLeadership", "AIStrategy", "FutureOfWork",
        ]),
    },
}


def _generate_hashtags(topic: str, defaults: list[str]) -> list[str]:
    """Create hashtag list: topic-derived + defaults."""
    # Convert topic words to a camel-case hashtag
    words = re.sub(r"[^a-zA-Z0-9\s]", "", topic).split()
    topic_tag = "".join(w.capitalize() for w in words[:3])
    tags = [topic_tag] + defaults if topic_tag else defaults
    return tags


def _sanitize_topic(topic: str, max_len: int = 50) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", topic).strip("-")
    return slug[:max_len]


# ---------------------------------------------------------------------------
# Draft generation
# ---------------------------------------------------------------------------

def generate_post_draft(topic: str, template: str = "service_promotion") -> dict:
    """Generate a LinkedIn post draft from *topic* and *template*.

    Returns dict with keys: topic, template, body, hashtags, generated_at.
    Raises ``ValueError`` for unknown template names.
    """
    if template not in POST_TEMPLATES:
        valid = ", ".join(POST_TEMPLATES)
        raise ValueError(f"Unknown template '{template}'. Choose from: {valid}")

    tmpl = POST_TEMPLATES[template]
    body = tmpl["generate"](topic)
    hashtags = tmpl["hashtags"](topic)

    return {
        "topic": topic,
        "template": template,
        "body": body,
        "hashtags": hashtags,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def save_draft(draft: dict, vault_path: Path,
               logger: AuditLogger | None = None) -> Path:
    """Save a draft dict as a Markdown file in ``Pending_Approval/``."""
    approval = vault_path / "Pending_Approval"
    approval.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc)
    time_part = ts.strftime("%H%M%S")
    safe_topic = _sanitize_topic(draft["topic"])
    filename = f"LINKEDIN_{time_part}_{safe_topic}.md"
    dest = approval / filename

    if dest.exists():
        filename = f"LINKEDIN_{time_part}_{safe_topic}-{int(time.time()) % 10000}.md"
        dest = approval / filename

    hashtags_yaml = ", ".join(f'"{t}"' for t in draft["hashtags"])
    hashtag_str = " ".join(f"#{t}" for t in draft["hashtags"])

    content = (
        f'---\n'
        f'type: linkedin_post\n'
        f'topic: "{draft["topic"]}"\n'
        f'template: {draft["template"]}\n'
        f'platform: linkedin\n'
        f'status: draft\n'
        f'generated_at: "{draft["generated_at"]}"\n'
        f'hashtags: [{hashtags_yaml}]\n'
        f'---\n\n'
        f'# LinkedIn Post Draft: {draft["topic"]}\n\n'
        f'## Post Content\n\n'
        f'{draft["body"]}\n'
        f'{hashtag_str}\n'
    )

    dest.write_text(content, encoding="utf-8")

    if logger:
        logger.log("linkedin_draft_created", filename, "success",
                    details={"topic": draft["topic"],
                             "template": draft["template"]})
    return dest


# ---------------------------------------------------------------------------
# Approved-post scanning & publishing
# ---------------------------------------------------------------------------

def scan_approved_posts(vault_path: Path) -> list[Path]:
    """Return paths of ``LINKEDIN_*.md`` files in ``Approved/``."""
    approved = vault_path / "Approved"
    if not approved.exists():
        return []
    return sorted(approved.glob("LINKEDIN_*.md"))


def _parse_frontmatter_simple(content: str) -> tuple[dict, str]:
    """Minimal frontmatter parser (same logic as process_inbox)."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("---", 3)
    if end == -1:
        return {}, content
    fm_text = content[3:end].strip()
    body = content[end + 3:].strip()
    fm: dict[str, str] = {}
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
    """Pull the text between ``## Post Content`` and the next heading / EOF."""
    match = re.search(r"## Post Content\s*\n(.*?)(?=\n## |\Z)", body, re.DOTALL)
    return match.group(1).strip() if match else body


def simulate_post(content: str, title: str,
                  logger: AuditLogger | None = None) -> dict:
    """Log a simulated post and return result dict."""
    sim_id = f"SIM-{int(time.time())}"
    print(f"  [SIMULATE] Post '{title}' -> {sim_id}")
    if logger:
        logger.log("linkedin_post_simulated", title, "success",
                    details={"topic": title, "sim_id": sim_id})
    return {"success": True, "post_id": sim_id, "mode": "simulate"}


def post_to_linkedin(content: str, access_token: str,
                     person_urn: str) -> dict:
    """Publish a text post to LinkedIn via the v2 ugcPosts API."""
    import requests

    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    payload = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": content},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC",
        },
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code in (200, 201):
            post_id = resp.json().get("id", "unknown")
            return {"success": True, "post_id": post_id, "mode": "linkedin_api"}
        return {"success": False, "post_id": None, "mode": "linkedin_api",
                "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except Exception as exc:
        return {"success": False, "post_id": None, "mode": "linkedin_api",
                "error": str(exc)}


# ---------------------------------------------------------------------------
# Playwright-based LinkedIn posting
# ---------------------------------------------------------------------------


def check_linkedin_session(page) -> bool:
    """Return ``True`` if LinkedIn shows the feed (authenticated)."""
    import time as _t
    _t.sleep(3)
    url = page.url
    title = page.title()
    # If redirected to login/authwall, not logged in
    if any(k in url for k in ("login", "authwall", "checkpoint/lg")):
        return False
    # If we see "Feed" in title or /feed/ in URL, we're in
    if "feed" in url or "Feed" in title:
        return True
    # Try selectors as fallback
    selectors = [
        LINKEDIN_SELECTORS["feed"],
        "div.feed-shared-update-v2",
        "nav.global-nav",
        "div#global-nav",
        "div.scaffold-layout",
        "input[aria-label='Search']",
    ]
    for sel in selectors:
        try:
            page.wait_for_selector(sel, timeout=3_000)
            return True
        except Exception:
            continue
    return False


def setup_linkedin_session(session_dir: str | None = None) -> None:
    """Open a visible browser for manual LinkedIn login, then save session.

    The user logs in manually; the persistent browser context stores cookies
    so subsequent headless runs are authenticated.
    """
    from playwright.sync_api import sync_playwright

    sdir = session_dir or LINKEDIN_SESSION_DIR
    Path(sdir).mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=sdir,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(LINKEDIN_URL, wait_until="domcontentloaded")

        if check_linkedin_session(page):
            print("LinkedIn session already valid — no login needed.")
        else:
            print("\n" + "=" * 50)
            print("  A Chrome browser window has opened.")
            print("  Please log in to LinkedIn there.")
            print("  (This is a SEPARATE browser, not your regular one)")
            print("=" * 50)
            print("\nWaiting up to 5 minutes for login ...")
            import time as _time
            _deadline = _time.time() + 300
            _logged_in = False
            while _time.time() < _deadline:
                if check_linkedin_session(page):
                    _logged_in = True
                    break
                _time.sleep(3)
            if _logged_in:
                print("Login successful!")
            else:
                print("Login timed out. Please try again and log in faster.")
                ctx.close()
                return

        # Allow session storage and cookies to flush fully
        print("Saving session (please wait 5 seconds)...")
        time.sleep(5)
        ctx.close()
        print(f"LinkedIn session saved to {sdir}")


def post_to_linkedin_playwright(
    content: str,
    session_dir: str | None = None,
    logger: AuditLogger | None = None,
) -> dict:
    """Publish a text post to LinkedIn via Playwright browser automation.

    Returns a result dict with keys: success, post_id, mode, (error).
    """
    from playwright.sync_api import sync_playwright

    sdir = session_dir or LINKEDIN_SESSION_DIR

    if not Path(sdir).exists():
        return {
            "success": False,
            "post_id": None,
            "mode": "playwright",
            "error": f"Session directory not found: {sdir}. Run --li-setup first.",
        }

    def _try_selectors(pg, selectors, action="click", timeout=10_000):
        """Try multiple selectors, return the first one that works."""
        for sel in selectors:
            try:
                pg.wait_for_selector(sel, timeout=timeout)
                return sel
            except Exception:
                continue
        return None

    try:
        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=sdir,
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(LINKEDIN_URL, wait_until="domcontentloaded")
            time.sleep(5)

            # Verify session
            if not check_linkedin_session(page):
                ctx.close()
                return {
                    "success": False,
                    "post_id": None,
                    "mode": "playwright",
                    "error": "Session expired — run --li-setup to re-authenticate.",
                }

            # Click "Start a post" — try multiple selectors
            start_sel = _try_selectors(page, LINKEDIN_START_POST_SELECTORS, timeout=15_000)
            if not start_sel:
                ctx.close()
                return {"success": False, "post_id": None, "mode": "playwright",
                        "error": "Could not find 'Start a post' button"}
            page.click(start_sel, timeout=15_000)
            time.sleep(2)

            # Find editor
            editor_sel = _try_selectors(page, LINKEDIN_EDITOR_SELECTORS, timeout=10_000)
            if not editor_sel:
                ctx.close()
                return {"success": False, "post_id": None, "mode": "playwright",
                        "error": "Could not find post editor"}

            # Type the post content
            editor = page.locator(editor_sel)
            editor.click()
            editor.fill(content)

            # Let LinkedIn JS process the input
            time.sleep(2)

            # Click "Post" button — try multiple selectors
            post_btn_sel = _try_selectors(page, LINKEDIN_POST_BUTTON_SELECTORS, timeout=10_000)
            if not post_btn_sel:
                ctx.close()
                return {"success": False, "post_id": None, "mode": "playwright",
                        "error": "Could not find Post button"}
            page.click(post_btn_sel, timeout=10_000)

            # Wait for the post modal to close (indicates success)
            try:
                page.wait_for_selector(
                    editor_sel,
                    state="hidden",
                    timeout=15_000,
                )
            except Exception:
                pass  # Modal may have closed differently

            # Try to capture the post URL from the feed
            post_url = page.url
            time.sleep(2)
            ctx.close()

            post_id = f"PW-{int(time.time())}"
            if logger:
                logger.log(
                    "linkedin_playwright_posted", "system", "success",
                    details={"post_id": post_id, "url": post_url},
                )

            return {
                "success": True,
                "post_id": post_id,
                "mode": "playwright",
                "url": post_url,
            }

    except Exception as exc:
        return {
            "success": False,
            "post_id": None,
            "mode": "playwright",
            "error": str(exc),
        }


def publish_approved_post(
    file_path: Path,
    vault_path: Path,
    mode: str = "simulate",
    logger: AuditLogger | None = None,
) -> str:
    """Publish an approved LinkedIn post and move the file to Done/.

    Returns ``"posted"`` | ``"simulated"`` | ``"error"``.
    """
    content = file_path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter_simple(content)
    post_text = _extract_post_content(body)
    title = fm.get("topic", file_path.stem)

    if logger:
        logger.log("linkedin_approval_detected", file_path.name, "success",
                    details={"approved_at": datetime.now(timezone.utc).isoformat()})

    # ---- Publish ----
    if mode == "playwright":
        result = post_to_linkedin_playwright(post_text, logger=logger)
        if not result["success"]:
            print(f"  [WARN] Playwright post failed: {result.get('error')}"
                  " — falling back to simulation")
            if logger:
                logger.log("linkedin_post_failed", file_path.name, "error",
                           error=result.get("error", "unknown"))
            result = simulate_post(post_text, title, logger)
        else:
            if logger:
                logger.log("linkedin_post_published", file_path.name,
                           "success", details={"mode": "playwright",
                                                "post_id": result["post_id"]})
    elif mode == "linkedin_api":
        token = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
        urn = os.getenv("LINKEDIN_PERSON_URN", "")
        if not token or not urn:
            print("  [WARN] LinkedIn credentials missing — falling back to simulation")
            result = simulate_post(post_text, title, logger)
        else:
            result = post_to_linkedin(post_text, token, urn)
            if result["success"]:
                if logger:
                    logger.log("linkedin_post_published", file_path.name,
                               "success", details={"mode": "linkedin_api",
                                                    "post_id": result["post_id"]})
            else:
                if logger:
                    logger.log("linkedin_post_failed", file_path.name, "error",
                               error=result.get("error", "unknown"))
                print(f"  [ERROR] Post failed: {result.get('error')}")
                return "error"
    else:
        result = simulate_post(post_text, title, logger)

    # ---- Update frontmatter & move to Done/ ----
    fm["status"] = "posted"
    fm["posted_at"] = datetime.now(timezone.utc).isoformat()
    fm["post_mode"] = result.get("mode", mode)
    fm["approved_at"] = fm.get("approved_at",
                               datetime.now(timezone.utc).isoformat())

    updated = _serialize_fm(fm, body)

    done = vault_path / "Done"
    done.mkdir(parents=True, exist_ok=True)
    dest = done / file_path.name
    if dest.exists():
        stem = file_path.stem
        dest = done / f"{stem}-{int(time.time()) % 10000}.md"

    dest.write_text(updated, encoding="utf-8")

    if dest.exists() and dest.stat().st_size > 0:
        file_path.unlink()

    return "simulated" if result["mode"] == "simulate" else "posted"


# ---------------------------------------------------------------------------
# Dashboard: Recent Social Posts section
# ---------------------------------------------------------------------------

def build_social_posts_table(vault_path: Path, limit: int = 10) -> str:
    """Build a Markdown table of recent LinkedIn posts across all folders."""
    posts: list[tuple[str, str, str, str]] = []  # (filename, date, status, topic)

    for folder, status_label in [
        (vault_path / "Pending_Approval", "draft"),
        (vault_path / "Approved", "approved"),
        (vault_path / "Done", "posted"),
    ]:
        if not folder.exists():
            continue
        for f in folder.glob("LINKEDIN_*.md"):
            content = f.read_text(encoding="utf-8")
            fm, _ = _parse_frontmatter_simple(content)
            topic = fm.get("topic", f.stem)
            status = fm.get("status", status_label)
            date_val = fm.get("generated_at", fm.get("posted_at", ""))
            if date_val:
                date_str = date_val[:16].replace("T", " ")
            else:
                mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
                date_str = mtime.strftime("%Y-%m-%d %H:%M")
            posts.append((f.name, date_str, status, topic[:40]))

    # Sort by date descending, limit
    posts.sort(key=lambda x: x[1], reverse=True)
    posts = posts[:limit]

    if not posts:
        return ""

    rows = []
    for name, date_str, status, topic in posts:
        rows.append(f"| {topic} | {date_str} | {status} | linkedin |")
    return "\n".join(rows) + "\n"


def update_dashboard_social(vault_path: Path,
                            logger: AuditLogger | None = None) -> None:
    """Insert / replace the ``Recent Social Posts`` section in Dashboard.md."""
    dashboard = vault_path / "Dashboard.md"
    if not dashboard.exists():
        return

    table = build_social_posts_table(vault_path)
    section = (
        "## Recent Social Posts\n\n"
        "<!-- START_SOCIAL_POSTS -->\n"
        "| Post | Date | Status | Platform |\n"
        "|------|------|--------|----------|\n"
        f"{table}"
        "<!-- END_SOCIAL_POSTS -->\n"
    )

    content = dashboard.read_text(encoding="utf-8")

    start_marker = "<!-- START_SOCIAL_POSTS -->"
    end_marker = "<!-- END_SOCIAL_POSTS -->"

    if start_marker in content:
        # Replace existing section
        start = content.find("## Recent Social Posts")
        if start == -1:
            start = content.find(start_marker)
        end = content.find(end_marker) + len(end_marker)
        content = content[:start] + section + content[end:]
    else:
        # Insert before "## How It Works" or at end
        insert_point = content.find("## How It Works")
        if insert_point == -1:
            insert_point = content.find("## Recent Activity")
        if insert_point == -1:
            content += "\n" + section
        else:
            content = content[:insert_point] + section + "\n" + content[insert_point:]

    dashboard.write_text(content, encoding="utf-8")

    post_count = len(list((vault_path / "Pending_Approval").glob("LINKEDIN_*.md"))) \
        + len(list((vault_path / "Approved").glob("LINKEDIN_*.md"))) \
        + len(list((vault_path / "Done").glob("LINKEDIN_*.md")))

    if logger:
        logger.log("linkedin_dashboard_updated", "system", "success",
                    details={"post_count": post_count})


# ---------------------------------------------------------------------------
# Approval watcher loop
# ---------------------------------------------------------------------------

def start_approval_watcher(vault_path: Path, interval: float = 10.0) -> None:
    """Poll ``Approved/`` for LinkedIn posts and publish them."""
    logger = AuditLogger(vault_path)
    mode = os.getenv("LINKEDIN_POST_MODE", "simulate")
    print(f"LinkedIn approval watcher started (mode={mode}, interval={interval}s)")

    try:
        while True:
            approved = scan_approved_posts(vault_path)
            for f in approved:
                status = publish_approved_post(f, vault_path, mode=mode,
                                               logger=logger)
                print(f"  [{status.upper()}] {f.name}")
            if approved:
                update_dashboard_social(vault_path, logger)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopping approval watcher ...")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="LinkedIn post drafting & publishing")
    parser.add_argument("--vault-path", default=None,
                        help="Path to vault root")
    parser.add_argument("--draft", default=None, metavar="TOPIC",
                        help="Generate a draft with this topic")
    parser.add_argument("--template", default="service_promotion",
                        choices=list(POST_TEMPLATES),
                        help="Template for draft generation")
    parser.add_argument("--publish", action="store_true",
                        help="Process all approved posts (one-shot)")
    parser.add_argument("--watch", action="store_true",
                        help="Continuously watch Approved/ for posts")
    parser.add_argument("--li-setup", action="store_true",
                        help="Open browser for LinkedIn login (Playwright mode)")
    parser.add_argument("--dashboard", action="store_true",
                        help="Update Dashboard social section only")
    args = parser.parse_args()

    vault = Path(args.vault_path or os.getenv("VAULT_PATH",
                 str(Path(__file__).parent.parent)))
    logger = AuditLogger(vault)

    if args.li_setup:
        setup_linkedin_session()
        return

    if args.draft:
        draft = generate_post_draft(args.draft, template=args.template)
        path = save_draft(draft, vault, logger)
        print(f"Draft saved: {path}")
        return

    if args.publish:
        mode = os.getenv("LINKEDIN_POST_MODE", "simulate")
        approved = scan_approved_posts(vault)
        if not approved:
            print("No approved LinkedIn posts found.")
            return
        for f in approved:
            status = publish_approved_post(f, vault, mode=mode, logger=logger)
            print(f"  [{status.upper()}] {f.name}")
        update_dashboard_social(vault, logger)
        return

    if args.watch:
        start_approval_watcher(vault)
        return

    if args.dashboard:
        update_dashboard_social(vault, logger)
        print("Dashboard social section updated.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
