---
id: 023
title: Gold tier autonomous specification
stage: spec
date: 2026-02-24
surface: agent
model: claude-opus-4-6
feature: 005-gold-tier-autonomous
branch: 005-gold-tier-autonomous
user: jansher
command: /sp.specify
labels: ["gold-tier", "spec", "odoo", "social-media", "mcp-servers", "ralph-wiggum-loop"]
links:
  spec: specs/005-gold-tier-autonomous/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/005-gold-tier-autonomous/spec.md
  - specs/005-gold-tier-autonomous/checklists/requirements.md
tests:
  - null
---

## Prompt

Gold Tier: Autonomous Employee – Full Requirements
Target: Complete Gold Tier exactly as per hackathon document
Focus: Odoo accounting + social integrations + weekly audit + advanced loop
Success criteria (document exact):
- All Silver requirements (done)
- Full cross-domain integration (Personal + Business)
- Odoo Community accounting system (self-hosted) + MCP integration (JSON-RPC APIs)
- Integrate Facebook and Instagram (post messages + generate summary)
- Integrate Twitter (X) (post messages + generate summary)
- Multiple MCP servers (email, social, Odoo)
- Weekly Business and Accounting Audit with CEO Briefing generation
- Error recovery and graceful degradation
- Comprehensive audit logging
- Ralph Wiggum loop for autonomous multi-step task completion
- Documentation of architecture and lessons learned
- All AI functionality as Agent Skills
Constraints:
- Local-first where possible (Odoo self-hosted)
- Secure, HITL for sensitive actions
- Use existing vault + watchers + MCP base
What the agent does: Generate complete Gold Tier specification with all functional requirements, success criteria, edge cases, and scope boundaries.

## Response snapshot

Created full Gold Tier specification on branch `005-gold-tier-autonomous`:

- **7 user stories** across 3 priority levels:
  - P1: Odoo Accounting Integration, Social Media Posting (Facebook/Instagram/Twitter), Weekly Business Audit
  - P2: MCP Servers (email/social/Odoo), Ralph Wiggum Loop (autonomous multi-step execution), Error Recovery
  - P3: Architecture Documentation

- **32 functional requirements** (FR-001 to FR-032) covering:
  - Odoo accounting (FR-001 to FR-005): invoice reading, journal entries, overdue detection, CSV fallback, secure credentials
  - Social media (FR-006 to FR-012): Facebook/Instagram/Twitter drafts, platform prefixes, simulation mode, publishing, activity summary
  - MCP servers (FR-013 to FR-016): Odoo MCP, social MCP, email MCP, structured error responses
  - Weekly audit (FR-017 to FR-020): Odoo financials, social summary, week-over-week comparison, recommended actions
  - Ralph Wiggum loop (FR-021 to FR-025): cross-domain detection, domain-tagged plans, autonomous execution, error recovery, metrics
  - Error recovery (FR-026 to FR-029): graceful degradation, structured logging, crash detection, health status
  - Documentation (FR-030 to FR-032): ARCHITECTURE.md, Agent Skills, comprehensive audit trail

- **12 success criteria** (SC-001 to SC-012) with measurable targets
- **7 edge cases** (invalid credentials, rate limiting, circular dependencies, file conflicts, empty data, character limits, session expiry)
- **6 key entities** (Invoice, Social Post, Audit Report, Execution Plan, MCP Tool, Health Status)
- **Quality checklist**: 16/16 PASS — no [NEEDS CLARIFICATION] markers

## Outcome

- ✅ Impact: Complete Gold Tier specification ready for planning — 32 requirements, 12 success criteria, 7 user stories
- 🧪 Tests: No tests (spec phase)
- 📁 Files: 2 created (spec.md, checklists/requirements.md)
- 🔁 Next prompts: `/sp.plan` for Gold Tier implementation planning, then `/sp.tasks` for task breakdown
- 🧠 Reflection: Spec builds cleanly on Silver Tier patterns (vault workflow, approval routing, audit logging). Odoo read-only scope and simulation-default for social APIs are pragmatic constraints that reduce risk while demonstrating full integration capability.

## Evaluation notes (flywheel)

- Failure modes observed: PowerShell create-new-feature.ps1 had a partial argument parsing error but branch and spec directory were created successfully
- Graders run and results (PASS/FAIL): Quality checklist 16/16 PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Run /sp.plan to generate implementation architecture for Gold Tier
