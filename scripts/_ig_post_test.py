"""Test Instagram posting via Playwright — debug the Create > Post flow."""

from playwright.sync_api import sync_playwright
from pathlib import Path
import time
import sys
import json

sys.path.insert(0, str(Path(__file__).parent))
from social_poster import generate_instagram_image

SESSION_DIR = "C:/Users/HP User/.ai_employee/instagram_session"
img_path = generate_instagram_image(
    "AI-powered automation for your business.\n\n"
    "No more manual tasks.\nNo more missed deadlines.\n\n"
    "Smart workflows that keep YOU in control.",
    output_path=Path(__file__).parent / "assets" / "ig_live_post.png",
)
print(f"Image: {img_path} ({img_path.stat().st_size} bytes)")

with sync_playwright() as pw:
    ctx = pw.chromium.launch_persistent_context(
        user_data_dir=SESSION_DIR,
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1280, "height": 900},
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
    time.sleep(8)
    print("Page loaded")

    # Step 1: Click Create (+) in the sidebar
    svg = page.locator('svg[aria-label="New post"]').first
    bbox = svg.bounding_box()
    print(f"Create SVG at: {bbox}")
    page.mouse.click(bbox["x"] + bbox["width"] / 2, bbox["y"] + bbox["height"] / 2)
    time.sleep(3)

    # Step 2: The submenu shows "Post" and "AI" — click "Post"
    # Find the Post item in the expanded submenu
    post_items = page.locator("span").all()
    for item in post_items:
        try:
            text = item.inner_text()
            if text.strip() == "Post" and item.is_visible():
                item_box = item.bounding_box()
                if item_box and item_box["y"] > bbox["y"]:  # Below the Create button
                    print(f"Found 'Post' submenu at y={item_box['y']}")
                    page.mouse.click(
                        item_box["x"] + item_box["width"] / 2,
                        item_box["y"] + item_box["height"] / 2,
                    )
                    time.sleep(4)
                    break
        except Exception:
            continue

    page.screenshot(path="scripts/assets/ig_debug_after_post.png")

    # Check what happened — dialog? file input? URL change?
    print(f"URL: {page.url}")
    dialog_count = page.locator('[role="dialog"]').count()
    file_count = page.locator('input[type="file"]').count()
    print(f"Dialogs: {dialog_count}, File inputs: {file_count}")

    # Scan for any overlay text
    for d in page.locator('[role="dialog"]').all():
        try:
            print(f"Dialog text: {d.inner_text()[:200]}")
        except Exception:
            pass

    # Check for "Create new post" or "Drag photos" text
    body_text = page.locator("body").inner_text()
    for phrase in ["Create new post", "Drag photos", "Select from", "new post",
                   "select from computer", "drag", "upload"]:
        if phrase.lower() in body_text.lower():
            print(f"FOUND: '{phrase}' in page!")

    # If dialog opened, try to upload
    if file_count > 0:
        print("Uploading image via file input...")
        page.locator('input[type="file"]').first.set_input_files(str(img_path))
        time.sleep(5)
        page.screenshot(path="scripts/assets/ig_uploaded.png")

        # Click Next twice (crop -> filter)
        for i in range(2):
            try:
                page.locator('div[role="button"]:has-text("Next")').first.click(timeout=8000)
                time.sleep(3)
                print(f"Next {i + 1}")
            except Exception:
                print(f"No Next {i + 1}")

        # Caption
        try:
            cap = page.locator(
                'div[aria-label="Write a caption..."],'
                'textarea[aria-label="Write a caption..."]'
            ).first
            cap.click(timeout=5000)
            page.keyboard.type(
                "AI-powered automation for your business. "
                "Smart workflows, zero manual work. "
                "#AIAutomation #BusinessGrowth #Productivity",
                delay=15,
            )
            print("Caption typed")
        except Exception as e:
            print(f"Caption error: {e}")

        # Share
        try:
            page.locator('div[role="button"]:has-text("Share")').first.click(timeout=10000)
            time.sleep(10)
            page.screenshot(path="scripts/assets/ig_shared.png")
            print("POSTED SUCCESSFULLY!")
        except Exception as e:
            print(f"Share error: {e}")
    else:
        # Maybe the dialog needs a different trigger — try waiting for file input
        print("No file input found. Checking for hidden inputs...")
        hidden = page.evaluate("""() => {
            const inputs = document.querySelectorAll('input[type="file"]');
            return Array.from(inputs).map(i => ({
                accept: i.accept,
                hidden: i.hidden,
                display: window.getComputedStyle(i).display
            }));
        }""")
        print(f"Hidden file inputs: {hidden}")

        if hidden:
            page.locator('input[type="file"]').first.set_input_files(str(img_path))
            time.sleep(5)
            page.screenshot(path="scripts/assets/ig_uploaded.png")
            print("Uploaded via hidden input!")

    # Final state
    page.screenshot(path="scripts/assets/ig_final.png")
    ctx.close()
    print("Done!")
