# LinkedInPostSkill

## Description

Generates professional LinkedIn post drafts from a topic and template, saves them for human approval, and handles publishing (simulated or real) after approval. Supports three templates: service promotion, case study highlight, and thought leadership tip.

## When to Use

- When the user wants to create a LinkedIn post about a business topic
- When reviewing or publishing approved LinkedIn post drafts
- When updating the Dashboard with social media post activity

## Prerequisites

- Python 3.10+ with `python-dotenv` installed
- (Optional) `requests` package for real LinkedIn API posting
- (Optional) LinkedIn API credentials in `.env` for real posting

## Input

- **Draft generation**: Topic string + template type
  - Templates: `service_promotion` (default), `case_study`, `thought_leadership`
- **Publishing**: No input — processes files in `Approved/` folder
- **Dashboard**: No input — scans all folders for LinkedIn post files

## Output

Draft files in `Pending_Approval/` with format `LINKEDIN_{HHMMSS}_{topic}.md`:
- YAML frontmatter: type, topic, template, platform, status, generated_at, hashtags
- Markdown body: post title, formatted content, hashtags

After approval and posting, files are moved to `Done/` with updated status.

## Usage

```bash
# Generate a draft (service promotion template)
python scripts/linkedin_poster.py --draft "AI Automation for Small Businesses"

# Generate with specific template
python scripts/linkedin_poster.py --draft "Client Success Story" --template case_study

# Thought leadership post
python scripts/linkedin_poster.py --draft "Future of AI" --template thought_leadership

# Process all approved posts (one-shot)
python scripts/linkedin_poster.py --publish

# Continuously watch for approved posts
python scripts/linkedin_poster.py --watch

# Update Dashboard social section
python scripts/linkedin_poster.py --dashboard
```

## Approval Workflow

1. Draft generated → saved to `Pending_Approval/LINKEDIN_*.md`
2. User reviews the draft in Obsidian or any editor
3. **To approve**: Move the file to `Approved/`
4. **To reject**: Delete the file or move to `Done/`
5. Run `--publish` or `--watch` to process approved posts

## Configuration

Environment variables in `.env`:
- `LINKEDIN_POST_MODE` — `simulate` (default) or `linkedin_api`
- `LINKEDIN_ACCESS_TOKEN` — OAuth token (required for `linkedin_api` mode)
- `LINKEDIN_PERSON_URN` — Person URN (required for `linkedin_api` mode)

## Integration

- Drafts saved to `Pending_Approval/` → human approval → `Approved/` → published → `Done/`
- Dashboard updated with "Recent Social Posts" section
- All events logged to `Logs/YYYY-MM-DD.audit.jsonl`
- Simulation mode (default) requires zero configuration

## Script

`scripts/linkedin_poster.py`
