# MCP Tool Contracts: Email Server

**Server**: `mcp_email_server.py`
**Transport**: stdio (FastMCP)

## Tools

### `fetch_unread_emails`

**Description**: Fetch unread emails from Gmail.

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| max_results | int | no | 10 | Maximum emails to return |

**Returns** (success):
```json
{
  "emails": [
    {
      "id": "msg_12345",
      "from": "client@example.com",
      "subject": "Invoice #1234",
      "snippet": "Please find attached...",
      "date": "2026-02-24",
      "is_important": true
    }
  ],
  "count": 5,
  "success": true
}
```

**Returns** (error):
```json
{
  "error": "Gmail credentials not configured. Set GMAIL_CREDENTIALS_PATH in .env",
  "success": false
}
```

---

### `send_email`

**Description**: Send an email via Gmail. Requires human approval (HITL).

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| to | str | yes | - | Recipient email address |
| subject | str | yes | - | Email subject line |
| body_text | str | yes | - | Plain text email body |

**Returns** (success):
```json
{
  "sent": true,
  "message_id": "msg_67890",
  "success": true
}
```

---

### `reply_to_email`

**Description**: Reply to an existing email thread. Requires human approval (HITL).

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| message_id | str | yes | - | Gmail message ID to reply to |
| body_text | str | yes | - | Reply text |

**Returns** (success):
```json
{
  "sent": true,
  "message_id": "msg_67891",
  "thread_id": "thread_12345",
  "success": true
}
```

---

### `mark_email_read`

**Description**: Mark an email as read in Gmail.

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| message_id | str | yes | - | Gmail message ID to mark as read |

**Returns**:
```json
{
  "marked_read": true,
  "message_id": "msg_12345",
  "success": true
}
```

---

### `create_email_task`

**Description**: Create a vault task from an email (saves to Needs_Action/).

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| message_id | str | yes | - | Gmail message ID |
| priority | str | no | "medium" | Task priority (`low`, `medium`, `high`) |

**Returns**:
```json
{
  "task_file": "EMAIL_143022_Invoice-1234.md",
  "created_in": "Needs_Action/",
  "success": true
}
```
