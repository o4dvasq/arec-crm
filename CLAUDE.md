# arec-crm

Multi-user CRM and fundraising platform for the AREC team. Manages investor pipeline, relationship briefs, and contact intelligence backed by PostgreSQL and Entra ID SSO.

**Production URL:** https://arec-crm-app.azurewebsites.net/crm
**Repo:** `~/Dropbox/projects/arec-crm/`

---

## ⚠️ CRITICAL: Development Rules

1. **ALL work on `azure-migration` branch.** Run `git checkout azure-migration` before doing anything. NEVER modify `deprecated-markdown` — it has stale markdown-based code. A pre-push hook blocks pushes to it. If the hook is missing, run `bash scripts/install-hooks.sh`.
2. **No local-only features.** Everything must deploy to Azure. If it doesn't work on Azure, it doesn't ship.
3. **No markdown backend.** The app uses PostgreSQL only. `crm_reader.py` is deleted. Do NOT import it. All data goes through `crm_db.py`.
4. **Test before pushing.** Run `python3.12 -m pytest app/tests/ -v --tb=short` (101 tests). CI runs tests on every push — failures block deployment.
5. **Push deploys automatically.** Push to `azure-migration` → GitHub Actions runs tests → deploys to Azure App Service. No manual deployment steps.

---

## Run Commands

```bash
git checkout azure-migration                      # ALWAYS start here
python3 app/delivery/dashboard.py                 # Local dev — http://localhost:8000
python3.12 -m pytest app/tests/ -v --tb=short      # Run 101 tests (uses SQLite in-memory)
python3 scripts/seed_user.py                      # Add a new user to the users table
python3 scripts/refresh_interested_briefs.py      # Bulk brief refresh for Stage 5 prospects
python3 app/drain_inbox.py                        # Drain crm@avilacapllc.com shared mailbox
```

**Local dev requires:** `DATABASE_URL` in `app/.env` pointing to local Postgres (`postgresql://localhost/arec_crm`) or Azure Postgres.

---

## Key Files

| File | Purpose |
|------|---------|
| `app/sources/crm_db.py` | PostgreSQL CRM data layer — single source of truth (2000+ lines, 45+ functions) |
| `app/delivery/crm_blueprint.py` | CRM routes + relationship brief synthesis endpoints |
| `app/delivery/admin_blueprint.py` | Admin routes (user management at `/admin/users`) |
| `app/delivery/dashboard.py` | Flask app factory (DB init → auth init → blueprint registration) |
| `app/models.py` | SQLAlchemy ORM models (14 tables, including User with role field) |
| `app/db.py` | Database engine/session management |
| `app/auth/entra_auth.py` | Entra ID SSO (MSAL OAuth), auto-provisioning, DEV_USER support |
| `app/auth/decorators.py` | `@require_admin` decorator for admin-only routes |
| `app/briefing/brief_synthesizer.py` | Claude API caller for relationship brief generation |
| `app/graph_poller.py` | Multi-user Graph API email polling (not yet scheduled) |
| `.github/workflows/azure-deploy.yml` | CI/CD: tests → deploy to Azure |
| `startup.sh` | Azure App Service startup (dependency install + DB check + gunicorn) |
| `scripts/seed_user.py` | Add new users to users table |
| `scripts/migrate_add_auth_columns.py` | Migration: adds role, display_name, last_login_at, created_at columns |
| `app/tests/conftest.py` | Test fixtures (SQLite in-memory, seed data) |

---

## Non-Obvious Conventions

- **PostgreSQL-only**: No markdown CRM files. All data reads/writes go through `crm_db.py`. No `crm_reader.py` imports allowed anywhere.
- **Multi-user authentication**: Entra ID SSO (MSAL OAuth flow) for production. DEV_USER env var for local dev. Auto-provisions users on first login. Oscar Vasquez auto-promoted to admin role.
- **Initialization order in dashboard.py**: `db.init_app(app)` → `init_auth_routes(app)` → `app.register_blueprint(crm_bp)`. Auth routes query the users table, so DB must init first.
- **Two-tier email matching**: Domain match first (Tier 1), then person email lookup (Tier 2). Unmatched → `unmatched_emails` table.
- **Brief synthesis JSON contract**: Claude must return `{narrative, at_a_glance}`. `brief_synthesizer.py` handles parse fallbacks.
- **Currency stored as BIGINT cents**: $50M = 5000000000. Display helpers `_format_currency()` / `_parse_currency()` in `crm_db.py`.
- **Env var fallback pattern**: `entra_auth.py` reads both `AZURE_*` and `ENTRA_*` env var names.
- **Personal productivity moved to Overwatch**: Tasks, briefings, meeting summaries, personal calendar — all in `~/Dropbox/projects/overwatch/`. This repo is fundraising CRM only.

---

## Authentication & User Management

- **DEV_USER for local dev**: Set `DEV_USER=oscar@avilacapllc.com` in `app/.env` to bypass OAuth during local development. Warning logged at startup.
- **Auto-provisioning**: New `@avilacapllc.com` users are auto-created on first login with role=`user` (except oscar@avilacapllc.com → `admin`).
- **Role-based access**: `users.role` column with values `admin` or `user`. Admin role gates `/admin/*` routes via `@require_admin` decorator.
- **Admin page**: `/admin/users` allows admins to view all users and change roles. Cannot demote yourself.
- **g.user available everywhere**: Flask `before_request` hook populates `g.user` with full user record (id, email, display_name, role, last_login_at).
- **Production uses Entra ID SSO**: Azure App Service handles OAuth redirect. Flask reads MSAL token and manages sessions.

## Active Constraints

- **Organization field is always a dropdown**: The Organization/Company field on People Detail edit must use a `<select>` from `/crm/api/orgs`. Never render a free-text input.
- **Prospect task creation uses `/crm/api/tasks` POST**: Never use `/crm/api/followup` to create tasks from the prospect detail page.
- **Root route redirects to CRM**: `/` redirects to `/crm` (pipeline view). No dashboard home page.
- **Assigned To filter on pipeline**: Pipeline view has dropdown to filter prospects by `assigned_to` field.
- **No markdown fallback**: App assumes PostgreSQL is available. No `crm_reader.py` imports allowed.
- **User provisioning is automatic**: Users auto-created on first login. No manual seeding required. oscar@avilacapllc.com promoted to admin on first login.
- **Tests use SQLite in-memory**: `conftest.py` defaults to `sqlite:///:memory:` when `TEST_DATABASE_URL` not set. All 101 tests run this way in CI.

---

## Azure Infrastructure

| Resource | Value |
|----------|-------|
| App Service | `arec-crm-app` (Linux, Python 3.12, B1, centralus) |
| PostgreSQL | `arec-crm-db` (Flexible Server, B1ms, centralus) |
| Key Vault | `kv-arec-crm` (secrets: DATABASE-URL, ANTHROPIC-API-KEY, ENTRA-CLIENT-SECRET) |
| Entra Client ID | `94270ca6-e1e1-4f0f-bdd0-f8df2cbb3750` |
| Tenant ID | `ebd42ab2-7f1c-4d40-8b44-f5ecc51d2659` |

---

## Specs & Documentation

- `docs/PROJECT_STATE.md` — Current state (overwritten each session)
- `docs/ARCHITECTURE.md` — System architecture (load for structural changes)
- `docs/DECISIONS.md` — Append-only decisions log
- `docs/specs/AZURE_DEPLOYMENT_STATUS.md` — Azure migration status (COMPLETE)
- `docs/specs/SPEC_*.md` — Feature specs ready for implementation
