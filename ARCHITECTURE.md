# AI Employee Vault — Architecture

## System Overview

The AI Employee Vault is a local-first autonomous assistant that monitors
communication channels (Gmail, WhatsApp), processes tasks through an Obsidian
vault, integrates with business systems (Odoo accounting), and publishes to
social platforms — all with human-in-the-loop (HITL) approval gates.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                                │
│  Launches, monitors, and auto-restarts all components              │
│  scripts/orchestrator.py                                           │
└────┬──────────┬──────────┬──────────┬──────────┬──────────┬────────┘
     │          │          │          │          │          │
     ▼          ▼          ▼          ▼          ▼          ▼
 ┌────────┐┌────────┐┌─────────┐┌─────────┐┌─────────┐┌──────────┐
 │ File   ││ Gmail  ││WhatsApp ││ Weekly  ││Odoo MCP ││Social MCP│
 │Watcher ││Watcher ││Watcher  ││Briefing ││ Server  ││ Server   │
 │Bronze  ││Silver  ││Silver   ││Gold     ││Gold     ││Gold      │
 └───┬────┘└───┬────┘└───┬─────┘└───┬─────┘└────┬────┘└────┬─────┘
     │         │         │          │            │          │
     ▼         ▼         ▼          ▼            ▼          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      OBSIDIAN VAULT                                │
│                                                                    │
│  Needs_Action/  ─►  Plans/  ─►  Pending_Approval/  ─►  Done/     │
│                                                                    │
│  Briefings/          Logs/*.audit.jsonl          Dashboard.md      │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### Tier 1 — Bronze (Core)

| Component | File | Purpose |
|-----------|------|---------|
| File Watcher | `scripts/watcher.py` | Monitors vault for new files, triggers processing |
| Process Inbox | `scripts/process_inbox.py` | Classifies tasks, moves to correct folders |
| Data Analyzer | `scripts/data_analyzer.py` | CSV financial analysis with anomaly detection |
| Dashboard | `scripts/update_dashboard.py` | Generates `Dashboard.md` with vault stats |
| Audit Logger | `scripts/audit_logger.py` | JSONL audit trail in `Logs/` |

### Tier 2 — Silver (Integrations)

| Component | File | Purpose |
|-----------|------|---------|
| Gmail Watcher | `scripts/gmail_watcher.py` | Polls Gmail API, creates task files |
| WhatsApp Watcher | `scripts/whatsapp_watcher.py` | Playwright-based WhatsApp Web monitor |
| LinkedIn Poster | `scripts/linkedin_poster.py` | Draft/approve/publish LinkedIn posts |
| Weekly Briefing | `scripts/weekly_briefing.py` | CEO briefing with financial + operational data |

### Tier 3 — Gold (Autonomous)

| Component | File | Purpose |
|-----------|------|---------|
| Odoo Client | `scripts/odoo_client.py` | JSON-RPC client for Odoo Community |
| Social Poster | `scripts/social_poster.py` | Multi-platform posting (FB/IG/X/LinkedIn) |
| Reasoning Loop | `scripts/reasoning_loop.py` | Ralph Wiggum loop — autonomous plan/execute |
| Error Recovery | `scripts/error_recovery.py` | `safe_call()` + `HealthTracker` |
| Orchestrator | `scripts/orchestrator.py` | Process manager with auto-restart |

### MCP Servers (Claude Code Integration)

| Server | File | Tools |
|--------|------|-------|
| Odoo | `scripts/mcp_odoo_server.py` | `list_invoices`, `get_overdue_invoices`, `get_financial_summary`, ... |
| Social | `scripts/mcp_social_server.py` | `draft_social_post`, `list_social_drafts`, `publish_approved_posts`, ... |
| Email | `scripts/mcp_email_server.py` | `fetch_unread_emails`, `send_email`, `reply_to_email`, ... |

## Data Flow

```
External Sources                Processing Pipeline              Output
─────────────────               ──────────────────               ──────

Gmail API ──────►  gmail_watcher.py ──► Needs_Action/*.md ──┐
                                                             │
WhatsApp Web ───►  whatsapp_watcher.py ─► Needs_Action/*.md ─┤
                                                             │
Manual drop ────►  watcher.py ──────────► Needs_Action/*.md ─┤
                                                             ▼
                                                   process_inbox.py
                                                        │
                                        ┌───────────────┼──────────────┐
                                        ▼               ▼              ▼
                                  Plans/*.md    Pending_Approval/   Done/
                                        │               │
                                        ▼               ▼
                               reasoning_loop.py   Human Review
                               (execute steps)     (approve/reject)
                                        │               │
                                        ▼               ▼
                                    Done/*.md     Approved/*.md
                                                        │
                                                        ▼
                                              social_poster.py
                                              linkedin_poster.py
                                              odoo_client.py
```

## HITL Approval Gates

Sensitive actions require human approval before execution:

1. **Financial actions** (amount > $500, new vendor) → `Pending_Approval/`
2. **Social media posts** → `Pending_Approval/LINKEDIN_*.md`
3. **Email replies** → `Pending_Approval/` with draft content
4. **Odoo entries** → Draft invoices/expenses require confirmation

The vault's folder structure serves as the approval workflow:
- `Pending_Approval/` = awaiting human review
- `Approved/` = human approved, ready for execution
- `Done/` = completed and archived

## Error Recovery Strategy

```
                    ┌──────────────┐
                    │  safe_call() │  Wraps every external call
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         Success      Transient     Permanent
              │        Error          Error
              │            │              │
              ▼            ▼              ▼
        HealthTracker   Retry (1x)    Log + Skip
        .record_success()  │          .record_failure()
                           │
                      ┌────┴────┐
                      ▼         ▼
                  Success    Fail
                      │         │
                      ▼         ▼
              record_success  record_failure
                              (degraded/unavailable)
```

- **Graceful degradation**: If Odoo is down, briefings use CSV fallback
- **Auto-restart**: Orchestrator restarts crashed components (max 3 attempts)
- **Independent failures**: MCP servers isolated — one crash doesn't affect others

## Audit Logging

All actions logged to `Logs/YYYY-MM-DD.audit.jsonl`:

```json
{
  "timestamp": "2026-02-25T10:30:00Z",
  "action": "email_processed",
  "target": "EMAIL_215334_invoice.md",
  "result": "success",
  "details": {"category": "finance", "priority": "high"}
}
```

Actions tracked: `email_fetched`, `task_classified`, `plan_created`,
`plan_step_executed`, `social_posted`, `odoo_invoice_drafted`,
`orchestrator_launch`, `orchestrator_crash`, `orchestrator_restart`.
