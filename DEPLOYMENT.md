# AREC CRM - Azure Deployment Guide

## Phase I1: Database + Auth + Web App Deployment

This guide covers deploying the AREC CRM to Azure App Service with PostgreSQL and Entra ID SSO.

---

## Prerequisites (Oscar's Manual Steps)

Before running the migration scripts, Oscar must complete the Azure Portal setup as documented in **SPEC_phase-I1-database-auth-webapp.md § 10**.

**Required Azure resources:**
1. Resource Group: `rg-arec-crm`
2. PostgreSQL Flexible Server: `arec-crm-db`
3. Database: `arec_crm`
4. Azure Key Vault: `kv-arec-crm`
5. Entra ID App Registration: AREC Intelligence Platform
6. App Service: `arec-crm`

Once complete, Oscar should provide:
- `DATABASE_URL` connection string
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET` (confirm it's in Key Vault)
- App Service name confirmation

---

## Local Testing (Before Migration)

### 1. Set up local environment

```bash
cd ~/Dropbox/projects/arec-crm
cp app/.env.azure app/.env

# Edit app/.env with actual Azure credentials:
# - DATABASE_URL (from PostgreSQL)
# - AZURE_CLIENT_ID (from Entra ID)
# - AZURE_CLIENT_SECRET (from Key Vault)
# - ANTHROPIC_API_KEY
```

### 2. Install dependencies

```bash
python3 -m pip install -r app/requirements.txt
```

### 3. Create schema

```bash
python3 scripts/create_schema.py
```

**Expected output:**
```
AREC CRM Schema Creation
==================================================
Dropping all tables...
Creating all tables...
✓ Schema created successfully
✓ Seeded 9 pipeline stages
✓ Seeded 8 team members

✓ Schema creation complete!
```

### 4. Migrate data

```bash
python3 scripts/migrate_to_postgres.py
```

**Expected output:**
```
AREC CRM Data Migration: Markdown → PostgreSQL
==================================================

Migrating organizations...
✓ Migrated 129 organizations

Migrating offerings...
✓ Migrated 3 offerings

Migrating contacts...
✓ Migrated X contacts

Migrating prospects...
✓ Migrated 161 prospects (Y skipped due to missing org/offering)

... (additional tables)

==================================================
MIGRATION SUMMARY
==================================================
  Organizations: 129
  Offerings: 3
  Contacts: X
  Prospects: 161
  ...
==================================================

✓ Migration complete!
```

### 5. Verify migration

```bash
python3 scripts/verify_migration.py
```

**Expected output:**
```
AREC CRM Migration Verification
======================================================================
Table                     Markdown        PostgreSQL      Status
----------------------------------------------------------------------
Organizations             129             129             ✓ PASS
Offerings                 3               3               ✓ PASS
Contacts                  X               X               ✓ PASS
Prospects                 161             161             ✓ PASS
...
----------------------------------------------------------------------

Spot-checking sample records...
  ✓ All organizations have types
  ✓ Org type normalization correct (HNWI / FO)
  ✓ Pipeline stages remapped correctly
  ✓ All prospects have organization and offering
  ✓ Currency stored as cents (sample: 5000000000)
  ✓ All 8 team members seeded
  ✓ All 9 pipeline stages seeded

======================================================================
✓ VERIFICATION PASSED

All record counts match and spot checks passed.
Migration successful!
```

### 6. Test locally

```bash
cd app
python3 delivery/dashboard.py
```

Visit: http://localhost:3001/crm

Test SSO login (requires Entra ID callback configured for localhost).

---

## Deployment to Azure

### 1. Deploy code

**Option A: GitHub Actions (Recommended)**

Set up GitHub Actions workflow (see `.github/workflows/azure-deploy.yml` template).

**Option B: Manual ZIP Deploy**

```bash
# From project root
cd ~/Dropbox/projects/arec-crm

# Create deployment package
zip -r deploy.zip app/ scripts/ startup.sh requirements.txt -x "*.pyc" -x "**/__pycache__/*"

# Deploy via Azure CLI
az webapp deployment source config-zip \
  --resource-group rg-arec-crm \
  --name arec-crm-app \
  --src deploy.zip
```

### 2. Configure environment variables

Set via Azure Portal or CLI:

```bash
az webapp config appsettings set \
  --resource-group rg-arec-crm \
  --name arec-crm-app \
  --settings \
    DATABASE_URL="@Microsoft.KeyVault(VaultName=kv-arec-crm;SecretName=DATABASE-URL)" \
    ANTHROPIC_API_KEY="@Microsoft.KeyVault(VaultName=kv-arec-crm;SecretName=ANTHROPIC-API-KEY)" \
    AZURE_CLIENT_ID="<from_entra_id>" \
    AZURE_CLIENT_SECRET="@Microsoft.KeyVault(VaultName=kv-arec-crm;SecretName=AZURE-CLIENT-SECRET)" \
    AZURE_TENANT_ID="ebd42ab2-7f1c-4d40-8b44-f5ecc51d2659" \
    FLASK_SECRET_KEY="<generate_random_key>" \
    FLASK_DEBUG="false" \
    SCM_DO_BUILD_DURING_DEPLOYMENT="true"
```

### 3. Set startup command

Via Azure Portal → Configuration → General settings → Startup Command:

```
/home/site/wwwroot/startup.sh
```

Or via CLI:

```bash
az webapp config set \
  --resource-group rg-arec-crm \
  --name arec-crm-app \
  --startup-file /home/site/wwwroot/startup.sh
```

### 4. Restart app

```bash
az webapp restart --resource-group rg-arec-crm --name arec-crm-app
```

### 5. Test deployment

Visit: https://arec-crm-app.azurewebsites.net/crm

Test:
- SSO login (should redirect to Microsoft login)
- Pipeline table loads
- Org detail page works
- Inline editing (update a prospect field)
- Brief synthesis (trigger AI brief generation)

---

## Monitoring & Logs

**View logs:**

```bash
az webapp log tail --resource-group rg-arec-crm --name arec-crm-app
```

**Check app health:**

```bash
az webapp show --resource-group rg-arec-crm --name arec-crm-app --query state
```

---

## Troubleshooting

### Database connection fails

- Verify `DATABASE_URL` is set correctly
- Check PostgreSQL firewall rules allow App Service IP
- Confirm SSL mode is `require` in connection string

### SSO redirect fails

- Verify `AZURE_REDIRECT_URI` matches Entra ID app registration
- Check `AZURE_CLIENT_ID` and `AZURE_CLIENT_SECRET` are correct
- Ensure all 8 users have been granted access to the app in Entra ID

### Import errors

- Verify all dependencies in `requirements.txt` are installed
- Check Python version is 3.12
- Review deployment logs for build errors

---

## Rollback Plan

If issues arise, the local CRM continues running unchanged. No cutover until Azure deployment is confirmed stable.

To rollback:
1. Stop Azure App Service
2. Continue using local CRM (`python3 app/delivery/dashboard.py`)
3. Investigate and fix issues
4. Re-deploy when ready

---

## Next Phases

After Phase I1 is stable:
- **Phase I2**: Intelligence pipeline (data processing)
- **Phase I3**: Intelligence UI / timeline
- **Phase I4**: Briefing engine
- **Phase I5**: Meeting transcript processing

See SPEC for details.
