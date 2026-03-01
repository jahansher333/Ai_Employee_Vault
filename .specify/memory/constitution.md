<!--
Sync Impact Report
===================
- Version change: 0.0.0 (template) → 1.0.0
- Modified principles: N/A (initial creation)
- Added sections:
  - 6 Core Principles (I–VI)
  - Operational Constraints
  - Development Workflow
  - Governance
- Removed sections: None (template placeholders replaced)
- Templates requiring updates:
  - `.specify/templates/plan-template.md` — ⚠ pending (Constitution Check section references generic gates; update to reference Bronze Tier principles on first /sp.plan run)
  - `.specify/templates/spec-template.md` — ✅ compatible (FR/SC structure aligns with Principle I)
  - `.specify/templates/tasks-template.md` — ✅ compatible (phase structure supports modularity and checkpoints)
- Follow-up TODOs: None
-->

# Bronze Tier AI Employee Constitution

## Core Principles

### I. Clarity of Requirements

Every feature, task, and change MUST begin with an unambiguous specification
before any implementation work starts.

- All requirements MUST use RFC 2119 keywords (MUST, SHOULD, MAY) to indicate
  obligation level.
- Acceptance criteria MUST be testable: each criterion has a concrete
  pass/fail condition.
- Ambiguous or incomplete requirements MUST be flagged with
  `NEEDS CLARIFICATION` and resolved before implementation proceeds.
- User stories MUST follow Given/When/Then format for acceptance scenarios.
- No feature enters implementation without a reviewed `spec.md` containing
  functional requirements and success criteria.

### II. Security and Sensitive Action Approval

All actions that affect external systems, credentials, or user data MUST
require explicit human approval before execution.

- The system MUST NOT execute destructive operations (delete, overwrite,
  force-push) without user confirmation.
- Secrets, tokens, and credentials MUST NOT appear in code, logs, or version
  control; use environment variables and `.env` files exclusively.
- Any action touching authentication, authorization, or access control MUST
  be reviewed and approved by the user before execution.
- Sensitive configuration changes MUST be logged with the approver identity
  and timestamp.
- All dependencies MUST be reviewed for known vulnerabilities before adoption.

### III. Logging and Audit Records

Every significant action, decision, and change MUST produce a traceable
record.

- All user prompts MUST be recorded as Prompt History Records (PHRs) with
  verbatim input preserved.
- Architectural decisions MUST be surfaced for ADR documentation when they
  meet the significance threshold (impact + alternatives + cross-cutting scope).
- Runtime operations MUST produce structured logs with timestamp, action type,
  actor, and outcome.
- Audit trails MUST be append-only; existing records MUST NOT be modified
  or deleted.
- PHRs MUST be routed to the correct subdirectory under `history/prompts/`
  based on stage (constitution, feature, or general).

### IV. Modular Code Organization

Code MUST be organized into small, single-responsibility modules that can
be developed, tested, and understood independently.

- Each module MUST have a clear, documented purpose and well-defined
  boundaries.
- Modules MUST NOT contain circular dependencies.
- Shared utilities MUST be extracted only when used by three or more modules;
  premature abstraction is prohibited.
- File structure MUST follow the project layout defined in `plan.md` for
  each feature.
- Each module MUST be independently testable without requiring the full
  application context.

### V. Readable Task and Plan Artifacts

All planning and task artifacts MUST be written for human comprehension first,
machine parsing second.

- Plans (`plan.md`) MUST include a summary, technical context, project
  structure, and constitution compliance check.
- Tasks (`tasks.md`) MUST be organized by user story with clear phase
  boundaries and dependency ordering.
- Every task MUST include an exact file path and a concrete deliverable
  description.
- Checkpoints between phases MUST define what "done" looks like for
  independent validation.
- Artifact formatting MUST use consistent Markdown with heading hierarchy
  preserved across all features.

### VI. Detection Only — No Direct External Automation

The Bronze Tier AI Employee MUST detect, report, and recommend actions but
MUST NOT autonomously execute changes against external systems.

- The system MUST NOT send emails, messages, API calls to third-party
  services, or trigger webhooks without explicit user initiation.
- Detection results MUST be presented as structured recommendations with
  context and suggested next steps.
- All external integrations MUST operate in read-only or observation mode
  unless the user explicitly authorizes a write action per-invocation.
- Automated scheduling, polling, or background jobs that mutate external
  state are prohibited at the Bronze Tier.
- The boundary between detection and action MUST be clearly documented in
  every feature spec that involves external systems.

## Operational Constraints

- **Technology stack**: Determined per feature; no framework is mandated at
  the constitution level. Each feature spec MUST declare its stack.
- **Dependency policy**: Prefer well-maintained, widely-adopted libraries.
  Pin versions explicitly. Review changelogs before upgrading.
- **Error handling**: All modules MUST handle errors explicitly. Silent
  failures are prohibited. Errors MUST propagate with context sufficient
  for diagnosis.
- **Performance**: Performance budgets MUST be defined per feature in the
  spec. No global mandate, but measured baselines are required before
  optimization work.
- **Secrets management**: `.env` files for local development. No secrets in
  source control. Document required environment variables in each feature's
  quickstart guide.

## Development Workflow

- **Spec before code**: No implementation without a reviewed `spec.md`.
- **Plan before tasks**: No task generation without a reviewed `plan.md`
  that passes the Constitution Check.
- **Smallest viable diff**: Each change MUST address exactly what was
  requested. No unrelated refactoring or speculative improvements.
- **Checkpoint validation**: At each phase boundary in `tasks.md`, verify
  that the completed work is independently functional before proceeding.
- **PHR on every interaction**: Every user prompt that results in
  implementation, planning, debugging, or specification work MUST produce
  a PHR.
- **ADR on significant decisions**: When architectural decisions meet the
  three-part significance test (impact + alternatives + cross-cutting),
  suggest documentation via `/sp.adr`.

## Governance

This constitution is the authoritative source of project principles for
the Bronze Tier AI Employee. All plans, specs, tasks, and code reviews
MUST verify compliance with these principles.

- **Amendment process**: Any principle change MUST be documented with
  rationale, approved by the project owner, and reflected in a version
  bump following semantic versioning (MAJOR for removals/redefinitions,
  MINOR for additions/expansions, PATCH for clarifications).
- **Compliance review**: Every `plan.md` MUST include a Constitution Check
  section that verifies alignment with all six principles before
  implementation proceeds.
- **Conflict resolution**: When project constraints conflict with a
  principle, the conflict MUST be documented in the plan's Complexity
  Tracking table with justification for the deviation.
- **Versioning**: Follows semantic versioning. See amendment process above.

**Version**: 1.0.0 | **Ratified**: 2026-02-17 | **Last Amended**: 2026-02-17
