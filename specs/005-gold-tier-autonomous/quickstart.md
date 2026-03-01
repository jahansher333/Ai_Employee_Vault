# Quickstart: Gold Tier — Autonomous Employee

**Feature**: 005-gold-tier-autonomous
**Prerequisites**: Silver Tier complete (233 tests passing)

## 1. Odoo Community Setup

### Install Odoo (Docker — recommended for development)

```bash
# Pull and run Odoo Community 17.0 with PostgreSQL
docker run -d -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo \
  -e POSTGRES_DB=postgres --name db postgres:15
docker run -d -p 8069:8069 --name odoo --link db:db \
  -e HOST=db -e USER=odoo -e PASSWORD=odoo odoo:17.0

# Access at http://localhost:8069
# Create database, set master password, create admin user
```

### Configure Environment Variables

Add to `.env`:
```bash
# Odoo Community (Gold Tier)
ODOO_URL=http://localhost:8069
ODOO_DB=mycompany
ODOO_USER=admin
ODOO_PASSWORD=admin
```

### Create Sample Data in Odoo

1. Go to Invoicing → Customers → Create some test customers
2. Go to Invoicing → Invoices → Create a few invoices (some overdue)
3. Go to Accounting → Journal Entries to see auto-generated entries

### Verify Connection

```bash
python scripts/odoo_client.py --test
# Expected: "Connected to Odoo (uid=2, version=17.0)"
```

## 2. Social Media Setup

### Simulation Mode (Default — No API Keys Needed)

Social posting works in simulation mode by default. No API credentials required.

```bash
# Draft a Facebook post
python scripts/social_poster.py --draft "AI Automation" --platform facebook

# Draft a Twitter post (enforces 280-char limit)
python scripts/social_poster.py --draft "AI Automation" --platform twitter

# Draft an Instagram caption
python scripts/social_poster.py --draft "AI Automation" --platform instagram
```

### Real API Mode (Optional)

Add to `.env` for real posting:

```bash
# Facebook (requires Facebook App + Page Access Token)
FACEBOOK_POST_MODE=api
FACEBOOK_PAGE_ID=your_page_id
FACEBOOK_PAGE_ACCESS_TOKEN=your_token

# Instagram (requires Facebook Business + Instagram Business Account)
INSTAGRAM_POST_MODE=api
INSTAGRAM_USER_ID=your_ig_user_id
INSTAGRAM_ACCESS_TOKEN=your_token
INSTAGRAM_DEFAULT_IMAGE_URL=https://your-brand-image.jpg

# Twitter/X (requires Developer Account + OAuth 2.0)
TWITTER_POST_MODE=api
TWITTER_BEARER_TOKEN=your_bearer_token
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
```

## 3. MCP Servers

### Verify MCP Server Configuration

After implementation, `.claude/settings.json` will contain MCP server configs. Restart Claude Code to load them.

```bash
# Test each MCP server independently
python -m fastmcp dev scripts/mcp_odoo_server.py
python -m fastmcp dev scripts/mcp_social_server.py
python -m fastmcp dev scripts/mcp_email_server.py
```

### Use MCP Tools in Claude Code

Once configured, Claude Code can directly:
- "What invoices are overdue?" → Calls `list_invoices(overdue_only=true)`
- "Draft a tweet about our new feature" → Calls `draft_social_post(topic, platform="twitter")`
- "Check unread emails" → Calls `fetch_unread_emails()`

## 4. Weekly Audit (Enhanced)

The weekly audit now includes Odoo data and social activity:

```bash
# Generate enhanced briefing (includes Odoo + social + WoW comparison)
python scripts/weekly_briefing.py

# Scheduler runs automatically Sunday 8 PM PKT
python scripts/weekly_briefing.py --schedule
```

## 5. Ralph Wiggum Loop

The enhanced reasoning loop handles cross-domain tasks:

```bash
# Process a cross-domain task
python scripts/reasoning_loop.py --file Needs_Action/complex-task.md

# Run all active plans with retry logic
python scripts/reasoning_loop.py --run-plans
```

## 6. Launch Everything

```bash
# Full orchestrator with all Gold Tier components
python scripts/orchestrator.py

# Or selectively disable components
python scripts/orchestrator.py --no-odoo --no-social
```

## 7. Run Tests

```bash
# Full test suite (250+ tests expected)
python -m pytest tests/ -v

# Gold Tier tests only
python -m pytest tests/test_odoo_client.py tests/test_social_poster.py tests/test_ralph_wiggum.py -v

# Gold Tier self-test
python -m pytest tests/test_gold_tier_selftest.py -v
```

## Required Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VAULT_PATH` | Yes | Project root | Path to Obsidian vault |
| `ODOO_URL` | For Odoo | None | Odoo server URL |
| `ODOO_DB` | For Odoo | None | Odoo database name |
| `ODOO_USER` | For Odoo | None | Odoo login username |
| `ODOO_PASSWORD` | For Odoo | None | Odoo login password |
| `FACEBOOK_POST_MODE` | No | simulate | `simulate` or `api` |
| `FACEBOOK_PAGE_ID` | For FB API | None | Facebook Page ID |
| `FACEBOOK_PAGE_ACCESS_TOKEN` | For FB API | None | Page access token |
| `INSTAGRAM_POST_MODE` | No | simulate | `simulate` or `api` |
| `INSTAGRAM_USER_ID` | For IG API | None | Instagram Business user ID |
| `INSTAGRAM_ACCESS_TOKEN` | For IG API | None | Instagram access token |
| `INSTAGRAM_DEFAULT_IMAGE_URL` | For IG API | None | Default image for posts |
| `TWITTER_POST_MODE` | No | simulate | `simulate` or `api` |
| `TWITTER_BEARER_TOKEN` | For X API | None | Twitter Bearer token |
| `TWITTER_API_KEY` | For X API | None | Twitter API key |
| `TWITTER_API_SECRET` | For X API | None | Twitter API secret |
| `TWITTER_ACCESS_TOKEN` | For X API | None | Twitter user access token |
| `TWITTER_ACCESS_TOKEN_SECRET` | For X API | None | Twitter user access token secret |
