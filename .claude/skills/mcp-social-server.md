# MCP Social Server Skill

## Purpose
MCP (Model Context Protocol) server for multi-platform social media operations. Draft, publish, check comments, and reply across Facebook, Instagram, Twitter/X, and LinkedIn — all via Playwright browser automation.

## When to Use
- When Claude Code needs to draft or publish social media posts
- When checking comments or replying on social platforms
- User asks to "post to Facebook", "draft a tweet", "check Instagram comments", etc.

## Commands
```bash
# Start MCP server (stdio transport)
python scripts/mcp_social_server.py
```

Add to `.claude/mcp.json` for auto-discovery by Claude Code.

## Configuration
Set in `.env`:
- `VAULT_PATH` — Path to vault root
- Platform credentials managed via Playwright browser sessions (no API tokens needed)

## MCP Tools — Drafting & Publishing
| Tool | Description |
|------|-------------|
| `draft_social_post` | Generate a draft and save to Pending_Approval/ (topic, platform, template) |
| `list_social_drafts` | List all pending drafts across platforms |
| `publish_approved_posts` | Publish all approved posts (Approved/ to Done/) |
| `get_social_activity_summary` | Activity summary across all platforms |

## MCP Tools — Engagement (Playwright)
| Tool | Description |
|------|-------------|
| `check_comments` | Check comments on posts (platform or 'all') |
| `reply_to_comment` | Reply to a comment (platform, reply_text, post_url) |

## MCP Tools — Direct Posting (Playwright)
| Tool | Description |
|------|-------------|
| `post_to_instagram` | Post with auto-generated quote-card image |
| `post_to_facebook` | Post text to Facebook |
| `post_to_twitter` | Post a tweet (max 280 chars) |
| `post_to_linkedin` | Post to LinkedIn |

## Response Format
All tools return a dict with `success: bool` and either the result data or `error: str`. Draft tools include `char_count` and `char_limit` for validation.

## Integration
- Delegates to `social_poster.py`, `linkedin_poster.py`, and `social_engagement.py`
- Drafts saved to `Pending_Approval/` with platform prefix (FACEBOOK_, INSTAGRAM_, etc.)
- All actions logged via AuditLogger
- Server name: `social`

## Script
`scripts/mcp_social_server.py`
