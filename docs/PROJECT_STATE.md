# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-19 — SPEC_primary-contact-on-org implemented

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
- **Drain Inbox Hardening**: `drain_inbox.py` runs safely as unattended launchd process — dedup via `drain_seen_ids.json`, last-run metadata in `drain_last_run.json`, `Mail.ReadWrite.Shared` scope added to fix 403 on mark-as-read
- **Primary Contact on Org**: Primary contact is now an org-level attribute. `contacts/{slug}.md` files carry `Primary: true`. Star toggle on org detail page. Prospect detail + pipeline resolve primary through org, not the prospect record.

---

## What Was Just Completed (March 19, 2026)

### Primary Contact on Org (SPEC_primary-contact-on-org.md)

**What Was Done:**
- ✅ `PEOPLE_ROOT` fixed to `contacts/` (had been accidentally reverted to `memory/people/`)
- ✅ `load_person()` now parses `Primary:` field and returns `is_primary: bool`
- ✅ `get_primary_contact(org)`, `set_primary_contact(org, name)`, `clear_primary_contact(org)` added to `crm_reader.py`
- ✅ Helper `_set_contact_primary_field(slug, value)` writes/removes `- **Primary:** true` in contact files
- ✅ `Primary Contact` removed from `PROSPECT_FIELD_ORDER` and `EDITABLE_FIELDS`
- ✅ Auto-link trigger for primary contact removed from `update_prospect_field()`
- ✅ `get_prospect_full()` resolves `Primary Contact` string through org's contacts (backward-compatible)
- ✅ `POST /crm/api/org/<org_name>/primary-contact` added (set with `{contact_name: "Name"}`, clear with `{contact_name: null}`)
- ✅ `api_org_add_contact()`: fixed `people_dir` to `contacts/`; auto-sets primary when first contact added to org
- ✅ Org detail page: star button (filled gold = primary, outline = not) with `togglePrimary()` JS; `lucide.createIcons()` called after re-render
- ✅ Prospect detail: resolved from `primary_contact_name` passed by route (server-side), not prospect record
- ✅ Prospect edit form: Primary Contact field + JS removed entirely
- ✅ Migration script `scripts/migrate_primary_contact_to_org.py` created and run: 98 orgs updated, 4 conflicts resolved (highest stage wins), 200 `Primary Contact:` lines removed from `crm/prospects.md`

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

### 3. SPEC_drain-inbox-hardening.md — Next spec ready
Only spec remaining in `docs/specs/` is `SPEC_drain-inbox-hardening.md`.

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
