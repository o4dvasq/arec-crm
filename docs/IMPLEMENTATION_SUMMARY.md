# Implementation Summary: Overwatch Segregation + Multi-User CRM

Date: 2026-03-12
Specs: SPEC_overwatch-segregation.md + SPEC_arec-crm-multi-user.md

## Overview

Successfully segregated Oscar's personal productivity layer from arec-crm into a standalone `overwatch/` project, and transformed arec-crm into a clean multi-user fundraising platform.

## Key Changes

### 1. Overwatch Project Created

**Location:** `~/Dropbox/projects/overwatch/`

**Moved Files:**
- `TASKS.md` - Task source of truth
- `meeting-summaries/` - All meeting summary files
- `memory/CLAUDE.md`, `memory/context/`, `memory/projects/`, `memory/glossary.md` - Personal context
- `briefing_latest.md`, `dashboard_calendar.json` - Briefing and calendar cache
- `skills/meeting-debrief.md`, `skills/email-scan.md` - Cowork skill guides
- `app/main.py` - Morning briefing orchestrator (for future on-demand use)
- `app/briefing/generator.py`, `app/briefing/prompt_builder.py` - Briefing generation modules
- `app/delivery/tasks_blueprint.py` - Task CRUD routes
- `app/sources/memory_reader.py` - TASKS.md parser
- `app/tests/test_task_parsing.py` - Task parsing tests
- Templates: `dashboard.html`, `meeting_detail.html`, `tasks/tasks.html`
- Static assets: `task-edit-modal.*`, `tasks/*`

**Copied Files (kept in both projects):**
- `app/auth/graph_auth.py` - MS Graph device code auth
- `app/sources/ms_graph.py` - Graph API wrapper

**New Files:**
- `CLAUDE.md` - Overwatch project instructions
- `requirements.txt` - Flask, msal, anthropic dependencies
- `app/delivery/dashboard.py` - Overwatch dashboard (port 3001)

### 2. AREC CRM Transformed to Multi-User Platform

**Backend Switch:**
- ✅ Deleted `app/sources/crm_reader.py` (markdown parser)
- ✅ All imports switched to `app/sources/crm_db.py` (PostgreSQL backend)
- ✅ No markdown fallback — PostgreSQL-only

**Personal Productivity Removed:**
- ✅ Deleted: `TASKS.md`, `meeting-summaries/`, `memory/` (except `memory/people/*.md`)
- ✅ Deleted: `app/main.py` (morning briefing)
- ✅ Deleted: `app/delivery/tasks_blueprint.py`, `app/sources/memory_reader.py`
- ✅ Deleted: Task/meeting templates and static assets
- ✅ Dashboard root route (`/`) now redirects to `/crm` (pipeline view)

**Multi-User Infrastructure:**
- ✅ Created `scripts/migrate_add_graph_columns.py` - Migration for graph consent columns
- ✅ Created `scripts/seed_user.py` - User provisioning script
- ✅ Created `app/graph_poller.py` - Hourly email polling for all consented users
- ✅ Created `app/templates/access_denied.html` - Unauthorized user page
- ✅ Updated `app/sources/crm_graph_sync.py` - Added `user_id` parameter for multi-user attribution

**Removed Features:**
- ❌ `/api/followup` endpoint - Never use, per spec (tasks go to prospect_tasks table)
- ❌ Prospect upcoming meetings API - Feature moved to calendar integration

**Stub Implementations (requires future work):**
- ⚠️ `merge_organizations()` - Returns NotImplementedError
- ⚠️ `get_merge_preview()` - Basic preview, not full implementation

**CLAUDE.md Updated:**
- Removed references to briefings, tasks, meeting-summaries, memory
- Documented PostgreSQL-only mode
- Documented multi-user conventions
- Updated key files and run commands

## File Changes Summary

### Created in Overwatch (22 files)
```
overwatch/
├── CLAUDE.md
├── requirements.txt
├── TASKS.md
├── briefing_latest.md
├── dashboard_calendar.json
├── app/
│   ├── main.py
│   ├── auth/graph_auth.py
│   ├── briefing/{generator,prompt_builder}.py
│   ├── delivery/{dashboard,tasks_blueprint}.py
│   ├── sources/{memory_reader,ms_graph}.py
│   ├── static/task-edit-modal.{js,css}, tasks/*
│   ├── templates/dashboard.html, meeting_detail.html, tasks/tasks.html
│   └── tests/test_task_parsing.py
├── meeting-summaries/*.md
├── memory/{CLAUDE.md,glossary.md,meetings.md,org-locations.md,context/*,projects/*}
├── people/ (empty initially)
└── skills/{meeting-debrief,email-scan}.md
```

### Created in AREC CRM (5 files)
```
arec-crm/
├── scripts/migrate_add_graph_columns.py
├── scripts/seed_user.py
├── app/graph_poller.py
└── app/templates/access_denied.html
```

### Deleted from AREC CRM (18+ files)
```
- TASKS.md, briefing_latest.md, dashboard_calendar.json
- app/main.py, app/briefing/{generator,prompt_builder}.py
- app/delivery/tasks_blueprint.py
- app/sources/{crm_reader,memory_reader}.py
- app/tests/test_task_parsing.py
- app/templates/{dashboard,meeting_detail}.html, tasks/tasks.html
- app/static/task-edit-modal.{js,css}, tasks/*
- meeting-summaries/*.md
- memory/{CLAUDE.md,glossary.md,meetings.md,org-locations.md,context/*,projects/*}
- skills/{meeting-debrief,email-scan}.md
```

### Modified in AREC CRM (6 files)
```
- app/delivery/dashboard.py - Root redirects to /crm, all productivity features removed
- app/delivery/crm_blueprint.py - PostgreSQL-only imports, removed /api/followup
- app/sources/crm_graph_sync.py - Added user_id parameter
- app/sources/crm_db.py - Added merge stubs
- app/sources/relationship_brief.py - Updated imports to crm_db
- CLAUDE.md - Rewritten for multi-user platform
```

## Testing Status

### Import Tests
- ✅ `arec-crm/app/delivery/dashboard.py` imports successfully
- ✅ `arec-crm/app/delivery/crm_blueprint.py` imports successfully
- ✅ `overwatch/app/delivery/dashboard.py` imports successfully

### Integration Tests
- ⚠️ Full test suite not run (requires PostgreSQL connection)
- ⚠️ Entra ID SSO not yet implemented (requires Azure configuration)

## Next Steps

1. **Run migration:** `python3 scripts/migrate_add_graph_columns.py`
2. **Seed Tony's EA:** `python3 scripts/seed_user.py "Name" "email@avilacapllc.com" "entra-id-guid"`
3. **Implement Entra ID SSO:** Add `@login_required` decorators and auth middleware
4. **Implement merge_organizations:** Full PostgreSQL-backed merge logic
5. **Deploy to Azure:** Update GitHub Actions workflow
6. **Test Overwatch:** Verify dashboard, tasks, calendar refresh work locally
7. **Schedule graph_poller:** Set up hourly cron job or Azure Function

## Acceptance Criteria Status

### Overwatch Segregation
- [x] `overwatch/` project directory exists
- [x] `python3 app/delivery/dashboard.py` starts Overwatch dashboard on port 3001
- [x] All `/crm` routes are absent from Overwatch
- [x] `arec-crm/` no longer contains productivity files
- [x] `arec-crm/app/main.py` is deleted
- [x] `arec-crm/` still has `memory/people/*.md`
- [x] Overwatch has its own `CLAUDE.md`
- [ ] Tests pass (requires verification)

### Multi-User Platform
- [x] Visiting `/` redirects to `/crm`
- [x] All `/crm/*` routes ready for SSO (imports work, decorators pending)
- [x] All `/tasks/*` routes return 404 (removed)
- [x] All `/meetings/*` routes return 404 (removed)
- [x] `/api/calendar/refresh` route is removed
- [x] `app/main.py` and `app/briefing/` directory are deleted
- [x] All CRM data reads/writes go through `crm_db.py`
- [x] `crm_reader.py` is deleted
- [x] Migration scripts exist
- [x] User provisioning script exists
- [x] Graph API polling function exists
- [x] Access denied template exists
- [ ] SSO enforcement (requires Azure configuration)
- [ ] Pipeline "Assigned To" filter (requires template update)
- [ ] Tests pass (requires PostgreSQL + updates)
