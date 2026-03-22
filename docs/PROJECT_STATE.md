# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-21 — SPEC_engagement-heatmap implementation

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
  - 5 status tiers: No Contact (red) → Outbound Only (orange) → Inbound Reply (yellow) → Meeting Held (light green) → Meeting Scheduled (green)
  - Staleness muting: chip--aging (75% opacity, 8–14 days), chip--stale (50% opacity, 15–21 days)
  - Prospects >21 days since any interaction fall to No Contact
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

---

## What Was Just Completed (March 21, 2026)

### SPEC_engagement-heatmap

**What Was Done:**
- ✅ `get_heatmap_prospects()` added to `crm_reader.py` — scores all Stage 5 prospects across meetings.json, email_log.json, and interactions.md with a 21-day recency cutoff
- ✅ `/crm/health` route added to `crm_blueprint.py` — server-side scoring + group/sort, renders `crm_health.html`
- ✅ `crm_health.html` created — full dark theme, 5-tier color sections, status chips with staleness muting, prospect links, refresh button
- ✅ "Health" nav tab added to `_nav.html` (after Pipeline, before People)
- ✅ 3 `next_action` references removed from `crm_blueprint.py`:
  - `if field == 'next_action'` reject guard in inline-edit route (lines 1039–1040)
  - `('Next Action', 35)` column from Excel export column list
  - `next_action = p.get('Next Action', '')` + `cell_next` write in Excel row loop (shifted Notes → col 10, Last Touch → col 11)
- ✅ 84/84 tests passing

**Files Modified:**
- `app/sources/crm_reader.py` — added `get_heatmap_prospects()` and `AREC_DOMAINS` constant
- `app/delivery/crm_blueprint.py` — added `/crm/health` route, imported `get_heatmap_prospects`, removed 3 `next_action` refs
- `app/templates/crm_health.html` — new file
- `app/templates/_nav.html` — Health tab added

---

## What Was Completed (March 21, 2026 — earlier session)

### SPEC_teams-transcript-retrieval

**What Was Done:**
- ✅ Step 4b added to `crm-update` skill — pulls Teams transcripts for past meetings after calendar scan
- ✅ Full `read_resource(uri=event.uri)` → `read_resource(uri=meetingTranscriptUrl)` retrieval pattern
- ✅ WEBVTT parser: speaker-labeled output, consecutive-line consolidation
- ✅ Stores `transcript_url` + `notes_raw` on meeting record, marks `status="completed"`
- ✅ 84/84 tests passing

---

## Active Branch: `main`

**⚠️ ALL WORK HAPPENS ON `main`. DO NOT USE `deprecated-markdown`.**

---

## In Progress / Next Up

### 1. One Pending Spec
`docs/specs/SPEC_daily-health-report.md` is ready to implement. Run `/code-start` to begin.

### 2. Test `crm-update` Transcript Retrieval in Practice
Step 4b is implemented in the skill bundle. Run `/crm-update` after a Teams meeting to verify the full retrieval → WEBVTT conversion → notes_raw storage pipeline works end-to-end.

### 3. Tony Sync Setup Required
- **EGNYTE_API_TOKEN needed** — Must be obtained from Egnyte developer console and added to `app/.env`
- **Not scheduled yet** — Needs launchd job for 6 AM daily run
- **Manual review workflow not implemented** — Desktop/CoWork workflow for resolving low-confidence matches from `crm/tony_sync_pending.json`

### 4. Drain Inbox Re-auth
After adding `Mail.ReadWrite.Shared` scope, delete `~/.arec_briefing_token_cache.json` and re-run `drain_inbox.py` to trigger re-auth with the new scope.

---

## Known Issues

- **No test coverage for meetings subsystem** — meeting dedup tested manually only
- **No test coverage for org merge** — feature manually tested but no automated tests
- **MetLife contact ambiguity**: "Chris Aiken" and "Christopher Aiken" both exist; migration chose Chris Aiken (Stage 5). Worth auditing manually.
- **33 orgs without primary contact** — Migration skipped contacts where Primary Contact string didn't match a contact file (e.g., "TBD"). These orgs show "—" for primary contact.
- **meeting_history.md still exists** — Old format file retained for backward compatibility.
- **Existing data not retroactively normalized** — `resolve_org_name()` only affects new writes.

---

## Deferred / Parked

- Azure deployment (not applicable to markdown-only app)
- PostgreSQL migration (reverted, staying with markdown)
- Multi-user auth (single-user local app)
- SPEC_drain-inbox-mcp-migration.md (future enhancement — requires MCP Outlook connector setup)
