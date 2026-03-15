# SPEC: Azure Deploy (Branch 3 of 4)

**Project:** arec-crm
**Date:** 2026-03-14
**Status:** Ready for implementation

---

## Objective

Deploy the working postgres-local app to Azure App Service with zero application code changes. The app already works locally against Azure Postgres (Branch 2 verified this). This branch adds only deployment infrastructure: a startup script, a GitHub Actions workflow, and App Service configuration. No new features, no auth, no multi-user.

---

## Context for Claude Code

You have **zero context** from the design conversation. Here is what you need to know:

We're following a 4-branch incremental migration:

| Branch | Status | What changed |
|--------|--------|-------------|
| 1. `postgres-local` | Done | Replaced markdown backend with local Postgres |
| 2. `azure-db` | Done | Verified local app works against Azure Postgres |
| **3. `azure-deploy`** (this spec) | **Now** | Deploy app to Azure App Service — infra only |
| 4. `multi-user` | Next | Entra SSO, roles, Graph API |

The previous `azure-migration` branch attempted all 4 at once and became undebuggable. We're doing them one at a time.

**The app is single-user, no auth.** Anyone who can reach the URL can use it. Auth comes in Branch 4. This is acceptable because the app was already working this way locally.

---

## Starting Point

Branch off `azure-db` (which is identical to `postgres-local` code-wise, just verified against Azure Postgres).

```bash
git checkout azure-db
git checkout -b azure-deploy
```

---

## Scope

### In Scope

1. **`startup.sh`** — Azure App Service startup script
2. **`.github/workflows/azure-deploy.yml`** — GitHub Actions CI/CD
3. **`Procfile`** or equivalent gunicorn config
4. **App Service environment variable documentation**
5. **Verification that the deployed app loads and functions**

### Explicitly Out of Scope

- **No application code changes** — no new routes, no new models, no import changes
- **No authentication** — no Entra ID, no MSAL, no `@login_required`, no User model
- **No `entra_auth.py`** — doesn't exist on this branch
- **No admin blueprint** — doesn't exist on this branch
- **No `ms_graph.py`** — doesn't exist on this branch
- **No schema changes** — `models.py` is unchanged from Branch 1
- **No `create_schema.py` or `migrate_to_postgres.py`** — the Azure database was already seeded in Branch 2. The seed script exists at `scripts/seed_from_markdown.py` but doesn't need to run on Azure (data is already there)

---

## File 1: `startup.sh`

This runs when Azure App Service boots the container. It must:

1. Activate the Oryx-built virtual environment (Azure builds Python apps using Oryx)
2. Install/sync dependencies from `requirements.txt` (handles stale antenv)
3. Run `auto_migrate` against the production database (additive-only, safe)
4. Start gunicorn

**IMPORTANT:** This is a simpler version than the old azure-migration startup.sh. No auth init, no schema creation, no user provisioning.

```bash
#!/bin/bash
set -e

echo "=== AREC CRM Startup ==="

# Activate Oryx virtual environment
if [ -d "/home/site/wwwroot/antenv" ]; then
    echo "Activating virtual environment..."
    source /home/site/wwwroot/antenv/bin/activate
fi

# Ensure dependencies are current (handles stale antenv after code deploy)
echo "Installing/syncing dependencies..."
pip install -r /home/site/wwwroot/app/requirements.txt --quiet 2>&1 | tail -5

# Run auto-migrate (additive-only DDL — safe to run every boot)
echo "Running auto-migrate..."
cd /home/site/wwwroot
PYTHONPATH=/home/site/wwwroot/app python3 -c "
import db as db_module
from auto_migrate import auto_migrate
db_module.init_db()
auto_migrate(db_module.engine)
print('Auto-migrate complete.')
"

# Start gunicorn
echo "Starting gunicorn on port ${PORT:-8000}..."
cd /home/site/wwwroot/app
exec gunicorn delivery.dashboard:app \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
```

**Notes:**
- `delivery.dashboard:app` — gunicorn needs the module path to the Flask app object. The Flask app is `app` defined in `app/delivery/dashboard.py`. Since we `cd` into `/home/site/wwwroot/app`, the module path is `delivery.dashboard`.
- `PYTHONPATH` must include the `app/` directory so imports like `from sources.crm_db import ...` resolve.
- `--workers 4` is fine for the B1 tier (1 core, 1.75GB RAM). Each worker uses ~50-80MB.
- `--timeout 120` — brief synthesis calls Claude API, which can take 30-60 seconds.

---

## File 2: `.github/workflows/azure-deploy.yml`

GitHub Actions workflow for CI/CD. Triggers on push to `azure-deploy` branch.

```yaml
name: Deploy to Azure App Service

on:
  push:
    branches: [azure-deploy]
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r app/requirements.txt

      - name: Run tests
        run: |
          cd app
          python3 -m pytest tests/ --ignore=tests/test_tasks_api_key.py -v --tb=short

  deploy:
    runs-on: ubuntu-latest
    needs: test
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Create deployment package
        run: |
          zip -r deploy.zip \
            app/ \
            scripts/ \
            startup.sh \
            crm/ \
            memory/ \
            meeting-summaries/ \
            TASKS.md \
            -x "app/tests/*" \
            -x "app/__pycache__/*" \
            -x "**/__pycache__/*" \
            -x "*.pyc" \
            -x "app/.env"

      - name: Login to Azure
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Deploy to App Service
        uses: azure/webapps-deploy@v3
        with:
          app-name: arec-crm-app
          package: deploy.zip

      - name: Restart App Service
        run: az webapp restart --name arec-crm-app --resource-group rg-arec-crm

      - name: Verify deployment (wait for startup)
        run: |
          echo "Waiting 30s for app to start..."
          sleep 30
          STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://arec-crm-app.azurewebsites.net/crm/ --max-time 30)
          echo "HTTP status: $STATUS"
          if [ "$STATUS" -ge 200 ] && [ "$STATUS" -lt 400 ]; then
            echo "Deployment verified successfully!"
          else
            echo "WARNING: App returned HTTP $STATUS — check logs"
            az webapp log tail --name arec-crm-app --resource-group rg-arec-crm --lines 50
            exit 1
          fi
```

**Notes:**
- The `crm/`, `memory/`, `meeting-summaries/`, and `TASKS.md` are included in the deploy package because `relationship_brief.py` reads from `memory/people/` and `meeting-summaries/` for brief synthesis context. These are read-only on the server.
- `secrets.AZURE_CREDENTIALS` must be configured in GitHub repo settings. This is a JSON blob from `az ad sp create-for-rbac`.
- No auth check in the verification step — the app has no auth on this branch.

---

## File 3: App Service Configuration

These settings must be configured on the Azure App Service. They are NOT in code — they're set via Azure Portal or CLI.

### Environment Variables (App Settings)

Set via `az webapp config appsettings set`:

```bash
az webapp config appsettings set \
  --name arec-crm-app \
  --resource-group rg-arec-crm \
  --settings \
    DATABASE_URL="@Microsoft.KeyVault(VaultName=kv-arec-crm;SecretName=DATABASE-URL)" \
    ANTHROPIC_API_KEY="@Microsoft.KeyVault(VaultName=kv-arec-crm;SecretName=ANTHROPIC-API-KEY)" \
    SCM_DO_BUILD_DURING_DEPLOYMENT=true \
    FLASK_DEBUG=false
```

**Key Vault secrets required:**
| Secret Name | Value |
|-------------|-------|
| `DATABASE-URL` | `postgresql://arecadmin:<PASSWORD>@arec-crm-db.postgres.database.azure.com:5432/arec_crm?sslmode=require` |
| `ANTHROPIC-API-KEY` | Claude API key for brief synthesis |

These already exist in Key Vault from the previous azure-migration deployment.

### Startup Command

```bash
az webapp config set \
  --name arec-crm-app \
  --resource-group rg-arec-crm \
  --startup-file startup.sh
```

### General Config

```bash
az webapp config set \
  --name arec-crm-app \
  --resource-group rg-arec-crm \
  --linux-fx-version "PYTHON|3.12" \
  --always-on true
```

---

## Constraints

1. **No application code changes.** If you find yourself editing `crm_db.py`, `models.py`, `dashboard.py`, `crm_blueprint.py`, or any template, stop. The app already works against Azure Postgres from Branch 2. If something breaks on Azure, it's a deployment/infra issue, not a code issue.

2. **`auto_migrate` runs on every boot.** This is safe because it's additive-only (create tables, add columns, add indexes — never drops). It ensures the schema stays in sync if we add models later.

3. **The database is already seeded.** Do NOT run `seed_from_markdown.py` from startup.sh. The data was seeded in Branch 2. Running the seed script again from Azure could create duplicates depending on idempotency guarantees.

4. **No authentication on this branch.** The app is open to anyone who can reach the URL. The App Service does have network-level restrictions (Azure VNET or IP whitelisting if configured), but the app itself has no auth. This is intentional — auth is Branch 4.

5. **The `app/` directory is the WSGI root.** Gunicorn runs inside `app/` and the module path is `delivery.dashboard:app`. All imports in the codebase use paths relative to `app/` (e.g., `from sources.crm_db import ...`).

6. **`PYTHONPATH` must include `app/`.** The startup.sh sets this for the auto-migrate step. Gunicorn handles it by running from the `app/` directory.

---

## Verification Steps

After deployment, verify from your Mac:

1. **App loads:** `curl -s -o /dev/null -w "%{http_code}" https://arec-crm-app.azurewebsites.net/crm/` returns 200
2. **Pipeline renders:** Open `https://arec-crm-app.azurewebsites.net/crm/` in browser — should show all prospects
3. **Prospect detail works:** Click into any prospect — fields, contacts, interactions render
4. **Edit works:** Change a prospect's stage or notes, save, refresh — change persists
5. **Brief synthesis works:** Click "Generate Brief" on a prospect — Claude API is called, narrative appears
6. **Org detail works:** Click into an org — contacts, prospects, domain listed
7. **Export works:** Hit `/crm/api/export` — downloads Excel file
8. **Logs look clean:** `az webapp log tail --name arec-crm-app --resource-group rg-arec-crm` shows no errors on boot

---

## Rollback

If deployment fails:

```bash
az webapp deployment list-publishing-profiles \
  --name arec-crm-app \
  --resource-group rg-arec-crm

az webapp config set \
  --name arec-crm-app \
  --resource-group rg-arec-crm \
  --startup-file ""

az webapp restart --name arec-crm-app --resource-group rg-arec-crm
```

Or just push a revert commit — GitHub Actions will redeploy.

---

## Files Created/Modified

| File | Action | Purpose |
|------|--------|---------|
| `startup.sh` | **Create** | Azure App Service startup (activate venv, pip install, auto-migrate, gunicorn) |
| `.github/workflows/azure-deploy.yml` | **Create** | CI/CD: test → package → deploy → verify |
| `CLAUDE.md` | **Edit** | Add deployment section with Azure URLs and log commands |

**No application code files are modified.**

---

## Debugging Checklist

If the deployed app doesn't work, check in this order:

1. **Startup logs:** `az webapp log tail --name arec-crm-app --resource-group rg-arec-crm` — look for import errors, missing modules
2. **Environment variables:** `az webapp config appsettings list --name arec-crm-app --resource-group rg-arec-crm` — confirm DATABASE_URL and ANTHROPIC_API_KEY are set
3. **Key Vault access:** The App Service's managed identity needs "Key Vault Secrets User" role on `kv-arec-crm`
4. **Database connectivity:** The App Service's outbound IPs must be allowed through the Azure Postgres firewall. Check: `az webapp show --name arec-crm-app --resource-group rg-arec-crm --query "outboundIpAddresses"` and compare to firewall rules
5. **PYTHONPATH:** If imports fail, the issue is likely that gunicorn isn't running from the right directory. The startup.sh `cd` into `app/` before exec'ing gunicorn
6. **Oryx build:** If pip install fails, check that `SCM_DO_BUILD_DURING_DEPLOYMENT=true` is set — this tells Oryx to build a virtual environment during deployment
