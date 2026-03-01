# Research: Silver Tier Final Lock — WhatsApp Watcher + LinkedIn Post Skill

**Feature**: 004-whatsapp-linkedin-silver
**Date**: 2026-02-22
**Status**: Complete — all unknowns resolved

## Research Tasks

### RT-1: WhatsApp Web Automation Library Selection

**Question**: Which Python library best supports reading incoming WhatsApp messages with session persistence and headless operation?

**Options Evaluated**:

| Library | Language | Read Messages | Session Persist | Headless | Maintained |
|---------|----------|--------------|-----------------|----------|------------|
| Playwright (Python) | Python | Yes (DOM scraping) | Yes (`user_data_dir`) | Yes | Active |
| Selenium | Python | Yes (DOM scraping) | Partial (manual profile) | Yes | Active |
| whatsapp-web.js | Node.js | Yes (native protocol) | Yes | Yes | Active |
| pywhatkit | Python | No (send only) | No | No | Stale |
| yowsup | Python | Yes | No | Yes | Abandoned |
| WhatsApp Business API | REST | Yes | N/A (cloud) | N/A | Official |

**Decision**: **Playwright (Python)**

**Rationale**:
- Python-native — no subprocess bridge to Node.js, matches existing codebase language
- `browser.launch_persistent_context(user_data_dir=...)` handles session persistence natively
- First run: `headless=False` for QR code scanning; subsequent: `headless=True`
- Actively maintained by Microsoft, broad community
- Installation: `pip install playwright && playwright install chromium`

**Alternatives rejected**:
- **whatsapp-web.js**: Best protocol-level support but requires Node.js. Would need subprocess bridge (`subprocess.Popen(["node", "whatsapp-bridge.js"])`) adding complexity and a second runtime dependency.
- **Selenium**: Works but heavier, less reliable session persistence (requires manual Chrome profile management), slower element interaction.
- **WhatsApp Business API**: Requires Meta Business verification — not feasible for a hackathon timeline.
- **pywhatkit**: Cannot read incoming messages, only sends. Does not meet FR-001.

**Key implementation details**:
- Session directory: `~/.ai_employee/whatsapp_session/` (outside vault per FR-005)
- DOM selectors for unread messages, sender names, and message text must be externalized
- Poll interval: 30 seconds (configurable via `WHATSAPP_POLL_INTERVAL`)
- Message dedup: hash of `sender + timestamp + message_text[:50]` stored in ledger

---

### RT-2: LinkedIn Posting Mechanism

**Question**: What is the simplest approach for LinkedIn posting that supports simulation mode and optional real posting?

**Options Evaluated**:

| Approach | Effort | Credentials Needed | Risk | Demo Quality |
|----------|--------|-------------------|------|-------------|
| Simulation (log + file move) | Trivial | None | None | Good (shows workflow) |
| LinkedIn API (`w_member_social`) | Low-Medium | OAuth token | None (official) | Excellent (real post) |
| Buffer API | Low | Buffer token | None | Good |
| Browser automation | High | LinkedIn login | Very High (bans) | Poor (fragile) |

**Decision**: **Three-mode architecture — simulate (default) → LinkedIn API → Buffer (optional)**

**Rationale**:
- **Simulation mode** (default): Zero configuration. Logs "POST SIMULATED: {title}" and moves file to `Done/`. Perfect for demo when no credentials are available.
- **LinkedIn API mode**: The `w_member_social` scope is available on any free LinkedIn App without review. One-time OAuth redirect dance produces a 60-day access token stored in `.env`. REST POST to `https://api.linkedin.com/v2/ugcPosts` with `author` URN and `shareCommentary` text.
- **Buffer mode**: Optional future enhancement. Not needed for hackathon.

**LinkedIn API details**:
- Create app at https://www.linkedin.com/developers/
- Request `w_member_social` scope (auto-approved for free apps)
- OAuth 2.0 authorization code flow → access token (60-day expiry)
- POST endpoint: `https://api.linkedin.com/v2/ugcPosts`
- Required headers: `Authorization: Bearer {token}`, `X-Restli-Protocol-Version: 2.0.0`
- Person URN format: `urn:li:person:{member_id}`

**Alternatives rejected**:
- **Browser automation**: LinkedIn actively detects and bans automated browser access. Session cookies are short-lived. Too fragile for any use.
- **Buffer-only**: Adds unnecessary third-party dependency for a hackathon.

---

### RT-3: WhatsApp DOM Selector Strategy

**Question**: How to reliably extract message data from WhatsApp Web's DOM?

**Decision**: Externalized selector configuration with startup validation.

**Approach**:
```python
SELECTORS = {
    "chat_list": 'div[aria-label="Chat list"]',
    "unread_chat": 'span[aria-label*="unread message"]',
    "chat_item": 'div[role="listitem"]',
    "sender_name": 'span[dir="auto"][title]',
    "message_text": 'span.selectable-text',
    "timestamp": 'div[data-pre-plain-text]',
}
```

**Validation at startup**: Before entering the poll loop, verify each selector returns at least one element on the WhatsApp Web page. Log warnings for any selector that fails, and exit with a clear error if critical selectors (chat_list, message_text) fail.

**Fallback**: If selectors break, the watcher logs an error and stops gracefully rather than creating incorrect task files.

---

### RT-4: Session Persistence Architecture

**Question**: How to store WhatsApp session data securely outside the vault?

**Decision**: Use Playwright's `user_data_dir` parameter pointing to `~/.ai_employee/whatsapp_session/`.

**Details**:
- Playwright's persistent context stores all browser state (cookies, localStorage, IndexedDB) in the specified directory
- First run: `headless=False` → user scans QR code → session saved automatically
- Subsequent runs: `headless=True` → session loaded from directory → no QR needed
- Session typically lasts 24+ hours before WhatsApp requires re-auth
- If session expires: Playwright will show the QR code page → detected by checking for QR element → log error + alert user

**Security**:
- Directory is `~/.ai_employee/whatsapp_session/` — outside vault, not in git
- Permissions: `0700` on the directory (user-only access)
- `.gitignore` already excludes anything outside vault root

---

### RT-5: LinkedIn Post Template Design

**Question**: What post templates provide the best hackathon demo value?

**Decision**: Three templates matching FR-014.

**Templates**:

1. **Service Promotion**: Announces a service/product with value proposition, bullet points, and call-to-action. Professional tone, 3-5 hashtags.

2. **Case Study Highlight**: Summarizes a client success story with problem/solution/result structure. Social proof emphasis, 3-4 hashtags.

3. **Thought Leadership Tip**: Shares an industry insight or tip with personal perspective. Conversational tone, 2-3 hashtags.

Each template produces 150-300 word posts (LinkedIn optimal length) with:
- Hook line (first sentence visible in feed)
- Body content (template-specific structure)
- Call-to-action
- Hashtags (3-5, industry-relevant)

---

### RT-6: Concurrent Watcher Architecture

**Question**: How to run 3 watchers (file, Gmail, WhatsApp) concurrently without conflicts?

**Decision**: Independent processes with no shared mutable state.

**Analysis**:
- **File watcher** (`watcher.py`): Uses watchdog Observer, writes to `Logs/.watcher_ledger.txt`
- **Gmail watcher** (`gmail_watcher.py`): Polls Gmail API, writes to `Logs/.gmail_ledger.txt`
- **WhatsApp watcher** (`whatsapp_watcher.py`): Polls browser DOM, writes to `Logs/.whatsapp_ledger.txt`

**No conflicts because**:
- Each watcher has its own ledger file (no shared writes)
- All write to `Needs_Action/` but with different filename prefixes (`EMAIL_*`, `WHATSAPP_*`, task files)
- All use the same `AuditLogger` but it's append-only JSON Lines (concurrent appends are safe on same-line writes)
- No shared browser instances or API connections

**Startup**: Three separate terminal windows or `&` background processes. No orchestrator needed for hackathon.

---

### RT-7: Dashboard Social Posts Section

**Question**: How to integrate LinkedIn post tracking into the existing Dashboard?

**Decision**: Add a new marker-bounded section following the existing analytics pattern.

**Implementation**:
- New markers: `<!-- START_SOCIAL_POSTS -->` / `<!-- END_SOCIAL_POSTS -->`
- Positioned after the existing sections in Dashboard template
- Function `build_social_posts_table()` scans all three folders for `LINKEDIN_*.md` files
- Shows: Post Title, Date, Status (draft/approved/posted), Platform
- Limited to last 10 posts (most recent first)

**Follows existing pattern**: Same approach as `<!-- START_ANALYTICS -->` / `<!-- END_ANALYTICS -->` used by `data_analyzer.py`.
