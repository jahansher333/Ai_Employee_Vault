# Implementation Plan: Platinum Tier — Always-On Cloud + Local Executive

**Branch**: `006-platinum-tier-cloud` | **Date**: 2026-03-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-platinum-tier-cloud/spec.md`

## Summary

Deploy the AI Employee to Oracle Cloud Free Tier for 24/7 operation with a Cloud/Local work-zone split. Cloud handles read-only and draft-creation tasks (email triage, social drafts, Odoo reads). Local handles sensitive operations (approvals, WhatsApp, payments, sending). Communication between zones uses a Git-synced Obsidian vault with structured domain folders and a claim-by-move protocol. Odoo Community runs on the cloud VM behind nginx/HTTPS. An optional Phase 2 adds direct A2A messaging between agents.

## Technical Context

**Language/Version**: Python 3.11+ (existing codebase)
**Primary Dependencies**: existing scripts (orchestrator, watchers, MCP servers), Docker/Docker Compose (Odoo), nginx, Certbot, Git, cron, systemd
**Storage**: File-based vault (Obsidian/Markdown), PostgreSQL 16 (Odoo database)
**Testing**: pytest (existing), bash integration tests for cloud deployment
**Target Platform**: Oracle Cloud Always Free ARM VM (Ubuntu 22.04, 1 OCPU, 6 GB RAM) + Windows 10 local
**Project Type**: Single project — scripts/ directory pattern continues
**Performance Goals**: Vault sync <2 min, health checks every 60s, Odoo responds in <5s, alerts within 5 min of failure
**Constraints**: Oracle Always Free limits (1 OCPU, 6 GB RAM, 50 GB disk, 10 Mbps), no local secrets on cloud
**Scale/Scope**: Single CEO user, ~50 emails/day, ~10 social drafts/week, 1 Odoo instance

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Clarity of Requirements | PASS | Spec has 30 FRs with RFC 2119 keywords, 14 SCs with measurable targets, Given/When/Then scenarios |
| II | Security and Sensitive Action Approval | PASS | FR-007/FR-009 enforce cloud cannot send/post; FR-016/FR-017/FR-018 enforce secret exclusion; all writes go through Local approval |
| III | Logging and Audit Records | PASS | FR-025 requires A2A audit logging; existing audit_logger.py continues; all sync operations logged |
| IV | Modular Code Organization | PASS | Zone config is a single module; cloud_health_monitor.py is independent; vault_sync.py is standalone; no circular deps |
| V | Readable Task and Plan Artifacts | PASS | This plan follows template structure; tasks.md will have phase boundaries |
| VI | Detection Only (Bronze constraint) | JUSTIFIED DEVIATION | Platinum Tier explicitly upgrades beyond Bronze: Cloud zone does draft-creation (not just detection), Local zone executes sends. This is the documented tier progression. The Cloud zone still follows the spirit by being read-only/draft-only — no autonomous external writes. |

## Project Structure

### Documentation (this feature)

```text
specs/006-platinum-tier-cloud/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── zone-config.yaml # Zone operation mapping
└── tasks.md             # Phase 2 output (/sp.tasks)
```

### Source Code (repository root)

```text
scripts/
├── orchestrator.py          # MODIFIED — add ZONE_MODE, cloud component list
├── cloud_health_monitor.py  # NEW — watchdog service for cloud components
├── vault_sync.py            # NEW — Git push/pull sync with conflict detection
├── zone_config.py           # NEW — zone enforcement (cloud vs local operation map)
├── claim_task.py            # NEW — claim-by-move protocol implementation
├── local_approval.py        # NEW — Local zone approval workflow (pick up cloud drafts)
├── a2a_server.py            # NEW — A2A webhook receiver (Phase 2)
├── a2a_client.py            # NEW — A2A webhook sender with vault fallback (Phase 2)
├── watcher.py               # EXISTING — no changes
├── gmail_watcher.py         # MODIFIED — respect ZONE_MODE (draft-only in cloud)
├── process_inbox.py         # EXISTING — no changes
├── social_poster.py         # MODIFIED — respect ZONE_MODE (draft-only in cloud)
├── mcp_odoo_server.py       # MODIFIED — read-only enforcement in cloud mode
├── mcp_email_server.py      # MODIFIED — draft-only enforcement in cloud mode
├── mcp_social_server.py     # MODIFIED — draft-only enforcement in cloud mode
├── error_recovery.py        # EXISTING — reused by cloud_health_monitor
├── update_dashboard.py      # MODIFIED — single-writer mode for cloud
├── audit_logger.py          # EXISTING — no changes
└── ...                      # All other existing scripts unchanged

deploy/
├── setup-vm.sh              # NEW — Oracle Cloud VM provisioning script
├── docker-compose.yml       # NEW — Odoo 17 + PostgreSQL 16
├── nginx/
│   ├── odoo.conf            # NEW — nginx reverse proxy config
│   └── ssl-renew.sh         # NEW — Certbot renewal cron helper
├── backup/
│   └── odoo-backup.sh       # NEW — pg_dump daily backup script
├── systemd/
│   ├── ai-employee.service  # NEW — systemd service for orchestrator
│   └── vault-sync.timer     # NEW — systemd timer for vault sync
├── sync/
│   ├── git-sync.sh          # NEW — Git push/pull sync script
│   └── syncthing-setup.sh   # NEW — Alternative Syncthing setup
└── .env.cloud.example       # NEW — Cloud-specific env template

tests/
├── test_platinum_tier_selftest.py  # NEW — Platinum tier self-test
├── test_zone_config.py             # NEW — Zone enforcement tests
├── test_vault_sync.py              # NEW — Vault sync tests
├── test_claim_task.py              # NEW — Claim-by-move tests
├── test_cloud_health.py            # NEW — Health monitor tests
└── test_a2a.py                     # NEW — A2A protocol tests (Phase 2)

Needs_Action/
├── EMAIL/           # NEW subdomain folder — cloud writes email triage here
├── SOCIAL/          # NEW subdomain folder — cloud writes social drafts here
└── ODOO/            # NEW subdomain folder — cloud writes Odoo triage here

Plans/
├── EMAIL/           # NEW — cloud writes email response plans
├── SOCIAL/          # NEW — cloud writes social campaign plans
└── ODOO/            # NEW — cloud writes accounting plans

Pending_Approval/
├── EMAIL/           # NEW — drafts awaiting CEO approval
├── SOCIAL/          # NEW — social post drafts awaiting approval
└── ODOO/            # NEW — Odoo write operations awaiting approval

In_Progress/
├── cloud/           # NEW — tasks claimed by cloud agent
└── local/           # NEW — tasks claimed by local agent

Updates/              # NEW — one-way Cloud→Local status channel
```

**Structure Decision**: Extends existing `scripts/` flat layout. New deployment infrastructure goes in `deploy/`. Domain-specific subfolders added to vault directories. No monorepo or package restructure needed.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Constitution Principle VI (Detection Only) | Platinum Tier is explicitly designed to go beyond Bronze detection-only. Cloud zone creates drafts; Local zone executes sends. This is the documented tier progression. | Staying detection-only would make Platinum impossible — the whole point is cloud automation + local execution. |
| Docker on VM | Odoo requires PostgreSQL + web server. Docker Compose bundles this cleanly. | Manual install of Odoo + PostgreSQL is error-prone on ARM and harder to maintain/backup. |

## Implementation Phases

### Phase 1: Zone Configuration + Vault Structure (Foundation)

**Goal**: Establish the Cloud/Local zone enforcement and domain folder structure.

**Deliverables**:
1. `scripts/zone_config.py` — Zone mode (`ZONE_MODE=cloud|local`), operation-to-zone mapping, enforcement decorator
2. `scripts/claim_task.py` — Claim-by-move protocol: atomic `os.rename()` to `/In_Progress/<agent>/`
3. Domain subfolders: `Needs_Action/<domain>/`, `Plans/<domain>/`, `Pending_Approval/<domain>/`, `In_Progress/<agent>/`, `Updates/`
4. Modify existing scripts to respect `ZONE_MODE`: orchestrator, gmail_watcher, social_poster, MCP servers
5. `scripts/update_dashboard.py` — Add single-writer mode (only writes when `ZONE_MODE=cloud`)
6. Tests: `test_zone_config.py`, `test_claim_task.py`

**Checkpoint**: Zone enforcement tests pass. Cloud mode blocks send/post. Claim-by-move works with concurrent attempts.

### Phase 2: Vault Sync Mechanism

**Goal**: Reliable Git-based sync between Cloud and Local with security exclusions.

**Deliverables**:
1. `scripts/vault_sync.py` — Python wrapper for Git sync (add, commit, pull --rebase, push) with conflict detection
2. `deploy/sync/git-sync.sh` — Bash script for cron-based sync every 2 minutes
3. `.gitignore` updates — Ensure `.env`, `credentials.json`, `token.json`, `*.session`, `__pycache__/` excluded
4. `.syncignore` — For Syncthing alternative (mirrors .gitignore exclusions)
5. `deploy/sync/syncthing-setup.sh` — Alternative setup script with documented steps
6. `deploy/systemd/vault-sync.timer` — systemd timer for automated sync on VM
7. Tests: `test_vault_sync.py` (sync, conflict detection, secret exclusion)

**Checkpoint**: File created on one side appears on the other within 2 minutes. `.env` files never sync. Conflicts are detected and logged.

### Phase 3: Cloud VM Deployment + Health Monitoring

**Goal**: Deploy orchestrator and watchers on Oracle Cloud VM with health monitoring and alerts.

**Deliverables**:
1. `deploy/setup-vm.sh` — Provision script: install Python 3.11, Docker, Git, nginx, certbot, create ai-employee user
2. `deploy/systemd/ai-employee.service` — systemd service for orchestrator (auto-start on boot)
3. `scripts/cloud_health_monitor.py` — Watchdog: check process liveness, HTTP endpoints, sync freshness; alert after 3 failures
4. `deploy/.env.cloud.example` — Cloud-specific env template (`ZONE_MODE=cloud`, cloud Odoo URL, no local secrets)
5. Modify `scripts/orchestrator.py` — Add `--zone cloud` flag, exclude Local-only components, integrate health monitor
6. Tests: `test_cloud_health.py` (simulated crashes, alert generation, restart verification)

**Checkpoint**: Orchestrator runs on VM with `ZONE_MODE=cloud`. Health monitor detects simulated crash, orchestrator restarts component within 60s, alert generated after 3 failures.

### Phase 4: Odoo Cloud Deployment

**Goal**: Deploy Odoo Community on the cloud VM, accessible via HTTPS, with backups and health monitoring.

**Deliverables**:
1. `deploy/docker-compose.yml` — Odoo 17.0 (ARM) + PostgreSQL 16, persistent volumes
2. `deploy/nginx/odoo.conf` — Reverse proxy: HTTPS termination, proxy to localhost:8069
3. `deploy/nginx/ssl-renew.sh` — Certbot auto-renewal helper
4. `deploy/backup/odoo-backup.sh` — `pg_dump` cron daily with 7-day retention
5. Modify `scripts/mcp_odoo_server.py` — Enforce read-only when `ZONE_MODE=cloud`; write ops create `/Pending_Approval/ODOO/` files
6. Tests: deployment smoke test (HTTP 200 on /web/health), backup existence check

**Checkpoint**: Odoo accessible at `https://<domain>/web`, HTTPS certificate valid, daily backup present, MCP reads invoices but write ops route to Pending_Approval.

### Phase 5: Local Approval Workflow

**Goal**: Local machine picks up Cloud-created drafts, presents for approval, executes on confirmation.

**Deliverables**:
1. `scripts/local_approval.py` — Scans `Pending_Approval/<domain>/` for drafts, presents to CEO, executes approved actions, moves to `Done/`
2. Integrate with existing scripts: email send (gmail_watcher), social publish (social_poster), Odoo writes (odoo_client)
3. Modify `scripts/orchestrator.py` — In `ZONE_MODE=local`, add local_approval as a managed component
4. Cloud writes `/Updates/` status messages; Local reads and merges into Dashboard
5. Tests: approval flow end-to-end (cloud creates draft → sync → local approves → execute → done)

**Checkpoint**: Cloud-created email draft in `Pending_Approval/EMAIL/` is picked up by Local, approved, sent, and moved to `Done/` with audit trail.

### Phase 6: A2A Upgrade (Phase 2 — Optional)

**Goal**: Direct agent-to-agent messaging between Cloud and Local, with vault audit trail and file-based fallback.

**Deliverables**:
1. `scripts/a2a_server.py` — HTTP webhook receiver on Local (Flask/FastAPI lightweight)
2. `scripts/a2a_client.py` — HTTP webhook sender on Cloud; fallback to vault file if POST fails
3. Vault audit: every A2A message also written to `/Updates/A2A_<timestamp>.md`
4. Modify orchestrator to optionally start A2A server/client based on `A2A_ENABLED=true`
5. Tests: `test_a2a.py` (send/receive, audit logging, fallback behavior)

**Checkpoint**: Cloud sends A2A message, Local receives within 5s, vault audit record created. On connection failure, falls back to file-based handoff within 30s.

### Phase 7: Platinum Demo + Self-Test

**Goal**: End-to-end demo script and comprehensive self-test proving all Platinum requirements.

**Deliverables**:
1. `scripts/platinum_demo.py` — Demo script: checks cloud deployment, vault sync, zone enforcement, Odoo HTTPS, health monitoring
2. `tests/test_platinum_tier_selftest.py` — Comprehensive self-test (all 30 FRs, 14 SCs)
3. Updated `ARCHITECTURE.md` — Add Platinum tier section
4. Updated `.env.example` — Add Platinum-specific variables

**Checkpoint**: `python scripts/platinum_demo.py` runs all checks, reports PASS/FAIL for each Platinum requirement. Self-test suite passes with all green.

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Oracle Cloud ARM incompatibility with Odoo Docker | Low | High | Odoo official Docker images support ARM since 16.0. Test with `docker run --platform linux/arm64 odoo:17` before full deploy. |
| Git sync conflicts from simultaneous writes | Medium | Medium | Claim-by-move prevents same-file edits. Dashboard.md is single-writer. Conflict detection with alert. |
| Free tier resource exhaustion (CPU/RAM) | Low | High | Monitor resource usage. Odoo + AI Employee fit in 6 GB. Add swap as safety valve. |

## ADR Candidates

The following decisions are architecturally significant and should be documented:

1. **Cloud/Local Zone Architecture** — The split between draft-only cloud and execute-only local is the core safety model. Impacts every component.
2. **Git as Primary Sync Mechanism** — Choosing Git over Syncthing for vault sync affects latency, conflict handling, and operational complexity.
3. **Claim-by-Move Protocol** — Using atomic file moves for task ownership is simpler than file locking but has implications for cross-filesystem operations.
