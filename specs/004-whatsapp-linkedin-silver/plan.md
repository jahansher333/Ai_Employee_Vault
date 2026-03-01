# Implementation Plan: Silver Tier Final Lock — WhatsApp Watcher + LinkedIn Post Skill

**Branch**: `004-whatsapp-linkedin-silver` | **Date**: 2026-02-22 | **Spec**: `specs/004-whatsapp-linkedin-silver/spec.md`
**Input**: Feature specification from `/specs/004-whatsapp-linkedin-silver/spec.md`

## Summary

Complete the Silver Tier by adding two final capabilities: (1) a WhatsApp Web watcher that monitors incoming messages for priority keywords and creates task files in `Needs_Action/`, and (2) a LinkedIn posting skill that generates post drafts for human approval and supports simulated or real posting after approval. Both integrate with the existing audit logger, process_inbox pipeline, Dashboard, and folder-based workflow.

**Technical approach**: WhatsApp monitoring via Playwright browser automation with persistent sessions. LinkedIn posting via direct LinkedIn API (`w_member_social` scope) with simulation-mode fallback. Both follow the established patterns: ledger-based deduplication, YAML-frontmatter task files, audit logging, and Dashboard marker-based updates.

## Technical Context

**Language/Version**: Python 3.10+ (matches existing codebase)
**Primary Dependencies**: playwright (WhatsApp browser automation), requests/urllib3 (LinkedIn API calls), existing: watchdog, google-api-python-client, pandas, python-dotenv
**Storage**: Markdown files with YAML frontmatter (vault filesystem), text ledgers in `Logs/`, session data in `~/.ai_employee/whatsapp_session/`
**Testing**: pytest (matches existing test suite in `tests/`)
**Target Platform**: Windows 10+ desktop (current dev environment), headless browser after initial setup
**Project Type**: Single project — extending existing `scripts/` + `tests/` layout
**Performance Goals**: WhatsApp message detection within 60s of arrival (SC-001), LinkedIn draft generation within 5s (SC-004)
**Constraints**: No external writes without HITL approval (Constitution VI), session tokens outside vault (SC-009), 3 concurrent watchers without conflicts (SC-007)
**Scale/Scope**: Single user, single WhatsApp account, single LinkedIn account, ~300 existing task files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. Clarity of Requirements** | PASS | Spec has 21 FRs with RFC 2119 keywords, 6 user stories with Given/When/Then, 9 edge cases |
| **II. Security & Sensitive Action Approval** | PASS | WhatsApp session stored outside vault (FR-005, SC-009). LinkedIn posts require HITL approval (FR-015). Credentials in `.env` only |
| **III. Logging & Audit Records** | PASS | All events logged to audit trail (FR-007, SC-008). Ledger deduplication follows Gmail pattern |
| **IV. Modular Code Organization** | PASS | Each component is a separate script: `whatsapp_watcher.py`, `linkedin_poster.py`. Skills are separate `.md` files. No circular dependencies |
| **V. Readable Task & Plan Artifacts** | PASS | This plan follows template structure. Tasks will follow existing pattern |
| **VI. Detection Only — No Direct External Automation** | **DEVIATION** | LinkedIn posting (FR-011) writes to external system. **Justified**: (a) requires explicit HITL approval per FR-015, (b) simulation mode is default per FR-016, (c) spec explicitly defines this as Silver Tier capability beyond Bronze detection-only. See Complexity Tracking |

**Gate Result**: PASS with documented deviation for Principle VI.

## Project Structure

### Documentation (this feature)

```text
specs/004-whatsapp-linkedin-silver/
├── plan.md              # This file
├── research.md          # Phase 0 output — technology decisions
├── data-model.md        # Phase 1 output — entity definitions
├── quickstart.md        # Phase 1 output — setup guide
├── contracts/           # Phase 1 output — internal interfaces
│   ├── whatsapp-watcher.md
│   └── linkedin-poster.md
└── tasks.md             # Phase 2 output (/sp.tasks)
```

### Source Code (repository root)

```text
scripts/
├── audit_logger.py          # Existing — shared logging (no changes)
├── watcher.py               # Existing — file system watcher (no changes)
├── gmail_watcher.py         # Existing — Gmail watcher (no changes)
├── process_inbox.py         # Existing — minor update: handle whatsapp type
├── update_dashboard.py      # Existing — update: add social posts section
├── data_analyzer.py         # Existing — no changes
├── whatsapp_watcher.py      # NEW — WhatsApp Web message monitor
└── linkedin_poster.py       # NEW — LinkedIn draft generation + posting

.claude/skills/
├── simple-task-reader.md        # Existing
├── process-inbox-item.md        # Existing
├── move-to-done.md              # Existing
├── check-pending-approvals.md   # Existing
├── data-analyzer.md             # Existing
├── generate-status-report.md    # Existing
├── whatsapp-message-parser.md   # NEW — WhatsApp message parsing skill
└── linkedin-poster.md           # NEW — LinkedIn post drafting skill

tests/
├── conftest.py                  # Update: add Approved/ fixture, sample data
├── test_whatsapp_watcher.py     # NEW — WhatsApp watcher tests
├── test_linkedin_poster.py      # NEW — LinkedIn poster tests
└── ... (existing tests unchanged)
```

**Structure Decision**: Extending the existing flat `scripts/` layout. No new directories needed beyond `Approved/` (for the posting workflow) and `contracts/` (under specs). This matches the established pattern where each feature is a single script + skill pair.

## Complexity Tracking

> Constitution Check deviation documented below.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle VI: LinkedIn posting writes to external system | Silver Tier explicitly requires "Auto-post LinkedIn (with approval)" as a tier completion requirement. The hackathon rubric scores this capability. | Detection-only would not meet Silver Tier requirements. Mitigation: simulation mode is default, real posting requires explicit HITL approval + credentials, no post executes without file physically moved to `Approved/` by the user. |

## Architecture Decisions

### AD-1: WhatsApp Monitoring via Playwright

**Decision**: Use Playwright (Python) for WhatsApp Web browser automation.

**Rationale**:
- Python-native (`pip install playwright`) — matches existing codebase
- `persistent_context` with `user_data_dir` provides session persistence across restarts
- Supports headless mode after initial QR code setup
- Active maintenance and broad adoption
- No Node.js subprocess bridge needed

**Alternatives considered**:
- Selenium: heavier, less reliable session persistence
- whatsapp-web.js (Node): requires subprocess bridge, different language
- WhatsApp Business API: requires business verification, not suitable for hackathon
- pywhatkit: limited to sending, cannot read incoming messages

**Risks**:
- DOM selector fragility if WhatsApp updates their web UI. Mitigation: externalize selectors to a config dict, validate at startup, log warnings if selectors fail.
- WhatsApp ToS technically prohibits automation. Mitigation: this is a hackathon demo, personal account, read-only monitoring.

### AD-2: LinkedIn Posting Strategy — Simulation Default + API Optional

**Decision**: Three-mode architecture: simulate (default) → LinkedIn direct API → Buffer API (optional).

**Rationale**:
- Simulation mode (log + move file) requires zero credentials — perfect for demo
- LinkedIn `w_member_social` scope is available on free apps without review
- One-time OAuth dance gets a 60-day token stored in `.env`
- Clean separation: draft generation is always local, posting is mode-dependent

**Alternatives considered**:
- Browser automation for LinkedIn: high ban risk, fragile
- Buffer-only: adds unnecessary dependency for hackathon
- API-only: would fail without credentials, bad demo experience

### AD-3: Folder-Based Approval Workflow for LinkedIn Posts

**Decision**: Reuse existing `Pending_Approval/` → `Approved/` → `Done/` folder workflow for LinkedIn posts.

**Rationale**:
- Matches the established HITL pattern from Bronze Tier
- User already understands the paradigm (move file = approve)
- No new UI or approval mechanism needed
- Auditable via existing logging

**New folder**: `Approved/` must be created. Posts move: `Pending_Approval/LINKEDIN_*.md` → (user moves) → `Approved/LINKEDIN_*.md` → (system posts + moves) → `Done/LINKEDIN_*.md`.

## Component Design

### WhatsApp Watcher (`whatsapp_watcher.py`)

**Responsibilities**:
1. Launch Playwright browser with persistent session context
2. Navigate to WhatsApp Web, handle QR auth on first run
3. Poll for unread messages at configurable interval (default: 30s)
4. Extract sender, message text, timestamp from DOM
5. Match against priority keywords (case-insensitive)
6. Create `WHATSAPP_{HHMMSS}_{sender}.md` in `Needs_Action/`
7. Deduplicate via `Logs/.whatsapp_ledger.txt`
8. Log all events to audit logger

**Key design patterns**:
- Same ledger pattern as `gmail_watcher.py` (text file, one ID per line)
- Same task file format as `gmail_watcher.py` (YAML frontmatter + markdown body)
- Same CLI pattern: `--setup` for QR auth, `--check` for one-shot, default for polling
- Session stored in `~/.ai_employee/whatsapp_session/` (outside vault)
- Selectors externalized in a `SELECTORS` dict at module top for easy maintenance

**Frontmatter schema**:
```yaml
---
type: whatsapp
from: "Sender Name"
message: "Message text preview"
date: "ISO8601"
priority: high|medium
matched_keywords: ["urgent", "invoice"]
chat_type: individual|group
status: new
---
```

### LinkedIn Poster (`linkedin_poster.py`)

**Responsibilities**:
1. Generate LinkedIn post drafts from topic + template type
2. Save drafts to `Pending_Approval/LINKEDIN_{HHMMSS}_{topic}.md`
3. Watch `Approved/` for approved posts (`LINKEDIN_*.md` pattern)
4. Post via configured mode (simulate / linkedin_api / buffer)
5. Move posted files to `Done/`
6. Update Dashboard with social posts section

**Key design patterns**:
- Draft generation uses template strings (service promotion, case study, thought leadership)
- Simulation mode: logs "POST SIMULATED" + moves to Done — zero config needed
- LinkedIn API mode: uses `LINKEDIN_ACCESS_TOKEN` from `.env`, posts via REST API
- Same approval detection pattern: poll `Approved/` directory for `LINKEDIN_*.md` files
- Dashboard update uses marker pattern: `<!-- START_SOCIAL_POSTS -->` / `<!-- END_SOCIAL_POSTS -->`

**Frontmatter schema** (draft):
```yaml
---
type: linkedin_post
topic: "AI Automation Services"
template: service_promotion|case_study|thought_leadership
platform: linkedin
status: draft
generated_at: "ISO8601"
---
```

**Frontmatter schema** (posted):
```yaml
---
type: linkedin_post
topic: "AI Automation Services"
template: service_promotion
platform: linkedin
status: posted
generated_at: "ISO8601"
approved_at: "ISO8601"
posted_at: "ISO8601"
post_mode: simulate|linkedin_api
---
```

### Dashboard Updates (`update_dashboard.py` modifications)

**Changes**:
1. Add `Approved` folder to Quick Status table
2. Add `<!-- START_SOCIAL_POSTS -->` / `<!-- END_SOCIAL_POSTS -->` section
3. New function: `build_social_posts_table(vault: Path) -> str`
   - Scans `Pending_Approval/`, `Approved/`, `Done/` for `LINKEDIN_*.md`
   - Shows last 10 posts with: title, date, status, platform
4. Add WhatsApp watcher to Quick Status description

### Existing Script Modifications

**`process_inbox.py`**: Add `whatsapp` to known types for action plan generation. No structural changes — the existing pipeline handles any `.md` file with frontmatter.

**`conftest.py`**: Add `Approved/` directory to vault fixture.

### Agent Skills

**`whatsapp-message-parser.md`**: Defines how Claude Code invokes WhatsApp message parsing. Input: message text + sender. Output: task file in `Needs_Action/`.

**`linkedin-poster.md`**: Defines how Claude Code invokes LinkedIn draft generation. Input: topic + template type. Output: draft file in `Pending_Approval/`.

## Environment Variables (new)

```bash
# WhatsApp Watcher (Silver Tier)
WHATSAPP_POLL_INTERVAL=30          # seconds between polls
WHATSAPP_SESSION_DIR=~/.ai_employee/whatsapp_session
WHATSAPP_KEYWORDS=urgent,invoice,payment,help,deadline,asap

# LinkedIn Poster (Silver Tier)
LINKEDIN_POST_MODE=simulate        # simulate | linkedin_api
LINKEDIN_ACCESS_TOKEN=             # Required only for linkedin_api mode
LINKEDIN_PERSON_URN=               # Required only for linkedin_api mode (urn:li:person:xxx)
```

## Dependency Changes

**New in `requirements.txt`**:
```
# Silver Tier — WhatsApp + LinkedIn
playwright>=1.40.0
requests>=2.31.0
```

**Post-install step**: `playwright install chromium` (one-time browser download).

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| WhatsApp DOM selectors break | Medium | High — watcher stops working | Externalize selectors, validate at startup, log clear errors |
| WhatsApp session expires during demo | Low | Medium — requires re-auth | Check session validity at startup, alert user proactively |
| LinkedIn API token expires | Low | Low — falls back to simulation | 60-day token lifetime, simulation mode is default |
| Playwright install fails on target machine | Low | High — no WhatsApp watcher | Document in quickstart, provide troubleshooting steps |
| 3 concurrent watchers cause resource contention | Low | Medium — missed events | Each watcher is independent, no shared state beyond ledgers |
