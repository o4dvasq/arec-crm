# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-15 — CRM UI cleanup round 2: 5-page UX sweep removing dead UI, fixing brief persistence, and redesigning the Tasks Board as an owner-grouped Kanban.

**Active branch:** `main`

---

## What's Built and Working

### Markdown Backend
- `app/sources/crm_reader.py` — Single source of truth for all CRM data. ~1800 lines, 60+ functions. Reads/writes markdown and JSON files directly. All production code imports from here.
- `app/sources/email_matching.py` — Extracted from deleted `crm_graph_sync.py`. Pure utility: `_fuzzy_match_org`, `_is_internal`, `_resolve_participant`. No Graph dependency.

### Web Dashboard (Flask — local dev, port 8000)
- `app/delivery/dashboard.py` — Flask app factory. No DB init. Loads env → registers blueprints → serves. `g.user` set from `DEV_USER` env var.
- `app/delivery/crm_blueprint.py` — All CRM routes backed by `crm_reader.py`. `prospect_detail` route injects `config['current_user']` for the notes form. Graph-dependent routes return 501.
- `app/delivery/tasks_blueprint.py` — Tasks page. Markdown-backed task CRUD.
- `app/auth/decorators.py` — `require_api_key_or_login` is a no-op passthrough for local dev.
- Dark theme throughout. Pipeline, prospect detail, org detail, person detail, tasks pages all functional.
- Brief synthesis via Claude API (`brief_synthesizer.py`).

### Pipeline Page (`crm_pipeline.html`)
- Tasks column shows owner initials in blue before task text (e.g., `(TA) Schedule meeting...`).
- Clicking task text opens the task-edit modal; clicking elsewhere on the row navigates to prospect detail.
- At a Glance column: `#94a3b8` color, italic, no lightning bolt emoji.

### Prospect Detail (`crm_prospect_detail.html`)
- Quick Actions card completely removed.
- Relationship Brief loads from disk on page load — no spinner. JS renders saved brief or "Generate Brief" button.
- Notes Log: no author input field; author auto-set from `CURRENT_USER` JS constant (injected from `DEV_USER`).

### Org Detail (`crm_org_detail.html`)
- Notes section completely removed (HTML + JS).
- Section order: Heading → Summary Card (Type + Domain) → Contacts → Meeting History → Brief → Prospects.

### Person Detail (`crm_person_detail.html`)
- Person Brief section completely removed (CSS + HTML + all brief JS functions).
- Shows only: Contact Info card + Interaction History + Meeting Summaries + Email History.

### Tasks Board (`app/static/tasks/`)
- Owner-grouped Kanban (single-column, max-width 800px). Oscar first, then others alphabetically.
- Each card: priority badge (Hi/Med/Lo, color-coded), task text, org link, section label.
- Add form per owner group with section dropdown.
- Done footer aggregates all completed tasks at the bottom.

### Task API (Overwatch-compatible)
- `GET /crm/api/tasks/dashboard` — All open tasks, enriched.
- `GET /crm/api/tasks?org=X` — Tasks for specific org.
- `POST /crm/api/tasks` — Create task (markdown-backed, returns synthetic task object).

### Contact Profiles
- `contacts/{name}.md` — 211 contact profile files (formerly `memory/people/`).

### Test Suite
- `app/tests/test_brief_synthesizer.py`, `test_email_matching.py`, `test_task_parsing.py`
- **52 tests passing**. No DB fixtures. No DATABASE_URL required.

### Skills (Claude Desktop via MCP — unaffected by cleanup)
- `skills/email-scan.md`
- `app/auth/graph_auth.py`, `app/sources/ms_graph.py` — preserved for skill use

### Sister Repo
- `~/Dropbox/projects/overwatch/` — Personal productivity system (tasks, briefing, personal contacts). Separate repo, separate Flask app on port 3002.

---

## What Was Just Completed

**SPEC_crm-ui-cleanup-round2 + SPEC_prospect-detail-cleanup (2026-03-15)**

- **Pipeline**: Owner initials prepended to task text in blue; clicking task text opens task-edit modal with `stopPropagation`; at-a-glance color fixed to `#94a3b8`, lightning bolt removed.
- **Prospect Detail**: Quick Actions card (Add Task / Add Quick Note) fully deleted; brief no longer shows loading spinner on page load; notes author field removed and replaced with auto-set `CURRENT_USER` constant injected by `prospect_detail` route.
- **Org Detail**: Notes section (Section 4) completely removed from HTML and JS; Contacts card moved above Relationship Brief; `'notes'` removed from `EDITABLE_PROSPECT_FIELDS` and `PROSPECT_DISPLAY_FIELDS`.
- **Person Detail**: Person Brief card and all related CSS/JS fully removed (`loadBrief`, `refreshBrief`, `showBriefLoading`, `showBriefError`, `submitPersonUpdate`, `cancelUpdate`, 9 functions total).
- **Tasks Board**: Full rewrite to owner-grouped Kanban replacing the 3-column layout. `tasks.js` and `tasks.css` both rewritten from scratch.

---

## Known Issues

- **`/api/task/complete` and `/api/tasks/prospect/<id>/complete` return 501** — ID-based task completion doesn't exist in the markdown layer.
- **Interactions seeding** — `interactions.md` has only 1 entry using a person name as heading instead of org. Skipped on import. No data loss.
- **Personal section in arec-crm TASKS.md** — Still present; Overwatch is now the confirmed home for personal tasks. Clean up when convenient.

---

## Next Up

1. Remaining spec candidates: none currently in `docs/specs/` — check `docs/specs/future/` for next candidates
2. Clean up Personal section from arec-crm TASKS.md
3. Update iPhone Shortcut file path from `inbox.md` (arec-crm) → `~/Dropbox/projects/overwatch/inbox.md`

**Local dev setup:**
```bash
echo "DEV_USER=oscar" > app/.env     # First time only
python3 app/delivery/dashboard.py    # http://localhost:8000
python3.12 -m pytest app/tests/ -v  # 52 tests
```

---

## Open Design Questions

<!-- None at this time -->

---

## Deferred / Parked

- Prospect task completion by ID — requires either a DB or a slug/index scheme in the markdown layer
- Graph API features (`email-scan`, `auto-capture`) — work via Claude Desktop skill; disabled as in-app routes (return 501)
- `arec-mobile/` PWA — functional, not actively iterated
- `prospect_meetings` — JSON file-backed (`crm/prospect_meetings.json`); no DB table
- Overwatch cross-repo task display in arec-crm dashboard — out of scope per spec; future read-only integration
