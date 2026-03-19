# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-19 — SPEC_drain-inbox-hardening implemented

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

---

## What Was Just Completed (March 19, 2026)

### Drain Inbox Hardening (SPEC_drain-inbox-hardening.md)

**What Was Done:**
- ✅ `crm/drain_last_run.json` written after every run (success, failure, and quiet inbox). Schema: `{last_run, messages_processed, messages_skipped_dedup, exit_code, error}`.
- ✅ `crm/drain_seen_ids.json` dedup: messages already written to `inbox.md` are skipped on subsequent runs even if still unread in the mailbox (mark-as-read failure protection). Entries older than 30 days pruned automatically.
- ✅ Seen IDs written to `drain_seen_ids.json` **before** `mark_as_read` call — ensures dedup holds even if mark-as-read fails silently.
- ✅ `Mail.ReadWrite.Shared` added to `DELEGATED_SCOPES` in `graph_auth.py` — fixes 403 on shared mailbox write operations. (Note: re-auth required after this change to pick up new scope.)
- ✅ Both `crm/drain_last_run.json` and `crm/drain_seen_ids.json` added to `.gitignore` (machine-local state).
- ✅ `ms_graph.py` confirmed already correct — `mark_as_read` and `move_message` already use `users/{mailbox}` URLs, not `/me/`.

**Test Results:** 89/89 passing

---

## Active Branch: `main`

**⚠️ ALL WORK HAPPENS ON `main`. DO NOT USE `deprecated-markdown`.**

---

## In Progress / Next Up

### 1. SPEC_primary-contact-on-org.md — READY TO IMPLEMENT

Spec is written and reviewed. Implementation plan confirmed. No code written yet.

**Key changes:**
- `crm_reader.py`: restore `PEOPLE_ROOT = contacts/` (working tree accidentally reverted to `memory/people/`); add `get_primary_contact()`, `set_primary_contact()`, `clear_primary_contact()`; update `load_person()` to parse `Primary:` field; update `get_contacts_for_org()` to include `is_primary`; update `get_prospect_full()` to resolve primary from org; remove `Primary Contact` from `PROSPECT_FIELD_ORDER`/`EDITABLE_FIELDS`; remove auto-link trigger in `update_prospect_field()`
- `crm_blueprint.py`: add `POST /api/org/<org_name>/primary-contact`; update `api_org_add_contact` for auto-primary
- `crm_org_detail.html`: star toggle on contact cards
- `crm_prospect_detail.html`: resolve primary contact via server-side `primary_contact_name`
- `crm_prospect_edit.html`: remove Primary Contact field
- `scripts/migrate_primary_contact_to_org.py`: new migration script (run manually after implementation)

**Path discrepancy to fix:** Working tree has `PEOPLE_ROOT = memory/people/` but HEAD commit (and correct location) is `contacts/`. Fix as first step of implementation.

### 2. Re-auth required for drain inbox
After adding `Mail.ReadWrite.Shared` scope, the cached MSAL token needs to be refreshed. Delete `~/.arec_briefing_token_cache.json` and re-run `drain_inbox.py` to trigger a new device code flow that includes the new scope.

### 3. Tony Sync Setup Required
- **EGNYTE_API_TOKEN needed** — Must be obtained from Egnyte developer console and added to `app/.env`
- **Not scheduled yet** — Needs launchd job for 6 AM daily run
- **Manual review workflow not implemented** — Desktop/CoWork workflow for resolving low-confidence matches from `crm/tony_sync_pending.json`

---

## Known Issues

- **No test coverage for org merge** — Feature manually tested but no automated tests yet
- **`PEOPLE_ROOT` working tree revert** — Current working tree has `memory/people/` but should be `contacts/`; will be fixed as part of SPEC_primary-contact-on-org implementation

---

## Deferred / Parked

- Azure deployment (not applicable to markdown-only app)
- PostgreSQL migration (reverted, staying with markdown)
- Multi-user auth (single-user local app)
- SPEC_drain-inbox-mcp-migration.md (future enhancement — requires MCP Outlook connector setup)
