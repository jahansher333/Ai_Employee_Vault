---
id: "015"
title: WhatsApp LinkedIn Silver Spec
stage: spec
date: 2026-02-21
surface: agent
model: claude-opus-4-6
feature: whatsapp-linkedin-silver
branch: 004-whatsapp-linkedin-silver
user: human
command: /sp.specify
labels: ["silver-tier", "whatsapp", "linkedin", "specification", "watcher"]
links:
  spec: specs/004-whatsapp-linkedin-silver/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/004-whatsapp-linkedin-silver/spec.md
  - specs/004-whatsapp-linkedin-silver/checklists/requirements.md
tests:
  - N/A (specification phase)
---

## Prompt

Silver Tier: Add WhatsApp Watcher + LinkedIn Auto-Post Skill. WhatsApp Watcher uses Playwright to monitor WhatsApp Web for urgent messages (keywords: urgent, invoice, payment, help). Creates .md files in Needs_Action/. LinkedIn Auto-Post generates sales post drafts in Pending_Approval/, simulates posting on approval. Both integrate with existing vault pipeline.

## Response snapshot

Created comprehensive spec with 5 user stories (2x P1, 2x P2, 1x P3), 17 functional requirements, 10 success criteria, 8 edge cases. WhatsApp Watcher covers message detection, keyword filtering, session management, ledger dedup. LinkedIn Auto-Post covers draft generation, approval workflow, simulated posting, Dashboard integration. Checklist 16/16 PASS.

## Outcome

- Impact: Full specification for WhatsApp + LinkedIn Silver Tier features
- Tests: N/A (specification phase)
- Files: 2 created (spec.md, checklists/requirements.md)
- Next prompts: /sp.plan or /sp.clarify
- Reflection: Combined two features into one spec for efficient Silver Tier delivery

## Evaluation notes (flywheel)

- Failure modes observed: PowerShell script positional parameter error (branch created anyway)
- Graders run and results (PASS/FAIL): Checklist 16/16 PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
