# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-15 — Stripped all Postgres/Azure/Entra infrastructure; returned to markdown-only local CRM

**Active branch:** `postgres-local`

---

## What's Built and Working

### Markdown Backend
- `app/sources/crm_reader.py` — Single source of truth for all CRM data. ~1800 lines, 60+ functions. Reads/writes markdown and JSON files directly. All production code imports from here.
- `app/sources/email_matching.py` — Extracted from deleted `crm_graph_sync.py`. Pure utility: `_fuzzy_match_org`, `_is_internal`, `_resolve_participant`. No Graph dependency.

### Web Dashboard (Flask — local dev, port 8000)
- `app/delivery/dashboard.py` — Flask app factory. No DB init. Loads env → registers blueprints → serves. `g.user` set from `DEV_USER` env var.
- `app/delivery/crm_blueprint.py` — All CRM routes backed by `crm_reader.py`. Graph-dependent routes (`email-scan`, `auto-capture`) return 501 with helpful message.
- `app/delivery/tasks_blueprint.py` — Tasks page. Markdown-backed task CRUD. ID-based prospect task routes return 501.
- `app/auth/decorators.py` — `require_api_key_or_login` is a no-op passthrough for local dev. Decorator stays on all `/crm/api/tasks*` routes for pattern preservation.
- Dark theme throughout. Pipeline, prospect detail, orgs, people, tasks pages all functional.
- Brief synthesis via Claude API (`brief_synthesizer.py`).

### Task API (Overwatch-compatible)
- `GET /crm/api/tasks/dashboard` — All open tasks, enriched.
- `GET /crm/api/tasks?org=X` — Tasks for specific org.
- `POST /crm/api/tasks` — Create task (markdown-backed, returns synthetic task object).
- `PATCH /crm/api/tasks/complete` — Returns 501 (ID-based completion requires DB).
- `PATCH /crm/api/tasks/<id>` — Returns 501 (ID-based update requires DB).

### Morning Briefing (`app/main.py`)
- Degrades gracefully if Graph dependencies unavailable. Skips calendar/email fetch; proceeds with local data only.

### Contact Profiles
- `contacts/{name}.md` — 211 contact profile files (formerly `memory/people/`).
- `crm/org-locations.md` — Org location data.
- `projects/arec-fund-ii.md` — Project notes.

### Test Suite
- `app/tests/test_brief_synthesizer.py`, `test_email_matching.py`, `test_task_parsing.py`
- **52 tests passing**. No DB fixtures. No DATABASE_URL required.

### Skills (Claude Desktop via MCP — unaffected by cleanup)
- `skills/email-scan.md`, `skills/meeting-debrief.md`
- `app/auth/graph_auth.py`, `app/sources/ms_graph.py` — preserved for skill use

---

## What Was Just Completed

**crm-markdown-cleanup (2026-03-15)**

- **Deleted 19 Postgres/Azure/Entra files** — `crm_db.py`, `models.py`, `db.py`, `auto_migrate.py`, `crm_graph_sync.py`, `entra_auth.py`, all migration scripts, Azure deploy workflow, `startup.sh`, `DEPLOYMENT.md`, Postgres-specific tests.
- **Rewired all delivery layer imports** — `dashboard.py`, `crm_blueprint.py`, `tasks_blueprint.py` now import from `crm_reader.py`. DB-only routes (task complete/update by ID) return 501 with helpful messages.
- **Made `decorators.py` a no-op passthrough** — `require_api_key_or_login` lets all requests through for local dev. Decorator stays in place for future auth.
- **Guarded `main.py` Graph imports** — `try/except` at top level; `_GRAPH_AVAILABLE` flag gates all Graph calls. App gracefully skips calendar/email if Graph not available.
- **Extracted `email_matching.py`** — The 3 pure utility functions from the deleted `crm_graph_sync.py` were needed by `test_email_matching.py`. Extracted to their own module, no Graph dependency.
- **Archived Azure/Postgres docs** — Specs and architecture docs moved to `docs/archive/azure-migration-march-2026/`. `LESSONS_LEARNED.md` already existed there.
- **App starts clean** with `python3 app/delivery/dashboard.py` and no env vars beyond `DEV_USER`.

---

## Known Issues

- **`/api/task/complete` and `/api/tasks/prospect/<id>/complete` return 501** — ID-based task completion doesn't exist in the markdown layer. Workaround: complete by org + text substring via `complete_prospect_task(org, text)` in `crm_reader.py`.
- **Interactions seeding** — `interactions.md` has only 1 entry using a person name as heading instead of org. Skipped on import. No data loss.

---

## Next Up

1. Decide on next spec — candidates: `global-search-bar`, `people-detail-contact-box`, `overwatch-repo-scaffold`
2. If restoring Overwatch task integration: implement `add_prospect_task_and_return` wrapper in `crm_reader.py` to return a synthetic task dict after adding (unblocks `POST /crm/api/tasks` returning a real task object).

**Local dev setup:**
```bash
echo "DEV_USER=oscar" > app/.env     # First time only
python3 app/delivery/dashboard.py    # http://localhost:8000
python3.12 -m pytest app/tests/ -v  # 52 tests
```

---

## Open Design Questions

<!-- None at this time -->

---

## Deferred / Parked

- Prospect task completion by ID — requires either a DB or a slug/index scheme in the markdown layer
- Graph API features (`email-scan`, `auto-capture`) — work via Claude Desktop skill; disabled as in-app routes (return 501)
- `arec-mobile/` PWA — functional, not actively iterated
- `prospect_meetings` — JSON file-backed (`crm/prospect_meetings.json`); no DB table
