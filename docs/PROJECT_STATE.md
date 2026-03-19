# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-19 — SPEC_remove-email-deep-scan-button implemented

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
  - **Three-tier deduplication**: graph_event_id exact match + org+date±1 day fuzzy match (any status) + read-time dedup safety net
- **Organization Aliases**: Single source of truth is the `Aliases` field on each org in `organizations.md`. Used by search, briefs, merge, and Tony sync. `crm/org_aliases.json` retired and deleted.
- **Organization Merge**: Full merge workflow on org edit page — select target, preview data migration, execute atomic merge, redirect to target org with success flash
- **Prospect Detail Page**: Clean UI with notes log, task editing, email scanning, and markdown-free display
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

### Deep Scan Button Removed (SPEC_remove-email-deep-scan-button.md)

**What Was Done:**
- ✅ Removed `.btn-scan`, `.btn-scan:hover`, `.btn-scan:disabled` CSS from `crm_prospect_detail.html` (`.scan-status` kept — still used by header Scan Email button)
- ✅ Removed Deep Scan button HTML and its wrapper `<div>` from the Email History section header; kept collapsible toggle
- ✅ Removed `runDeepEmailScan()` JS function (~40 lines)
- ✅ Removed `api_prospect_email_scan()` Flask route and handler (~200 lines) from `crm_blueprint.py`
- ✅ Removed `search_emails_deep()` from `ms_graph.py` (was only called by the deleted route)
- ✅ Spec moved to `docs/specs/implemented/`

**Test Results:** 67/67 passing

**Impact:**
- Route `/crm/api/prospect/{offering}/{org}/email-scan` now returns 404
- Email History section still renders correctly — reads from brief endpoint, unaffected
- No Haiku API credits wasted on per-email summarization
- Email scanning now exclusively via the `/email-scan` Cowork skill (6-pass, all mailboxes)

---

## Active Branch: `main`

**⚠️ ALL WORK HAPPENS ON `main`. DO NOT USE `deprecated-markdown`.**

---

## In Progress / Next Up

### 1. SPEC_drain-inbox-hardening — Re-auth required
After adding `Mail.ReadWrite.Shared` scope, the cached MSAL token needs to be refreshed. Delete `~/.arec_briefing_token_cache.json` and re-run `drain_inbox.py` to trigger a new device code flow that includes the new scope.

### 2. Tony Sync Setup Required
- **EGNYTE_API_TOKEN needed** — Must be obtained from Egnyte developer console and added to `app/.env`
- **Not scheduled yet** — Needs launchd job for 6 AM daily run
- **Manual review workflow not implemented** — Desktop/CoWork workflow for resolving low-confidence matches from `crm/tony_sync_pending.json`

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
