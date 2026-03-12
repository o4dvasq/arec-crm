# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-12 — Multi-user enforcement complete: @login_required on all routes, graph_poller background system, access control ready

---

## What's Built and Working

### AREC CRM — Multi-User Fundraising Platform (PRODUCTION)
- **Production URL**: https://arec-crm-app.azurewebsites.net/crm
- **Backend**: PostgreSQL-only (`crm_db.py`). All 45+ functions operational. No markdown fallback.
- **Database**: Azure PostgreSQL Flexible Server (`arec-crm-db`, centralus, Burstable B1ms)
- **Local Database**: PostgreSQL 14 on localhost for dev (`postgresql://localhost/arec_crm`)
- **Schema**: 14 tables with all relationships and foreign keys
- **Authentication**: Entra ID SSO (MSAL confidential client). Auto-provisioning on first login. DEV_USER bypass for local dev. **All CRM routes now require authentication** (`@login_required` on 49 routes).
- **User Management**: Admin page at `/admin/users` with role management. oscar@avilacapllc.com auto-promoted to admin.
- **CI/CD**: GitHub Actions — push to `azure-migration` → 99 tests → auto-deploy to Azure
- **CRM Features**: Pipeline, prospect detail, org management, relationship briefs, contact intelligence, interaction history
- **Brief Synthesis**: Relationship briefs (org + person) via Claude API, cached in PostgreSQL
- **Email Integration**: Graph API poller ready (`graph_poller.py` multi-user support), auto-capture, two-tier matching
- **Multi-User Email Polling**: `graph_poller.py` iterates over users with `graph_consent_granted=True`, acquires tokens, calls `run_auto_capture(user_id)`, records `scanned_by` attribution
- **Access Control**: Unapprovisioned users see access_denied.html page
- **Dark Theme**: Full dark theme throughout
- **User Menu**: Navigation shows logged-in user display name, admin badge, logout link

### Overwatch — Personal Productivity Platform (LOCAL ONLY)
- **Location**: `~/Dropbox/projects/overwatch/`
- **Port**: 3001 (local-only, single-user, no Azure deployment)
- **Features**: Task management (TASKS.md), meeting summaries, personal memory, calendar integration
- **Independence**: Zero imports from arec-crm

---

## What Was Just Completed (March 12, 2026)

1. **Multi-user authentication enforcement** — Added `@login_required` decorator to all 49 CRM routes. All pages and API endpoints now require Entra ID SSO authentication.
2. **Multi-user email polling system** — Created `app/graph_poller.py` for background email scanning with per-user attribution via `scanned_by` FK.
3. **Graph consent columns** — Added `graph_consent_granted` (Boolean) and `graph_consent_date` (TIMESTAMP) to User model. Created migration script `migrate_add_graph_columns.py`.
4. **Access control** — Created `access_denied.html` template for unapprovisioned users (though auto-provisioning is currently enabled).
5. **User menu in navigation** — `_nav.html` already displays logged-in user display name, admin badge for admins, and logout link (verified working).

---

## Active Branch: `azure-migration`

**⚠️ ALL WORK HAPPENS ON `azure-migration`. DO NOT USE `main`.**

`main` branch has stale markdown-based code from before the migration. It should not be modified until a deliberate merge is done.

**Development workflow:**
1. `git checkout azure-migration`
2. Make changes
3. `python -m pytest app/tests/ -v --tb=short`
4. Commit and push → CI auto-deploys to Azure
5. Verify at https://arec-crm-app.azurewebsites.net/crm

---

## Known Issues

- **Graph API polling not scheduled** — `graph_poller.py` exists but no Azure Function or cron job set up yet
- **Auto-provisioning still enabled** — All `@avilacapllc.com` users auto-created on first login. Access denied page only applies if auto-provisioning is disabled.
- **`merge_organizations()` not implemented** — Returns NotImplementedError (stub only)
- **57 orphaned contacts / 54 orphaned prospects** — Pre-existing data quality issues in markdown source, not migration bugs
- **`main` branch is stale** — Contains old markdown-based code. Needs merge from `azure-migration` when ready

---

## Next Up

1. **Run graph column migration** — Execute `python3 scripts/migrate_add_graph_columns.py` on Azure database
2. **Schedule `graph_poller.py`** — Deploy as Azure Function or container job for hourly email polling
3. **Test multi-user email attribution** — Set `graph_consent_granted=True` for test users, verify `scanned_by` records
4. **Implement `merge_organizations()`** — Currently a stub (SPEC_merge-orgs.md ready)
5. **Merge `azure-migration` → `main`** — When confident production is stable
6. **Feature specs ready for implementation** (see docs/specs/):
   - SPEC_calendar-forward-scan.md — Auto-discovered prospect meetings
   - SPEC_org-aliases.md — Organization AKA names

---

## Deferred / Parked

- `arec-mobile/` PWA — functional, not actively iterated
- Phase I2-I5 features (Intelligence pipeline enhancements, Intelligence UI, Briefing engine, Meeting transcript processing)
- Morning briefing removed entirely (moved to Overwatch, deprecated)
- Data cleanup for orphaned contacts/prospects
