SPEC: AREC CRM Multi-User Platform
Project: arec-crm
Date: 2026-03-11
Status: Ready for implementation

---

## 1. Objective

Transform the AREC CRM from Oscar's single-user local tool into a multi-user fundraising platform for the AREC team. This means: enforcing Entra ID SSO for all pages, onboarding Tony's EA as the first new user, replacing the local markdown backend with PostgreSQL on Azure, building automated Graph API email polling to feed the canonical people knowledge base, and stripping out all personal productivity features (tasks, briefings, meeting summaries) that now live in Overwatch.

## 2. Scope

### In Scope

- **Strip personal productivity features**: Remove dashboard home (tasks, calendar, meetings), task blueprint, briefing modules, memory system. The CRM's root route (`/`) redirects to `/crm`.
- **Enforce Entra ID SSO on all routes**: Every page and API endpoint requires authentication. `@login_required` decorator on all blueprint routes. Only `@avilacapllc.com` accounts.
- **Commit to PostgreSQL backend**: Remove `crm_reader.py` (markdown parser). All routes import from `crm_db.py` only. Delete local markdown CRM files (`crm/prospects.md`, `crm/organizations.md`, etc.) from the deployed codebase.
- **Graph API background email polling**: Hourly Azure Function (or App Service background thread) scans each team member's mailbox, creates interactions, enriches the canonical people knowledge base.
- **Canonical people knowledge base write model**: AI-maintained contact intelligence in the `contacts` table. Manual edits limited to contact info fields (phone, email, org affiliation). Relationship context, email history, and intelligence notes are AI-only.
- **User onboarding**: Tony's EA added to Entra ID tenant, seeded in `users` table, assigned `@avilacapllc.com` email.
- **Remove morning briefing entirely**: Delete `app/main.py`, `app/briefing/` directory, `briefing_latest.md`. No scheduled or on-demand briefing generation in the CRM.
- **Per-user data visibility**: Prospects filtered by `assigned_to` on pipeline views. Interactions attributed to the user whose mailbox they came from.

### Out of Scope

- Personal dashboard or mixed task board (that's Overwatch)
- Overwatch integration or sync
- Per-user briefing generation (removed entirely; future Overwatch feature)
- Mobile app or responsive redesign
- Role-based access control beyond basic auth (all authenticated users see the same CRM features)
- API endpoint authentication (later phase — currently SSO covers web UI)
- Notion sync (permanently disabled per project conventions)

## 3. Business Rules

- **Authentication is mandatory**: No anonymous access to any route or API endpoint. Unauthenticated requests redirect to Entra ID login.
- **Tenant restriction**: Only `@avilacapllc.com` accounts in Entra ID tenant `ebd42ab2-7f1c-4d40-8b44-f5ecc51d2659` can authenticate.
- **People knowledge base is AI-maintained**: The `contacts` table stores relationship context, email history summaries, and intelligence notes. These fields are written only by the Graph API polling system and brief synthesis engine. Users can manually edit: name, email, phone, organization affiliation. Users cannot manually edit: relationship narrative, email history, intelligence notes.
- **Email polling runs per-user**: Each team member's mailbox is scanned independently. The system needs a Graph API token with `Mail.Read` scope for each user. Phase 1 uses a single app registration with delegated permissions; users consent on first login.
- **Two-tier email matching** (existing logic, preserved): Domain match first (Tier 1), then person email lookup (Tier 2). Unmatched emails go to `unmatched_emails` table for manual review.
- **Interaction attribution**: Every auto-captured interaction records `created_by` = the user whose mailbox it came from. Manual interactions record the logged-in user.
- **Organization field is always a dropdown**: The Organization/Company field on People Detail edit must use a `<select>` populated from `/crm/api/orgs`. Never a free-text input.
- **Prospect task creation uses `/crm/api/tasks` POST**: Never use `/crm/api/followup`.
- **"Settler" filter**: Exclude anything regarding "Settler" from any automated surfaces (preserved from existing convention).

## 4. Data Model / Schema Changes

### Existing Tables (no changes needed)

The PostgreSQL schema from Phase I1 already supports multi-user. Key tables:

| Table | Multi-User Ready? | Notes |
|-------|-------------------|-------|
| `users` | Yes | 8 users seeded. Has `entra_id`, `email`, `display_name`, `last_login`, `briefing_enabled`, `briefing_scope` |
| `organizations` | Yes | No user ownership — shared across team |
| `contacts` | Yes | Shared canonical knowledge base |
| `prospects` | Yes | `assigned_to` FK to `users` for filtering |
| `interactions` | Yes | `created_by` FK to `users` for attribution |
| `email_scan_log` | Yes | `message_id` UNIQUE for dedup |
| `offerings` | Yes | Shared (Fund I, Fund II, etc.) |
| `briefs` | Yes | UNIQUE on `(brief_type, key)` |
| `prospect_notes` | Yes | Timestamped, attributable |
| `unmatched_emails` | Yes | Review queue |

### New Columns

```sql
-- Add graph_consent_granted to track which users have consented to email scanning
ALTER TABLE users ADD COLUMN graph_consent_granted BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN graph_consent_date TIMESTAMP;

-- Add scanned_by to email_scan_log to track which user's mailbox the email came from
ALTER TABLE email_scan_log ADD COLUMN scanned_by INTEGER REFERENCES users(id);
```

### Contacts Table — Field Access Control

No schema change, but enforce at the application layer:

| Field | Editable By | Written By |
|-------|-------------|------------|
| `name` | User (manual) | Migration, user |
| `email` | User (manual) | Migration, user, Graph polling |
| `phone` | User (manual) | Migration, user |
| `organization_id` | User (manual) | Migration, user |
| `role` | User (manual) | Migration, user |
| `type` | AI only | Graph polling, brief synthesis |
| `email_history` | AI only | Graph polling |
| `relationship_context` | AI only | Brief synthesis |
| `last_interaction_date` | AI only | Graph polling |
| `intelligence_notes` | AI only | Brief synthesis |

### Dropped Local Files

After PostgreSQL cutover, these local files are no longer read by the app and can be archived:

- `crm/prospects.md`
- `crm/organizations.md`
- `crm/offerings.md`
- `crm/contacts_index.md`
- `crm/interactions.md`
- `crm/email_log.json`
- `crm/briefs.json`
- `crm/prospect_notes.json`
- `crm/prospect_meetings.json`
- `crm/unmatched_review.json`

## 5. UI / Interface

### Navigation Changes

- **Root route (`/`)**: Redirects to `/crm` (pipeline view). No dashboard home page.
- **Top nav**: "Pipeline", "Organizations", "People", "Unmatched Queue". No "Tasks" or "Meetings" links.
- **User menu** (top right): Logged-in user's display name from Entra ID, "Sign Out" link.

### Pipeline View (`/crm`)

Existing pipeline table. One change: add an "Assigned To" filter dropdown at the top so users can filter prospects to their own assignments or see all.

### States

- **Unauthenticated**: Redirect to Entra ID login page
- **Auth callback error**: Error page with "Authentication failed — contact your administrator" and retry link
- **First login (new user)**: If user's `entra_id` not in `users` table, show "Access denied — your account has not been provisioned" page. (Users must be seeded in the DB before they can access the CRM.)
- **Graph consent pending**: Banner on pipeline page: "Email scanning is not yet enabled for your account. Contact Oscar to set up."
- **Empty pipeline**: "No prospects found" with link to create new prospect

### Removed from CRM UI

- Dashboard home page (tasks, calendar, meetings)
- Task board and all task routes (`/tasks/*`)
- Meeting summaries list and detail pages (`/meetings/*`)
- Calendar refresh button
- Briefing display

## 6. Integration Points

- **Reads from**: PostgreSQL (`arec_crm` database on `arec-crm-db.postgres.database.azure.com`)
- **Writes to**: PostgreSQL (prospect edits, interaction logging, contact updates, brief caching)
- **Authenticates via**: Entra ID SSO (MSAL Confidential Client flow)
- **Reads from**: Microsoft Graph API (email polling per user)
- **Calls**: Claude API (relationship brief synthesis via `app/briefing/brief_synthesizer.py` and `app/sources/relationship_brief.py`)
- **Reads from**: Shared mailbox via `app/drain_inbox.py` (crm@avilacapllc.com — keep for manual drain)
- **Deployed to**: Azure App Service (`arec-crm-app`)
- **Secrets from**: Azure Key Vault (`kv-arec-crm`)
- **Does NOT read/write**: TASKS.md, `memory/`, `meeting-summaries/`, `briefing_latest.md`, `dashboard_calendar.json`

## 7. Constraints

- **PostgreSQL only**: Remove all `crm_reader.py` imports. The import swap pattern (`if USE_DB: from crm_db import ... else: from crm_reader import ...`) is eliminated. All blueprints import directly from `crm_db`.
- **No local markdown fallback**: The app assumes PostgreSQL is available. Local dev uses a local Postgres instance or connects to Azure dev DB.
- **User provisioning is manual**: New users must be (1) added to Entra ID tenant, (2) seeded in the `users` table via a migration script. No self-service signup.
- **Graph API polling architecture**: Phase 1 uses an Azure Function with timer trigger (hourly). It iterates over users where `graph_consent_granted = True`, acquires a token for each (using client credentials flow with `Mail.Read` application permission), and calls the existing `crm_graph_sync.run_auto_capture()` logic with a `user_id` parameter.
- **No breaking changes to CRM routes**: All existing `/crm/*` URL patterns, API endpoints, and query parameters remain stable. Frontend JavaScript references these paths.
- **Gunicorn deployment**: Continue using 4 workers on port 8000 via `startup.sh`. No container or Kubernetes migration.
- **Keep `memory/people/*.md` in repo for now**: These files are the source-of-truth for the people knowledge base until all contacts are fully migrated to PostgreSQL with AI enrichment. Once verified, archive them.

## 8. Acceptance Criteria

- [ ] Visiting `/` redirects to `/crm` (no dashboard home page)
- [ ] All `/crm/*` routes return 401/redirect for unauthenticated users
- [ ] All `/tasks/*` routes return 404 (removed)
- [ ] All `/meetings/*` routes return 404 (removed)
- [ ] `/api/calendar/refresh` route is removed
- [ ] `app/main.py` and `app/briefing/` directory are deleted
- [ ] Pipeline view shows "Assigned To" filter dropdown
- [ ] User menu shows logged-in user's display name and "Sign Out" link
- [ ] All CRM data reads/writes go through `crm_db.py` — no `crm_reader.py` imports remain
- [ ] `crm_reader.py` is deleted from the codebase
- [ ] New user (Tony's EA) can authenticate via Entra ID and see the pipeline
- [ ] Unapprovisioned users (valid Entra ID but not in `users` table) see "Access denied" page
- [ ] Graph API email polling function exists (Azure Function or background thread)
- [ ] Email polling creates interactions with correct `created_by` attribution
- [ ] Contact detail page shows AI-maintained fields as read-only, manual fields as editable
- [ ] `python3 -m pytest app/tests/` passes (tests updated for PostgreSQL-only backend)
- [ ] GitHub Actions deploys successfully to `arec-crm-app` App Service
- [ ] Feedback loop prompt has been run

## 9. Files Likely Touched

### Deleted from arec-crm

| File | Reason |
|------|--------|
| `app/main.py` | Morning briefing removed entirely |
| `app/briefing/generator.py` | Morning briefing Claude API call — removed |
| `app/briefing/prompt_builder.py` | Morning briefing prompt construction — removed |
| NOTE: `app/briefing/brief_synthesizer.py` STAYS | Used by `crm_blueprint.py` for relationship brief synthesis (not a morning briefing file) |
| `app/delivery/tasks_blueprint.py` | Task management moved to Overwatch |
| `app/sources/crm_reader.py` | Markdown CRM parser — replaced by `crm_db.py` only |
| `app/sources/memory_reader.py` | Memory/task loader — moved to Overwatch |
| `app/tests/test_task_parsing.py` | Task tests moved to Overwatch |
| `app/templates/dashboard.html` | Dashboard home page removed |
| `app/templates/meeting_detail.html` | Meeting detail page removed |
| `app/templates/tasks/tasks.html` | Task board page removed |
| `app/static/task-edit-modal.js` | Task edit modal JavaScript removed |
| `app/static/task-edit-modal.css` | Task edit modal styles removed |
| `app/static/tasks/tasks.js` | Task board JavaScript removed |
| `app/static/tasks/tasks.css` | Task board styles removed |

### Modified

| File | Reason |
|------|--------|
| `app/delivery/dashboard.py` | Remove task loading, meeting routes, calendar refresh. Root route (`/`) redirects to `/crm`. Remove `tasks_bp` registration. Add `@login_required` to remaining routes. |
| `app/delivery/crm_blueprint.py` | Replace `from sources.crm_reader import ...` with `from sources.crm_db import ...`. Add `@login_required` to all routes. Add "Assigned To" filter to pipeline query. |
| `app/delivery/crm_blueprint.py` | Contact detail template: mark AI-maintained fields as read-only in the edit form |
| `app/sources/crm_graph_sync.py` | Add `user_id` parameter to `run_auto_capture()`. Record `scanned_by` in `email_scan_log`. Use per-user token acquisition. |
| `app/sources/crm_db.py` | Add `graph_consent_granted`, `graph_consent_date` columns to User model. Add `scanned_by` column to EmailScanLog model. |
| `app/models.py` | Add new columns to User and EmailScanLog models |
| `app/db.py` | No changes expected — connection pooling already correct |
| `app/auth/entra_auth.py` | Add check: if user's `entra_id` not in `users` table, show "Access denied" page instead of creating session |
| `app/templates/crm/pipeline.html` | Add "Assigned To" filter dropdown, add user menu to top nav |
| `app/templates/base.html` (or equivalent) | Add user menu (display name + sign out), remove Tasks/Meetings nav links |
| `.github/workflows/azure-deploy.yml` | Remove briefing-related files from deploy zip |
| `startup.sh` | No changes expected |
| `CLAUDE.md` | Update: remove references to briefings, TASKS.md, meeting-summaries, memory/. Document PostgreSQL-only mode. Document multi-user conventions. |

### New Files

| File | Reason |
|------|--------|
| `app/graph_poller.py` (or Azure Function) | Hourly email polling: iterate users, acquire tokens, call `run_auto_capture()` per user |
| `scripts/seed_user.py` | CLI script to add a new user to the `users` table (name, email, entra_id) |
| `scripts/migrate_add_graph_columns.py` | Alembic or raw SQL migration for new columns |
| `app/templates/access_denied.html` | "Your account has not been provisioned" page |
