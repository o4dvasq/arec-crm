# Azure Migration Status

**Date:** March 12, 2026
**Status:** ✅ COMPLETE — App live on Azure with PostgreSQL

---

## Production Environment

| Resource | Value |
|----------|-------|
| App URL | https://arec-crm-app.azurewebsites.net/crm |
| App Service | `arec-crm-app` (Linux, Python 3.12, B1) |
| PostgreSQL | `arec-crm-db` (Flexible Server, Burstable B1ms, centralus) |
| Database | `arec_crm` |
| Key Vault | `kv-arec-crm` (RBAC mode, centralus) |
| Resource Group | `rg-arec-crm` (westus2) |
| Tenant | Avila Capital LLC (`ebd42ab2-7f1c-4d40-8b44-f5ecc51d2659`) |
| Subscription | `064d6342-5dc5-424e-802f-53ff17bc02be` |
| Entra Client ID | `94270ca6-e1e1-4f0f-bdd0-f8df2cbb3750` |
| CI/CD | GitHub Actions → auto-deploy on push to `azure-migration` |
| Tests | 99 passing (CI runs on every push) |

---

## Implementation Steps — ALL COMPLETE

| Step | Description | Status |
|------|-------------|--------|
| 0 | Create `azure-migration` branch | ✅ |
| 1 | `app/models.py` — SQLAlchemy models | ✅ |
| 2 | `app/db.py` — Engine/session factory | ✅ |
| 3 | `scripts/create_schema.py` | ✅ |
| 4 | `scripts/migrate_to_postgres.py` | ✅ |
| 5 | `scripts/verify_migration.py` | ✅ |
| 6 | `app/sources/crm_db.py` — 45+ function replacement | ✅ |
| 7 | `app/auth/entra_auth.py` — MSAL SSO | ✅ |
| 8 | Import swaps (crm_reader → crm_db) | ✅ |
| 9 | `dashboard.py` updates (DB init, SSO) | ✅ |
| 10 | `_nav.html` updates (user name + logout) | ✅ |
| 11 | Test rewrite for Postgres — 99 tests passing | ✅ |
| 12 | Deployment config (startup.sh, requirements, workflow) | ✅ |
| 13 | Data migration to Azure Postgres | ✅ |
| 14 | Deploy, smoke test, fix startup issues | ✅ |
| 15 | Overwatch segregation + feature sync | ✅ |

---

## Data Migration Results (March 12, 2026)

| Category | Markdown | PostgreSQL | Status |
|----------|----------|------------|--------|
| Organizations | 146 | 146 | ✅ Complete |
| Offerings | 3 | 3 | ✅ Complete |
| Contacts | 194 | 137 | Partial (57 — orphaned refs to nonexistent orgs) |
| Prospects | 180 | 126 | Partial (54 — same root cause) |
| Interactions | 1 | 0 | 1 missing (data quality) |
| Email Log | 56 | 56 | ✅ Complete |
| Briefs | 59 | 59 | ✅ Complete |
| Prospect Notes | 21 | 21 | ✅ Complete |

---

## Development Workflow

**All development happens on the `azure-migration` branch. Do NOT use `main`.**

```
1. Make changes on azure-migration branch
2. Run tests: python -m pytest app/tests/ -v --tb=short
3. Commit and push to azure-migration
4. GitHub Actions automatically: runs 99 tests → deploys to Azure
5. Verify at https://arec-crm-app.azurewebsites.net/crm
```

**Local dev:** Set `DATABASE_URL` in `app/.env` pointing to local PostgreSQL (`postgresql://localhost/arec_crm`) or Azure Postgres. Run `python3 app/delivery/dashboard.py`.

---

## Critical Rules

- **NEVER modify `main` branch.** All work on `azure-migration`. `main` has stale markdown-based code.
- **No markdown fallback.** App reads from PostgreSQL only. `crm_reader.py` is deleted.
- **No local-only features.** Everything must work on Azure. If it doesn't deploy, it doesn't ship.
- **Migration script is idempotent.** Safe to re-run `scripts/migrate_to_postgres.py` for data re-sync.
- **Test before pushing.** CI will catch failures, but catching them locally is faster.

---

## Key Files

| File | Purpose |
|------|---------|
| `app/sources/crm_db.py` | PostgreSQL data layer (2000+ lines, 45+ functions) |
| `app/delivery/crm_blueprint.py` | CRM routes + brief synthesis |
| `app/delivery/dashboard.py` | Flask app factory (DB init, auth, blueprints) |
| `app/models.py` | SQLAlchemy ORM models (14 tables) |
| `app/db.py` | Database engine/session management |
| `app/auth/entra_auth.py` | Entra ID SSO |
| `app/graph_poller.py` | Multi-user email polling (not yet scheduled) |
| `.github/workflows/azure-deploy.yml` | CI/CD pipeline |
| `startup.sh` | Azure App Service startup (DB init + gunicorn) |
| `scripts/seed_user.py` | Add new users to `users` table |

---

## Deployment Issues Fixed (for reference)

1. **Missing `requirements.txt` in deploy zip** — Added to `azure-deploy.yml`
2. **Startup command not configured** — Set `--startup-file "startup.sh"` on App Service
3. **`dashboard.py` missing `db.init_app(app)`** — Added DB + auth initialization
4. **Env var mismatch** — `entra_auth.py` supports both `AZURE_*` and `ENTRA_*` names
5. **Missing Flask `secret_key`** — Added from env var with random fallback
6. **Port binding** — `startup.sh` reads `PORT` env var (Azure sets this dynamically)
7. **Dependency installation** — `startup.sh` installs from `app/requirements.txt` on first boot

---

## Pending (non-blocking)

- **Merge `azure-migration` → `main`** — Do this when ready to make `main` the production branch
- **Rotate Entra client secret** — ✅ Done (March 12, 2026)
- **Schedule `graph_poller.py`** — Deploy as Azure Function or container job for hourly email polling
- **Data cleanup** — 57 orphaned contacts, 54 orphaned prospects in markdown source (not critical)
- **`@login_required` on all routes** — SSO enforcement not yet applied to all CRM endpoints
