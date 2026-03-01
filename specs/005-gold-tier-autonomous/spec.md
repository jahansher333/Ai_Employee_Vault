# Feature Specification: Gold Tier — Autonomous Employee

**Feature Branch**: `005-gold-tier-autonomous`
**Created**: 2026-02-24
**Status**: Draft
**Input**: User description: "Gold Tier: Autonomous Employee with Odoo accounting, social integrations (Facebook, Instagram, Twitter/X), weekly audit, MCP servers, and advanced reasoning loop (Ralph Wiggum loop)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Odoo Accounting Integration (Priority: P1)

The CEO connects their self-hosted Odoo Community instance to the AI Employee. The system reads invoices, journal entries, and account balances from Odoo. During the weekly audit, the AI Employee pulls real financial data from Odoo instead of relying on CSV files, producing an accurate CEO briefing with revenue, expenses, outstanding invoices, and anomalies.

**Why this priority**: Odoo integration is the core Gold Tier differentiator. It transforms the AI Employee from a file-based assistant into a cross-domain business system that reads real accounting data. All other Gold features (weekly audit, CEO briefing) depend on this integration working.

**Independent Test**: Can be fully tested by configuring Odoo credentials, running the Odoo MCP server, and verifying that financial data (invoices, journal entries) flows into the vault and appears in Dashboard.md.

**Acceptance Scenarios**:

1. **Given** an Odoo instance with invoices and journal entries, **When** the AI Employee runs a financial sync, **Then** it creates a summary of outstanding invoices, revenue, and expenses in the vault.
2. **Given** Odoo credentials are configured, **When** the Odoo MCP server starts, **Then** Claude Code can query invoices, customers, and account balances via MCP tools.
3. **Given** Odoo is unreachable, **When** the AI Employee attempts a sync, **Then** it logs the error, falls back to CSV-based analysis, and alerts the CEO in the next briefing.

---

### User Story 2 — Social Media Posting (Facebook, Instagram, Twitter/X) (Priority: P1)

The CEO asks the AI Employee to post a business update across all social platforms. The system generates platform-appropriate drafts (character limits, hashtag styles, media requirements vary by platform), saves them to `Pending_Approval/` for human review, and publishes approved posts. After publishing, the AI generates a summary of recent social activity for the CEO briefing.

**Why this priority**: Social integrations (Facebook, Instagram, Twitter/X) are explicit Gold Tier requirements. They extend the existing LinkedIn posting pattern to three additional platforms, demonstrating cross-domain capability.

**Independent Test**: Can be tested by running `--draft` for each platform, approving the files, running `--publish`, and verifying posts appear in `Done/` with correct status and the Dashboard social section updates.

**Acceptance Scenarios**:

1. **Given** a topic, **When** the CEO requests a Facebook post draft, **Then** the system generates a draft with appropriate formatting and saves to `Pending_Approval/FACEBOOK_*.md`.
2. **Given** a topic, **When** the CEO requests an Instagram post draft, **Then** the system generates a caption-focused draft with hashtag suggestions and saves to `Pending_Approval/INSTAGRAM_*.md`.
3. **Given** a topic, **When** the CEO requests a Twitter/X post draft, **Then** the system generates a draft within 280 characters and saves to `Pending_Approval/TWITTER_*.md`.
4. **Given** an approved social post in `Approved/`, **When** the publish command runs, **Then** the post is published (or simulated), moved to `Done/`, and logged.
5. **Given** published posts across platforms, **When** the weekly briefing runs, **Then** it includes a social activity summary with post counts per platform.

---

### User Story 3 — Weekly Business and Accounting Audit (Priority: P1)

Every Sunday at 8 PM PKT, the AI Employee runs an enhanced weekly audit that combines Odoo financial data, task pipeline status, social media activity, error patterns, and bottleneck analysis into a comprehensive CEO briefing. The audit compares current week financials against previous periods, flags overdue invoices from Odoo, and recommends actions.

**Why this priority**: The weekly audit ties all Gold Tier integrations together into a single executive-level report, demonstrating full cross-domain intelligence.

**Independent Test**: Can be tested by running the audit manually and verifying the briefing contains Odoo financial data, social media summary, task pipeline, and comparison metrics.

**Acceptance Scenarios**:

1. **Given** Odoo data and social activity, **When** the weekly audit runs, **Then** it generates `Briefings/YYYY-MM-DD_Monday_Briefing.md` with sections for financials, social, tasks, and recommendations.
2. **Given** overdue invoices in Odoo, **When** the audit runs, **Then** it flags them as bottlenecks with customer names and amounts.
3. **Given** the previous week's briefing exists, **When** a new audit runs, **Then** it includes week-over-week comparison (revenue change, expense change, task velocity).

---

### User Story 4 — MCP Servers (Email, Social, Odoo) (Priority: P2)

Claude Code can directly interact with Gmail, social platforms, and Odoo through MCP servers. The CEO asks Claude "What invoices are overdue?" and Claude queries the Odoo MCP server in real time. The CEO asks "Post this update on Twitter" and Claude uses the social MCP server to draft and queue the post.

**Why this priority**: MCP servers are the mechanism that makes the AI Employee truly autonomous — Claude Code can read and act on external systems without running standalone scripts.

**Independent Test**: Can be tested by starting each MCP server and verifying Claude Code tools appear and return valid data.

**Acceptance Scenarios**:

1. **Given** the Odoo MCP server is running, **When** Claude Code calls `list_invoices`, **Then** it returns current invoice data from Odoo.
2. **Given** the social MCP server is running, **When** Claude Code calls `draft_social_post`, **Then** it generates platform-specific drafts.
3. **Given** the email MCP server is running, **When** Claude Code calls `fetch_unread_emails`, **Then** it returns current unread emails.
4. **Given** an MCP server loses connection, **When** Claude Code calls a tool, **Then** it receives a structured error with recovery suggestions.

---

### User Story 5 — Ralph Wiggum Loop (Autonomous Multi-Step Execution) (Priority: P2)

The AI Employee receives a complex cross-domain task (e.g., "Prepare month-end close: reconcile Odoo accounts, generate financial report, draft CEO update for LinkedIn, and schedule the briefing"). The Ralph Wiggum loop breaks this into steps, determines execution order with dependencies, executes each step autonomously (pulling from Odoo, generating reports, drafting posts), pauses for human approval on sensitive actions, and completes the plan.

**Why this priority**: The advanced reasoning loop demonstrates Gold Tier autonomy — the system handles multi-system, multi-step workflows without manual intervention at each step.

**Independent Test**: Can be tested by creating a multi-domain task and verifying the loop creates a plan with cross-domain steps, executes non-sensitive steps, and pauses for approval on sensitive ones.

**Acceptance Scenarios**:

1. **Given** a task requiring Odoo data + social posting, **When** the Ralph Wiggum loop processes it, **Then** it creates a plan with steps spanning multiple domains (accounting, social, reporting).
2. **Given** a plan with 5+ steps, **When** the loop executes, **Then** it respects step dependencies and executes in correct order.
3. **Given** a step fails (e.g., Odoo unreachable), **When** the loop encounters the failure, **Then** it logs the error, marks the step as failed, attempts a retry, and continues with independent steps.
4. **Given** a step requires approval (e.g., publishing a post, sending money), **When** the loop reaches it, **Then** it routes to `Pending_Approval/` and waits.

---

### User Story 6 — Error Recovery and Graceful Degradation (Priority: P2)

When any external system (Odoo, Facebook, Twitter, Gmail) is unavailable, the AI Employee continues functioning with reduced capabilities. It logs degraded state, skips unavailable integrations in the weekly audit, and alerts the CEO about which systems are down.

**Why this priority**: Production-grade autonomy requires the system to handle failures without crashing. This separates a demo from a usable tool.

**Independent Test**: Can be tested by starting the orchestrator with one or more services intentionally unavailable and verifying it continues running, logs warnings, and produces a partial briefing.

**Acceptance Scenarios**:

1. **Given** Odoo is unreachable, **When** the weekly audit runs, **Then** it skips Odoo financials, uses CSV fallback if available, and notes "Odoo unavailable" in the briefing.
2. **Given** Twitter API returns an error during publishing, **When** the social poster runs, **Then** it logs the error, marks the post as "failed", and does not move it to `Done/`.
3. **Given** the orchestrator is running and a watcher crashes, **When** the health check detects the crash, **Then** it logs the event and optionally restarts the component.

---

### User Story 7 — Architecture Documentation (Priority: P3)

The AI Employee generates documentation describing its architecture, integration patterns, and lessons learned. This is available as a markdown file in the vault and referenced from the README.

**Why this priority**: Documentation is a hackathon scoring requirement but does not affect functionality.

**Independent Test**: Can be tested by verifying the architecture document exists, covers all components, and is referenced from README.

**Acceptance Scenarios**:

1. **Given** the Gold Tier is complete, **When** the user opens `ARCHITECTURE.md`, **Then** it describes all components, integration patterns, data flows, and lessons learned.

---

### Edge Cases

- What happens when Odoo credentials are invalid? System MUST log a clear error and continue without Odoo data.
- What happens when a social platform API rate-limits the system? System MUST back off, log the rate limit, and retry after the cooldown period.
- What happens when a Ralph Wiggum loop plan has a circular dependency? System MUST detect and reject circular dependencies at plan creation time.
- What happens when two MCP servers try to write to the same vault file? System MUST use file-level coordination to prevent data corruption.
- What happens when the CEO briefing is generated with no data from any source? System MUST still generate a valid briefing with "no data available" messages.
- What happens when a social post exceeds a platform's character limit? System MUST truncate or reject at draft time, not at publish time.
- What happens when Odoo session expires mid-operation? System MUST re-authenticate automatically and retry the operation.

## Requirements *(mandatory)*

### Functional Requirements

**Odoo Accounting Integration**

- **FR-001**: System MUST connect to a self-hosted Odoo Community instance and read invoice data (customer, amount, due date, status).
- **FR-002**: System MUST read journal entries and account balances from Odoo for financial reporting.
- **FR-003**: System MUST detect overdue invoices (past due date with unpaid status) and flag them as bottlenecks.
- **FR-004**: System MUST fall back to CSV-based analysis when Odoo is unavailable, with a warning in the audit report.
- **FR-005**: System MUST store Odoo credentials securely (not in the vault, not committed to git).

**Social Media Integration**

- **FR-006**: System MUST generate Facebook post drafts with appropriate formatting (no character limit enforced, but optimized for engagement).
- **FR-007**: System MUST generate Instagram post drafts optimized as captions with hashtag suggestions.
- **FR-008**: System MUST generate Twitter/X post drafts within the 280-character limit.
- **FR-009**: System MUST save all social drafts to `Pending_Approval/` with platform-specific prefixes (`FACEBOOK_*.md`, `INSTAGRAM_*.md`, `TWITTER_*.md`).
- **FR-010**: System MUST support simulation mode (default) and real API mode for each social platform.
- **FR-011**: System MUST publish approved posts by moving from `Approved/` to `Done/` with full audit trail.
- **FR-012**: System MUST generate a social activity summary (posts per platform, engagement if available) for the weekly briefing.

**MCP Servers**

- **FR-013**: System MUST provide an Odoo MCP server with tools to query invoices, journal entries, account balances, and customers.
- **FR-014**: System MUST provide a social media MCP server with tools to draft, list, and publish posts across all platforms.
- **FR-015**: System MUST provide an email MCP server with tools to fetch, send, and reply to emails (extending Silver Tier).
- **FR-016**: Each MCP server MUST return structured error responses (not crash) when external services are unavailable.

**Weekly Audit Enhancement**

- **FR-017**: Weekly audit MUST include Odoo financial data (revenue, expenses, outstanding invoices, overdue amounts) when available.
- **FR-018**: Weekly audit MUST include social media activity summary across all platforms.
- **FR-019**: Weekly audit MUST include week-over-week comparison metrics (revenue change, expense change, task velocity) when prior briefing data exists.
- **FR-020**: Weekly audit MUST generate recommended actions prioritized by urgency and business impact.

**Ralph Wiggum Loop (Advanced Reasoning)**

- **FR-021**: System MUST detect cross-domain tasks (tasks that span accounting, social, email, or reporting domains).
- **FR-022**: System MUST create plans with domain-tagged steps indicating which external system each step interacts with.
- **FR-023**: System MUST execute plan steps autonomously, respecting dependencies and pausing for human approval on sensitive actions.
- **FR-024**: System MUST implement error recovery per step: log failure, retry once, continue with independent steps if retry fails.
- **FR-025**: System MUST track plan execution metrics (steps completed, time elapsed, retries, failures) for the audit.

**Error Recovery and Operational Resilience**

- **FR-026**: System MUST continue operating when any single external service is unavailable.
- **FR-027**: System MUST log all errors with context (service name, operation attempted, error details, timestamp).
- **FR-028**: Orchestrator MUST detect crashed components and optionally restart them (configurable).
- **FR-029**: System MUST include a health status section in the weekly briefing showing which services are operational.

**Documentation and Skills**

- **FR-030**: System MUST generate an `ARCHITECTURE.md` documenting all components, data flows, and integration patterns.
- **FR-031**: All new AI functionality MUST be implemented as reusable Agent Skills in `.claude/skills/`.
- **FR-032**: System MUST log every action to the audit trail, including cross-domain operations and MCP tool invocations.

### Key Entities

- **Invoice**: Represents an Odoo invoice with customer, amount, due date, payment status, and currency.
- **Social Post**: A platform-specific post draft with content, hashtags, platform identifier, status (draft/approved/posted/failed), and timestamps.
- **Audit Report**: A weekly briefing document combining financial, social, task, and operational data with recommendations.
- **Execution Plan**: A multi-step plan created by the Ralph Wiggum loop with domain-tagged steps, dependencies, approval gates, and execution status.
- **MCP Tool**: A callable function exposed via MCP server protocol that Claude Code can invoke to interact with external systems.
- **Health Status**: Per-service operational status (operational/degraded/unavailable) tracked by the orchestrator.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Odoo financial data appears in the weekly audit within 30 seconds of sync initiation.
- **SC-002**: Social post drafts for all 4 platforms (LinkedIn, Facebook, Instagram, Twitter) are generated within 10 seconds each.
- **SC-003**: The weekly audit includes data from at least 3 domains (accounting, social, tasks) when all services are available.
- **SC-004**: Ralph Wiggum loop completes a 5-step cross-domain plan within 2 minutes (excluding human approval wait time).
- **SC-005**: System continues operating for at least 24 hours with one external service intentionally unavailable.
- **SC-006**: All MCP servers respond to tool calls within 5 seconds under normal conditions.
- **SC-007**: 100% of external actions require human approval before execution (HITL compliance).
- **SC-008**: Weekly audit produces a briefing with week-over-week comparison when prior data exists.
- **SC-009**: At least 14 Agent Skills are defined (4 Bronze + 7 Silver + 3+ Gold).
- **SC-010**: Architecture document covers all components, is human-readable, and is referenced from README.
- **SC-011**: Full test suite passes with 250+ tests covering all tiers.
- **SC-012**: Error recovery handles at least 3 failure scenarios (Odoo down, social API error, MCP server crash) without data loss.

## Assumptions

- Odoo Community Edition 17.0+ is self-hosted and accessible from the machine running the AI Employee.
- Social platform APIs (Facebook Graph API, Instagram Graph API, Twitter/X API v2) require developer accounts; simulation mode is the default.
- The user has already completed Silver Tier setup (Gmail, WhatsApp, LinkedIn, reasoning loop, scheduling).
- MCP servers use stdio transport with the `fastmcp` library (already in requirements.txt).
- The Ralph Wiggum loop extends the existing reasoning loop rather than replacing it.
- Health monitoring uses the existing orchestrator's 10-second health check interval.
- Odoo authentication uses session-based login (JSON-RPC over HTTP).

## Scope

### In Scope

- Odoo Community integration via JSON-RPC (invoices, journal entries, accounts, customers)
- Facebook, Instagram, Twitter/X post drafting and publishing (simulation + real API)
- 3 MCP servers (email, social, Odoo) callable from Claude Code
- Enhanced weekly audit with Odoo data, social summary, and week-over-week comparison
- Ralph Wiggum loop for cross-domain autonomous task execution
- Error recovery and graceful degradation across all integrations
- Architecture documentation
- All functionality as Agent Skills

### Out of Scope

- Odoo write operations (creating invoices, recording payments) — read-only for safety
- Social media analytics/engagement metrics from platform APIs (only post counts tracked)
- Real-time notification systems (push notifications, webhooks)
- Multi-user support (single CEO/operator)
- Mobile app or web UI — vault-based interface only
- Odoo Enterprise features (only Community Edition)
- Video/image upload for social posts (text-only)

## Dependencies

- Silver Tier complete (Gmail watcher, WhatsApp watcher, LinkedIn poster, reasoning loop, weekly briefing, orchestrator, 233 tests passing)
- Odoo Community Edition instance accessible over HTTP
- Facebook/Instagram/Twitter developer accounts for real API mode (not needed for simulation)
- `fastmcp>=2.0.0` (already in requirements.txt)
