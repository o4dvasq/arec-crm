# SPEC: Postgres-Local Migration (Branch 1 of 4)

**Project:** arec-crm
**Date:** 2026-03-14
**Status:** Ready for implementation

---

## Objective

Replace the markdown file backend (`crm_reader.py`) with a local PostgreSQL backend (`crm_db.py`) while changing absolutely nothing else — same routes, same templates, same UI, same single-user local dev experience. This is the first of four incremental branches that decompose the current `azure-migration` mega-branch into testable, isolated milestones. The app must look and behave identically to the `deprecated-markdown` baseline, but read/write all CRM data from `postgresql://localhost/arec_crm` instead of flat files in `crm/`.

---

## Context for Claude Code

You have **zero context** from the design conversation. Here is what you need to know:

The `azure-migration` branch attempted three things simultaneously — Postgres migration, Azure deployment, and multi-user auth — which made debugging impossible. We are starting over with an incremental approach:

| Branch | What changes | What stays the same |
|--------|-------------|---------------------|
| **1. `postgres-local`** (this spec) | Data layer: markdown → local Postgres | Routes, templates, UI, single-user, runs locally |
| 2. `azure-db` | DATABASE_URL points to Azure Postgres | Everything else (still runs locally) |
| 3. `azure-deploy` | App hosted on Azure App Service | No code changes, just infra |
| 4. `multi-user` | Entra SSO, roles, Graph API | Built on stable deployed app |

**You are implementing Branch 1 only.**

---

## Starting Point

Branch off `deprecated-markdown` (the original single-commit baseline). Do NOT cherry-pick from `azure-migration`. You will port specific files by reading them from that branch with `git show azure-migration:<path>`, then adapting them to fit the markdown-era app structure.

```bash
git checkout deprecated-markdown
git checkout -b postgres-local
```

---

## Scope

### In Scope

1. **Port the database layer** — bring over `app/models.py`, `app/db.py`, `app/sources/crm_db.py`, and `app/auto_migrate.py` from `azure-migration`, then adapt them:
   - Strip all multi-user columns and references (no `updated_by`, `created_by`, `scanned_by` foreign keys to `users` table)
   - Strip `User` model entirely (no auth system in this branch)
   - Strip `graph_consent_granted`, `graph_consent_date` columns
   - Keep `assigned_to` as a plain `String` field (team member name), NOT a foreign key to users
   - Keep all 13 remaining tables: Offering, Organization, Contact, PipelineStage, Prospect, Interaction, EmailScanLog, Brief, ProspectNote, UnmatchedEmail, PendingInterview, ProspectTask (plus Contact relationships)
   - `crm_db.py` functions must return the **exact same data shapes** that `crm_reader.py` returns — dicts with the same keys, same currency formatting, same date formats — so templates and JS don't need changes

2. **Replace all imports** — every file that does `from app.sources.crm_reader import ...` or `from app.sources import crm_reader` must switch to `from app.sources.crm_db import ...`. The function signatures are intentionally compatible. Files to update:
   - `app/delivery/crm_blueprint.py`
   - `app/delivery/dashboard.py`
   - `app/briefing/brief_synthesizer.py` (or `generator.py` / `prompt_builder.py` — whatever exists)
   - Any other file importing `crm_reader`

3. **Write a seed script** (`scripts/seed_from_markdown.py`) that reads the existing markdown/JSON files and populates the local Postgres database:
   - Read `crm/config.md` → seed `pipeline_stages` table
   - Read `crm/offerings.md` → seed `offerings` table
   - Read `crm/organizations.md` → seed `organizations` table
   - Read `crm/contacts_index.md` + `memory/people/*.md` → seed `contacts` table
   - Read `crm/prospects.md` → seed `prospects` table (resolve org/offering/contact foreign keys)
   - Read `crm/interactions.md` → seed `interactions` table
   - Read `crm/meeting_history.md` → seed `interactions` table (type=Meeting)
   - Read `crm/briefs.json` → seed `briefs` table
   - Read `crm/email_log.json` → seed `email_scan_log` table
   - Read `crm/prospect_notes.json` → seed `prospect_notes` table
   - Read `crm/unmatched_review.json` → seed `unmatched_emails` table
   - Read `crm/pending_interviews.json` → seed `pending_interviews` table
   - Read task lines from `TASKS.md` (org-tagged tasks only) → seed `prospect_tasks` table
   - The script should be idempotent (safe to run multiple times — upsert or clear-and-reseed)
   - The script should import and use `crm_reader.py` functions to parse the markdown (it's the last consumer of that module)

4. **Database initialization** — `dashboard.py` must:
   - Call `db.init_app(app)` on startup
   - Call `auto_migrate(engine)` to ensure schema is current
   - Continue registering blueprints as before
   - Use `DEV_USER` env var pattern is NOT needed yet (no auth), but leave the door open

5. **Update requirements** — ensure `sqlalchemy>=2.0.0` and `psycopg2-binary>=2.9.9` are in requirements files (they may already be on `deprecated-markdown`)

6. **Write/port tests** — bring over the test suite structure from `azure-migration`:
   - `app/tests/conftest.py` with SQLite in-memory fixtures
   - `app/tests/test_crm_db.py` — test all major crm_db functions
   - Tests must pass with `python3.12 -m pytest app/tests/ -v --tb=short`
   - Target: at minimum, test CRUD for orgs, contacts, prospects, interactions, briefs, tasks

7. **Keep `crm_reader.py` in the repo** but do NOT import it from any production code. It is used only by the seed script. Add a comment at the top: `# DEPRECATED: Used only by scripts/seed_from_markdown.py. All production code uses crm_db.py.`

8. **Preserve the tasks blueprint** — `app/delivery/tasks_blueprint.py` currently reads from `TASKS.md` via `memory_reader.py`. Convert it to read from the `prospect_tasks` table via `crm_db.py` instead. The task routes in dashboard.py (`/api/task/complete`, `/api/task/add`, `/api/task/status`) should also use `crm_db.py`.

### Explicitly Out of Scope

- **No Azure deployment** — no `startup.sh`, no GitHub Actions, no App Service config
- **No authentication** — no Entra SSO, no MSAL, no `User` model, no `@login_required`, no `g.user`, no `entra_auth.py`, no admin blueprint
- **No multi-user features** — no `updated_by`/`created_by` audit columns, no role-based access
- **No Graph API** — no `ms_graph.py`, no `graph_poller.py`, no email polling
- **No new features** — no contact enrichment, no org merging, no prospect detail overhaul
- **No UI changes** — templates render identically. If a template references `g.user`, stub it or remove the reference with a static name
- **No schema changes beyond what `crm_reader.py` data requires** — if azure-migration added columns that don't correspond to markdown data, don't include them

---

## Data Model / Schema

Port these tables from `azure-migration:app/models.py`, with modifications noted:

### offerings
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| name | String(255) | unique, not null |
| target | BigInteger | stored in cents, nullable |
| hard_cap | BigInteger | stored in cents, nullable |
| created_at | TIMESTAMP | default=now |
| updated_at | TIMESTAMP | default=now |

*Removed: `updated_by` FK*

### organizations
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| name | String(255) | unique, not null |
| type | String(100) | not null |
| domain | String(255) | default='' |
| notes | Text | default='' |
| created_at | TIMESTAMP | default=now |
| updated_at | TIMESTAMP | default=now |

*Removed: `updated_by` FK*

### contacts
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| name | String(255) | not null |
| organization_id | Integer FK → organizations.id | CASCADE, not null |
| title | String(255) | default='' |
| email | String(255) | default='' |
| phone | String(255) | default='' |
| notes | Text | default='' |
| created_at | TIMESTAMP | default=now |
| updated_at | TIMESTAMP | default=now |

*Removed: `linkedin_url`, `enriched_at`, `enrichment_source`, `updated_by` — these are Branch 4 features. Unique constraint on (name, organization_id).*

### pipeline_stages
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| number | Integer | unique, not null |
| name | String(100) | unique, not null |
| is_terminal | Boolean | default=False |
| sort_order | Integer | not null |

### prospects
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| organization_id | Integer FK → organizations.id | CASCADE, not null |
| offering_id | Integer FK → offerings.id | CASCADE, not null |
| stage | String(50) | not null, default='1. Prospect' |
| target | BigInteger | default=0, stored in cents |
| committed | BigInteger | default=0, stored in cents |
| primary_contact_id | Integer FK → contacts.id | nullable |
| closing | String(20) | nullable (store as plain string: '1st', '2nd', 'Final') |
| urgency | String(20) | nullable (store as plain string: 'High', 'Med', 'Low') |
| assigned_to | String(255) | nullable, plain text team member name |
| notes | Text | default='' |
| last_touch | Date | nullable |
| relationship_brief | Text | default='' |
| brief_refreshed | Date | nullable |
| disambiguator | String(255) | nullable |
| created_at | TIMESTAMP | default=now |
| updated_at | TIMESTAMP | default=now |

*Key change: `assigned_to` is String not FK. `closing` and `urgency` are String not Enum (simpler, matches markdown flexibility). Removed: `next_action`, `updated_by`. Added: `brief_refreshed` (was tracked in markdown).*

### interactions
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| organization_id | Integer FK → organizations.id | CASCADE, not null |
| offering_id | Integer FK → offerings.id | nullable |
| contact_id | Integer FK → contacts.id | nullable |
| interaction_date | Date | not null |
| type | String(50) | not null (Email, Meeting, Call, Note) |
| subject | String(500) | default='' |
| summary | Text | default='' |
| source | String(50) | default='manual' |
| source_ref | String(500) | default='' |
| created_at | TIMESTAMP | default=now |

*Removed: `team_members` JSON, `created_by` FK. Changed: type and source are plain strings, not Enums.*

### email_scan_log
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| message_id | String(500) | unique, not null |
| from_email | String(255) | default='' |
| to_emails | Text | default='' |
| subject | String(500) | default='' |
| email_date | Date | nullable |
| org_name | String(255) | default='' |
| matched | Boolean | default=False |
| snippet | Text | default='' |
| scanned_at | TIMESTAMP | default=now |

*Removed: `outlook_url`, `scanned_by` FK*

### briefs
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| brief_type | String(50) | not null |
| key | String(255) | not null |
| narrative | Text | default='' |
| at_a_glance | Text | default='' |
| content_hash | String(64) | default='' |
| created_at | TIMESTAMP | default=now |
| updated_at | TIMESTAMP | default=now |

*Unique constraint on (brief_type, key)*

### prospect_notes
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| org_name | String(255) | not null |
| offering_name | String(255) | not null |
| author | String(255) | default='' |
| text | Text | not null |
| created_at | TIMESTAMP | default=now |

### unmatched_emails
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| email | String(255) | not null |
| display_name | String(255) | default='' |
| subject | String(500) | default='' |
| date | Date | nullable |
| created_at | TIMESTAMP | default=now |

### pending_interviews
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| org_name | String(255) | not null |
| offering_name | String(255) | default='' |
| reason | Text | default='' |
| created_at | TIMESTAMP | default=now |

### prospect_tasks
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| org_name | String(255) | not null |
| text | Text | not null |
| owner | String(255) | default='' |
| priority | String(20) | default='Med' |
| status | String(20) | default='open' |
| created_at | TIMESTAMP | default=now |
| completed_at | TIMESTAMP | nullable |

---

## Business Rules

1. **Currency is stored as BIGINT cents.** $50M = 5,000,000,000 cents. Display helpers `_format_currency()` and `_parse_currency()` in `crm_db.py` handle conversion. Templates receive formatted strings like "$50M" — they never see raw cents.

2. **Prospect identity is (org_name, offering_name, disambiguator).** The disambiguator is optional and appears in markdown as `### Org Name (Disambiguator)`. Most prospects have no disambiguator.

3. **Contact identity is (name, organization_id).** The `slug` concept from markdown (`memory/people/first-last.md`) maps to contacts by name. `crm_db.py` must provide `_name_to_slug()` and `load_person(slug)` that work by converting slug back to name and querying the contacts table.

4. **Stage values are stored as strings** like `"5. Interested"` — the number prefix is part of the value, matching the markdown convention.

5. **`load_crm_config()` must return a dict** with keys: `stages` (list), `terminal_stages` (list), `org_types` (list), `closing_options` (list), `team` (list of dicts with name/email), `urgency_levels` (list). On the markdown branch this was parsed from `config.md`. In the Postgres version, this can be hardcoded or loaded from `pipeline_stages` table + hardcoded config values. The simplest approach: seed `pipeline_stages` from config.md, hardcode the rest (org_types, closing_options, team, urgency_levels) since they change rarely.

6. **Internal domains** (`avilacapllc.com`, `avilacapital.com`, `builderadvisorgroup.com`) and **generic domains** (`gmail.com`, `yahoo.com`, etc.) are excluded from org-domain matching. These constants should remain in `crm_db.py`.

7. **The `load_email_log()` return format** must match the JSON structure: `{"version": 1, "lastScan": "...", "emails": [...]}`. Templates and JS may depend on this shape.

8. **Brief synthesis** — `brief_synthesizer.py` calls Claude API with relationship data and expects `{narrative, at_a_glance}` JSON back. The data-gathering functions (`collect_relationship_data`, `compute_content_hash`) that feed it must work against the DB, not markdown.

---

## Integration Points

- **Reads from:** Local PostgreSQL (`postgresql://localhost/arec_crm`)
- **Reads from (seed only):** Markdown files in `crm/` directory and `memory/people/*.md`
- **Writes to:** Local PostgreSQL
- **Calls:** Claude API (Anthropic) for brief synthesis (unchanged from markdown version)
- **Does NOT call:** Microsoft Graph API, Azure Key Vault, Entra ID

---

## UI / Interface

**No changes.** Every template, every JS file, every CSS file remains identical. The data shapes returned by `crm_db.py` must exactly match what `crm_reader.py` returned so templates render correctly.

If any template references `g.user` (from the auth system), replace with a hardcoded stub or remove the reference. On `deprecated-markdown`, there should be no `g.user` references since auth didn't exist yet — but verify.

---

## Constraints

1. **Do not cherry-pick commits from `azure-migration`.** Read files with `git show azure-migration:<path>` and adapt them. The azure-migration versions have multi-user code woven throughout that must be stripped.

2. **Function signature compatibility is critical.** Every public function in `crm_db.py` that replaces a `crm_reader.py` function must accept the same arguments and return the same data shape. If `crm_reader.load_prospects()` returns `[{"org": "Foo", "Stage": "5. Interested", "Target": "$50M", ...}]`, then `crm_db.load_prospects()` must return the exact same structure.

3. **No Enums in the ORM models for this branch.** Use plain strings for `closing`, `urgency`, `type`, `source`. Enums caused migration headaches on Azure — we can add them later when the app is stable.

4. **The seed script must be the ONLY consumer of `crm_reader.py`.** After seeding, all production code paths go through `crm_db.py`.

5. **Tests use SQLite in-memory** (via `conftest.py` setting `TEST_DATABASE_URL=sqlite:///:memory:`). All tests must pass without a running Postgres instance.

6. **Local Postgres setup is a prerequisite, not part of this spec.** Document the setup in a comment at the top of `dashboard.py` or in a `LOCAL_SETUP.md`:
   ```
   brew install postgresql@16
   createdb arec_crm
   echo 'DATABASE_URL=postgresql://localhost/arec_crm' >> app/.env
   python scripts/seed_from_markdown.py
   python app/delivery/dashboard.py
   ```

7. **`auto_migrate.py` must be additive-only.** It creates missing tables and adds missing columns. It never drops, renames, or alters existing columns. It must work on both PostgreSQL (production) and SQLite (tests).

---

## Acceptance Criteria

1. `git checkout postgres-local` succeeds and the branch exists off `deprecated-markdown`
2. `createdb arec_crm && python scripts/seed_from_markdown.py` populates all tables from markdown files without errors
3. `python app/delivery/dashboard.py` starts the Flask app on `http://localhost:8000` without errors
4. Pipeline view (`/crm/`) renders with all prospects, stages, and offerings — visually identical to the markdown version
5. Clicking into a prospect detail page shows all fields, contacts, interactions, and briefs
6. Editing a prospect (stage, target, notes, assigned_to) persists to Postgres and survives app restart
7. Creating a new prospect, org, or contact works and appears in the pipeline/lists
8. Deleting a prospect works
9. Organization detail pages show contacts, prospects, and email history
10. Person detail pages show contact info and email history
11. Brief synthesis (Claude API) generates and saves briefs to the `briefs` table
12. Task creation and completion from prospect detail pages works via `prospect_tasks` table
13. Unmatched email list loads and resolve/dismiss actions work
14. Export to Excel (`/api/export`) works
15. `python3.12 -m pytest app/tests/ -v --tb=short` passes all tests (target: 50+ tests covering CRUD for all major entities)
16. No file in `app/delivery/`, `app/briefing/`, or `app/` imports `crm_reader` (only `scripts/seed_from_markdown.py` does)
17. The `crm/` markdown directory still exists but is not read by any production code path
18. Feedback loop prompt has been run: after implementation, do a full walkthrough of the app clicking every page and verifying data renders correctly

---

## Files Likely Touched

| File | Action | Reason |
|------|--------|--------|
| `app/models.py` | **Rewrite** | Port from azure-migration, strip multi-user columns |
| `app/db.py` | **Rewrite** | Port from azure-migration (engine/session setup) |
| `app/sources/crm_db.py` | **Create** | Port from azure-migration, strip multi-user code, ensure return-shape parity with crm_reader |
| `app/sources/crm_reader.py` | **Edit** | Add deprecation comment at top; do not delete |
| `app/auto_migrate.py` | **Create** | Port from azure-migration |
| `app/delivery/dashboard.py` | **Edit** | Add db.init_app + auto_migrate; change imports from crm_reader to crm_db |
| `app/delivery/crm_blueprint.py` | **Edit** | Change all crm_reader imports to crm_db |
| `app/delivery/tasks_blueprint.py` | **Edit** | Replace memory_reader/TASKS.md reads with crm_db task functions |
| `app/briefing/brief_synthesizer.py` | **Edit** | Change imports if it references crm_reader |
| `app/briefing/generator.py` | **Edit** | Change imports if it references crm_reader |
| `app/briefing/prompt_builder.py` | **Edit** | Change imports if it references crm_reader |
| `scripts/seed_from_markdown.py` | **Create** | New script: reads markdown → writes to Postgres |
| `app/tests/conftest.py` | **Create** | SQLite in-memory test fixtures |
| `app/tests/test_crm_db.py` | **Create** | Tests for all major crm_db functions |
| `requirements.txt` | **Edit** | Ensure sqlalchemy, psycopg2-binary present |
| `app/.env.example` | **Create** | Document DATABASE_URL |
| `CLAUDE.md` | **Edit** | Update run commands and key files for this branch |

---

## Implementation Order (Suggested)

1. Create branch off `deprecated-markdown`
2. Port `app/db.py` and `app/models.py` (stripped-down versions)
3. Port `app/auto_migrate.py`
4. Port `app/sources/crm_db.py` (stripped-down, return-shape-compatible)
5. Write `scripts/seed_from_markdown.py`
6. Update `app/delivery/dashboard.py` (add DB init, change imports)
7. Update `app/delivery/crm_blueprint.py` (change imports)
8. Update `app/delivery/tasks_blueprint.py` (change imports + logic)
9. Update briefing files (change imports)
10. Write `app/tests/conftest.py` and `app/tests/test_crm_db.py`
11. Run tests, fix failures
12. Manual walkthrough of every page
13. Seed local Postgres and verify full app functionality
