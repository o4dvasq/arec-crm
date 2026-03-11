# Step 12: Deployment Configuration Summary

**Date:** March 11, 2026
**Status:** Complete ✅

---

## Overview

Created comprehensive deployment infrastructure for Azure App Service, including automated GitHub Actions deployment, environment templates with actual Azure resource values, and complete documentation covering all deployment scenarios.

---

## Files Created

### 1. GitHub Actions Workflow

**`.github/workflows/azure-deploy.yml`** (50 lines)

Automated deployment pipeline:
- Triggers on push to `azure-migration` branch
- Runs all tests first (fail-fast)
- Creates deployment package (excludes tests, .env files)
- Authenticates with Azure via service principal
- Deploys to App Service via ZIP deploy
- Restarts app to load new code
- Displays deployment URL

**Benefits:**
- Automated deployment on every push
- Tests must pass before deploy
- No manual steps required
- Audit trail in GitHub Actions

### 2. Environment Template

**`app/.env.azure`** (24 lines)

Template with actual Azure resource values:
- Database URL format for arec-crm-db
- Entra Client ID: `94270ca6-e1e1-4f0f-bdd0-f8df2cbb3750`
- Tenant ID: `ebd42ab2-7f1c-4d40-8b44-f5ecc51d2659`
- Redirect URI: `https://arec-crm-app.azurewebsites.net/.auth/login/aad/callback`
- Key Vault name: `kv-arec-crm`
- Placeholder markers for secrets (to be filled from Key Vault)

**Usage:**
```bash
cp app/.env.azure app/.env
# Fill in actual secret values from Key Vault
```

### 3. Deployment Checklist

**`DEPLOYMENT_CHECKLIST.md`** (430 lines)

Complete deployment guide covering:

**Pre-Deployment:**
- Azure infrastructure verification
- Secrets configuration checklist
- Local testing setup

**Migration & Testing:**
- Step-by-step migration procedure
- Verification commands
- Local testing checklist

**Deployment Options:**
- GitHub Actions (automated)
- Manual ZIP deploy
- Post-deployment configuration

**Testing:**
- Smoke test checklist
- Core functionality validation
- Log monitoring

**Troubleshooting:**
- Common issues and solutions
- Rollback procedure
- Success criteria

### 4. Quick Reference Guide

**`DEPLOY_QUICK_REFERENCE.md`** (330 lines)

Command reference for common tasks:

**Sections:**
- Pre-flight checks
- Deploy (manual & GitHub Actions)
- Configuration management
- Monitoring commands
- Database operations
- Key Vault operations
- Troubleshooting shortcuts
- Resource IDs

**Use Cases:**
- Quick command lookup
- Copy-paste deployment commands
- Troubleshooting during incidents

### 5. GitHub Actions Setup

**`.github/GITHUB_ACTIONS_SETUP.md`** (230 lines)

Guide for setting up automated deployment:

**Topics:**
- Service principal creation
- GitHub secrets configuration
- Workflow usage (automatic & manual)
- Monitoring deployments
- Troubleshooting CI/CD
- Security best practices
- Permissions management

---

## Files Modified

### Updated Deployment Documentation

**`DEPLOYMENT.md`**

Fixed critical errors:
- App name: `arec-crm` → `arec-crm-app` (all references)
- URL: updated to `https://arec-crm-app.azurewebsites.net`
- Tenant ID: corrected to `ebd42ab2-7f1c-4d40-8b44-f5ecc51d2659`

### Updated .gitignore

**`.gitignore`**

Added exceptions:
- Allow `.env.azure` template (not actual secrets)
- Allow `.env.example` template
- Block `deploy.zip` and deployment artifacts
- Block test databases (`.db`, `.sqlite`)

---

## Existing Files Verified

### Startup Script

**`startup.sh`** (23 lines)

Already exists and correct:
- ✅ Executable permissions set
- ✅ Navigates to `/home/site/wwwroot/app`
- ✅ Starts Gunicorn with 4 workers
- ✅ Binds to `0.0.0.0:8000`
- ✅ Logs to stdout/stderr
- ✅ Runs `delivery.dashboard:app`

### Requirements

**`app/requirements.txt`**

Already includes all Azure dependencies:
- ✅ `sqlalchemy>=2.0.0` (database ORM)
- ✅ `psycopg2-binary>=2.9.9` (Postgres driver)
- ✅ `gunicorn>=21.2.0` (production server)
- ✅ `msal>=1.28.0` (Microsoft auth)
- ✅ `anthropic>=0.25.0` (Claude API)
- ✅ `flask>=3.0.0` (web framework)
- ✅ `pytest>=8.0.0` (testing)

---

## Deployment Options

### Option 1: GitHub Actions (Recommended)

**Setup (One-time):**
1. Create Azure service principal
2. Add `AZURE_CREDENTIALS` to GitHub secrets

**Usage:**
```bash
git push origin azure-migration
```

**Benefits:**
- Fully automated
- Tests run before deploy
- Audit trail
- Rollback capability

**See:** `.github/GITHUB_ACTIONS_SETUP.md`

### Option 2: Manual ZIP Deploy

**Usage:**
```bash
# Create package
zip -r deploy.zip app/ scripts/ startup.sh \
  -x "*.pyc" -x "**/__pycache__/*" -x "**/tests/*" -x "**/.env*"

# Deploy
az webapp deployment source config-zip \
  --resource-group rg-arec-crm \
  --name arec-crm-app \
  --src deploy.zip

# Restart
az webapp restart \
  --resource-group rg-arec-crm \
  --name arec-crm-app
```

**Benefits:**
- Direct control
- No GitHub dependency
- Works offline (with Azure CLI)

**See:** `DEPLOYMENT_CHECKLIST.md` and `DEPLOY_QUICK_REFERENCE.md`

---

## Environment Variables

### Required in Azure App Service

Set via Azure Portal → Configuration → Application Settings:

| Variable | Source | Format |
|----------|--------|--------|
| `DATABASE_URL` | Key Vault | `@Microsoft.KeyVault(...)` |
| `ANTHROPIC_API_KEY` | Key Vault | `@Microsoft.KeyVault(...)` |
| `AZURE_CLIENT_ID` | Plain value | `94270ca6-e1e1-4f0f-bdd0-f8df2cbb3750` |
| `AZURE_CLIENT_SECRET` | Key Vault | `@Microsoft.KeyVault(...)` |
| `AZURE_TENANT_ID` | Plain value | `ebd42ab2-7f1c-4d40-8b44-f5ecc51d2659` |
| `AZURE_AUTHORITY` | Plain value | `https://login.microsoftonline.com/{tenant}` |
| `AZURE_REDIRECT_URI` | Plain value | `https://arec-crm-app.azurewebsites.net/.auth/login/aad/callback` |
| `FLASK_SECRET_KEY` | Generate | Random 64-char hex string |
| `FLASK_DEBUG` | Plain value | `false` |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | Plain value | `true` |

**See:** `DEPLOYMENT_CHECKLIST.md` for setup commands

---

## Pre-Deployment Checklist

Before deploying, verify:

### Azure Resources
- [ ] PostgreSQL server running
- [ ] Database `arec_crm` created
- [ ] Key Vault accessible
- [ ] Secrets stored in Key Vault
- [ ] App Service created
- [ ] Managed Identity enabled
- [ ] Key Vault access granted

### Local Testing
- [ ] Schema created (`scripts/create_schema.py`)
- [ ] Data migrated (`scripts/migrate_to_postgres.py`)
- [ ] Migration verified (`scripts/verify_migration.py`)
- [ ] Tests passing (`pytest app/tests/`)
- [ ] Local app works (`python3 app/delivery/dashboard.py`)

### Configuration
- [ ] Environment variables set in Azure
- [ ] Startup command configured
- [ ] Entra ID redirect URI updated
- [ ] Service principal created (for GitHub Actions)

**See:** `DEPLOYMENT_CHECKLIST.md` for detailed checklist

---

## Post-Deployment Validation

After deployment, verify:

### Smoke Tests
- [ ] App accessible at https://arec-crm-app.azurewebsites.net/crm
- [ ] SSO login works
- [ ] Pipeline table loads
- [ ] Org detail page works
- [ ] Prospect detail page works
- [ ] Inline editing persists
- [ ] Brief synthesis works
- [ ] People pages load
- [ ] Logout works

### Monitoring
- [ ] Check app logs for errors
- [ ] Verify database connections
- [ ] Test with all 8 team members
- [ ] Confirm data integrity

**See:** `DEPLOYMENT_CHECKLIST.md` § Smoke Testing

---

## Troubleshooting Resources

### Quick Fixes

**App won't start:**
```bash
az webapp log tail --resource-group rg-arec-crm --name arec-crm-app
```

**Database connection error:**
```bash
# Check DATABASE_URL is set
az webapp config appsettings list --resource-group rg-arec-crm --name arec-crm-app --query "[?name=='DATABASE_URL']"
```

**SSO not working:**
```bash
# Verify Entra settings
az webapp config appsettings list --resource-group rg-arec-crm --name arec-crm-app --query "[?starts_with(name, 'AZURE_')]"
```

**See:**
- `DEPLOYMENT_CHECKLIST.md` § Troubleshooting
- `DEPLOY_QUICK_REFERENCE.md` § Troubleshooting

---

## Documentation Index

| Document | Purpose | Length |
|----------|---------|--------|
| `DEPLOYMENT_CHECKLIST.md` | Complete deployment guide | 430 lines |
| `DEPLOY_QUICK_REFERENCE.md` | Command reference | 330 lines |
| `.github/GITHUB_ACTIONS_SETUP.md` | CI/CD setup guide | 230 lines |
| `DEPLOYMENT.md` | Detailed deployment procedures | 400+ lines |
| `app/.env.azure` | Environment template | 24 lines |

**Total documentation:** ~1,400 lines

---

## Security Notes

### Service Principal

Created for GitHub Actions:
- Contributor role on `rg-arec-crm` only
- Cannot access other resources
- Credentials stored in GitHub secrets (encrypted)
- Rotate every 90 days

### Secrets Management

- All secrets in Azure Key Vault
- App Service uses Managed Identity to access
- No secrets in code or environment files
- `.env.azure` is a template (placeholders only)

### .gitignore

- Blocks all `.env` files except templates
- Blocks deployment artifacts (`deploy.zip`)
- Allows `.env.azure` and `.env.example` (templates only)

---

## Next Steps

### Step 13: Deploy and Smoke Test

**Ready to deploy:**
1. Follow `DEPLOYMENT_CHECKLIST.md`
2. Run local migration and testing
3. Deploy via GitHub Actions or manual ZIP
4. Run smoke tests
5. Validate with team

**Expected outcome:**
- App running on Azure
- All 8 team members can log in
- All CRM functionality works
- Data matches local CRM

**Documentation ready:**
- Step-by-step guides
- Command references
- Troubleshooting help
- Quick fixes

---

## Summary

**Step 12 Deliverables:**
- ✅ GitHub Actions workflow
- ✅ Environment template with actual values
- ✅ Deployment checklist (430 lines)
- ✅ Quick reference guide (330 lines)
- ✅ GitHub Actions setup guide (230 lines)
- ✅ Updated deployment docs
- ✅ Security configuration
- ✅ Troubleshooting guides

**Status:** Deployment infrastructure complete and documented. Ready for Step 13.
