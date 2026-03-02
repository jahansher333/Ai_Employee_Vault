# Research: Platinum Tier — Always-On Cloud + Local Executive

**Feature**: `006-platinum-tier-cloud`
**Date**: 2026-03-01

## R1: Oracle Cloud Free Tier VM Constraints

**Decision**: Use Oracle Cloud Always Free tier ARM-based VM (Ampere A1)
**Rationale**: Oracle Cloud Always Free includes up to 4 OCPUs and 24 GB RAM on Ampere A1 (ARM). For a single VM, we allocate 1 OCPU + 6 GB RAM — sufficient for Python watchers, Odoo Community, PostgreSQL, and nginx. No credit card charges as long as within Always Free limits.
**Alternatives considered**:
- AWS Free Tier (t2.micro, 1 GB RAM — too small for Odoo)
- GCP Free Tier (e2-micro, 1 GB RAM — too small)
- Azure Free Tier (B1s, 1 GB RAM — too small)
- Self-hosted VPS (costs money, not free tier)

**Key constraints**:
- ARM architecture (aarch64) — all Python code is compatible; Odoo Community runs on ARM
- Ubuntu 22.04 LTS (Canonical image available on OCI)
- 50 GB boot volume (Always Free)
- 10 Mbps network bandwidth (Always Free)
- Static public IP via Reserved Public IP (Always Free)

## R2: Vault Sync — Git vs Syncthing

**Decision**: Git (push/pull via cron) as primary; Syncthing as documented alternative
**Rationale**: Git is already the project's VCS; adding a sync cron is minimal overhead. Git provides atomic commits, merge conflict detection, and branch history. Syncthing is simpler for real-time sync but lacks atomic conflict resolution — offered as alternative for users who want sub-minute sync.

| Criteria       | Git (cron push/pull) | Syncthing           |
|----------------|---------------------|---------------------|
| Latency        | 1-5 min (cron)      | ~real-time (<10s)   |
| Conflicts      | Git merge tooling   | .sync-conflict files |
| Setup           | SSH keys + cron     | Install + share ID  |
| Audit trail    | Git log             | None (file-level)   |
| Security       | .gitignore          | .stignore           |

**Git sync implementation**:
- Cloud: cron every 2 minutes runs `git add -A && git commit -m "cloud-sync" && git pull --rebase && git push`
- Local: cron every 2 minutes runs `git pull --rebase && git add -A && git commit -m "local-sync" && git push`
- Dedicated `vault-sync` branch to avoid polluting feature branches
- `.gitignore` already excludes `.env`, `credentials.json`, `token.json`

## R3: Claim-by-Move Protocol

**Decision**: Atomic `os.rename()` with `/In_Progress/<agent>/` directory
**Rationale**: On Linux (ext4), `os.rename()` within the same filesystem is atomic. If both Cloud and Local attempt to move the same file, exactly one succeeds and the other gets `FileNotFoundError`. This is simpler and more reliable than file locking.

**Protocol**:
1. Agent reads file from `/Pending_Approval/<domain>/`
2. Agent attempts `os.rename(src, /In_Progress/<agent_id>/<filename>)`
3. If rename succeeds → agent owns the task
4. If `FileNotFoundError` → another agent claimed it, skip
5. On completion → move to `Done/`

## R4: Work-Zone Enforcement

**Decision**: Configuration-driven zone mode via `ZONE_MODE` env var (`cloud` or `local`)
**Rationale**: A single env var (`ZONE_MODE=cloud`) disables all send/post/approve capabilities at startup. The orchestrator reads this and excludes Local-only components. Additionally, the zone config maps each operation to cloud/local, so even if code exists, it refuses to execute send operations in cloud mode.

**Zone mapping**:
- Cloud: `gmail_watcher` (read-only), `process_inbox` (triage), `social_poster --draft-only`, `mcp_odoo_server --read-only`, `update_dashboard`
- Local: `whatsapp_watcher`, `linkedin_poster --publish`, `social_poster --publish`, `mcp_email_server --send`, approval workflows, payment actions

## R5: Odoo Community Cloud Deployment

**Decision**: Docker Compose (Odoo 17.0 + PostgreSQL 16) behind nginx reverse proxy with Let's Encrypt
**Rationale**: Docker Compose is the standard Odoo deployment method. It isolates Odoo and PostgreSQL, simplifies upgrades, and works on ARM. Nginx provides HTTPS termination with Certbot for free certificates.

**Stack**:
- `docker-compose.yml`: Odoo 17.0 (port 8069) + PostgreSQL 16
- nginx: reverse proxy on ports 80/443 with SSL termination
- Certbot: auto-renewing Let's Encrypt certificate
- Backup: `pg_dump` cron daily → `/backups/odoo/` with 7-day retention
- Health: HTTP check on `http://localhost:8069/web/health` every 60s

## R6: A2A Protocol (Phase 2)

**Decision**: Lightweight HTTP webhook (Cloud → Local) + WebSocket (bidirectional, optional)
**Rationale**: HTTP webhooks are the simplest reliable A2A mechanism. Cloud sends POST to Local's webhook endpoint when a task is ready. Local confirms receipt. For bidirectional real-time, an optional WebSocket upgrade is available. Both write audit records to `/Updates/`.

**Fallback**: If webhook POST fails (timeout/connection refused), write task file to vault and rely on Git sync. Log the fallback event.

## R7: Health Monitoring Architecture

**Decision**: Watchdog service (Python) running alongside orchestrator, checking all components + Odoo + sync
**Rationale**: Extends the existing Gold Tier `HealthTracker` class. The watchdog runs as a separate process managed by the orchestrator. It checks process liveness, HTTP endpoints (Odoo, MCP servers), and sync status. After 3 consecutive failures, it writes an alert file and optionally sends an email via the Gmail API.

**Health checks**:
- Process-level: `poll()` on subprocess PIDs
- HTTP: GET to Odoo `/web/health`, MCP server endpoints
- Sync: Check last sync timestamp file (stale if >5 min)
- Alert: Write to `/Updates/ALERT_<timestamp>.md` + optional email
