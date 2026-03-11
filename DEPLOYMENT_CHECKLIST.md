# AREC CRM Azure Deployment Checklist

**Phase I1: Database + Auth + Web App**
**Date:** March 11, 2026
**Branch:** `azure-migration`

---

## Pre-Deployment Checklist

### ✅ Azure Infrastructure (Oscar's Prerequisites - COMPLETED)

All Azure resources have been provisioned per SPEC § 10:

- [x] Resource Group: `rg-arec-crm` (westus2)
- [x] PostgreSQL Server: `arec-crm-db` (centralus)
- [x] Database: `arec_crm`
- [x] Key Vault: `kv-arec-crm` (centralus)
- [x] Entra App: Client ID `94270ca6-e1e1-4f0f-bdd0-f8df2cbb3750`
- [x] App Service: `arec-crm-app` (centralus)
- [x] Managed Identity assigned to App Service
- [x] Key Vault access granted to App Service

### 📋 Secrets Configuration

**Required secrets in Azure Key Vault:**

```bash
# Verify secrets exist
az keyvault secret list --vault-name kv-arec-crm --query "[].name"

# Expected secrets:
# - ANTHROPIC-API-KEY
# - DATABASE-URL
# - ENTRA-CLIENT-SECRET
```

**Generate Flask secret key:**

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 🔐 Local Testing Setup

**1. Create local .env file:**

```bash
cd ~/Dropbox/projects/arec-crm
cp app/.env.azure app/.env
```

**2. Edit `app/.env` with actual values:**

- `DATABASE_URL` → Get from Azure Portal or Key Vault
- `ANTHROPIC_API_KEY` → Get from Key Vault
- `AZURE_CLIENT_SECRET` → Get from Key Vault
- `FLASK_SECRET_KEY` → Generate with command above

**3. Install dependencies:**

```bash
python3 -m pip install -r app/requirements.txt
```

---

## Migration & Testing (Local)

### Step 1: Create Database Schema

```bash
python3 scripts/create_schema.py
```

**Expected output:**
```
✓ Schema created successfully
✓ Seeded 9 pipeline stages
✓ Seeded 8 team members
```

### Step 2: Migrate Data from Markdown

```bash
python3 scripts/migrate_to_postgres.py
```

**Expected output:**
```
✓ Migrated 129 organizations
✓ Migrated 3 offerings
✓ Migrated 161 prospects
✓ Migration complete!
```

### Step 3: Verify Migration

```bash
python3 scripts/verify_migration.py
```

**Expected output:**
```
✓ VERIFICATION PASSED
All record counts match and spot checks passed.
```

### Step 4: Run Tests

```bash
python3 -m pytest app/tests/ -v
```

**Expected:** At least 75 tests passing (72%+ pass rate)

### Step 5: Test Locally

```bash
cd app
python3 delivery/dashboard.py
```

Visit: http://localhost:3001/crm

**Test:**
- [ ] App loads without errors
- [ ] Pipeline table displays
- [ ] Click on an org → org detail page loads
- [ ] Click on a prospect → prospect detail page loads
- [ ] Edit a prospect field (inline)
- [ ] Changes persist after refresh

**Note:** SSO will not work locally unless you configure Entra ID redirect URI for localhost.

---

## Deployment to Azure

### Option A: GitHub Actions (Recommended)

**1. Set up GitHub secrets:**

```bash
# Create Azure service principal for GitHub Actions
az ad sp create-for-rbac \
  --name "github-arec-crm-deploy" \
  --role contributor \
  --scopes /subscriptions/064d6342-5dc5-424e-802f-53ff17bc02be/resourceGroups/rg-arec-crm \
  --sdk-auth

# Copy the entire JSON output
```

**2. Add to GitHub repository secrets:**

Go to: https://github.com/o4dvasq/arec-crm/settings/secrets/actions

Add secret:
- Name: `AZURE_CREDENTIALS`
- Value: (paste the JSON from above)

**3. Push to trigger deployment:**

```bash
git push origin azure-migration
```

**4. Monitor deployment:**

Go to: https://github.com/o4dvasq/arec-crm/actions

Watch the "Deploy to Azure App Service" workflow.

---

### Option B: Manual ZIP Deploy

**1. Create deployment package:**

```bash
cd ~/Dropbox/projects/arec-crm

zip -r deploy.zip \
  app/ \
  scripts/ \
  startup.sh \
  -x "*.pyc" \
  -x "**/__pycache__/*" \
  -x "**/tests/*" \
  -x "**/.env*"
```

**2. Deploy via Azure CLI:**

```bash
az webapp deployment source config-zip \
  --resource-group rg-arec-crm \
  --name arec-crm-app \
  --src deploy.zip
```

**3. Wait for deployment to complete:**

```bash
az webapp deployment list \
  --resource-group rg-arec-crm \
  --name arec-crm-app \
  --query "[0].{status:status, complete_time:end_time}"
```

---

## Post-Deployment Configuration

### 1. Configure App Settings

**Set environment variables via Azure Portal:**

Configuration → Application settings → New application setting

Or via CLI:

```bash
az webapp config appsettings set \
  --resource-group rg-arec-crm \
  --name arec-crm-app \
  --settings \
    DATABASE_URL="@Microsoft.KeyVault(VaultName=kv-arec-crm;SecretName=DATABASE-URL)" \
    ANTHROPIC_API_KEY="@Microsoft.KeyVault(VaultName=kv-arec-crm;SecretName=ANTHROPIC-API-KEY)" \
    AZURE_CLIENT_ID="94270ca6-e1e1-4f0f-bdd0-f8df2cbb3750" \
    AZURE_CLIENT_SECRET="@Microsoft.KeyVault(VaultName=kv-arec-crm;SecretName=ENTRA-CLIENT-SECRET)" \
    AZURE_TENANT_ID="ebd42ab2-7f1c-4d40-8b44-f5ecc51d2659" \
    AZURE_AUTHORITY="https://login.microsoftonline.com/ebd42ab2-7f1c-4d40-8b44-f5ecc51d2659" \
    AZURE_REDIRECT_URI="https://arec-crm-app.azurewebsites.net/.auth/login/aad/callback" \
    FLASK_SECRET_KEY="<paste_generated_secret_key>" \
    FLASK_DEBUG="false" \
    SCM_DO_BUILD_DURING_DEPLOYMENT="true"
```

### 2. Set Startup Command

**Via Portal:**

Configuration → General settings → Startup Command:
```
/home/site/wwwroot/startup.sh
```

**Via CLI:**

```bash
az webapp config set \
  --resource-group rg-arec-crm \
  --name arec-crm-app \
  --startup-file /home/site/wwwroot/startup.sh
```

### 3. Restart App Service

```bash
az webapp restart \
  --resource-group rg-arec-crm \
  --name arec-crm-app
```

---

## Smoke Testing (Production)

### 1. Access the App

Visit: https://arec-crm-app.azurewebsites.net/crm

**Expected:** Redirect to Microsoft login page

### 2. Authenticate

Log in with: `oscar@avilacapllc.com` or `tony@avilacapllc.com`

**Expected:** Redirect back to CRM pipeline view

### 3. Test Core Functionality

- [ ] **Pipeline loads:** All prospects visible
- [ ] **Org detail:** Click org → see contacts, prospects, interactions
- [ ] **Prospect detail:** Click prospect → see brief, notes, emails, tasks
- [ ] **Inline edit:** Update a prospect field → change persists
- [ ] **Brief synthesis:** Click "Refresh Brief" → Claude generates new brief
- [ ] **People page:** Navigate to `/crm/people` → contacts listed
- [ ] **Person detail:** Click contact → see profile
- [ ] **Logout:** Top-right logout → returns to login

### 4. Check Logs

```bash
az webapp log tail \
  --resource-group rg-arec-crm \
  --name arec-crm-app
```

**Look for:**
- No Python errors
- Successful database connections
- Gunicorn workers starting

### 5. Verify Data

**Check record counts:**

```bash
# Connect to database via Azure Portal or psql
# Run: SELECT COUNT(*) FROM prospects;
# Expected: 161 (or current count from migration)
```

---

## Troubleshooting

### App won't start

**Check logs:**
```bash
az webapp log tail --resource-group rg-arec-crm --name arec-crm-app
```

**Common issues:**
- Missing environment variable → Check App Settings
- Database connection error → Verify DATABASE_URL and firewall rules
- Import error → Check startup.sh working directory

### SSO not working

**Check:**
- Entra app redirect URI matches: `https://arec-crm-app.azurewebsites.net/.auth/login/aad/callback`
- Client ID and secret are correct
- Tenant ID matches Avila Capital LLC tenant

### Database connection issues

**Check:**
- App Service IP allowed in PostgreSQL firewall
- DATABASE_URL format correct
- Database exists and is accessible

**Test connection:**
```bash
# From App Service SSH console
python3 -c "import os; from sqlalchemy import create_engine; engine = create_engine(os.environ['DATABASE_URL']); print(engine.connect())"
```

### Secrets not loading from Key Vault

**Check:**
- App Service managed identity is enabled
- Managed identity has "Key Vault Secrets User" role
- App Settings use correct Key Vault reference format:
  `@Microsoft.KeyVault(VaultName=kv-arec-crm;SecretName=SECRET-NAME)`

---

## Rollback Plan

If deployment fails or issues are discovered:

### 1. Stop the Azure App

```bash
az webapp stop \
  --resource-group rg-arec-crm \
  --name arec-crm-app
```

### 2. Local CRM continues running

The `main` branch remains unchanged. Oscar's local CRM on laptop continues to work.

### 3. Fix and redeploy

Make fixes on `azure-migration` branch, test locally, then redeploy.

---

## Success Criteria

- [ ] All 8 team members can log in via SSO
- [ ] Pipeline table displays all 161 prospects
- [ ] Org detail pages load correctly
- [ ] Inline editing works and persists
- [ ] Brief synthesis generates new briefs
- [ ] No errors in application logs
- [ ] Database queries perform well (<500ms)
- [ ] All acceptance criteria from SPEC § 8 met

---

## Next Steps After Successful Deployment

1. **Monitor for 24 hours:** Check logs, performance, user feedback
2. **Run final data sync:** If stable, run migration script one more time for latest data
3. **Merge to main:** `git merge azure-migration` (after confirming stability)
4. **Retire local CRM:** Switch team to Azure-only
5. **Phase I2:** Begin intelligence pipeline implementation

---

## Contact

**Issues during deployment:** See TROUBLESHOOTING section above
**Questions:** Review DEPLOYMENT.md and SPEC_phase-I1-database-auth-webapp.md
