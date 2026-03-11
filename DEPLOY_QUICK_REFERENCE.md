# Azure Deployment Quick Reference

**App:** arec-crm-app
**Resource Group:** rg-arec-crm
**URL:** https://arec-crm-app.azurewebsites.net

---

## Pre-Flight

```bash
# Verify you're on azure-migration branch
git branch

# Ensure all tests pass
python3 -m pytest app/tests/ -v

# Verify Azure CLI logged in
az account show
```

---

## Deploy (Manual)

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

---

## Deploy (GitHub Actions)

```bash
git push origin azure-migration
```

Monitor at: https://github.com/o4dvasq/arec-crm/actions

---

## Configuration

### View Current Settings

```bash
az webapp config appsettings list \
  --resource-group rg-arec-crm \
  --name arec-crm-app \
  --query "[].{name:name, value:value}" \
  --output table
```

### Set App Settings

```bash
az webapp config appsettings set \
  --resource-group rg-arec-crm \
  --name arec-crm-app \
  --settings KEY="value"
```

### Set Startup Command

```bash
az webapp config set \
  --resource-group rg-arec-crm \
  --name arec-crm-app \
  --startup-file /home/site/wwwroot/startup.sh
```

---

## Monitoring

### Stream Logs

```bash
az webapp log tail \
  --resource-group rg-arec-crm \
  --name arec-crm-app
```

### Download Logs

```bash
az webapp log download \
  --resource-group rg-arec-crm \
  --name arec-crm-app \
  --log-file app_logs.zip
```

### Check Status

```bash
az webapp show \
  --resource-group rg-arec-crm \
  --name arec-crm-app \
  --query "{name:name, state:state, hostNames:defaultHostName}"
```

---

## Control

### Stop App

```bash
az webapp stop \
  --resource-group rg-arec-crm \
  --name arec-crm-app
```

### Start App

```bash
az webapp start \
  --resource-group rg-arec-crm \
  --name arec-crm-app
```

### Restart App

```bash
az webapp restart \
  --resource-group rg-arec-crm \
  --name arec-crm-app
```

---

## Database

### Connection String

From Key Vault:
```bash
az keyvault secret show \
  --vault-name kv-arec-crm \
  --name DATABASE-URL \
  --query value \
  --output tsv
```

### Test Connection (from App Service SSH)

```bash
# Open SSH
az webapp ssh \
  --resource-group rg-arec-crm \
  --name arec-crm-app

# Inside SSH console
python3 -c "import os; from sqlalchemy import create_engine; \
  engine = create_engine(os.environ['DATABASE_URL']); \
  conn = engine.connect(); print('✓ Connected'); conn.close()"
```

### Run Migration Scripts (if needed)

```bash
# From App Service SSH
cd /home/site/wwwroot
python3 scripts/create_schema.py
python3 scripts/migrate_to_postgres.py
python3 scripts/verify_migration.py
```

---

## Key Vault

### List Secrets

```bash
az keyvault secret list \
  --vault-name kv-arec-crm \
  --query "[].name"
```

### Get Secret Value

```bash
az keyvault secret show \
  --vault-name kv-arec-crm \
  --name SECRET-NAME \
  --query value \
  --output tsv
```

### Update Secret

```bash
az keyvault secret set \
  --vault-name kv-arec-crm \
  --name SECRET-NAME \
  --value "new_value"
```

---

## Troubleshooting

### App returns 500 error

```bash
# Check logs
az webapp log tail --resource-group rg-arec-crm --name arec-crm-app

# Check if app is running
az webapp show --resource-group rg-arec-crm --name arec-crm-app --query state

# Restart
az webapp restart --resource-group rg-arec-crm --name arec-crm-app
```

### Database connection error

```bash
# Verify DATABASE_URL is set
az webapp config appsettings list \
  --resource-group rg-arec-crm \
  --name arec-crm-app \
  --query "[?name=='DATABASE_URL']"

# Check PostgreSQL firewall rules
az postgres flexible-server firewall-rule list \
  --resource-group rg-arec-crm \
  --name arec-crm-db \
  --output table
```

### SSO not working

```bash
# Verify Entra ID settings
az webapp config appsettings list \
  --resource-group rg-arec-crm \
  --name arec-crm-app \
  --query "[?starts_with(name, 'AZURE_')]"
```

### Check Key Vault access

```bash
# Verify managed identity
az webapp identity show \
  --resource-group rg-arec-crm \
  --name arec-crm-app

# Check role assignment
az role assignment list \
  --scope /subscriptions/064d6342-5dc5-424e-802f-53ff17bc02be/resourceGroups/rg-arec-crm/providers/Microsoft.KeyVault/vaults/kv-arec-crm \
  --query "[].{principal:principalName, role:roleDefinitionName}"
```

---

## Common Tasks

### Update environment variable

```bash
# Get secret from Key Vault
az keyvault secret show --vault-name kv-arec-crm --name ANTHROPIC-API-KEY --query value -o tsv

# Set in App Service (using Key Vault reference)
az webapp config appsettings set \
  --resource-group rg-arec-crm \
  --name arec-crm-app \
  --settings ANTHROPIC_API_KEY="@Microsoft.KeyVault(VaultName=kv-arec-crm;SecretName=ANTHROPIC-API-KEY)"

# Restart to load new value
az webapp restart --resource-group rg-arec-crm --name arec-crm-app
```

### Run schema migration

```bash
# SSH into app
az webapp ssh --resource-group rg-arec-crm --name arec-crm-app

# Run script
cd /home/site/wwwroot
python3 scripts/create_schema.py
exit

# Restart app
az webapp restart --resource-group rg-arec-crm --name arec-crm-app
```

### View deployment history

```bash
az webapp deployment list \
  --resource-group rg-arec-crm \
  --name arec-crm-app \
  --query "[].{id:id, status:status, time:end_time}" \
  --output table
```

---

## URLs

- **App:** https://arec-crm-app.azurewebsites.net/crm
- **Azure Portal:** https://portal.azure.com
- **GitHub Actions:** https://github.com/o4dvasq/arec-crm/actions
- **PostgreSQL:** arec-crm-db.postgres.database.azure.com
- **Key Vault:** https://kv-arec-crm.vault.azure.net/

---

## Resource IDs

```
Subscription: 064d6342-5dc5-424e-802f-53ff17bc02be
Tenant: ebd42ab2-7f1c-4d40-8b44-f5ecc51d2659
Resource Group: rg-arec-crm
App Service: arec-crm-app
PostgreSQL: arec-crm-db
Database: arec_crm
Key Vault: kv-arec-crm
Entra App: 94270ca6-e1e1-4f0f-bdd0-f8df2cbb3750
```
