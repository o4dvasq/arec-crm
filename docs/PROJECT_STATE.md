# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-18 — Tasks screen overhaul: grouped By Prospect / By Owner views, orphan audit script, complete endpoint fix.

**Active branch:** `main`

---

## What's Built and Working

### Markdown Backend
- `app/sources/crm_reader.py` — Single source of truth for all CRM data. 70+ functions. Reads/writes markdown and JSON files directly. All production code imports from here.
- `app/sources/email_matching.py` — Extracted from deleted `crm_graph_sync.py`. Pure utility: `_fuzzy_match_org`, `_is_internal`, `_resolve_participant`. No Graph dependency.

### Web Dashboard (Flask — local dev, port 8000)
- `app/delivery/dashboard.py` — Flask app factory. No DB init. Loads env → registers blueprints → serves. `g.user` set from `DEV_USER` env var.
- `app/delivery/crm_blueprint.py` — All CRM routes backed by `crm_reader.py`. Includes pipeline, prospect detail, orgs, people, meetings, and tasks API. Graph-dependent routes return 501.
- `app/delivery/tasks_blueprint.py` — General task CRUD on TASKS.md (Overwatch-compatible).
- `app/auth/decorators.py` — `require_api_key_or_login` is a no-op passthrough for local dev.
- Dark theme throughout. Pipeline, prospect detail, org detail, person detail, meetings, and tasks pages all functional.

### Pipeline Page (`crm_pipeline.html`)
- Tasks column shows ALL unique owner initials in blue before task text (e.g., `(OV, TA) Schedule meeting...`).
- Clicking task text in the popover opens the task-edit modal directly.
- At a Glance column: `#94a3b8` color, italic, no lightning bolt emoji.

### Prospect Detail (`crm_prospect_detail.html`)
- **Prospect card hides empty fields** — Type, Primary Contact, Assigned To, Target ($0 also hidden), Last Touch, Closing are all hidden when not populated. Stage always shown. Urgent shown only when true.
- **Prospect Briefing with AI synthesis** — Loads from `crm/briefs.json` on page load (instant). Refresh button calls Claude Sonnet → persists to briefs.json. Fallback summary if API unavailable.
- **At a Glance card** — Populated on Refresh only; hidden until first Refresh.
- **Contacts** — Merged from CRM contacts + contacts/*.md intel files. Contact names link to Person Detail via slug.
- **Interaction History** — Collapsible (starts expanded), CSS type badges, no emojis.
- **Meeting Summaries** — Collapsible, filtered to prospect-relevant meetings only.
- **Notes Log** — Freeform team notes with author auto-set from CURRENT_USER.
- **Upcoming/Past Meetings** — From unified `meetings.json`. No manual "Add Meeting" form.
- **Email History** — Collapsible (starts collapsed).
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
- **Org Brief** — AI-synthesized org-level brief. AT A GLANCE bullet list + narrative prose + "Last refreshed: [date] by [user]" attribution. Cached in `crm/briefs.json` under `org` bucket. Refresh on demand.
- **Org Notes** — Append-only timestamped log. "+ Add Note" opens inline textarea. Notes newest-first. Backed by `crm/org_notes.json`.

### Person Detail (`crm_person_detail.html`)
- Shows: Contact Info card + Interaction History + Meeting Summaries + Email History.
- Title, Email, Phone always rendered — shows `--` (muted italic) when empty. Click any field to inline-edit.

### Tasks Page (`crm_tasks.html` — `/crm/tasks`)
- **Two sub-tab views:** By Prospect (default) and By Owner.
- Both views server-rendered (Jinja2). Sub-tab switching via `history.pushState` — `?view=prospect` or `?view=owner` persists on refresh.
- **By Prospect:** Tasks grouped under prospect name headers, sorted by prospect `target` descending. Task card subtitle shows owner name.
- **By Owner:** Tasks grouped under owner name headers, sorted by max prospect `target` descending. Task card subtitle shows prospect/org name.
- Priority normalized to Hi / Med / Lo regardless of raw format (`high`, `normal`, `Hi`, etc.).
- `+ Add` on each group header pre-fills the context field (prospect or owner). Owner dropdown from `config.team`; prospect dropdown from `load_prospects()`.
- Complete button calls `PATCH /crm/api/tasks/complete` with `{org, text}` — now functional.
- No "Fundraising - Me" or category labels in UI.

### Task API (Overwatch-compatible)
- `GET /crm/api/tasks/dashboard` — All open tasks, enriched.
- `GET /crm/api/tasks?org=X` — Tasks for specific org.
- `POST /crm/api/tasks` — Create task. Returns 400 if `org`, `text`, or `owner` missing/empty.
- `PATCH /crm/api/tasks/complete` — Complete task by `{org, text}`. Now works (was 501).

### AI Brief Infrastructure
- `app/briefing/brief_synthesizer.py` — `call_claude_brief()` with JSON parse fallbacks. `AT_A_GLANCE_JSON_SUFFIX` for prospect/person briefs (10-word status). Org briefs use a self-contained system prompt with bullet-format at_a_glance.
- `app/sources/relationship_brief.py` — 10-source aggregation for prospect briefs.
- `crm/briefs.json` — Cached briefs (prospect, person, org). Each entry: `narrative`, `at_a_glance`, `content_hash`, `generated_at`, `generated_by`.

### Contact Profiles
- `contacts/{name}.md` — 213+ contact profile files.

### Test Suite
- `app/tests/test_meetings.py`, `test_brief_synthesizer.py`, `test_email_matching.py`, `test_task_parsing.py`, `test_drain_inbox.py`, `test_tasks_api_key.py`
- **98 tests passing**. No DB fixtures. No DATABASE_URL required.

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

**Tasks screen overhaul (2026-03-18)**
- Replaced two-column My Tasks / Team Tasks layout with grouped By Prospect / By Owner sub-tab views, both sorted by prospect `target` descending.
- Added `get_tasks_grouped_by_prospect()` and `get_tasks_grouped_by_owner()` to `crm_reader.py`; priority normalized to Hi/Med/Lo from legacy formats.
- `PATCH /crm/api/tasks/complete` now works — accepts `{org, text}` and calls `complete_prospect_task()`. Was previously a 501 stub.
- `scripts/audit_orphan_tasks.py` — read-only script that reports tasks missing `[org:]` or `[owner:]` tags. Found 55 orphans (all legacy `assigned:Name` format) — review `docs/orphan_tasks_report.md` before deploying.
- Added `test_tasks_api_key.py` with 15 tests covering 400 enforcement and both grouping functions. Full suite: 98 passing.

---

## Known Issues

- **55 orphan tasks in TASKS.md** — Tasks in legacy `assigned:Name` sections (Fundraising - Me, Fundraising - Others, etc.) missing `[org:]` and `[owner:]` tags. They won't appear in the new grouped view until manually tagged. See `docs/orphan_tasks_report.md`.
- **Personal section in arec-crm TASKS.md** — Still present; Overwatch is the confirmed home for personal tasks. Clean up when convenient.

---

## Next Up

1. Tag orphan tasks in TASKS.md (review `docs/orphan_tasks_report.md`) — old sections need `[org:]` + `[owner:]` added manually
2. Implement `SPEC_meetings-tab-view.md` or `SPEC_org-detail-enhancements.md` (remaining specs in `docs/specs/local-crm/`)
3. Create calendar scan skill file (`skills/calendar-scan.md`) — referenced in meetings spec but not yet built
4. Clean up Personal section from arec-crm TASKS.md
5. Update iPhone Shortcut file path: `inbox.md` (arec-crm) → `~/Dropbox/projects/overwatch/inbox.md`

**Local dev setup:**
```bash
echo "DEV_USER=oscar" > app/.env     # First time only — also add ANTHROPIC_API_KEY
python3 app/delivery/dashboard.py    # http://localhost:8000
python3 -m pytest app/tests/ -v      # 98 tests
```

---

## Open Design Questions

<!-- None at this time -->

---

## Deferred / Parked

- Graph API features (`email-scan`, `auto-capture`) — work via Claude Desktop skill; disabled as in-app routes (return 501)
- `arec-mobile/` PWA — functional, not actively iterated
- Overwatch cross-repo task display in arec-crm dashboard — out of scope; future read-only integration
- Tony's Excel pipeline tracker — no file found; `/crm-update` skips until path configured in `crm/config.md`
