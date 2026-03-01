# Feature Specification: Silver Tier Final Lock — WhatsApp Watcher + LinkedIn Post Skill

**Feature Branch**: `004-whatsapp-linkedin-silver`
**Created**: 2026-02-21
**Updated**: 2026-02-21
**Status**: Draft
**Input**: User description: "Silver Tier: Final Lock – Add WhatsApp Watcher + LinkedIn Post Skill"

## Silver Tier Completion Matrix

This feature completes all remaining Silver Tier requirements:

| Requirement | Status | Component |
|-------------|--------|-----------|
| 2+ Watcher scripts | Done: File System + Gmail. **Adding: WhatsApp** | watcher.py, gmail_watcher.py, **whatsapp_watcher.py** |
| Auto-post LinkedIn (with approval) | **New** | **linkedin_poster.py** |
| All AI as Agent Skills | Done: SimpleTaskReaderSkill, DataAnalyzerSkill. **Adding: WhatsAppMessageParserSkill, LinkedInPostSkill** | .claude/skills/ |
| Human-in-the-loop approval | Done | Pending_Approval/ workflow |
| Basic scheduling | Done | Watcher intervals, poll cycles |
| Dashboard analytics | Done | Dashboard.md with analytics |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - WhatsApp Urgent Message Detection (Priority: P1)

As a business owner, I want to be notified when urgent WhatsApp messages arrive so that I can respond to time-sensitive client requests without constantly monitoring my phone.

The system monitors WhatsApp Web for unread messages containing priority keywords (urgent, invoice, payment, help, deadline, ASAP). When detected, the **WhatsAppMessageParserSkill** creates a task file in `Needs_Action/` with the sender name, message text, timestamp, and priority level. The AI Employee then processes it through the existing inbox pipeline (process_inbox.py).

**Why this priority**: Urgent client messages are the highest-value notifications — missed messages directly impact revenue and client satisfaction.

**Independent Test**: Can be tested by sending a WhatsApp message containing "urgent" to the monitored number and verifying a `WHATSAPP_*.md` file appears in `Needs_Action/` within one polling cycle.

**Acceptance Scenarios**:

1. **Given** WhatsApp Web is authenticated and the watcher is running, **When** an unread message arrives containing "urgent", **Then** a task file `WHATSAPP_{HHMMSS}_{sender}.md` is created in `Needs_Action/` with sender, message text, time, and priority "high".
2. **Given** the watcher is running, **When** a regular message arrives without keywords, **Then** no task file is created (only keyword-matched messages are captured).
3. **Given** the watcher has already processed a message, **When** the same message is seen again on next poll, **Then** it is not duplicated (ledger deduplication).

---

### User Story 2 - LinkedIn Sales Post Drafting (Priority: P1)

As a business owner, I want the AI Employee to draft LinkedIn posts promoting my services so that I can maintain a consistent social media presence and generate sales leads.

The **LinkedInPostSkill** generates a professional LinkedIn post draft based on configurable templates (service promotion, case study, thought leadership). The draft is saved as `LINKEDIN_{timestamp}_{topic}.md` in `Pending_Approval/` for human review before posting. No post is published without explicit human approval.

**Why this priority**: Social media presence directly drives sales leads. Automated drafting saves significant time while maintaining the human-in-the-loop safety.

**Independent Test**: Can be tested by running the LinkedInPostSkill with a topic like "New AI automation service" and verifying a draft appears in `Pending_Approval/LINKEDIN_*.md` with proper formatting.

**Acceptance Scenarios**:

1. **Given** the LinkedInPostSkill is invoked with a topic, **When** the draft is generated, **Then** a `LINKEDIN_*.md` file appears in `Pending_Approval/` with the post content, hashtags, and metadata.
2. **Given** a draft exists in `Pending_Approval/`, **When** the user moves it to `Approved/`, **Then** the system detects the approval and posts via the posting mechanism (simulated or real).
3. **Given** a draft is rejected (deleted or moved to `Done/`), **Then** no posting occurs and the rejection is logged.

---

### User Story 3 - LinkedIn Post Approval & Automated Posting (Priority: P2)

As a business owner, I want approved LinkedIn post drafts to be automatically posted so that I only need to review and approve, not manually copy-paste to LinkedIn.

After the user approves a draft by moving it from `Pending_Approval/` to `Approved/`, the system detects the approval and posts to LinkedIn. The system supports both simulated posting (logging only) and real posting (via browser automation or API). The Dashboard is updated with a "Recent Social Posts" section showing post status.

**Why this priority**: Automates the final step of the posting workflow. Real posting capability makes the Silver Tier demo-ready for the hackathon.

**Independent Test**: Can be tested by placing a `LINKEDIN_*.md` in `Approved/`, running the approval watcher, and verifying the post is logged as "posted" and appears on the Dashboard.

**Acceptance Scenarios**:

1. **Given** a `LINKEDIN_*.md` file is in `Approved/`, **When** the approval watcher runs, **Then** the post is published (or simulated) and the file is moved to `Done/`.
2. **Given** a post is completed, **Then** the Dashboard "Recent Social Posts" section shows the post title, date, and status.
3. **Given** LinkedIn credentials are not configured, **Then** posting falls back to simulation mode with a logged warning.

---

### User Story 4 - WhatsApp Session Management (Priority: P2)

As a user, I want a simple one-time setup for WhatsApp Web authentication so that the watcher can run unattended after initial login.

The first run opens a browser window for QR code scanning. After authentication, the session is persisted in a secure directory outside the vault. Subsequent runs reuse the saved session without re-authentication. If the session expires, the system alerts the user to re-authenticate.

**Why this priority**: Session management is essential for the watcher to run reliably, but only needs to work once after setup.

**Independent Test**: Can be tested by running the watcher with `--setup` to authenticate, then restarting the watcher and verifying it connects without prompting for QR code.

**Acceptance Scenarios**:

1. **Given** no existing session, **When** the watcher starts with `--setup`, **Then** a browser window opens for QR code scanning and the session is saved.
2. **Given** a valid saved session exists, **When** the watcher starts, **Then** it connects automatically without user interaction.
3. **Given** the session has expired, **When** the watcher starts, **Then** it logs an error and prompts the user to re-authenticate.

---

### User Story 5 - Dashboard Social Posts & Watcher Status (Priority: P3)

As a user, I want to see recent LinkedIn post activity and all watcher statuses on the Dashboard so that I can track everything at a glance.

The Dashboard is updated with a "Recent Social Posts" section showing the last 10 posts with their title, date, status (draft/approved/posted), and platform. The Quick Status section reflects all 3 watchers.

**Why this priority**: Visibility into social posting activity is valuable but not blocking for core functionality.

**Independent Test**: Can be tested by creating sample LinkedIn post files in various states and running the dashboard update to verify the section appears correctly.

**Acceptance Scenarios**:

1. **Given** LinkedIn post files exist in various folders, **When** the Dashboard is updated, **Then** the "Recent Social Posts" section shows posts with correct status.

---

### User Story 6 - End-to-End Silver Tier Test Flow (Priority: P1)

As a hackathon judge, I want to see the complete Silver Tier flow demonstrated end-to-end to verify all requirements are met.

The test flow: (1) WhatsApp message with "urgent invoice" arrives → (2) WhatsApp watcher creates `WHATSAPP_*.md` in `Needs_Action/` → (3) process_inbox.py reads and processes → (4) LinkedInPostSkill generates a business post draft about services → (5) Draft appears in `Pending_Approval/LINKEDIN_*.md` → (6) User approves by moving to `Approved/` → (7) Post is published (or simulated) → (8) File moves to `Done/` → (9) Dashboard updates with all activity.

**Why this priority**: Demonstrates the complete Silver Tier value chain for hackathon evaluation.

**Independent Test**: Run the full flow with a test WhatsApp message and verify each step produces the expected output.

**Acceptance Scenarios**:

1. **Given** all 3 watchers are running, **When** an urgent WhatsApp message arrives, **Then** the full pipeline executes and the Dashboard reflects all activity within 2 minutes.

---

### Edge Cases

- What happens when WhatsApp Web disconnects mid-session? System logs the disconnection and retries on the next poll cycle.
- What happens when a WhatsApp message contains only emojis or media (no text)? System ignores messages without text content matching keywords.
- What happens when the same urgent keyword appears in a group chat? System processes group messages the same as individual messages, noting the group name as sender context.
- What happens when LinkedIn draft generation fails (no topic provided)? System logs an error and does not create a partial draft file.
- What happens when multiple messages arrive between polls? All qualifying messages are processed and individual task files are created for each.
- What happens when the Approved/ folder contains non-LinkedIn files? System only processes files matching the `LINKEDIN_*.md` pattern.
- What happens when WhatsApp session storage directory is not writable? System logs an error at startup and exits with a clear message.
- What happens when a message matches multiple keywords? System creates one task file with all matched keywords listed.
- What happens when LinkedIn posting fails (network error)? System retains the file in `Approved/` and logs the error for retry.

## Requirements *(mandatory)*

### Functional Requirements

**WhatsApp Watcher (whatsapp_watcher.py + WhatsAppMessageParserSkill):**

- **FR-001**: System MUST monitor WhatsApp Web for unread messages at a configurable interval (default: 30 seconds).
- **FR-002**: System MUST detect messages containing priority keywords: "urgent", "invoice", "payment", "help", "deadline", "ASAP" (case-insensitive).
- **FR-003**: System MUST create a Markdown task file in `Needs_Action/` for each keyword-matched message with: sender name, message text, timestamp, priority level, matched keywords, and source "whatsapp".
- **FR-004**: System MUST deduplicate messages using a persistent ledger (same pattern as Gmail watcher).
- **FR-005**: System MUST store session data in a secure directory outside the vault (default: `~/.ai_employee/whatsapp_session/`).
- **FR-006**: System MUST support a `--setup` mode for initial QR code authentication.
- **FR-007**: System MUST log all events (message detected, session error, poll cycle) to the audit log.
- **FR-008**: System MUST run in headless mode after initial setup (no visible browser window).

**LinkedIn Auto-Post (linkedin_poster.py + LinkedInPostSkill):**

- **FR-009**: System MUST generate LinkedIn post drafts from a topic/prompt input via the LinkedInPostSkill.
- **FR-010**: System MUST save drafts as `LINKEDIN_{HHMMSS}_{topic}.md` in `Pending_Approval/` with frontmatter (type, topic, platform, status, generated_at).
- **FR-011**: System MUST detect approved posts (files moved to `Approved/` folder) and execute posting (real or simulated).
- **FR-012**: System MUST move posted files to `Done/` after successful posting.
- **FR-013**: System MUST update Dashboard.md with a "Recent Social Posts" section between markers.
- **FR-014**: System MUST support multiple post templates: service promotion, case study highlight, thought leadership tip.
- **FR-015**: System MUST NOT post to any external platform without explicit human approval (HITL requirement per constitution).
- **FR-016**: System MUST gracefully fall back to simulation mode when LinkedIn credentials are not configured.

**Agent Skills:**

- **FR-017**: WhatsAppMessageParserSkill MUST be defined in `.claude/skills/whatsapp-message-parser.md` with clear invocation instructions.
- **FR-018**: LinkedInPostSkill MUST be defined in `.claude/skills/linkedin-poster.md` with topic input and template selection.

**Integration:**

- **FR-019**: Both features MUST integrate with the existing audit logger, process_inbox pipeline, and Dashboard.
- **FR-020**: System MUST update README.md with setup instructions for WhatsApp watcher and LinkedIn posting.
- **FR-021**: System MUST support running all 3 watchers concurrently (file system + Gmail + WhatsApp).

### Key Entities

- **WhatsApp Message**: Sender name, message text, timestamp, chat type (individual/group), matched keywords, priority level.
- **LinkedIn Post Draft**: Topic, post body, hashtags, template type, platform, status (draft/approved/posted/rejected), timestamps.
- **Approved Post**: Post content, approval timestamp, posting result, destination.
- **Agent Skill Definition**: Skill name, description, trigger, input parameters, output format.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Urgent WhatsApp messages are detected and task files created within 60 seconds of message arrival.
- **SC-002**: 100% of keyword-matched messages generate task files (zero missed urgent messages during active monitoring).
- **SC-003**: WhatsApp session persists across watcher restarts without requiring re-authentication (until session naturally expires).
- **SC-004**: LinkedIn post drafts are generated within 5 seconds of topic input.
- **SC-005**: No LinkedIn post is published without the user explicitly moving the draft to the Approved folder (100% HITL compliance).
- **SC-006**: Dashboard "Recent Social Posts" section accurately reflects the current state of all post drafts.
- **SC-007**: System operates with 3 concurrent watchers (file system + Gmail + WhatsApp) without conflicts.
- **SC-008**: All WhatsApp and LinkedIn events are captured in the audit log with full traceability.
- **SC-009**: Zero sensitive data (session tokens, credentials) stored in the vault directory.
- **SC-010**: README provides complete setup instructions that a new user can follow to configure both features in under 10 minutes.
- **SC-011**: End-to-end test flow (WhatsApp message → task file → LinkedIn draft → approval → post → Done) completes within 2 minutes.
- **SC-012**: All AI functionality is accessible as named Agent Skills (minimum 4 skills total across Bronze + Silver).

## Assumptions

- WhatsApp Web maintains an active session for at least 24 hours before requiring re-authentication.
- The user has a WhatsApp account linked to a phone with active internet connection.
- The system runs on a machine with a display server available for initial WhatsApp QR code setup (headless mode used after setup).
- Keywords for WhatsApp filtering are English-language; multi-language support is out of scope.
- Group chat messages are treated the same as individual messages for keyword detection.
- LinkedIn credentials (if provided) use session-based browser authentication or API tokens stored in `.env`.
- Existing Silver Tier components are working: file watcher, Gmail watcher, process_inbox, data_analyzer, audit_logger, Dashboard.

## Out of Scope

- Replying to WhatsApp messages automatically (HITL principle — detection only).
- WhatsApp media file processing (images, voice notes, documents).
- LinkedIn analytics or engagement tracking.
- Multi-account support for either WhatsApp or LinkedIn.
- Scheduling posts for specific times (all posting is immediate upon approval).
- Gold Tier features (calendar integration, CRM, advanced scheduling).
