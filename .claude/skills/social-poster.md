# Social Media Poster Skill

## Purpose
Generate platform-appropriate social media drafts for Facebook, Instagram, and Twitter/X. Manage the draft → approval → publish workflow with simulation mode default.

## When to Use
- User asks to create a social media post
- User says "post to Facebook/Instagram/Twitter"
- User asks for a social media activity summary
- Weekly briefing needs social activity data

## Commands
```bash
# Generate a Facebook draft
python scripts/social_poster.py --draft "AI Update" --platform facebook

# Generate a Twitter draft (280-char enforced)
python scripts/social_poster.py --draft "New Feature" --platform twitter

# Generate an Instagram caption draft
python scripts/social_poster.py --draft "Business Tips" --platform instagram

# Publish all approved posts (simulation default)
python scripts/social_poster.py --publish

# Social activity summary (all platforms)
python scripts/social_poster.py --summary
```

## Supported Platforms
| Platform | Prefix | Char Limit | Hashtag Style |
|----------|--------|------------|---------------|
| Facebook | FACEBOOK_ | None (optimal ~500) | Inline |
| Instagram | INSTAGRAM_ | 2200 | Block at end |
| Twitter/X | TWITTER_ | 280 (enforced) | Minimal (2-3) |

## Workflow
1. **Draft** → Saved to `Pending_Approval/` with platform prefix
2. **Review** → CEO reviews and moves to `Approved/`
3. **Publish** → `--publish` processes all approved posts → moved to `Done/`

## Post Modes
Set via environment variables (`FACEBOOK_POST_MODE`, `TWITTER_POST_MODE`, `INSTAGRAM_POST_MODE`):
- `simulate` (default) — Logs simulated post with SIM-ID
- `api` — Posts via real API (requires credentials)

## Configuration
Set in `.env`:
- `FACEBOOK_PAGE_ID`, `FACEBOOK_PAGE_ACCESS_TOKEN` — Facebook Graph API
- `TWITTER_BEARER_TOKEN` — Twitter API v2
- `INSTAGRAM_USER_ID`, `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_DEFAULT_IMAGE_URL` — Instagram Graph API

## Audit Trail
All social operations logged to `Logs/*.audit.jsonl` with actions: `*_draft_created`, `*_post_simulated`, `*_post_published`.
