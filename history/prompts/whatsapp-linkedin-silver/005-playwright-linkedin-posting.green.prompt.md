---
id: 005
title: Add Playwright-based LinkedIn Posting
stage: green
date: 2026-02-23
surface: agent
model: claude-opus-4-6
feature: whatsapp-linkedin-silver
branch: 004-whatsapp-linkedin-silver
user: Jansher
command: implement
labels: ["playwright", "linkedin", "browser-automation", "posting"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - scripts/linkedin_poster.py
  - tests/test_linkedin_poster.py
  - .env.example
tests:
  - tests/test_linkedin_poster.py::TestPlaywrightConstants::test_selectors_keys
  - tests/test_linkedin_poster.py::TestPlaywrightConstants::test_session_dir_default
  - tests/test_linkedin_poster.py::TestCheckLinkedinSession::test_returns_true_when_feed_found
  - tests/test_linkedin_poster.py::TestCheckLinkedinSession::test_returns_false_on_timeout
  - tests/test_linkedin_poster.py::TestPostToLinkedinPlaywright::test_missing_session_dir
  - tests/test_linkedin_poster.py::TestPostToLinkedinPlaywright::test_successful_post
  - tests/test_linkedin_poster.py::TestPostToLinkedinPlaywright::test_expired_session_returns_error
  - tests/test_linkedin_poster.py::TestPublishApprovedPlaywright::test_playwright_mode_success
  - tests/test_linkedin_poster.py::TestPublishApprovedPlaywright::test_playwright_fallback_to_simulate
---

## Prompt

Implement the following plan: Add Playwright-based LinkedIn Posting. Add a `playwright` post mode to `linkedin_poster.py` that uses browser automation to post directly to LinkedIn via the web UI, reusing the same Playwright pattern as `whatsapp_watcher.py`. Includes session management, `--li-setup` CLI flag, `post_to_linkedin_playwright()` function, and integration into `publish_approved_post()`.

## Response snapshot

Implemented Playwright-based LinkedIn posting with:
- `LINKEDIN_SESSION_DIR` constant and `LINKEDIN_SELECTORS` dict for DOM selectors
- `check_linkedin_session()` — validates feed is loaded (authenticated)
- `setup_linkedin_session()` — opens visible browser for manual login, saves persistent session
- `post_to_linkedin_playwright()` — headless posting via click "Start a post" → fill editor → click "Post"
- `--li-setup` CLI flag for browser login setup
- `playwright` branch in `publish_approved_post()` with fallback to simulate on failure
- `LINKEDIN_SESSION_DIR` added to `.env.example`
- 9 new tests covering constants, session check, posting, and publish integration
- All 134 tests pass (28 LinkedIn-specific)

## Outcome

- ✅ Impact: New `playwright` post mode fully integrated into LinkedIn poster pipeline
- 🧪 Tests: 134/134 passing (9 new Playwright tests added)
- 📁 Files: 3 modified (linkedin_poster.py, test_linkedin_poster.py, .env.example)
- 🔁 Next prompts: End-to-end manual test with real LinkedIn session
- 🧠 Reflection: Followed WhatsApp watcher pattern closely for consistency; lazy Playwright import avoids test dependency issues

## Evaluation notes (flywheel)

- Failure modes observed: Initial test patching used wrong import path for lazy-imported sync_playwright; fixed by patching playwright.sync_api.sync_playwright
- Graders run and results (PASS/FAIL): pytest PASS (134/134)
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): null
