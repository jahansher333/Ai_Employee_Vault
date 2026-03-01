# MCP Tool Contracts: Social Media Server

**Server**: `mcp_social_server.py`
**Transport**: stdio (FastMCP)

## Tools

### `draft_social_post`

**Description**: Generate a platform-specific social media post draft and save to Pending_Approval/.

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| topic | str | yes | - | Post topic |
| platform | str | yes | - | `facebook`, `instagram`, `twitter`, `linkedin` |
| template | str | no | "service_promotion" | Template name |

**Returns** (success):
```json
{
  "draft_file": "TWITTER_143022_AI-Automation.md",
  "platform": "twitter",
  "char_count": 245,
  "within_limit": true,
  "success": true
}
```

**Returns** (error — character limit):
```json
{
  "error": "Generated content exceeds Twitter 280-char limit (312 chars). Truncated version saved.",
  "draft_file": "TWITTER_143022_AI-Automation.md",
  "success": false
}
```

---

### `list_social_drafts`

**Description**: List all social media drafts in Pending_Approval/.

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| platform | str | no | null | Filter by platform (null = all) |

**Returns**:
```json
{
  "drafts": [
    {
      "file": "FACEBOOK_120000_AI-Update.md",
      "platform": "facebook",
      "topic": "AI Update",
      "status": "draft",
      "created": "2026-02-24T12:00:00+00:00"
    }
  ],
  "count": 3,
  "success": true
}
```

---

### `publish_social_post`

**Description**: Publish an approved social media post from Approved/.

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| filename | str | yes | - | Filename in Approved/ to publish |

**Returns** (success):
```json
{
  "published": true,
  "platform": "facebook",
  "post_id": "SIM-1708819200",
  "mode": "simulate",
  "moved_to": "Done/FACEBOOK_120000_AI-Update.md",
  "success": true
}
```

---

### `get_social_activity_summary`

**Description**: Get a summary of social media activity across all platforms.

**Parameters**: None

**Returns**:
```json
{
  "summary": {
    "linkedin": {"drafts": 2, "approved": 0, "posted": 5},
    "facebook": {"drafts": 1, "approved": 1, "posted": 3},
    "instagram": {"drafts": 0, "approved": 0, "posted": 2},
    "twitter": {"drafts": 1, "approved": 0, "posted": 4}
  },
  "total_posted": 14,
  "total_pending": 5,
  "success": true
}
```
