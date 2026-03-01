# Data Model: Silver Tier Final Lock — WhatsApp Watcher + LinkedIn Post Skill

**Feature**: 004-whatsapp-linkedin-silver
**Date**: 2026-02-22

## Entities

### 1. WhatsAppMessage

**Source**: WhatsApp Web DOM scraping via Playwright
**Storage**: Markdown file in `Needs_Action/WHATSAPP_{HHMMSS}_{sender}.md`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | string | Yes | Always `"whatsapp"` |
| from | string | Yes | Sender display name |
| message | string | Yes | Message text (first 200 chars) |
| date | string (ISO8601) | Yes | Message timestamp |
| priority | enum: high, medium | Yes | `high` if keywords matched, `medium` otherwise |
| matched_keywords | list[string] | Yes | Keywords found in message (e.g., `["urgent", "invoice"]`) |
| chat_type | enum: individual, group | Yes | Whether message is from 1:1 or group chat |
| group_name | string | No | Group name if `chat_type == "group"` |
| status | enum: new, planned, done | Yes | Processing status (starts `new`) |
| processed_at | string (ISO8601) | No | Set by process_inbox.py |
| completed_at | string (ISO8601) | No | Set when moved to Done/ |

**Deduplication key**: SHA-256 hash of `f"{sender}|{timestamp}|{message_text[:50]}"` stored in `Logs/.whatsapp_ledger.txt`.

**File naming**: `WHATSAPP_{HHMMSS}_{sanitized_sender}.md` where:
- `HHMMSS` = time component from message timestamp
- `sanitized_sender` = sender name with non-alphanumeric chars replaced by `-`, max 50 chars

**Example file**:
```yaml
---
type: whatsapp
from: "Ahmed Client"
message: "Urgent - need the invoice for Project X by EOD"
date: "2026-02-22T14:30:00+05:00"
priority: high
matched_keywords: ["urgent", "invoice"]
chat_type: individual
status: new
---

# WhatsApp Message from Ahmed Client

**From**: Ahmed Client
**Time**: 2026-02-22T14:30:00+05:00
**Chat**: Individual
**Priority**: HIGH (matched: urgent, invoice)

## Message

Urgent - need the invoice for Project X by EOD

## Action Plan

*Pending processing by AI Employee*
```

---

### 2. LinkedInPostDraft

**Source**: LinkedInPostSkill template generation
**Storage**: Markdown file, lifecycle across three folders:
- `Pending_Approval/LINKEDIN_{HHMMSS}_{topic}.md` (draft)
- `Approved/LINKEDIN_{HHMMSS}_{topic}.md` (approved by user)
- `Done/LINKEDIN_{HHMMSS}_{topic}.md` (posted or rejected)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | string | Yes | Always `"linkedin_post"` |
| topic | string | Yes | Post topic/subject |
| template | enum: service_promotion, case_study, thought_leadership | Yes | Template used for generation |
| platform | string | Yes | Always `"linkedin"` |
| status | enum: draft, approved, posted, rejected | Yes | Current lifecycle stage |
| generated_at | string (ISO8601) | Yes | When draft was created |
| approved_at | string (ISO8601) | No | When user moved to Approved/ |
| posted_at | string (ISO8601) | No | When post was published/simulated |
| post_mode | enum: simulate, linkedin_api | No | How the post was published |
| hashtags | list[string] | Yes | Generated hashtags |

**File naming**: `LINKEDIN_{HHMMSS}_{sanitized_topic}.md` where:
- `HHMMSS` = time component from generation timestamp
- `sanitized_topic` = topic with non-alphanumeric chars replaced by `-`, max 50 chars

**Example file** (draft state):
```yaml
---
type: linkedin_post
topic: "AI Automation for Small Businesses"
template: service_promotion
platform: linkedin
status: draft
generated_at: "2026-02-22T15:00:00+05:00"
hashtags: ["AIAutomation", "SmallBusiness", "Productivity", "DigitalTransformation"]
---

# LinkedIn Post Draft: AI Automation for Small Businesses

## Post Content

Are you still spending hours on tasks that could take minutes?

Small businesses waste an average of 23 hours per week on repetitive admin work.
Here's how AI automation is changing the game:

- Automated email triage and prioritization
- Instant document processing and filing
- Smart scheduling and follow-up reminders

The best part? You stay in control. Every action requires your approval.

Ready to reclaim your time? Let's talk about what automation can do for your business.

#AIAutomation #SmallBusiness #Productivity #DigitalTransformation
```

---

### 3. WhatsAppSession (runtime, not file-based)

**Source**: Playwright persistent browser context
**Storage**: `~/.ai_employee/whatsapp_session/` directory (browser profile)

| Field | Type | Description |
|-------|------|-------------|
| user_data_dir | Path | Playwright persistent context storage location |
| authenticated | bool | Whether QR code has been scanned and session is active |
| last_connected | datetime | Last successful connection to WhatsApp Web |
| headless | bool | Whether browser runs without visible window |

**Not stored in vault** — this is Playwright's internal browser state directory.

---

### 4. WhatsAppLedger

**Storage**: `Logs/.whatsapp_ledger.txt`
**Format**: One dedup hash per line (same pattern as `.watcher_ledger.txt` and `.gmail_ledger.txt`)

---

### 5. PostTemplate (code constant, not file-based)

**Storage**: Defined in `linkedin_poster.py` as Python dict constants

| Field | Type | Description |
|-------|------|-------------|
| name | string | Template identifier |
| structure | string | Template string with `{topic}`, `{hook}`, `{body}`, `{cta}` placeholders |
| tone | string | Writing tone guidance |
| hashtag_count | int | Number of hashtags to generate |
| word_range | tuple[int, int] | Target word count (min, max) |

## State Transitions

### WhatsApp Message Lifecycle
```
[WhatsApp Web] → detected by watcher → WHATSAPP_*.md created in Needs_Action/ (status: new)
  → process_inbox.py processes → (status: planned)
  → user moves to Done/ → (status: done)

  If sensitive keywords detected:
  → routed to Pending_Approval/ → user approves/rejects → Done/
```

### LinkedIn Post Lifecycle
```
[Topic input] → LinkedInPostSkill generates draft
  → LINKEDIN_*.md in Pending_Approval/ (status: draft)
  → User moves to Approved/ (status: approved, approved_at set)
  → linkedin_poster.py detects approval
  → Posts (simulate or API) (status: posted, posted_at set, post_mode set)
  → File moved to Done/

  If user deletes or moves to Done/ directly:
  → (status: rejected) → no posting occurs
```

## Relationships

```
WhatsAppMessage ──creates──▶ TaskFile (Needs_Action/)
                              │
                              ▼
                         process_inbox.py
                              │
                              ▼
                         Dashboard.md (Pending Tasks table)

LinkedInPostDraft ──saved to──▶ Pending_Approval/
                                    │
                              (user moves)
                                    │
                                    ▼
                              Approved/
                                    │
                              (system posts)
                                    │
                                    ▼
                              Done/ + Dashboard.md (Social Posts table)

AuditLogger ◀──logs──── WhatsAppWatcher
            ◀──logs──── LinkedInPoster
            ◀──logs──── All existing scripts
```
