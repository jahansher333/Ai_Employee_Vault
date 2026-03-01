# Implementation Plan: Gold Tier — Autonomous Employee

**Branch**: `005-gold-tier-autonomous` | **Date**: 2026-02-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/005-gold-tier-autonomous/spec.md`

## Summary

Gold Tier extends the Silver Tier AI Employee with: (1) Odoo Community accounting integration via JSON-RPC for reading invoices, journal entries, and account balances; (2) social media posting across Facebook, Instagram, and Twitter/X (extending existing LinkedIn pattern); (3) three MCP servers (email, social, Odoo) for Claude Code tool access; (4) enhanced weekly audit with Odoo financials and week-over-week comparison; (5) Ralph Wiggum loop for autonomous cross-domain multi-step task execution; (6) error recovery and graceful degradation; (7) architecture documentation.

## Technical Context

**Language/Version**: Python 3.14 (existing project)
**Primary Dependencies**: requests (HTTP/JSON-RPC), playwright (browser automation), fastmcp>=2.0.0 (MCP servers), pandas (data analysis), python-dotenv (env vars), watchdog (file watcher), google-api-python-client (Gmail)
**New Dependencies**: tweepy>=4.14.0 (Twitter/X API v2), facebook-sdk>=3.0.0 (Facebook Graph API) — both optional, simulation mode is default
**Storage**: Obsidian vault (Markdown files with YAML frontmatter), JSON Lines audit logs
**Testing**: pytest (233 tests passing at Silver Tier, target 250+ at Gold)
**Target Platform**: Windows 10 (primary), cross-platform compatible
**Project Type**: Single project — Python scripts with vault-based data flow
**Performance Goals**: MCP tool responses <5s, Odoo sync <30s, social drafts <10s each, Ralph Wiggum 5-step plan <2min
**Constraints**: HITL for all external writes, read-only Odoo, simulation-default social APIs, single-user (CEO)
**Scale/Scope**: 1 user, ~12 scripts, 14+ Agent Skills, 3 MCP servers, 5 external integrations (Gmail, WhatsApp, Odoo, social x3)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Clarity of Requirements | PASS | 32 functional requirements with testable acceptance criteria |
| II. Security and Sensitive Action Approval | PASS | HITL for all publishing, Odoo read-only, credentials in .env only |
| III. Logging and Audit Records | PASS | AuditLogger already in JSON Lines, all new actions logged |
| IV. Modular Code Organization | PASS | Each integration is its own script, single responsibility |
| V. Readable Task and Plan Artifacts | PASS | Plan follows template, will generate tasks.md |
| VI. Detection Only — No Direct External Automation | DEVIATION | Gold Tier intentionally extends beyond Bronze's detection-only principle — publishes to social platforms and reads from Odoo. Justified in Complexity Tracking below. |

## Project Structure

### Documentation (this feature)

```text
specs/005-gold-tier-autonomous/
├── plan.md              # This file
├── research.md          # Phase 0: Technology research
├── data-model.md        # Phase 1: Entity definitions
├── quickstart.md        # Phase 1: Setup guide
├── contracts/           # Phase 1: API contracts
│   ├── odoo-tools.md    # Odoo MCP server tool contracts
│   ├── social-tools.md  # Social MCP server tool contracts
│   └── email-tools.md   # Email MCP server tool contracts
└── tasks.md             # Phase 2: Task breakdown (/sp.tasks)
```

### Source Code (repository root)

```text
scripts/
├── audit_logger.py          # (existing) JSON Lines audit logger
├── data_analyzer.py         # (existing) CSV financial analysis
├── gmail_watcher.py         # (existing) Gmail monitoring
├── linkedin_poster.py       # (existing) LinkedIn draft/publish
├── orchestrator.py          # (modify) Add Gold Tier components
├── process_inbox.py         # (existing) Task routing
├── reasoning_loop.py        # (modify) Extend to Ralph Wiggum loop
├── update_dashboard.py      # (modify) Add Odoo + social sections
├── watcher.py               # (existing) File system watcher
├── weekly_briefing.py       # (modify) Add Odoo data + week-over-week
├── whatsapp_watcher.py      # (existing) WhatsApp monitoring
├── odoo_client.py           # (new) Odoo JSON-RPC client
├── social_poster.py         # (new) Facebook/Instagram/Twitter posting
├── mcp_odoo_server.py       # (new) Odoo MCP server
├── mcp_social_server.py     # (new) Social media MCP server
└── mcp_email_server.py      # (new) Email MCP server

.claude/
├── skills/                  # 14+ Agent Skills (11 existing + 3+ new)
│   ├── odoo-accounting.md   # (new) Odoo integration skill
│   ├── social-poster.md     # (new) Multi-platform social posting
│   └── ralph-wiggum-loop.md # (new) Cross-domain autonomous execution
└── settings.json            # (new) MCP server configuration

tests/
├── test_odoo_client.py      # (new) Odoo client tests
├── test_social_poster.py    # (new) Social poster tests
├── test_mcp_odoo_server.py  # (new) Odoo MCP server tests
├── test_mcp_social_server.py # (new) Social MCP server tests
├── test_mcp_email_server.py # (new) Email MCP server tests
├── test_ralph_wiggum.py     # (new) Ralph Wiggum loop tests
├── test_gold_tier_selftest.py # (new) Gold Tier self-test
└── ... (existing test files)

ARCHITECTURE.md              # (new) Architecture documentation
```

**Structure Decision**: Continue existing flat `scripts/` + `tests/` pattern. Each new integration gets its own script file. MCP servers are separate scripts that wrap existing script functions. No new directories needed — follows established conventions.

## Architecture Decisions

### AD-1: Odoo Integration via JSON-RPC

Odoo Community 17.0+ exposes a JSON-RPC API at `/jsonrpc` (and XML-RPC at `/xmlrpc/2/`). We use JSON-RPC because:
- Native Python `requests` library (already a dependency)
- Session-based authentication with automatic re-auth on expiry
- Read-only operations: `account.move` (invoices), `account.move.line` (journal entries), `account.account` (chart of accounts), `res.partner` (customers)

**Pattern**: `odoo_client.py` provides a `OdooClient` class:
```python
class OdooClient:
    def __init__(self, url, db, user, password)
    def authenticate(self) -> int  # Returns uid
    def search_read(self, model, domain, fields, limit) -> list[dict]
    def list_invoices(self, **filters) -> list[dict]
    def list_journal_entries(self, **filters) -> list[dict]
    def get_account_balances(self) -> list[dict]
    def get_overdue_invoices(self) -> list[dict]
```

### AD-2: Social Media Posting — Multi-Platform Extension

Extend existing `linkedin_poster.py` pattern to Facebook, Instagram, Twitter/X. Create `social_poster.py` that:
- Reuses the `generate_post_draft()` → `save_draft()` → `publish_approved_post()` workflow
- Adapts content per platform (character limits, hashtag styles, formatting)
- Uses platform-specific file prefixes: `FACEBOOK_*.md`, `INSTAGRAM_*.md`, `TWITTER_*.md`
- Supports three modes: `simulate` (default), `api` (real API calls), `playwright` (browser automation for Instagram)

**Platform specifics**:
- **Facebook**: Graph API v18+, `POST /{page-id}/feed`, page access token. No character limit but optimize for engagement (~500 chars).
- **Instagram**: Graph API via Facebook Business. Requires image for posts — in simulation mode, generate caption-only draft. In API mode, use a placeholder brand image.
- **Twitter/X**: API v2, `POST /2/tweets`, OAuth 2.0 (PKCE). Strict 280-character limit enforced at draft time.

### AD-3: MCP Servers — Three Isolated Servers

Three separate MCP servers using `fastmcp` (stdio transport), one per domain:

| Server | File | Wraps | Why Separate |
|--------|------|-------|-------------|
| Odoo | `mcp_odoo_server.py` | `odoo_client.py` | Odoo session state, network dependency |
| Social | `mcp_social_server.py` | `social_poster.py`, `linkedin_poster.py` | Platform API state, Playwright lifecycle |
| Email | `mcp_email_server.py` | `gmail_watcher.py` | Gmail OAuth service, separate failure domain |

Each server:
- Returns structured dicts from every tool (never raises unhandled exceptions)
- On error: `{"error": "description", "success": false}`
- Responds within 5 seconds under normal conditions

### AD-4: Ralph Wiggum Loop — Cross-Domain Extension

Extends existing `reasoning_loop.py` with:

1. **Cross-domain detection**: New `detect_cross_domain()` function checks if a task spans multiple domains (accounting, social, email, reporting)
2. **Domain-tagged steps**: Each plan step gets a `domain` field (e.g., "accounting", "social", "email", "reporting", "general")
3. **Retry logic**: Each step gets one retry on failure before being marked failed
4. **Independent continuation**: If step N fails, skip dependent steps but continue with independent ones
5. **Metrics tracking**: `plan_metrics` dict tracks `steps_completed`, `steps_failed`, `retries`, `time_elapsed`, `domains_touched`
6. **Circular dependency detection**: At plan creation time, validate no step depends on a step that depends back on it

**Implementation**: Add new functions to `reasoning_loop.py` rather than creating a separate file. The Ralph Wiggum loop IS the enhanced reasoning loop.

### AD-5: Enhanced Weekly Audit

Extend `weekly_briefing.py` with:
1. `collect_odoo_financials()` — Pull invoice/journal data from Odoo (falls back to CSV if Odoo unavailable)
2. `collect_social_activity()` — Count posts per platform from vault folders
3. `collect_week_over_week()` — Compare current briefing data against previous week's briefing
4. `collect_health_status()` — Check which services are operational
5. New briefing sections: Odoo Financials, Social Activity, Week-over-Week, System Health

### AD-6: Error Recovery Pattern

Unified error handling across all integrations:
```python
def safe_call(func, *args, service_name="unknown", **kwargs):
    """Call func with retry and structured error handling."""
    try:
        return func(*args, **kwargs)
    except Exception as exc:
        logger.log(f"{service_name}_error", str(exc), "error")
        return {"error": str(exc), "service": service_name, "success": False}
```

Each integration degrades gracefully:
- Odoo down → CSV fallback → "No financial data" in briefing
- Social API error → Mark post "failed", don't move to Done
- MCP server crash → Claude Code gets structured error, suggests retry
- Orchestrator detects crashed component → log + optional restart

## Implementation Order

Following the user's specified order, mapped to implementation phases:

### Phase 1: Odoo Client + Tests (Foundation)
1. Create `scripts/odoo_client.py` with OdooClient class
2. Create `tests/test_odoo_client.py` with mocked JSON-RPC responses
3. Create `.claude/skills/odoo-accounting.md`
4. Update `.env.example` with Odoo environment variables

### Phase 2: Social Media Poster + Tests
1. Create `scripts/social_poster.py` (Facebook, Instagram, Twitter)
2. Create `tests/test_social_poster.py`
3. Create `.claude/skills/social-poster.md`
4. Update `.env.example` with social platform variables

### Phase 3: MCP Servers (Odoo, Social, Email)
1. Create `scripts/mcp_odoo_server.py`
2. Create `scripts/mcp_social_server.py`
3. Create `scripts/mcp_email_server.py`
4. Create `tests/test_mcp_*.py` for each server
5. Create `.claude/settings.json` for MCP configuration

### Phase 4: Enhanced Weekly Audit
1. Modify `scripts/weekly_briefing.py` — add Odoo, social, WoW sections
2. Modify `scripts/update_dashboard.py` — add multi-platform social table
3. Update existing tests to cover new briefing sections

### Phase 5: Ralph Wiggum Loop
1. Modify `scripts/reasoning_loop.py` — add cross-domain detection, domain tags, retry logic, metrics, circular dependency check
2. Create `tests/test_ralph_wiggum.py`
3. Create `.claude/skills/ralph-wiggum-loop.md`

### Phase 6: Orchestrator Update + Error Recovery
1. Modify `scripts/orchestrator.py` — add Gold Tier components, health status, restart logic
2. Update orchestrator tests

### Phase 7: Documentation + Self-Test
1. Create `ARCHITECTURE.md`
2. Update `README.md` with Gold Tier sections
3. Create `tests/test_gold_tier_selftest.py`
4. Verify all 250+ tests pass

## Complexity Tracking

> Constitution Principle VI deviation justified:

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| External writes (social posting) | Gold Tier explicitly requires social media publishing across 4 platforms | Detection-only would not satisfy hackathon Gold Tier requirements. HITL approval gate preserves safety. |
| Odoo read operations | Gold Tier requires real accounting data in briefings | CSV-only analysis (Bronze/Silver) lacks real-time business data. Read-only minimizes risk. |
| MCP server external calls | Gold Tier requires Claude Code to interact with external systems directly | Without MCP, Claude Code cannot autonomously query systems. All MCP tool results go through Claude's judgment before action. |
