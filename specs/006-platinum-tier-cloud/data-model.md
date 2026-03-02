# Data Model: Platinum Tier — Always-On Cloud + Local Executive

**Feature**: `006-platinum-tier-cloud`
**Date**: 2026-03-01

## Entities

### ZoneConfig

Defines which operations are permitted in each zone.

| Field | Type | Description |
|-------|------|-------------|
| zone_mode | enum (cloud, local) | Current zone this instance runs in |
| operations | dict[str, str] | Maps operation names to zone (e.g., "email_send" → "local") |
| cloud_components | list[str] | Components to launch in cloud mode |
| local_components | list[str] | Components to launch in local mode |

### VaultTask

Represents a task file flowing through the vault pipeline.

| Field | Type | Description |
|-------|------|-------------|
| id | str | Unique task ID (from filename) |
| domain | enum (EMAIL, SOCIAL, ODOO) | Task domain |
| stage | enum (needs_action, plans, pending_approval, in_progress, done) | Current pipeline stage |
| zone_owner | enum (cloud, local, unclaimed) | Which zone owns this task |
| created_by | str | Agent that created the task (cloud/local) |
| created_at | datetime | When the task file was created |
| claimed_at | datetime | When the task was claimed (moved to In_Progress) |
| claimed_by | str | Agent ID that claimed the task |
| file_path | str | Current absolute file path |

**State transitions**:
```
Needs_Action/<domain>/ → Plans/<domain>/ → Pending_Approval/<domain>/
                                              ↓ (claim-by-move)
                                          In_Progress/<agent>/
                                              ↓ (execute/approve)
                                          Done/
```

### HealthCheck

Represents a health check result for a monitored component.

| Field | Type | Description |
|-------|------|-------------|
| component | str | Component name (e.g., "gmail_watcher", "odoo") |
| status | enum (healthy, degraded, unavailable) | Current health status |
| checked_at | datetime | When this check was performed |
| consecutive_failures | int | Number of sequential failures (resets on success) |
| last_error | str | Most recent error message (null if healthy) |
| response_time_ms | int | How long the health check took |

### SyncState

Tracks vault sync status between Cloud and Local.

| Field | Type | Description |
|-------|------|-------------|
| last_sync_at | datetime | When last successful sync completed |
| direction | enum (push, pull) | Last sync direction |
| files_changed | int | Number of files changed in last sync |
| conflicts | list[str] | Files with unresolved conflicts |
| status | enum (synced, pending, conflict, error) | Current sync state |

### A2AMessage (Phase 2)

Represents a direct message between Cloud and Local agents.

| Field | Type | Description |
|-------|------|-------------|
| id | str | Unique message ID (UUID) |
| from_zone | enum (cloud, local) | Sender zone |
| to_zone | enum (cloud, local) | Recipient zone |
| message_type | enum (task, status, alert, ack) | Message category |
| payload | dict | Message content (task data, status update, etc.) |
| sent_at | datetime | When the message was sent |
| received_at | datetime | When the message was received (null if pending) |
| delivery_method | enum (a2a, vault_fallback) | How the message was delivered |
| vault_audit_path | str | Path to the vault audit record for this message |

## Relationships

- **ZoneConfig** governs which components run and which operations are blocked
- **VaultTask** flows through domain folders; **ZoneConfig** determines which zone can act on it
- **HealthCheck** is collected by the cloud health monitor for each component defined in **ZoneConfig.cloud_components**
- **SyncState** is updated by the vault sync mechanism and checked by **HealthCheck**
- **A2AMessage** optionally replaces the VaultTask file-based handoff; both produce audit records
