# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-19 — SPEC_prospect-org-redesign-fixes implementation

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
- **Organization Merge**: Full merge workflow on org edit page — select target, preview data migration, execute atomic merge, redirect to target org with success flash
- **Prospect Detail Page**: Context-dependent color coding with clear ownership boundaries (FULLY WORKING):
  - **Native sections (GREEN left-border)**: Prospect Card, Prospect Brief, Notes Log
  - **Cross-reference sections (BLUE right-border)**: Org Info Card, Org Brief, Meeting Summaries, Email History
  - Edit Prospect, Edit Org, and Scan Email buttons removed from header
  - All cross-reference cards have blue dot + navigation badge linking to owning page
  - No auto-synthesis on page load — all briefs show "Generate" button when empty
  - Org Brief is strictly read-only — shows "Generate one from the Org page" when empty
- **Org Edit Page**: Context-dependent color coding with clear ownership boundaries (FULLY WORKING):
  - **Native sections (GREEN left-border)**: Org Card (Type, Domain, Contacts), Org Brief, Org Notes Log, Meeting Summaries, Email History
  - **Cross-reference sections (BLUE right-border)**: Prospect summary cards (one per offering, read-only)
  - Notes field removed from org top card — now a standalone Notes Log card
  - Add Note button styled consistently (blue, not white)
  - Brief renamed "Org Brief" (was "Relationship Brief")
  - No auto-synthesis on page load — shows "Generate" button when no cached brief exists
- **Tony Excel Sync**: Daily Egnyte polling for Tony's Excel tracker, fuzzy org matching with alias support (`crm_reader.get_org_aliases_map()`), auto-syncs high-confidence changes to CRM with prospect notes integration
- **Pipeline Polish**: At a Glance text with 2-line wrap, Tasks column 350px width, assignee initials in parentheses, markdown stripping throughout
- **Person Name Linking**: App-wide clickable person names linking to `/crm/people/<slug>` using client-side `linkifyPersonNames()` function
- **Task Grouping APIs**: `/crm/api/tasks/by-prospect` and `/crm/api/tasks/by-owner` fully functional with filtering, sorting, and enrichment
- **Drain Inbox Hardening**: `drain_inbox.py` runs safely as unattended launchd process — dedup via `drain_seen_ids.json`, last-run metadata in `drain_last_run.json`, `Mail.ReadWrite.Shared` scope added to fix 403 on mark-as-read
- **Primary Contact on Org**: Primary contact is now an org-level attribute. `contacts/{slug}.md` files carry `Primary: true`. Star toggle on org detail page. Prospect detail + pipeline resolve primary through org, not the prospect record.
- **Primary Contact Field Persistence**: `Primary Contact` added to `PROSPECT_FIELD_ORDER` in `crm_reader.py`. Prospect-level Primary Contact values now survive write/read round trips. Different prospects for the same org can have different primary contacts.
- **Pipeline Type Column**: Type column now correctly displays org Type for each prospect. Type filter works on pipeline view.
- **Email Scan**: Header "Scan Email" button on prospect detail uses the `/crm/api/prospect/.../email-scan` route (via `runScanEmail()`). The per-prospect "Deep Scan (90d)" button has been removed — email scanning is now handled exclusively by the `/email-scan` Cowork skill.

---

## What Was Just Completed (March 19, 2026)

### Prospect & Org Redesign — Implementation Fixes

**Spec:** `SPEC_prospect-org-redesign-fixes.md` (moved to `docs/specs/implemented/`)

**What Was Done:**
- ✅ Fixed CSS specificity issue preventing color sidebar bars from rendering — added `!important` to `.card-native` and `.card-crossref` border rules in `app/static/crm.css`
- ✅ Fixed org brief auto-synthesis on org detail page — replaced auto-synthesis with `renderOrgBriefEmpty()` that shows "Generate" button
- ✅ Verified org brief on prospect detail is strictly read-only — loads from cache, shows "Generate from Org page" message if none exists, NEVER triggers synthesis
- ✅ Verified prospect brief on prospect detail shows "Generate" button when empty — no auto-synthesis on page load
- ✅ Verified GET endpoints (`/crm/api/prospect/.../prospect-brief` and `/crm/api/org/...`) return cached data ONLY — no server-side synthesis
- ✅ Verified meeting summaries section is called on page load via `loadMeetings()` on line 478
- ✅ All tests passing (67/67)
- ✅ Spec moved to `docs/specs/implemented/`

**Impact:**
- **Visual color coding now works**: Green left-borders visible on native cards, blue right-borders visible on cross-reference cards (both pages)
- **No unwanted API calls on page load**: Briefs only synthesize when user explicitly clicks Generate/Refresh buttons
- **Better UX**: Empty state messages clearly communicate where to generate briefs
- **Read-only integrity**: Org brief on prospect page never attempts to modify org data

**Files Modified:**
- `app/static/crm.css` — Added `!important` to border rules (3 lines)
- `app/templates/crm_org_edit.html` — Fixed `loadOrgBrief()`, added `renderOrgBriefEmpty()` function (13 lines changed)
- `app/templates/crm_prospect_detail.html` — Verified correct (no changes needed)
- `app/delivery/crm_blueprint.py` — Verified correct (no changes needed)

---

## Active Branch: `main`

**⚠️ ALL WORK HAPPENS ON `main`. DO NOT USE `deprecated-markdown`.**

---

## In Progress / Next Up

### 1. No Pending Specs
All specs in `docs/specs/` have been implemented.

### 2. Tony Sync Setup Required
- **EGNYTE_API_TOKEN needed** — Must be obtained from Egnyte developer console and added to `app/.env`
- **Not scheduled yet** — Needs launchd job for 6 AM daily run
- **Manual review workflow not implemented** — Desktop/CoWork workflow for resolving low-confidence matches from `crm/tony_sync_pending.json`

### 3. Drain Inbox Re-auth
After adding `Mail.ReadWrite.Shared` scope, the cached MSAL token needs to be refreshed. Delete `~/.arec_briefing_token_cache.json` and re-run `drain_inbox.py` to trigger a new device code flow that includes the new scope.

---

## Known Issues

- **No test coverage for meetings subsystem** — `test_meetings.py` mentioned in recent spec does not exist; meeting dedup tested manually
- **No test coverage for org merge** — Feature manually tested but no automated tests yet
- **MetLife contact ambiguity**: "Chris Aiken" and "Christopher Aiken" both exist; migration chose Chris Aiken (Stage 5). Worth auditing manually.
- **33 orgs without primary contact** — Migration skipped contacts where the prospect's Primary Contact string didn't match a contact file (e.g., "TBD", informal descriptions, email-appended names). These orgs show "—" for primary contact.
- **meeting_history.md still exists** — Old format file retained for backward compatibility with org detail pages that use `load_meeting_history()`. The two systems (meeting_history.md + meetings.json) are not yet unified.

---

## Deferred / Parked

- Azure deployment (not applicable to markdown-only app)
- PostgreSQL migration (reverted, staying with markdown)
- Multi-user auth (single-user local app)
- SPEC_drain-inbox-mcp-migration.md (future enhancement — requires MCP Outlook connector setup)
