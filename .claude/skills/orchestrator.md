# Orchestrator Skill

## Purpose

Single entry point to launch and manage all AI Employee components as concurrent subprocesses. Provides graceful startup, health monitoring, and coordinated shutdown.

## Trigger

- User runs: "Start the AI Employee" or "Launch all watchers"
- Direct CLI: `python scripts/orchestrator.py`
- After system restart or deployment

## Components Managed

| Component | Script | Tier | Required |
|-----------|--------|------|----------|
| File Watcher | `watcher.py` | Bronze | Yes |
| Gmail Watcher | `gmail_watcher.py` | Silver | No (needs credentials) |
| WhatsApp Watcher | `whatsapp_watcher.py` | Silver | No |
| Weekly Briefing Scheduler | `weekly_briefing.py --schedule` | Silver | No |

## Steps

1. **Validate** vault directory structure (creates missing folders)
2. **Build** component list based on flags and available credentials
3. **Validate** all script files exist
4. **Launch** each component as a subprocess
5. **Monitor** health every 10 seconds (detect crashes)
6. **Shutdown** gracefully on Ctrl+C (terminate, then kill after 5s)
7. **Log** all lifecycle events to audit trail

## CLI Commands

```bash
# Launch all components
python scripts/orchestrator.py

# Skip specific watchers
python scripts/orchestrator.py --no-gmail
python scripts/orchestrator.py --no-whatsapp
python scripts/orchestrator.py --no-scheduler

# Preview without launching
python scripts/orchestrator.py --dry-run

# Custom vault path
python scripts/orchestrator.py --vault-path /path/to/vault
```

## Audit Log Entries

- `orchestrator_started` — All components launching
- `orchestrator_launch` — Individual component started (includes PID)
- `orchestrator_crash` — Component exited unexpectedly
- `orchestrator_stop` — Component gracefully stopped
- `orchestrator_stopped` — Orchestrator shutdown complete
