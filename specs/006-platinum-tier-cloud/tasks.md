# Tasks: Platinum Tier — Always-On Cloud + Local Executive

**Input**: Design documents from `/specs/006-platinum-tier-cloud/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/zone-config.yaml

**Organization**: Tasks grouped by user story. Each story is independently testable. Tests included per phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1–US7)
- All paths relative to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create vault domain folder structure and cloud deployment skeleton

- [ ] T001 [P] Create domain subfolders: `Needs_Action/EMAIL/`, `Needs_Action/SOCIAL/`, `Needs_Action/ODOO/` with `.gitkeep` files
- [ ] T002 [P] Create domain subfolders: `Plans/EMAIL/`, `Plans/SOCIAL/`, `Plans/ODOO/` with `.gitkeep` files
- [ ] T003 [P] Create domain subfolders: `Pending_Approval/EMAIL/`, `Pending_Approval/SOCIAL/`, `Pending_Approval/ODOO/` with `.gitkeep` files
- [ ] T004 [P] Create agent folders: `In_Progress/cloud/`, `In_Progress/local/` with `.gitkeep` files
- [ ] T005 [P] Create status channel folder: `Updates/` with `.gitkeep` file
- [ ] T006 [P] Create deployment skeleton: `deploy/`, `deploy/nginx/`, `deploy/backup/`, `deploy/systemd/`, `deploy/sync/` directories
- [ ] T007 Update `.gitignore` to add: `*.session`, `deploy/.env`, `In_Progress/` content (keep `.gitkeep`), and validate existing `.env`/`credentials.json`/`token.json` exclusions in `.gitignore`
- [ ] T008 Create `deploy/.env.cloud.example` with all Platinum cloud env vars (`ZONE_MODE=cloud`, `VAULT_PATH`, `HEALTH_CHECK_INTERVAL`, `SYNC_METHOD`, `SYNC_INTERVAL`, `A2A_ENABLED=false`) per `specs/006-platinum-tier-cloud/quickstart.md`

**Checkpoint**: All domain folders exist. Deployment skeleton created. `.gitignore` validated.

---

## Phase 2: Foundational — Zone Config + Claim-by-Move (Blocking Prerequisites) [P1]

**Purpose**: Core zone enforcement and task-claiming protocol that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T009 [P1] Create `scripts/zone_config.py` — `ZoneConfig` class: reads `ZONE_MODE` env var (`cloud`|`local`), loads operation-to-zone mapping from `contracts/zone-config.yaml` or inline defaults, exposes `is_allowed(operation)` method, `@zone_required(operation)` decorator that raises `ZoneViolationError` if operation not allowed in current zone, `get_components()` returns components list for current zone
- [ ] T010 [P1] Create `scripts/claim_task.py` — `claim_task(file_path, agent_id)` function: atomic `os.rename()` from source to `In_Progress/<agent_id>/<filename>`, returns `True` on success, catches `FileNotFoundError`/`OSError` and returns `False` (another agent claimed it), `complete_task(file_path)` moves from `In_Progress/` to `Done/`, `list_pending(domain)` lists files in `Pending_Approval/<domain>/`
- [ ] T011 [P1] Create `tests/test_zone_config.py` — test cloud mode blocks send/post/approve, test local mode allows send/post, test decorator raises `ZoneViolationError`, test `get_components()` returns correct list per zone, test missing `ZONE_MODE` defaults to `local`
- [ ] T012 [P1] Create `tests/test_claim_task.py` — test successful claim moves file, test double-claim returns False for second agent, test `complete_task` moves to `Done/`, test `list_pending` returns correct files, test claim on non-existent file returns False

**Checkpoint**: `pytest tests/test_zone_config.py tests/test_claim_task.py` passes. Zone enforcement blocks cloud send operations. Claim-by-move works atomically.

---

## Phase 3: User Story 2 — Work-Zone Specialization (Priority: P1)

**Goal**: Modify existing scripts to respect `ZONE_MODE` — cloud only drafts, local only executes

**Independent Test**: Run orchestrator with `ZONE_MODE=cloud` and verify send/post operations are blocked; run with `ZONE_MODE=local` and verify approval workflows activate

### Implementation

- [ ] T013 [P] [US2] Modify `scripts/orchestrator.py` — add `--zone` CLI flag (reads `ZONE_MODE` env if not passed), filter `build_component_list()` to only include components allowed in current zone per `zone_config.get_components()`, add health monitor component when `ZONE_MODE=cloud`
- [ ] T014 [P] [US2] Modify `scripts/gmail_watcher.py` — import `zone_config`, wrap `send_email()` calls with `@zone_required("email_send")` decorator, in cloud mode: triage emails and write drafts to `Needs_Action/EMAIL/` but skip all send operations
- [ ] T015 [P] [US2] Modify `scripts/social_poster.py` — import `zone_config`, wrap `publish_post()` with `@zone_required("social_publish")`, in cloud mode: generate drafts to `Pending_Approval/SOCIAL/` but skip all publish operations
- [ ] T016 [P] [US2] Modify `scripts/mcp_odoo_server.py` — import `zone_config`, wrap write tools (`create_invoice`, `confirm_payment`) with `@zone_required("odoo_write")`, in cloud mode: read-only operations succeed, write operations save draft to `Pending_Approval/ODOO/` and return "queued for local approval"
- [ ] T017 [P] [US2] Modify `scripts/mcp_email_server.py` — import `zone_config`, wrap `send_email` tool with `@zone_required("email_send")`, in cloud mode: `fetch_unread_emails` works, `send_email` returns "queued for local approval" and writes draft to `Pending_Approval/EMAIL/`
- [ ] T018 [P] [US2] Modify `scripts/mcp_social_server.py` — import `zone_config`, wrap `publish_approved_posts` tool with `@zone_required("social_publish")`, in cloud mode: `draft_social_post` works, publish returns "queued for local approval"
- [ ] T019 [US2] Modify `scripts/update_dashboard.py` — add single-writer mode: only write `Dashboard.md` when `ZONE_MODE=cloud`, in local mode read only and skip write operations

**Checkpoint**: `python scripts/orchestrator.py --zone cloud --dry-run` shows only cloud components. MCP servers in cloud mode reject write operations. Social poster in cloud mode creates drafts but never publishes.

---

## Phase 4: User Story 4 — Vault Sync Mechanism (Priority: P1)

**Goal**: Git-based vault sync between Cloud and Local with security exclusions and conflict detection

**Independent Test**: Create file on one side, run sync, verify it appears on the other. Create `.env` file and verify it never syncs.

### Implementation

- [ ] T020 [P] [US4] Create `scripts/vault_sync.py` — `VaultSync` class: `__init__(vault_path, remote, branch)`, `sync()` method runs: `git add -A`, `git commit -m "auto-sync <zone> <timestamp>"`, `git pull --rebase`, `git push`, returns `SyncResult(files_changed, conflicts, status)`, conflict detection: parse rebase output for CONFLICT lines, write conflicts to `Updates/SYNC_CONFLICT_<ts>.md`, `validate_exclusions()` scans staged files for `.env`/`credentials.json`/`token.json` patterns and unstages them before commit
- [ ] T021 [P] [US4] Create `deploy/sync/git-sync.sh` — bash script: source `.env` for `VAULT_PATH`, `cd` to vault, run `python scripts/vault_sync.py --once`, log output to `Logs/vault_sync.log`, exit codes: 0=success, 1=conflict, 2=error
- [ ] T022 [P] [US4] Create `deploy/systemd/vault-sync.timer` — systemd timer unit: runs `vault-sync.service` every 2 minutes, `vault-sync.service` runs `deploy/sync/git-sync.sh`
- [ ] T023 [P] [US4] Create `.syncignore` for Syncthing alternative — mirrors `.gitignore` exclusions: `.env`, `.env.*`, `credentials.json`, `token.json`, `token.json.bak`, `*.session`, `__pycache__/`, `.venv/`, `.pytest_cache/`, `node_modules/`
- [ ] T024 [P] [US4] Create `deploy/sync/syncthing-setup.sh` — setup script: install Syncthing, configure shared folder for vault path, apply `.syncignore`, print Syncthing device ID for pairing
- [ ] T025 [US4] Create `tests/test_vault_sync.py` — test `sync()` commits and pushes, test `validate_exclusions()` unstages `.env` files, test conflict detection writes alert file, test `SyncResult` fields, test sync with empty changes (no commit created)

**Checkpoint**: `pytest tests/test_vault_sync.py` passes. Git sync script runs without error. `.env` is never committed. Conflicts produce alert files.

---

## Phase 5: User Story 1 — Cloud 24/7 Deployment (Priority: P1) — MVP

**Goal**: Deploy AI Employee on Oracle Cloud Free VM with health monitoring, auto-restart, and alerts

**Independent Test**: Deploy to VM, run for 24+ hours, kill a component, verify auto-restart within 60s, verify alert after 3 consecutive failures

### Implementation

- [ ] T026 [P] [US1] Create `deploy/setup-vm.sh` — Oracle Cloud VM provisioning: update apt, install Python 3.11, pip, Docker, Docker Compose, Git, nginx, certbot, create `ai-employee` user, clone vault repo, install Python deps from `requirements.txt`, setup SSH key for Git sync, configure firewall (allow 80, 443, 22), add 2 GB swap file
- [ ] T027 [P] [US1] Create `deploy/systemd/ai-employee.service` — systemd unit: `ExecStart=python scripts/orchestrator.py --zone cloud --auto-restart --vault-path /home/ai-employee/vault`, `Restart=always`, `RestartSec=10`, `User=ai-employee`, `WorkingDirectory=/home/ai-employee/vault`, `EnvironmentFile=/home/ai-employee/vault/.env`
- [ ] T028 [US1] Create `scripts/cloud_health_monitor.py` — `HealthMonitor` class: extends existing `HealthTracker` from `error_recovery.py`, `check_process(name, pid)` polls subprocess, `check_http(name, url)` GET with 5s timeout, `check_sync_freshness(max_stale_seconds=300)` reads last sync timestamp, `run_checks()` iterates all registered checks, `consecutive_failures[name] >= 3` triggers `send_alert(name, error)`, alert writes `Updates/ALERT_<ts>.md` with component name, error, timestamp; optional email alert via Gmail API if `HEALTH_ALERT_EMAIL` env var set, main loop: check every `HEALTH_CHECK_INTERVAL` seconds (default 60)
- [ ] T029 [US1] Integrate health monitor into orchestrator — modify `scripts/orchestrator.py`: when `ZONE_MODE=cloud`, launch `cloud_health_monitor.py` as managed component, pass process PIDs to health monitor via shared state or file, health monitor reports to `Dashboard.md` health section
- [ ] T030 [US1] Create `tests/test_cloud_health.py` — test `check_process` detects dead PID, test `check_http` with mock server, test consecutive failure counter and alert threshold, test alert file creation in `Updates/`, test `check_sync_freshness` with stale timestamp

**Checkpoint**: `pytest tests/test_cloud_health.py` passes. Orchestrator in cloud mode launches health monitor. Simulated crash triggers auto-restart. 3 consecutive failures produce alert file.

---

## Phase 6: User Story 3 — Delegation via Synced Vault (Priority: P1)

**Goal**: Structured folder-based communication between Cloud and Local — domain folders, claim-by-move, single-writer Dashboard, Updates channel

**Independent Test**: Cloud creates file in `Needs_Action/EMAIL/`, sync runs, Local sees it, Local claims via move to `In_Progress/local/`, Cloud cannot re-claim, Local completes to `Done/`

### Implementation

- [ ] T031 [US3] Create vault delegation protocol in `scripts/vault_delegation.py` — `create_task(domain, content, zone)` writes markdown file to `Needs_Action/<domain>/TASK_<ts>.md` with YAML frontmatter (domain, created_by, created_at, status), `promote_to_approval(task_path, domain)` moves from `Needs_Action/` or `Plans/` to `Pending_Approval/<domain>/`, `write_update(content, zone)` writes to `Updates/UPDATE_<ts>.md`, `read_updates()` lists and reads all files in `Updates/`, `merge_updates()` processes updates and archives read ones to `Updates/archived/`
- [ ] T032 [US3] Modify `scripts/update_dashboard.py` — integrate with vault delegation: in cloud mode, write `Dashboard.md` with sections: Component Health (from health monitor), Pending Tasks per domain (count files in `Pending_Approval/*/`), Recent Updates (from `Updates/`), Sync Status (from vault_sync), Last Updated timestamp; in local mode, read-only (do not write)
- [ ] T033 [US3] Integrate delegation with existing watchers — modify `scripts/gmail_watcher.py` cloud mode: use `vault_delegation.create_task("EMAIL", triage_result)` instead of flat `Needs_Action/` writes; modify `scripts/social_poster.py` cloud mode: use `vault_delegation.promote_to_approval(draft_path, "SOCIAL")` for completed drafts

**Checkpoint**: Cloud creates domain-tagged tasks. Claim-by-move prevents double-processing. Dashboard.md shows accurate status. Updates flow from Cloud to Local.

---

## Phase 7: User Story 5 — Odoo Community Cloud Deployment (Priority: P2)

**Goal**: Deploy Odoo 17 on Cloud VM behind HTTPS nginx, with daily backups and health monitoring

**Independent Test**: Access `https://<domain>/web`, verify HTTPS valid, run backup script, verify dump file exists, query invoices via Cloud MCP

### Implementation

- [ ] T034 [P] [US5] Create `deploy/docker-compose.yml` — services: `odoo` (image `odoo:17`, port `8069:8069`, volumes for data + addons + config, depends_on `db`), `db` (image `postgres:16`, env `POSTGRES_USER=odoo`, `POSTGRES_PASSWORD` from env, `POSTGRES_DB=postgres`, volume for pgdata), networks: `odoo-net`
- [ ] T035 [P] [US5] Create `deploy/nginx/odoo.conf` — nginx server block: listen 80 redirect to 443, listen 443 ssl, `ssl_certificate /etc/letsencrypt/live/<domain>/fullchain.pem`, proxy_pass `http://localhost:8069`, proxy headers (`X-Forwarded-For`, `X-Forwarded-Proto`, `Host`), static file caching, websocket support for longpolling (`/longpolling/` → port 8072)
- [ ] T036 [P] [US5] Create `deploy/nginx/ssl-renew.sh` — certbot renewal: `certbot renew --quiet --deploy-hook "systemctl reload nginx"`, add to crontab twice daily
- [ ] T037 [P] [US5] Create `deploy/backup/odoo-backup.sh` — `pg_dump` backup: `docker exec odoo-db pg_dump -U odoo postgres | gzip > /backups/odoo/odoo_$(date +%Y%m%d_%H%M%S).sql.gz`, delete backups older than 7 days (`find /backups/odoo/ -mtime +7 -delete`), log success/failure, add to crontab daily at 2 AM
- [ ] T038 [US5] Modify `scripts/mcp_odoo_server.py` — add cloud Odoo URL support: read `ODOO_URL` from env (defaults to `http://localhost:8069`), in cloud mode connect to cloud Odoo instance, add Odoo health check: `GET /web/health`, integrate with `cloud_health_monitor.py` for Odoo-specific monitoring
- [ ] T039 [US5] Add Odoo to `deploy/setup-vm.sh` — append to VM setup: create `/backups/odoo/` dir, install `docker-compose.yml`, run `docker compose up -d`, request Let's Encrypt cert via `certbot --nginx -d <domain>`, enable nginx, add backup cron, add SSL renewal cron

**Checkpoint**: Odoo accessible at `https://<domain>/web`. HTTPS certificate valid. `pg_dump` backup exists in `/backups/odoo/`. MCP reads invoices from cloud Odoo.

---

## Phase 8: User Story 2+5 Integration — Cloud MCP Drafts + Local Approval (Priority: P3)

**Goal**: Cloud MCP creates draft operations (Odoo writes, email sends), Local picks up and executes after CEO approval

**Independent Test**: Cloud MCP creates draft invoice → appears in `Pending_Approval/ODOO/` → Local approval script presents it → CEO approves → Odoo write executes → moved to `Done/`

### Implementation

- [ ] T040 [P] [US2] Create `scripts/local_approval.py` — `LocalApprovalService` class: `scan_pending(domains)` lists all files in `Pending_Approval/<domain>/` across EMAIL, SOCIAL, ODOO; `present_for_approval(task_file)` reads file, prints summary, prompts CEO (approve/reject/skip); `execute_approved(task_file, domain)` dispatches to correct handler: EMAIL → `gmail_watcher.send_email()`, SOCIAL → `social_poster.publish_post()`, ODOO → `odoo_client.execute_write()`; `reject_task(task_file)` moves to `Done/` with `status: rejected` appended; uses `claim_task.py` for atomic claim before execution; logs all actions via `audit_logger`
- [ ] T041 [US2] Integrate `local_approval.py` into orchestrator — modify `scripts/orchestrator.py`: when `ZONE_MODE=local`, add `local_approval.py` as managed component with `--scan-interval 30` (scan every 30 seconds), add `--interactive` flag for manual approval mode (default) vs `--auto-approve` for testing
- [ ] T042 [US2] Write `Updates/` merge logic — modify `scripts/local_approval.py`: on startup and every scan, read new files from `Updates/`, log each update, archive processed updates to `Updates/archived/`, merge relevant status into local state

**Checkpoint**: Full round-trip: Cloud creates draft → sync → Local scans → CEO approves → action executes → `Done/`. Rejected items also move to `Done/` with status.

---

## Phase 9: User Story 6 — A2A Upgrade (Phase 2 — Optional) (Priority: P3)

**Goal**: Direct agent-to-agent messaging replacing file handoffs, with vault audit and fallback

**Independent Test**: Cloud sends A2A message → Local receives within 5s → vault audit record created → kill A2A → Cloud falls back to file-based handoff

### Implementation

- [ ] T043 [P] [US6] Create `scripts/a2a_server.py` — lightweight HTTP server (stdlib `http.server` or Flask): `POST /a2a` endpoint accepts JSON `{"id", "from_zone", "to_zone", "message_type", "payload"}`, validates message schema, writes to `Updates/A2A_<id>.md` as audit, queues task for local_approval processing, returns `{"status": "received", "id": "<id>"}`, listens on `A2A_LISTEN_PORT` (default 8765)
- [ ] T044 [P] [US6] Create `scripts/a2a_client.py` — `A2AClient` class: `__init__(local_webhook_url)`, `send(message_type, payload)` POSTs JSON to local webhook, timeout 5s, on success: also write audit to `Updates/A2A_<id>.md`, on failure (timeout/connection refused): log warning, fall back to `vault_delegation.create_task()` for file-based handoff, `is_available()` pings `GET /a2a/health` with 2s timeout
- [ ] T045 [US6] Integrate A2A into orchestrator — modify `scripts/orchestrator.py`: when `A2A_ENABLED=true`, cloud mode starts `a2a_client.py` alongside vault_sync, local mode starts `a2a_server.py` alongside local_approval, A2A and vault sync coexist (A2A is preferred channel, vault is fallback + audit)
- [ ] T046 [US6] Create `tests/test_a2a.py` — test server receives and acks message, test audit record written to `Updates/`, test client fallback on connection failure, test client fallback on timeout, test A2A and vault coexistence, test message schema validation

**Checkpoint**: `pytest tests/test_a2a.py` passes. A2A message delivered in <5s. Audit trail in vault. Fallback to file-based within 30s of connection loss.

---

## Phase 10: User Story 7 — Platinum Demo + Self-Test (Priority: P4)

**Goal**: End-to-end demo proving all Platinum requirements + comprehensive test suite

**Independent Test**: Run `python scripts/platinum_demo.py` and verify all checkpoints report PASS

### Implementation

- [ ] T047 [P] [US7] Create `scripts/platinum_demo.py` — demo script with checkpoints: (1) verify `zone_config.py` loads and `ZONE_MODE` works, (2) verify domain folders exist, (3) verify claim-by-move works, (4) verify vault_sync.py can run (or mock), (5) verify `.gitignore` excludes secrets, (6) verify orchestrator `--zone cloud --dry-run` shows correct components, (7) verify cloud health monitor starts, (8) verify MCP servers in cloud mode reject writes, (9) verify local_approval scans pending, (10) if `A2A_ENABLED`: verify A2A send/receive, (11) output summary table with PASS/FAIL per checkpoint, map to FR-001 through FR-030
- [ ] T048 [P] [US7] Create `tests/test_platinum_tier_selftest.py` — pytest suite: test all 30 FRs mapped to test functions, test all 14 SCs as parametrized tests, test Gold Tier regressions (import and run `test_gold_tier_selftest.py`), structured as: `TestCloudDeployment`, `TestZoneEnforcement`, `TestVaultSync`, `TestClaimByMove`, `TestHealthMonitoring`, `TestOdooCloud`, `TestLocalApproval`, `TestA2A` (skip if not enabled), `TestPlatinumDemo`
- [ ] T049 [US7] Update `ARCHITECTURE.md` — add Platinum Tier section: component table (cloud_health_monitor, vault_sync, zone_config, claim_task, local_approval, a2a_server/client), Cloud/Local zone diagram, vault folder structure with domain subfolders, sync flow diagram, data flow showing Cloud draft → sync → Local approve → execute
- [ ] T050 [US7] Update `.env.example` — append Platinum-specific variables: `ZONE_MODE=local`, `HEALTH_CHECK_INTERVAL=60`, `HEALTH_ALERT_EMAIL=`, `HEALTH_CONSECUTIVE_FAILURES=3`, `SYNC_METHOD=git`, `SYNC_INTERVAL=120`, `SYNC_REMOTE=origin`, `SYNC_BRANCH=vault-sync`, `A2A_ENABLED=false`, `A2A_LOCAL_WEBHOOK_URL=`, `A2A_LISTEN_PORT=8765`
- [ ] T051 [US7] Update `README.md` — add Platinum Tier section with: overview of Cloud/Local split, setup instructions (link to quickstart.md), demo instructions (`python scripts/platinum_demo.py`), tier progression summary (Bronze → Silver → Gold → Platinum)

**Checkpoint**: `python scripts/platinum_demo.py` reports all PASS. `pytest tests/test_platinum_tier_selftest.py` all green. Architecture docs updated. All Platinum requirements verified.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Zone Config + Claim)**: Depends on Phase 1 folders — BLOCKS all user stories
- **Phase 3 (Work-Zone US2)**: Depends on Phase 2 zone_config.py
- **Phase 4 (Vault Sync US4)**: Depends on Phase 2 — can run parallel with Phase 3
- **Phase 5 (Cloud Deploy US1)**: Depends on Phase 2 + Phase 3 (needs zone enforcement)
- **Phase 6 (Delegation US3)**: Depends on Phase 2 + Phase 4 (needs sync)
- **Phase 7 (Odoo Cloud US5)**: Depends on Phase 5 (needs VM)
- **Phase 8 (Local Approval US2+5)**: Depends on Phase 3 + Phase 6 + Phase 7
- **Phase 9 (A2A US6)**: Depends on Phase 6 — optional
- **Phase 10 (Demo US7)**: Depends on ALL previous phases

### User Story Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundation) ──── BLOCKS ALL ────
    ↓                    ↓               ↓
Phase 3 (US2: Zones)  Phase 4 (US4: Sync)
    ↓                    ↓
Phase 5 (US1: Cloud) ←──┘
    ↓
Phase 6 (US3: Delegation)
    ↓
Phase 7 (US5: Odoo Cloud)
    ↓
Phase 8 (US2+5: Local Approval)
    ↓
Phase 9 (US6: A2A) [optional]
    ↓
Phase 10 (US7: Demo)
```

### Parallel Opportunities

- **Phase 1**: All T001–T008 can run in parallel (different directories)
- **Phase 2**: T009+T010 in parallel (different files), T011+T012 in parallel (different test files)
- **Phase 3**: T013–T018 all in parallel (different scripts)
- **Phase 4**: T020–T024 all in parallel (different files)
- **Phase 5**: T026+T027 in parallel (different files)
- **Phase 7**: T034–T037 all in parallel (different files)
- **Phase 9**: T043+T044 in parallel (different files)
- **Phase 10**: T047+T048 in parallel (different files)

---

## Implementation Strategy

### MVP First (Phases 1–5)

1. Complete Phase 1: Setup folders + deployment skeleton
2. Complete Phase 2: Zone config + claim-by-move (CRITICAL GATE)
3. Complete Phase 3: Modify existing scripts for zone enforcement
4. Complete Phase 4: Vault sync mechanism
5. Complete Phase 5: Cloud VM deployment + health monitoring
6. **STOP and VALIDATE**: Deploy to Oracle Cloud, run for 24+ hours, verify cloud-only drafts

### Incremental Delivery

1. Phases 1–2 → Foundation ready
2. + Phase 3 → Zone enforcement working (can demo Cloud vs Local)
3. + Phase 4 → Vault syncing (can demo file propagation)
4. + Phase 5 → Cloud deployment (can demo 24/7 operation)
5. + Phase 6 → Vault delegation (can demo full Cloud→Local pipeline)
6. + Phase 7 → Odoo on cloud (can demo HTTPS accounting)
7. + Phase 8 → Local approval (can demo full approval workflow)
8. + Phase 9 → A2A optional upgrade
9. + Phase 10 → Full Platinum demo with all checkpoints PASS

---

## Task Summary

| Phase | Story | Tasks | Parallel |
|-------|-------|-------|----------|
| 1 Setup | — | 8 | 7 |
| 2 Foundation | — | 4 | 2 |
| 3 Zones | US2 | 7 | 6 |
| 4 Sync | US4 | 6 | 5 |
| 5 Cloud | US1 | 5 | 2 |
| 6 Delegation | US3 | 3 | 0 |
| 7 Odoo | US5 | 6 | 4 |
| 8 Approval | US2+5 | 3 | 1 |
| 9 A2A | US6 | 4 | 2 |
| 10 Demo | US7 | 5 | 2 |
| **Total** | | **51** | **31** |

---

## Notes

- [P] tasks = different files, no dependencies — safe to parallelize
- [Story] labels map to spec.md user stories (US1–US7)
- Each phase checkpoint is independently verifiable
- A2A (Phase 9) is optional — skip if time-constrained
- All `deploy/` scripts target Ubuntu 22.04 ARM (Oracle Cloud Always Free)
- All vault operations use `audit_logger.py` for traceability
- Gold Tier regression: `test_gold_tier_selftest.py` imported in Phase 10 self-test
