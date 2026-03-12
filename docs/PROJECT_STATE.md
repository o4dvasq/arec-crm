# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-12 — EasyAuth SSO & user management implemented, admin page live, auto-provisioning active

---

## What's Built and Working

### AREC CRM — Multi-User Fundraising Platform (PRODUCTION)
- **Production URL**: https://arec-crm-app.azurewebsites.net/crm
- **Backend**: PostgreSQL-only (`crm_db.py`). All 45+ functions operational. No markdown fallback.
- **Database**: Azure PostgreSQL Flexible Server (`arec-crm-db`, centralus, Burstable B1ms)
- **Local Database**: PostgreSQL 14 on localhost for dev (`postgresql://localhost/arec_crm`)
- **Schema**: 14 tables with all relationships and foreign keys
- **Authentication**: Entra ID SSO (MSAL confidential client). Auto-provisioning on first login. DEV_USER bypass for local dev.
- **User Management**: Admin page at `/admin/users` with role management. oscar@avilacapllc.com auto-promoted to admin.
- **CI/CD**: GitHub Actions — push to `azure-migration` → 99 tests → auto-deploy to Azure
- **CRM Features**: Pipeline, prospect detail, org management, relationship briefs, contact intelligence, interaction history
- **Brief Synthesis**: Relationship briefs (org + person) via Claude API, cached in PostgreSQL
- **Email Integration**: Graph API poller ready (not yet scheduled), auto-capture, two-tier matching
- **Dark Theme**: Full dark theme throughout
- **Multi-User**: 8 team members seeded, graph consent columns, user attribution on all interactions

### Overwatch — Personal Productivity Platform (LOCAL ONLY)
- **Location**: `~/Dropbox/projects/overwatch/`
- **Port**: 3001 (local-only, single-user, no Azure deployment)
- **Features**: Task management (TASKS.md), meeting summaries, personal memory, calendar integration
- **Independence**: Zero imports from arec-crm

---

## What Was Just Completed (March 12, 2026)

1. **EasyAuth SSO & User Management** — Auto-provisioning on first login, admin/user roles, oscar@avilacapllc.com promoted to admin
2. **Admin page implemented** — `/admin/users` shows team members, inline role editor, self-demotion prevention
3. **DEV_USER local dev bypass** — Set `DEV_USER=oscar@avilacapllc.com` in `.env` to skip OAuth, auto-provision user, log warning at startup
4. **Database migration for auth** — Added `role`, `display_name`, `last_login_at`, `created_at` columns to users table
5. **Navigation improvements** — Admin badge in header for admin users, current user display with logout link

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

- **Graph API polling not scheduled** — `graph_poller.py` exists but no Azure Function or cron job
- **`merge_organizations()` not implemented** — Returns NotImplementedError (stub only)
- **57 orphaned contacts / 54 orphaned prospects** — Pre-existing data quality issues in markdown source, not migration bugs
- **`main` branch is stale** — Contains old markdown-based code. Needs merge from `azure-migration` when ready

---

## Next Up

1. **Schedule `graph_poller.py`** — Deploy as Azure Function or container job for hourly email polling
2. **Implement `merge_organizations()`** — Currently a stub
3. **Merge `azure-migration` → `main`** — When confident production is stable
4. **Feature specs ready for implementation** (see docs/specs/):
   - SPEC_calendar-forward-scan.md — Auto-discovered prospect meetings
   - SPEC_merge-orgs.md — Organization merge tool
   - SPEC_org-aliases.md — Organization AKA names
   - SPEC_global-search-bar.md — Cross-entity search (already implemented, spec marked complete)

---

## Deferred / Parked

- `arec-mobile/` PWA — functional, not actively iterated
- Phase I2-I5 features (Intelligence pipeline enhancements, Intelligence UI, Briefing engine, Meeting transcript processing)
- Morning briefing removed entirely (moved to Overwatch, deprecated)
- Data cleanup for orphaned contacts/prospects
