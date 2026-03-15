# arec-crm

CRM and fundraising platform for the AREC team. Manages investor pipeline, relationship briefs, and contact intelligence backed by markdown files. Single-user local deployment.

**Location:** `~/Dropbox/projects/arec-crm/`
**Branch:** `postgres-local` (active dev branch)
**Sister repo:** `~/Dropbox/projects/overwatch/` (personal productivity — tasks, briefings, personal contacts)

---

## Run Commands

```bash
echo "DEV_USER=oscar" > app/.env                       # First time only
python3 app/delivery/dashboard.py                     # Web dashboard — http://localhost:8000
python3.12 -m pytest app/tests/ -v                    # 52 tests
```

## Key Files

| File | Purpose |
|------|---------|
| `app/sources/crm_reader.py` | Markdown backend — single source of truth (~1800 lines, 60+ functions) |
| `app/delivery/dashboard.py` | Flask app factory (load env → register blueprints) |
| `app/delivery/crm_blueprint.py` | CRM routes + relationship brief synthesis endpoints |
| `app/delivery/tasks_blueprint.py` | Tasks page routes |
| `app/auth/decorators.py` | `require_api_key_or_login` — no-op passthrough for local dev |
| `app/tests/conftest.py` | pytest path setup (no DB fixtures) |
| `app/sources/email_matching.py` | Org/participant fuzzy matching utilities |
| `app/auth/graph_auth.py` | Graph token auth — used by email-scan Claude Desktop skill only |
| `app/sources/ms_graph.py` | MS Graph API calls — used by email-scan Claude Desktop skill only |

## Non-Obvious Conventions

- **Markdown-only**: All production code reads/writes through `crm_reader.py`. No database.
- **No auth**: `require_api_key_or_login` is a no-op passthrough. `g.user` is set by `before_request` via `DEV_USER` env var.
- **Currency as floats in markdown**: `_format_currency()` / `_parse_currency()` in `crm_reader.py`.
- **Brief synthesis JSON contract**: Claude must return `{narrative, at_a_glance}`. `brief_synthesizer.py` handles parse fallbacks.
- **Graph-dependent routes return 501**: Email scan and auto-capture routes return 501 with a message pointing to the Claude Desktop skill.
- **Morning briefing (`main.py`) degrades gracefully**: If Graph dependencies are unavailable, it skips calendar/email fetch and proceeds with local data only.

## Active Constraints

- **No database imports in production code**: `crm_db.py`, `models.py`, `db.py`, `auto_migrate.py` do not exist on this branch.
- **Organization field is always a dropdown**: The Organization field on People Detail edit uses `<select>` from `/crm/api/orgs`. Never free-text.
- **Task API routes use `@require_api_key_or_login`**: Decorator is a passthrough but must stay on all 5 `/crm/api/tasks*` routes so the pattern is preserved for future auth.
- **Keep both `requirements.txt` files in sync**: `app/requirements.txt` and root `requirements.txt` must match. Update both when adding a dependency.
