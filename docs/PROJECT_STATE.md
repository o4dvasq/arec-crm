# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-19 — SPEC_prospect-org-page-redesign implemented

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
  - Row click opens edit modal pre-populated from meeting record
  - Prospect name link (when org+offering present) navigates to prospect detail page
  - Edit modal: "Edit Meeting" header, "Save Changes" button, PATCH on submit
  - Delete with inline "Are you sure? Yes · No" confirmation (no browser dialog)
  - Meeting Time field removed from modal entirely
  - Column header and label renamed "Organization" → "Prospect"
  - **Three-tier deduplication**: graph_event_id exact match + org+date±1 day fuzzy match (any status) + read-time dedup safety net
- **Organization Aliases**: Single source of truth is the `Aliases` field on each org in `organizations.md`. Used by search, briefs, merge, and Tony sync. `crm/org_aliases.json` retired and deleted.
- **Organization Merge**: Full merge workflow on org edit page — select target, preview data migration, execute atomic merge, redirect to target org with success flash
- **Prospect Detail Page**: Color-coded UI (blue=prospect-owned, green=org-owned) with:
  - Prospect Brief (offering-specific, 2-3 sentences)
  - Org Brief (read-only, comprehensive org-level intelligence)
  - Org Info Card (read-only, includes Type, Domain, Contacts)
  - Cross-reference badges linking back to org page
  - Notes Log (prospect-owned)
  - Meeting Summaries (org-owned, badged)
  - Email History (org-owned, badged)
- **Org Edit Page**: Color-coded UI (green=org-owned, blue=prospect-owned) with:
  - Org Card (Type, Domain, Notes, Contacts inline)
  - Prospect Cards (one per offering, read-only, badged)
  - Org Brief (refreshable)
  - Org Notes Log (separate from prospect notes)
  - Meeting Summaries (org-owned)
  - Email History (org-owned)
- **Tony Excel Sync**: Daily Egnyte polling for Tony's Excel tracker, fuzzy org matching with alias support (`crm_reader.get_org_aliases_map()`), auto-syncs high-confidence changes to CRM with prospect notes integration
- **Pipeline Polish**: At a Glance text with 2-line wrap, Tasks column 350px width, assignee initials in parentheses, markdown stripping throughout
- **Person Name Linking**: App-wide clickable person names linking to `/crm/people/<slug>` using client-side `linkifyPersonNames()` function
- **Task Grouping APIs**: `/crm/api/tasks/by-prospect` and `/crm/api/tasks/by-owner` fully functional with filtering, sorting, and enrichment
- **Drain Inbox Hardening**: `drain_inbox.py` runs safely as unattended launchd process — dedup via `drain_seen_ids.json`, last-run metadata in `drain_last_run.json`, `Mail.ReadWrite.Shared` scope added to fix 403 on mark-as-read
- **Primary Contact on Org**: Primary contact is now an org-level attribute. `contacts/{slug}.md` files carry `Primary: true`. Star toggle on org detail page. Prospect detail + pipeline resolve primary through org, not the prospect record.
- **Pipeline Type Column**: Type column now correctly displays org Type for each prospect. Type filter works on pipeline view.
- **Email Scan**: Header "Scan Email" button on prospect detail uses the `/crm/api/prospect/.../email-scan` route (via `runScanEmail()`). The per-prospect "Deep Scan (90d)" button has been removed — email scanning is now handled exclusively by the `/email-scan` Cowork skill.

---

## What Was Just Completed (March 19, 2026)

### Prospect/Org Page Redesign (SPEC_prospect-org-page-redesign.md)

**What Was Done:**
- ✅ Created two-tier brief system: Prospect Brief (offering-specific) + Org Brief (org-level)
- ✅ Added `PROSPECT_BRIEF_SYSTEM_PROMPT` to `relationship_brief.py` (2-3 sentence offering-focused prompt)
- ✅ Added `load_org_notes()` and `save_org_note()` to `crm_reader.py` (uses `org:{org}` key in `prospect_notes.json`)
- ✅ Added `/crm/api/prospect/<offering>/<org>/prospect-brief` routes (GET/POST) to `crm_blueprint.py`
- ✅ Added `/crm/api/org/<name>/notes` routes (GET/POST) to `crm_blueprint.py`
- ✅ Updated `prospect_detail()` route to pass `org_brief_saved`, `prospect_brief_saved`, `meetings`, `emails` to template
- ✅ Updated `org_edit()` route to pass `org_notes`, `meetings`, `emails` to template
- ✅ Created `static/crm.css` with color-coded card classes (`.card-prospect`, `.card-org`, `.card-badge-*`)
- ✅ Restructured `crm_prospect_detail.html`:
  - Prospect Card (blue) with Stage, Assigned To, Target, Closing, Primary Contact, Last Touch
  - Org Info Card (green, read-only) with Type, Domain, Contacts
  - Prospect Brief Card (blue) with refresh button
  - Org Brief Card (green, read-only) with "From Org →" badge
  - Notes Log (blue, prospect-owned)
  - Meeting Summaries (green, org-owned, badged)
  - Email History (green, org-owned, badged)
- ✅ Restructured `crm_org_edit.html`:
  - Org Card (green) with Type, Domain, Notes, Contacts inline
  - Prospect Cards (blue, read-only, one per offering) with "View Prospect →" badge
  - Org Brief Card (green) with refresh button
  - Meeting Summaries (green, collapsible)
  - Org Notes Log (green) with add note form
  - Email History (green, collapsible)
- ✅ Updated JavaScript in both templates to handle new brief sections and data loading
- ✅ Spec moved to `docs/specs/implemented/`

**Test Results:** 67/67 passing

**Impact:**
- Clear ownership boundaries: blue = prospect-owned, green = org-owned
- Prospect Brief focuses on current offering status (2-3 sentences)
- Org Brief provides comprehensive org-level context (read-only on prospect page)
- Contacts now read-only on prospect page (org-owned)
- Org page has dedicated Notes Log (separate from prospect notes)
- Visual cross-references with badges reduce navigation confusion
- All data flows preserved — nothing lost, just reorganized for clarity

---

## Active Branch: `main`

**⚠️ ALL WORK HAPPENS ON `main`. DO NOT USE `deprecated-markdown`.**

---

## In Progress / Next Up

### 1. SPEC_primary-contact-batch-enrichment
Ready to implement in `docs/specs/`. Adds batch enrichment workflow for orgs missing primary contact.

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

---

## Deferred / Parked

- Azure deployment (not applicable to markdown-only app)
- PostgreSQL migration (reverted, staying with markdown)
- Multi-user auth (single-user local app)
- SPEC_drain-inbox-mcp-migration.md (future enhancement — requires MCP Outlook connector setup)
