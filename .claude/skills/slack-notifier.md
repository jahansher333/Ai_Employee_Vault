# Slack Notifier Skill

## Purpose
Send Slack notifications for AI Employee events: task completions, approval requests, briefings, low stock alerts, and overdue invoices.

## When to Use
- When a task completes and moves to Done/
- When an item needs human approval
- When CEO briefing is generated
- When low stock products are detected
- When overdue invoices are found
- User asks to "notify Slack" or "send status to Slack"

## Commands
```bash
# Send a test message
python scripts/slack_notifier.py --test "Hello from AI Employee"

# Send vault status summary
python scripts/slack_notifier.py --summary
```

## Configuration
Set in `.env`:
- `SLACK_WEBHOOK_URL` — Incoming Webhook URL (required for real sending)
- `SLACK_CHANNEL` — Override channel (optional)

Without `SLACK_WEBHOOK_URL`, runs in simulation mode (logs to audit trail).

## Notification Types
| Function | Trigger | Color |
|----------|---------|-------|
| `notify_task_complete` | Task → Done/ | Green |
| `notify_approval_needed` | Task → Pending_Approval/ | Orange |
| `notify_briefing_ready` | Briefing generated | Blue |
| `notify_low_stock` | Inventory below threshold | Red |
| `notify_overdue_invoices` | Overdue invoices found | Red |

## Integration
- Called by other scripts after key events
- All notifications logged to `Logs/*.audit.jsonl`
- Simulation mode requires zero configuration

## Script
`scripts/slack_notifier.py`
