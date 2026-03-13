# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-13 — Person name linking + simplify pass (index caching, Jinja readability, typeof guard cleanup)

---

## What's Built and Working

### AREC CRM — Multi-User Fundraising Platform (PRODUCTION)
- **Production URL**: https://arec-crm-app.azurewebsites.net/crm
- **Backend**: PostgreSQL-only (`crm_db.py`). All 45+ functions operational. No markdown fallback.
- **Database**: Azure PostgreSQL Flexible Server (`arec-crm-db`, centralus, Burstable B1ms)
- **Local Database**: PostgreSQL 14 on localhost for dev (`postgresql://localhost/arec_crm`)
- **Schema**: 14 tables with all relationships and foreign keys
- **Authentication**: Entra ID SSO (MSAL confidential client). Auto-provisioning on first login. DEV_USER bypass for local dev. All CRM routes require authentication (`@login_required` on 50 routes).
- **User Management**: Admin page at `/admin/users` with role management. oscar@avilacapllc.com auto-promoted to admin.
- **CI/CD**: GitHub Actions — push to `azure-migration` → 120 tests → auto-deploy to Azure
- **CRM Features**: Pipeline, prospect detail, org management, relationship briefs, contact intelligence, interaction history
- **Brief Synthesis**: Relationship briefs (org + person) via Claude API, cached in PostgreSQL
- **Email Integration**: Graph API poller ready (`graph_poller.py` multi-user support), auto-capture, two-tier matching
- **Multi-User Email Polling**: `graph_poller.py` iterates over users with `graph_consent_granted=True`, acquires tokens, calls `run_auto_capture(user_id)`, records `scanned_by` attribution
- **Access Control**: Unapprovisioned users see access_denied.html page
- **Dark Theme**: Full dark theme throughout
- **Navigation**: Lucide target icon, user name on right with hover dropdown (Admin + Logout), centered nav tabs (Pipeline, People, Orgs, Tasks), global search on right
- **Pipeline UI Polish**: At a Glance column is muted/lighter (2-line clamp), Tasks column wider with assignee initials, markdown stripped from display text
- **Tasks Page**: `/crm/tasks` — My Tasks + Team Tasks sections, priority/size sort, client-side search, prospect links
- **Person Name Linking**: All person names app-wide are clickable links to `/crm/people/<slug>` via `linkifyPersonNames()` in `crm.js`

### Overwatch — Personal Productivity Platform (LOCAL ONLY)
- **Location**: `~/Dropbox/projects/overwatch/`
- **Port**: 3001 (local-only, single-user, no Azure deployment)
- **Features**: Task management (TASKS.md), meeting summaries, personal memory, calendar integration
- **Independence**: Zero imports from arec-crm

---

## What Was Just Completed (March 13, 2026)

1. **`linkifyPersonNames()` in `crm.js`** — Global function that reads `window.SEARCH_INDEX` (already injected by `_nav.html`), builds a name→URL lookup for all `type: 'person'` entries, finds all `[data-person-name]` elements, and replaces them with `.person-link` anchors. `stopPropagation()` added to prevent triggering table row click handlers. Called on `DOMContentLoaded` for server-rendered content.
2. **`.person-link` CSS** — Added to `crm.css`: subtle blue (`#60a5fa`), no underline until hover, matches app accent color.
3. **Pipeline primary contact** — Wrapped primary contact text in `<span data-person-name>` in `renderCell()`; `linkifyPersonNames()` called at end of `renderTable()` since rows are JS-rendered after page load.
4. **Prospect detail primary contact** — Jinja template updated to emit `<span data-person-name>` when primary contact name is present; falls back to `—` when empty.
5. **Prospect detail note authors** — `data-person-name` added to `.note-author` span in `renderNotesLog()`; `linkifyPersonNames()` called after notes `innerHTML` is set.
6. **Simplify pass** — `_personNameIndex` cached at module scope (built once, reused on all `renderTable()` / `renderNotesLog()` calls); cramped Jinja primary contact block expanded to readable multi-line; unnecessary `typeof linkifyPersonNames` guards removed.

---

## Active Branch: `azure-migration`

**⚠️ ALL WORK HAPPENS ON `azure-migration`. DO NOT USE `deprecated-markdown`.**

`main` was renamed to `deprecated-markdown`. A pre-push hook blocks pushes to it. If the hook is missing, run `bash scripts/install-hooks.sh`.

**Development workflow:**
1. `git checkout azure-migration`
2. Make changes
3. `python3.12 -m pytest app/tests/ -v --tb=short`
4. Commit and push → CI auto-deploys to Azure
5. Verify at https://arec-crm-app.azurewebsites.net/crm

---

## Known Issues

- **Graph API polling not scheduled** — `graph_poller.py` exists but no Azure Function or cron job set up yet
- **Auto-provisioning still enabled** — All `@avilacapllc.com` users auto-created on first login. Access denied page only applies if auto-provisioning is disabled.
- **`merge_organizations()` not implemented** — Returns NotImplementedError (stub only)
- **57 orphaned contacts / 54 orphaned prospects** — Pre-existing data quality issues in markdown source, not migration bugs
- **`deprecated-markdown` branch is stale** — Contains old markdown-based code. Pre-push hook blocks pushes to it.
- **Tasks page shows DB tasks only** — Tasks in TASKS.md (created before DB migration) won't appear on `/crm/tasks`. Only tasks in `prospect_tasks` DB table are shown. Prospect detail page task functions still read/write TASKS.md — split-system state.
- **`prospect_tasks` has no `due_date`** — Spec referenced this field but it doesn't exist in the model. Due date column omitted from tasks page.

---

## Next Up

1. **SPEC_prospect-detail-overhaul.md** — Prospect detail page overhaul
2. **SPEC_contact-enrichment.md** — Contact enrichment features
3. **SPEC_nav-redesign.md** — Nav redesign (if any remaining items)
4. **SPEC_pipeline-polish.md** — Pipeline polish
5. **Run graph column migration** — Execute `python3 scripts/migrate_add_graph_columns.py` on Azure database
6. **Schedule `graph_poller.py`** — Deploy as Azure Function or container job for hourly email polling

---

## Deferred / Parked

- `arec-mobile/` PWA — functional, not actively iterated
- Phase I2-I5 features (Intelligence pipeline enhancements, Intelligence UI, Briefing engine, Meeting transcript processing)
- Morning briefing removed entirely (moved to Overwatch, deprecated)
- Data cleanup for orphaned contacts/prospects
- `merge_organizations()` implementation (SPEC_merge-orgs.md)
- Migrate TASKS.md tasks to `prospect_tasks` DB table (would unify task sources)
