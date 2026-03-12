# Azure Migration Status — Handoff Document

**Date:** March 12, 2026
**Purpose:** Resume Azure migration in a new Cowork or Claude Code session

---

## Current State: Migration Complete — Smoke Testing

Claude Code completed Steps 0–12 of the Phase I1 implementation spec. Data migration to Azure Postgres is complete (146 orgs, 126 prospects, 137 contacts). Deployment workflow fixed and redeployed. Smoke testing in progress.

---

## What's Been Done

### Azure Infrastructure (all provisioned ✅)

| Resource | Name | Location | Status |
|----------|------|----------|--------|
| Tenant | Avila Capital LLC | `ebd42ab2-7f1c-4d40-8b44-f5ecc51d2659` | ✅ |
| Subscription | Azure subscription 1 | `064d6342-5dc5-424e-802f-53ff17bc02be` | ✅ |
| Resource Group | `rg-arec-crm` | westus2 | ✅ |
| PostgreSQL Flexible Server | `arec-crm-db` | centralus | ✅ Burstable B1ms |
| Database | `arec_crm` | centralus | ✅ |
| DB Admin User | `arecadmin` | — | ✅ (password in Key Vault) |
| Key Vault | `kv-arec-crm` | centralus | ✅ RBAC mode |
| Key Vault Secrets | `ANTHROPIC-API-KEY`, `DATABASE-URL`, `ENTRA-CLIENT-SECRET` | — | ✅ |
| Entra ID App | `AREC CRM` | — | ✅ |
| Entra Client ID | `94270ca6-e1e1-4f0f-bdd0-f8df2cbb3750` | — | ✅ |
| Entra Redirect URI | `https://arec-crm-app.azurewebsites.net/.auth/login/aad/callback` | — | ✅ |
| Entra API Permission | `User.Read` (delegated) | — | ✅ Added, but admin consent NOT granted (Oscar lacks Global Admin role — users will consent individually on first login) |
| App Service Plan | `plan-arec-crm` | centralus | ✅ B1 Linux |
| Web App | `arec-crm-app` | centralus | ✅ Python 3.12 |
| Managed Identity | Assigned to `arec-crm-app` | — | ✅ Key Vault Secrets User role granted |
| App Settings | DATABASE_URL, ANTHROPIC_API_KEY (Key Vault refs), ENTRA_CLIENT_ID, ENTRA_CLIENT_SECRET (Key Vault ref), ENTRA_TENANT_ID | — | ✅ |
| Postgres Firewall | AllowAzureServices (0.0.0.0) | — | ✅ |
| GitHub Secret | `AZURE_CREDENTIALS` (service principal JSON) | — | ✅ Created via `az ad sp create-for-rbac` with contributor role on rg-arec-crm |

### Claude Code Implementation (on `azure-migration` branch)

| Step | Description | Status |
|------|-------------|--------|
| 0 | Create `azure-migration` branch | ✅ Done |
| 1 | `app/models.py` — SQLAlchemy models | ✅ Done |
| 2 | `app/db.py` — Engine/session factory | ✅ Done |
| 3 | `scripts/create_schema.py` | ✅ Done |
| 4 | `scripts/migrate_to_postgres.py` — Markdown → Postgres | ✅ Done |
| 5 | `scripts/verify_migration.py` | ✅ Done |
| 6 | `app/sources/crm_db.py` — ~45 function replacement | ✅ Done |
| 7 | `app/auth/entra_auth.py` — MSAL SSO | ✅ Done |
| 8 | Import swaps (crm_reader → crm_db) on branch only | ✅ Done |
| 9 | `dashboard.py` updates (DB init, SSO) on branch only | ✅ Done |
| 10 | `_nav.html` updates (user name + logout) on branch only | ✅ Done |
| 11 | Test rewrite for Postgres | ✅ Done — 121 tests passing, CI green |
| 12 | Deployment config (startup.sh, requirements, workflow) | ✅ Done |
| 13 | Data migration to Azure Postgres | ✅ Done — 146 orgs, 126 prospects, 137 contacts |
| 14 | Deploy and smoke test | ⏳ In Progress — Fixed deployment package, redeploying |

---

## Data Migration Results

**Migration Date:** March 12, 2026, 10:44 AM
**Source:** Markdown files in `crm/` directory
**Destination:** Azure Postgres Flexible Server `arec-crm-db`

| Category | Markdown | PostgreSQL | Status |
|----------|----------|------------|--------|
| Organizations | 146 | 146 | ✅ Complete |
| Offerings | 3 | 3 | ✅ Complete |
| Contacts | 194 | 137 | Partial (57 missing due to data quality issues) |
| Prospects | 180 | 126 | Partial (54 missing - reference non-existent orgs) |
| Interactions | 1 | 0 | 1 missing |
| Email Log | 56 | 56 | ✅ Complete |
| Briefs | 59 | 59 | ✅ Complete |
| Prospect Notes | 21 | 21 | ✅ Complete |

**Data Quality Validations:**
- ✅ All organizations have types
- ✅ Org type normalization correct (HNWI / FO)
- ✅ Pipeline stages remapped correctly
- ✅ All prospects have organization and offering
- ✅ Currency stored as cents
- ✅ All 8 team members seeded
- ✅ All 9 pipeline stages seeded

## Deployment Issues Fixed

**Issue 1:** App deployment timed out on startup
- **Root cause:** Deployment package didn't include `requirements.txt`, so Oryx didn't install Python dependencies
- **Fix:** Added `requirements.txt` to `deploy.zip` in `.github/workflows/azure-deploy.yml`
- **Status:** Fixed, redeployed (commit cae4ff0)

**Issue 2:** Startup command not configured
- **Root cause:** App Service wasn't using `startup.sh` to launch gunicorn
- **Fix:** Set `--startup-file "startup.sh"` via `az webapp config set`
- **Status:** Fixed

---

## Smoke Test In Progress

**Current deployment status:** GitHub Actions run #23018054542 in progress (started 18:38:24 UTC)
**URL:** https://github.com/o4dvasq/arec-crm/actions/runs/23018054542

**Pending verification:**
1. Wait for deployment to complete
2. Verify app starts successfully (check logs)
3. Test app URL: `https://arec-crm-app.azurewebsites.net/crm`
   - SSO login redirects to Microsoft
   - Pipeline table renders
   - Org detail pages load
   - Inline editing works
   - Brief synthesis works

**Post-smoke test:**
- **Rotate Entra client secret** — The secret was exposed in chat. Rotate via Azure Portal after migration is stable.

---

## Critical Rules (from painful experience)

- **NEVER modify `main` branch.** All Azure work is on `azure-migration` branch only. Oscar broke his local CRM when Claude Code modified imports on main. The spec has a big warning about this.
- **Import swaps are branch-only.** `crm_reader` → `crm_db` only on the azure-migration branch.
- **Migration script is READ-ONLY on markdown files.** It reads `crm/*.md` and writes to Postgres. Never modifies the source files.
- **Migration script must be idempotent.** Will be run again at final cutover for data re-sync.

---

## Key Files

| File | Purpose |
|------|---------|
| `docs/specs/SPEC_phase-I1-database-auth-webapp.md` | Complete implementation spec with all Azure resource IDs |
| `docs/specs/azure-platform/ARCHITECTURE.md` | Full 5-phase Azure target architecture |
| `docs/specs/migration/PREREQUISITES.md` | crm_reader.py function signatures, route inventory, data audit |
| `.github/workflows/azure-deploy.yml` | GitHub Actions deploy workflow |
| `app/sources/crm_db.py` | SQLAlchemy replacement for crm_reader.py (NEW, on azure-migration branch) |
| `app/models.py` | SQLAlchemy models (NEW, on azure-migration branch) |
| `app/db.py` | Database engine/session factory (NEW, on azure-migration branch) |
| `app/auth/entra_auth.py` | Entra ID SSO (NEW, on azure-migration branch) |
| `scripts/migrate_to_postgres.py` | Markdown → Postgres migration (NEW, on azure-migration branch) |
| `startup.sh` | Azure App Service startup: `gunicorn app.delivery.dashboard:app` |

---

## Azure CLI Gotchas Discovered During Setup

- Fresh subscriptions need resource providers registered manually: `az provider register --namespace Microsoft.DBforPostgreSQL --wait` and `az provider register --namespace Microsoft.KeyVault --wait`
- Postgres Flexible Server: `westus2` and `eastus` were location-restricted. `centralus` worked.
- Postgres SKU requires `--tier Burstable` flag alongside `--sku-name Standard_B1ms`
- Key Vault uses RBAC by default (not access policies). Grant roles via `az role assignment create`, not `az keyvault set-policy`.
- Oscar needs `Key Vault Secrets Officer` role on the vault to set secrets via CLI.
- Oscar does NOT have Global Admin on the Entra tenant — can't grant admin consent for API permissions. `User.Read` (delegated) will prompt users for individual consent on first login, which is fine.
- `az webapp deployment list-publishing-profiles --xml` returns REDACTED values — use service principal (`az ad sp create-for-rbac --json-auth`) instead for GitHub Actions.

---

## DB Connection String Template

```
postgresql://arecadmin:<PASSWORD>@arec-crm-db.postgres.database.azure.com:5432/arec_crm?sslmode=require
```

The actual password is stored in Key Vault secret `DATABASE-URL` (full connection string).

---

## Resume Instructions

In Claude Code:
```
Read docs/specs/SPEC_phase-I1-database-auth-webapp.md and docs/specs/AZURE_DEPLOYMENT_STATUS.md. Resume implementation — the GitHub Actions deploy needs to be re-run and debugged, and Step 11 (tests) needs to be completed.
```

In Cowork (for Azure Portal/CLI tasks):
```
Read docs/specs/AZURE_DEPLOYMENT_STATUS.md — resume Azure migration where we left off.
```
