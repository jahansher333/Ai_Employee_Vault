# Data Model: Gold Tier — Autonomous Employee

**Feature**: 005-gold-tier-autonomous
**Date**: 2026-02-24

## Entities

### Invoice (from Odoo)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| id | int | Odoo `account.move.id` | Odoo record ID |
| name | str | Odoo `account.move.name` | Invoice number (e.g., "INV/2026/0001") |
| partner_name | str | Odoo `res.partner.name` | Customer/vendor name |
| partner_id | int | Odoo `account.move.partner_id` | Odoo partner record ID |
| move_type | str | Odoo `account.move.move_type` | `out_invoice`, `in_invoice`, `out_refund`, `in_refund` |
| amount_total | float | Odoo `account.move.amount_total` | Total invoice amount (currency) |
| amount_residual | float | Odoo `account.move.amount_residual` | Remaining unpaid amount |
| currency | str | Odoo `account.move.currency_id.name` | Currency code (e.g., "USD", "PKR") |
| invoice_date | str | Odoo `account.move.invoice_date` | Invoice date (YYYY-MM-DD) |
| invoice_date_due | str | Odoo `account.move.invoice_date_due` | Due date (YYYY-MM-DD) |
| payment_state | str | Odoo `account.move.payment_state` | `not_paid`, `partial`, `paid`, `reversed` |
| state | str | Odoo `account.move.state` | `draft`, `posted`, `cancel` |
| is_overdue | bool | Computed | `invoice_date_due < today AND payment_state != 'paid'` |

**Validation Rules**:
- `amount_total >= 0`
- `invoice_date_due` must be a valid date or null
- `payment_state` must be one of: `not_paid`, `partial`, `paid`, `reversed`

---

### Social Post

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| platform | str | Generated | `facebook`, `instagram`, `twitter`, `linkedin` |
| topic | str | User input | Post topic/subject |
| template | str | System | Template name used for generation |
| body | str | Generated | Post content text |
| hashtags | list[str] | Generated | Platform-appropriate hashtags |
| char_count | int | Computed | Character count (critical for Twitter) |
| status | str | Lifecycle | `draft`, `approved`, `posted`, `failed` |
| generated_at | str | System | ISO 8601 timestamp |
| approved_at | str | User action | ISO 8601 timestamp (when moved to Approved/) |
| posted_at | str | System | ISO 8601 timestamp (when published) |
| post_mode | str | Config | `simulate`, `api`, `playwright` |
| post_id | str | API response | Platform-specific post ID |
| file_prefix | str | Convention | `FACEBOOK_`, `INSTAGRAM_`, `TWITTER_`, `LINKEDIN_` |

**State Transitions**:
```
draft → approved → posted
                 → failed → (stays in Approved/ for retry)
```

**Validation Rules**:
- Twitter posts: `char_count <= 280` enforced at draft time
- Instagram posts: Must have hashtag suggestions
- All platforms: `body` must not be empty
- File naming: `{PREFIX}{HHMMSS}_{sanitized-topic}.md`

---

### Audit Report (Enhanced Weekly Briefing)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| date | str | Computed | Briefing target date (YYYY-MM-DD) |
| generated_at | str | System | ISO 8601 generation timestamp |
| status | str | Lifecycle | `new`, `reviewed` |
| odoo_available | bool | Runtime | Whether Odoo data was included |
| financials | dict | Odoo/CSV | Revenue, expenses, net income, overdue invoices |
| social_activity | dict | Vault scan | Posts per platform, total published this week |
| task_pipeline | dict | Vault scan | Counts per queue (Needs_Action, Plans, etc.) |
| bottlenecks | list[dict] | Analysis | Stale tasks, blocked plans, error patterns |
| week_over_week | dict | Comparison | Revenue change %, expense change %, task velocity |
| health_status | dict | Orchestrator | Per-service operational status |
| recommendations | list[str] | Analysis | Prioritized action items |

**New Briefing Sections** (extending Silver):
- Odoo Financial Summary (revenue, expenses, overdue invoices table)
- Social Media Activity (posts per platform this week)
- Week-over-Week Comparison (delta metrics)
- System Health (per-service status)

---

### Execution Plan (Ralph Wiggum Enhanced)

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| type | str | System | Always `plan` |
| source_file | str | Task file | Original task filename |
| source_type | str | Task metadata | `email`, `whatsapp`, `task`, `cross_domain` |
| objective | str | Task content | Plan objective title |
| priority | str | Task metadata | `low`, `medium`, `high` |
| status | str | Lifecycle | `active`, `awaiting_approval`, `completed`, `failed` |
| is_cross_domain | bool | Detection | Whether task spans multiple domains |
| domains | list[str] | Detection | Which domains are involved |
| total_steps | int | Generated | Total number of plan steps |
| completed_steps | int | Execution | Steps completed so far |
| failed_steps | int | Execution | Steps that failed after retry |
| retries | int | Execution | Total retry attempts |
| created_at | str | System | ISO 8601 timestamp |
| completed_at | str | System | ISO 8601 timestamp (when all steps done) |
| time_elapsed_ms | int | Computed | Total execution time in milliseconds |

**Step Structure** (enhanced):
| Field | Type | Description |
|-------|------|-------------|
| step_num | int | Sequential step number |
| description | str | What this step does |
| category | str | `analysis`, `execution`, `security`, `review`, `cleanup` |
| domain | str | `accounting`, `social`, `email`, `reporting`, `general` |
| requires_approval | bool | Whether human approval is needed |
| is_complete | bool | Whether step has been executed |
| is_failed | bool | Whether step failed after retry |
| depends_on | list[int] | Step numbers this step depends on |
| retry_count | int | Number of retries attempted |

**Validation Rules**:
- No circular dependencies (checked at plan creation)
- Failed steps must have `retry_count >= 1` before being marked failed
- Cross-domain plans must have steps from 2+ domains

---

### MCP Tool

| Field | Type | Description |
|-------|------|-------------|
| server | str | `odoo`, `social`, `email` |
| tool_name | str | Function name (e.g., `list_invoices`) |
| parameters | dict | Input parameters schema |
| returns | dict | Output schema (always includes `success` or `error` key) |

---

### Health Status

| Field | Type | Description |
|-------|------|-------------|
| service | str | Service name (e.g., `odoo`, `facebook`, `gmail`) |
| status | str | `operational`, `degraded`, `unavailable` |
| last_checked | str | ISO 8601 timestamp |
| last_error | str | Most recent error message (if any) |
| error_count | int | Errors since last successful operation |
| consecutive_failures | int | Failures in a row (resets on success) |

**Status Transitions**:
```
operational → degraded (1 error)
degraded → unavailable (3+ consecutive failures)
unavailable → operational (successful operation)
degraded → operational (successful operation)
```
