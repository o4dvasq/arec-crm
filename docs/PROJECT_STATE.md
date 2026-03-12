# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-12 — Local PostgreSQL setup complete, database fully initialized and functional

---

## What's Built and Working

### AREC CRM — Multi-User Fundraising Platform
- **Backend**: PostgreSQL-only (`crm_db.py`). All 45+ functions operational.
- **Local Database**: PostgreSQL 14.22 running on `localhost/arec_crm`
- **Schema**: 14 tables created with all relationships and foreign keys
- **Seeded Data**: 8 team members, 9 pipeline stages
- **Graph Columns**: `graph_consent_granted`, `graph_consent_date`, `scanned_by` added
- **Root route**: Redirects to `/crm` (pipeline view). No dashboard home page.
- **CRM Features**: Pipeline, prospect detail, org management, relationship briefs, contact intelligence, interaction history
- **Brief Synthesis**: Relationship briefs (org-level + person-level) via Claude API, cached in PostgreSQL
- **Email Integration**: Deep Email Scan, auto-capture, two-tier matching ready (needs data)
- **Dark Theme**: Full dark theme throughout (CSS custom properties)
- **Multi-User Infrastructure**: Migration scripts, user seeding, graph poller, access denied page
- **Testing**: Dashboard imports successfully, routes return 200/302, templates render correctly

### Overwatch — Personal Productivity Platform
- **Location**: `~/Dropbox/projects/overwatch/`
- **Port**: 3001 (local-only, single-user)
- **Status**: Fully functional, tested end-to-end
- **Features**: Task management (TASKS.md), meeting summaries, personal memory, calendar integration
- **Components**: Dashboard (tasks + calendar + meetings), tasks blueprint, calendar refresh API, meeting detail pages
- **Templates**: dashboard.html, meeting_detail.html, _nav.html, tasks/tasks.html
- **Static Assets**: All CSS/JS copied from arec-crm (crm.css, crm.js, task-edit-modal.*)
- **Testing**: HTTP 200 on all routes, templates render correctly, static assets served

### Intelligence Pipeline
- **Auto-capture**: Email/calendar → CRM interactions (two-tier matching: domain then person email)
- **Email Enrichment**: Domain discovery, email history append, contact email enrichment
- **Unmatched Queue**: `unmatched_emails` table for manual review
- **Brief Synthesis**: `brief_synthesizer.py` handles all Claude calls (prospect + org + person)

### Data Layer
- **PostgreSQL Tables**: 14 tables fully created and initialized
- **Migration Scripts**: All scripts functional with local database support
- **People Knowledge Base**: `memory/people/*.md` files preserved (canonical contact intel)

### Testing
- 52 tests in arec-crm (need PostgreSQL fixtures)
- Overwatch dashboard: End-to-end HTTP tests passed
- AREC CRM: Import tests passed, HTTP routes functional

---

## What Was Just Completed

**Local PostgreSQL Setup + Database Initialization** (2026-03-12)
- **Installed PostgreSQL 14.22** via Homebrew, configured to start on login
- **Created arec_crm database** on localhost
- **Fixed schema scripts** to use local `.env` instead of `.env.azure`
- **Ran schema creation** — 14 tables created, 8 users seeded, 9 pipeline stages seeded
- **Ran graph columns migration** — Added `graph_consent_granted`, `graph_consent_date` to users; `scanned_by` to email_scan_log
- **Updated .env** — Added `DATABASE_URL=postgresql://localhost/arec_crm` and Flask config vars
- **Tested dashboard** — All routes functional, pipeline renders successfully (80KB response)

---

## Known Issues

- **No CRM data yet** — Database schema exists but empty (no prospects, orgs, contacts). Run `migrate_to_postgres.py` to import from markdown files if needed.
- **SSO not implemented** — `@login_required` decorators need to be added to all CRM routes
- **Tests need PostgreSQL fixtures** — Existing 52 tests use markdown fixtures
- **merge_organizations() not implemented** — Returns NotImplementedError
- **Pipeline Assigned To filter** — Frontend dropdown not yet built (backend supports it)
- **Graph API polling** — `graph_poller.py` exists but not scheduled (needs cron or Azure Function)

---

## Next Up

1. **Import existing CRM data** (optional): `python3 scripts/migrate_to_postgres.py` if you have markdown files to import
2. **Test locally**: Run `python3 app/delivery/dashboard.py` and visit http://localhost:8000
3. **Add SSO enforcement** — Apply `@login_required` to all CRM blueprint routes
4. **Update tests** — Rewrite test suite with PostgreSQL fixtures
5. **Add real Entra IDs** — Update placeholder user IDs with real ones from Azure
6. **Deploy to Azure** — Update GitHub Actions, configure App Service
7. **Schedule graph_poller** — Set up hourly email polling

---

## Open Design Questions

<!-- None at this time -->

---

## Deferred / Parked

- `arec-mobile/` PWA — functional, not actively iterated
- Phase I2-I5 features (Intelligence pipeline enhancements, Intelligence UI, Briefing engine, Meeting transcript processing)
- Morning briefing removed entirely (moved to Overwatch, not scheduled)
