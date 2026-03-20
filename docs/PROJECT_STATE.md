# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-19 — SPEC_enhanced-at-a-glance implementation

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
  - Edit Prospect, Edit Org, and Scan Email buttons removed from header
  - All cross-reference cards have blue dot + navigation badge linking to owning page
  - No auto-synthesis on page load — all briefs show "Generate" button when empty
  - Org Brief is strictly read-only — shows "Generate one from the Org page" when empty
  - **Both brief cards server-rendered** — saved briefs appear instantly on page load without AJAX
- **Org Edit Page**: Context-dependent color coding with clear ownership boundaries (FULLY WORKING):
  - **Native sections (GREEN left-border)**: Org Card (Type, Domain, Aliases, Contacts), Org Brief, Org Notes Log, Meeting Summaries, Email History
  - **Cross-reference sections (BLUE right-border)**: Prospect summary cards (one per offering, read-only)
  - Notes field removed from org top card — now a standalone Notes Log card
  - Add Note button styled consistently (blue, not white)
  - Brief renamed "Org Brief" (was "Relationship Brief")
  - No auto-synthesis on page load — shows "Generate" button when no cached brief exists
  - **Org brief server-rendered** — saved brief appears instantly on page load without AJAX
  - **Aliases field editable** — click to edit, comma-separated list, saves via PATCH endpoint
- **Tony Excel Sync**: Daily Egnyte polling for Tony's Excel tracker, fuzzy org matching with alias support (`crm_reader.get_org_aliases_map()`), auto-syncs high-confidence changes to CRM with prospect notes integration
- **Pipeline Polish**: At a Glance 2-line clamp display, Tasks column 350px width, assignee initials in parentheses, markdown stripping throughout
- **Enhanced At a Glance (NEW — FULLY WORKING)**: Pipeline "At a Glance" column upgraded from 10-word status tags to 2-sentence condensed relationship summaries
  - Claude prompt updated to request 2-sentence max, ~150-char summaries with specific names, dates, and next steps
  - Pipeline column now wraps to 2 lines with `-webkit-line-clamp:2` overflow; tooltip preserves full text
  - Old short values continue to display correctly until regenerated
- **Person Name Linking**: App-wide clickable person names linking to `/crm/people/<slug>` using client-side `linkifyPersonNames()` function
- **Task Grouping APIs**: `/crm/api/tasks/by-prospect` and `/crm/api/tasks/by-owner` fully functional with filtering, sorting, and enrichment
- **Drain Inbox Hardening**: `drain_inbox.py` runs safely as unattended launchd process — dedup via `drain_seen_ids.json`, last-run metadata in `drain_last_run.json`, `Mail.ReadWrite.Shared` scope added to fix 403 on mark-as-read
- **Primary Contact — Prospect-Level (FULLY WORKING)**: Primary Contact is a prospect-level field. `Primary Contact` field in `PROSPECT_FIELD_ORDER` survives write/read round trips. Pipeline API and Prospect Detail route both read from the prospect record — no more contact-file lookups for these two paths. Multi-prospect orgs (e.g., UTIMCO) can show different primary contacts per prospect.
- **Pipeline Type Column**: Type column now correctly displays org Type for each prospect. Type filter works on pipeline view.
- **Email Scan**: Header "Scan Email" button on prospect detail uses the `/crm/api/prospect/.../email-scan` route (via `runScanEmail()`). The per-prospect "Deep Scan (90d)" button has been removed — email scanning is now handled exclusively by the `/email-scan` Cowork skill.
- **Contact Title Field (FULLY WORKING)**: "Role" field renamed to "Title" throughout. `load_person()` returns `title` key. All 287 contact files migrated (`**Role:**` → `**Title:**`). Backward-compatible: files with `**Role:**` still parse correctly (mapped to `title`, but `**Title:**` always wins if both present).

---

## What Was Just Completed (March 19, 2026)

### Enhanced At a Glance Brief

**Spec:** `SPEC_enhanced-at-a-glance.md` (moved to `docs/specs/implemented/`)

**What Was Done:**
- ✅ Updated `AT_A_GLANCE_JSON_SUFFIX` in `brief_synthesizer.py` — prompt now requests 2-sentence max, ~150-char condensed narrative summary with specific names, dates, and next steps
- ✅ Replaced 10-word status tag examples with 2-sentence condensed brief examples
- ✅ Instruction changed from "10 words MAX" to "150 characters MAX, 2 sentences MAX"
- ✅ Updated `at_a_glance` cell renderer in `crm_pipeline.html` — removed 60-char truncation, added 2-line clamp CSS (`-webkit-line-clamp:2`, `white-space:normal`, `max-width:300px`), tooltip preserved
- ✅ All 84 tests passing

**Files Modified:**
- `app/briefing/brief_synthesizer.py`
- `app/templates/crm_pipeline.html`

**Business Impact:**
- Next time a prospect brief is generated, the At a Glance column will show a meaningful 2-sentence relationship summary instead of a sparse status tag
- Existing short values continue to render correctly until regenerated

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
- **Existing data not retroactively normalized** — `resolve_org_name()` only affects new writes. Old meetings/prospects with variant names remain as-is (alias-based reads handle them correctly).
- **Existing at_a_glance values are short tags** — Old 10-word status tags remain in `briefs.json` until each prospect's brief is regenerated. No backfill needed.

---

## Deferred / Parked

- Azure deployment (not applicable to markdown-only app)
- PostgreSQL migration (reverted, staying with markdown)
- Multi-user auth (single-user local app)
- SPEC_drain-inbox-mcp-migration.md (future enhancement — requires MCP Outlook connector setup)
