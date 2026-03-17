# Cowork Task: Gather Phase I1 Prerequisites

**Date:** March 8, 2026  
**Context:** Oscar is in a Claude.ai conversation building the Phase I1 spec for the AREC Intelligence Platform (Azure migration). We need information from Oscar's local machine to produce the Claude Code handoff.

---

## What's Happened So Far

1. Local CRM Phases 1–4 are complete
2. Architecture doc finalized: `AREC-INTELLIGENCE-PLATFORM-ARCHITECTURE.md` (in project files)
3. Azure subscription created under Avila Capital LLC tenant (`064d6342-5dc5-424e-802f-53ff17bc02be`)
4. Oscar is logged into Azure CLI under tenant `ebd42ab2-7f1c-4d40-8b44-f5ecc51d2659`
5. No resource group created yet

---

## What We Need From You

Please examine Oscar's local CRM codebase and answer these questions. The goal is to produce a Phase I1 Claude Code spec that knows exactly what exists today.

### 1. Directory Layout
Navigate to the CRM project directory (likely in `~/Dropbox/Tech/ClaudeProductivity/` or wherever the Flask app lives) and provide:
- Full directory tree (files and folders)
- Specifically locate: `crm_reader.py`, `dashboard.py` (or equivalent main Flask file), templates, static files, any `config.py` or `.env`

### 2. crm_reader.py — Function Signatures
Open `crm_reader.py` and list all public function signatures with their return types. Phase I1 needs `crm_db.py` to be a drop-in replacement with the same function signatures so the Flask routes don't change.

### 3. Flask Routes
Open the main Flask file and list all CRM-related routes:
- URL pattern
- HTTP method
- What it does (one-line summary)
- Which `crm_reader.py` functions it calls

### 4. Templates & Static Files
List all HTML templates and static assets (CSS, JS) used by the CRM pages. Note which ones are CRM-specific vs. morning briefing or other features.

### 5. Config / Environment
Check for:
- Any `.env` file or config variables the Flask app uses
- How the app currently starts (e.g., `flask run`, `python dashboard.py`, etc.)
- Port number and any other runtime config

### 6. Markdown File Samples
Grab the first ~20 lines of each CRM markdown file so the migration script knows the exact format:
- `crm/prospects.md`
- `crm/organizations.md`
- `crm/config.md`
- `crm/offerings.md`
- `TASKS.md` (just to confirm format — this stays in Dropbox, not migrated)

### 7. Entra ID Status
Ask Oscar:
- Has he registered an app in Microsoft Entra ID for this project yet?
- Does he want the CRM accessible from the public internet (SSO-gated) or restricted to AREC network?
- Does he have a DNS record for `crm.avilacapllc.com` or should we use default Azure URL for now?

---

## Output

Please compile your findings into a single markdown response that Oscar can paste back into the Claude.ai conversation. Format it as a clean summary — no need to paste entire files, just the structural information requested above.
