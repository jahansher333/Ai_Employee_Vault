---
id: 030
title: Platinum Tier Implementation Plan
stage: plan
date: 2026-03-01
surface: agent
model: claude-opus-4-6
feature: 006-platinum-tier-cloud
branch: 006-platinum-tier-cloud
user: CEO
command: /sp.plan
labels: ["platinum", "plan", "cloud-deployment", "oracle-cloud", "vault-sync", "zone-config", "odoo", "a2a"]
links:
  spec: specs/006-platinum-tier-cloud/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/006-platinum-tier-cloud/plan.md
  - specs/006-platinum-tier-cloud/research.md
  - specs/006-platinum-tier-cloud/data-model.md
  - specs/006-platinum-tier-cloud/quickstart.md
  - specs/006-platinum-tier-cloud/contracts/zone-config.yaml
tests:
  - none
---

## Prompt

Platinum Tier: Always-On Cloud + Local Executive
Use specs from previous phase.
Success criteria:
- Cloud VM: Oracle Cloud Free VM setup + deploy watchers/orchestrator/health monitoring
- Specialization: Cloud drafts (email/social/Odoo), Local executes (WhatsApp/payments/send)
- Synced Vault: Git setup (push/pull), Syncthing alternative, /Needs_Action/<domain>/ folders, claim-by-move (/In_Progress/<agent>/)
- Odoo Cloud: Deploy on VM, HTTPS (nginx), backups (pg_dump cron), health monitoring (watchdog)
- Cloud MCP for Odoo drafts + Local approval
- A2A Phase 2: Optional direct messages (socket or API, vault audit)
- Demo test: Simulate offline Local → Cloud draft → sync → Local approve → execute
Tech stack: Oracle Cloud VM, Git/Syncthing, nginx, pg_dump
What the agent does: Output plan.md with step-by-step (VM setup, sync config, Odoo deploy, A2A). Ready for /sp.tasks.

## Response snapshot

Created implementation plan with 7 phases: (1) Zone Configuration + Vault Structure, (2) Vault Sync Mechanism, (3) Cloud VM Deployment + Health Monitoring, (4) Odoo Cloud Deployment, (5) Local Approval Workflow, (6) A2A Upgrade (optional Phase 2), (7) Platinum Demo + Self-Test. Produced 5 artifacts: plan.md, research.md, data-model.md, quickstart.md, contracts/zone-config.yaml. Constitution Check passed with one justified deviation (Principle VI — Platinum explicitly upgrades beyond Bronze detection-only). Identified 3 ADR candidates.

## Outcome

- ✅ Impact: Full Platinum Tier implementation plan — ready for /sp.tasks
- 🧪 Tests: No tests yet (plan phase)
- 📁 Files: 5 files created (plan.md, research.md, data-model.md, quickstart.md, zone-config.yaml)
- 🔁 Next prompts: /sp.tasks to generate implementation tasks
- 🧠 Reflection: Zone enforcement as env var is simple and effective. Git sync as primary over Syncthing keeps operational complexity low. Claim-by-move via os.rename is elegant for single-filesystem concurrency.

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): Constitution Check 6/6 PASS (1 justified deviation)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Proceed to /sp.tasks for task generation
