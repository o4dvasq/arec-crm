# Deploy to Azure - GitHub Actions

**Current Branch:** `azure-migration`
**Commits Ready:** All Step 0-12 work committed
**Deployment Method:** GitHub Actions (automatic)

---

## Step 1: Create Azure Service Principal for GitHub Actions

Run this command to create credentials for GitHub Actions:

```bash
az ad sp create-for-rbac \
  --name "github-arec-crm-deploy" \
  --role contributor \
  --scopes /subscriptions/064d6342-5dc5-424e-802f-53ff17bc02be/resourceGroups/rg-arec-crm \
  --sdk-auth
```

**Expected output:** A JSON object like this:

```json
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "clientSecret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "subscriptionId": "064d6342-5dc5-424e-802f-53ff17bc02be",
  "tenantId": "ebd42ab2-7f1c-4d40-8b44-f5ecc51d2659",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  "activeDirectoryGraphResourceId": "https://graph.windows.net/",
  "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
  "galleryEndpointUrl": "https://gallery.azure.com/",
  "managementEndpointUrl": "https://management.core.windows.net/"
}
```

**⚠️ COPY THIS ENTIRE JSON OUTPUT - You'll need it in Step 2**

---

## Step 2: Add GitHub Secret

1. **Open GitHub repository settings:**
   ```
   https://github.com/o4dvasq/arec-crm/settings/secrets/actions
   ```

2. **Click "New repository secret"**

3. **Create the secret:**
   - **Name:** `AZURE_CREDENTIALS`
   - **Value:** Paste the entire JSON from Step 1

4. **Click "Add secret"**

---

## Step 3: Configure Azure App Service Settings

Set the environment variables in Azure App Service:

```bash
# Generate Flask secret key
FLASK_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Set all app settings
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
    FLASK_SECRET_KEY="$FLASK_SECRET" \
    FLASK_DEBUG="false" \
    SCM_DO_BUILD_DURING_DEPLOYMENT="true"
```

---

## Step 4: Set Startup Command

```bash
az webapp config set \
  --resource-group rg-arec-crm \
  --name arec-crm-app \
  --startup-file /home/site/wwwroot/startup.sh
```

---

## Step 5: Push to GitHub and Deploy

Push the azure-migration branch to trigger deployment:

```bash
git push origin azure-migration
```

**This will:**
1. Push all commits to GitHub
2. Automatically trigger the GitHub Actions workflow
3. Run all tests (75+ tests)
4. Create deployment package
5. Deploy to Azure App Service
6. Restart the app

---

## Step 6: Monitor Deployment

**Watch GitHub Actions:**

Visit: https://github.com/o4dvasq/arec-crm/actions

You'll see a workflow run called "Deploy to Azure App Service" starting immediately.

**Steps to watch for:**
- ✅ Checkout code
- ✅ Set up Python
- ✅ Install dependencies
- ✅ Run tests
- ✅ Create deployment package
- ✅ Azure Login
- ✅ Deploy to Azure Web App
- ✅ Restart App Service

**Expected time:** 5-10 minutes

---

## Step 7: Check Deployment Logs

Once deployment completes, check app logs:

```bash
az webapp log tail \
  --resource-group rg-arec-crm \
  --name arec-crm-app
```

**Look for:**
- ✅ "Starting AREC CRM on Azure App Service..."
- ✅ "Starting Gunicorn..."
- ✅ Gunicorn workers starting
- ✅ No Python errors

**Press Ctrl+C to exit when satisfied**

---

## Step 8: Smoke Test the Deployment

### Access the App

Visit: **https://arec-crm-app.azurewebsites.net/crm**

**Expected:** Redirect to Microsoft login page

### Test SSO Login

Log in with your Microsoft credentials:
- Email: `oscar@avilacapllc.com` or `tony@avilacapllc.com`

**Expected:** Redirect back to CRM pipeline view

### Test Core Functionality

Run through this checklist:

- [ ] **Pipeline loads:** All prospects visible in table
- [ ] **Org detail:** Click on "UTIMCO" → see org detail page
- [ ] **Prospect detail:** Click a prospect → see prospect detail page
- [ ] **Inline edit:** Click a prospect field → edit → save → refresh page → change persists
- [ ] **People page:** Navigate to `/crm/people` → contacts listed
- [ ] **Person detail:** Click a contact → see profile
- [ ] **Nav bar:** User name shows in top-right
- [ ] **Logout:** Click logout → returns to login page

### Check Data Integrity

Verify record counts:

```bash
# Connect to database
az postgres flexible-server connect \
  --name arec-crm-db \
  --admin-user arecadmin \
  --database-name arec_crm

# Inside psql, run:
# SELECT COUNT(*) FROM prospects;
# SELECT COUNT(*) FROM organizations;
# SELECT COUNT(*) FROM contacts;
```

**Expected:**
- Prospects: Should match local CRM count
- Organizations: Should match local CRM count
- Contacts: Should match local CRM count

---

## Troubleshooting

### If GitHub Actions Fails

**Check the workflow logs:**
- Go to https://github.com/o4dvasq/arec-crm/actions
- Click on the failed run
- Expand the failed step to see error

**Common issues:**
- Tests failing → Fix tests locally, commit, push again
- Authentication error → Verify AZURE_CREDENTIALS secret is correct
- Deployment error → Check Azure CLI has permissions

### If App Won't Start

**Check logs:**
```bash
az webapp log tail --resource-group rg-arec-crm --name arec-crm-app
```

**Common issues:**
- Missing environment variable → Check app settings
- Database connection error → Verify DATABASE_URL
- Import error → Check startup.sh path

### If SSO Doesn't Work

**Verify Entra ID settings:**
```bash
az webapp config appsettings list \
  --resource-group rg-arec-crm \
  --name arec-crm-app \
  --query "[?starts_with(name, 'AZURE_')]"
```

**Check redirect URI:**
- Should be: `https://arec-crm-app.azurewebsites.net/.auth/login/aad/callback`
- Update in Azure Portal → Entra ID → App registrations → AREC CRM → Redirect URIs

### If Database Connection Fails

**Check firewall rules:**
```bash
az postgres flexible-server firewall-rule list \
  --resource-group rg-arec-crm \
  --name arec-crm-db
```

**Ensure "AllowAzureServices" rule exists (0.0.0.0)**

---

## Success Criteria

When all these are true, deployment is successful:

- ✅ GitHub Actions workflow completed successfully
- ✅ App accessible at https://arec-crm-app.azurewebsites.net/crm
- ✅ SSO login works for all team members
- ✅ Pipeline table displays
- ✅ All CRUD operations work
- ✅ Inline editing persists
- ✅ No errors in application logs
- ✅ Database queries work

---

## After Successful Deployment

1. **Test with team:**
   - Have Tony and other team members log in
   - Verify they can access and use the app

2. **Monitor for 24 hours:**
   - Watch logs for errors
   - Check performance
   - Gather user feedback

3. **Run migration (when ready to cut over):**
   ```bash
   # Final data sync from local CRM to Azure
   python3 scripts/migrate_to_postgres.py
   ```

4. **Merge to main (after confirming stable):**
   ```bash
   git checkout main
   git merge azure-migration
   git push origin main
   ```

---

## Quick Commands Reference

**Watch logs:**
```bash
az webapp log tail --resource-group rg-arec-crm --name arec-crm-app
```

**Restart app:**
```bash
az webapp restart --resource-group rg-arec-crm --name arec-crm-app
```

**Check app status:**
```bash
az webapp show --resource-group rg-arec-crm --name arec-crm-app --query state
```

**View deployment history:**
```bash
az webapp deployment list --resource-group rg-arec-crm --name arec-crm-app --query "[0]"
```

---

## Ready to Deploy?

**Pre-flight checklist:**
- [ ] Azure service principal created (Step 1)
- [ ] AZURE_CREDENTIALS secret added to GitHub (Step 2)
- [ ] App settings configured in Azure (Step 3)
- [ ] Startup command set (Step 4)
- [ ] Current branch is `azure-migration`
- [ ] All changes committed

**If all checked, run:**

```bash
git push origin azure-migration
```

**Then monitor at:** https://github.com/o4dvasq/arec-crm/actions

Good luck! 🚀
