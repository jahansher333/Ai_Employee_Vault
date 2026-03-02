---
id: 029
title: Platinum Tier Cloud Specification
stage: spec
date: 2026-03-01
surface: agent
model: claude-opus-4-6
feature: 006-platinum-tier-cloud
branch: 006-platinum-tier-cloud
user: CEO
command: /sp.specify
labels: ["platinum", "cloud", "specification", "oracle-cloud", "vault-sync", "a2a"]
links:
  spec: specs/006-platinum-tier-cloud/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/006-platinum-tier-cloud/spec.md
  - specs/006-platinum-tier-cloud/checklists/requirements.md
tests:
  - none
---

## Prompt

Platinum Tier: Always-On Cloud + Local Executive
Target: Complete Platinum Tier exactly as per hackathon document
Focus: Cloud 24/7 + synced vault + Odoo cloud deploy + A2A upgrade
Success criteria (document exact):
- All Gold requirements (done)
- Run AI Employee on Cloud 24/7 (watchers + orchestrator + health monitoring on Oracle Cloud Free VM)
- Work-Zone Specialization: Cloud (email triage, drafts, social drafts) + Local (approvals, WhatsApp, payments, send/post)
- Delegation via Synced Vault (Phase 1): /Needs_Action/<domain>/, /Plans/<domain>/, /Pending_Approval/<domain>/, claim-by-move rule, single-writer Dashboard.md, Cloud writes to /Updates/, Local merges
- Vault sync: Git or Syncthing
- Security: no secrets sync (.env, tokens, sessions)
- Deploy Odoo Community on Cloud VM (24/7, HTTPS, backups, health monitoring) + Cloud MCP for draft-only actions + Local approval for posting
- Optional A2A Upgrade (Phase 2): replace file handoffs with direct A2A messages (vault as audit)
- Platinum demo

## Response snapshot

Created Platinum Tier specification with 7 user stories (P1-P3), 30 functional requirements, 14 success criteria, and 7 edge cases. Key areas: Cloud 24/7 deployment on Oracle Cloud Free Tier, work-zone specialization (Cloud=drafts, Local=approvals), synced vault with claim-by-move delegation, security exclusions for secrets, Odoo cloud deployment with HTTPS, optional A2A upgrade (Phase 2), and Platinum demo script. All quality checklist items pass (16/16). No NEEDS CLARIFICATION markers.

## Outcome

- ✅ Impact: Full Platinum Tier specification created — ready for planning
- 🧪 Tests: No tests yet (spec phase)
- 📁 Files: 2 files created (spec.md, checklists/requirements.md)
- 🔁 Next prompts: /sp.clarify or /sp.plan
- 🧠 Reflection: Spec covers all hackathon requirements. A2A correctly scoped as Phase 2 optional. Work-zone split is the key safety innovation.

## Evaluation notes (flywheel)

- Failure modes observed: None — all checklist items pass
- Graders run and results (PASS/FAIL): Quality checklist 16/16 PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Proceed to /sp.plan for architecture decisions
