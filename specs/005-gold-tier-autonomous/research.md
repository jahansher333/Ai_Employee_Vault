# Research: Gold Tier — Autonomous Employee

**Feature**: 005-gold-tier-autonomous
**Date**: 2026-02-24

## R-001: Odoo Community JSON-RPC API

**Decision**: Use JSON-RPC over HTTP (not XML-RPC)

**Rationale**: JSON-RPC uses `requests` (already a dependency), returns native Python dicts, and supports the same operations as XML-RPC. The endpoint is `/jsonrpc` on the Odoo server.

**Authentication Flow**:
1. POST to `http://<host>:8069/jsonrpc` with method `call` and service `common`, method `login`
2. Pass `{"db": "<dbname>", "login": "<user>", "password": "<pass>"}`
3. Returns `uid` (integer) on success, `false` on failure
4. Use `uid` + password for subsequent `object.execute_kw` calls

**Key Models**:
- `account.move` — Invoices and bills (type: `out_invoice`, `in_invoice`, `out_refund`, `in_refund`)
- `account.move.line` — Journal entry lines
- `account.account` — Chart of accounts
- `res.partner` — Customers and vendors

**Read Pattern**:
```python
# Search + Read in one call
result = jsonrpc_call("object", "execute_kw", [
    db, uid, password,
    "account.move",        # model
    "search_read",         # method
    [[["state", "=", "posted"]]],  # domain filter
    {"fields": ["name", "partner_id", "amount_total", "invoice_date_due", "payment_state"],
     "limit": 100}
])
```

**Overdue Detection**: Filter where `invoice_date_due < today` AND `payment_state != 'paid'`

**Session Expiry**: Odoo sessions expire after inactivity (default ~2 hours). Re-authenticate by calling `common.login` again. Detect expiry when `execute_kw` returns an authentication error.

**Alternatives Considered**:
- XML-RPC (`xmlrpc.client`): More verbose, requires separate calls for search and read
- OdooRPC library: Additional dependency, not widely maintained
- REST API (Odoo Enterprise only): Not available in Community Edition

---

## R-002: Facebook Graph API

**Decision**: Use Facebook Graph API v18+ with page access tokens

**Rationale**: Official API for posting to Facebook Pages. Requires a Facebook App and Page Access Token with `pages_manage_posts` permission.

**Posting Pattern**:
```python
import requests
resp = requests.post(
    f"https://graph.facebook.com/v18.0/{page_id}/feed",
    data={"message": post_text, "access_token": page_access_token},
    timeout=30
)
```

**Rate Limits**: 200 calls per hour per page (very generous for our use case)

**Token Requirements**: Page Access Token (long-lived, ~60 days). Can be refreshed via the Graph API.

**Simulation Mode**: Default. Returns `{"id": "SIM-<timestamp>", "success": True}` without API call.

**Alternatives Considered**:
- Playwright browser automation: Possible but fragile, Facebook actively blocks automation
- Third-party posting services (Buffer, Hootsuite): Adds external dependency and cost

---

## R-003: Instagram Graph API

**Decision**: Use Instagram Graph API via Facebook Business for API mode; simulation default

**Rationale**: Instagram's Content Publishing API requires a Facebook Page linked to an Instagram Business account. Text-only posts are NOT supported — every post requires an image/video.

**Workaround for Text-Only**:
- In simulation mode: Generate caption + hashtags only (no image needed)
- In API mode: Use a configured brand placeholder image URL (set via `INSTAGRAM_DEFAULT_IMAGE_URL` env var)
- Caption-focused: The value is in the caption text and hashtag strategy

**Posting Pattern (API mode)**:
```python
# Step 1: Create media container
container = requests.post(
    f"https://graph.facebook.com/v18.0/{ig_user_id}/media",
    data={"image_url": image_url, "caption": caption, "access_token": token}
)
# Step 2: Publish container
publish = requests.post(
    f"https://graph.facebook.com/v18.0/{ig_user_id}/media_publish",
    data={"creation_id": container.json()["id"], "access_token": token}
)
```

**Rate Limits**: 25 posts per 24 hours per account

**Alternatives Considered**:
- Playwright automation: Instagram heavily blocks automation, risk of account ban
- Omitting Instagram: Would reduce Gold Tier completeness

---

## R-004: Twitter/X API v2

**Decision**: Use Twitter API v2 with OAuth 2.0 (User Context)

**Rationale**: Official API for posting tweets. Free tier allows 1,500 tweets per month (50/day).

**Posting Pattern**:
```python
import requests
resp = requests.post(
    "https://api.twitter.com/2/tweets",
    json={"text": tweet_text},
    headers={"Authorization": f"Bearer {bearer_token}"},
    timeout=30
)
```

**Authentication**: OAuth 2.0 with PKCE for user context, or App-only Bearer Token for read. For posting, need user-level OAuth 2.0 access token.

**Character Limit**: 280 characters. URLs count as 23 characters regardless of length. Must enforce at draft time.

**Rate Limits**: Free tier — 50 tweets/day, 1,500/month. Basic tier ($100/month) — 3,000 tweets/month.

**Alternatives Considered**:
- tweepy library: Adds a dependency but simplifies OAuth flow. Decision: Use `requests` directly for consistency, document tweepy as optional enhancement.
- Playwright: Twitter/X blocks automation aggressively

---

## R-005: FastMCP Server Pattern

**Decision**: Use `fastmcp` library with stdio transport for all three MCP servers

**Rationale**: FastMCP 2.0+ provides a simple decorator-based API for creating MCP tools. Already in requirements.txt.

**Server Pattern**:
```python
from fastmcp import FastMCP

mcp = FastMCP("odoo-server")

@mcp.tool()
def list_invoices(limit: int = 50) -> dict:
    """List invoices from Odoo."""
    try:
        client = get_odoo_client()
        invoices = client.list_invoices(limit=limit)
        return {"invoices": invoices, "count": len(invoices)}
    except Exception as e:
        return {"error": str(e), "success": False}

if __name__ == "__main__":
    mcp.run()
```

**Error Handling**: Every tool function wraps in try/except, returns structured dict, never raises.

**Configuration** (`.claude/settings.json`):
```json
{
  "mcpServers": {
    "odoo": {
      "command": "python",
      "args": ["scripts/mcp_odoo_server.py"],
      "env": {"VAULT_PATH": "D:/Hac3/Ai_Employee_Vault"}
    }
  }
}
```

**Alternatives Considered**:
- Single monolithic MCP server: Rejected — one crash takes down all tools. Three servers isolate failure domains.
- HTTP transport: More complex setup, stdio is simpler for local-first architecture.

---

## R-006: Ralph Wiggum Loop — Cross-Domain Reasoning

**Decision**: Extend existing `reasoning_loop.py` with domain awareness, retry logic, and metrics

**Rationale**: The existing reasoning loop already handles complexity detection, plan creation, and step execution. Ralph Wiggum adds cross-domain intelligence, not a separate system.

**Cross-Domain Detection**:
```python
DOMAIN_KEYWORDS = {
    "accounting": ["invoice", "payment", "expense", "revenue", "ledger", "odoo"],
    "social": ["post", "linkedin", "facebook", "instagram", "twitter", "publish"],
    "email": ["email", "gmail", "reply", "forward", "send"],
    "reporting": ["report", "briefing", "audit", "dashboard", "summary"],
}
```

A task is cross-domain when it matches keywords from 2+ domains.

**Retry Logic**: Per-step retry with configurable max (default 1 retry):
```python
def execute_step_with_retry(plan_path, step_num, vault_path, logger, max_retries=1):
    for attempt in range(max_retries + 1):
        success = execute_step(plan_path, step_num, vault_path, logger)
        if success:
            return True
        logger.log("step_retry", f"step_{step_num}", "warning",
                   details={"attempt": attempt + 1})
    return False
```

**Circular Dependency Detection**: At plan creation, build a directed graph of step dependencies and check for cycles using DFS.

**Alternatives Considered**:
- Separate `ralph_wiggum.py` file: Rejected — would duplicate the entire reasoning loop infrastructure. Better to extend.
- LLM-based planning: Out of scope — plans are rule-based from task content, not LLM-generated.

---

## R-007: Error Recovery Patterns

**Decision**: Unified `safe_call()` wrapper + per-service health tracking

**Rationale**: Each integration can fail independently. The system must continue operating with reduced capabilities rather than crashing entirely.

**Health Status Model**:
```python
class ServiceHealth:
    OPERATIONAL = "operational"
    DEGRADED = "degraded"       # Working but with issues
    UNAVAILABLE = "unavailable" # Completely down
```

**Tracked in orchestrator**: Dict mapping service name → health status, last checked, error count.

**Fallback Chain**:
- Odoo unavailable → Try CSV files → Report "no financial data"
- Facebook API error → Log error → Keep post in Approved/ (don't move to Done)
- Gmail unreachable → Skip email section in briefing
- MCP server crash → Return error dict to Claude Code

**Alternatives Considered**:
- Circuit breaker pattern: Over-engineered for single-user system with at most 5 integrations
- Automatic retry with exponential backoff: Useful for transient errors, but simple one-retry is sufficient for our scale
