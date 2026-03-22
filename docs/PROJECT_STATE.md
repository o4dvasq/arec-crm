# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-22 — SPEC_fundraising-allies implementation

---

## What's Built and Working

### AREC CRM — Single-User Fundraising Platform (LOCAL ONLY)
- **Local URL**: http://localhost:8000/crm
- **Backend**: Markdown-only (`crm_reader.py`). All data in `crm/*.md` and `crm/*.json` files.
- **Authentication**: DEV_USER env var sets g.user. No database, no MSAL.
- **CRM Features**: Pipeline, prospect detail, org management, relationship briefs, contact intelligence, interaction history, tasks, meetings, engagement health
- **Brief Synthesis**: Two-tier brief system — Prospect Brief (offering-specific, 2-3 sentences) + Org Brief (comprehensive, org-level)
- **Dark Theme**: Full dark theme throughout
- **Navigation**: Global search, centered nav tabs (Tasks | Pipeline | Health | People | Orgs | Meetings) with bullseye icon and hover user menu
- **Flat Task CRUD (`/crm/tasks`)**: Canonical tasks page — owner-grouped Kanban board. Flat task list (no sections). All CRUD routes live on `crm_blueprint.py` at `/crm/api/task/<index>`.
  - `GET /crm/api/all-tasks` returns `{"open": [...], "done": [...]}`
  - `POST /crm/api/task` → create; `PUT /crm/api/task/<index>` → edit; `DELETE` → delete
  - `POST /crm/api/task/<index>/complete` and `/restore` physically move tasks to/from `## Done`
  - `PATCH /crm/api/task/<index>/status` and `/priority` for quick updates
  - `task-edit-modal.js` (shared by crm_tasks and pipeline) calls `/crm/api/task/...`
- **CRM Tasks Page (`/crm/tasks`)**: Two-section view (My Tasks | Team Tasks) with search, sorting by priority then deal size, enriched with prospect data
- **Meetings Page**: `/crm/meetings` — two-tab view (Scheduled | Past) with full CRUD, AI notes processing, insight approval workflow. In main nav.
  - Data backed by `crm/meetings.json` (migrated from `meeting_history.md`)
  - Row click opens edit modal pre-populated from meeting record
  - Three-tier deduplication: graph_event_id exact match + org+date±1 day fuzzy match + read-time dedup safety net
- **Health Page (`/crm/health`)**: Engagement heatmap for all Stage 5 prospects
  - 6 status tiers: No Contact (red) → Needs Follow-up (dark red) → Outbound Only (orange) → Inbound Reply (yellow) → Meeting Held (light green) → Meeting Scheduled (green)
  - Staleness muting: chip--aging (75% opacity, 8–14 days), chip--stale (50% opacity, 15–21 days) — applies to tiers 2–4 only; No Contact and Needs Follow-up have no opacity muting
  - Prospects >21 days since last interaction: "Needs Follow-up" if any history exists, "No Contact" only if zero history across all sources
  - Within each tier sorted by Target descending
  - Data sourced from meetings.json, email_log.json, interactions.md
- **Organization Aliases**: Single source of truth is the `Aliases` field on each org in `organizations.md`. Used by search, briefs, merge, and Tony sync.
- **Alias Normalization (FULLY WORKING)**: Write-path normalization prevents org name drift
  - `resolve_org_name()` converts aliases to canonical names before storage
  - All 5 write endpoints normalized: meeting create/update, prospect create, org contacts add, org notes add
  - Email fuzzy matching enhanced to check aliases (6-char threshold preserved)
- **Organization Merge**: Full merge workflow on org edit page
- **Prospect Detail Page**: Context-dependent color coding; both brief cards server-rendered; resilient loading
- **Tony Excel Sync**: Daily Egnyte polling for Tony's Excel tracker, fuzzy org matching with alias support
- **Teams Transcript Auto-Retrieval**: `crm-update` skill Step 4b pulls Teams transcripts for past meetings after calendar scan, converts WEBVTT to speaker-labeled text, stores as `notes_raw` → auto-processed by Step 5 AI summarization
- **Enhanced At a Glance**: Temporal awareness, meeting-centric priority framework, unified `{org}::{offering}` brief key format
- **Person Name Linking**: App-wide clickable person names linking to `/crm/people/<slug>`
- **Task Grouping APIs**: `/crm/api/tasks/by-prospect` and `/crm/api/tasks/by-owner` fully functional
- **Drain Inbox Hardening**: Runs as unattended launchd process with dedup and last-run metadata
- **Primary Contact — Prospect-Level (FULLY WORKING)**: Primary Contact is a prospect-level field
- **Fundraising Ally Pass-Through (FULLY WORKING)**: Placement agents and individual connectors are treated as pass-through entities in the email/calendar matching pipeline. Emails matched to an ally continue scanning for a real prospect org. Ally-only emails are silently skipped.

---

## What Was Just Completed (March 22, 2026)

### SPEC_fundraising-allies

**What Was Done:**
- ✅ `crm/fundraising_allies.json` — new config file with 3 placement agent orgs (South40 Capital, Angeloni & Co, JTP Capital) and 3 individual connectors (Greg Kostka, Scott Richland, Ira Lubert)
- ✅ `crm/config.md` — added `Placement Agent` org type
- ✅ `crm/organizations.md` — JRT Partners renamed to JTP Capital; South40 Capital and Angeloni & Co added as new entries; all three classified as `Placement Agent`
- ✅ `crm_reader.py` — `load_fundraising_allies()`, `is_ally_org()`, `is_ally_email()`, `get_individual_ally_name()`, `FUNDRAISING_ALLIES_PATH` constant
- ✅ `email_matching.py` — `ALLY_DOMAINS` frozenset loaded from fundraising_allies.json at import time
- ✅ `graph_poller.py` — `match_email_to_org()` rewritten with ally pass-through; `_is_ally_participant()` and `_scan_for_real_org()` helpers; `via_ally` field in `build_staged_item()`
- ✅ `deep_scan_team.py` — `match_calendar_event_to_org()` rewritten with same pass-through logic; `via_ally` in `build_calendar_staged_item()`
- ✅ 10 new tests in `test_email_matching.py`: ally org/email helpers, pass-through match, ally-only skip, Lubert email-vs-domain distinction
- ✅ 108/108 tests passing
- ✅ Key constraint honored: `ilubert@belgravialp.com` is email-keyed only — other `@belgravialp.com` addresses match Belgravia Management normally (Stage 7 prospect)

**Files Modified:**
- `crm/fundraising_allies.json` — new
- `crm/config.md`
- `crm/organizations.md`
- `app/sources/crm_reader.py`
- `app/sources/email_matching.py`
- `app/graph_poller.py`
- `scripts/deep_scan_team.py`
- `app/tests/test_email_matching.py`

---

## What Was Completed (March 22, 2026 — earlier session)

### SPEC_heatmap-stale-tier
- ✅ Added `stale` ("Needs Follow-up") tier to `get_heatmap_prospects()` — distinguishes prospects with prior history (stale) from truly zero-history prospects (no_contact)
- ✅ PSERS and San Joaquin CERA now correctly appear in "Needs Follow-up" instead of "No Contact"
- ✅ 98/98 tests passing

---

## Active Branch: `main`

**⚠️ ALL WORK HAPPENS ON `main`. DO NOT USE `deprecated-markdown`.**

---

## In Progress / Next Up

### 1. One Pending Spec
`docs/specs/SPEC_daily-health-report.md` is ready to implement. Run `/code-start` to begin.

### 2. Greg Kostka Email Missing
`crm/fundraising_allies.json` has `"email": ""` for Greg Kostka — no email on file in `contacts/`. When his email is known, update `fundraising_allies.json` so he's properly filtered as an individual ally.

### 3. Test `crm-update` Transcript Retrieval in Practice
Step 4b is implemented in the skill bundle. Run `/crm-update` after a Teams meeting to verify the full retrieval → WEBVTT conversion → notes_raw storage pipeline works end-to-end.

### 4. Tony Sync Setup Required
- **EGNYTE_API_TOKEN needed** — Must be obtained from Egnyte developer console and added to `app/.env`
- **Not scheduled yet** — Needs launchd job for 6 AM daily run
- **Manual review workflow not implemented** — Desktop/CoWork workflow for resolving low-confidence matches from `crm/tony_sync_pending.json`

### 5. Drain Inbox Re-auth
After adding `Mail.ReadWrite.Shared` scope, delete `~/.arec_briefing_token_cache.json` and re-run `drain_inbox.py` to trigger re-auth with the new scope.

---

## Known Issues

- **No test coverage for meetings subsystem** — meeting dedup tested manually only
- **No test coverage for org merge** — feature manually tested but no automated tests
- **MetLife contact ambiguity**: "Chris Aiken" and "Christopher Aiken" both exist; migration chose Chris Aiken (Stage 5). Worth auditing manually.
- **33 orgs without primary contact** — Migration skipped contacts where Primary Contact string didn't match a contact file (e.g., "TBD"). These orgs show "—" for primary contact.
- **meeting_history.md still exists** — Old format file retained for backward compatibility.
- **Existing data not retroactively normalized** — `resolve_org_name()` only affects new writes.
- **Greg Kostka email unknown** — `fundraising_allies.json` has blank email for Greg Kostka; his pass-through won't trigger until email is populated.

---

## Deferred / Parked

- Azure deployment (not applicable to markdown-only app)
- PostgreSQL migration (reverted, staying with markdown)
- Multi-user auth (single-user local app)
- SPEC_drain-inbox-mcp-migration.md (future enhancement — requires MCP Outlook connector setup)
