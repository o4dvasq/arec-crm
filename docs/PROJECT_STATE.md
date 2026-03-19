# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-18 — Meeting detail modal + row click behavior + remove time field

---

## What's Built and Working

### AREC CRM — Single-User Fundraising Platform (LOCAL ONLY)
- **Local URL**: http://localhost:8000/crm
- **Backend**: Markdown-only (`crm_reader.py`). All data in `crm/*.md` and `crm/*.json` files.
- **Authentication**: DEV_USER env var sets g.user. No database, no MSAL.
- **CRM Features**: Pipeline, prospect detail, org management, relationship briefs, contact intelligence, interaction history, tasks, meetings
- **Brief Synthesis**: Relationship briefs (org + person) via Claude API, cached in `crm/briefs.json`
- **Dark Theme**: Full dark theme throughout
- **Navigation**: Global search, centered nav tabs (Pipeline, People, Orgs, Tasks, Meetings) with bullseye icon and hover user menu
- **Tasks Page**: `/crm/tasks` — Two-section view (My Tasks | Team Tasks) with search, sorting by priority then deal size, enriched with prospect data
- **Meetings Page**: `/crm/meetings` — two-tab view (Scheduled | Past) with full CRUD, AI notes processing, insight approval workflow
  - Row click opens edit modal pre-populated from meeting record
  - Prospect name link (when org+offering present) navigates to prospect detail page
  - Edit modal: "Edit Meeting" header, "Save Changes" button, PATCH on submit
  - Delete with inline "Are you sure? Yes · No" confirmation (no browser dialog)
  - Meeting Time field removed from modal entirely
  - Column header and label renamed "Organization" → "Prospect"
- **Organization Aliases**: Org edit page has Aliases field (inline-editable). Aliases included in global search and relationship brief context.
- **Organization Merge**: Full merge workflow on org edit page — select target, preview data migration, execute atomic merge, redirect to target org with success flash
- **Prospect Detail Page**: Clean UI with notes log, task editing, email scanning, and markdown-free display
- **Tony Excel Sync**: Daily Egnyte polling for Tony's Excel tracker, fuzzy org matching with alias support, auto-syncs high-confidence changes to CRM with prospect notes integration
- **Pipeline Polish**: At a Glance text with 2-line wrap, Tasks column 350px width, assignee initials in parentheses, markdown stripping throughout
- **Person Name Linking**: App-wide clickable person names linking to `/crm/people/<slug>` using client-side `linkifyPersonNames()` function
- **Task Grouping APIs**: `/crm/api/tasks/by-prospect` and `/crm/api/tasks/by-owner` fully functional with filtering, sorting, and enrichment

---

## What Was Just Completed (March 18, 2026)

### Meeting Detail Modal + Row Click + Remove Time Field (SPEC_meeting-detail-modal.md)

**What Was Done:**
- ✅ Renamed "Organization" → "Prospect" on table column header, modal field label, dropdown placeholder
- ✅ Replaced `openMeetingDetail()` alert stub with full edit modal behavior
- ✅ Row click opens existing `add-meeting-modal` in edit mode, pre-populated from `allMeetings` array (no extra fetch)
- ✅ Prospect cell with org+offering renders `<a>` link only — navigates to prospect detail page, `stopPropagation()` intact
- ✅ Prospect cell with no org/offering renders plain `—` so row click fires normally → opens edit modal
- ✅ Edit mode: "Edit Meeting" header, "Save Changes" button, PATCH to `/crm/api/meetings/<id>`
- ✅ Delete link ("Delete Meeting", red) visible only in edit mode, bottom-left of modal footer
- ✅ Inline delete confirmation: "Are you sure? Yes · No" — no `confirm()` dialog
- ✅ "Yes" → DELETE to `/crm/api/meetings/<id>`, closes modal, refreshes table
- ✅ "No" → restores "Delete Meeting" link
- ✅ `closeAddMeetingModal()` resets all edit state: clears `currentEditMeetingId`, resets header/button/delete section
- ✅ Removed `form-time` `<input type="time">` and its label entirely from HTML
- ✅ Form submit branches on `currentEditMeetingId`: PATCH (edit) vs POST (add)
- ✅ Add mode still works correctly (no regressions)

**Backend:** No changes needed — PATCH and DELETE routes already existed in `crm_blueprint.py`.

**Test Results:** 89/89 passing

---

## Active Branch: `main`

**⚠️ ALL WORK HAPPENS ON `main`. DO NOT USE `deprecated-markdown`.**

---

## Known Issues / Remaining Work

### Tony Sync Setup Required
- **EGNYTE_API_TOKEN needed** — Must be obtained from Egnyte developer console and added to `app/.env`
- **Not scheduled yet** — Needs launchd job for 6 AM daily run (called via `python app/main.py`)
- **Manual review workflow not implemented** — Desktop/CoWork workflow for resolving low-confidence matches from `crm/tony_sync_pending.json`

### Other Known Issues
- **test_drain_inbox.py import error** — Test file needs fixing or removal
- **No test coverage for org merge** — Feature manually tested but no automated tests yet

---

## Next Up

1. **Set up Tony sync in production:**
   - Obtain EGNYTE_API_TOKEN from Egnyte developer console
   - Add to `app/.env`
   - Create launchd job for 6 AM daily run
   - Test with real Excel file
2. **Implement low-confidence match review workflow** (Desktop/CoWork)
3. Fix or remove test_drain_inbox.py
4. Add test coverage for org merge feature

---

## Deferred / Parked

- Azure deployment (not applicable to markdown-only app)
- PostgreSQL migration (reverted, staying with markdown)
- Multi-user auth (single-user local app)
- SPEC_drain-inbox-mcp-migration.md (future enhancement — requires MCP Outlook connector setup)
