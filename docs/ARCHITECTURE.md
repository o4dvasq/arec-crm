# Architecture

> Last updated: 2026-03-16 (post crm-update-skill)

---

## System Overview

arec-crm is a single-user local CRM and fundraising platform. All data lives in markdown and JSON files. No database. No auth server. Runs as a local Flask app on port 8000.

---

## Data Layer

```
crm/
  prospects.md         # Active fundraising pipeline
  organizations.md     # Org registry
  interactions.md      # Interaction log
  meeting_history.md   # Meeting log
  org-locations.md     # Org location metadata
  briefs.json          # Cached relationship briefs
  email_log.json       # Email scan log
  unmatched_review.json
  prospect_meetings.json
  prospect_notes.json
  ai_inbox_queue.md    # Shared queue: Overwatch writes pending items; /crm-update processes them
contacts/              # 213 contact profiles (one .md per person)
projects/              # Deal notes (arec-fund-ii.md)
TASKS.md               # Personal + team task list (all sections)
```

**Single reader:** `app/sources/crm_reader.py` is the only module that reads/writes these files. All production code imports from here. `~1800 lines, 60+ functions`.

---

## Application Layer

```
app/
  delivery/
    dashboard.py         # Flask app factory — env load, blueprint registration
    crm_blueprint.py     # /crm routes (pipeline, prospect detail, orgs, people, tasks API)
    tasks_blueprint.py   # /tasks routes (general task CRUD on TASKS.md)
  sources/
    crm_reader.py        # Markdown/JSON CRM backend (source of truth)
    email_matching.py    # Org/participant fuzzy matching utilities (no Graph dep)
    ms_graph.py          # MS Graph API — used by Claude Desktop skill only
    memory_reader.py     # TASKS.md parser and formatter
    relationship_brief.py  # Brief assembly from contacts/, meetings, tasks
  briefing/
    generator.py         # Claude API call for morning briefing
    prompt_builder.py    # Prompt assembly for morning briefing
    brief_synthesizer.py # Parse Claude's JSON brief response with fallbacks
  auth/
    graph_auth.py        # MSAL token acquisition — Claude Desktop skill only
    decorators.py        # require_api_key_or_login (no-op passthrough for local dev)
  main.py                # Morning briefing orchestrator (run manually or via launchd)
  templates/             # Jinja2 templates (dark theme)
  static/                # CSS, JS
```

---

## Request Flow

```
Browser → Flask (dashboard.py)
  before_request: g.user = DEV_USER env var
  / → redirect → /crm/pipeline
  /crm/* → crm_blueprint.py → crm_reader.py → markdown files
  /tasks/* → tasks_blueprint.py → memory_reader.py → TASKS.md
  /meetings/* → dashboard.py → meeting-summaries/*.md
```

---

## External Integrations

| Integration | How | Status |
|-------------|-----|--------|
| Claude API | `briefing/generator.py`, `brief_synthesizer.py` via `crm_blueprint.py` | Active |
| MS Graph (email/calendar) | `auth/graph_auth.py` + `sources/ms_graph.py` | Skill-only (not in Flask app) |
| Notion | Claude Desktop MCP | Skill-only |
| Overwatch | `~/Dropbox/projects/overwatch/` — sister repo, port 3002 | Separate app; can read arec-crm data files by path, no shared Python modules |

---

## Graph-Dependent Routes (return 501)

These routes exist in the codebase but always return `501 Not Implemented`:
- `POST /crm/api/prospect/<offering>/<org>/email-scan` — use Claude Desktop `/email-scan` skill
- `POST /crm/api/auto-capture` — use Claude Desktop skill
- `PATCH /crm/api/tasks/complete` — ID-based; no ID scheme in markdown
- `PATCH /crm/api/tasks/<id>` — ID-based; no ID scheme in markdown

---

## Morning Briefing (`main.py`)

Separate from the web app. Run manually or via launchd at 5 AM.

```
get_access_token() [Graph] → get_today_events() → get_recent_emails()
  → write_dashboard_calendar.json
  → build_prompt() → generate_briefing() [Claude API]
  → write briefing_latest.md
  → run_auto_capture() [Graph]
```

Gracefully skips all Graph steps if `msal`/`ms_graph` import fails or token unavailable.

---

## Cowork Skills (Claude Desktop via MCP)

Not part of the Flask app. Step-by-step instruction files stored at `~/.skills/skills/` (local machine, not in repo). Operate via Claude Desktop + MCP tools.

| Skill | Path | Purpose |
|-------|------|---------|
| `/crm-update` | `~/.skills/skills/crm-update/SKILL.md` | CRM intelligence cycle: queue → email scan → calendar → meeting summaries → enrichment |
| `/meeting-debrief` | `~/.skills/skills/meeting-debrief/SKILL.md` | Post-meeting debrief via Notion MCP |
| `/productivity-update` | `~/.skills/skills/productivity-update/SKILL.md` | Overwatch daily briefing (personal) |

Graph-relevant files preserved in repo for skill use:
- `app/auth/graph_auth.py` — MSAL token acquisition
- `app/sources/ms_graph.py` — MS Graph API calls
