# Architecture

> Last updated: 2026-03-18 (tasks screen overhaul: grouped views, audit script, complete endpoint fix)

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
  meeting_history.md.bak  # Legacy meeting log (replaced by meetings.json)
  meetings.json        # Unified meeting store — UUID-keyed, status lifecycle, AI insights
  calendar_users.json  # Calendar scan config (Oscar + Tony email addresses)
  org-locations.md     # Org location metadata
  briefs.json          # Cached briefs (prospect, person, org) — each entry: narrative, at_a_glance, generated_at, generated_by, content_hash
  org_notes.json       # Org-level notes log — { org_name: [{date, author, text}] }
  email_log.json       # Email scan log
  unmatched_review.json
  prospect_meetings.json.bak  # Legacy (replaced by meetings.json)
  prospect_notes.json
  ai_inbox_queue.md    # Shared queue: drain_inbox.py writes high-priority shared inbox items; Overwatch writes normal-priority items; /crm-update processes all pending
contacts/              # 213 contact profiles (one .md per person)
projects/              # Deal notes (arec-fund-ii.md)
TASKS.md               # Personal + team task list (all sections)
scripts/
  batch_primary_contact.py  # One-time backfill: set Primary Contact on prospects missing it
  migrate_meetings.py       # One-time: prospect_meetings.json + meeting_history.md → meetings.json
  audit_orphan_tasks.py     # One-time read-only: report tasks missing [org:] or [owner:] tags → docs/orphan_tasks_report.md
```

**Single reader:** `app/sources/crm_reader.py` is the only module that reads/writes these files. All production code imports from here. `~2100 lines, 70+ functions`.

---

## Application Layer

```
app/
  delivery/
    dashboard.py         # Flask app factory — env load, blueprint registration
    crm_blueprint.py     # /crm routes (pipeline, prospect detail, orgs, people, meetings, tasks API)
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
  drain_inbox.py         # Shared mailbox drain: crm@avilacapllc.com → crm/ai_inbox_queue.md
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
  /crm/tasks → crm_blueprint.py → get_tasks_grouped_by_prospect/owner() → crm_tasks.html (server-rendered)
  /crm/api/tasks → GET list / POST create (400 if org|owner|text missing) / PATCH complete (org+text)
  /crm/meetings → crm_blueprint.py → meetings list view (standalone tab)
  /crm/api/meetings/* → CRUD + notes + insights → crm_reader.py → meetings.json
  /crm/api/org/<name>/notes → POST — append timestamped note → crm_reader.py → org_notes.json
  /crm/api/synthesize-org-brief → POST — Claude API → crm_reader.py → briefs.json (org bucket)
  /crm/people/api/<slug>/contact → PATCH — inline field update (Title, Email, Phone)
  /tasks/* → tasks_blueprint.py → memory_reader.py → TASKS.md
```

---

## Meetings Subsystem

Unified meeting data model backed by `crm/meetings.json`. Replaces legacy `prospect_meetings.json` + `meeting_history.md`.

**Status lifecycle:** `scheduled` → `completed` → `reviewed`

- `scheduled`: Future meeting, no notes yet. Auto-transitions to `completed` when meeting date passes.
- `completed`: Meeting occurred, notes may be attached. AI processing generates summary + insights.
- `reviewed`: All AI-generated insights have been approved or dismissed by a human.

**Deduplication (two-tier):**
1. **Exact:** `graph_event_id` match (calendar sync creates meetings with Graph event IDs).
2. **Fuzzy:** Same org + meeting date within ±1 day + existing meeting is `scheduled` (attaches notes to the scheduled meeting rather than creating a duplicate).

**AI pipeline:** `POST /crm/api/meetings/<id>/notes` with `process_with_ai=true` → calls Claude Sonnet → extracts structured summary + actionable insights → stores on the meeting object. Insights enter a review queue (approve writes to prospect Notes; dismiss discards).

**Calendar scan config:** `crm/calendar_users.json` lists email addresses for Graph calendar scanning (Oscar + Tony).

**Routes:**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/crm/meetings` | Standalone meetings list page |
| GET | `/crm/api/meetings` | List with filters (org, status, future_only, past_only) |
| POST | `/crm/api/meetings` | Create meeting |
| GET | `/crm/api/meetings/<id>` | Detail |
| PATCH | `/crm/api/meetings/<id>` | Update |
| DELETE | `/crm/api/meetings/<id>` | Delete |
| POST | `/crm/api/meetings/<id>/notes` | Attach notes + optional AI processing |
| POST | `/crm/api/meetings/<id>/insights/<iid>/approve` | Approve insight → writes to prospect Notes |
| POST | `/crm/api/meetings/<id>/insights/<iid>/dismiss` | Dismiss insight |

---

## External Integrations

| Integration | How | Status |
|-------------|-----|--------|
| Claude API | `briefing/generator.py`, `brief_synthesizer.py`, `crm_reader.process_meeting_notes()` via `crm_blueprint.py` | Active |
| MS Graph (email/calendar) | `auth/graph_auth.py` + `sources/ms_graph.py` | Skill-only (not in Flask app) |
| Notion | Claude Desktop MCP | Skill-only |
| Overwatch | `~/Dropbox/projects/overwatch/` — sister repo, port 3002 | Separate app; can read arec-crm data files by path, no shared Python modules |

---

## Graph-Dependent Routes (return 501)

These routes exist in the codebase but always return `501 Not Implemented`:
- `POST /crm/api/prospect/<offering>/<org>/email-scan` — use Claude Desktop `/email-scan` skill
- `POST /crm/api/auto-capture` — use Claude Desktop skill
- `PATCH /crm/api/tasks/<id>` — ID-based update; no ID scheme in markdown

Note: `PATCH /crm/api/tasks/complete` was previously a 501 stub and is now functional — accepts `{org, text}`.

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
