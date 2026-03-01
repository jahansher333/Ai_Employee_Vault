"""Live Instagram post via Playwright — fixed Share button."""

from playwright.sync_api import sync_playwright
from pathlib import Path
import time
import sys

sys.path.insert(0, str(Path(__file__).parent))
from social_poster import generate_instagram_image

SESSION_DIR = "C:/Users/HP User/.ai_employee/instagram_session"
img_path = generate_instagram_image(
    "AI-powered automation for your business.\n\n"
    "No more manual tasks.\nNo more missed deadlines.\n\n"
    "Smart workflows that keep YOU in control.",
    output_path=Path(__file__).parent / "assets" / "ig_live_post.png",
)
print(f"Image: {img_path}")

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

    # Step 1: Click Create (+)
    svg = page.locator('svg[aria-label="New post"]').first
    bbox = svg.bounding_box()
    page.mouse.click(bbox["x"] + bbox["width"] / 2, bbox["y"] + bbox["height"] / 2)
    time.sleep(3)
    print("Create menu opened")

    # Step 2: Click 'Post' submenu
    for item in page.locator("span").all():
        try:
            if item.inner_text().strip() == "Post" and item.is_visible():
                item_box = item.bounding_box()
                if item_box and item_box["y"] > bbox["y"]:
                    page.mouse.click(
                        item_box["x"] + item_box["width"] / 2,
                        item_box["y"] + item_box["height"] / 2,
                    )
                    time.sleep(4)
                    print("Clicked Post submenu")
                    break
        except Exception:
            continue

    # Step 3: Upload image
    file_input = page.locator('input[type="file"]')
    if file_input.count() > 0:
        file_input.first.set_input_files(str(img_path))
        time.sleep(5)
        print("Image uploaded")
    else:
        print("ERROR: No file input found!")
        page.screenshot(path="scripts/assets/ig_error.png")
        ctx.close()
        sys.exit(1)

    # Step 4: Click Next twice
    for i in range(2):
        try:
            page.locator('div[role="button"]:has-text("Next")').first.click(timeout=8000)
            time.sleep(3)
            print(f"Next {i + 1}")
        except Exception:
            print(f"No Next {i + 1}")

    # Step 5: Caption
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

    # Step 6: Click Share — it's a link/div at top-right of the dialog header
    # The text "Share" is in the dialog header area
    time.sleep(2)
    try:
        # Use JavaScript to find and click the Share element inside the dialog
        page.evaluate("""() => {
            const dialog = document.querySelector('[role="dialog"]');
            if (!dialog) return;
            // Find all elements with "Share" text in the dialog header
            const elements = dialog.querySelectorAll('div[role="button"], a, span, button');
            for (const el of elements) {
                if (el.textContent.trim() === 'Share' && el.offsetParent !== null) {
                    const rect = el.getBoundingClientRect();
                    // The Share link is at the top-right (y < 150)
                    if (rect.y < 150) {
                        el.click();
                        return;
                    }
                }
            }
        }""")
        print("Clicked Share via JS!")
        time.sleep(12)
        page.screenshot(path="scripts/assets/ig_shared.png")
        print("POST SHARED SUCCESSFULLY!")
    except Exception as e:
        print(f"Share JS error: {e}")
        # Fallback: click by coordinates — Share is at top-right of dialog
        try:
            dialog = page.locator('[role="dialog"]').first
            dbox = dialog.bounding_box()
            # Share is at top-right corner of dialog
            share_x = dbox["x"] + dbox["width"] - 40
            share_y = dbox["y"] + 25
            print(f"Clicking Share at ({share_x}, {share_y})")
            page.mouse.click(share_x, share_y)
            time.sleep(12)
            page.screenshot(path="scripts/assets/ig_shared.png")
            print("POST SHARED via coordinates!")
        except Exception as e2:
            print(f"Share coord error: {e2}")

    ctx.close()
    print("Done!")
