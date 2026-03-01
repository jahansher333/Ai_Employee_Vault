---
id: 024
title: Gold tier implementation plan
stage: plan
date: 2026-02-24
surface: agent
model: claude-opus-4-6
feature: 005-gold-tier-autonomous
branch: 005-gold-tier-autonomous
user: jansher
command: /sp.plan
labels: ["gold-tier", "plan", "odoo", "social-media", "mcp-servers", "ralph-wiggum-loop", "architecture"]
links:
  spec: specs/005-gold-tier-autonomous/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/005-gold-tier-autonomous/plan.md
  - specs/005-gold-tier-autonomous/research.md
  - specs/005-gold-tier-autonomous/data-model.md
  - specs/005-gold-tier-autonomous/quickstart.md
  - specs/005-gold-tier-autonomous/contracts/odoo-tools.md
  - specs/005-gold-tier-autonomous/contracts/social-tools.md
  - specs/005-gold-tier-autonomous/contracts/email-tools.md
tests:
  - null
---

## Prompt

Gold Tier: Autonomous Employee – Full Requirements
Use specs from previous phase.
Success criteria:
- Odoo Community: self-hosted local instance + MCP for JSON-RPC (draft invoices, expenses)
- Social Integrations: Facebook, Instagram, Twitter (X) post + summary skills
- Weekly Audit: Schedule + CEOBriefingSkill (revenue, bottlenecks, suggestions)
- Ralph Wiggum Loop: Full autonomous task completion (iterate until Done)
- Multiple MCP servers: email, social (FB/IG/X), Odoo
- Error Recovery: retry logic + graceful degradation
- Audit Logging: expand /Logs/ to JSON
- Documentation: README + architecture diagram
- Order: Odoo setup → social MCP → audit → loop → docs
Tech stack: Python + Odoo Community + requests + playwright
What the agent does: Output plan.md with step-by-step order, Odoo install guide, MCP extensions, loop logic. Ready for /sp.tasks.

## Response snapshot

Created comprehensive Gold Tier implementation plan with 7 artifacts:

**plan.md** — Full implementation plan covering:
- Technical Context: Python 3.14, requests, fastmcp, playwright, pandas
- Constitution Check: 6/6 principles checked (1 justified deviation for external writes)
- 6 Architecture Decisions: Odoo JSON-RPC, multi-platform social posting, 3 isolated MCP servers, Ralph Wiggum loop extension, enhanced weekly audit, error recovery patterns
- 7-phase implementation order: Odoo client → Social poster → MCP servers → Weekly audit → Ralph Wiggum → Orchestrator update → Documentation
- Project structure: 6 new scripts, 7 new test files, 3 new agent skills, 1 architecture doc

**research.md** — 7 research decisions:
- R-001: Odoo JSON-RPC API (auth flow, key models, search_read pattern, session expiry handling)
- R-002: Facebook Graph API v18+ (page access tokens, 200 calls/hr limit)
- R-003: Instagram Graph API (text-only workaround with placeholder image, 25 posts/day)
- R-004: Twitter/X API v2 (OAuth 2.0, 280-char enforcement, 50 tweets/day free tier)
- R-005: FastMCP server pattern (decorator-based tools, stdio transport, error handling)
- R-006: Ralph Wiggum cross-domain detection (domain keywords, retry logic, circular dep check)
- R-007: Error recovery (health status model, fallback chains, safe_call wrapper)

**data-model.md** — 6 entities: Invoice, Social Post, Audit Report, Execution Plan, MCP Tool, Health Status

**contracts/** — 3 MCP server tool contracts:
- odoo-tools.md: 5 tools (list_invoices, get_account_balances, get_journal_entries, get_financial_summary, check_odoo_connection)
- social-tools.md: 4 tools (draft_social_post, list_social_drafts, publish_social_post, get_social_activity_summary)
- email-tools.md: 5 tools (fetch_unread_emails, send_email, reply_to_email, mark_email_read, create_email_task)

**quickstart.md** — Setup guide covering Odoo Docker install, social API configuration, MCP server testing, and environment variable reference

## Outcome

- ✅ Impact: Complete Gold Tier implementation plan with all architecture decisions, research, data models, contracts, and setup guide
- 🧪 Tests: No tests (plan phase)
- 📁 Files: 7 created (plan.md, research.md, data-model.md, quickstart.md, 3 contracts)
- 🔁 Next prompts: `/sp.tasks` to generate task breakdown, then `/sp.implement` to execute
- 🧠 Reflection: Key insight: Instagram requires images for posts (no text-only API) — simulation mode handles this gracefully. Three separate MCP servers isolate failure domains, preventing one crash from taking down all tools.

## Evaluation notes (flywheel)

- Failure modes observed: Web search/research agents hit API rate limits — fell back to internal knowledge for API patterns
- Graders run and results (PASS/FAIL): Constitution check 6/6 PASS (1 justified deviation documented)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Run /sp.tasks to generate implementation task list
