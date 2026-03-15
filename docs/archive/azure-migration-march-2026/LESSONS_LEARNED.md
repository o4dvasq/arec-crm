# Azure Migration Lessons Learned — March 2026

**Date:** 2026-03-15
**Duration:** ~5 days (March 10–14)
**Outcome:** Aborted. postgres-local branch works; Azure deployment not production-ready.
**Decision:** Return to markdown-local for daily use. Revisit Azure methodically later.

---

## What We Tried

Three things simultaneously on a mega-branch (`azure-migration`, later `postgres-local`):

1. Data layer: markdown files → PostgreSQL via new `crm_db.py` (2000+ lines, 45+ functions)
2. Auth: Entra ID SSO with auto-provisioning for 8 AREC team members
3. Deployment: Azure App Service + GitHub Actions CI/CD + managed Postgres

## What Worked

**The Postgres layer is solid.** 128+ tests passing, all CRUD operations working, seed script idempotent, auto_migrate safe. The `postgres-local` branch is a genuine asset — keep it.

**Data shape compatibility was perfect.** By maintaining identical function signatures between `crm_reader.py` and `crm_db.py`, zero template changes were needed. This design should be preserved.

**Key architectural decisions that held up:**
- Plain strings (not Enums) for `urgency`, `closing`, `type`, `source` — avoided migration headaches
- Currency as BIGINT cents ($50M = 5,000,000,000) — clean everywhere
- Additive-only auto_migrate — never drops columns, safe to run on every startup
- SQLite in-memory test fixtures — tests never need a running Postgres instance

## What Went Wrong

**Nine distinct deployment issues consumed ~1.5 days:**

1. **Port binding** — Azure sets PORT dynamically; our startup.sh hardcoded 8000
2. **Stale files** — Zip deploy is additive; old templates persisted across deploys
3. **502 timeout** — `--clean true` wipes 10,000+ files sequentially, exceeding Azure's 2-min timeout
4. **Worker boot failure** — `auto_migrate()` ran at module import time, crashing all gunicorn workers before they started
5. **Oryx venv caching** — Azure's build system skipped pip install on repeat deploys when it shouldn't have
6. **Oryx path extraction** — Zip extracted to `/tmp/.../build/` not `/home/site/wwwroot`; startup.sh couldn't find the app
7. **Deployment trigger mismatch** — `az webapp deploy` stops the app during deploy; the action doesn't
8. **Health check too fast** — Verification curl ran at 30s; app takes 60s to cold-start
9. **Oryx complexity** — Final fix was to disable Oryx entirely (`SCM_DO_BUILD_DURING_DEPLOYMENT=false`)

**Root cause was scope.** Each issue was individually solvable (30 min – 2 hours). But hitting them in sequence while also debugging data migration and auth logic made progress feel impossible. The problems were infrastructure, not code — but they blocked everything.

## Recommendations for Next Attempt

### Strategy: Decompose into 4 branches

```
Branch 1: postgres-local     ← DONE (March 14)
Branch 2: azure-db           ← Same code, DATABASE_URL → Azure Postgres (no deployment)
Branch 3: azure-deploy       ← Pure infra: startup.sh, CI/CD, health checks
Branch 4: multi-user         ← Entra ID, roles, Graph scanner, briefing engine
```

Each branch is independently testable. Bugs are isolated. Deployment complexity is confined to Branch 3.

### Tactical

- Disable Oryx from day one (`SCM_DO_BUILD_DURING_DEPLOYMENT=false`)
- Prototype deployment on a dummy Flask "hello world" app first — isolate infra from business logic
- Use explicit stop → deploy → start lifecycle (not the GitHub action's implicit handling)
- Health check wait: 120+ seconds for cold-start
- Stream logs immediately with `az webapp log tail` during any deploy
- Test startup.sh locally before deploying
- Set up Key Vault immediately, test `@Microsoft.KeyVault(...)` reference syntax on simple app first

### What to Preserve from postgres-local

- `crm_db.py` — all 45+ functions, identical signatures to crm_reader.py
- `models.py` — 12 tables, no Enums, clean schema
- `auto_migrate.py` — additive-only, production-safe
- `conftest.py` — SQLite in-memory fixtures (gold for testing)
- `seed_from_markdown.py` — idempotent markdown → Postgres seeder
- All 128+ tests
- The branch strategy architecture doc

## Files Archived

The following files from `postgres-local` are preserved in this archive directory:
- `SPEC_azure-deploy.md`
- `SPEC_postgres-local.md`
- `SPEC_postgres-local-import-cleanup.md`
- Azure platform architecture docs
- Deployment guides

The `postgres-local` branch itself remains intact on GitHub as the canonical reference.
