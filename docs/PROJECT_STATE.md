# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-18 — Two sessions: meetings page two-tab redesign + org detail enhancements (Org Brief upgrade, Org Notes, Prospect Briefing rename).

**Active branch:** `main`

---

## What's Built and Working

### Markdown Backend
- `app/sources/crm_reader.py` — Single source of truth for all CRM data. 70+ functions. Reads/writes markdown and JSON files directly. All production code imports from here.
- `app/sources/email_matching.py` — Extracted from deleted `crm_graph_sync.py`. Pure utility: `_fuzzy_match_org`, `_is_internal`, `_resolve_participant`. No Graph dependency.

### Web Dashboard (Flask — local dev, port 8000)
- `app/delivery/dashboard.py` — Flask app factory. No DB init. Loads env → registers blueprints → serves. `g.user` set from `DEV_USER` env var.
- `app/delivery/crm_blueprint.py` — All CRM routes backed by `crm_reader.py`. Includes pipeline, prospect detail, orgs, people, meetings, and tasks API. Graph-dependent routes return 501.
- `app/delivery/tasks_blueprint.py` — Tasks page. Markdown-backed task CRUD.
- `app/auth/decorators.py` — `require_api_key_or_login` is a no-op passthrough for local dev.
- Dark theme throughout. Pipeline, prospect detail, org detail, person detail, meetings, and tasks pages all functional.

### Pipeline Page (`crm_pipeline.html`)
- Tasks column shows ALL unique owner initials in blue before task text (e.g., `(OV, TA) Schedule meeting...`).
- Clicking task text in the popover opens the task-edit modal directly.
- At a Glance column: `#94a3b8` color, italic, no lightning bolt emoji.

### Prospect Detail (`crm_prospect_detail.html`)
- **Prospect card hides empty fields** — Type, Primary Contact, Assigned To, Target ($0 also hidden), Last Touch, Closing are all hidden when not populated. Stage always shown. Urgent shown only when true.
- **Prospect Briefing with AI synthesis** — Loads from `crm/briefs.json` on page load (instant). Refresh button calls Claude Sonnet → persists to briefs.json. Fallback summary if API unavailable. (Was "Relationship Brief" — renamed to "Prospect Briefing".)
- **At a Glance card** — Populated on Refresh only; hidden until first Refresh.
- **Contacts** — Merged from CRM contacts + contacts/*.md intel files. Contact names link to Person Detail via slug.
- **Interaction History** — Collapsible (starts expanded), CSS type badges, no emojis.
- **Meeting Summaries** — Collapsible, filtered to prospect-relevant meetings only (placeholder contact names like "TBD" excluded from matching). Redundant header lines stripped from display.
- **Notes Log** — Freeform team notes with author auto-set from CURRENT_USER.
- **Upcoming/Past Meetings** — From unified `meetings.json`. No manual "Add Meeting" form.
- **Email History** — Collapsible (starts collapsed). Graph API errors show user-friendly message.
- **Active Tasks** — Opens task-edit modal on click; "Add Task" button.

### Meetings Page (`crm_meetings.html`)
- Standalone meetings list view accessible via "Meetings" nav tab.
- **Two-tab view:** Past (most recent first) and Scheduled (soonest first). Default tab: Scheduled.
- Tab classification by Pacific time (`America/Los_Angeles`) — evaluated client-side on every page load/tab switch.
- Columns: Date, Org, Title, Attendees. Past tab also shows Notes column (Review link / summary preview / dash).
- Date format: short human-friendly (`Mar 18`; year appended only if different from current calendar year).
- Text search only (no status dropdown, no date range pickers). Filters within active tab only.
- Meeting detail modal with notes entry, AI processing toggle, insights review queue (approve/dismiss).

### Meetings Subsystem (`crm/meetings.json`)
- **Unified data model** replacing legacy `prospect_meetings.json` + `meeting_history.md` (both renamed to `.bak`).
- **Status lifecycle:** scheduled → completed → reviewed.
- **Two-tier dedup:** (1) Exact `graph_event_id` match, (2) Fuzzy org + date ±1 day for notes attachment.
- **Auto-transition:** Past scheduled meetings auto-complete on load.
- **AI pipeline:** Notes → Claude Sonnet → summary + structured insights → review queue.
- **Insight review:** Approve writes to prospect Notes in `prospects.md`; dismiss discards.
- **Calendar config:** `crm/calendar_users.json` lists Oscar + Tony for Graph calendar scanning.

### Org Detail (`crm_org_detail.html`)
- Top card: Type + Domain only. Notes field never rendered.
- Section order: Heading → Summary Card → Contacts → Meeting History → **Org Brief** → Prospects → **Org Notes**.
- **Org Brief** — AI-synthesized org-level brief. Opens with which offerings the org is considering. Renders AT A GLANCE bullet list + narrative prose + "Last refreshed: [date] by [user]" attribution. Cached in `crm/briefs.json` under `org` bucket. Refresh on demand (no auto-synthesis — shows empty state on first visit).
- **Org Notes** — Append-only timestamped log. "+ Add Note" opens inline textarea. Notes newest-first. Author from session user. Backed by `crm/org_notes.json`.

### Person Detail (`crm_person_detail.html`)
- Shows: Contact Info card + Interaction History + Meeting Summaries + Email History.
- Title, Email, Phone always rendered — shows `--` (muted italic) when empty. Click any field to inline-edit.

### Tasks Board (`app/static/tasks/`)
- Owner-grouped Kanban (single-column, max-width 800px). Oscar first, then others alphabetically.
- Each card: priority badge (Hi/Med/Lo, color-coded), task text, org link, section label.
- Add form per owner group with section dropdown.
- Done footer aggregates all completed tasks at the bottom.

### Task API (Overwatch-compatible)
- `GET /crm/api/tasks/dashboard` — All open tasks, enriched.
- `GET /crm/api/tasks?org=X` — Tasks for specific org.
- `POST /crm/api/tasks` — Create task (markdown-backed, returns synthetic task object).

### AI Brief Infrastructure
- `app/briefing/brief_synthesizer.py` — `call_claude_brief()` with JSON parse fallbacks. `AT_A_GLANCE_JSON_SUFFIX` for prospect/person briefs (10-word status). Org briefs use a self-contained system prompt with bullet-format at_a_glance.
- `app/sources/relationship_brief.py` — 10-source aggregation for prospect briefs.
- `crm/briefs.json` — Cached briefs (prospect, person, org). Each entry: `narrative`, `at_a_glance`, `content_hash`, `generated_at`, `generated_by`.

### Contact Profiles
- `contacts/{name}.md` — 213+ contact profile files.

### Test Suite
- `app/tests/test_meetings.py`, `test_brief_synthesizer.py`, `test_email_matching.py`, `test_task_parsing.py`, `test_drain_inbox.py`
- **83 tests passing**. No DB fixtures. No DATABASE_URL required.

### Cowork Skills (Claude Desktop via MCP)
- `~/.skills/skills/crm-update/SKILL.md` — CRM intelligence update cycle.
- `~/.skills/skills/meeting-debrief/SKILL.md` — Post-meeting debrief via Notion MCP.
- `~/.skills/skills/productivity-update/SKILL.md` — Overwatch daily briefing cycle.
- `app/auth/graph_auth.py`, `app/sources/ms_graph.py` — preserved for skill use.

### Queue + Email Infrastructure
- `crm/ai_inbox_queue.md` — Shared queue between Overwatch and arec-crm.
- `crm/email_log.json` — Email scan audit trail. Dedup by `internetMessageId`.

### Primary Contact Auto-Fill
- `scripts/batch_primary_contact.py` — One-time batch script. Ran 2026-03-16.
- `_auto_set_primary_contact_for_org()` in `crm_reader.py` — Auto-sets on contact add.

### Sister Repo
- `~/Dropbox/projects/overwatch/` — Personal productivity system. Separate repo, port 3002.

---

## What Was Just Completed

**Meetings page two-tab redesign (2026-03-18)**
- Replaced flat single-table meetings view with Past / Scheduled two-tab layout; Scheduled is the default tab.
- Removed Source and Status columns from both tabs; Notes column retained on Past tab only (Review link / summary preview / dash).
- Added human-friendly date formatting: `Mar 18` within current year, `Feb 7, 2025` cross-year.
- Replaced status dropdown + date range pickers with tab switcher + single search bar (filters within active tab only).
- Tab-specific sort: Past = most recent first (descending); Scheduled = soonest first (ascending).
- Tab classification uses Pacific time (`America/Los_Angeles`); tab-specific empty states.

**Org detail enhancements (2026-03-18)**
- **Org Brief upgraded**: New system prompt opens with offerings sentence; `at_a_glance` is 3-5 bullets (not 10-word status); context includes prospect briefs + org notes + 20 interactions/emails. `save_brief()` stores `generated_by`. Empty state instead of auto-synthesis on first visit.
- **Org Notes section added**: Append-only log backed by `crm/org_notes.json`. Route: `POST /crm/api/org/<name>/notes`. Inline add-note form. Notes newest-first.
- **Prospect Briefing rename**: "Relationship Brief" → "Prospect Briefing" on prospect detail page (heading text only).
- **Data model**: `ORG_NOTES_PATH`, `load_org_notes()`, `save_org_note()` added to crm_reader.py; `save_brief()` gains `generated_by` parameter.

---

## Known Issues

- **`/api/task/complete` and `/api/tasks/prospect/<id>/complete` return 501** — ID-based task completion doesn't exist in the markdown layer.
- **Personal section in arec-crm TASKS.md** — Still present; Overwatch is the confirmed home for personal tasks. Clean up when convenient.

---

## Next Up

1. Implement `SPEC_tasks-screen-overhaul.md` (in `docs/specs/local-crm/`)
2. Create calendar scan skill file (`skills/calendar-scan.md`) — referenced in meetings spec but not yet built
3. Clean up Personal section from arec-crm TASKS.md
4. Update iPhone Shortcut file path: `inbox.md` (arec-crm) → `~/Dropbox/projects/overwatch/inbox.md`

**Local dev setup:**
```bash
echo "DEV_USER=oscar" > app/.env     # First time only — also add ANTHROPIC_API_KEY
python3 app/delivery/dashboard.py    # http://localhost:8000
python3 -m pytest app/tests/ -v      # 83 tests
```

---

## Open Design Questions

<!-- None at this time -->

---

## Deferred / Parked

- Prospect task completion by ID — requires either a DB or a slug/index scheme in the markdown layer
- Graph API features (`email-scan`, `auto-capture`) — work via Claude Desktop skill; disabled as in-app routes (return 501)
- `arec-mobile/` PWA — functional, not actively iterated
- Overwatch cross-repo task display in arec-crm dashboard — out of scope; future read-only integration
- Tony's Excel pipeline tracker — no file found; `/crm-update` skips until path configured in `crm/config.md`
