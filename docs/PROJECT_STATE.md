# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-20 — SPEC_fix-prospect-detail-briefs implementation

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
- **Tasks Page**: `/crm/tasks` — Two-section view (My Tasks | Team Tasks) with search, sorting by priority then deal size, enriched with prospect data
- **Meetings Page**: `/crm/meetings` — two-tab view (Scheduled | Past) with full CRUD, AI notes processing, insight approval workflow
  - Data backed by `crm/meetings.json` (migrated from `meeting_history.md`)
  - Row click opens edit modal pre-populated from meeting record
  - Prospect name link (when org+offering present) navigates to prospect detail page
  - Edit modal: "Edit Meeting" header, "Save Changes" button, PATCH on submit
  - Delete with inline "Are you sure? Yes · No" confirmation (no browser dialog)
  - Meeting Time field removed from modal entirely
  - Column header and label renamed "Organization" → "Prospect"
  - **Three-tier deduplication**: graph_event_id exact match + org+date±1 day fuzzy match (any status) + read-time dedup safety net
- **Organization Aliases**: Single source of truth is the `Aliases` field on each org in `organizations.md`. Used by search, briefs, merge, and Tony sync. `crm/org_aliases.json` retired and deleted.
- **Alias Normalization (FULLY WORKING)**: Write-path normalization prevents org name drift
  - `resolve_org_name()` function in `crm_reader.py` converts aliases to canonical names before storage
  - All 5 write endpoints normalized: meeting create/update, prospect create, org contacts add, org notes add
  - Aliases field visible and editable on Org Detail page (inline edit, same pattern as Type/Domain)
  - Email fuzzy matching enhanced to check aliases (6-char threshold preserved)
  - Unknown org names pass through unchanged (allows meetings for orgs not yet in CRM)
  - Case-insensitive matching on both org names and aliases
- **Organization Merge**: Full merge workflow on org edit page — select target, preview data migration, execute atomic merge, redirect to target org with success flash
- **Prospect Detail Page**: Context-dependent color coding with clear ownership boundaries (FULLY WORKING):
  - **Native sections (GREEN left-border)**: Prospect Card, Prospect Brief, Notes Log
  - **Cross-reference sections (BLUE right-border)**: Org Info Card, Org Brief, Meeting Summaries, Email History
  - Both brief cards server-rendered — saved briefs appear instantly on page load without AJAX
  - `loadProspectBrief()` and `loadOrgBrief()` always execute on page load, independent of main data fetch
  - Brief generation failure shows red error message with Retry button (not misleading placeholder)
  - GET `/brief` route has full exception handling — serialization errors return 500 with traceback logged
- **Org Edit Page**: Context-dependent color coding with clear ownership boundaries (FULLY WORKING)
- **Tony Excel Sync**: Daily Egnyte polling for Tony's Excel tracker, fuzzy org matching with alias support
- **Enhanced At a Glance (FULLY COMPLETE)**:
  - `BRIEF_SYSTEM_PROMPT` and `PROSPECT_BRIEF_SYSTEM_PROMPT` include meeting-centric priority framework and temporal awareness rules
  - Today's date injected at top of every context block
  - All brief routes use unified `{org}::{offering}` key format
  - Focused prospect brief route uses `want_json=True`, stores `at_a_glance`
  - Pipeline column wraps to 2 lines with `-webkit-line-clamp:2`
- **Person Name Linking**: App-wide clickable person names linking to `/crm/people/<slug>`
- **Task Grouping APIs**: `/crm/api/tasks/by-prospect` and `/crm/api/tasks/by-owner` fully functional
- **Drain Inbox Hardening**: Runs as unattended launchd process with dedup and last-run metadata
- **Primary Contact — Prospect-Level (FULLY WORKING)**: Primary Contact is a prospect-level field
- **Pipeline Type Column**: Type column correctly displays org Type; Type filter works
- **Contact Title Field (FULLY WORKING)**: "Role" renamed to "Title" throughout; backward-compatible

---

## What Was Just Completed (March 20, 2026)

### SPEC_fix-prospect-detail-briefs

**What Was Done:**
- ✅ Fix 1: `loadProspectBrief()` and `loadOrgBrief()` moved outside the try/catch in `loadPageData()` — they now always execute even if the main `/brief` GET fails
- ✅ Fix 2: GET brief route's response construction wrapped in second try/except — unhandled serialization errors now produce a logged 500 instead of a silent crash
- ✅ Fix 4: `refreshProspectBrief()` catch now renders a red error state with Retry button instead of the misleading "No prospect brief yet" placeholder
- ✅ All 84 tests passing

**Files Modified:**
- `app/templates/crm_prospect_detail.html` — Fix 1 (loadPageData resilience), Fix 4 (error state)
- `app/delivery/crm_blueprint.py` — Fix 2 (exception handling on GET brief)

**Note on Fix 3:** The actual 500 error described in the spec (root cause) appears to have been resolved by the prior session's key format unification. Both GET and POST endpoints returned 200 on manual testing today — no additional server-side fix was needed.

---

## Active Branch: `main`

**⚠️ ALL WORK HAPPENS ON `main`. DO NOT USE `deprecated-markdown`.**

---

## In Progress / Next Up

### 1. One Pending Spec
`docs/specs/SPEC_intelligent-task-extraction.md` — ready for implementation.

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
- **meeting_history.md still exists** — Old format file retained for backward compatibility. The two systems (meeting_history.md + meetings.json) are not yet unified.
- **Existing data not retroactively normalized** — `resolve_org_name()` only affects new writes.
- **Existing at_a_glance values are short tags** — Old 10-word tags remain in `briefs.json` until each brief is regenerated. No backfill needed.

---

## Deferred / Parked

- Azure deployment (not applicable to markdown-only app)
- PostgreSQL migration (reverted, staying with markdown)
- Multi-user auth (single-user local app)
- SPEC_drain-inbox-mcp-migration.md (future enhancement — requires MCP Outlook connector setup)
