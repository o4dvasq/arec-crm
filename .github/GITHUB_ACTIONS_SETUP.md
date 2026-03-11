# GitHub Actions Deployment Setup

This guide explains how to set up automated deployment to Azure App Service using GitHub Actions.

---

## Overview

The workflow in `.github/workflows/azure-deploy.yml` automatically:

1. Runs tests on every push to `azure-migration`
2. Creates a deployment package
3. Deploys to Azure App Service
4. Restarts the app

---

## One-Time Setup

### Step 1: Create Azure Service Principal

Create a service principal with contributor access to the resource group:

```bash
az ad sp create-for-rbac \
  --name "github-arec-crm-deploy" \
  --role contributor \
  --scopes /subscriptions/064d6342-5dc5-424e-802f-53ff17bc02be/resourceGroups/rg-arec-crm \
  --sdk-auth
```

This will output JSON like:

```json
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "clientSecret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "subscriptionId": "064d6342-5dc5-424e-802f-53ff17bc02be",
  "tenantId": "ebd42ab2-7f1c-4d40-8b44-f5ecc51d2659",
  ...
}
```

**Copy the entire JSON output.**

### Step 2: Add GitHub Repository Secret

1. Go to: https://github.com/o4dvasq/arec-crm/settings/secrets/actions

2. Click **"New repository secret"**

3. Create secret:
   - **Name:** `AZURE_CREDENTIALS`
   - **Value:** Paste the entire JSON from Step 1

4. Click **"Add secret"**

---

## Usage

### Automatic Deployment

Push to the `azure-migration` branch:

```bash
git push origin azure-migration
```

The workflow will automatically:
- Run all tests
- Deploy to Azure if tests pass
- Restart the app

### Manual Deployment

Trigger manually from GitHub:

1. Go to: https://github.com/o4dvasq/arec-crm/actions
2. Select "Deploy to Azure App Service"
3. Click "Run workflow"
4. Select branch: `azure-migration`
5. Click "Run workflow"

---

## Monitoring

### View Deployment Progress

1. Go to: https://github.com/o4dvasq/arec-crm/actions
2. Click on the latest workflow run
3. Watch the deployment steps in real-time

### Deployment Steps

The workflow executes in this order:

1. **Checkout code** — Downloads the repository
2. **Set up Python** — Installs Python 3.12
3. **Install dependencies** — Installs from requirements.txt
4. **Run tests** — Runs pytest (deployment fails if tests fail)
5. **Create deployment package** — Creates deploy.zip
6. **Azure Login** — Authenticates with service principal
7. **Deploy to Azure Web App** — Uploads and deploys the package
8. **Restart App Service** — Restarts the app to load new code
9. **Check deployment status** — Displays the app URL

### Check Deployment Logs

After deployment completes, check app logs:

```bash
az webapp log tail \
  --resource-group rg-arec-crm \
  --name arec-crm-app
```

---

## Troubleshooting

### Tests Fail in CI

**Symptom:** Workflow fails at "Run tests" step

**Solution:**
- Fix failing tests locally first
- Ensure all tests pass: `python3 -m pytest app/tests/ -v`
- Push again

### Authentication Error

**Symptom:** `Error: Login failed with Error: Service principal clientId is invalid`

**Solution:**
- Verify `AZURE_CREDENTIALS` secret is set correctly
- Re-create service principal if credentials expired
- Update the GitHub secret

### Deployment Fails

**Symptom:** "Deploy to Azure Web App" step fails

**Solution:**
- Check service principal has Contributor role on resource group
- Verify app name is correct: `arec-crm-app`
- Check Azure subscription is active

### App Doesn't Start After Deployment

**Symptom:** Deployment succeeds but app returns 500 errors

**Solution:**
- Check App Service logs (see above)
- Verify environment variables are set in Azure Portal
- Ensure startup.sh is executable and correct
- Check database connection string

---

## Workflow Configuration

### Triggers

The workflow runs on:

- **Push to `azure-migration`** — Automatic deployment
- **Manual trigger** — Via GitHub Actions UI

### Environment

- **Runner:** Ubuntu latest
- **Python:** 3.12
- **Deployment method:** ZIP deploy

### What Gets Deployed

Included in package:
- `app/` (Python application)
- `scripts/` (migration scripts)
- `startup.sh` (startup command)

Excluded:
- Tests (`**/tests/*`, `test_*.py`)
- Environment files (`**/.env*`)
- Python cache (`*.pyc`, `__pycache__`)

---

## Security Notes

### Service Principal Permissions

The service principal has **Contributor** access to the `rg-arec-crm` resource group only. It cannot:
- Access other resource groups
- Modify subscription settings
- Create new subscriptions
- Access secrets in Key Vault (unless explicitly granted)

### Secrets Management

- **NEVER** commit `AZURE_CREDENTIALS` to the repository
- Service principal credentials can be rotated without affecting the workflow (just update the secret)
- GitHub encrypts all secrets at rest

### Best Practices

1. Rotate service principal credentials every 90 days
2. Review GitHub Actions logs for suspicious activity
3. Use separate service principals for dev/staging/production
4. Limit service principal permissions to minimum required

---

## Disabling Auto-Deployment

To disable automatic deployment temporarily:

### Option 1: Disable Workflow

1. Go to: https://github.com/o4dvasq/arec-crm/actions/workflows/azure-deploy.yml
2. Click "⋯" (three dots)
3. Click "Disable workflow"

### Option 2: Edit Workflow

Comment out the `push` trigger in `.github/workflows/azure-deploy.yml`:

```yaml
on:
  # push:
  #   branches:
  #     - azure-migration
  workflow_dispatch:  # Manual trigger still works
```

---

## Support

**Workflow issues:** Check the Actions tab for error messages
**Azure issues:** Use Azure Portal or CLI to diagnose
**Code issues:** Fix locally and push again
