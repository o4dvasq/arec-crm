# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-11 — Bug fixes: org dropdowns, backend revert to markdown, search labels, prospect task edit modal

---

## What's Built and Working

### Morning Briefing Pipeline (Local, Unchanged)
- `app/main.py` orchestrates: MSAL auth → MS Graph fetch → prompt build → Claude call → write `briefing_latest.md`
- Runs via launchd at 5 AM; token cached after first device flow auth
- Auto-capture runs after briefing: email + calendar → CRM interaction log (two-tier matching)

### Web Dashboard (Local Dev)
- Flask app with CRM and Tasks blueprints
- **Dark theme throughout**: All pages use CSS custom properties (`--bg-primary: #0f172a`, `--bg-secondary: #1e293b`, `--border: #334155`, `--text: #e2e8f0`, `--muted: #94a3b8`, `--accent: #2563eb`)
- CRM pipeline view: entire row clicks navigate to prospect detail; filter preservation via `back_filters` query param; fully dark-themed
- Prospect detail: Click-to-edit fields (Stage, Org Type, Assigned To, Target, Closing), Quick Actions bar, relationship brief synthesis, interaction history, notes, contacts with "+ Add Contact"
- Prospect detail: Deep Email Scan button — queries Archive + Sent over 90 days for org domain + contacts; also scans Tony's delegate mailbox; returns enrichment stats
- People detail: Always-visible Contact Info card at top showing Company (linked), Title, Email, Phone — all click-to-edit; edit form includes all 4 fields
- Org edit page (`/crm/org/<name>/edit`): Prospect-style summary card — bold title above card, 3-column grid (Type, Domain), full-width Notes row below, all click-to-edit with auto-save green flash
- Org detail page (`/crm/org/<name>/detail`): Same summary card treatment — page title above card, 3-column grid, Notes row hidden when empty
- Contacts: Shared `_contacts_table.html` partial with typeahead search + create new contact flow
- Tasks: kanban view, status updates, add new tasks with assignee routing
- **Backend**: Local markdown only (`crm_reader.py`). Azure migration infrastructure exists but is deferred.

### Global Search Bar
- Appears on every page in nav row 2, right of the "Orgs" tab
- Three entity types: Prospects (name + offering), People (name + org), Orgs (name only)
- Each result shows: bold name, muted secondary context, right-aligned type label (`Prospect` / `Person` / `Org`) in grey
- Prefix matches rank above substring matches; within tiers: Prospects → People → Orgs → alpha
- Keyboard: arrow keys, Enter to navigate, Escape to dismiss

### Org Type Dropdown
- Full 19-type list (from `crm_db.py` config) used across all org type dropdowns
- Create Org modal (`crm_orgs.html`) now uses `{% for t in config.org_types %}` Jinja loop — no more hardcoded short list
- Org list route passes `config` to template

### Active Tasks on Prospect Detail
- Loaded from `/tasks/api/tasks/for-org?org=ORG` — new endpoint in `tasks_blueprint.py`
- Matches tasks by `[org: ...]` tag OR `(OrgName)` parenthetical OR org name anywhere in task text
- Task rows are **clickable** — opens `task-edit-modal.js` for full edit (text, priority, status, assignee, context, delete)
- **"+ Add Task" button** in the tasks card header — opens modal in create mode, pre-fills org
- `taskModalOnSave` / `taskModalOnDelete` callbacks reload task list after changes
- Tasks card always visible (never hidden); shows "No open tasks." when empty
- Quick Actions "Add Task" form still works (uses `/crm/api/tasks` POST → `add_prospect_task()`)

### Pipeline Task Overflow
- When a prospect has >1 open task, shows `+N` badge (count of hidden tasks)
- Clicking badge opens a popover listing all tasks with priority badges and owner names

### Brief Synthesis
- `brief_synthesizer.py` handles all Claude calls for briefs (prospect-level and org-level)
- Aggregates 9 data sources into context block; returns `{narrative, at_a_glance}` JSON
- Cached in `crm/briefs.json`
- Refresh via dashboard or `scripts/refresh_interested_briefs.py`

### Email Inbox Drain (Local, Unchanged)
- `app/drain_inbox.py` reads `crm@avilacapllc.com` shared mailbox
- Parses forwarded emails (intent note + original); appends to `inbox.md`

### Azure Migration Infrastructure (Deferred)
- `app/models.py`, `app/db.py`, `app/sources/crm_db.py`, `scripts/` migration scripts all exist
- `app/auth/entra_auth.py` SSO middleware exists
- NOT active — local CRM runs on markdown only until Oscar completes Azure Portal setup

### Testing
- 52 tests across 3 files: `test_brief_synthesizer.py` (10), `test_task_parsing.py` (22), `test_email_matching.py` (20)

---

## What Was Just Completed

**Bug fixes + Task UI overhaul** (2026-03-11)
- **Org type dropdown fixed**: Create Org modal had hardcoded short list (4 types). Replaced with Jinja2 loop over `config.org_types`. Fixed missing `config` param in `orgs_list()` route.
- **Backend reverted to markdown**: Previous session had partially migrated `dashboard.py` and `crm_blueprint.py` to import `crm_db` and call `init_db_app`. Both reverted to `crm_reader.py`; no DATABASE_URL needed for local dev.
- **Global search type labels**: Added `typeLabel` field (`'Prospect'`, `'Person'`, `'Org'`) to all entries in `inject_search_index()`. JS and CSS for `.search-result-type` were already in place.
- **New `/tasks/api/tasks/for-org` endpoint**: Scans TASKS.md with section+index tracking, matches tasks for an org by `[org:]` tag OR org name in text, returns full parsed data (text, priority, status, assigned_to, context, section, index).
- **Prospect detail task edit modal**: Replaced checkboxes + completeTask with clickable rows that open the shared `task-edit-modal.js`. Added "+ Add Task" button in card header. Wired `TASK_MODAL_TEAM_MAP`, `TASK_MODAL_SECTIONS`, `taskModalOnSave/Delete` callbacks. Task card always visible.

---

## Known Issues

- **Phase I1 tests not yet written** — Existing 52 tests use markdown backend. Need `test_crm_db.py` with Postgres fixtures (deferred with Azure migration).
- **Azure Portal prerequisites incomplete** — Oscar must complete Resource Group, PostgreSQL, Key Vault, Entra ID app registration, App Service setup before migration can run.
- **Pipeline org_type badge** — Still uses light colors inconsistent with dark theme. Minor cosmetic.
- **Launchd plist** — May still point to old `~/Dropbox/Tech/ClaudeProductivity/` path; needs manual update.

---

## Next Up

1. **Oscar completes Azure Portal setup** (when ready for cloud migration):
   - Create Resource Group, PostgreSQL Flexible Server, Key Vault, Entra ID app registration, App Service
   - Provide `DATABASE_URL`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`
2. Continue iterating on prospect detail UX as needed

---

## Open Design Questions

<!-- None at this time -->

---

## Deferred / Parked

- `arec-mobile/` PWA — functional, not actively iterated
- Azure migration (Phase I1) — infrastructure built, awaiting Oscar's Azure Portal setup
- Phase I2-I5 features (Intelligence pipeline, Intelligence UI, Briefing engine, Meeting transcript processing)
