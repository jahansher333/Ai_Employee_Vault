# Feature Specification: Platinum Tier — Always-On Cloud + Local Executive

**Feature Branch**: `006-platinum-tier-cloud`
**Created**: 2026-03-01
**Status**: Draft
**Input**: User description: "Platinum Tier: Always-On Cloud + Local Executive — Cloud 24/7 + synced vault + Odoo cloud deploy + A2A upgrade"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Cloud 24/7 AI Employee (Priority: P1)

The CEO deploys the AI Employee to an Oracle Cloud Free Tier VM so it runs continuously without requiring a local machine to be powered on. The cloud instance runs the file watchers, orchestrator, and a health monitoring service 24/7. The CEO can check system health remotely and receives alerts if any component goes down.

**Why this priority**: Running 24/7 on the cloud is the core Platinum Tier differentiator. It transforms the AI Employee from a local tool that only works when the CEO's machine is on, into an always-available business assistant. All other Platinum features (vault sync, work-zone specialization) depend on the cloud deployment.

**Independent Test**: Can be fully tested by provisioning the Oracle Cloud VM, deploying the orchestrator, running all watchers for 24+ hours, and verifying health checks report all components alive.

**Acceptance Scenarios**:

1. **Given** an Oracle Cloud Free Tier VM is provisioned, **When** the deployment script runs, **Then** the orchestrator, all watchers, and health monitoring start successfully and report healthy status.
2. **Given** the cloud AI Employee is running, **When** a component crashes, **Then** the orchestrator auto-restarts it within 60 seconds and logs the restart event.
3. **Given** the cloud AI Employee is running for 24+ hours, **When** the CEO checks health status, **Then** all components show uptime metrics and no unrecovered failures.
4. **Given** the cloud AI Employee is running, **When** a health check fails 3 consecutive times, **Then** an alert is sent to the CEO (via email or vault notification).

---

### User Story 2 — Work-Zone Specialization: Cloud vs Local (Priority: P1)

The system splits responsibilities between Cloud and Local zones. The Cloud zone handles read-only and draft-creation work autonomously (email triage, draft composition, social media draft generation). The Local zone handles sensitive operations that require human proximity (approvals, WhatsApp interaction, payments, actual sending/posting). This ensures sensitive operations never execute on the cloud without explicit CEO involvement.

**Why this priority**: Work-zone specialization is what makes the Cloud deployment safe and trustworthy. Without clear zone boundaries, running on the cloud would risk unauthorized sends or payments. This is a safety-critical architectural requirement.

**Independent Test**: Can be tested by verifying that the cloud instance only performs draft/triage actions and never executes send, post, approve, or payment operations; and that the local instance correctly picks up pending items for approval and execution.

**Acceptance Scenarios**:

1. **Given** a new email arrives, **When** the Cloud AI Employee processes it, **Then** it triages the email (priority, category, summary) and saves a draft response to `/Needs_Action/EMAIL/` but does NOT send any reply.
2. **Given** the Cloud AI Employee drafts a social post, **When** the draft is complete, **Then** it saves to `/Pending_Approval/SOCIAL/` but does NOT publish to any platform.
3. **Given** the Local AI Employee starts, **When** it scans for pending approvals, **Then** it presents all cloud-created drafts (email replies, social posts) for CEO review and approval.
4. **Given** the CEO approves a draft on the Local machine, **When** the approval is confirmed, **Then** the Local AI Employee executes the send/post action and moves the item to `Done/`.
5. **Given** a WhatsApp message arrives, **When** the system processes it, **Then** only the Local AI Employee handles the interaction (Cloud never accesses WhatsApp).
6. **Given** a payment-related task is detected, **When** the system routes it, **Then** it is always routed to the Local zone for human approval and execution.

---

### User Story 3 — Delegation via Synced Vault (Phase 1) (Priority: P1)

The Cloud and Local AI Employees communicate through a synced Obsidian vault using a structured folder convention. The Cloud writes to designated folders; the Local merges and acts. A claim-by-move rule prevents both zones from working on the same task simultaneously. A single-writer `Dashboard.md` (owned by Cloud) provides a unified status view, while `/Updates/` serves as a one-way channel from Cloud to Local.

**Why this priority**: The synced vault is the communication backbone between Cloud and Local. Without it, the two zones cannot coordinate. This is the foundational mechanism that enables the entire Platinum architecture.

**Independent Test**: Can be tested by creating files in Cloud-zone folders, syncing them, verifying they appear on the Local side, confirming the claim-by-move rule prevents conflicts, and checking Dashboard.md reflects accurate status.

**Acceptance Scenarios**:

1. **Given** the Cloud AI Employee identifies a new action, **When** it creates a task file, **Then** the file is placed in `/Needs_Action/<domain>/` (e.g., `/Needs_Action/EMAIL/`, `/Needs_Action/SOCIAL/`).
2. **Given** the Cloud AI Employee creates a plan, **When** it saves the plan, **Then** it is placed in `/Plans/<domain>/` with a clear filename convention.
3. **Given** a task needs CEO approval, **When** the Cloud moves it, **Then** it goes to `/Pending_Approval/<domain>/` and the Local instance picks it up.
4. **Given** the Local AI Employee claims a task, **When** it moves the file out of `/Pending_Approval/`, **Then** the file is atomically moved (claim-by-move) and no other agent can claim it simultaneously.
5. **Given** the Cloud writes an update, **When** it saves status information, **Then** it writes to `/Updates/` and the Local AI Employee merges updates into its local state.
6. **Given** `Dashboard.md` is owned by Cloud (single-writer), **When** the Local AI Employee reads it, **Then** it sees the latest system status without write conflicts.

---

### User Story 4 — Vault Sync Mechanism (Priority: P1)

The vault syncs between Cloud and Local using either Git (push/pull) or Syncthing (real-time file sync). The sync mechanism ensures no secrets (`.env` files, API tokens, session files) are ever transmitted to or stored on the cloud. A `.syncignore` or `.gitignore` enforces security exclusions.

**Why this priority**: Without reliable sync, the Cloud and Local cannot communicate. Without security exclusions, sensitive credentials could leak to the cloud VM. This is both a functional requirement and a security-critical requirement.

**Independent Test**: Can be tested by creating a file locally, verifying it appears on the cloud after sync, creating a `.env` file locally, and verifying it does NOT appear on the cloud.

**Acceptance Scenarios**:

1. **Given** a file is created in the vault on the Cloud, **When** sync runs, **Then** the file appears on the Local machine within the sync interval.
2. **Given** a file is created in the vault on the Local machine, **When** sync runs, **Then** the file appears on the Cloud VM within the sync interval.
3. **Given** a `.env` file exists locally, **When** sync runs, **Then** the `.env` file is NOT synced to the Cloud VM.
4. **Given** token or session files exist locally, **When** sync runs, **Then** they are excluded from sync per the security exclusion list.
5. **Given** both Cloud and Local modify different files, **When** sync runs, **Then** both changes propagate without conflict.
6. **Given** both Cloud and Local modify the same file, **When** sync detects a conflict, **Then** it preserves both versions and alerts for manual resolution (no silent data loss).

---

### User Story 5 — Odoo Community Cloud Deployment (Priority: P2)

The CEO deploys Odoo Community Edition on the same Oracle Cloud Free Tier VM (or a separate one), accessible 24/7 over HTTPS. The cloud-deployed Odoo serves as the always-on accounting backend. Automated backups protect data. Health monitoring ensures Odoo stays available. A Cloud MCP server connects to cloud Odoo for draft-only read actions; actual posting (e.g., creating invoices, confirming payments) requires Local approval.

**Why this priority**: Running Odoo on the cloud makes accounting data available 24/7, enabling the Cloud AI Employee to triage invoices, generate reports, and prepare drafts even when the CEO's machine is off. However, all write operations go through Local approval.

**Independent Test**: Can be tested by deploying Odoo on the VM, accessing it via HTTPS, verifying backups complete successfully, and confirming the Cloud MCP can read invoices but cannot confirm payments without Local approval.

**Acceptance Scenarios**:

1. **Given** the deployment script runs on the Oracle Cloud VM, **When** Odoo Community installs, **Then** it is accessible via HTTPS with a valid certificate.
2. **Given** Odoo is running on the cloud, **When** the automated backup runs daily, **Then** a database backup is saved to a designated backup location.
3. **Given** Odoo health monitoring is active, **When** Odoo becomes unresponsive, **Then** an alert is generated and auto-restart is attempted.
4. **Given** the Cloud MCP connects to cloud Odoo, **When** it queries invoices or account balances, **Then** it returns data successfully (read-only operations).
5. **Given** a draft invoice is prepared by the Cloud AI Employee, **When** it requires confirmation or payment action, **Then** it is queued in `/Pending_Approval/ODOO/` for Local approval.

---

### User Story 6 — A2A Upgrade (Phase 2 — Optional) (Priority: P3)

In Phase 2, the file-based handoff between Cloud and Local is upgraded to direct Agent-to-Agent (A2A) messaging. Instead of writing files and waiting for sync, the Cloud agent sends structured messages directly to the Local agent. The vault continues to serve as an audit trail and fallback, but primary communication shifts to A2A for lower latency and richer coordination.

**Why this priority**: A2A is an optional upgrade that improves latency and coordination but is not required for Platinum to function. Phase 1 (vault-based) must work first. A2A is additive, not foundational.

**Independent Test**: Can be tested by sending an A2A message from Cloud to Local, verifying it arrives, confirming the vault also logs the message as an audit record, and verifying fallback to file-based handoff if A2A is unavailable.

**Acceptance Scenarios**:

1. **Given** A2A messaging is configured between Cloud and Local agents, **When** the Cloud agent sends a task message, **Then** the Local agent receives it within 5 seconds.
2. **Given** an A2A message is sent, **When** it is delivered, **Then** a copy is also written to the vault `/Updates/` folder as an audit trail.
3. **Given** A2A messaging is unavailable (network issue), **When** the Cloud agent attempts to send, **Then** it falls back to file-based vault handoff and logs the fallback.
4. **Given** Phase 1 (vault-based) is operational, **When** A2A is enabled, **Then** both mechanisms coexist and either can be used depending on availability.

---

### User Story 7 — Platinum Demo (Priority: P2)

The CEO runs a Platinum demo that showcases the full system: Cloud AI Employee running 24/7 on Oracle Cloud, vault syncing between Cloud and Local, work-zone specialization in action (Cloud drafts, Local approves), Odoo accessible via HTTPS on the cloud, and health monitoring showing all-green status. The demo proves the system operates autonomously in the cloud and safely defers sensitive operations to the local machine.

**Why this priority**: The demo is the tangible proof that all Platinum features work together. It validates the entire tier for the hackathon judges.

**Independent Test**: Can be tested by running the full demo script end-to-end and verifying each checkpoint produces the expected output.

**Acceptance Scenarios**:

1. **Given** the Platinum demo starts, **When** it checks cloud deployment, **Then** it confirms the orchestrator and watchers are running on Oracle Cloud VM.
2. **Given** the demo runs a vault sync test, **When** a file is created on the cloud, **Then** it appears locally within the sync window and vice versa.
3. **Given** the demo triggers an email triage on the cloud, **When** a draft response is created, **Then** it appears in `/Pending_Approval/EMAIL/` on the local machine.
4. **Given** the demo shows Odoo, **When** it queries invoices via HTTPS, **Then** real data is returned from the cloud-hosted Odoo instance.
5. **Given** the demo checks health monitoring, **When** all components are healthy, **Then** a green-status dashboard is displayed with uptime metrics.

---

### Edge Cases

- What happens when the Oracle Cloud VM runs out of free tier resources (CPU, memory, bandwidth)?
- How does the system handle vault sync conflicts when both Cloud and Local write to the same folder simultaneously?
- What happens when the Cloud VM loses internet connectivity mid-operation?
- How does the system recover if Odoo's database becomes corrupted and a backup restore is needed?
- What happens when the sync mechanism (Git or Syncthing) encounters a large file that exceeds transfer limits?
- How does the claim-by-move rule handle race conditions when both zones attempt to claim the same task at exactly the same time?
- What happens when the A2A channel is intermittently available (flapping connection)?

## Requirements *(mandatory)*

### Functional Requirements

**Cloud 24/7 Deployment**

- **FR-001**: System MUST run on an Oracle Cloud Free Tier VM continuously (24/7) with the orchestrator managing all watchers and services.
- **FR-002**: System MUST include a health monitoring service that checks all components at regular intervals and reports status.
- **FR-003**: System MUST auto-restart any crashed component within 60 seconds via the orchestrator.
- **FR-004**: System MUST send an alert (email notification or vault file) to the CEO when a component fails 3 consecutive health checks.
- **FR-005**: System MUST provide a deployment script that provisions and configures the Oracle Cloud VM with all required dependencies.

**Work-Zone Specialization**

- **FR-006**: Cloud zone MUST only perform read-only and draft-creation operations: email triage, email draft responses, social media draft generation.
- **FR-007**: Cloud zone MUST NOT execute any send, post, approve, or payment operations.
- **FR-008**: Local zone MUST handle all sensitive operations: approvals, WhatsApp interactions, payments, sending emails, publishing social posts.
- **FR-009**: System MUST enforce zone boundaries through configuration, not just convention — cloud-deployed code MUST lack the capability to perform Local-only operations.
- **FR-010**: System MUST route tasks to the correct zone based on operation type, with a clear mapping of operations to zones.

**Synced Vault (Phase 1 Delegation)**

- **FR-011**: Vault MUST use structured domain folders: `/Needs_Action/<domain>/`, `/Plans/<domain>/`, `/Pending_Approval/<domain>/`.
- **FR-012**: System MUST implement claim-by-move: when an agent claims a task, it atomically moves the file, preventing double-processing.
- **FR-013**: `Dashboard.md` MUST be single-writer (Cloud owns writes); Local reads only.
- **FR-014**: Cloud MUST write status updates to `/Updates/` folder; Local MUST merge updates from this folder.
- **FR-015**: System MUST support vault sync via Git (push/pull on schedule) or Syncthing (real-time file sync).

**Security**

- **FR-016**: Sync mechanism MUST exclude `.env` files, API tokens, session files, and any credential-bearing files from Cloud sync.
- **FR-017**: System MUST maintain a security exclusion list (`.syncignore` or `.gitignore`) that is validated on every sync cycle.
- **FR-018**: Cloud VM MUST NOT store any local secrets; it uses its own cloud-specific credentials (separate `.env`).

**Odoo Cloud Deployment**

- **FR-019**: System MUST deploy Odoo Community Edition on the Cloud VM, accessible via HTTPS with a valid TLS certificate.
- **FR-020**: System MUST run automated daily backups of the Odoo database.
- **FR-021**: System MUST monitor Odoo health and auto-restart if unresponsive.
- **FR-022**: Cloud MCP server MUST connect to cloud Odoo for read-only (draft) operations only.
- **FR-023**: Any Odoo write operation (create invoice, confirm payment) MUST be routed to `/Pending_Approval/ODOO/` for Local approval.

**A2A Upgrade (Phase 2 — Optional)**

- **FR-024**: System MUST support direct Agent-to-Agent messaging between Cloud and Local agents (when A2A is enabled).
- **FR-025**: Every A2A message MUST be logged to the vault (`/Updates/`) as an audit trail.
- **FR-026**: System MUST fall back to file-based vault handoff when A2A messaging is unavailable.
- **FR-027**: A2A and vault-based delegation MUST coexist; enabling A2A does not disable vault sync.

**Platinum Demo**

- **FR-028**: System MUST include a demo script that validates all Platinum requirements end-to-end.
- **FR-029**: Demo MUST verify: cloud deployment running, vault sync operational, work-zone specialization enforced, Odoo accessible via HTTPS, health monitoring all-green.
- **FR-030**: Demo MUST produce a summary report with pass/fail status for each Platinum checkpoint.

### Key Entities

- **Cloud Zone**: The Oracle Cloud VM instance running watchers, orchestrator, health monitor, and draft-creation services. Performs only read/draft operations.
- **Local Zone**: The CEO's local machine running approval workflows, WhatsApp integration, payment processing, and send/post execution. Handles all sensitive operations.
- **Synced Vault**: The Obsidian vault shared between Cloud and Local via Git or Syncthing. Contains structured domain folders and serves as the communication backbone.
- **Health Monitor**: A service that periodically checks all running components and reports status, sending alerts on failures.
- **Claim-by-Move**: An atomic file-move protocol that ensures only one agent processes a given task — moving the file out of a shared folder constitutes claiming it.
- **A2A Channel**: An optional direct messaging channel between Cloud and Local agents, replacing file-based handoffs with structured messages while maintaining vault-based audit.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All Gold Tier requirements continue to pass (23 existing test requirements remain green).
- **SC-002**: Cloud AI Employee runs continuously for 48+ hours on Oracle Cloud Free Tier VM without unrecovered failures.
- **SC-003**: Health monitoring detects a simulated component crash and the orchestrator restarts it within 60 seconds.
- **SC-004**: CEO receives an alert within 5 minutes when a component fails 3 consecutive health checks.
- **SC-005**: Cloud zone processes 50+ emails (triage + draft) without executing any send operation.
- **SC-006**: Local zone picks up and processes all Cloud-created drafts, approving or rejecting each within the standard workflow.
- **SC-007**: Vault sync propagates a file from Cloud to Local (or vice versa) within 2 minutes.
- **SC-008**: Zero secrets (`.env`, tokens, sessions) are found on the Cloud VM after a full sync cycle.
- **SC-009**: Odoo Community is accessible via HTTPS on the Cloud VM with a valid certificate, responding to health checks.
- **SC-010**: Odoo daily backup completes successfully and the backup file is retrievable.
- **SC-011**: Cloud MCP reads Odoo data (invoices, balances) without performing any write operations.
- **SC-012**: Platinum demo script runs end-to-end and reports all checkpoints as PASS.
- **SC-013**: (Optional, Phase 2) A2A message delivery latency is under 5 seconds between Cloud and Local agents.
- **SC-014**: (Optional, Phase 2) A2A fallback to vault-based handoff completes within 30 seconds of connection loss.

## Assumptions

- The CEO has access to an Oracle Cloud Free Tier account with sufficient resources (1 OCPU, 1 GB RAM minimum for the Always Free tier).
- The local machine and Cloud VM both have reliable internet connectivity for vault sync.
- Git is the default sync mechanism; Syncthing is offered as an alternative for users who prefer real-time sync over scheduled sync.
- Odoo Community Edition 17.0 is the target version for cloud deployment.
- The existing Gold Tier orchestrator and watcher architecture is reused and extended for cloud deployment — no rewrite of core components.
- HTTPS certificates are obtained via Let's Encrypt (free, automated).
- A2A (Phase 2) uses a lightweight protocol (e.g., HTTP-based webhook or WebSocket) — the specific protocol will be decided during planning.
- WhatsApp integration remains Local-only due to Playwright browser automation requiring a GUI session.
