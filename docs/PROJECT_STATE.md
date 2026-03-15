# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-14 — Renamed `memory/` to `contacts/`, removing productivity-plugin data from CRM

**Active branch:** `postgres-local` (created off `deprecated-markdown`)
**Azure deployment branch:** `azure-migration` (currently deployed; pending switch to `postgres-local`)

---

## What's Built and Working

### PostgreSQL Backend (postgres-local branch)
- `app/sources/crm_db.py` — Drop-in replacement for `crm_reader.py`. All 45+ functions re-implemented with SQLAlchemy. Plain strings everywhere (no Enums, no User FK). Team hardcoded as Oscar + Tony. Includes `add_prospect_task_and_return` and `update_prospect_task` for ID-based task mutation.
- `app/models.py` — 12 SQLAlchemy ORM models: Organization, Offering, Contact, PipelineStage, Prospect, Interaction, EmailScanLog, Brief, ProspectNote, UnmatchedEmail, PendingInterview, ProspectTask. No User model. No Enum types.
- `app/db.py` — Engine/session management. SQLite-aware: skips `pool_size`/`max_overflow` for SQLite (required for tests).
- `app/auto_migrate.py` — Additive-only schema migration (create missing tables, add missing columns, create missing indexes). Skips ALTER TABLE on SQLite.
- `app/delivery/dashboard.py` — Flask app wired to `crm_db.py`. DB init at startup + auto_migrate call. Root route → `/crm`. Port 8000. `before_request` hook sets `g.user` from session or `DEV_USER` env var.
- `app/delivery/crm_blueprint.py` — All CRM routes use `crm_db.py`. All 5 task API routes protected by `@require_api_key_or_login`. Includes `/crm/tasks` page route and `/crm/api/tasks/dashboard` + `/crm/api/tasks/<id>` PATCH.
- `app/delivery/tasks_blueprint.py` — CRM task routes use `crm_db.py`; general tasks page still uses `memory_reader.py`.
- `app/auth/decorators.py` — `require_api_key_or_login` decorator: accepts `X-API-Key` header (if `OVERWATCH_API_KEY` set) or `g.user` session. Returns 401 JSON if neither.
- `app/sources/relationship_brief.py` — All 5 inline imports point to `crm_db.py`. Brief synthesis and person update routing fully DB-backed. Person intel reads from `contacts/` directory.
- `app/briefing/prompt_builder.py` — Both imports point to `crm_db.py`. Morning briefing prompt assembly fully DB-backed. Intel files read from `contacts/`.

### Contact Profiles
- `contacts/{name}.md` — 211 contact profile files (formerly `memory/people/`). Flat directory, no subdirectory. Clean filenames (e.g., `darren-sutton.md`).
- `crm/org-locations.md` — Org location data (formerly `memory/org-locations.md`).
- `projects/arec-fund-ii.md` — Project notes (formerly `memory/projects/`).
- `crm/meeting_history.md` — Meeting log; merged content from former `memory/meetings.md`.

### Task API (Overwatch-compatible)
- `GET /crm/api/tasks/dashboard` — All open tasks, enriched. API key or session required.
- `GET /crm/api/tasks?org=X` — Tasks for specific org. `GET /crm/api/tasks` (no param) — all open tasks.
- `POST /crm/api/tasks` — Create task. Returns `{ok, task}`.
- `PATCH /crm/api/tasks/complete` — Complete by `{id}`.
- `PATCH /crm/api/tasks/<id>` — Update fields (text, owner, priority, status). Returns `{ok, task}`.
- All 5 accept `X-API-Key: <OVERWATCH_API_KEY>` or session cookie.

### Tasks Page
- `GET /crm/tasks` — Standalone tasks page showing all open prospect tasks. My Tasks / Team Tasks columns. AJAX-loaded, complete/add actions, client-side owner+org filtering. Nav updated to point here.

### Test Suite
- `app/tests/conftest.py` — SQLite in-memory fixtures.
- `app/tests/test_crm_db.py` — 52 tests covering full postgres backend.
- `app/tests/test_tasks_api_key.py` — 24 tests covering API key auth on all 5 task endpoints.
- **128 tests total passing**.

### Seed Script
- `scripts/seed_from_markdown.py` — Reads all markdown/JSON files via `crm_reader.py`, writes to Postgres. Idempotent. Reads contacts from `contacts/` (updated).

### Web Dashboard (Flask — local dev)
- Dark theme throughout. Pipeline, prospect detail, orgs, people, tasks pages all functional.
- Prospect detail: click-to-edit fields, relationship briefs, interaction history, notes, contacts.
- Brief synthesis via Claude API (`brief_synthesizer.py`).
- Nav shows "AREC CRM" (not "Overwatch"). Tasks nav link → `/crm/tasks`.

### Azure Deployment
- `requirements.txt` at repo root — ensures Oryx populates `antenv` correctly on every deploy.
- `startup.sh` — activates `antenv`, pip-installs deps, runs auto-migrate, launches gunicorn.
- App currently deployed at `https://arec-crm-app.azurewebsites.net` from `azure-migration` branch.
- `.github/workflows/azure-deploy.yml` — packages `contacts/` and `projects/` (not `memory/`).

---

## What Was Just Completed

**memory/ → contacts/ rename (2026-03-14)**

- **Renamed `memory/people/` → `contacts/`** — 211 profile files moved, flattened (no `people/` subdirectory). `darren-sutton-dsuttonsuttoncapitalgroupcom.md` cleaned up to `darren-sutton.md`.
- **Removed productivity-plugin data** — `memory/context/` (me.md, company.md) and `memory/glossary.md` deleted from CRM repo. These belong to the local productivity plugin, not the deployed CRM.
- **Relocated supporting files** — `memory/org-locations.md` → `crm/org-locations.md`; `memory/projects/arec-fund-ii.md` → `projects/arec-fund-ii.md`; `memory/meetings.md` merged into `crm/meeting_history.md`.
- **Updated all code path constants** — `PEOPLE_ROOT` in `crm_db.py`, `crm_reader.py`; path joins in `relationship_brief.py`, `prompt_builder.py`, `crm_blueprint.py`, `bootstrap_contacts_index.py`, `seed_from_markdown.py`, `migrate_to_postgres.py`.
- **Updated deploy pipeline** — `.github/workflows/azure-deploy.yml` now packages `contacts/` and `projects/` instead of `memory/`.
- **128 tests still passing** after all changes.

---

## Known Issues

- **Azure deployment source mismatch** — Azure App Service is configured to deploy from `azure-migration` branch. All current development is on `postgres-local`. Decision needed: switch deployment branch, or merge postgres-local into azure-migration.
- **Interactions seeding** — `interactions.md` only has 1 entry and it uses a person name (`Tony Avila`) as the heading instead of an org name, so it gets skipped. No data loss; interactions come in via the app.
- **Contacts: 47 skipped on first seed run** — Some contacts have orgs that appear only in `prospects.md`. Auto-created on prospect seeding; picked up on second seed run.

---

## Next Up

1. **Commit and push** `contacts/` rename changes to `postgres-local`.
2. **Decide deployment branch** — switch Azure to `postgres-local`, or merge postgres-local → azure-migration.
3. **Branch 2**: Full Azure deploy with PostgreSQL Flexible Server, Key Vault, Entra ID. See `docs/specs/SPEC_azure-deploy.md`.

**Local dev setup** (postgres-local branch):
```bash
createdb arec_crm                  # First time only
echo "DATABASE_URL=postgresql://localhost/arec_crm" > app/.env
python3 scripts/seed_from_markdown.py   # Populate DB from markdown/contacts/
python3 app/delivery/dashboard.py       # http://localhost:8000
python3.12 -m pytest app/tests/ -v     # 128 tests
```

---

## Open Design Questions

<!-- None at this time -->

---

## Deferred / Parked

- Morning briefing pipeline (`app/main.py`) — still markdown-based; not in scope for postgres-local
- `arec-mobile/` PWA — functional, not actively iterated
- `prospect_meetings` — still JSON file-backed (`crm/prospect_meetings.json`); no DB table in Branch 1 scope
- Graph API features (`email-scan`, `auto-capture`) — disabled on this branch; will be re-enabled in Branch 2/3
