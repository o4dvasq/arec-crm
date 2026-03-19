# arec-crm — Architecture

> Load this file when discussing structural or architectural changes.
> Do NOT load for routine task/CRM/briefing work.

**Location:** `~/Dropbox/projects/arec-crm/`

**Last audited:** 2026-03-19 (updated: drain inbox hardening — drain_last_run.json, drain_seen_ids.json)

---

## ⚠️ Development Rules

**ALL work on `azure-migration` branch. NEVER modify `deprecated-markdown`.** The branch name is historical — this is the active development branch.

---

## System Overview

arec-crm is a single-user fundraising CRM platform backed entirely by markdown files. Runs locally on Flask (port 8000). No database. No authentication server. Just files and a web UI.

**Local URL:** http://localhost:8000/crm

**Core layers:**

1. **Web Dashboard** — Flask app (port 8000). Full dark theme.
2. **Markdown Backend** — All CRM data in markdown files (`crm/*.md`) and JSON files (`crm/*.json`). `crm_reader.py` is the data layer.
3. **Local Auth** — DEV_USER env var sets g.user. No database, no MSAL.
4. **Intelligence** — Relationship briefs (org + person) via Claude API, cached in `crm/briefs.json`.

---

## Directory Map

```
arec-crm/                        (~/Dropbox/projects/arec-crm/)
├── CLAUDE.md                  ← Project config (run commands, key files, conventions)
├── config.yaml                ← App configuration (stages, team, offerings)
├── crm-inbox.md               ← CRM inbox queue
│
├── docs/                      ← Architecture, decisions, specs
│   ├── ARCHITECTURE.md        ← This file
│   ├── DECISIONS.md           ← Append-only decisions log
│   ├── PROJECT_STATE.md       ← Overwritten after each session
│   └── specs/                 ← SPEC_ files per feature
│
├── app/                       ← Python backend
│   ├── .env                   ← Environment variables (DEV_USER, ANTHROPIC_API_KEY, EGNYTE_API_TOKEN)
│   ├── main.py                ← Morning briefing orchestrator (now includes Tony sync)
│   ├── delivery/
│   │   ├── dashboard.py       ← Flask main app (sets g.user from DEV_USER)
│   │   └── crm_blueprint.py   ← CRM routes + brief synthesis endpoints
│   ├── sources/
│   │   ├── crm_reader.py      ← Markdown backend (all read/write functions)
│   │   ├── relationship_brief.py  ← Context aggregation for briefs
│   │   └── tony_sync.py       ← Egnyte polling + Excel parsing + fuzzy org matching
│   ├── briefing/
│   │   └── brief_synthesizer.py  ← Claude API call + JSON parsing
│   ├── templates/
│   │   ├── crm_pipeline.html
│   │   ├── crm_prospect_detail.html
│   │   ├── crm_tasks.html
│   │   ├── crm_org_edit.html
│   │   ├── crm_people.html
│   │   └── crm_person_detail.html
│   ├── static/
│   │   ├── crm.css
│   │   └── crm.js
│   └── tests/                 ← Unit tests
│
├── crm/                       ← CRM data files (markdown + JSON)
│   ├── config.yaml            ← Linked to root config.yaml
│   ├── prospects.md           ← Prospect records (markdown table)
│   ├── organizations.md       ← Organization records (markdown table)
│   ├── contacts_index.md      ← Contact→org mapping
│   ├── interactions_log.md    ← Interaction history
│   ├── TASKS.md               ← Prospect tasks
│   ├── email_log.json         ← Email history
│   ├── briefs.json            ← Cached relationship briefs
│   ├── unmatched.json         ← Unmatched emails
│   ├── prospect_notes.json    ← Prospect notes log
│   ├── meetings.json          ← Meeting records (UUID-keyed)
│   ├── org_notes.json         ← Organization notes log
│   ├── org_aliases.json       ← Org name aliases for fuzzy matching (Tony sync)
│   ├── tony_sync_state.json   ← Tony Excel sync state (last processed file)
│   ├── tony_sync_pending.json ← Low-confidence matches awaiting manual review
│   ├── drain_last_run.json    ← Last drain_inbox.py run metadata (gitignored)
│   └── drain_seen_ids.json    ← Message IDs already written to inbox.md (gitignored)
│
└── contacts/                  ← People knowledge base
    └── {slug}.md              ← Individual person profiles
```

---

## Core Data Flows

### Relationship Brief Synthesis (dashboard, on demand)
```
User clicks "Refresh Brief" on prospect detail page
  → Aggregate context from 9 sources:
      1. prospect record          2. org record
      3. contacts + people intel  4. interaction history
      5. glossary entry           6. meeting summaries
      7. active tasks             8. email history
      9. freeform notes
  → brief_synthesizer.py
      → Claude API (claude-sonnet-4-6, 1600 tokens)
      → Parse JSON {narrative, at_a_glance}
      → Fallback to raw response if parse fails
  → Cache in crm/briefs.json
  → Display on prospect card
```

### Person Brief Synthesis (dashboard, on demand)
```
User clicks "Refresh Brief" on person detail page
  → relationship_brief.py → collect_person_data()
  → build_person_context_block()
  → Claude API (claude-sonnet-4-6) with PERSON_BRIEF_SYSTEM_PROMPT
  → Parse JSON {narrative, at_a_glance}
```

### Tony Excel Sync (daily, 6 AM)
```
app/main.py (morning briefing)
  → tony_sync.run_sync()
      1. List Egnyte folder: Shared/AREC/Investor Relations/General Fundraising/
      2. Find newest file matching pattern: "AREC Debt Fund II Marketing A List - MASTER*"
      3. Check crm/tony_sync_state.json → if same file, exit
      4. Download Excel via Egnyte API
      5. Parse Active sheet (row 6+): Col A=Priority, B=Org, C=Point Person, K=Notes
      6. For each row:
          a. Strip parentheticals from org name
          b. Match org: alias lookup → exact match → fuzzy match (difflib)
          c. Normalize Point Person (Avila → Tony Avila, Reisner/Flynn → Zach Reisner)
          d. Detect changes: Assigned To, Notes, Priority='x'→Declined, 'Closed'→Closed
      7. Send email diff to Oscar + Paige (MS Graph API)
      8. Apply high-confidence changes (≥0.85):
          - New prospects → Stage 5 Interested, Urgency High
          - Update Assigned To, Notes (only if Tony's notes non-empty)
          - Set stage Declined/Closed on 'x'/'Closed' priority
      9. Update crm/tony_sync_state.json (filename, modified timestamp)
```

---

## External Integrations

| Service | Library | Usage |
|---------|---------|-------|
| Claude API | `anthropic` | Brief synthesis, person briefs |
| Egnyte | `requests` | Tony Excel sync (file polling + download) |
| MS Graph API | `requests` | Email notifications (Tony sync), email scanning |

### Claude API
- Primary model: `claude-sonnet-4-6` (briefs)
- Max tokens: 1600 (brief synthesis)
- API key: `ANTHROPIC_API_KEY` in `app/.env`

### Egnyte API
- Domain: `avilacapitalllc.egnyte.com`
- Target folder: `/Shared/AREC/Investor Relations/General Fundraising`
- Authentication: Bearer token (`EGNYTE_API_TOKEN` in `app/.env`)
- List folder: `GET /pubapi/v1/fs/{folder_path}`
- Download file: `GET /pubapi/v1/fs-content/{file_path}`

---

## Key Design Patterns

**Markdown-only backend** — All CRM data in markdown files and JSON files. `crm_reader.py` is the single source of truth. `crm_db.py` exists in the codebase (PostgreSQL layer) but is NOT active — do not import from it in new code.

**relationship_brief.py must import from crm_reader** — `collect_relationship_data()` imports all data functions (`get_prospect`, `get_organization`, `get_contacts_for_org`, `load_interactions`, `get_emails_for_org`, `load_prospect_notes`, `load_prospect_meetings`) from `sources.crm_reader`. If these imports ever drift back to `crm_db`, notes/contacts/emails will silently disappear from briefs.

**No authentication** — `g.user` set from `DEV_USER` env var in `dashboard.py` before_request hook. No database, no MSAL.

**Brief synthesis JSON contract** — All Claude calls for briefs expect JSON `{narrative, at_a_glance}`. `brief_synthesizer.py` handles parse fallbacks.

**Notes log flow** — Note saved via `crm_reader.save_prospect_note` → `api_add_prospect_note` returns full `notes_log` → frontend renders immediately → background POST to `/brief` regenerates the brief with note in context.

**Person intelligence pipeline** — Person briefs operate independently. `collect_person_data()` aggregates per-person context, Claude generates person-specific brief.

**Prospect detail page — what's present vs. what's not**
- ✅ Prospect header card (server-rendered: stage, type, primary contact, assigned to, target, last touch, closing)
- ✅ At a Glance strip (from saved brief)
- ✅ Relationship Brief (cached, with Refresh button)
- ✅ Active Tasks (JS-rendered from `/api/tasks`)
- ✅ Interaction History (collapsible, JS-rendered)
- ✅ Meeting Summaries (collapsible, JS-rendered from memory/meetings/)
- ✅ Notes Log (freeform, with add-note form that triggers brief regen)
- ✅ Email History (collapsible, with Deep Scan button)
- ❌ Organization & Contacts card — **removed** (contacts live on org page only)
- ❌ Upcoming Meetings form — **removed** (meetings come from calendar integration)

---

## Tech Stack

| Layer | Stack |
|-------|-------|
| Backend | Python 3, Flask |
| Data | Markdown + JSON files |
| Auth | DEV_USER env var (local only) |
| Frontend | Jinja2, vanilla JS, CSS custom properties (dark theme) |
| Intelligence | Claude API (claude-sonnet-4-6) |

---

## Environment Variables

All variables live in `app/.env`.

| Variable | Purpose |
|----------|---------|
| `DEV_USER` | User email for g.user (default: oscar). No database needed. |
| `ANTHROPIC_API_KEY` | Claude API authentication for brief synthesis |

> Note: `DATABASE_URL` is no longer required. The app uses the markdown backend (`crm_reader.py`) exclusively. `crm_db.py` (PostgreSQL) is in the codebase but inactive.

---

## Naming Conventions

- Specs: `docs/specs/SPEC_[FeatureName].md`
- People profiles: `contacts/[firstname-lastname].md`
- Meeting IDs: UUID v4
- Insight IDs: UUID v4
