SPEC: CRM Markdown Cleanup
Project: arec-crm | Branch: markdown-local | Date: 2026-03-15
Status: Ready for implementation

---

## 1. Objective

Strip all PostgreSQL, Azure, Entra ID, and multi-user infrastructure from the arec-crm codebase, leaving a clean markdown-only local CRM. The app already works against markdown files — this is a dead code removal and cleanup pass, not a rewrite. Archive lessons learned from the Azure migration attempt for future reference.

## 2. Scope

### In Scope
- Delete all files whose sole purpose is Postgres, Azure deploy, migration, or Entra auth
- Remove lazy imports of Graph/auth from route functions that won't work without Graph tokens
- Clean up requirements.txt (remove sqlalchemy, psycopg2-binary, msal, gunicorn)
- Make `auth/decorators.py` a no-op passthrough (keeps route syntax stable)
- Archive Azure/Postgres specs to `docs/archive/azure-migration-march-2026/`
- Create `docs/archive/azure-migration-march-2026/LESSONS_LEARNED.md`
- Update CLAUDE.md to reflect markdown-only reality
- Verify app starts and all non-Graph routes work

### Out of Scope
- Functional CRM changes (no new features, no bug fixes)
- Overwatch repo creation (separate spec)
- Re-implementing Graph email scan (this was a Claude Desktop skill, not app code — the skill still works via MCP)
- Any database work

## 3. Business Rules

- The email scan skill (`skills/email-scan.md`) operates through Claude Desktop + MCP, not through Flask routes. The lazy Graph imports in `crm_blueprint.py` (lines 442-444, 1287-1288) are for an in-app email scan feature that requires a Graph token the local app doesn't have. These routes should return a clear error message ("Email scan available via Claude Desktop skill") rather than crashing.
- The `/crm/api/auto-capture` route (line 1287) also depends on Graph. Same treatment — friendly error, not crash.
- The calendar refresh route in `dashboard.py` (line 303) depends on Graph. Same treatment.
- `auth/decorators.py` `require_api_key_or_login` becomes a passthrough. All routes are open for local use. The decorator stays so route definitions don't need editing.

## 4. Data Model / Schema Changes

None. Markdown files are unchanged.

## 5. Files to Delete

```
.github/workflows/azure-deploy.yml
startup.sh
DEPLOYMENT.md
app/auth/entra_auth.py
app/db.py
app/models.py
app/auto_migrate.py
app/sources/crm_db.py
app/sources/crm_graph_sync.py
scripts/create_schema.py
scripts/migrate_to_postgres.py
scripts/verify_migration.py
scripts/seed_from_markdown.py
scripts/phase1-migrate.sh
scripts/phase1-preflight.sh
scripts/phase2-machine-b.sh
app/tests/test_crm_db.py
app/tests/test_tasks_api_key.py
```

Keep but do NOT delete:
- `app/auth/graph_auth.py` — still needed by email-scan skill via Claude Desktop
- `app/sources/ms_graph.py` — still needed by email-scan skill via Claude Desktop
- `app/auth/__init__.py` — keep directory intact

## 6. Files to Edit

### app/delivery/dashboard.py
Remove or guard these blocks:
- Any import of `db`, `models`, `auto_migrate` (should not exist on this branch, verify)
- Lines ~303-304: Calendar refresh route's lazy import of `graph_auth` and `ms_graph` — wrap in try/except, return JSON error if Graph auth unavailable

### app/delivery/crm_blueprint.py
- Lines ~442-444: `email_scan_live()` route's lazy import of `graph_auth`, `ms_graph` — replace function body with: `return jsonify({'ok': False, 'error': 'Live email scan requires Graph auth. Use Claude Desktop /email-scan skill instead.'}), 501`
- Lines ~1287-1288: `auto_capture()` route's lazy import of `crm_graph_sync` — same treatment, return 501 with message

### app/auth/decorators.py
Replace body of `require_api_key_or_login` with passthrough:
```python
def require_api_key_or_login(f):
    """No-op for local dev. Auth bypassed."""
    @wraps(f)
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated
```

### app/requirements.txt
Remove: `msal>=1.28.0`, `sqlalchemy>=2.0.0`, `psycopg2-binary>=2.9.9`, `gunicorn>=21.2.0`
Add: `markdown>=3.5.0`

### app/.env.example
Replace contents with:
```
DEV_USER=oscar
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### CLAUDE.md
Already updated in branch setup commit. Verify it matches the new reality after cleanup.

## 7. Docs to Archive

Create `docs/archive/azure-migration-march-2026/` and move:
- `docs/specs/SPEC_azure-deploy.md`
- `docs/specs/SPEC_postgres-local.md`
- `docs/specs/SPEC_postgres-local-import-cleanup.md`
- `docs/specs/SPEC_crm-tasks-api-endpoint.md` (if Postgres-specific)
- `docs/specs/SPEC_crm-tasks-page.md` (if Postgres-specific)
- `docs/ARCHITECTURE.md` (Azure-centric architecture doc)
- `IMPLEMENTATION_SUMMARY.md`
- Any other Azure-specific docs

Also create `docs/archive/azure-migration-march-2026/LESSONS_LEARNED.md` — see separate deliverable.

## 8. Integration Points

- Claude Desktop skills (`skills/email-scan.md`, `skills/meeting-debrief.md`) still work via MCP tools and are unaffected by this cleanup
- `app/auth/graph_auth.py` and `app/sources/ms_graph.py` remain for skill use
- Update orchestrator (`app/main.py`) has lazy Graph imports — same treatment as above (try/except, degrade gracefully if no Graph token)

## 9. Constraints

- Do not modify any CRM data files (crm/*.md, crm/*.json)
- Do not modify crm_reader.py (it's the working backend)
- Do not modify any templates (UI is stable)
- Do not rename routes or change URL patterns
- Preserve all test files that test markdown-backed functionality (test_brief_synthesizer.py, test_email_matching.py, test_task_parsing.py)
- Keep git history clean — one commit per logical change, not one giant commit

## 10. Acceptance Criteria

- `python3 app/delivery/dashboard.py` starts without errors, without DATABASE_URL, without any Azure env vars
- All CRM page routes load (pipeline, orgs, org detail, people, person detail, prospect detail)
- All CRM API routes that don't require Graph return 200 (fund-summary, prospects, orgs, contacts, tasks, briefs, notes, meetings)
- Graph-dependent routes return 501 with helpful message
- `python3 -m pytest app/tests/ -v` passes (excluding deleted test files)
- No imports of `crm_db`, `models`, `auto_migrate`, `psycopg2`, `sqlalchemy`, `entra_auth` remain in any production code path
- `grep -r "crm_db\|auto_migrate\|entra_auth" app/delivery/ app/sources/crm_reader.py` returns zero matches
- CLAUDE.md accurately describes the markdown-only system
- `docs/archive/azure-migration-march-2026/LESSONS_LEARNED.md` exists

## 11. Files Likely Touched

| File | Reason |
|------|--------|
| `app/delivery/dashboard.py` | Guard Graph imports in calendar refresh |
| `app/delivery/crm_blueprint.py` | Guard Graph imports in email scan + auto-capture routes |
| `app/auth/decorators.py` | Make auth decorator a passthrough |
| `app/main.py` | Guard Graph imports in update orchestrator |
| `app/requirements.txt` | Remove Postgres/Azure deps |
| `app/.env.example` | Simplify to local-only vars |
| `CLAUDE.md` | Verify/update |
| 18 files deleted | See Section 5 |
| 6+ docs moved | See Section 7 |
