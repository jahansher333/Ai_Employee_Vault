# API Server Skill

## Purpose
FastAPI backend that exposes vault status, tasks, approvals, financial data, inventory, social posts, briefings, and audit logs as JSON endpoints for the dashboard frontend.

## When to Use
- When starting the AI Employee web API
- When a frontend or external system needs vault data
- User asks to "start API", "launch server", or "expose dashboard data"

## Commands
```bash
# Start on default port 5000
python scripts/api_server.py

# Custom port and host
python scripts/api_server.py --port 8080 --host 0.0.0.0
```

API docs available at `http://localhost:5000/docs` (Swagger UI).

## Configuration
Set in `.env`:
- `VAULT_PATH` — Path to vault root (default: parent of scripts/)
- Odoo credentials (for `/api/financial` and `/api/inventory` endpoints)

Requires: `pip install fastapi uvicorn python-dotenv`

## Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Vault folder counts overview |
| `/api/tasks` | GET | List tasks from Needs_Action/ (supports `?limit=`) |
| `/api/approvals` | GET | List items in Pending_Approval/ |
| `/api/done` | GET | List completed items (supports `?limit=`) |
| `/api/financial` | GET | Financial summary from Odoo or CSV fallback |
| `/api/inventory` | GET | Inventory data from Odoo |
| `/api/social` | GET | Social media post counts by platform |
| `/api/briefings` | GET | List available CEO briefings |
| `/api/audit` | GET | Recent audit log entries (last 20) |
| `/api/health` | GET | API health check |

## Integration
- Reads vault folders (Needs_Action/, Pending_Approval/, Done/, etc.)
- Parses YAML frontmatter from .md files for metadata
- Falls back to CSV analysis if Odoo is unavailable for financial data
- CORS enabled for all origins (development mode)

## Script
`scripts/api_server.py`
