# Quickstart: WhatsApp Watcher + LinkedIn Post Skill

**Feature**: 004-whatsapp-linkedin-silver
**Date**: 2026-02-22

## Prerequisites

- Python 3.10+
- Existing Bronze + Silver Tier setup working (file watcher, Gmail watcher, Dashboard)
- WhatsApp account linked to a phone with active internet
- (Optional) LinkedIn developer app for real posting

## Step 1: Install New Dependencies

```bash
pip install -r requirements.txt
```

New dependencies added:
- `playwright>=1.40.0` — browser automation for WhatsApp Web
- `requests>=2.31.0` — HTTP client for LinkedIn API

Then install the Chromium browser for Playwright:

```bash
playwright install chromium
```

## Step 2: Update Environment

Add to your `.env` file:

```bash
# WhatsApp Watcher (Silver Tier)
WHATSAPP_POLL_INTERVAL=30
WHATSAPP_SESSION_DIR=~/.ai_employee/whatsapp_session
WHATSAPP_KEYWORDS=urgent,invoice,payment,help,deadline,asap

# LinkedIn Poster (Silver Tier)
LINKEDIN_POST_MODE=simulate
# LINKEDIN_ACCESS_TOKEN=          # Only for real posting
# LINKEDIN_PERSON_URN=            # Only for real posting (urn:li:person:xxx)
```

## Step 3: WhatsApp Watcher Setup

### First-time authentication (QR code scan)

```bash
python scripts/whatsapp_watcher.py --setup
```

This opens a visible Chromium browser window with WhatsApp Web. Scan the QR code with your phone's WhatsApp app. After successful login, the session is saved to `~/.ai_employee/whatsapp_session/` and the browser closes.

### Start the watcher (headless)

```bash
python scripts/whatsapp_watcher.py
```

The watcher polls WhatsApp Web every 30 seconds for unread messages containing priority keywords. Matching messages create `WHATSAPP_*.md` files in `Needs_Action/`.

### Quick check (one-shot)

```bash
python scripts/whatsapp_watcher.py --check
```

Scrapes unread messages once, prints results, and exits. Useful for verifying the session works.

## Step 4: LinkedIn Posting

### Generate a draft

```bash
python scripts/linkedin_poster.py --draft "AI Automation for Small Businesses"
```

Options for `--template`:
- `service_promotion` (default) — Service/product announcement
- `case_study` — Client success story
- `thought_leadership` — Industry insight or tip

The draft appears in `Pending_Approval/LINKEDIN_*.md`.

### Review and approve

1. Open the draft file in Obsidian or any editor
2. Edit the post content if desired
3. **To approve**: Move the file to `Approved/`
4. **To reject**: Delete the file or move to `Done/`

### Publish approved posts

```bash
# One-shot: process all approved posts
python scripts/linkedin_poster.py --publish

# Continuous: watch for approvals
python scripts/linkedin_poster.py --watch
```

**Default mode is simulation** — posts are logged as "SIMULATED" and moved to `Done/`.

### (Optional) Enable real LinkedIn posting

1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/)
2. Create an app (any name)
3. Under Products, request `Share on LinkedIn` (auto-approved)
4. Under Auth, note the Client ID and Client Secret
5. Complete OAuth 2.0 flow to get an access token
6. Add to `.env`:
   ```bash
   LINKEDIN_POST_MODE=linkedin_api
   LINKEDIN_ACCESS_TOKEN=your_token_here
   LINKEDIN_PERSON_URN=urn:li:person:your_member_id
   ```

## Step 5: Run All Watchers

Open three terminal windows:

```bash
# Terminal 1: File watcher (Bronze)
python scripts/watcher.py

# Terminal 2: Gmail watcher (Silver)
python scripts/gmail_watcher.py

# Terminal 3: WhatsApp watcher (Silver)
python scripts/whatsapp_watcher.py
```

All three run concurrently with no conflicts.

## Step 6: Update Dashboard

```bash
python scripts/update_dashboard.py
```

Dashboard now shows:
- Quick Status with all 3 watchers + Approved folder count
- Pending Tasks (including WhatsApp messages)
- Recent Social Posts (LinkedIn drafts/posts)
- Recent Activity (all audit log events)

## Verification Checklist

- [ ] `playwright install chromium` completes without errors
- [ ] `--setup` opens browser, QR scan succeeds, session saved
- [ ] `--check` shows unread messages (or empty if none)
- [ ] Headless watcher creates `WHATSAPP_*.md` files for keyword-matched messages
- [ ] `--draft` creates `LINKEDIN_*.md` in `Pending_Approval/`
- [ ] Moving draft to `Approved/` + `--publish` moves to `Done/`
- [ ] Dashboard shows "Recent Social Posts" section
- [ ] All events appear in `Logs/YYYY-MM-DD.audit.jsonl`
- [ ] Three watchers run concurrently without errors

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `playwright install` fails | Try `pip install playwright --upgrade` then `playwright install chromium` again |
| QR code not appearing | Check internet connection, try `--setup` again |
| Session expired | Run `--setup` again to re-authenticate |
| WhatsApp selectors failing | WhatsApp Web may have updated — check logs for selector warnings |
| LinkedIn token expired | Re-do OAuth flow, update `LINKEDIN_ACCESS_TOKEN` in `.env` |
| No messages detected | Verify keywords in `.env`, check that messages contain keywords |

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `VAULT_PATH` | Parent of scripts/ | Vault root directory |
| `WHATSAPP_POLL_INTERVAL` | `30` | Seconds between WhatsApp polls |
| `WHATSAPP_SESSION_DIR` | `~/.ai_employee/whatsapp_session` | Browser session storage |
| `WHATSAPP_KEYWORDS` | `urgent,invoice,...` | Comma-separated priority keywords |
| `LINKEDIN_POST_MODE` | `simulate` | `simulate` or `linkedin_api` |
| `LINKEDIN_ACCESS_TOKEN` | None | LinkedIn OAuth token |
| `LINKEDIN_PERSON_URN` | None | LinkedIn person URN |
