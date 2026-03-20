# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-20 — SPEC_eliminate-task-sections implementation

---

## What's Built and Working

### AREC CRM — Single-User Fundraising Platform (LOCAL ONLY)
- **Local URL**: http://localhost:8000/crm
- **Backend**: Markdown-only (`crm_reader.py`). All data in `crm/*.md` and `crm/*.json` files.
- **Authentication**: DEV_USER env var sets g.user. No database, no MSAL.
- **CRM Features**: Pipeline, prospect detail, org management, relationship briefs, contact intelligence, interaction history, tasks, meetings
- **Brief Synthesis**: Two-tier brief system — Prospect Brief (offering-specific, 2-3 sentences) + Org Brief (comprehensive, org-level)
- **Dark Theme**: Full dark theme throughout
- **Navigation**: Global search, centered nav tabs (Pipeline, People, Orgs, Tasks, Meetings) with bullseye icon and hover user menu
- **Tasks Page (`/tasks`)**: Owner-grouped Kanban board. Flat task list (no sections). Responsive add-form per owner group.
  - `GET /tasks/api/tasks` returns `{"open": [...], "done": [...]}` — flat structure, no sections
  - All CRUD routes use index-only: `/tasks/api/task/<index>` (no section in URL)
  - Complete/restore physically move tasks to/from `## Done` in TASKS.md
  - Task cards show org link only in metadata (no section label)
- **CRM Tasks Page (`/crm/tasks`)**: Two-section view (My Tasks | Team Tasks) with search, sorting by priority then deal size, enriched with prospect data
- **Meetings Page**: `/crm/meetings` — two-tab view (Scheduled | Past) with full CRUD, AI notes processing, insight approval workflow
  - Data backed by `crm/meetings.json` (migrated from `meeting_history.md`)
  - Row click opens edit modal pre-populated from meeting record
  - Three-tier deduplication: graph_event_id exact match + org+date±1 day fuzzy match + read-time dedup safety net
- **Organization Aliases**: Single source of truth is the `Aliases` field on each org in `organizations.md`. Used by search, briefs, merge, and Tony sync.
- **Alias Normalization (FULLY WORKING)**: Write-path normalization prevents org name drift
  - `resolve_org_name()` converts aliases to canonical names before storage
  - All 5 write endpoints normalized: meeting create/update, prospect create, org contacts add, org notes add
  - Email fuzzy matching enhanced to check aliases (6-char threshold preserved)
- **Organization Merge**: Full merge workflow on org edit page
- **Prospect Detail Page**: Context-dependent color coding; both brief cards server-rendered; resilient loading
- **Tony Excel Sync**: Daily Egnyte polling for Tony's Excel tracker, fuzzy org matching with alias support
- **Enhanced At a Glance**: Temporal awareness, meeting-centric priority framework, unified `{org}::{offering}` brief key format
- **Person Name Linking**: App-wide clickable person names linking to `/crm/people/<slug>`
- **Task Grouping APIs**: `/crm/api/tasks/by-prospect` and `/crm/api/tasks/by-owner` fully functional
- **Drain Inbox Hardening**: Runs as unattended launchd process with dedup and last-run metadata
- **Primary Contact — Prospect-Level (FULLY WORKING)**: Primary Contact is a prospect-level field

---

## What Was Just Completed (March 20, 2026)

### SPEC_eliminate-task-sections

**What Was Done:**
- ✅ TASKS.md flattened: section headers removed (except `## Done`), 70 open tasks in flat list, 95 done tasks under `## Done`, 11 bracket-format `[org:] [owner:]` tasks from `## IR / Fundraising` converted to `(OrgName) — assigned:Name` standard format
- ✅ `GET /tasks/api/tasks` now returns `{"open": [...], "done": [...]}` instead of section-keyed dict
- ✅ All CRUD routes changed from `/<section>/<index>` → `/<index>` (8 routes updated)
- ✅ `TASK_SECTIONS` constant removed from `tasks_blueprint.py`
- ✅ Complete/restore now physically move tasks between open list and `## Done` section
- ✅ `_parse_task_line` and `_format_task_line` — `section` parameter removed
- ✅ `load_tasks()` in `memory_reader.py` returns `{"open": [...], "personal": [...]}` from flat structure
- ✅ `update_task_status()` searches by text without section parameter
- ✅ `append_task_to_section()` → `append_task()` — inserts before `## Done`
- ✅ `load_tasks_by_org()`, `get_tasks_for_prospect()`, `get_all_prospect_tasks()` — section tracking removed, flat index used
- ✅ `add_prospect_task()` — writes `(OrgName) — assigned:Name` format, inserts before `## Done`, `section` param removed
- ✅ `tasks.js` — consumes flat `{open, done}` response; section removed from all API URLs and card metadata; section dropdown removed from add form
- ✅ `task-edit-modal.js` — `_section` state removed; all save/delete/restore URLs index-only
- ✅ `tasks.html` — `TASK_MODAL_SECTIONS` and `SECTIONS` window variables removed
- ✅ 84/84 tests passing

**Files Modified:**
- `TASKS.md` — flattened
- `app/delivery/tasks_blueprint.py` — full rewrite of task helpers and all 8 CRUD routes
- `app/sources/memory_reader.py` — section removed from parse/format/load/update/append functions
- `app/sources/crm_reader.py` — 4 task functions updated
- `app/static/tasks/tasks.js` — full rewrite of board render and API calls
- `app/static/task-edit-modal.js` — section state and URL references removed
- `app/templates/tasks/tasks.html` — section window variables removed

---

## Active Branch: `main`

**⚠️ ALL WORK HAPPENS ON `main`. DO NOT USE `deprecated-markdown`.**

---

## In Progress / Next Up

### 1. No Pending Specs
`docs/specs/` is empty. Write the next spec in CoWork, save to `docs/specs/`, then `/code-start`.

### 2. Tony Sync Setup Required
- **EGNYTE_API_TOKEN needed** — Must be obtained from Egnyte developer console and added to `app/.env`
- **Not scheduled yet** — Needs launchd job for 6 AM daily run
- **Manual review workflow not implemented** — Desktop/CoWork workflow for resolving low-confidence matches from `crm/tony_sync_pending.json`

### 3. Drain Inbox Re-auth
After adding `Mail.ReadWrite.Shared` scope, delete `~/.arec_briefing_token_cache.json` and re-run `drain_inbox.py` to trigger re-auth with the new scope.

---

## Known Issues

- **No test coverage for meetings subsystem** — meeting dedup tested manually only
- **No test coverage for org merge** — feature manually tested but no automated tests
- **MetLife contact ambiguity**: "Chris Aiken" and "Christopher Aiken" both exist; migration chose Chris Aiken (Stage 5). Worth auditing manually.
- **33 orgs without primary contact** — Migration skipped contacts where Primary Contact string didn't match a contact file (e.g., "TBD"). These orgs show "—" for primary contact.
- **meeting_history.md still exists** — Old format file retained for backward compatibility.
- **Existing data not retroactively normalized** — `resolve_org_name()` only affects new writes.
- **CRM tasks page (`/crm/tasks`) not yet updated** — Still uses old section-based task format internally. Works for display but `section` field in its response is now a no-op. Follow-up spec if needed.

---

## Deferred / Parked

- Azure deployment (not applicable to markdown-only app)
- PostgreSQL migration (reverted, staying with markdown)
- Multi-user auth (single-user local app)
- SPEC_drain-inbox-mcp-migration.md (future enhancement — requires MCP Outlook connector setup)
