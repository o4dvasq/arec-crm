# Phase I1: Database + Auth + Core Web App

**Date:** March 8, 2026  
**Phase:** I1 of AREC Intelligence Platform  
**Goal:** Multi-user CRM on Azure with Postgres and Entra ID. Full pipeline table, org detail, inline editing.  
**Prerequisite:** Local CRM Phases 1–4 complete (working `crm_reader.py`, Flask dashboard, stable markdown file format)

---

## How to Use This Document

This spec has two parts:

- **Part A — Terminal Commands (Oscar runs these).** Copy-paste blocks. Provisions Azure resources, installs tools, sets up auth. No file editing required.
- **Part B — Claude Code Handoff.** A self-contained spec with full context, file structure, and acceptance criteria. Hand the entire Part B section to Claude Code as a single prompt.

---

# PART A — AZURE SETUP (Oscar in Terminal)

Run these on your iMac. Each section is a copy-paste block.

---

## A1. Install Azure CLI

```bash
brew update && brew install azure-cli
```

Verify:

```bash
az version
```

## A2. Log In to Azure

This opens a browser window. Sign in with your AREC Microsoft 365 account.

```bash
az login
```

After login, confirm your subscription:

```bash
az account show --query "{name:name, id:id, tenantId:tenantId}" -o table
```

Save the `tenantId` value — you'll need it in A4.

## A3. Set Variables

Paste this block to set environment variables for the rest of the session. Adjust `REGION` if you prefer a different Azure region.

```bash
export RG_NAME="arec-crm-rg"
export REGION="westus2"
export PG_SERVER="arec-crm-pg"
export PG_ADMIN="arecadmin"
export PG_DB="arec_crm"
export APP_NAME="arec-crm-app"
export KEYVAULT_NAME="arec-crm-kv"
export APP_SERVICE_PLAN="arec-crm-plan"
```

## A4. Generate a Secure Postgres Password

This generates a 24-character random password and stores it for use in subsequent commands. Do not type a custom password — let the system generate one.

```bash
export PG_PASSWORD=$(openssl rand -base64 18)
echo "Postgres password (save this somewhere safe): $PG_PASSWORD"
```

## A5. Create Resource Group

```bash
az group create --name $RG_NAME --location $REGION
```

## A6. Create PostgreSQL Flexible Server

This takes 2-5 minutes.

```bash
az postgres flexible-server create \
  --resource-group $RG_NAME \
  --name $PG_SERVER \
  --location $REGION \
  --admin-user $PG_ADMIN \
  --admin-password "$PG_PASSWORD" \
  --database-name $PG_DB \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 16 \
  --yes
```

Allow Azure services to connect (needed for App Service → Postgres):

```bash
az postgres flexible-server firewall-rule create \
  --resource-group $RG_NAME \
  --name $PG_SERVER \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

Allow your current IP (for running migration script locally):

```bash
export MY_IP=$(curl -s ifconfig.me)
az postgres flexible-server firewall-rule create \
  --resource-group $RG_NAME \
  --name $PG_SERVER \
  --rule-name AllowMyIP \
  --start-ip-address $MY_IP \
  --end-ip-address $MY_IP
```

## A7. Create Key Vault and Store Secrets

```bash
az keyvault create \
  --resource-group $RG_NAME \
  --name $KEYVAULT_NAME \
  --location $REGION
```

Store the Postgres connection string:

```bash
export PG_HOST="${PG_SERVER}.postgres.database.azure.com"
export PG_CONN="postgresql://${PG_ADMIN}:${PG_PASSWORD}@${PG_HOST}:5432/${PG_DB}?sslmode=require"

az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name "DATABASE-URL" \
  --value "$PG_CONN"
```

## A8. Register Entra ID Application

This creates the app registration for SSO. Replace `YOUR_TENANT_ID` with the tenantId from A2.

```bash
export TENANT_ID="YOUR_TENANT_ID"
```

Create the application:

```bash
az ad app create \
  --display-name "AREC CRM" \
  --sign-in-audience AzureADMyOrg \
  --web-redirect-uris \
    "https://${APP_NAME}.azurewebsites.net/auth/callback" \
    "http://localhost:5000/auth/callback" \
  --query "{appId:appId, objectId:id}" -o table
```

Save the `appId` output — this is your `CLIENT_ID`.

```bash
export CLIENT_ID="PASTE_APP_ID_HERE"
```

Create a client secret (valid 2 years):

```bash
az ad app credential reset \
  --id $CLIENT_ID \
  --append \
  --years 2 \
  --query "{password:password, endDate:endDateTime}" -o table
```

Save the `password` output — this is your `CLIENT_SECRET`. It is shown only once.

```bash
export CLIENT_SECRET="PASTE_SECRET_HERE"
```

Store auth secrets in Key Vault:

```bash
az keyvault secret set --vault-name $KEYVAULT_NAME --name "CLIENT-ID" --value "$CLIENT_ID"
az keyvault secret set --vault-name $KEYVAULT_NAME --name "CLIENT-SECRET" --value "$CLIENT_SECRET"
az keyvault secret set --vault-name $KEYVAULT_NAME --name "TENANT-ID" --value "$TENANT_ID"
```

## A9. Create App Service

```bash
az appservice plan create \
  --resource-group $RG_NAME \
  --name $APP_SERVICE_PLAN \
  --sku B1 \
  --is-linux

az webapp create \
  --resource-group $RG_NAME \
  --plan $APP_SERVICE_PLAN \
  --name $APP_NAME \
  --runtime "PYTHON:3.11"
```

Grant the web app access to Key Vault:

```bash
az webapp identity assign \
  --resource-group $RG_NAME \
  --name $APP_NAME

export APP_PRINCIPAL_ID=$(az webapp identity show \
  --resource-group $RG_NAME \
  --name $APP_NAME \
  --query principalId -o tsv)

az keyvault set-policy \
  --name $KEYVAULT_NAME \
  --object-id $APP_PRINCIPAL_ID \
  --secret-permissions get list
```

Configure app settings (environment variables the Flask app will read):

```bash
az webapp config appsettings set \
  --resource-group $RG_NAME \
  --name $APP_NAME \
  --settings \
    KEYVAULT_NAME=$KEYVAULT_NAME \
    FLASK_ENV=production \
    SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

## A10. Verify Everything Provisioned

```bash
echo "=== Resource Group ==="
az group show --name $RG_NAME --query "{name:name, location:location}" -o table

echo "=== PostgreSQL ==="
az postgres flexible-server show --resource-group $RG_NAME --name $PG_SERVER --query "{name:name, state:state, fqdn:fullyQualifiedDomainName}" -o table

echo "=== Key Vault ==="
az keyvault show --name $KEYVAULT_NAME --query "{name:name, uri:properties.vaultUri}" -o table

echo "=== App Service ==="
az webapp show --resource-group $RG_NAME --name $APP_NAME --query "{name:name, state:state, url:defaultHostName}" -o table

echo "=== Entra App ==="
az ad app show --id $CLIENT_ID --query "{appId:appId, displayName:displayName}" -o table
```

## A11. Save Connection Info for Claude Code

Run this to create a file Claude Code will need. This writes a local env file — do NOT commit it to git.

```bash
cat > ~/arec-crm-azure-env.txt << EOF
DATABASE_URL=$PG_CONN
PG_HOST=$PG_HOST
PG_ADMIN=$PG_ADMIN
PG_PASSWORD=$PG_PASSWORD
PG_DB=$PG_DB
CLIENT_ID=$CLIENT_ID
CLIENT_SECRET=$CLIENT_SECRET
TENANT_ID=$TENANT_ID
KEYVAULT_NAME=$KEYVAULT_NAME
APP_NAME=$APP_NAME
RG_NAME=$RG_NAME
REDIRECT_URI=https://${APP_NAME}.azurewebsites.net/auth/callback
EOF

echo "Saved to ~/arec-crm-azure-env.txt"
```

## A12. Install psql (for Migration Script)

The migration script runs locally and writes to Azure Postgres. You need the postgres client.

```bash
brew install libpq
echo 'export PATH="/opt/homebrew/opt/libpq/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Verify connectivity:

```bash
psql "$PG_CONN" -c "SELECT 1 AS connected;"
```

If this returns `connected = 1`, you're good.

---

## A-Summary: What You Have After Part A

| Resource | Value |
|----------|-------|
| Resource Group | `arec-crm-rg` |
| PostgreSQL | `arec-crm-pg.postgres.database.azure.com` |
| Database | `arec_crm` |
| App Service | `arec-crm-app.azurewebsites.net` |
| Key Vault | `arec-crm-kv` |
| Entra App Registration | AREC CRM (client ID in Key Vault) |
| Local env file | `~/arec-crm-azure-env.txt` |

All secrets are in Key Vault. The env file is your local reference only.

---
---

# PART B — CLAUDE CODE HANDOFF

> **Instructions for Claude Code:** Build the AREC CRM web application per this spec. This is Phase I1 of a multi-phase intelligence platform. This phase covers: Postgres schema, data migration from markdown, data access layer, Entra ID authentication, Flask web app with pipeline table + org detail + inline editing, and Azure deployment.

---

## B1. Project Context

AREC (Avila Real Estate Capital) has an existing single-user CRM built on markdown files in Dropbox, parsed by Python. Phase I1 replaces the markdown backend with PostgreSQL on Azure and adds multi-user auth via Microsoft Entra ID. The UI (pipeline table, org detail, inline editing) ports directly — same Flask/Jinja/vanilla JS patterns, new data layer.

**Existing local files (read-only references for migration):**

| File | Path | Purpose |
|------|------|---------|
| prospects.md | `~/Dropbox/Tech/ClaudeProductivity/crm/prospects.md` | Prospect records |
| organizations.md | `~/Dropbox/Tech/ClaudeProductivity/crm/organizations.md` | Org type lookup |
| config.md | `~/Dropbox/Tech/ClaudeProductivity/crm/config.md` | Stages, types, urgency, team, closings |
| offerings.md | `~/Dropbox/Tech/ClaudeProductivity/crm/offerings.md` | Offering names and targets |
| TASKS.md | `~/Dropbox/Tech/ClaudeProductivity/TASKS.md` | Task list (NOT migrated — stays in Dropbox) |

**Azure resources already provisioned (Part A):**
- PostgreSQL Flexible Server with database `arec_crm`
- App Service running Python 3.11
- Key Vault with secrets: `DATABASE-URL`, `CLIENT-ID`, `CLIENT-SECRET`, `TENANT-ID`
- Entra ID app registration with redirect URIs configured
- Connection details in `~/arec-crm-azure-env.txt`

---

## B2. Project Structure

```
arec-crm/
├── app.py                      # Flask application entry point
├── config.py                   # Configuration (reads Key Vault or env vars)
├── requirements.txt
├── startup.sh                  # Azure App Service startup command
├── .deployment                 # Azure deployment config
│
├── models/
│   ├── __init__.py
│   └── models.py               # SQLAlchemy models (all tables)
│
├── db/
│   ├── __init__.py
│   ├── crm_db.py               # Data access layer (replaces crm_reader.py)
│   └── schema.sql              # Raw SQL schema for reference/manual setup
│
├── auth/
│   ├── __init__.py
│   └── auth.py                 # MSAL Entra ID integration
│
├── migrate/
│   ├── migrate_markdown.py     # One-time migration: markdown → Postgres
│   └── validate_migration.py   # Post-migration validation
│
├── templates/
│   ├── base.html               # Layout with nav, auth state, flash messages
│   ├── login.html              # Login page
│   ├── pipeline.html           # Pipeline table with offering tabs
│   ├── org_detail.html         # Org detail with contacts + prospects
│   └── partials/
│       ├── pipeline_row.html   # Single prospect row (for inline edit responses)
│       └── prospect_form.html  # Prospect edit fields
│
├── static/
│   ├── style.css               # Stylesheet
│   └── crm.js                  # Client-side: inline editing, filters, search
│
└── tests/
    ├── test_migration.py       # Migration correctness tests
    └── test_crm_db.py          # Data access layer tests
```

---

## B3. Database Schema

Use SQLAlchemy models as the source of truth. Also produce `schema.sql` for reference.

### B3.1 Enums

```python
import enum

class OrgType(str, enum.Enum):
    INSTITUTIONAL = "INSTITUTIONAL"
    HNWI_FO = "HNWI / FO"
    BUILDER = "BUILDER"
    INTRODUCER = "INTRODUCER"

class UrgencyLevel(str, enum.Enum):
    HIGH = "High"
    MED = "Med"
    LOW = "Low"

class ClosingOption(str, enum.Enum):
    FIRST = "1st"
    SECOND = "2nd"
    FINAL = "Final"

class BriefingScope(str, enum.Enum):
    EXECUTIVE = "executive"
    FULL = "full"
    STANDARD = "standard"
    MINIMAL = "minimal"
```

### B3.2 Tables

Implement the full schema from the architecture doc Section 6. Key points:

- **Currency is BIGINT in cents.** `$50,000,000` → `5000000000`. The migration script handles conversion from markdown `$50,000,000` strings.
- **`users` table** — pre-seed with the 8 AREC team members (see B5).
- **`pipeline_stages` table** — pre-seed from config.md stages list.
- **`prospects.notes`** — Keep a `notes` TEXT field for Phase I1. The architecture says it gets replaced by `intelligence_notes` in Phase I3, but during Phase I1 we need it for the existing Notes data. Add a comment: `# Replaced by intelligence_notes in Phase I3`.
- **`next_action`** — Keep this field. It maps to the existing Next Action in prospects.md. Will be superseded by TASKS.md integration later.
- **`disambiguator`** — Some orgs have multiple prospect entries under the same offering, differentiated by contact name in parens in the markdown heading (e.g., `### UTIMCO (John Smith)`). The disambiguator stores that context.
- **`updated_by`** and `updated_at`** — On every write, set these to the logged-in user and current timestamp.

### B3.3 Indexes

Include all indexes from architecture doc Section 6.4.

### B3.4 Schema for Future Phases (DO NOT CREATE YET)

The following tables are defined in the architecture but belong to later phases. Do NOT create them in Phase I1: `interactions`, `intelligence_notes`, `signals`, `email_scan_log`, `briefing_history`. They are listed here only for context so you don't design anything that conflicts with them.

---

## B4. Configuration

`config.py` should support two modes:

**Local development:**
- Read `DATABASE_URL`, `CLIENT_ID`, `CLIENT_SECRET`, `TENANT_ID` from environment variables or `.env` file
- `REDIRECT_URI = http://localhost:5000/auth/callback`

**Azure production:**
- Read secrets from Azure Key Vault using managed identity
- `REDIRECT_URI = https://arec-crm-app.azurewebsites.net/auth/callback`

Use `azure-identity` + `azure-keyvault-secrets` for Key Vault access. Detect environment via `KEYVAULT_NAME` env var — if present, use Key Vault; otherwise, read from env vars.

```python
# Pseudocode for config loading
if os.environ.get("KEYVAULT_NAME"):
    # Production: read from Key Vault
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=f"https://{kv_name}.vault.azure.net", credential=credential)
    DATABASE_URL = client.get_secret("DATABASE-URL").value
    CLIENT_ID = client.get_secret("CLIENT-ID").value
    # ... etc
else:
    # Local dev: read from env vars / .env file
    DATABASE_URL = os.environ["DATABASE_URL"]
    CLIENT_ID = os.environ["CLIENT_ID"]
    # ... etc
```

---

## B5. Migration Script (`migrate/migrate_markdown.py`)

**Purpose:** One-time migration from markdown files to Postgres. Interactive — prompts for confirmation at each stage.

**Behavior:**

1. **Parse config.md** → seed `pipeline_stages` table
2. **Parse offerings.md** → seed `offerings` table
3. **Parse organizations.md** → seed `organizations` table
4. **Parse prospects.md** → seed `prospects` + `contacts` tables
5. **Seed users** → insert AREC team members (hardcoded list below)
6. **Validate** → run counts, print summary table
7. **Prompt** at each stage: "Parsed X offerings. Insert into database? [y/n]"

**AREC Team Members to Seed:**

| display_name | email | briefing_scope |
|-------------|-------|---------------|
| Tony Avila | tony@avilacapllc.com | executive |
| Oscar Vasquez | oscar@avilacapllc.com | full |
| Truman Flynn | truman@avilacapllc.com | standard |
| Zach Reisner | zach@avilacapllc.com | standard |
| James Walton | james@avilacapllc.com | standard |
| Anthony Albuquerque | anthony@avilacapllc.com | standard |
| Ian Morgan | ian@avilacapllc.com | standard |
| Kevin Van Gorder | kevin@avilacapllc.com | standard |

Notes on user seeding:
- `entra_id` — set to a placeholder (e.g., `pending-{email}`) since we won't know real Entra object IDs until first login. Update `entra_id` on first SSO login.
- `is_active` = true, `briefing_enabled` = true for all

**Markdown Parsing Rules:**

These are the exact formats the migration script must handle. Reference the existing `crm_reader.py` for behavior — the migration must produce the same data that the Python parsers currently extract.

**prospects.md format:**
```markdown
## Fund II

### Merseyside Pension Fund
- **Stage:** 6. Verbal
- **Target:** $50,000,000
- **Committed:** $0
- **Primary Contact:** Susannah Friar
- **Closing:** Final
- **Urgency:** High
- **Assigned To:** James Walton
- **Notes:** Sent Credit and Index Comparisons on 2/25.
- **Next Action:** Meeting March 2
- **Last Touch:** 2025-02-25

### UTIMCO (John Smith)
- **Stage:** 3. Meeting Set
...
```

Parsing rules:
- `## OfferingName` → match to offerings table
- `### OrgName` or `### OrgName (Disambiguator)` → match to organizations table; disambiguator stored separately
- `- **Field:** Value` → field-value pairs
- **Target/Committed:** Strip `$` and commas, parse as integer, multiply by 100 for cents storage
- **Primary Contact:** Match or create in contacts table, linked to the org
- **Assigned To:** Match by display_name to users table
- **Stage:** Store the full string (e.g., "6. Verbal")
- **Last Touch:** Parse as date (YYYY-MM-DD format)
- **Urgency:** Map "High"→High, "Med"→Med, "Low"→Low; blank→NULL
- **Closing:** Map "1st"→1st, "2nd"→2nd, "Final"→Final; blank→NULL

**organizations.md format:**
```markdown
## INSTITUTIONAL
- Merseyside Pension Fund
- NPS (Korea SWF)

## HNWI / FO
- Smith Family Office
...
```

Parsing rules:
- `## TypeName` → org_type enum
- `- OrgName` → organization name

**config.md format:**
```markdown
## Pipeline Stages
- 1. New Lead
- 2. Initial Outreach
- 3. Meeting Set
- 4. Materials Sent
- 5. Interested
- 6. Verbal
- 7. Committed
- 8. Closed / Funded
- 9. Declined
- 10. Dormant

## Types
...

## Closings
- 1st
- 2nd
- Final

## Team
- Tony Avila
- Oscar Vasquez
...
```

Parsing rules:
- `## Pipeline Stages` section: parse `- N. StageName` → pipeline_stages table. Stages 8+ are `is_terminal = true`. Sort order matches the number.
- Other sections: read for validation but not stored as separate tables (types are an enum, closings are an enum, team maps to users).

**offerings.md format:**
```markdown
## Fund II
- **Target:** $1,000,000,000
- **Hard Cap:** $1,500,000,000

## Homebuilder Finance Fund I
- **Target:** $500,000,000
...
```

Parsing rules:
- `## OfferingName` → offering name
- `- **Target:** $X` → target in cents
- `- **Hard Cap:** $X` → hard_cap in cents (may be absent → NULL)

**Migration output example:**
```
=== AREC CRM Migration ===
Source: ~/Dropbox/Tech/ClaudeProductivity/crm/

Parsing config.md...
  Found 10 pipeline stages
  Insert into database? [y/n]: y
  ✓ 10 stages inserted

Parsing offerings.md...
  Found 3 offerings:
    Fund II ($1,000,000,000 target)
    Homebuilder Finance Fund I ($500,000,000 target)
    ...
  Insert into database? [y/n]: y
  ✓ 3 offerings inserted

Parsing organizations.md...
  Found 67 organizations (42 INSTITUTIONAL, 15 HNWI/FO, 8 BUILDER, 2 INTRODUCER)
  Insert into database? [y/n]: y
  ✓ 67 organizations inserted

Parsing prospects.md...
  Found 72 prospects across 3 offerings
  Found 68 unique contacts
  Insert into database? [y/n]: y
  ✓ 72 prospects inserted
  ✓ 68 contacts inserted

Seeding users...
  8 team members
  Insert into database? [y/n]: y
  ✓ 8 users inserted

=== Validation ===
  pipeline_stages: 10 rows
  offerings: 3 rows
  organizations: 67 rows
  contacts: 68 rows
  prospects: 72 rows
  users: 8 rows

  Cross-reference check:
  ✓ All prospect.organization_id references valid
  ✓ All prospect.offering_id references valid
  ✓ All prospect.assigned_to references valid or NULL
  ✓ All contact.organization_id references valid
  ✓ All currency values > 0 are stored in cents

Migration complete.
```

---

## B6. Data Access Layer (`db/crm_db.py`)

This module replaces `crm_reader.py`. It provides all the data functions the Flask routes need. Use SQLAlchemy for all queries.

### Required Functions

```python
# --- Offerings ---
def get_offerings() -> list[dict]:
    """Return all offerings with computed commitment totals.
    Each dict: {id, name, target, hard_cap, total_committed, prospect_count}
    total_committed = SUM(prospects.committed) for that offering
    prospect_count = COUNT(prospects) for that offering
    """

def get_offering(offering_id: int) -> dict:
    """Single offering by ID."""

# --- Organizations ---
def get_organizations() -> list[dict]:
    """All orgs. Each: {id, name, type}"""

def get_organization_detail(org_id: int) -> dict:
    """Org with nested contacts and prospects (across all offerings).
    {id, name, type, notes,
     contacts: [{id, name, title, email, phone}],
     prospects: [{id, offering_name, stage, target, committed, ...}]}
    """

# --- Prospects ---
def get_prospects(offering_id: int, filters: dict = None) -> list[dict]:
    """Prospects for an offering, with optional filters.
    filters keys: stage, urgency, type, closing, assigned_to, search (org name substring)
    Each dict includes: org_name, org_type, stage, target, committed,
    primary_contact_name, closing, urgency, assigned_to_name, notes,
    next_action, last_touch, staleness_days, staleness_level
    Sort: stage DESC, urgency (High > Med > Low > NULL), target DESC
    staleness_level: 'green' if <7d, 'yellow' if 8-14d, 'red' if 15+d, 'gray' if NULL
    """

def get_prospect(prospect_id: int) -> dict:
    """Single prospect with all fields + org name + contact name + assigned user name."""

def update_prospect(prospect_id: int, field: str, value, updated_by_user_id: int) -> dict:
    """Update a single field on a prospect. Used for inline editing.
    Handles type conversion:
      - target/committed: accept string like "$50,000,000" or "50000000", store as cents
      - stage: accept full stage string
      - urgency: accept "High"/"Med"/"Low"/""
      - closing: accept "1st"/"2nd"/"Final"/""
      - assigned_to: accept user display_name, resolve to user_id
      - primary_contact: accept contact name, resolve to contact_id
      - notes/next_action: accept string
      - last_touch: accept YYYY-MM-DD string
    Sets updated_at = now(), updated_by = user_id.
    Returns updated prospect dict.
    """

def create_prospect(offering_id: int, org_id: int, data: dict, created_by_user_id: int) -> dict:
    """Create a new prospect. data contains initial field values."""

# --- Contacts ---
def get_contacts(org_id: int) -> list[dict]:
    """Contacts for an org."""

def create_contact(org_id: int, name: str, **kwargs) -> dict:
    """Create a contact linked to an org."""

# --- Pipeline Stages ---
def get_pipeline_stages() -> list[dict]:
    """All stages in sort order. Each: {id, number, name, is_terminal}"""

# --- Users ---
def get_users() -> list[dict]:
    """All active users. Each: {id, display_name, email}"""

def get_user_by_entra_id(entra_id: str) -> dict:
    """Find user by Entra object ID. Returns None if not found."""

def get_or_create_user_by_entra(entra_id: str, email: str, display_name: str) -> dict:
    """On first SSO login, match by email → update entra_id.
    If no email match, create new user.
    Used by the auth callback."""

# --- Config ---
def get_filter_options(offering_id: int) -> dict:
    """Return all values needed to populate filter dropdowns.
    {stages: [...], types: [...], urgency_levels: [...],
     closings: [...], team_members: [...]}
    """
```

### Currency Display Helper

```python
def format_currency_display(cents: int) -> str:
    """Convert cents to display string.
    5000000000 → '$50M'
    500000000 → '$5M'
    150000000 → '$1.5M'
    50000 → '$500'
    0 → '$0'
    """

def parse_currency_input(value: str) -> int:
    """Convert display string to cents.
    '$50,000,000' → 5000000000
    '50000000' → 5000000000
    '$50M' → 5000000000
    """
```

---

## B7. Authentication (`auth/auth.py`)

Use MSAL (Microsoft Authentication Library) for Python.

### Auth Flow

1. User visits any page → if no session → redirect to `/login`
2. `/login` → renders login page with "Sign in with Microsoft" button
3. Button → `/auth/login` → MSAL builds auth URL → redirect to Microsoft login
4. Microsoft redirects back to `/auth/callback` with auth code
5. `/auth/callback` → MSAL exchanges code for tokens → extract user info from ID token
6. Call `get_or_create_user_by_entra(entra_id, email, display_name)` → get local user record
7. Store `user_id`, `display_name`, `email` in Flask session
8. Redirect to `/crm`

### Key Implementation Details

- Use `msal.ConfidentialClientApplication`
- Authority: `https://login.microsoftonline.com/{TENANT_ID}`
- Scopes: `["User.Read"]` (basic profile only — Graph permissions for scanning come in Phase I2)
- Session secret: generate random key, store in Key Vault as `FLASK-SECRET-KEY` (add to Part A if needed, or generate at app startup and store in memory for dev)
- Token cache: server-side session (Flask session with filesystem or Redis backend). For Phase I1, filesystem sessions are fine.

### Auth Decorator

```python
def login_required(f):
    """Decorator. If user not in session → redirect to /login.
    Adds current_user to g for use in templates."""
```

### Templates Access

All templates should have access to:
- `current_user.display_name` — for header display
- `current_user.id` — for tracking who made edits

---

## B8. Flask Application (`app.py`)

### Routes

```python
# --- Auth ---
GET  /login              → login.html
GET  /auth/login         → redirect to Microsoft SSO
GET  /auth/callback      → process SSO callback, create session
GET  /auth/logout        → clear session, redirect to login

# --- CRM ---
GET  /crm                → pipeline.html (default offering)
GET  /crm?offering=2     → pipeline.html (specific offering)
GET  /crm?offering=2&stage=5.+Interested&urgency=High  → filtered
POST /crm/prospect/<id>  → inline edit (AJAX, returns updated row HTML)
GET  /crm/org/<id>       → org_detail.html
POST /crm/org/<id>/prospect → create new prospect for this org

# --- API (JSON, for AJAX) ---
GET  /api/filter-options?offering=2 → JSON filter dropdown values
GET  /api/prospects?offering=2&... → JSON prospect list (for JS filtering)
```

### Error Handling

- 401 → redirect to `/login`
- 404 → simple error page
- 500 → error page with "Something went wrong" (no stack traces in production)

---

## B9. Templates and UI

Port the existing local CRM dashboard UI. Same visual design, same interaction patterns. The templates below describe the target behavior.

### B9.1 `base.html`

- Header bar: "AREC CRM" on left, user name + logout link on right
- Flash message area
- Content block
- Color scheme: background `#f8f9fa`, header `#1a1a2e`, accent `#3b82f6`
- Font: `-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`

### B9.2 `pipeline.html`

**Offering tabs:**
- Horizontal tab bar near top of page
- One tab per offering (from `get_offerings()`)
- Active tab shows: `Fund II — $156M / $1B (16%)` with a thin progress bar
- Clicking a tab reloads with `?offering={id}`

**Filter bar:**
- Row of dropdowns: Stage, Type, Urgency, Closing, Assigned To
- Search input (org name, debounced)
- "Clear filters" link
- Dropdowns populated from `get_filter_options()`
- Filtering via query params (page reload) OR client-side JS filtering — implementer's choice, but client-side is preferred for speed

**Pipeline table:**

| Column | Width | Content |
|--------|-------|---------|
| Org | 200px | Org name (bold), click → org detail page |
| Type | 100px | Badge: INSTITUTIONAL, HNWI/FO, BUILDER, INTRODUCER |
| Stage | 130px | Inline dropdown |
| Target | 90px | Right-aligned, formatted as $50M |
| Committed | 90px | Right-aligned, formatted |
| Contact | 130px | Name text |
| Closing | 70px | Inline dropdown |
| Urgency | 80px | Inline dropdown, color-coded (red/amber/gray) |
| Assigned | 120px | Inline dropdown |
| Next Action | 200px | Inline text, click to edit |
| Last Touch | 100px | Date + staleness dot (🟢🟡🔴) |
| Last Modified By | 100px | User name, smaller text |

**Inline editing behavior:**
- Dropdowns (`<select>`) for: Stage, Closing, Urgency, Assigned To
- Click-to-edit text for: Next Action, Notes
- On change → POST `/crm/prospect/{id}` with `{field, value}` → server returns updated row HTML → replace row in DOM
- Show subtle save indicator (brief green flash on the cell)
- `updated_by` automatically set to current logged-in user

**Sort:**
- Default: Stage DESC, Urgency (High > Med > Low > NULL), Target DESC
- Column headers clickable for sort override

**Urgency row highlighting:**
- Rows with `urgent = true` (High urgency) get a light yellow background `#fffbeb`

### B9.3 `org_detail.html`

**Header section:**
- Org name (large)
- Type badge
- Org notes (editable textarea, save on blur)

**Contacts table:**
- Name, Title, Email, Phone
- Each field editable inline
- "Add contact" button at bottom

**Prospects across offerings:**
- Section per offering where this org has a prospect
- Same field layout as pipeline table, but for this single org
- All fields editable

**Notes section:**
- Full notes textarea (will be replaced by intelligence timeline in Phase I3)
- Save on blur

### B9.4 Client-Side JavaScript (`static/crm.js`)

- **Inline edit handler:** On `change` or `blur` of editable fields → POST to `/crm/prospect/{id}` → update DOM
- **Filter handler:** On dropdown change → filter table rows (client-side preferred)
- **Search handler:** On input (debounced 300ms) → filter table rows by org name
- **Sort handler:** On column header click → sort table rows
- **Currency formatting:** Display cents as `$50M` / `$1.5M` / `$500K`
- **Staleness calculation:** Compute from `last_touch` date, assign dot color
- **Save feedback:** Brief green flash animation on saved cells

---

## B10. Deployment

### B10.1 `requirements.txt`

```
Flask>=3.0
SQLAlchemy>=2.0
psycopg2-binary
msal
azure-identity
azure-keyvault-secrets
gunicorn
python-dotenv
```

### B10.2 `startup.sh`

```bash
gunicorn --bind=0.0.0.0:8000 --workers=2 --timeout=120 app:app
```

### B10.3 `.deployment`

```
[config]
SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

### B10.4 Deploy Command

After the app is built and tested locally, deploy via:

```bash
cd arec-crm
az webapp up --resource-group arec-crm-rg --name arec-crm-app --runtime "PYTHON:3.11"
```

### B10.5 Local Development

For local dev, create `.env` file from `~/arec-crm-azure-env.txt`:

```bash
cp ~/arec-crm-azure-env.txt arec-crm/.env
```

Then run:

```bash
cd arec-crm
pip install -r requirements.txt
flask run
```

The app should be accessible at `http://localhost:5000`. SSO redirects to Microsoft login and back to `http://localhost:5000/auth/callback`.

---

## B11. Migration Execution

After the app code is complete and the schema is applied:

1. Apply schema to Azure Postgres:

```bash
source ~/arec-crm-azure-env.txt
cd arec-crm
python -c "from models import Base; from db import engine; Base.metadata.create_all(engine)"
```

Or if using raw SQL:

```bash
psql "$DATABASE_URL" -f db/schema.sql
```

2. Run migration:

```bash
python migrate/migrate_markdown.py \
  --source ~/Dropbox/Tech/ClaudeProductivity/ \
  --database-url "$DATABASE_URL"
```

3. Run validation:

```bash
python migrate/validate_migration.py --database-url "$DATABASE_URL"
```

---

## B12. Acceptance Criteria

Phase I1 is complete when ALL of the following pass:

### Schema + Migration
- [ ] All tables created in Azure Postgres with correct types and constraints
- [ ] Migration script parses all 5 markdown files without errors
- [ ] Migration is interactive (prompts at each stage)
- [ ] All prospects migrated with correct currency (cents), stage, urgency, closing
- [ ] All org → type mappings correct
- [ ] All contact → org links correct
- [ ] All prospect → assigned_to user links correct (or NULL for unassigned)
- [ ] Disambiguator parsed correctly for multi-entry orgs
- [ ] Validation script confirms zero data loss (row counts match source files)
- [ ] Currency round-trip: cents in DB → display as `$50M` → edit as `$50,000,000` → stored as cents

### Authentication
- [ ] Unauthenticated user redirected to `/login`
- [ ] "Sign in with Microsoft" redirects to Microsoft SSO
- [ ] Successful login creates session and redirects to `/crm`
- [ ] User matched by email on first login, `entra_id` populated
- [ ] `current_user` available in all templates
- [ ] Logout clears session

### Pipeline Table
- [ ] Offering tabs display all offerings with commitment progress
- [ ] Pipeline table shows all prospects for selected offering
- [ ] Default sort: Stage DESC → Urgency (High first) → Target DESC
- [ ] All columns display correctly (org name clickable, currency right-aligned, staleness dots)
- [ ] Inline dropdown editing works for: Stage, Closing, Urgency, Assigned To
- [ ] Inline text editing works for: Next Action
- [ ] Edits save via AJAX, row updates without page reload
- [ ] `updated_by` and `updated_at` set on every edit
- [ ] `Last Modified By` column shows the user who last edited
- [ ] Urgency High rows have light yellow background
- [ ] Filters work: Stage, Type, Urgency, Closing, Assigned To
- [ ] Search by org name works (client-side, instant)
- [ ] "Clear filters" resets all

### Org Detail Page
- [ ] Shows org name, type, notes
- [ ] Lists all contacts with inline editing
- [ ] Shows prospects across all offerings
- [ ] All prospect fields editable
- [ ] "Add contact" works
- [ ] Changes save correctly to database

### Deployment
- [ ] App deploys to Azure App Service
- [ ] Key Vault secrets read correctly in production
- [ ] App accessible at `https://arec-crm-app.azurewebsites.net`
- [ ] SSO works in production (redirect URI matches)
- [ ] No secrets in source code or logs

### Parallel Operation
- [ ] Local/Cowork CRM continues to function unchanged (reads/writes markdown files in Dropbox)
- [ ] Azure CRM is a separate, independent system
- [ ] No shared state between local and Azure (migration is a one-time copy, not ongoing sync)

---

## B13. What This Phase Does NOT Include

Explicitly out of scope for Phase I1 — do not build these:

- `interactions` table or intelligence layer (Phase I3)
- `intelligence_notes` or `signals` tables (Phase I3)
- Graph email scanning (Phase I2)
- Shared mailbox processor (Phase I2)
- Meeting transcript processing (Phase I5)
- Briefing engine or email sending (Phase I4)
- `email_scan_log` or `briefing_history` tables (Phase I2/I4)
- Mobile PWA (deferred)
- Analytics or charts
- Task management (stays in TASKS.md / Dropbox)
- Any Cowork/Claude Desktop integration
- Any modification to the existing local CRM system

---

## B14. Email Addresses

For reference, AREC email domain is `avilacapllc.com` for all team members and the CRM shared mailbox (`crm@avilacapllc.com`). The shared mailbox is not used in Phase I1 but is mentioned here to avoid confusion if you encounter it in the markdown files.
