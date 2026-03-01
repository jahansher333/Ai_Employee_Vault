# Contract: LinkedIn Poster (`linkedin_poster.py`)

**Module**: `scripts/linkedin_poster.py`
**Date**: 2026-02-22

## Public Interface

### Functions

#### `generate_post_draft(topic: str, template: str = "service_promotion") -> dict`
Generate a LinkedIn post draft from a topic and template.
- **Input**: Topic string, template name (`service_promotion` | `case_study` | `thought_leadership`)
- **Output**: Dict with keys: `topic`, `template`, `body`, `hashtags`, `generated_at`
- **Errors**: Raises `ValueError` if template name is invalid

#### `save_draft(draft: dict, vault_path: Path) -> Path`
Save a generated draft as a Markdown file in `Pending_Approval/`.
- **Input**: Draft dict from `generate_post_draft()`, vault root path
- **Output**: Path to created file (`Pending_Approval/LINKEDIN_{HHMMSS}_{topic}.md`)
- **Side effects**: Writes file, logs `linkedin_draft_created`

#### `scan_approved_posts(vault_path: Path) -> list[Path]`
Find all approved LinkedIn posts ready for publishing.
- **Input**: Vault root path
- **Output**: List of Paths matching `Approved/LINKEDIN_*.md`
- **Errors**: Returns empty list if `Approved/` doesn't exist

#### `post_to_linkedin(content: str, access_token: str, person_urn: str) -> dict`
Publish a post to LinkedIn via the v2 API.
- **Input**: Post text content, OAuth access token, person URN
- **Output**: Dict with `success: bool`, `post_id: str | None`, `error: str | None`
- **Errors**: Returns `{success: False, error: message}` on API failure

#### `simulate_post(content: str, title: str) -> dict`
Simulate posting by logging the action.
- **Input**: Post text content, post title
- **Output**: `{success: True, post_id: "SIM-{timestamp}", mode: "simulate"}`
- **Side effects**: Logs `linkedin_post_simulated`

#### `publish_approved_post(file_path: Path, vault_path: Path, mode: str = "simulate") -> str`
Process a single approved post: publish and move to Done/.
- **Input**: Path to approved file, vault root, posting mode
- **Output**: Status string: `"posted"` | `"simulated"` | `"error"`
- **Side effects**: Updates frontmatter (status, posted_at, post_mode), moves to Done/, logs event

#### `update_dashboard_social(vault_path: Path) -> None`
Update Dashboard.md with the "Recent Social Posts" section.
- **Input**: Vault root path
- **Output**: None (side effect: writes Dashboard.md)
- **Side effects**: Scans all three folders for `LINKEDIN_*.md`, builds table, inserts between markers

#### `start_approval_watcher(vault_path: Path, interval: float = 10.0) -> None`
Poll `Approved/` for new LinkedIn posts and publish them.
- **Input**: Vault root path, poll interval in seconds
- **Output**: None (runs indefinitely until Ctrl+C)
- **Side effects**: Publishes approved posts, moves to Done/, updates Dashboard

### Post Templates

#### `SERVICE_PROMOTION`
```
Hook: Question about a pain point
Body: 3-4 bullet points about the service
CTA: Call-to-action for engagement
Hashtags: 4-5 industry hashtags
Tone: Professional, confident
Words: 150-250
```

#### `CASE_STUDY`
```
Hook: Impressive result statement
Body: Problem → Solution → Result structure
CTA: "Want similar results?"
Hashtags: 3-4 relevant hashtags
Tone: Evidence-based, credible
Words: 200-300
```

#### `THOUGHT_LEADERSHIP`
```
Hook: Contrarian or surprising insight
Body: Personal perspective + supporting points
CTA: "What's your take?"
Hashtags: 2-3 broad hashtags
Tone: Conversational, authentic
Words: 150-200
```

### CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--vault-path` | str | `$VAULT_PATH` or parent dir | Vault root directory |
| `--draft` | str | None | Generate a draft with this topic |
| `--template` | str | `service_promotion` | Template to use for draft |
| `--publish` | flag | False | Process all approved posts |
| `--watch` | flag | False | Continuous watch mode for approved posts |
| `--dashboard` | flag | False | Update Dashboard social section only |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LINKEDIN_POST_MODE` | `simulate` | Posting mode: `simulate` or `linkedin_api` |
| `LINKEDIN_ACCESS_TOKEN` | None | LinkedIn OAuth access token (required for `linkedin_api` mode) |
| `LINKEDIN_PERSON_URN` | None | LinkedIn person URN (required for `linkedin_api` mode) |

### Audit Log Events

| Action | Input Ref | Outcome | Details |
|--------|-----------|---------|---------|
| `linkedin_draft_created` | filename | success | `{topic, template}` |
| `linkedin_post_published` | filename | success | `{mode, post_id}` |
| `linkedin_post_simulated` | filename | success | `{topic}` |
| `linkedin_post_failed` | filename | error | `{error: message}` |
| `linkedin_approval_detected` | filename | success | `{approved_at}` |
| `linkedin_dashboard_updated` | `system` | success | `{post_count}` |

### LinkedIn API Contract (external)

**Endpoint**: `POST https://api.linkedin.com/v2/ugcPosts`

**Headers**:
```
Authorization: Bearer {access_token}
Content-Type: application/json
X-Restli-Protocol-Version: 2.0.0
```

**Request body**:
```json
{
  "author": "urn:li:person:{member_id}",
  "lifecycleState": "PUBLISHED",
  "specificContent": {
    "com.linkedin.ugc.ShareContent": {
      "shareCommentary": {
        "text": "{post_content}"
      },
      "shareMediaCategory": "NONE"
    }
  },
  "visibility": {
    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
  }
}
```

**Response** (success): `201 Created` with `id` field containing post URN
**Response** (error): `401` (token expired), `403` (missing scope), `422` (content validation)

### Dependencies

- `requests` (HTTP client for LinkedIn API)
- `audit_logger.AuditLogger` (internal)
- `python-dotenv` (env loading)
- `pathlib`, `argparse`, `re`, `datetime` (stdlib)
