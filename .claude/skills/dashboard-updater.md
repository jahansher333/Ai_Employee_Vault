# Dashboard Updater Skill

## Purpose
Regenerate Dashboard.md with current vault analytics: folder counts, pending tasks, active plans, completed items, social posts, briefings, service health, and recent activity from audit logs.

## When to Use
- After task processing, archiving, or any vault state change
- When generating a current status snapshot
- User asks to "update dashboard", "refresh status", or "show vault summary"

## Commands
```bash
# Update Dashboard.md
python scripts/update_dashboard.py

# Custom vault path
python scripts/update_dashboard.py --vault-path /path/to/vault
```

## Configuration
Set in `.env`:
- `VAULT_PATH` — Path to vault root (default: parent of scripts/)

## Dashboard Sections
| Section | Source |
|---------|--------|
| Quick Status | Folder counts (Needs_Action, Plans, Pending_Approval, Approved, Done) |
| Pending Tasks | Parses Needs_Action/*.md frontmatter |
| Active Plans | Parses Plans/PLAN_*.md with objective, progress, priority |
| Recently Completed | Parses Done/*.md with completion timestamps |
| Service Health | HealthTracker status for all integrations |
| Recent Social Posts | Scans Pending_Approval/, Approved/, Done/ for platform prefixes |
| Recent Briefings | Lists Briefings/*_Briefing*.md |
| Business Analytics | Placeholder for data_analyzer output |
| Recent Activity | Last 10 audit log entries |

## Key Functions
| Function | Purpose |
|----------|---------|
| `update_dashboard` | Main function — regenerates Dashboard.md |
| `build_pending_tasks_table` | Table rows from Needs_Action/ |
| `build_plans_table` | Table rows from Plans/ |
| `build_done_tasks_table` | Table rows from Done/ |
| `build_social_posts_table` | Cross-folder social post summary |
| `build_briefings_table` | Recent briefings list |
| `build_service_health_table` | Integration health status |

## Integration
- Writes to `Dashboard.md` at vault root
- Called by gmail_watcher after replies, process_inbox after completion
- Reads audit logs via AuditLogger for activity feed
- Uses error_recovery.HealthTracker for service status

## Script
`scripts/update_dashboard.py`
