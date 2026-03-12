# Claude Code Handoff: Debug Azure App Crash

**Date:** March 12, 2026
**Branch:** `azure-migration` (NEVER touch `main`)
**Problem:** App shows "Application Error" at https://arec-crm-app.azurewebsites.net/crm

---

## Context

The AREC CRM is a Flask app deployed to Azure App Service. It was recently switched from a markdown-file backend to PostgreSQL. The GitHub Actions CI/CD pipeline deploys on push to `azure-migration`. Tests pass (121 tests, all green). But the live app crashes on startup.

---

## Likely Root Causes (investigate in order)

### 1. `dashboard.py` never initializes the database

`app/delivery/dashboard.py` creates the Flask app and registers the CRM blueprint, but **never calls `db.init_app(app)` or `db.init_db()`**. The `crm_blueprint.py` imports ~40 functions from `sources.crm_db`, which all need `db.SessionLocal` to be initialized. On first request, every DB call will hit `RuntimeError: Database not initialized. Call init_db() first.`

**Fix:** Add `from db import init_app` and call `init_app(app)` in `dashboard.py` after creating the Flask app, before registering blueprints.

### 2. Env var name mismatch between Azure App Settings and code

Azure App Settings use these names (confirmed from deployment status doc):
- `ENTRA_CLIENT_ID`
- `ENTRA_CLIENT_SECRET`
- `ENTRA_TENANT_ID`

But `app/auth/entra_auth.py` reads:
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_TENANT_ID`

**Fix:** Either rename the Azure App Settings to `AZURE_*`, or update `entra_auth.py` to read `ENTRA_*` names. Pick one — just make them match. Updating the code to read both (with fallback) is safest:
```python
CLIENT_ID = os.environ.get('AZURE_CLIENT_ID') or os.environ.get('ENTRA_CLIENT_ID')
```

### 3. Flask secret key not set

`dashboard.py` never sets `app.secret_key`. Flask sessions (used by MSAL auth for OAuth state) require a secret key. Without it, session operations will fail silently or crash.

**Fix:** Add `app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(32).hex())` or pull from Key Vault.

### 4. Startup script PYTHONPATH issue

`startup.sh` sets `PYTHONPATH=/home/site/wwwroot:$PYTHONPATH` and runs `gunicorn app.delivery.dashboard:app`. The zip deploy creates this structure:
```
/home/site/wwwroot/
  app/
    delivery/dashboard.py
    sources/crm_db.py
    db.py
    models.py
  scripts/
  startup.sh
```

But `dashboard.py` does `sys.path.insert(0, APP_DIR)` where APP_DIR = the `app/` directory. Imports like `from sources.crm_db import ...` and `from db import init_db` resolve relative to `app/`. This should work, but verify by checking the actual deployed file structure.

---

## Debugging Steps

1. **Check app logs first:**
```bash
az webapp log tail --resource-group rg-arec-crm --name arec-crm-app --lines 100
```

If that doesn't show enough, enable full logging:
```bash
az webapp log config --resource-group rg-arec-crm --name arec-crm-app --application-logging filesystem --level verbose --detailed-error-messages true
```

Then check:
```bash
az webapp log download --resource-group rg-arec-crm --name arec-crm-app --log-file /tmp/logs.zip
unzip /tmp/logs.zip -d /tmp/logs
cat /tmp/logs/LogFiles/Application/*.log
```

2. **Verify Azure App Settings match code expectations:**
```bash
az webapp config appsettings list --resource-group rg-arec-crm --name arec-crm-app --query "[].{name:name}" -o table
```

Compare against what the code reads:
- `DATABASE_URL` — used by `app/db.py`
- `AZURE_CLIENT_ID` — used by `app/auth/entra_auth.py`
- `AZURE_CLIENT_SECRET` — used by `app/auth/entra_auth.py`
- `AZURE_TENANT_ID` — used by `app/auth/entra_auth.py`
- `ANTHROPIC_API_KEY` — used by `app/briefing/brief_synthesizer.py`

3. **Apply fixes, push, and verify:**
After fixing the issues, push to `azure-migration`. The GitHub Actions workflow will run tests and deploy automatically. Then check logs again to confirm the app starts.

4. **Smoke test:**
```bash
curl -s -o /dev/null -w "%{http_code}" https://arec-crm-app.azurewebsites.net/
```
- 302 = good (redirect to SSO or /crm)
- 500/503 = still broken, check logs

---

## Key Files

| File | What to check |
|------|---------------|
| `app/delivery/dashboard.py` | Missing `db.init_app(app)` call, missing `app.secret_key` |
| `app/auth/entra_auth.py` | Env var names (`AZURE_*` vs `ENTRA_*`) |
| `app/db.py` | `init_app()` and `init_db()` — these must be called before any DB operation |
| `app/sources/crm_db.py` | All 56 functions depend on `db.SessionLocal` being initialized |
| `startup.sh` | PYTHONPATH setup, gunicorn command |
| `.github/workflows/azure-deploy.yml` | Deployment package structure (zip contents) |
| `app/requirements.txt` | All deps: flask, sqlalchemy, psycopg2-binary, msal, gunicorn, etc. |

---

## Azure Resources

| Resource | Value |
|----------|-------|
| Resource Group | `rg-arec-crm` |
| Web App | `arec-crm-app` |
| PostgreSQL Server | `arec-crm-db` (centralus) |
| Database | `arec_crm` |
| Key Vault | `kv-arec-crm` |
| Entra Client ID | `94270ca6-e1e1-4f0f-bdd0-f8df2cbb3750` |
| Tenant ID | `ebd42ab2-7f1c-4d40-8b44-f5ecc51d2659` |

---

## Critical Rules

- **NEVER modify `main` branch.** All work on `azure-migration` only.
- **Import swaps are branch-only.** `crm_reader` → `crm_db` only on azure-migration.
- **After fixing, push to azure-migration** — CI will auto-deploy.
- **Check logs after deploy** to confirm startup succeeds.
