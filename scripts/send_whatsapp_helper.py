"""Helper script to send WhatsApp message via Playwright. Called by the dashboard."""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

def main():
    if len(sys.argv) < 2:
        print("ERROR: No input file provided")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)

    phone = data["phone"].replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    msg = data["message"]

    try:
        from playwright.sync_api import sync_playwright

        session_dir = os.path.expanduser(
            os.getenv("WHATSAPP_SESSION_DIR", "~/.ai_employee/whatsapp_session")
        )
        Path(session_dir).mkdir(parents=True, exist_ok=True)

        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=session_dir,
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()

            from urllib.parse import quote
            url = f"https://web.whatsapp.com/send?phone={phone}&text={quote(msg)}"
            page.goto(url, wait_until="domcontentloaded")

            # Wait for WhatsApp Web to fully load
            try:
                page.wait_for_selector('div[id="main"]', timeout=30000)
            except Exception:
                pass
            time.sleep(8)

            send_selectors = [
                'span[data-icon="send"]',
                'button[aria-label="Send"]',
                'button[data-testid="compose-btn-send"]',
                'div[role="button"][aria-label="Send"]',
            ]
            sent = False
            for sel in send_selectors:
                try:
                    el = page.wait_for_selector(sel, timeout=10000)
                    if el:
                        el.click()
                        sent = True
                        break
                except Exception:
                    continue

            if sent:
                time.sleep(3)
                print("SUCCESS")
            else:
                print("FAILED: Could not find send button. WhatsApp session may be expired. Run: python scripts/whatsapp_watcher.py --setup")

            ctx.close()
    except ImportError:
        print("FAILED: Playwright not installed. Run: pip install playwright && playwright install chromium")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
