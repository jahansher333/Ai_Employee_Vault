---
title: Company Handbook
version: "1.0"
updated: 2026-02-17
---

# Company Handbook — Bronze Tier AI Employee

## Operating Principles

### 1. Local-First

All processing happens on the local machine. No secrets, sessions, or
sensitive data are synced to cloud services. The Obsidian vault is the
single source of truth.

### 2. Human-in-the-Loop

The AI employee MUST NOT take sensitive actions autonomously. Any action
involving:
- Financial transactions (payments, invoices)
- Credentials or passwords
- Data deletion or removal
- API keys or access tokens

MUST be routed to `Pending_Approval/` for human review before execution.

### 3. Detection Only (Bronze Tier)

At the Bronze Tier, the AI employee operates in **detection and
recommendation mode**:
- **CAN**: Read files, analyze content, generate plans, write to vault
- **CANNOT**: Send emails, make API calls, trigger webhooks, execute payments

### 4. Audit Everything

Every action is logged to `Logs/` in structured JSON Lines format.
Logs are append-only and include: timestamp, action type, input reference,
outcome (success/error/skipped), and duration.

### 5. Security

- Credentials stored in `.env` only (never in vault files)
- `.env` is in `.gitignore` (never committed)
- No secrets in log files

## Task Format

Create `.md` files in `Needs_Action/` with this structure:

```markdown
---
type: task
priority: high | medium | low
category: research | draft | review | organize | analyze | general
status: new
---

# Task Title

Description of what needs to be done.

## Context

Any relevant background information.

## Expected Output

What the result should look like.
```

### Frontmatter Fields

| Field | Values | Default | Description |
|-------|--------|---------|-------------|
| type | task, request, note | task | Classification |
| priority | high, medium, low | medium | Urgency level |
| category | research, draft, review, organize, analyze, general | general | Domain |
| status | new, planned, pending_approval, done | new | Lifecycle state |

## Approval Workflow

Tasks containing sensitive keywords are automatically flagged:

1. Watcher detects new file in `Needs_Action/`
2. Processor checks for keywords: **payment**, **password**, **credential**, **delete**, **remove**, **api key**
3. If sensitive → file copied to `Pending_Approval/` with status `pending_approval`
4. Human reviews and changes status to `approved` or `rejected`
5. If not sensitive → action plan generated, status set to `planned`

## Folder Descriptions

| Folder | Purpose |
|--------|---------|
| `Needs_Action/` | Drop new task files here. The watcher monitors this folder. |
| `Pending_Approval/` | Contains sensitive tasks awaiting human review. |
| `Done/` | Completed tasks moved here after processing. |
| `Logs/` | Audit trail in JSON Lines format (one file per day). |
| `scripts/` | Python scripts: watcher, processor, dashboard updater. |
| `.claude/skills/` | Agent Skill definitions in Markdown format. |
