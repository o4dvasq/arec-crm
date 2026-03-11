# SPEC: Phase I1 — Database + Auth + Core Web App

**Project:** arec-crm → AREC Intelligence Platform (Azure)
**Date:** March 11, 2026
**Status:** Ready for implementation — Azure infrastructure provisioned ✅
**Depends on:** ~~Oscar completing Azure Portal prerequisites (see Section 10)~~ DONE

---

## ⚠️ CRITICAL: Parallel Deployment Strategy

**DO NOT modify any existing files in the `main` branch.**

The local markdown-based CRM must keep running on Oscar's laptop throughout the entire Azure migration. The two systems run in parallel until Azure is confirmed stable.

**How this works:**
1. Create a new git branch: `azure-migration`
2. ALL Azure work happens on that branch only
3. The `main` branch stays untouched — local CRM keeps working
4. Files that need Azure-specific changes (import swaps, SSO, DB init) are modified ONLY on the `azure-migration` branch
5. New files (`crm_db.py`, `models.py`, `db.py`, `entra_auth.py`, migration scripts) are added on that branch
6. The Azure branch is deployed to Azure App Service; `main` stays on Oscar's laptop
7. After Azure is stable, Oscar does a final data re-sync from markdown → Postgres, then merges

**Verification before any implementation:** Run `git branch` and confirm you are on `azure-migration`, NOT `main`. If on `main`, STOP and switch.

---

## 1. Objective

Create an Azure-deployed version of the AREC CRM with a PostgreSQL backend and Microsoft Entra ID SSO for the 8-person team, while keeping the existing local markdown-based CRM running untouched. The pipeline table, org detail, prospect detail, people pages, and inline editing must work identically to the local CRM — same UI, same API routes, new data layer. Both systems run in parallel until Azure is confirmed stable, then a final data re-sync and cutover.

---

## 2. Scope

### In Scope
- PostgreSQL schema creation (all CRM tables, enums, indexes)
- `crm_db.py` — drop-in replacement for `crm_reader.py` (same function signatures, SQLAlchemy backend)
- One-time migration script: parse markdown files → insert into Postgres
- Entra ID SSO integration (MSAL for Python, application-level)
- `_nav.html` updated with user display name + logout
- Azure App Service deployment configuration
- Azure Key Vault integration for secrets
- `updated_by` tracking on all write operations
- All existing tests rewritten for the Postgres backend
- `.env.azure` template for Azure environment variables

### Out of Scope
- Intelligence pipeline (Phase I2)
- Intelligence UI / timeline (Phase I3)
- Briefing engine (Phase I4)
- Meeting transcript processing (Phase I5)
- Morning briefing (`main.py`) — stays local, unchanged
- Task management (`tasks_blueprint.py`, `TASKS.md`) — stays local, unchanged
- `drain_inbox.py` — stays local, unchanged
- `memory/` directory — stays local, unchanged
- `meeting-summaries/` — stays local, unchanged
- Dashboard home page (`dashboard.html`) — stays local, not deployed
- Mobile PWA (`arec-mobile/`) — stays local, unchanged
- Custom domain (use default `*.azurewebsites.net` for now)

---

## 3. Business Rules

1. **Zero data loss.** Every prospect, organization, contact, offering, interaction, email log entry, brief, and prospect note in the markdown files must appear in Postgres after migration. Counts must match.

2. **Organization type is VARCHAR(100), not an enum.** There are 19 distinct org types in live data (see PREREQUISITES.md §9). Migrate all as-is. Normalize `HNWI/FO` → `HNWI / FO` (add space).

3. **Pipeline stages are canonical.** Remap `2. Qualified` → `2. Cold`. Remap `3. Presentation` → `3. Outreach`. Final stage list: 0. Declined, 1. Prospect, 2. Cold, 3. Outreach, 4. Engaged, 5. Interested, 6. Verbal, 7. Legal / DD, 8. Closed.

4. **Single owner per prospect.** `assigned_to` is a single FK to `users`. Migration picks the first name from semicolon-separated values in markdown. Others are dropped.

5. **Currency stored as BIGINT (cents).** `$50M` → `5000000000`. The existing `_parse_currency()` helper in `crm_reader.py` handles this.

6. **Contacts table gets basics only.** Name, org FK, title, email, phone, notes. Rich bios stay in `memory/people/*.md` (not migrated). Pull contact data from `contacts_index.md` cross-referenced with `memory/people/*.md` files.

7. **`crm_db.py` must satisfy the exact import contract.** `crm_blueprint.py` imports 39 functions. `crm_graph_sync.py` imports 13 functions. `prompt_builder.py` imports 4 functions. All signatures must match (see Section 6).

8. **SSO is mandatory.** No unauthenticated access. All 8 team members authenticate via Entra ID. User records are seeded during migration.

9. **`updated_by` is tracked.** Every PATCH/POST write operation records the authenticated user's ID.

10. **Parallel pilot — separate branch.** All Azure work happens on the `azure-migration` git branch. The `main` branch is NEVER modified. The local CRM on `main` keeps running throughout. Oscar cuts over when confident, at which point he does a final data re-sync and merges the branch.

---

## 4. Data Model / Schema Changes

### 4.1 Enums and Types

```sql
-- Use VARCHAR for org_type (not enum) — 19 distinct values in live data
-- Pipeline stages stored in pipeline_stages table, referenced by name

CREATE TYPE urgency_level AS ENUM ('High', 'Med', 'Low');
CREATE TYPE closing_option AS ENUM ('1st', '2nd', 'Final');
CREATE TYPE interaction_type AS ENUM (
    'Email', 'Meeting', 'Call', 'Note', 'Document Sent', 'Document Received'
);
CREATE TYPE interaction_source AS ENUM (
    'manual', 'auto-graph', 'auto-teams', 'forwarded-email'
);
CREATE TYPE briefing_scope AS ENUM ('executive', 'full', 'standard', 'minimal');
```

### 4.2 Tables

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    entra_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    briefing_enabled BOOLEAN DEFAULT true,
    briefing_scope briefing_scope DEFAULT 'standard',
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

CREATE TABLE offerings (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    target BIGINT,
    hard_cap BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by INTEGER REFERENCES users(id)
);

CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(100) NOT NULL,
    domain VARCHAR(255) DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by INTEGER REFERENCES users(id)
);

CREATE TABLE contacts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    title VARCHAR(255) DEFAULT '',
    email VARCHAR(255) DEFAULT '',
    phone VARCHAR(255) DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by INTEGER REFERENCES users(id),
    UNIQUE(name, organization_id)
);

CREATE TABLE pipeline_stages (
    id SERIAL PRIMARY KEY,
    number INTEGER UNIQUE,
    name VARCHAR(100) UNIQUE NOT NULL,
    is_terminal BOOLEAN DEFAULT false,
    sort_order INTEGER NOT NULL
);

CREATE TABLE prospects (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    offering_id INTEGER NOT NULL REFERENCES offerings(id) ON DELETE CASCADE,
    stage VARCHAR(50) NOT NULL DEFAULT '1. Prospect',
    target BIGINT DEFAULT 0,
    committed BIGINT DEFAULT 0,
    primary_contact_id INTEGER REFERENCES contacts(id),
    closing closing_option,
    urgency urgency_level,
    assigned_to INTEGER REFERENCES users(id),
    next_action TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    last_touch DATE,
    relationship_brief TEXT DEFAULT '',
    disambiguator VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by INTEGER REFERENCES users(id),
    UNIQUE(organization_id, offering_id, disambiguator)
);

CREATE TABLE interactions (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    offering_id INTEGER REFERENCES offerings(id),
    contact_id INTEGER REFERENCES contacts(id),
    interaction_date DATE NOT NULL,
    type interaction_type NOT NULL,
    subject VARCHAR(500) DEFAULT '',
    summary TEXT DEFAULT '',
    source interaction_source DEFAULT 'manual',
    source_ref VARCHAR(500) DEFAULT '',
    team_members INTEGER[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id)
);

CREATE TABLE email_scan_log (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(500) UNIQUE NOT NULL,
    from_email VARCHAR(255) DEFAULT '',
    to_emails TEXT DEFAULT '',
    subject VARCHAR(500) DEFAULT '',
    email_date DATE,
    org_name VARCHAR(255) DEFAULT '',
    matched BOOLEAN DEFAULT false,
    snippet TEXT DEFAULT '',
    outlook_url TEXT DEFAULT '',
    scanned_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE briefs (
    id SERIAL PRIMARY KEY,
    brief_type VARCHAR(50) NOT NULL,
    key VARCHAR(255) NOT NULL,
    narrative TEXT DEFAULT '',
    at_a_glance TEXT DEFAULT '',
    content_hash VARCHAR(64) DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(brief_type, key)
);

CREATE TABLE prospect_notes (
    id SERIAL PRIMARY KEY,
    org_name VARCHAR(255) NOT NULL,
    offering_name VARCHAR(255) NOT NULL,
    author VARCHAR(255) DEFAULT '',
    text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE unmatched_emails (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) DEFAULT '',
    subject VARCHAR(500) DEFAULT '',
    date DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE pending_interviews (
    id SERIAL PRIMARY KEY,
    org_name VARCHAR(255) NOT NULL,
    offering_name VARCHAR(255) DEFAULT '',
    reason TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 4.3 Indexes

```sql
CREATE INDEX idx_prospects_offering ON prospects(offering_id);
CREATE INDEX idx_prospects_org ON prospects(organization_id);
CREATE INDEX idx_prospects_stage ON prospects(stage);
CREATE INDEX idx_contacts_org ON contacts(organization_id);
CREATE INDEX idx_contacts_email ON contacts(email);
CREATE INDEX idx_interactions_org ON interactions(organization_id);
CREATE INDEX idx_interactions_date ON interactions(interaction_date);
CREATE INDEX idx_email_scan_msg ON email_scan_log(message_id);
CREATE INDEX idx_email_scan_org ON email_scan_log(org_name);
CREATE INDEX idx_briefs_type_key ON briefs(brief_type, key);
CREATE INDEX idx_orgs_name ON organizations(name);
CREATE INDEX idx_orgs_domain ON organizations(domain);
```

### 4.4 Seed Data: Pipeline Stages

```sql
INSERT INTO pipeline_stages (number, name, is_terminal, sort_order) VALUES
(0, '0. Declined', true, 0),
(1, '1. Prospect', false, 1),
(2, '2. Cold', false, 2),
(3, '3. Outreach', false, 3),
(4, '4. Engaged', false, 4),
(5, '5. Interested', false, 5),
(6, '6. Verbal', false, 6),
(7, '7. Legal / DD', false, 7),
(8, '8. Closed', false, 8);
```

### 4.5 Seed Data: Users

```sql
INSERT INTO users (entra_id, email, display_name, briefing_scope) VALUES
('placeholder-tony', 'tony@avilacapllc.com', 'Tony Avila', 'executive'),
('placeholder-oscar', 'oscar@avilacapllc.com', 'Oscar Vasquez', 'full'),
('placeholder-truman', 'truman@avilacapllc.com', 'Truman Flynn', 'standard'),
('placeholder-zach', 'zach@avilacapllc.com', 'Zach Reisner', 'standard'),
('placeholder-james', 'james@avilacapllc.com', 'James Walton', 'standard'),
('placeholder-ian', 'ian@avilacapllc.com', 'Ian Morgan', 'standard'),
('placeholder-patrick', 'patrick@avilacapllc.com', 'Patrick McElhaney', 'standard'),
('placeholder-rob', 'rob@avilacapllc.com', 'Rob Banagale', 'standard');
```

Note: `entra_id` values are placeholders. After Entra ID app registration, update these with the actual object IDs from the Avila Capital LLC tenant. The SSO login flow should upsert on `email` match and set the real `entra_id` on first login.

---

## 5. UI / Interface

### No UI changes in Phase I1.
The pipeline table, org detail, prospect detail, people pages, and all inline editing work exactly as they do locally. Same templates, same CSS, same JS, same API endpoints.

### Changes:

- **`_nav.html`**: Add logged-in user's display name (top-right). Add "Logout" link that calls `/.auth/logout` (or MSAL logout endpoint).
- **All CRM pages**: Served only to authenticated users. Unauthenticated requests redirect to Entra ID login.

### States:
- **Loading**: Same as current (no change)
- **Empty**: Same as current (no change)
- **Error**: If database is unreachable, show a simple error page: "CRM is temporarily unavailable. Please try again."
- **Unauthenticated**: Redirect to Microsoft login. After login, redirect back to the originally requested page.

---

## 6. Integration Points

### Reads From
- PostgreSQL (all CRM data)
- Azure Key Vault (secrets: `ANTHROPIC_API_KEY`, `DATABASE_URL`, `ENTRA_CLIENT_SECRET`)
- Microsoft Entra ID (SSO tokens, client ID: `94270ca6-e1e1-4f0f-bdd0-f8df2cbb3750`)

### Writes To
- PostgreSQL (all CRM write operations)

### Calls
- Claude API (`ANTHROPIC_API_KEY`) — brief synthesis, same as local
- Microsoft Graph API — NOT in Phase I1 scope (stays local)

### The crm_db.py Contract

`crm_blueprint.py` imports exactly these 39 functions:

```python
from sources.crm_db import (
    load_prospects, load_offerings, get_fund_summary, get_fund_summary_all,
    load_crm_config, get_organization, write_organization, load_organizations,
    get_contacts_for_org, create_person_file, update_contact_fields,
    get_prospects_for_org, get_prospect, write_prospect, update_prospect_field,
    load_unmatched, remove_unmatched, add_unmatched,
    _parse_currency, load_person, load_tasks_by_org, load_all_persons,
    delete_prospect, load_meeting_history, add_meeting_entry,
    get_tasks_for_prospect, get_all_prospect_tasks, add_prospect_task,
    complete_prospect_task,
    load_email_log, get_emails_for_org, find_email_by_message_id,
    load_interactions, append_interaction,
    save_brief, load_saved_brief, load_all_briefs,
    load_prospect_notes, save_prospect_note,
    append_person_email_history, append_org_email_history,
    discover_and_enrich_contact_emails, enrich_org_domain,
    find_person_by_email,
)
```

`crm_graph_sync.py` imports these 13 functions:

```python
from sources.crm_db import (
    add_pending_interview, add_unmatched, append_interaction,
    append_org_email_history, append_person_email_history,
    discover_and_enrich_contact_emails, enrich_org_domain,
    enrich_person_email, find_person_by_email,
    load_organizations, load_prospects, purge_old_unmatched,
    load_interactions,
)
```

`prompt_builder.py` imports these 4 functions:

```python
from sources.crm_db import (
    load_interactions, load_prospects, find_person_by_email, get_contacts_for_org,
)
```

`crm_blueprint.py` also has a late import:

```python
from sources.crm_db import get_org_domains, add_emails_to_log
```

**Total unique functions `crm_db.py` must export: ~45.** Every signature must match what `crm_reader.py` currently provides. Reference PREREQUISITES.md §2 for the full list with return types.

### Functions that change behavior in crm_db.py

Most functions simply swap markdown parsing for SQL queries. Notable differences:

- `load_crm_config()` → reads from `pipeline_stages` table + hardcoded org types list (or a config table)
- `get_team_member_email(name)` → queries `users` table
- `create_person_file()` → in Phase I1, creates a `contacts` row only (no markdown file). The `memory/people/*.md` files are local-only.
- `load_person()` → queries `contacts` table. Returns same dict shape. Does NOT read `memory/people/*.md`.
- `load_all_persons()` → queries `contacts` table.
- `load_tasks_by_org()`, `get_tasks_for_prospect()`, `get_all_prospect_tasks()`, `add_prospect_task()`, `complete_prospect_task()` → **Phase I1 decision: these are CRM prospect-level tasks (not TASKS.md personal tasks).** They need a `prospect_tasks` table. Add:

```sql
CREATE TABLE prospect_tasks (
    id SERIAL PRIMARY KEY,
    org_name VARCHAR(255) NOT NULL,
    text TEXT NOT NULL,
    owner VARCHAR(255) DEFAULT '',
    priority VARCHAR(20) DEFAULT 'Med',
    status VARCHAR(20) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

- `_parse_currency()` and `_format_currency()` → pure utility functions, copy as-is.

---

## 7. Constraints

1. **ALL work on the `azure-migration` branch.** Never commit to `main`. Never modify files on `main`. The local CRM must keep running undisturbed. Before starting any work, run `git checkout azure-migration` (or `git checkout -b azure-migration` to create it). Verify with `git branch` before every session.
2. **Import swap happens on the branch only.** On the `azure-migration` branch, `crm_blueprint.py`, `crm_graph_sync.py`, and `prompt_builder.py` change their imports from `crm_reader` → `crm_db`. On `main`, these files remain untouched.
3. **No changes to templates or static files** except `_nav.html` (add user name + logout) — on the Azure branch only.
4. **SQLAlchemy is the ORM.** Use `sqlalchemy` with `psycopg2-binary`. No raw SQL in route handlers.
5. **All secrets in environment variables.** Never hardcode connection strings, API keys, or client secrets.
6. **Azure App Service deployment via ZIP deploy or GitHub Actions.** No Docker in Phase I1.
7. **Flask debug mode must be false in production.**
8. **Database connection pooling.** Use SQLAlchemy's built-in pool (default pool size is fine for 8 users).
9. **Migration script is idempotent.** Can be run multiple times safely (upsert or check-before-insert). This is critical because the final cutover requires a re-sync run.
10. **Migration script reads from markdown files but does NOT modify them.** It is a one-way read from `crm/*.md` → write to Postgres.

---

## 8. Acceptance Criteria

1. All 129 organizations migrated to Postgres with correct types (19 distinct). `HNWI/FO` normalized to `HNWI / FO`.
2. All 161 prospects migrated with correct stage remapping (`2. Qualified` → `2. Cold`, `3. Presentation` → `3. Outreach`). Multi-assignee values reduced to first name.
3. All 3 offerings migrated with correct target/hard_cap as BIGINT cents.
4. All contacts from `contacts_index.md` + `memory/people/*.md` migrated to `contacts` table with name, org FK, title, email.
5. All interactions migrated with correct date, type, source, org FK.
6. Email log entries migrated to `email_scan_log` table.
7. Cached briefs migrated to `briefs` table.
8. Pipeline table at `/crm` renders identically to local (sort, filter, inline edit all work).
9. Org detail page at `/crm/org/<name>` shows contacts, prospects, meetings, briefs — all from Postgres.
10. Prospect detail page at `/crm/prospect/<offering>/<org>/detail` shows brief, notes, emails, tasks — all from Postgres.
11. People pages at `/crm/people` and `/crm/people/<slug>` work from Postgres.
12. Inline editing (PATCH `/crm/api/prospect/field`) writes to Postgres and records `updated_by`.
13. Brief synthesis (POST `/crm/api/synthesize-brief`) calls Claude API and saves to Postgres.
14. 8 team members can log in via Microsoft SSO. Unauthenticated users are redirected to login.
15. Secrets (`ANTHROPIC_API_KEY`, `DATABASE_URL`) are read from environment (Key Vault in production).
16. App is accessible at `https://arec-crm-app.azurewebsites.net/crm`.
17. All existing test scenarios pass against the Postgres backend (52 tests rewritten).
18. Migration script produces a summary report: record counts per table, any skipped/failed records.
19. Feedback loop prompt has been run.

---

## 9. Files Likely Touched

### New Files
| File | Purpose |
|------|---------|
| `app/sources/crm_db.py` | SQLAlchemy replacement for `crm_reader.py` (~45 functions) |
| `app/models.py` | SQLAlchemy model definitions (all tables from Section 4) |
| `app/db.py` | Database engine/session factory, connection config |
| `app/auth/entra_auth.py` | Entra ID SSO middleware (MSAL confidential client) |
| `scripts/migrate_to_postgres.py` | One-time markdown → Postgres migration script |
| `scripts/verify_migration.py` | Post-migration verification (count comparisons, spot checks) |
| `app/.env.azure` | Azure environment variable template |
| `app/requirements-azure.txt` | Extended requirements (adds sqlalchemy, psycopg2-binary, gunicorn) |
| `startup.sh` | Azure App Service startup script (`gunicorn app.delivery.dashboard:app`) |
| `app/tests/test_crm_db.py` | Tests for crm_db.py (rewritten from test_email_matching etc.) |
| `app/tests/conftest_azure.py` | Test fixtures with ephemeral Postgres (or SQLite for CI) |

### Modified Files (on `azure-migration` branch ONLY — never on `main`)
| File | Change |
|------|--------|
| `app/delivery/crm_blueprint.py` | Line 26: `from sources.crm_reader import` → `from sources.crm_db import` |
| `app/delivery/crm_blueprint.py` | Line 410: same import rename |
| `app/sources/crm_graph_sync.py` | Line 12: same import rename |
| `app/briefing/prompt_builder.py` | Lines 9, 60: same import rename |
| `app/delivery/dashboard.py` | Add `db.init_app(app)`, SSO middleware, user session |
| `app/templates/_nav.html` | Add user display name + logout link |
| `app/requirements.txt` | Add `sqlalchemy`, `psycopg2-binary`, `gunicorn` |

### NEVER Modified (stay untouched on `main`, keep local CRM running)
- `app/main.py`, `app/drain_inbox.py`, `app/sources/memory_reader.py`
- `app/sources/crm_reader.py` — the local markdown backend stays as-is
- `app/delivery/tasks_blueprint.py` (tasks stay local)
- `app/templates/dashboard.html`, `app/templates/tasks/`
- All `memory/`, `meeting-summaries/`, `skills/`, `crm/` markdown files
- `config.yaml`

---

## 10. Oscar's Manual Prerequisites (Azure Portal / CLI)

These steps must be completed by Oscar before Claude Code can begin implementation. They require Azure Portal access and admin consent that can't be automated from code.

### Step 1: Verify Azure CLI login

You're already in the correct tenant. Confirm with:

```bash
az account show --output table
```

Tenant should be `ebd42ab2-7f1c-4d40-8b44-f5ecc51d2659` (Avila Capital LLC).
Subscription should be `064d6342-5dc5-424e-802f-53ff17bc02be` (Azure subscription 1).

### Step 2: Create Resource Group

```bash
az group create --name rg-arec-crm --location westus2  # Resource group is in westus2; resources are in centralus
```

### Step 3: Create PostgreSQL Flexible Server

```bash
az postgres flexible-server create \
  --resource-group rg-arec-crm \
  --name arec-crm-db \
  --location centralus \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 16 \
  --admin-user arecadmin \
  --admin-password '<GENERATE_STRONG_PASSWORD>' \
  --yes
```

Then create the database:

```bash
az postgres flexible-server db create \
  --resource-group rg-arec-crm \
  --server-name arec-crm-db \
  --database-name arec_crm
```

Save the connection string — you'll need it:
`postgresql://arecadmin:<PASSWORD>@arec-crm-db.postgres.database.azure.com:5432/arec_crm?sslmode=require`

### Step 4: Create Azure Key Vault

```bash
az keyvault create \
  --resource-group rg-arec-crm \
  --name kv-arec-crm \
  --location centralus
```

Store secrets:

```bash
az keyvault secret set --vault-name kv-arec-crm --name ANTHROPIC-API-KEY --value '<your_key>'
az keyvault secret set --vault-name kv-arec-crm --name DATABASE-URL --value 'postgresql://arecadmin:<PASSWORD>@arec-crm-db.postgres.database.azure.com:5432/arec_crm?sslmode=require'
```

### Step 5: Register Entra ID Application

In Azure Portal → Microsoft Entra ID → App registrations → New registration:

- **Name:** AREC Intelligence Platform
- **Supported account types:** Accounts in this organizational directory only (Avila Capital LLC)
- **Redirect URI:** Web — `https://<app-name>.azurewebsites.net/.auth/login/aad/callback`
  (You'll know the exact URL after Step 6. You can update this later.)

After registration:
1. Copy the **Application (client) ID** — you'll need this as `AZURE_CLIENT_ID`
2. Go to **Certificates & secrets** → New client secret → Copy the value → store in Key Vault:

```bash
az keyvault secret set --vault-name kv-arec-crm --name AZURE-CLIENT-SECRET --value '<client_secret>'
```

3. Go to **API permissions** → Add:
   - `User.Read` (delegated) — for SSO login
   - Grant admin consent

### Step 6: Create Azure App Service

```bash
az appservice plan create \
  --resource-group rg-arec-crm \
  --name plan-arec-crm \
  --sku B1 \
  --is-linux

az webapp create \
  --resource-group rg-arec-crm \
  --plan plan-arec-crm \
  --name arec-crm-app \
  --runtime "PYTHON:3.12"
```

Configure app settings:

```bash
az webapp config appsettings set \
  --resource-group rg-arec-crm \
  --name arec-crm-app \
  --settings \
    DATABASE_URL="@Microsoft.KeyVault(VaultName=kv-arec-crm;SecretName=DATABASE-URL)" \
    ANTHROPIC_API_KEY="@Microsoft.KeyVault(VaultName=kv-arec-crm;SecretName=ANTHROPIC-API-KEY)" \
    ENTRA_CLIENT_ID="94270ca6-e1e1-4f0f-bdd0-f8df2cbb3750" \
    ENTRA_CLIENT_SECRET="@Microsoft.KeyVault(VaultName=kv-arec-crm;SecretName=ENTRA-CLIENT-SECRET)" \
    ENTRA_TENANT_ID="ebd42ab2-7f1c-4d40-8b44-f5ecc51d2659" \
    FLASK_DEBUG="false" \
    SCM_DO_BUILD_DURING_DEPLOYMENT="true"
```

### Step 7: Grant App Service access to Key Vault

```bash
az webapp identity assign --resource-group rg-arec-crm --name arec-crm-app

# Then grant via RBAC (this vault uses RBAC, not access policies):
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee <PRINCIPAL_ID_FROM_ABOVE> \
  --scope /subscriptions/064d6342-5dc5-424e-802f-53ff17bc02be/resourceGroups/rg-arec-crm/providers/Microsoft.KeyVault/vaults/kv-arec-crm
```

### Step 8: Allow App Service to reach Postgres

```bash
az postgres flexible-server firewall-rule create \
  --resource-group rg-arec-crm \
  --name arec-crm-db \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

### Step 9: Confirm and report back — ✅ COMPLETED

All Azure infrastructure has been provisioned. Summary of actual resource IDs:

| Resource | Actual Value |
|----------|-------------|
| Tenant ID | `ebd42ab2-7f1c-4d40-8b44-f5ecc51d2659` |
| Subscription ID | `064d6342-5dc5-424e-802f-53ff17bc02be` |
| Resource Group | `rg-arec-crm` (westus2) |
| PostgreSQL Server | `arec-crm-db` (centralus) |
| Database | `arec_crm` |
| DB Admin User | `arecadmin` |
| DB Connection | `postgresql://arecadmin:<PASSWORD>@arec-crm-db.postgres.database.azure.com:5432/arec_crm?sslmode=require` |
| Key Vault | `kv-arec-crm` (centralus) |
| Key Vault Secrets | `ANTHROPIC-API-KEY`, `DATABASE-URL`, `ENTRA-CLIENT-SECRET` |
| Entra App Name | `AREC CRM` |
| Entra Client ID | `94270ca6-e1e1-4f0f-bdd0-f8df2cbb3750` |
| App Service Plan | `plan-arec-crm` (B1 Linux, centralus) |
| Web App | `arec-crm-app` (centralus) |
| Web App URL | `https://arec-crm-app.azurewebsites.net` |
| Managed Identity | Assigned, granted Key Vault Secrets User role |
| Firewall | AllowAzureServices rule on Postgres (0.0.0.0) |

App settings configured with Key Vault references for secrets. Entra ID client ID and tenant ID set as plain app settings.

---

## 11. Implementation Order (for Claude Code)

### Step 0: Create the Azure branch (MANDATORY FIRST STEP)

```bash
git checkout main
git pull
git checkout -b azure-migration
```

**Verify:** `git branch` must show `* azure-migration`. If it shows `main`, STOP.

ALL subsequent work happens on this branch. Never switch back to `main` to make changes.

### Steps 1–13: Build on `azure-migration` branch

Once Oscar completes the Azure Portal prerequisites:

1. **`app/models.py`** — SQLAlchemy models for all tables (NEW file)
2. **`app/db.py`** — Engine/session factory, reads `DATABASE_URL` from env (NEW file)
3. **Schema creation script** — `scripts/create_schema.py` using models (NEW file)
4. **`scripts/migrate_to_postgres.py`** — Parse all `crm/*.md` files (READ ONLY), insert into Postgres (NEW file). Must be idempotent for re-sync at cutover.
5. **`scripts/verify_migration.py`** — Count checks, spot-check sample records (NEW file)
6. **`app/sources/crm_db.py`** — All ~45 functions, one-for-one replacement for `crm_reader.py` (NEW file, `crm_reader.py` is NOT deleted)
7. **`app/auth/entra_auth.py`** — MSAL confidential client, session management (NEW file)
8. **Update imports on this branch** — `crm_blueprint.py`, `crm_graph_sync.py`, `prompt_builder.py` change `crm_reader` → `crm_db` (BRANCH-ONLY modifications)
9. **Update `dashboard.py` on this branch** — DB init, SSO middleware, user context (BRANCH-ONLY modification)
10. **Update `_nav.html` on this branch** — User name + logout (BRANCH-ONLY modification)
11. **`app/tests/test_crm_db.py`** — Rewrite all 52 tests for Postgres (NEW file)
12. **Deployment config** — `startup.sh`, `requirements-azure.txt`, `.env.azure` (NEW files)
13. **Deploy and smoke test** — ZIP deploy from `azure-migration` branch, verify `/crm` loads, inline edit works

### Cutover (later, when Azure is confirmed stable)

1. Oscar runs `scripts/migrate_to_postgres.py` one final time for a fresh data re-sync
2. Oscar verifies Azure data matches local
3. Oscar merges `azure-migration` → `main`
4. Local markdown CRM is retired

---

## 12. Estimated Effort

| Component | Estimate |
|-----------|----------|
| SQLAlchemy models + schema | 1–2 hours |
| Migration script | 2–3 hours |
| `crm_db.py` (45 functions) | 4–6 hours |
| Entra ID SSO integration | 1–2 hours |
| Import updates + dashboard changes | 30 min |
| Test rewrite | 2–3 hours |
| Deployment config + smoke test | 1–2 hours |
| **Total** | **~12–18 hours of Claude Code time** |
