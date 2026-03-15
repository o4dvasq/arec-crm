# arec-crm — Architecture

> Load this file when discussing structural or architectural changes.
> Do NOT load for routine task/CRM/briefing work.

**Location:** `~/Dropbox/projects/arec-crm/`
*(Migrated from `~/Dropbox/Tech/ClaudeProductivity/` on 2026-03-10)*

**Last audited:** 2026-03-14 (postgres-local branch — memory/ → contacts/ rename)

---

## System Overview

arec-crm is a personal productivity and CRM system built around Claude Code. It has four functional layers:

1. **Briefing Pipeline** — Scheduled daily briefing from Outlook + tasks + memory via Claude API
2. **Web Dashboard** — Flask app (port 3001) for CRM, tasks, and relationship brief synthesis. Full dark theme (CSS custom properties). Prospect detail has click-to-edit fields and inline task/brief rendering.
3. **Person Intelligence** — Person-level briefs, AI-routed CRM updates from free-text, and person intel management
4. **Skills Layer** — Instructional Claude guides for meeting debrief and email log scanning

---

## Directory Map

```
arec-crm/                        (~/Dropbox/projects/arec-crm/)
├── CLAUDE.md                  ← Project config (run commands, key files, conventions)
├── TASKS.md                   ← Single source of truth for tasks
├── Makefile                   ← CLI shortcuts (make dashboard, make briefing, etc.)
├── config.yaml                ← App configuration (graph.user_email)
├── inbox.md                   ← Voice-capture queue (iPhone Shortcuts, ephemeral)
├── briefing_latest.md         ← Most recent generated briefing (regenerated daily)
├── dashboard_calendar.json    ← Today's (+ tomorrow's after 3 PM) calendar for web dashboard
├── update.md                  ← Update log
├── crm-inbox.md               ← CRM inbox queue
├── crm-interview.md           ← Interview queue
├── crm-review.md              ← Review queue
├── ICON_REFERENCE.md          ← Icon usage reference
├── ICON_STANDARDIZATION.md    ← Icon standardization guide
├── IMPLEMENTATION_SUMMARY.md  ← Implementation notes
├── SHORTCUT-SETUP.md          ← iPhone Shortcuts setup guide
│
├── docs/                      ← Architecture, decisions, specs
│   ├── ARCHITECTURE.md        ← This file; load on demand
│   ├── DECISIONS.md           ← Append-only decisions log
│   ├── PROJECT_STATE.md       ← Overwritten after each session
│   └── specs/                 ← SPEC_ files per feature; archive/ for completed ones
│       ├── azure-platform/    ← Azure migration architecture + phase specs
│       └── migration/         ← Migration prerequisites and inventory
│
├── app/                       ← Python backend (all paths resolved from __file__, no hardcoded paths)
│   ├── .env                   ← Environment variables (local dev, see Environment Variables section)
│   ├── .env.azure             ← Azure environment template (DATABASE_URL, AZURE_CLIENT_ID, etc.)
│   ├── .env.example           ← Template for .env
│   ├── main.py                ← Morning briefing orchestrator
│   ├── drain_inbox.py         ← Shared mailbox email drain
│   ├── models.py              ← SQLAlchemy ORM models (14 tables)
│   ├── db.py                  ← Database connection + session management
│   ├── auth/
│   │   ├── decorators.py      ← Flask auth decorators (require_api_key_or_login)
│   │   ├── graph_auth.py      ← MSAL device flow authentication (local briefing)
│   │   └── entra_auth.py      ← MSAL confidential client (Azure SSO for web app)
│   ├── briefing/
│   │   ├── generator.py       ← Claude API call wrapper (claude-sonnet-4-6, 1500 tokens)
│   │   ├── prompt_builder.py  ← Briefing prompt assembly
│   │   └── brief_synthesizer.py  ← Shared Claude call + JSON parsing + task extraction
│   ├── sources/
│   │   ├── ms_graph.py        ← Microsoft Graph API wrapper (10 public functions)
│   │   ├── memory_reader.py   ← Load TASKS.md, CLAUDE.md, inbox.md; task CRUD helpers
│   │   ├── crm_reader.py      ← Central CRM parser (markdown backend, 1839 lines)
│   │   ├── crm_db.py          ← PostgreSQL backend (SQLAlchemy, 2000 lines, drop-in for crm_reader.py)
│   │   ├── crm_graph_sync.py  ← Auto-capture email/calendar → CRM interactions
│   │   └── relationship_brief.py  ← Context aggregation for org + person brief synthesis
│   ├── delivery/
│   │   ├── dashboard.py       ← Flask main app (DASHBOARD_PORT, FLASK_DEBUG env vars)
│   │   ├── crm_blueprint.py   ← CRM routes + brief synthesis endpoints (~69KB)
│   │   └── tasks_blueprint.py ← Task management routes (4 sections + Done)
│   ├── templates/
│   │   ├── dashboard.html
│   │   ├── crm_pipeline.html
│   │   ├── crm_prospect_detail.html
│   │   ├── crm_prospect_edit.html
│   │   ├── crm_orgs.html
│   │   ├── crm_org_detail.html
│   │   ├── crm_org_edit.html
│   │   ├── crm_people.html
│   │   ├── crm_person_detail.html
│   │   ├── crm_tasks.html         ← Standalone all-tasks page (/crm/tasks)
│   │   ├── _contacts_table.html   ← Contacts partial (included in org/prospect detail)
│   │   ├── _nav.html              ← Navigation partial
│   │   ├── meeting_detail.html
│   │   └── tasks/
│   │       └── tasks.html
│   ├── static/
│   │   ├── crm.css
│   │   ├── crm.js
│   │   ├── icons.js               ← Icon definitions for dashboard
│   │   ├── task-edit-modal.css
│   │   ├── task-edit-modal.js
│   │   └── tasks/
│   │       ├── tasks.css
│   │       └── tasks.js
│   ├── tests/                 ← 128 unit tests across 6 files
│   │   ├── conftest.py                     ← SQLite in-memory fixtures (db_engine, db_session, sample_*)
│   │   ├── test_crm_db.py                  (52 tests — full postgres backend coverage)
│   │   ├── test_tasks_api_key.py           (24 tests — API key auth on all 5 task endpoints)
│   │   ├── test_brief_synthesizer.py       (10 tests)
│   │   ├── test_email_matching.py          (20 tests)
│   │   └── test_task_parsing.py            (22 tests)
│   └── requirements.txt
│
├── scripts/
│   ├── seed_from_markdown.py  ← Seed Postgres from all markdown/JSON files (idempotent)
│   ├── create_schema.py       ← Create PostgreSQL schema, seed stages + users
│   ├── migrate_to_postgres.py ← Parse markdown files → insert into Postgres (old migration)
│   ├── verify_migration.py    ← Validate migration (count checks + spot checks)
│   └── refresh_interested_briefs.py  ← Bulk brief refresh CLI (Stage 5 prospects)
│
├── requirements.txt           ← Repo-root copy of app/requirements.txt — required for Oryx to populate antenv
├── startup.sh                 ← Azure App Service startup script (Gunicorn)
├── DEPLOYMENT.md              ← Azure deployment guide (local testing + production deploy)
│
├── crm/                       ← CRM data (markdown + JSON)
│   ├── prospects.md           ← Prospect records
│   ├── organizations.md       ← Organization registry
│   ├── contacts_index.md      ← Contact name → org mapping (lookup table)
│   ├── interactions.md        ← Interaction log
│   ├── meeting_history.md     ← Meeting records (merged from memory/meetings.md)
│   ├── org-locations.md       ← Org location data (moved from memory/)
│   ├── config.md              ← Pipeline stages, org types, team roster
│   ├── offerings.md           ← Deal targets
│   ├── briefs.json            ← Cached relationship briefs
│   ├── email_log.json         ← Scanned email metadata + summaries
│   ├── prospect_notes.json    ← Freeform notes per org/offering
│   ├── unmatched_review.json  ← Emails that couldn't be matched to orgs
│   └── pending_interviews.json ← High-urgency prospects to debrief
│
├── contacts/                  ← Contact profile files (formerly memory/people/)
│   └── {name}.md              ← Individual profiles, ~211 files, flat directory
│
├── projects/                  ← Project notes
│   └── arec-fund-ii.md        ← (moved from memory/projects/)
│
├── meeting-summaries/         ← Generated meeting notes (YYYY-MM-DD-slug.md)
│   └── archive/               ← Meetings older than 7 days
│
├── skills/                    ← Claude instructional guides (not executable Python)
│   ├── meeting-debrief.md     ← Calendar gap detection + debrief quiz
│   └── email-scan.md          ← Email log update (Oscar + Tony delegate)
│
└── arec-mobile/               ← Mobile PWA (reads/writes via Dropbox API)
    └── arec-mobile.html       ← Single-file PWA (Dropbox paths: /projects/arec-crm/)
```

---

## Core Data Flows

### Morning Briefing (5 AM, launchd)
```
Outlook Calendar + Email (Archive)
  → app/auth/graph_auth.py (MSAL device flow)
  → app/sources/ms_graph.py (calendar events, last 18h emails)
  → app/sources/memory_reader.py (TASKS.md, CLAUDE.md, inbox.md)
  → app/briefing/prompt_builder.py (builds system + user prompt)
  → app/briefing/generator.py (Claude API, claude-sonnet-4-6, 1500 tokens)
  → briefing_latest.md (YAML frontmatter + content)
  → dashboard_calendar.json (includes tomorrow's events if after 3 PM PT or <2 today)
  → app/sources/crm_graph_sync.py (auto-capture interactions)
```

### Email Inbox Drain (manual)
```
crm@avilacapllc.com shared mailbox (unread)
  → app/drain_inbox.py (env: AI_INBOX_EMAIL, default: crm@avilacapllc.com)
  → Parse forwarded emails (intent note + original)
  → inbox.md ([AI Inbox] entries)
  → Mark as read + move to "Processed" folder
```

### Auto-Capture (after briefing)
```
Outlook emails + calendar events (last 24h)
  → Two-tier matching:
      Tier 1: Domain fuzzy match → org (95% confidence)
      Tier 2: Person email lookup in contacts/ → org (90% confidence)
  → Log interaction to crm/interactions.md
  → Email enrichment (runs on every matched email):
      (a) Add Domain to org in organizations.md if missing
      (b) Append Email History to contacts/ person file + org record
      (c) Discover contact emails: match display names to contacts, set Email field
  → High-urgency prospect → crm/pending_interviews.json
  → Unmatched → crm/unmatched_review.json
  → Internal domains skipped: avilacapllc.com, avilacapital.com, builderadvisorgroup.com
```

### Relationship Brief Synthesis (dashboard, on demand)
```
User clicks "Refresh Brief" on prospect detail page
  → Aggregate context from 9 sources:
      1. prospect record          2. org record
      3. contacts + people intel  4. interaction history
      5. glossary entry           6. meeting summaries
      7. active tasks             8. email history
      9. freeform notes log (prospect_notes.json)
  → app/briefing/brief_synthesizer.py
      → Claude API (claude-sonnet-4-6, 1600 tokens)
      → Parse JSON {narrative, at_a_glance}
      → Fallback to raw response if parse fails
  → Cache in crm/briefs.json
  → Display on prospect card
```

### Person Brief Synthesis (dashboard, on demand)
```
User clicks "Refresh Brief" on person detail page
  → app/sources/relationship_brief.py
  → collect_person_data(): contacts, org record, people intel files,
      interactions, meeting summaries, email history
  → build_person_context_block(): structured text for AI
  → Claude API (claude-sonnet-4-6) with PERSON_BRIEF_SYSTEM_PROMPT
  → Parse JSON {narrative, at_a_glance}
```

### Person Update Routing (dashboard, on demand)
```
User submits free-text update about a person
  → PERSON_UPDATE_ROUTING_PROMPT → Claude determines which stores to update
  → execute_person_updates(): routes to person file, org record, tasks, interactions
  → append_person_intel(): add notes to person file
```

### Task Extraction from Meeting Notes
```
Meeting notes text
  → brief_synthesizer.py → extract_tasks_from_notes()
  → Claude API (claude-sonnet-4-20250514, 800 tokens)
  → TASK_EXTRACTION_SYSTEM_PROMPT → returns JSON array of tasks
```

### Post-Update Extensions (after /productivity:update)
```
Extension 1: skills/meeting-debrief.md
  → Outlook calendar → filter meaningful meetings
  → Cross-reference Notion + meeting-summaries/
  → Debrief gap meetings → meeting-summaries/YYYY-MM-DD-slug.md
  → Offer to add action items to TASKS.md

Extension 2: skills/email-scan.md
  → Pass 1: Oscar's Archive (last 14 days)
  → Pass 2: Oscar's Sent Items (last 14 days)
  → Pass 3: Tony's received mail (delegate access)
  → Pass 4: Tony's sent mail (delegate access)
  → Pass 5: CRM shared mailbox
  → Two-tier domain + person matching
  → Enrich matched emails with summaries + Outlook web URLs
  → Append to crm/email_log.json (dedup by messageId)
  → Email enrichment pass (Step 6.5):
      (a) Set org Domain from sender email if missing
      (b) Append Email History to contacts/ person files + org records
      (c) Discover and set contact emails from domain matching
```

---

## External Integrations

| Service | Library | Usage |
|---------|---------|-------|
| Microsoft Graph | `msal`, `requests` | Calendar, email, shared mailbox, Teams chat |
| Claude API | `anthropic` | Briefing generation, brief synthesis, person briefs, task extraction |
| Notion | MCP (claude_ai_Notion) | Meeting notes (read only) |
| Microsoft 365 | MCP (claude_ai_Microsoft_365) | Calendar + email via skills |

### Graph API Auth
- MSAL device flow on first run; token cached at `~/.arec_briefing_token_cache.json`
- Uses `acquire_token_silent_with_error` — surfaces real Azure AD errors (e.g., AADSTS50173 grant revoked)
- On `invalid_grant` / `interaction_required`, cache auto-deleted so next `python app/main.py` triggers clean device flow
- Scopes: `Mail.Read`, `Mail.Read.Shared`, `Calendars.Read`, `Chat.Read`, `User.Read`
- Shared mailbox access: `crm@avilacapllc.com`; delegate mailbox: `tony@avilacapllc.com`

### Graph API Functions (ms_graph.py)
| Function | Purpose |
|----------|---------|
| `get_today_events` | Today's calendar events |
| `get_tomorrow_events` | Tomorrow's calendar events |
| `get_events_range` | Calendar events in arbitrary date range |
| `get_recent_emails` | Recent emails from Archive folder (last N hours) |
| `get_shared_mailbox_messages` | Unread messages from shared mailbox |
| `get_folder_messages` | Messages from a specific folder (optional mailbox) |
| `mark_as_read` | Mark shared mailbox message as read |
| `move_message` | Move message to destination folder |
| `search_emails_deep` | Deep email search with keyword + date range + folder targeting |
| `get_recent_chats` | Recent Teams chat messages (last N hours) |

### Claude API
- Primary model: `claude-sonnet-4-6` (briefing, org briefs, person briefs)
- Legacy model: `claude-sonnet-4-20250514` (task extraction from meeting notes only)
- Max tokens: 1500 (briefing), 1600 (brief synthesis), 800 (task extraction)
- API key: `ANTHROPIC_API_KEY` in `app/.env`

---

## Key Design Patterns

**Dual backend architecture** — CRM data runs on markdown (`crm_reader.py`) on `deprecated-markdown` branch, OR PostgreSQL (`crm_db.py`) on `postgres-local` / `azure-migration` branches. Both expose identical function signatures. Import swap controlled in blueprints. `crm_reader.py` is preserved as source for `seed_from_markdown.py` and reference.

**Centralized CRM data access** — `crm_reader.py` (markdown) or `crm_db.py` (Postgres) is the only place CRM data is read/written. All other modules import from one or the other. Drop-in replacement: same 45+ function signatures. Includes email enrichment helpers (`enrich_org_domain`, `append_person_email_history`, `append_org_email_history`, `discover_and_enrich_contact_emails`) and contact auto-linking (`ensure_contact_linked`).

**Skills are instructional** — `meeting-debrief.md` and `email-scan.md` are step-by-step guides Claude executes using MCP tools (MS Graph, Notion). They are not Python scripts.

**Two-tier matching** — Email/calendar participants matched to CRM orgs via domain (Tier 1) then person email lookup in `contacts/` (Tier 2). Unmatched queued for manual review.

**Brief synthesis JSON contract** — All Claude calls for briefs use a JSON suffix. `brief_synthesizer.py` handles parse fallbacks (markdown-fenced JSON, plain fenced JSON, raw text). Frontend `loadBrief()` also auto-detects JSON strings stored in the `relationship_brief` field and parses out `narrative` / `at_a_glance`.

**Auto-link on Primary Contact edit** — When a prospect's Primary Contact field is updated via the PATCH API, `ensure_contact_linked()` idempotently creates a person file and contacts_index entry linking the contact to the org.

**Non-invasive auto-capture** — Logs interactions but never modifies source calendar or email data.

**Idempotent email enrichment** — Every email scan (daily incremental, Deep Scan, auto-capture) runs the same three enrichment passes: (a) org domain, (b) email history, (c) contact email discovery. All operations are dedup-safe and skip-if-already-set, so running them repeatedly is harmless.

**API key + session auth** — `@require_api_key_or_login` in `app/auth/decorators.py` accepts either a valid `X-API-Key` header (when `OVERWATCH_API_KEY` is set) or a `g.user` session (set by `before_request` from `session['user']` or `DEV_USER` env var). When `OVERWATCH_API_KEY` is unset, API key path is disabled entirely. Applied to all 5 task API routes.

**Task sections** — TASKS.md is organized into four active sections plus Done: Fundraising - Me, Fundraising - Others, Other Work, Personal. `tasks_blueprint.py` enforces this structure.

**Person intelligence pipeline** — Person briefs operate independently from org briefs. `collect_person_data()` aggregates per-person context, `build_person_context_block()` formats it, and Claude generates a person-specific `{narrative, at_a_glance}`. Free-text updates are routed by Claude via `PERSON_UPDATE_ROUTING_PROMPT` to the correct data stores.

---

## Tech Stack

| Layer | Stack |
|-------|-------|
| Backend | Python 3, Flask, SQLAlchemy |
| Database | PostgreSQL (Azure) OR Markdown (local) |
| Auth | MSAL (device flow for local briefing, confidential client for Azure SSO) |
| Frontend | Jinja2, vanilla JS, CSS custom properties (dark theme) |
| Intelligence | Claude API (claude-sonnet-4-6, claude-sonnet-4-20250514) |
| Data | PostgreSQL (14 tables) OR Markdown files + JSON caches |
| Integrations | Microsoft Graph API, Notion MCP, MS365 MCP |
| Platform | macOS (local, launchd, ~/Library/Logs) OR Azure (App Service, Gunicorn) |

---

## Environment Variables

All variables live in `app/.env`. No other env file is loaded.

| Variable | Current Value | Purpose |
|----------|---------------|---------|
| `ANTHROPIC_API_KEY` | `sk-ant-api03-...` | Claude API authentication |
| `AZURE_CLIENT_ID` | `d58c6152-...` | Entra ID app registration (personal tenant, local) OR app ID for SSO (Azure) |
| `AZURE_CLIENT_SECRET` | (Key Vault) | Client secret for SSO (Azure only) |
| `AZURE_TENANT_ID` | `064d6342-5dc5-424e-802f-53ff17bc02be` | Avila Capital LLC tenant |
| `MS_USER_ID` | `422b3092-...` | Oscar's Graph API user ID (delegated flow, local only) |
| `AI_INBOX_EMAIL` | `crm@avilacapllc.com` | Shared mailbox for AI inbox drain |
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection string (Azure only) |
| `FLASK_SECRET_KEY` | `dev-secret-key-...` | Flask session signing key (set in `.env`; required for session auth) |
| `OVERWATCH_API_KEY` | `overwatch-dev-key` | Shared secret for Overwatch machine-to-machine task API |
| `DEV_USER` | `oscar@avilacapllc.com` | Local dev auth bypass — auto-populates `g.user` on every request |

Dashboard env vars (read at runtime, not in `.env`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `DASHBOARD_PORT` | `3001` | Flask dashboard port |
| `FLASK_DEBUG` | `true` | Flask debug mode |

### Config File: config.yaml
```yaml
graph:
  user_email: "oscar@avilacapllc.com"
```

### Hardcoded Paths (macOS-specific)
| Path | File | Purpose |
|------|------|---------|
| `~/Library/Logs/arec-morning-briefing.log` | `main.py` | Briefing log output |
| `~/.arec_briefing_token_cache.json` | `graph_auth.py` | MSAL token cache |

### Internal Domain Allow List
Defined in `crm_graph_sync.py`, skipped during auto-capture matching:
- `avilacapllc.com`
- `avilacapital.com`
- `builderadvisorgroup.com`

---

## Azure Migration Notes

> See `docs/specs/azure-platform/ARCHITECTURE.md` for the full Azure migration architecture.
> See `docs/specs/migration/PREREQUISITES.md` for the detailed migration inventory.

### Oryx Build Behavior (Critical)

Azure App Service uses **Oryx** to build the Python environment during deployment:
- Oryx scans for `requirements.txt` at the **repo root** to create/populate `antenv`
- Gunicorn's PYTHONPATH is set to `antenv/lib/python3.12/site-packages` by Oryx at startup
- If `requirements.txt` is missing from the root, Oryx builds an empty `antenv` → app crashes with `ModuleNotFoundError` on every worker
- `startup.sh` pip install is a safety net (runs after Oryx), but installs to the Oryx-managed antenv only if it's activated first
- **Rule:** `requirements.txt` must exist at repo root. Keep it in sync with `app/requirements.txt`.

### What Changes for Azure

**Secrets → Azure Key Vault:**
- `ANTHROPIC_API_KEY` — move to Key Vault
- `AI_INBOX_EMAIL` — move to Key Vault
- Graph API credentials — replaced by managed identity

**Tenant change:**
- `AZURE_TENANT_ID`: stays `ebd42ab2-7f1c-4d40-8b44-f5ecc51d2659` (this IS the Avila Capital LLC tenant; subscription ID is `064d6342-5dc5-424e-802f-53ff17bc02be`)
- `AZURE_CLIENT_ID`: New app registration required in Avila Capital LLC tenant
- `MS_USER_ID`: Removed — application-level permissions replace delegated user flow (supports 8 team members)

**Auth model change:**
- Current: MSAL device flow (delegated, single user)
- Target: Application-level permissions with admin consent (multi-user)
- Token cache (`~/.arec_briefing_token_cache.json`): Replaced by managed identity or distributed cache
- Graph scopes shift from delegated (`Mail.Read`) to application (`Mail.Read` app-level)

**Data layer:**
- All `crm/*.md` files → PostgreSQL on Azure Flexible Server
- `crm_reader.py` → `crm_db.py` (same function signatures, SQL backend)
- JSON caches (`briefs.json`, `email_log.json`, etc.) → PostgreSQL tables
- `contacts/` profile files → PostgreSQL or Azure Blob Storage

**Platform dependencies:**
- `~/Library/Logs/` (macOS) → Azure App Service logging / Application Insights
- `launchd` scheduling → Azure Functions timer triggers
- `config.yaml` `graph.user_email` → must support multiple users
- `DASHBOARD_PORT` / `FLASK_DEBUG` → Azure App Service manages ports; debug must be false

**New environment variables needed:**
- `DATABASE_URL` — PostgreSQL connection string
- `AZURE_KEY_VAULT_URL` — Key Vault endpoint
- Email delivery service config (SendGrid or Azure Communication Services)
- `WEBSITE_PORT` — Azure App Service convention (replaces `DASHBOARD_PORT`)

**Stale code references to clean up:**
- `prompt_builder.py` variable `PRODUCTIVITY_ROOT` (leftover from ClaudeProductivity era)

---

## Naming Conventions

- Meeting summaries: `meeting-summaries/YYYY-MM-DD-title-slug.md`
- Specs: `docs/specs/SPEC_[FeatureName].md`
- People profiles: `contacts/[firstname-lastname].md`
- Migration scripts: `app/scripts/` (historical, not actively run)
- Project notes: `projects/[slug].md`
