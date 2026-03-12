# arec-crm — Architecture

> Load this file when discussing structural or architectural changes.
> Do NOT load for routine task/CRM/briefing work.

**Location:** `~/Dropbox/projects/arec-crm/`

**Last audited:** 2026-03-12 (updated: multi-user auth enforcement, graph_poller)

---

## ⚠️ Development Rules

**ALL work on `azure-migration` branch. NEVER modify `main`.** Push to `azure-migration` auto-deploys via GitHub Actions.

---

## System Overview

arec-crm is a multi-user fundraising CRM platform for the AREC team deployed on Azure. Personal productivity features (tasks, briefings, meetings, memory) were segregated into a separate `overwatch/` project on 2026-03-12.

**Production URL:** https://arec-crm-app.azurewebsites.net/crm

**Core layers:**

1. **Web Dashboard** — Flask app on Azure App Service (port 8000). Full dark theme. CI/CD via GitHub Actions.
2. **PostgreSQL Backend** — Azure Flexible Server. All CRM data in PostgreSQL. No markdown fallback. No `crm_reader.py`.
3. **Multi-User Auth** — Entra ID SSO (MSAL confidential client). Auto-provisioning on first login. Admin/user roles. DEV_USER bypass for local dev.
4. **Email Integration** — Graph API email polling (hourly background job, not yet scheduled), auto-capture, deep scan, two-tier matching.
5. **Intelligence** — Relationship briefs (org + person) via Claude API, cached in PostgreSQL.

---

## Directory Map

```
arec-crm/                        (~/Dropbox/projects/arec-crm/)
├── CLAUDE.md                  ← Project config (run commands, key files, conventions)
├── Makefile                   ← CLI shortcuts
├── config.yaml                ← App configuration (deprecated)
├── crm-inbox.md               ← CRM inbox queue
├── ICON_REFERENCE.md          ← Icon usage reference
├── IMPLEMENTATION_SUMMARY.md  ← Implementation notes (2026-03-12 session)
│
├── docs/                      ← Architecture, decisions, specs
│   ├── ARCHITECTURE.md        ← This file
│   ├── DECISIONS.md           ← Append-only decisions log
│   ├── PROJECT_STATE.md       ← Overwritten after each session
│   └── specs/                 ← SPEC_ files per feature
│
├── app/                       ← Python backend
│   ├── .env                   ← Environment variables (local dev)
│   ├── .env.azure             ← Azure environment template
│   ├── .env.example           ← Template for .env
│   ├── drain_inbox.py         ← Shared mailbox email drain
│   ├── graph_poller.py        ← Multi-user email polling (background job, not yet scheduled)
│   ├── models.py              ← SQLAlchemy ORM models (14 tables, User has graph_consent columns)
│   ├── db.py                  ← Database connection + session management
│   ├── auth/
│   │   ├── graph_auth.py      ← MSAL device flow (local dev only)
│   │   ├── entra_auth.py      ← MSAL confidential client (Azure SSO, auto-provisioning)
│   │   └── decorators.py      ← @require_admin decorator
│   ├── briefing/
│   │   └── brief_synthesizer.py  ← Claude API call + JSON parsing + task extraction
│   ├── sources/
│   │   ├── ms_graph.py        ← Microsoft Graph API wrapper
│   │   ├── crm_db.py          ← PostgreSQL backend (2000+ lines, 45+ functions)
│   │   ├── crm_graph_sync.py  ← Auto-capture email/calendar → CRM interactions
│   │   └── relationship_brief.py  ← Context aggregation for briefs
│   ├── delivery/
│   │   ├── dashboard.py       ← Flask main app
│   │   ├── crm_blueprint.py   ← CRM routes (all 49 require @login_required) + brief synthesis endpoints
│   │   └── admin_blueprint.py ← Admin routes (/admin/users)
│   ├── templates/
│   │   ├── crm_pipeline.html
│   │   ├── crm_prospect_detail.html
│   │   ├── crm_org_edit.html
│   │   ├── crm_people.html
│   │   ├── crm_person_detail.html
│   │   ├── access_denied.html      ← Unauthorized user page
│   │   ├── _contacts_table.html    ← Contacts partial
│   │   ├── _nav.html               ← Navigation partial (includes admin badge)
│   │   └── admin/
│   │       └── users.html          ← Admin user management page
│   ├── static/
│   │   ├── crm.css
│   │   ├── crm.js
│   │   └── icons.js
│   ├── tests/                 ← 99 unit tests (SQLite in-memory, CI green)
│   │   ├── conftest.py        ← Fixtures: seed users, orgs, contacts, prospects
│   │   ├── test_crm_db.py     ← 69 tests for all crm_db.py functions
│   │   ├── test_brief_synthesizer.py  ← 10 tests
│   │   └── test_email_matching.py     ← 20 tests
│   └── requirements.txt
│
├── scripts/
│   ├── create_schema.py           ← Create PostgreSQL schema, seed users
│   ├── migrate_to_postgres.py     ← Parse markdown → insert into Postgres
│   ├── verify_migration.py        ← Validate migration
│   ├── migrate_add_graph_columns.py  ← Add graph_consent_granted, graph_consent_date, scanned_by columns
│   ├── migrate_add_auth_columns.py   ← Add role, display_name, last_login_at columns
│   ├── seed_user.py               ← Add new user to users table
│   └── refresh_interested_briefs.py  ← Bulk brief refresh CLI
│
├── startup.sh                 ← Azure App Service startup script
├── DEPLOYMENT.md              ← Azure deployment guide
│
├── crm/                       ← Legacy markdown files (LOCAL ONLY — not deployed, not used by app)
│   └── *.md                   ← Historical data, read once by migration script
│
└── memory/                    ← Canonical people knowledge base
    └── people/{name}.md       ← Individual profiles (20+ files)
```

---

## Core Data Flows

### Email Auto-Capture (after graph poller runs)
```
Graph API (each user's mailbox)
  → crm_graph_sync.py (two-tier matching: domain → person email)
  → Log interaction to interactions table
  → Email enrichment:
      (a) Add Domain to organizations table if missing
      (b) Append to Email History on person file + org record
      (c) Discover contact emails: match display names, set Email field
  → High-urgency prospect → pending_interviews table
  → Unmatched → unmatched_emails table
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
      9. freeform notes
  → brief_synthesizer.py
      → Claude API (claude-sonnet-4-6, 1600 tokens)
      → Parse JSON {narrative, at_a_glance}
      → Fallback to raw response if parse fails
  → Cache in briefs table
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

### Multi-User Email Polling (background, not yet scheduled)
```
graph_poller.py (executable script: python3 app/graph_poller.py)
  → Query users table WHERE graph_consent_granted = True AND is_active = True
  → For each user:
      → Acquire Graph API token (application permissions)
      → call crm_graph_sync.run_auto_capture(token, user_id=user.id)
      → email_scan_log records get scanned_by = user.id
      → interactions records get created_by = user.id
  → Returns statistics: users_scanned, emails_found, interactions_created, errors
  → Can be scheduled via cron or deployed as Azure Function (timer trigger)
```

---

## External Integrations

| Service | Library | Usage |
|---------|---------|-------|
| Microsoft Graph | `msal`, `requests` | Calendar, email, shared mailbox |
| Claude API | `anthropic` | Brief synthesis, person briefs |
| PostgreSQL | `sqlalchemy`, `psycopg2` | All CRM data storage |
| Entra ID | `msal` | Multi-user SSO (live) |

### Graph API Auth
- MSAL device flow for local dev (single user, cached at `~/.arec_briefing_token_cache.json`)
- MSAL confidential client for Azure (multi-user, application permissions)
- Scopes: `Mail.Read`, `Mail.Read.Shared`, `Calendars.Read`, `User.Read`
- Shared mailbox: `crm@avilacapllc.com`

### Claude API
- Primary model: `claude-sonnet-4-6` (briefs)
- Max tokens: 1600 (brief synthesis)
- API key: `ANTHROPIC_API_KEY` in `app/.env`

---

## Key Design Patterns

**PostgreSQL-only backend** — All CRM data in PostgreSQL. `crm_db.py` is the single source of truth. No markdown fallback. `crm_reader.py` deleted.

**Multi-user attribution** — All interactions, email scans, and auto-captures record the user who triggered them via `created_by` and `scanned_by` foreign keys. Graph consent opt-in via `graph_consent_granted` column.

**Authentication enforcement** — All 49 CRM routes require `@login_required` decorator. Unauthenticated requests redirect to Entra ID login.

**Segregated productivity layer** — Tasks, briefings, meetings, personal memory moved to `~/Dropbox/projects/overwatch/` (separate project). AREC CRM is fundraising-only.

**Two-tier matching** — Email/calendar participants matched to CRM orgs via domain (Tier 1) then person email (Tier 2). Unmatched queued in `unmatched_emails` table.

**Brief synthesis JSON contract** — All Claude calls for briefs expect JSON `{narrative, at_a_glance}`. `brief_synthesizer.py` handles parse fallbacks.

**Auto-link on Primary Contact edit** — When prospect's Primary Contact updated, `ensure_contact_linked()` idempotently creates person file and contact record.

**Idempotent email enrichment** — Every email scan runs three enrichment passes: (a) org domain, (b) email history, (c) contact email discovery. All dedup-safe.

**Person intelligence pipeline** — Person briefs operate independently. `collect_person_data()` aggregates per-person context, Claude generates person-specific brief.

---

## Tech Stack

| Layer | Stack |
|-------|-------|
| Backend | Python 3, Flask, SQLAlchemy |
| Database | PostgreSQL (Azure Flexible Server) |
| Auth | MSAL (confidential client for SSO) |
| Frontend | Jinja2, vanilla JS, CSS custom properties (dark theme) |
| Intelligence | Claude API (claude-sonnet-4-6) |
| Data | PostgreSQL (14 tables) |
| Integrations | Microsoft Graph API |
| Platform | Azure App Service (Gunicorn) |

---

## Environment Variables

All variables live in `app/.env` (local) or Azure Key Vault (production).

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Claude API authentication |
| `AZURE_CLIENT_ID` | Entra ID app registration |
| `AZURE_CLIENT_SECRET` | Client secret for SSO |
| `AZURE_TENANT_ID` | Avila Capital LLC tenant (ebd42ab2-7f1c-4d40-8b44-f5ecc51d2659) |
| `DATABASE_URL` | PostgreSQL connection string |
| `FLASK_SECRET_KEY` | Flask session signing key |
| `DEV_USER` | Local dev only — bypasses OAuth, auto-provisions user |
| `AI_INBOX_EMAIL` | Shared mailbox (`crm@avilacapllc.com`) |

---

## Overwatch Project (Segregated)

**Location:** `~/Dropbox/projects/overwatch/`

**Purpose:** Personal productivity — tasks, meeting summaries, personal memory, calendar integration.

**Key files:**
- `TASKS.md` — Task source of truth
- `app/delivery/dashboard.py` — Dashboard (port 3001)
- `app/delivery/tasks_blueprint.py` — Task CRUD routes
- `meeting-summaries/` — Meeting summary markdown files
- `memory/` — Personal context, project notes, glossary

**Independence:** Zero imports from arec-crm. Shared modules (graph_auth, ms_graph) copied.

---

## Migration Notes

### PostgreSQL Schema
14 tables: `users`, `organizations`, `contacts`, `prospects`, `interactions`, `email_scan_log`, `briefs`, `prospect_notes`, `unmatched_emails`, `pending_interviews`, `offerings`, `pipeline_stages`, `prospect_tasks`, `urgency_levels`.

### Migration Workflow
1. `create_schema.py` — Drop/create tables, seed stages + users
2. `migrate_to_postgres.py` — Parse markdown → insert
3. `verify_migration.py` — Count validation + spot checks
4. `migrate_add_graph_columns.py` — Add graph consent columns

### What Stays Local (not deployed to Azure)
- `memory/people/*.md` — Canonical people intelligence files (referenced by brief synthesis)
- `crm/*.md` — Legacy markdown data files. Not used by app. Historical/backup only.
- `crm/meeting_history.md` — Meeting records (not migrated to Postgres)

---

## Naming Conventions

- Specs: `docs/specs/SPEC_[FeatureName].md`
- People profiles: `memory/people/[firstname-lastname].md`
- Migration scripts: `scripts/migrate_*.py`
