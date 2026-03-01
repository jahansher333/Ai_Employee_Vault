# CEO Briefing Skill

## Purpose

Generate a structured Monday briefing report for CEO/stakeholder review. Pulls financial data, task pipeline status, bottleneck analysis, and recommended actions into a single markdown document.

## Trigger

- Scheduled: Every Sunday at 8:00 PM PKT (via Task Scheduler or cron)
- On demand: User requests a briefing or runs the script manually
- Claude Code: "Generate a CEO briefing" or "What's the status this week?"

## Steps

1. **Collect financial data** from `data_analyzer.py` (revenue, expenses, net income, anomalies)
2. **Count tasks** across all vault folders (Needs_Action, Plans, Pending_Approval, Approved, Done)
3. **Detect bottlenecks**: stale tasks (>48h), pending approvals (>24h), blocked plans, error patterns
4. **Review audit log** for recent activity (last 15 events)
5. **Generate briefing** with sections: Executive Summary, Financial Overview, Task Pipeline, Bottlenecks, Recommended Actions, Recent Activity
6. **Write** to `Briefings/YYYY-MM-DD_Monday_Briefing.md`
7. **Update Dashboard** with latest briefing reference
8. **Log** generation to audit trail

## Output Format

```yaml
---
type: briefing
date: "2026-02-24"
generated_at: "2026-02-23T20:00:00+05:00"
status: new
priority: high
---
```

Sections:
- Executive Summary (1-line financials, open items, bottleneck count)
- Financial Overview (revenue/expenses table, anomalies, monthly trend)
- Task Pipeline (counts per queue with action needed)
- Bottlenecks & Risks (stale tasks, blocked approvals, errors)
- Recommended Actions (prioritized numbered list)
- Recent Activity (last 10 audit log entries)

## CLI Commands

```bash
# Generate briefing now (one-shot)
python scripts/weekly_briefing.py

# Run scheduler loop (Sunday 8 PM PKT)
python scripts/weekly_briefing.py --schedule
```

## Scheduling Setup

### Windows Task Scheduler
```
Action: Start a program
Program: python
Arguments: D:\Hac3\Ai_Employee_Vault\scripts\weekly_briefing.py
Trigger: Weekly, Sunday, 8:00 PM
```

### Linux/Mac cron
```
0 20 * * 0 cd /path/to/vault && python scripts/weekly_briefing.py
```

## Audit Log Entry

- `briefing_generated` — New briefing file created with task/financial summary
