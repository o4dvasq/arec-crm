# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-19 — SPEC_consolidate-alias-systems implemented

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
- **Organization Aliases**: Single source of truth is the `Aliases` field on each org in `organizations.md`. Used by search, briefs, merge, and Tony sync.
- **Organization Merge**: Full merge workflow on org edit page — select target, preview data migration, execute atomic merge, redirect to target org with success flash
- **Prospect Detail Page**: Clean UI with notes log, task editing, email scanning, and markdown-free display
- **Tony Excel Sync**: Daily Egnyte polling for Tony's Excel tracker, fuzzy org matching with alias support (`crm_reader.get_org_aliases_map()`), auto-syncs high-confidence changes to CRM with prospect notes integration
- **Pipeline Polish**: At a Glance text with 2-line wrap, Tasks column 350px width, assignee initials in parentheses, markdown stripping throughout
- **Person Name Linking**: App-wide clickable person names linking to `/crm/people/<slug>` using client-side `linkifyPersonNames()` function
- **Task Grouping APIs**: `/crm/api/tasks/by-prospect` and `/crm/api/tasks/by-owner` fully functional with filtering, sorting, and enrichment
- **Drain Inbox Hardening**: `drain_inbox.py` runs safely as unattended launchd process — dedup via `drain_seen_ids.json`, last-run metadata in `drain_last_run.json`, `Mail.ReadWrite.Shared` scope added to fix 403 on mark-as-read
- **Primary Contact on Org**: Primary contact is now an org-level attribute. `contacts/{slug}.md` files carry `Primary: true`. Star toggle on org detail page. Prospect detail + pipeline resolve primary through org, not the prospect record.

---

## What Was Just Completed (March 19, 2026)

### Consolidate Alias Systems (SPEC_consolidate-alias-systems.md)

**What Was Done:**
- ✅ Migrated all 8 entries from `crm/org_aliases.json` into `Aliases` fields on corresponding orgs in `organizations.md`
  - Future Fund → `FutureFund`
  - J.P. Morgan Asset Management → `JPMorgan Asset Mgmt` (already had JPAM, JP Morgan, JPMorgan AM)
  - Mass Mutual Life Insurance Co. → `Mass Mutual, MassMutual`
  - Merseyside Pension Fund → `Merseyside`
  - Teachers Retirement System of Texas (Texas Teachers) → `Teachers Retirement System (TRS), TRS` (added to existing TRS aliases)
  - UTIMCO - Hedge Fund → `UTIMCO`
  - UTIMCO - Real Estate → `UTIMCO (Matt Saverin)`
  - NPS (Korea SWF) — already canonical name, no alias needed
- ✅ `tony_sync.py`: removed `ALIASES_PATH` constant and `load_aliases()` function
- ✅ `tony_sync.py`: now imports and calls `crm_reader.get_org_aliases_map()` for alias resolution
- ✅ Diff report text updated to reference CRM org edit page instead of `org_aliases.json`
- ✅ `crm/org_aliases.json` deleted

**Test Results:** 89/89 passing

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

### 3. SPEC_primary-contact-on-org — Only remaining spec
Only spec in `docs/specs/` (non-README) is `SPEC_primary-contact-on-org.md`.

---

## Known Issues

- **No test coverage for org merge** — Feature manually tested but no automated tests yet
- **MetLife contact ambiguity**: "Chris Aiken" and "Christopher Aiken" both exist; migration chose Chris Aiken (Stage 5). Worth auditing manually.
- **33 orgs without primary contact** — Migration skipped contacts where the prospect's Primary Contact string didn't match a contact file (e.g., "TBD", informal descriptions, email-appended names). These orgs show "—" for primary contact.

---

## Deferred / Parked

- Azure deployment (not applicable to markdown-only app)
- PostgreSQL migration (reverted, staying with markdown)
- Multi-user auth (single-user local app)
- SPEC_drain-inbox-mcp-migration.md (future enhancement — requires MCP Outlook connector setup)
