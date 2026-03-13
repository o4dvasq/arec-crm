# Decisions Log

> **Append-only. Never overwrite or delete entries.**
> Add new decisions at the bottom. Format: date, decision, rationale.

---

## Format

```
## YYYY-MM-DD — [Short Decision Title]
**Decision:** What was decided.
**Rationale:** Why this choice was made over alternatives.
**Impact:** Files / systems affected.
```

---

## Log

## 2026-03-07 — Adopted docs/ Project Structure
**Decision:** Reorganized all projects to follow the `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `docs/PROJECT_STATE.md`, `docs/specs/SPEC_*.md` convention.
**Rationale:** Standardizes the design → spec → code → resume workflow across all Claude Code sessions. CLAUDE.md stays lean (working memory); docs/ carries structured reference material loaded on demand.
**Impact:** `specs/` folder replaced by `docs/specs/`. Active specs renamed to `SPEC_` prefix. Archive preserved at `docs/specs/archive/`.

---

<!-- Add new entries below this line -->

## 2026-03-11 — Global Search Bar: App-Level Context Processor

**Decision:** Moved `search_index_json` injection from `crm_bp.context_processor` (blueprint-level) to `app.context_processor` (app-level, in `dashboard.py`). Blueprint-level processor removed to avoid double-loading data on CRM routes.

**Rationale:** Blueprint context processors only run for routes registered on that blueprint. Dashboard (`/`) and Tasks (`/tasks`) routes are on the main `app`, not `crm_bp`, so the search index was silently empty on those pages. App-level covers all routes.

**Impact:** `app/delivery/dashboard.py` (new context processor), `app/delivery/crm_blueprint.py` (removed duplicate processor).

---

## 2026-03-11 — Brief Persistence: Prefer briefs.json Over Markdown Field

**Decision:** `loadBrief()` in `crm_prospect_detail.html` now checks `data.saved_brief.narrative` first (from `briefs.json`) and only falls back to `data.relationship_brief` (from the prospect markdown file) for legacy records.

**Rationale:** The POST brief endpoint calls `update_prospect_field()` with `narrative.replace('\n', ' ').strip()` — stripping paragraph breaks before writing to the markdown file. `narrativeToHtml()` splits on `\n\n` to create paragraphs, so the prose always rendered flat on reload. `saved_brief.narrative` in `briefs.json` preserves the original paragraph structure. The markdown field fallback is kept for records that only exist there.

**Impact:** `app/templates/crm_prospect_detail.html` (`loadBrief()` function, ~10 lines).

---

## 2026-03-11 — Active Tasks: Structured Endpoint, [org:] Tag Requirement

**Decision:** All task rendering on Prospect Detail now uses `/crm/api/tasks?org=ORG` (returns structured objects with `text`, `owner`, `priority`, `status`, `raw_line`) instead of `data.active_tasks` from the brief endpoint (raw TASKS.md strings). Task creation always uses `/crm/api/tasks` POST (calls `add_prospect_task()`, writes `[org: org_name]` tag). `/crm/api/followup` is no longer used for prospect-linked tasks.

**Rationale:** `complete_prospect_task()` searches for tasks by `[org: ...]` tag + text substring. Tasks created via `/crm/api/followup` don't get this tag and can never be completed via the API. Tasks loaded as raw strings from `find_org_tasks()` don't have a `raw_line` field and pass incorrect identifiers to the complete endpoint. Separating the structured task fetch from the brief fetch also keeps page load fast.

**Rejected:** Re-fetch brief on task add (expensive, full context rebuild). Instead, `loadTasks()` is a lightweight dedicated call.

**For the next designer:** Existing TASKS.md tasks without `[org: name]` tags (added before this system) will not appear in Active Tasks and cannot be completed via the checkbox. They remain visible on the Tasks page. New tasks added via Quick Actions always have the tag.

**Impact:** `app/templates/crm_prospect_detail.html` (`loadTasks`, `renderTasks`, `completeTask`, `submitQuickTask`).

---

## 2026-03-11 — Pipeline Task Popover: +N Badge Pattern

**Decision:** Pipeline tasks column shows the first task text plus a `+N` badge (count of remaining tasks). Clicking the badge opens a fixed-position popover listing all tasks. Dismissed on outside click.

**Rationale:** The previous tooltip-on-hover showed all tasks but was invisible on mobile and easy to miss. A clickable `+N` pattern is a standard affordance that communicates "there is more" and provides a deliberate action to see it.

**Impact:** `app/templates/crm_pipeline.html` (CSS: `.task-count-badge`, `#task-popover`, `.task-popover-*`; HTML: `#task-popover` div; JS: `showTaskPopover()`, `closeTaskPopover()`, click delegation).

## 2026-03-10 — People Detail Contact Box: org dropdown, not free text

**Decision:** The Organization field on the People Detail edit form is a `<select>` dropdown populated from `/crm/api/orgs`, not a free-text input. "Company" label removed everywhere in the app; replaced with "Organization".

**Rationale:** Contacts must be linked to actual org records — free text would allow typos, duplicates, and orphaned associations. Every organization already exists in `organizations.md`; the dropdown enforces referential integrity without a database.

**Rejected:** Free-text with typeahead. Adds complexity and still allows partial matches. Dropdown is simpler and correct.

**Impact:** `app/templates/crm_person_detail.html` — `showProfileEdit()` fetches `/crm/api/orgs` in parallel with person data, renders `<select>`. Display label changed from "Company" → "Organization".

---

## 2026-03-10 — Contact Block Write Format: `- **Field:** Value`

**Decision:** The PATCH endpoint (`/crm/people/api/<slug>/contact`) writes the contact block using `- **Field:** Value` (dash-prefixed bold label). The old implementation wrote `**Field:** Value` (no dash).

**Rationale:** Spec-defined format. Both are readable by the parser (`parse_kb_person_file` and `_build_person_profile` handle both with `(?:-|\*)?`), but the dash prefix is the canonical format for the contact block at the top of people files.

**Write logic:** Detect optional h1 at top → scan for contact block (dash-bold-field lines before first `##` or prose) → merge new values → rebuild block → blank-line separator → preserve all content below unchanged. h1 is always preserved.

**Clearing all fields:** If all four fields saved as empty, contact block is removed entirely (no empty lines left behind).

**Impact:** `app/delivery/crm_blueprint.py` — `api_person_contact_update` fully rewritten (~60 lines).

---

## 2026-03-08 — Removed Legacy #Productivity Folder Support
**Decision:** Deleted the `--folder` flag and all associated branching from `drain_inbox.py`. `get_folder_messages` import removed. `argparse` removed.
**Rationale:** The `#Productivity` Outlook folder workflow is no longer used. The shared mailbox (`crm@avilacapllc.com`) is the only inbox source. The legacy path was dead code adding noise and confusion.
**Impact:** `app/drain_inbox.py` — simplified to a single shared-mailbox drain with no CLI arguments.

---

## 2026-03-08 — Inbox Shared Mailbox Address
**Decision:** Corrected the shared mailbox address to `crm@avilacapllc.com` (was incorrectly hardcoded as `ai@avilacapital.com` — wrong domain and wrong username).
**Rationale:** The default in `drain_inbox.py` was a legacy placeholder from the original spec. Actual shared mailbox is `crm@avilacapllc.com` on the `avilacapllc.com` M365 tenant.
**Impact:** `app/drain_inbox.py:225` (default fallback); `.env` override via `AI_INBOX_EMAIL` remains the authoritative config. Any environment without `.env` set was silently polling the wrong mailbox.

---

## 2026-03-08 — Markdown as Database (observed, not decided this session)
**Decision:** All CRM data (prospects, orgs, contacts, interactions, meetings) is stored as markdown files. JSON is used only for metadata caches (briefs, email log, notes, unmatched items).
**Rationale:** Human-readable, git-friendly, directly editable by Claude without a database layer. Tradeoff: no query engine, relational joins done in Python at read time.
**Impact:** `crm/*.md`, `crm/*.json`; all callers parse through `crm_reader.py`.

---

## 2026-03-08 — Centralized CRM Reader (observed, not decided this session)
**Decision:** `app/sources/crm_reader.py` is the single source of truth for all CRM data parsing. No other module parses `crm/*.md` directly.
**Rationale:** Prevents parsing logic drift across multiple callers. Any schema change in markdown files requires only one update. Enforced by convention, not a framework constraint.
**Impact:** `crm_reader.py` (900+ lines); all consumers (`briefing/`, `delivery/`, `scripts/`) import from it.

---

## 2026-03-08 — Skills as Instructional Guides (observed, not decided this session)
**Decision:** `skills/meeting-debrief.md` and `skills/email-scan.md` are step-by-step instruction files for Claude to follow using MCP tools — not executable Python scripts.
**Rationale:** The operations they perform (querying Notion, scanning Outlook, writing meeting summaries) are best orchestrated interactively with Claude Code using available MCP integrations. Python scripts would require re-implementing the same MCP access patterns.
**Impact:** `skills/` directory; referenced from `memory/CLAUDE.md` post-update extension triggers.

---

## 2026-03-08 — Two-Tier Email Matching (observed, not decided this session)
**Decision:** Email/calendar participants are matched to CRM orgs in two tiers: (1) domain fuzzy match (~95% confidence), then (2) person email lookup in `memory/people/` files (~90% confidence). Unmatched participants go to `crm/unmatched_review.json`.
**Rationale:** Domain matching handles the common case instantly. Person lookup catches contacts at non-obvious domains (personal email, shared services). Manual review queue prevents silent data loss.
**Impact:** `app/sources/crm_graph_sync.py`, `crm/unmatched_review.json`.

---

## 2026-03-08 — Brief Synthesis JSON Contract (observed, not decided this session)
**Decision:** All Claude calls for brief synthesis expect a JSON response with exactly two fields: `{narrative, at_a_glance}`. A JSON suffix is appended to every brief prompt. `brief_synthesizer.py` handles parse fallbacks (markdown-fenced JSON, plain fenced JSON, raw text).
**Rationale:** Structured output needed for dashboard display (narrative in prose section, at_a_glance as bullet list). Fallback prevents silent failures when Claude returns prose instead of JSON.
**Impact:** `app/briefing/brief_synthesizer.py`, `app/delivery/crm_blueprint.py`, `crm/briefs.json`.

---

## 2026-03-08 — memory/CLAUDE.md Architecture Rule (observed, not decided this session)
**Decision:** `memory/CLAUDE.md` is capped at ~80 lines and contains only identity, inbox config, preferences, and post-update extension triggers. All people tables, company tables, terms, LP tables, and deal tables go to subdirectories (`memory/context/`, `memory/people/`, `memory/glossary.md`).
**Rationale:** CLAUDE.md is loaded into every conversation context. Keeping it lean prevents context bloat and ensures Claude has room to reason. Detailed reference material is loaded on demand.
**Impact:** `memory/CLAUDE.md`; all downstream memory files.

---

## 2026-03-09 — Add Task: Pipeline Rename + Prospect Detail Quick Actions Bar

**Decision:** Renamed "Create Follow-up" → "Add Task" in the pipeline context menu (label only). Added a combined Quick Actions bar to the prospect detail page with two toggle pills (Add Task, Add Quick Note). Both changes implemented in the same session, bundled with SPEC_quick-note.md (which was not yet implemented).
**Rationale:** Spec required bundling: the Quick Actions bar houses both forms, so the Quick Note form had to be built from scratch alongside Add Task rather than wrapping a pre-existing implementation.

**Key implementation choices:**

1. **Existing endpoint, actual field names** — The spec payload showed `{ org, offering, text, priority }` but the real `/crm/api/followup` endpoint uses `{ org, description, priority }` (no `offering` field). Matched the actual endpoint, not the spec's suggested payload.

2. **`<input type="text">` for Quick Note (not `<textarea>`)** — The Quick Actions bar is a compact fast-path. The Notes Log card at the bottom retains its `<textarea>` for longer, more deliberate entries. Two different affordances for two different use cases.

3. **Server-rendered author `<select>`** — Team member dropdown uses Jinja2 `{% for member in config.team %}` rather than a JS-populated list, consistent with how other templates in this app handle team data.

4. **DOM prepend on task success** — Rather than re-fetching the full brief on task add (expensive), the new task is constructed locally and prepended to `#tasks-list`. The raw text format matches what `renderTasks()` produces.

5. **CSS keyframe flash for tasks card** — "Flash green on Active Tasks section" implemented as a CSS `@keyframes taskFlash` animation added/removed via class toggle. No JS timers beyond `setTimeout` for cleanup.

6. **Single string change covers mobile** — Desktop right-click and mobile long-press both call `buildCtxMenu()`. One label change at line 920 covers both; no separate mobile-specific code path needed.

**For the next designer:** The Quick Actions bar sits between the At a Glance card and the Relationship Brief. If a "Quick Call Log" or similar third action is added later, the toggle pattern (`.quick-actions-toggle` pills + swapping form divs) extends naturally to a third pill.

**Impact:** `app/templates/crm_pipeline.html` (1 line), `app/templates/crm_prospect_detail.html` (CSS block, HTML card, JS functions).

---

## 2026-03-09 — Prospect Detail Redesign: Row Clicks, Org Edit, Contacts Table, Type Rationalization, Task Assignee

**Decision:** Implemented full prospect detail page redesign from SPEC_prospect-detail-redesign.md: entire row navigation, back button with filter preservation, org sub-section with Type dropdown, "+ Add Contact" with typeahead search, org edit page, org type standardization (16 categories), and task assignee selector.

**Key implementation choices:**

1. **Two-theme approach for contacts partial** — Prospect detail uses dark theme, org edit uses light theme. Rather than forcing a single shared component style, each page includes its own styled implementation of "+ Add Contact". The `_contacts_table.html` partial is light-themed for the org edit page.

2. **Typeahead search excludes AREC team** — `/api/people/search` filters out `config.team` members by name to prevent linking internal team members as external contacts. Backend exclusion at line 114-124 in `crm_blueprint.py`.

3. **Contact linking vs. creating** — API accepts `is_new: true/false` flag. When `false`, updates existing person's org field. When `true`, calls `create_person_file()` to generate new `memory/people/{slug}.md` with proper frontmatter.

4. **Org type rationalization: 16 categories** — Expanded from 4 (INSTITUTIONAL, HNWI / FO, BUILDER, INTRODUCER) to 16 comprehensive types covering institutional investors, asset managers, family offices, banks, etc. Standardized spacing and removed hybrid types (e.g., "Public Pension / Endowment" → "Endowment").

5. **Task assignee routing to sections** — `/api/followup` endpoint now maps assignee full name → short name via `team_map`, formats task as `**@{short}**`, and writes to `Fundraising - {short}` section instead of hardcoded "Fundraising - Me".

6. **Contacts always visible on prospect detail** — Changed `renderContacts()` to always show the contacts card (even if empty) so the "+ Add Contact" button is accessible. Empty state shows "No contacts yet."

7. **Search results dropdown includes "Create New Contact" action** — Typeahead results list ends with a "+ Create New Contact" button to switch to create mode, improving discoverability of the two-mode flow.

**For the next designer:**
- The `_contacts_table.html` partial expects `org_name` and `contacts` variables in Jinja context. It includes all JS inline.
- The org edit page route is `/crm/org/<name>/edit`; old `/crm/org/<name>` redirects to it for backward compat.
- Filter preservation uses `back_filters` URL param; frontend builds it from `getCurrentFilters()` on pipeline page.

**Impact:**
- `app/templates/_contacts_table.html` (new shared partial)
- `app/templates/crm_prospect_detail.html` (org sub-section, contacts with add, task assignee dropdown)
- `app/templates/crm_org_edit.html` (already existed, uses shared contacts partial)
- `app/delivery/crm_blueprint.py` (`/api/people/search`, `/api/org/<org>/contacts`, `/api/followup` assignee routing)
- `crm/config.md` (16 org types)
- `crm/organizations.md` (standardized 3 org type inconsistencies)

## 2026-03-10 — MS Graph Auth: acquire_token_silent_with_error + Cache Eviction

**Decision:** Replaced `acquire_token_silent` with `acquire_token_silent_with_error` in `graph_auth.py`. On `invalid_grant` or `interaction_required` errors, the stale token cache file is automatically deleted before raising.

**Rationale:** `acquire_token_silent` returns `None` when the refresh token is revoked (e.g., after a password reset — AADSTS50173). The caller then raises a generic "Authentication required" message with no explanation. `acquire_token_silent_with_error` returns the actual Azure AD error response, which is surfaced in the exception message. Auto-deleting the cache on revocation means the next `python app/main.py` triggers a clean device flow rather than re-hitting the bad token.

**Rejected approach:** Prompting for device flow from the web context (Deep Scan endpoint). The web server can't present a device code to the user in a browser-friendly way, so `allow_device_flow=False` stays correct. The fix is purely diagnostic + cleanup.

**Impact:** `app/auth/graph_auth.py`. Re-auth required after password changes or MFA policy updates — run `python app/main.py`.

---

## 2026-03-10 — People Detail: Always-Visible Contact Info Card

**Decision:** The Contact Info card on the People detail page is always shown (was conditionally hidden when no fields had data). All four fields — Company, Title, Email, Phone — are rendered with "—" placeholders when empty. Company field added to the edit form and PATCH payload.

**Rationale:** Users couldn't easily tell if a person had missing contact info or no card at all. An always-visible card with empty states makes the data gaps obvious and the Edit button always accessible.

**Data consistency fix:** `collect_person_data` extracted org_name only from `**Organization:**` fields. The PATCH endpoint writes back as `**Company:**`. Extended the regex in `relationship_brief.py` to also match `**Company:**` and `**Org:**` so edits survive a page reload.

**Impact:** `app/templates/crm_person_detail.html`, `app/sources/relationship_brief.py`.

---

## 2026-03-10 — Org Edit/Detail: Prospect-Style Summary Card

**Decision:** Both `crm_org_edit.html` and `crm_org_detail.html` now use the same compact summary card format as the Prospect detail page: org name as a standalone page title above the card, a 3-column grid (Type, Domain, spacer), and a full-width Notes row below the grid. All fields are click-to-edit (no always-on form controls).

**Rationale:** The org edit page had the org name inside the card as an `<h1>`, with Type always showing as a `<select>` and Notes as a `<textarea>`. This wasted vertical space and looked inconsistent with the Prospect detail UX. The prospect detail format (static display → click to edit inline → auto-save) is better for scanning.

**Notes row behavior:** Hidden when empty in both pages; shown when populated. Keeps the card compact for orgs with no notes.

**Auto-save pattern (edit page):** Type saves on `change` event; Domain and Notes save on `blur`. Same pattern as other inline-edit fields. Green border flash on successful save.

**Impact:** `app/templates/crm_org_edit.html` (full rewrite), `app/templates/crm_org_detail.html` (summary card CSS + JS + HTML).

---

## 2026-03-11 — Phase I1: PostgreSQL Migration with Drop-In Replacement Architecture

**Decision:** Implemented full database migration from markdown to PostgreSQL using a drop-in replacement pattern. Created `crm_db.py` with identical function signatures to `crm_reader.py`. All existing callers (`crm_blueprint.py`, `crm_graph_sync.py`, `prompt_builder.py`, `dashboard.py`) switch backend via import swap.

**Key implementation choices:**

1. **Drop-in replacement, not wrapper** — `crm_db.py` is a complete reimplementation of all 45+ `crm_reader.py` functions using SQLAlchemy, not a thin wrapper. This avoids the impedance mismatch of trying to adapt markdown-oriented APIs to SQL.

2. **Currency as BIGINT cents** — All dollar amounts stored as cents (e.g., $50M → 5000000000). Display layer uses `_format_currency()` and `_parse_currency()` helpers. Avoids floating-point precision issues in financial calculations.

3. **Org type as VARCHAR, not enum** — 16 org types stored as strings, not a Postgres ENUM. ENUM changes require migrations; VARCHAR allows flexibility. Type validation happens at application layer (dropdown in UI).

4. **Pipeline stage remapping during migration** — `2. Qualified` → `2. Cold`, `3. Presentation` → `3. Outreach` per spec. Hardcoded in `migrate_to_postgres.py` via `STAGE_REMAP` dict.

5. **Multi-assignee flattening** — Prospect `Assigned To` field stores semicolon-separated names in markdown. Migration takes first name only; writes to `assigned_to` foreign key. UI enforces single assignee.

6. **Contact linking on Primary Contact set** — `update_prospect_field()` calls `ensure_contact_linked()` when `primary_contact` changes. Idempotently creates contact record in DB if missing.

7. **Meeting history stays local** — `meeting_history.md` NOT migrated. `load_meeting_history()` / `add_meeting_entry()` continue reading/writing markdown file. Phase I1 scope: core CRM only.

8. **Tasks stay local** — TASKS.md NOT migrated. All task functions (`load_tasks_by_org`, `get_tasks_for_prospect`, `add_prospect_task`, `complete_prospect_task`) continue using markdown file. No SQL `prospect_tasks` table in active use.

9. **People files stay local** — `memory/people/*.md` NOT migrated. Contacts table stores name/title/email/phone only. Full person intel files (email history, meeting notes, context) stay in markdown.

10. **Three-script migration workflow** — `create_schema.py` (drop/create tables, seed stages + users), `migrate_to_postgres.py` (parse markdown → insert), `verify_migration.py` (count validation + spot checks). Idempotent: safe to re-run.

11. **Session management via Flask integration** — `db.py` provides `init_app(app)` for Flask teardown handler, `session_scope()` context manager for transactional blocks, and `get_session()` for manual session control.

12. **Placeholder Entra IDs** — 8 users seeded with `entra_id` like `placeholder-oscar`. SSO callback replaces placeholder with real `oid` claim from Azure on first login.

**Rejected approaches:**

- **ORM for markdown** — Tried building SQLAlchemy models for markdown files. Markdown doesn't map cleanly to relational structures (nested sections, freeform notes). Simpler to parse markdown directly.

- **Hybrid read path** — Considered querying Postgres when available, falling back to markdown. Rejected: two read paths double the testing surface. Single backend swap via import is cleaner.

- **Lazy migration** — Considered migrating records on-demand as they're accessed. Rejected: leaves stale data in markdown indefinitely. One-time batch migration is clearer.

**For the next designer:**

- **Tests need rewriting** — Existing 52 tests (`test_brief_synthesizer.py`, `test_email_matching.py`, `test_task_parsing.py`) use markdown fixtures. New `test_crm_db.py` needs ephemeral Postgres or SQLite in-memory DB.

- **Local CRM stays on markdown** — No automatic cutover. Oscar runs migration locally to populate Azure Postgres, then manually switches `dashboard.py` imports when confident.

- **`crm_reader.py` preserved indefinitely** — Keep for local dev mode and as reference implementation. Do not delete.

**Impact:**
- `app/models.py` (new, 14 tables)
- `app/db.py` (new, session management)
- `app/sources/crm_db.py` (new, ~2,000 lines, 45+ functions)
- `scripts/create_schema.py`, `scripts/migrate_to_postgres.py`, `scripts/verify_migration.py` (new)
- `app/delivery/crm_blueprint.py` (import updated)
- `app/sources/crm_graph_sync.py` (import updated)
- `app/briefing/prompt_builder.py` (import updated)
- `app/delivery/dashboard.py` (DB init added)
- `app/requirements.txt` (added `sqlalchemy`, `psycopg2-binary`, `gunicorn`)

---

## 2026-03-11 — Prospect Detail Tasks: Edit Modal Pattern

**Decision:** Replaced per-task checkboxes + PATCH-to-complete with clickable task rows that open the shared `task-edit-modal.js`. Tasks card is always visible (not hidden when empty). "+ Add Task" button in card header opens the modal in create mode with org pre-filled. `taskModalOnSave/Delete` callbacks call `loadTasks()` to refresh.

**New endpoint:** `/tasks/api/tasks/for-org?org=X` in `tasks_blueprint.py` — scans TASKS.md with section+index tracking (required by the modal's PUT/DELETE endpoints), returns full parsed task data. Matches by `[org: ...]` tag OR org name anywhere in task text (covers old-format tasks with `(OrgName)` parentheticals). Only open tasks returned.

**Why section+index instead of raw_line matching:** The shared modal saves via `PUT /tasks/api/task/{section}/{index}` and deletes via `DELETE /tasks/api/task/{section}/{index}`. These endpoints were already well-tested from the Tasks page. Building a new raw_line-based endpoint would have duplicated that infrastructure.

**Rejected:** Fixing the checkbox approach — the root problem was that old-format tasks (no `[org:]` tag) couldn't be matched by `complete_prospect_task()`. Rather than extend the complete endpoint to also handle legacy formats and potentially misfire on ambiguous org name matches, the modal gives full edit capabilities (change text, priority, status, assignee, mark complete) and is already used on Pipeline and Dashboard pages.

**Org type dropdown fix:** Create Org modal in `crm_orgs.html` had 4 hardcoded options. Fixed by (1) adding Jinja2 loop over `config.org_types` in template, and (2) passing `config` in the `orgs_list()` route (was previously omitted).

**Backend revert:** Previous session had partially wired `crm_db` imports and `init_db_app` into `dashboard.py`. Reverted both to `crm_reader.py` since `DATABASE_URL` is not set locally. Azure migration infrastructure remains in untracked files.

**Impact:**
- `app/delivery/tasks_blueprint.py` (new `/tasks/api/tasks/for-org` endpoint)
- `app/templates/crm_prospect_detail.html` (task card HTML, CSS, loadTasks, renderTasks, modal globals, script tag)
- `app/templates/crm_orgs.html` (org type dropdown — Jinja loop)
- `app/delivery/crm_blueprint.py` (orgs_list route now passes config; inject_search_index adds typeLabel)

---

## 2026-03-11 — Entra ID SSO with Placeholder User Seeding

**Decision:** Microsoft Entra ID (Azure AD) SSO implemented via MSAL confidential client flow. All 8 team members seeded in `users` table with placeholder Entra IDs (`placeholder-{name}`). On first login, SSO callback replaces placeholder with real `oid` claim and updates `last_login`.

**Rationale:** Cannot get real Entra IDs until Oscar completes app registration and all users grant consent. Seeding with placeholders allows migration to run and foreign keys to resolve. First login auto-upgrades the record.

**SSO flow:**
1. Unauthenticated user → redirect to `/.auth/login/aad`
2. MSAL generates authorization URL → redirect to Microsoft login
3. User authenticates → Microsoft redirects to `/.auth/login/aad/callback?code=...`
4. Exchange code for token via MSAL `acquire_token_by_authorization_code`
5. Extract `oid` (Entra ID), `preferred_username` (email), `name` (display name) from `id_token_claims`
6. Store in Flask session as `user` dict
7. Update `users.last_login`; replace `entra_id` if placeholder
8. Redirect to originally requested page

**Login required:** `@login_required` decorator checks `session['user']`. Populates `g.user` on every request via `@app.before_request`.

**Logout:** `/.auth/logout` → clear session → redirect to Microsoft logout URL with `post_logout_redirect_uri`.

**Environment variables:**
- `AZURE_CLIENT_ID` — App registration client ID
- `AZURE_CLIENT_SECRET` — Client secret (from Key Vault in production)
- `AZURE_TENANT_ID` — Avila Capital LLC tenant (064d6342-5dc5-424e-802f-53ff17bc02be)
- `AZURE_REDIRECT_URI` — Callback URL (e.g., `https://arec-crm.azurewebsites.net/.auth/login/aad/callback`)

**For the next designer:** SSO is optional for local dev. If `AZURE_CLIENT_ID` not set, SSO routes are not initialized. Local dev can run without authentication.

**Impact:**
- `app/auth/entra_auth.py` (new, ~150 lines)
- `app/delivery/dashboard.py` (SSO init, session config)
- `app/templates/_nav.html` (user display name + logout link)
- `scripts/create_schema.py` (seed 8 users with placeholder IDs)


## 2026-03-12 — Overwatch Segregation + PostgreSQL-Only Multi-User CRM

**Decision:** Split arec-crm into two projects: (1) Overwatch — personal productivity (tasks, meetings, memory, calendar) running locally on port 3001, and (2) AREC CRM — multi-user fundraising platform with PostgreSQL backend, Entra ID SSO, and graph API polling. All personal productivity features moved to Overwatch. AREC CRM root route redirects to `/crm`.

**Key implementation choices:**

1. **Two independent projects, not monorepo** — Overwatch at `~/Dropbox/projects/overwatch/`, AREC CRM at `~/Dropbox/projects/arec-crm/`. Zero imports between them. Shared modules (graph_auth, ms_graph) copied to both.

2. **PostgreSQL-only for CRM** — Deleted `crm_reader.py`. All imports switched to `crm_db.py`. No markdown fallback. Local dev uses local Postgres or Azure dev DB.

3. **Morning briefing removed entirely** — `app/main.py`, `generator.py`, `prompt_builder.py` moved to Overwatch but not scheduled. Morning briefing workflow deprecated. Brief synthesis (`brief_synthesizer.py`) stays in CRM for relationship briefs.

4. **Root route redirect** — AREC CRM `/` redirects to `/crm` (pipeline view). No dashboard home page. Overwatch `/` shows dashboard with tasks + calendar + meetings.

5. **Multi-user email attribution** — `crm_graph_sync.py` now takes `user_id` parameter. `email_scan_log` table has `scanned_by` FK. `graph_poller.py` iterates over users with `graph_consent_granted = True`.

6. **User provisioning is manual** — New users seeded via `scripts/seed_user.py`. No self-service signup. Users must exist in Entra ID tenant + `users` table.

7. **Merge stubs for compatibility** — `merge_organizations()` and `get_merge_preview()` added to `crm_db.py` as stubs (not implemented). `merge_organizations()` raises NotImplementedError.

8. **Overwatch has no CRM config** — `tasks_blueprint.py` in Overwatch uses stub `load_crm_config()` that returns empty dicts. No dependency on CRM data.

**Rationale:** 
- Oscar's personal productivity (tasks, memory, meeting summaries) should not be in a multi-user fundraising platform.
- Overwatch stays local (no Azure deployment), AREC CRM becomes team platform.
- PostgreSQL-only simplifies deployment and testing (no dual backend complexity).
- Morning briefing feature was deprecated; on-demand brief synthesis is the active workflow.

**Rejected approaches:**
- **Shared library for common code** — Creates coupling. Copying graph_auth and ms_graph is simpler.
- **Keep markdown fallback in CRM** — Dual backend doubles testing surface. PostgreSQL-only is cleaner.
- **Merge personal + team features** — Personal tasks/memory don't belong in team CRM. Clear separation is better.

**For the next designer:**
- Overwatch runs on port 3001, AREC CRM on port 8000 (Azure) or 3002 (local dev).
- Graph API token cache (`~/.arec_briefing_token_cache.json`) is shared between both projects for local dev.
- TASKS.md is in Overwatch only. CRM tasks use `prospect_tasks` table.
- `memory/people/*.md` stays in AREC CRM (canonical contact intel). Overwatch has separate `people/` directory (empty initially).

**Impact:**
- Created `~/Dropbox/projects/overwatch/` (22 files moved + 3 new)
- Deleted from arec-crm: 18+ files (tasks, meetings, memory, briefing orchestrator)
- Modified in arec-crm: 6 files (dashboard, crm_blueprint, crm_graph_sync, crm_db, relationship_brief, CLAUDE.md)
- New in arec-crm: 5 files (migration scripts, graph_poller, access_denied template)

---

## 2026-03-12 — Overwatch Dashboard Testing and Static Asset Strategy

**Decision:** During Overwatch testing, discovered missing `_nav.html` template and undefined `config` variable. Fixed by creating minimal nav template and adding config stub to dashboard route. Static assets (CSS/JS) copied from arec-crm rather than creating Overwatch-specific styles.

**Key fixes applied:**

1. **Created `_nav.html` for Overwatch** — Minimal navigation bar with project branding and user display. No CRM tabs, no global search. Single-user display ("Oscar Vasquez") hardcoded.

2. **Config stub in dashboard route** — Dashboard template expects `config.team` and `config.team_map` for task modal. Added stub return: `config = {'team': [], 'team_map': []}`. Single-user mode doesn't need team assignment.

3. **Removed CRM API dependency** — Dashboard template had `fetch('/crm/api/orgs')` to populate task modal org dropdown. Replaced with local stub: `window.TASK_MODAL_PROSPECT_ORGS = []`. Overwatch has no CRM orgs.

4. **Static asset reuse** — Copied `crm.css`, `crm.js`, `task-edit-modal.css`, `task-edit-modal.js` from arec-crm to Overwatch. Both projects share dark theme and task modal UI.

**Testing results:**
- ✓ Dashboard imports successfully
- ✓ Server starts on port 3001
- ✓ Root route returns HTTP 200
- ✓ Template renders (67KB response)
- ✓ Static assets served correctly

**Rationale:**
- Overwatch is a single-user local app. No need for multi-user nav, team assignment, or org dropdowns.
- Reusing static assets avoids duplicating 10KB+ of CSS/JS. Both projects use same dark theme.
- Nav template kept minimal — may evolve later if Overwatch adds more sections.

**Rejected approaches:**
- **Creating Overwatch-specific styles** — Unnecessary duplication. Dark theme works for both projects.
- **Removing task modal** — Tasks are core to Overwatch. Modal provides full CRUD UI.
- **Keeping CRM API calls** — Would fail at runtime. Local stub prevents fetch errors.

**For the next designer:**
- If Overwatch UI diverges significantly, consider splitting static assets.
- Task modal org links (`/crm/org/...`) are harmless in Overwatch but non-functional. Could be removed if task format changes.
- `_nav.html` is minimal. If more pages added (reports, analytics), extend nav accordingly.

**Impact:**
- `overwatch/app/templates/_nav.html` (new)
- `overwatch/app/delivery/dashboard.py` (config stub added)
- `overwatch/app/templates/dashboard.html` (CRM API call removed)
- `overwatch/app/static/` (4 files copied)

---

## 2026-03-12 — Local PostgreSQL Setup and Schema Script Fixes

**Decision:** Set up local PostgreSQL 14 for development instead of immediately using Azure database. Fixed schema creation scripts to load from `.env` instead of `.env.azure`.

**Key implementation choices:**

1. **PostgreSQL 14 via Homebrew** — Used `brew install postgresql@14` rather than Docker or Postgres.app. Homebrew service management (`brew services start`) ensures automatic startup.

2. **Database name: `arec_crm`** — Simple, matches project name. No special characters or versioning suffix. Created with default UTF-8 encoding.

3. **Local connection string** — `postgresql://localhost/arec_crm` (no username/password). Uses peer authentication (macOS user = Postgres user). Simpler for local dev.

4. **Fixed `.env` loading in scripts** — `create_schema.py` was hardcoded to load `.env.azure`. Changed to `.env` for local dev. `.env.azure` remains as deployment template.

5. **Added SQLAlchemy text() wrappers** — `migrate_add_graph_columns.py` failed with raw SQL strings. SQLAlchemy 2.0 requires explicit `text()` wrapper for all raw SQL. Applied to all `session.execute()` calls.

6. **Flask config added to .env** — Added `FLASK_SECRET_KEY`, `DASHBOARD_PORT=8000`, `FLASK_DEBUG=false` to match production conventions. Port 8000 (not 3001) to avoid conflict with Overwatch.

7. **Schema creation seeds users immediately** — `create_schema.py` seeds 8 team members with placeholder Entra IDs on first run. Avoids chicken-egg problem with foreign keys.

**Testing results:**
- ✓ PostgreSQL service running
- ✓ Database created
- ✓ Schema creation successful (14 tables)
- ✓ Users seeded (8 team members)
- ✓ Graph columns migration successful
- ✓ Dashboard functional (HTTP 200 on /crm)

**Rationale:**
- Local PostgreSQL avoids Azure costs during development and testing.
- Peer authentication simplifies local setup (no password management).
- Immediate user seeding prevents foreign key constraint failures when creating test data.
- Port 8000 standard for production-like local dev (matches Azure).

**Rejected approaches:**
- **Docker PostgreSQL** — Extra complexity, slower startup. Homebrew service is simpler.
- **SQLite for local dev** — Would require maintaining two SQL dialects. PostgreSQL-only is cleaner.
- **Azure database for local dev** — Slower, costs money, requires VPN/firewall rules.

**For the next designer:**
- All scripts now assume `.env` exists with `DATABASE_URL`. If switching to Azure, update `.env` (don't change scripts).
- `brew services start postgresql@14` must run on every machine. Add to setup docs.
- User placeholder IDs (`placeholder-oscar`, etc.) get replaced on first SSO login. See `entra_auth.py` callback.

**Impact:**
- `app/.env` (added DATABASE_URL + Flask config)
- `scripts/create_schema.py` (load `.env` instead of `.env.azure`)
- `scripts/migrate_add_graph_columns.py` (added init_db, dotenv loading, text() wrappers)
- PostgreSQL 14 installed and running as system service

---

## 2026-03-12 — Azure Deployment Fix: Database Initialization and Environment Variables

**Decision:** Fixed four critical initialization issues preventing Azure deployment: (1) added `db.init_app(app)` call in `dashboard.py`, (2) updated `entra_auth.py` to support both `ENTRA_*` and `AZURE_*` environment variable names, (3) added Flask secret key configuration, (4) added `init_auth_routes(app)` call.

**Rationale:**

1. **Database initialization** — `dashboard.py` created the Flask app and registered blueprints, but never called `db.init_app(app)` or `db.init_db()`. Every database operation would crash with "Database not initialized" error. The `crm_blueprint.py` imports 40+ functions from `crm_db.py`, all requiring `db.SessionLocal` to be initialized.

2. **Environment variable mismatch** — Azure App Settings used both `ENTRA_CLIENT_ID` and `AZURE_CLIENT_ID` conventions (set during different deployment phases). The `entra_auth.py` code only read `AZURE_*` names. Added fallback pattern: `os.environ.get('AZURE_CLIENT_ID') or os.environ.get('ENTRA_CLIENT_ID')` to support both.

3. **Flask secret key** — MSAL authentication requires Flask sessions, which require `app.secret_key`. Without it, session operations fail silently. Added `app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(32).hex())`.

4. **Auth routes registration** — SSO endpoints (`/.auth/login/aad`, `/.auth/login/aad/callback`, `/.auth/logout`) were defined in `entra_auth.py` but never registered on the Flask app. Added `init_auth_routes(app)` call.

**Deployment flow:**
- Code changes pushed to `azure-migration` branch
- GitHub Actions workflow triggered automatically
- Tests passed (121 tests)
- Deployment package built and deployed to Azure App Service
- App verified responding with HTTP 200

**Rejected approaches:**
- **Renaming all Azure App Settings to AZURE_*** — Would require coordinating deployment config changes with code changes. Fallback pattern is safer.
- **Lazy database initialization** — Considered initializing DB on first request. Flask `init_app` pattern is standard and avoids race conditions.

**For the next designer:**
- The initialization order matters: `init_app(app)` must happen before `init_auth_routes(app)` (auth routes query the users table).
- Both must happen before `app.register_blueprint(crm_bp)` (blueprint routes use DB and auth).
- If adding new blueprints, follow the same pattern: DB init → auth init → blueprints.

**Impact:**
- `app/delivery/dashboard.py` (added 3 imports, 3 function calls, secret key config)
- `app/auth/entra_auth.py` (added fallback env var support with `or` pattern)
- Azure deployment now functional at https://arec-crm-app.azurewebsites.net

---

## 2026-03-12 — Azure Production Cutover Complete

**Decision:** AREC CRM is now a production Azure application. All development happens on `azure-migration` branch with CI/CD auto-deploy. `main` branch is frozen (stale markdown-based code). No local-only features allowed.

**What changed:**
1. App live at https://arec-crm-app.azurewebsites.net/crm with PostgreSQL backend
2. 99 tests passing in CI (GitHub Actions), auto-deploy on push to `azure-migration`
3. Data migrated: 146 orgs, 126 prospects, 137 contacts, 59 briefs in Azure Postgres
4. Entra ID SSO operational, client secret rotated
5. Overwatch segregation committed (66 files removed from arec-crm)
6. Feature work synced (graph_poller, seed_user, CRM refinements)

**Rationale:** All infrastructure provisioned, tested, and verified. Smoke tests passed. No reason to continue running locally against markdown files.

**Rules going forward:**
- `git checkout azure-migration` before any work
- `main` is NOT the production branch — do not use it
- Everything must work on Azure. No local-only code.
- `crm_reader.py` is deleted. No markdown backend imports.
- Push deploys automatically. Test locally first.

**Impact:** All project docs updated (CLAUDE.md, PROJECT_STATE.md, ARCHITECTURE.md, all SPEC_ files, AZURE_DEPLOYMENT_STATUS.md).

---

## 2026-03-12 — EasyAuth SSO & User Management: Auto-Provisioning + Role Gating

**Decision:** Implemented Entra ID SSO with auto-provisioning, admin/user roles, and DEV_USER local dev bypass. Users are created on first login with role='user' (except oscar@avilacapllc.com → 'admin'). Admin page at `/admin/users` allows role management. DEV_USER environment variable bypasses OAuth for local development.

**Key implementation choices:**

1. **Auto-provisioning on first login** — `get_or_create_user()` helper in `entra_auth.py` checks if user exists in database. If not, creates user record with role='user' (or 'admin' for oscar@avilacapllc.com). Updates `last_login` on every request.

2. **DEV_USER bypass for local dev** — Setting `DEV_USER=oscar@avilacapllc.com` in `app/.env` bypasses OAuth flow entirely. `before_request` hook checks `DEV_USER` env var first, calls `get_or_create_user()` directly, populates `g.user`. Warning logged at startup: "⚠️ WARNING: DEV_USER is set — authentication is bypassed."

3. **Role field as VARCHAR(20)** — User model has `role` column with values 'admin' or 'user'. No enum, no foreign key. Simple string comparison for `@require_admin` decorator.

4. **Admin page uses inline role dropdowns** — `/admin/users` shows table of all users. Role column is a `<select>` with `onchange` → `POST /admin/users/<id>/role`. No separate edit form. Self-demotion prevented (dropdown disabled for current user).

5. **Migration script uses SQLAlchemy text()** — `migrate_add_auth_columns.py` wraps raw SQL in `text()` for SQLAlchemy 2.0 compatibility. Idempotent: uses `ADD COLUMN IF NOT EXISTS`.

6. **@require_admin decorator, not @login_required** — CRM routes do NOT have `@login_required` because EasyAuth is enforced at Azure infrastructure layer (all requests authenticated). Only admin-specific routes (`/admin/*`) use `@require_admin`.

7. **g.user populated by before_request hook** — `load_user()` runs on every request. Priority: (1) DEV_USER, (2) session['user']. Ensures `g.user` is always available in templates and route handlers.

**Rationale:**
- Auto-provisioning eliminates manual user creation. Any `@avilacapllc.com` user can log in immediately.
- DEV_USER bypass simplifies local development (no OAuth redirect, no client secret required).
- Role-based access control enables future admin-only features (config editing, user management, analytics).
- Inline role editor on admin page is faster than separate edit form (single-field change, not full CRUD).

**Rejected approaches:**
- **Manual user provisioning via admin UI** — Requires admin to manually add users before first login. Auto-provisioning is simpler.
- **Flask-Login library** — Adds dependency for features we don't need. Custom `@require_admin` decorator is 10 lines.
- **Role as ENUM** — Would require migration on every role addition. VARCHAR is more flexible.

**For the next designer:**
- Admin page only shows users who have logged in at least once. No way to pre-add users. Use `scripts/seed_user.py` if needed.
- oscar@avilacapllc.com is hardcoded as admin email. If Oscar leaves, update `entra_auth.py` line 103.
- DEV_USER must never be set in Azure App Settings. Add startup check to crash if DEV_USER is set in production.

**Impact:**
- `app/auth/entra_auth.py` (DEV_USER support, auto-provisioning, warning log)
- `app/auth/decorators.py` (new, `@require_admin`)
- `app/delivery/admin_blueprint.py` (new, `/admin/users` routes)
- `app/delivery/dashboard.py` (register admin blueprint)
- `app/templates/admin/users.html` (new, user management UI)
- `app/templates/_nav.html` (admin badge for admins)
- `app/templates/access_denied.html` (custom error message support)
- `app/models.py` (added `role` field to User model)
- `scripts/migrate_add_auth_columns.py` (new, idempotent migration)
- `app/.env` (added `DEV_USER=oscar@avilacapllc.com`)
- `CLAUDE.md` (documented auth system)

---
## 2026-03-12 — Multi-User Platform: @login_required Enforcement + Background Email Polling

**Decision:** Enforced authentication on all CRM routes by adding `@login_required` decorator to 49 route handlers. Created `graph_poller.py` for multi-user background email polling. Added `graph_consent_granted`, `graph_consent_date` columns to User model and `scanned_by` column to EmailScanLog model.

**Key implementation choices:**

1. **Import-and-decorate pattern** — Added `from auth.entra_auth import login_required` to top of `crm_blueprint.py`, then applied `@login_required` decorator to all 49 route handlers (both page routes and API endpoints). Used Python regex script to apply systematically.

2. **Graph consent columns for opt-in** — Added `graph_consent_granted` (Boolean, default False) and `graph_consent_date` (TIMESTAMP) to User model. Users must explicitly opt in to email scanning. `graph_poller.py` only scans users where `graph_consent_granted=True`.

3. **scanned_by attribution** — Added `scanned_by` (Integer FK to users.id) to EmailScanLog model. When `graph_poller.py` calls `run_auto_capture(token, user_id=user.id)`, all email_scan_log records created during that scan get `scanned_by=user.id`.

4. **Standalone graph_poller.py** — Created as executable script (`python3 app/graph_poller.py`) that iterates over consented users, acquires tokens, calls `run_auto_capture()` per user, returns statistics. Can be scheduled via cron or deployed as Azure Function.

5. **Migration script with text() wrappers** — `migrate_add_graph_columns.py` uses SQLAlchemy `text()` wrapper for all raw SQL (SQLAlchemy 2.0 requirement). Idempotent: safe to re-run.

6. **Access denied template created** — `access_denied.html` shows when authenticated user is not in users table. Currently unused since auto-provisioning is enabled, but ready if provisioning mode changes.

7. **User menu already existed** — `_nav.html` already had user display name, admin badge, and logout link from previous session (EasyAuth SSO). No changes needed.

**Rationale:**
- Authentication enforcement is required for multi-user platform (SPEC_arec-crm-multi-user.md acceptance criteria).
- Graph consent opt-in prevents scanning mailboxes without permission.
- `scanned_by` attribution enables per-user email ownership and debugging.
- Standalone poller script allows flexible deployment (cron, Azure Function, container job).

**Rejected approaches:**
- **Blueprint-level decorator** — Considered `@crm_bp.before_request` to apply auth to all routes at once. Rejected: explicit per-route decorators are clearer and allow route-by-route exceptions if needed later.
- **Automatic graph consent** — Considered auto-granting consent on first login. Rejected: email scanning is sensitive, opt-in is safer.
- **Modifying crm_graph_sync.py signature** — `run_auto_capture()` already took optional `user_id` parameter (forward-looking design from previous session). No signature changes needed.

**For the next designer:**
- `graph_poller.py` depends on Graph API application permissions (`Mail.Read` scope). Requires admin consent in Entra ID app registration.
- If scheduling via cron, run from project root: `cd ~/Dropbox/projects/arec-crm && python3 app/graph_poller.py`
- If deploying as Azure Function, use timer trigger with `0 0 * * * *` (hourly). Set `DATABASE_URL` and `ANTHROPIC_API_KEY` in function app settings.
- Migration must run on Azure database before deploying: `python3 scripts/migrate_add_graph_columns.py` (set `DATABASE_URL` to Azure connection string first).

**Impact:**
- `app/delivery/crm_blueprint.py` — Added `@login_required` to 49 routes
- `app/models.py` — Added 3 columns (graph_consent_granted, graph_consent_date, scanned_by)
- `app/graph_poller.py` — NEW: Multi-user background email polling (150 lines)
- `scripts/migrate_add_graph_columns.py` — NEW: Database migration script (75 lines)
- `app/templates/access_denied.html` — NEW: Unapprovisioned user error page
- `app/templates/tasks/` — DELETED: Task templates moved to Overwatch

---


## 2026-03-13 — Navigation Redesign: CSS Grid Centering + CSS-Only Hover Dropdown

**Decision:** Used 3-column CSS grid (`1fr auto 1fr`) on `.nav-tabs-inner` instead of flexbox with `margin-left: auto` or `justify-content: center` to center the tab row.

**Rationale:** Pure flexbox can't truly center a group of items when there's an asymmetric element (the search bar) on the right. `margin-left: auto` on the search would push tabs left, not center them. A 3-column grid (empty spacer | tabs | search) gives mathematically correct centering regardless of search bar width.

**Decision:** CSS-only hover dropdown for user menu (`.user-menu:hover .user-dropdown { display: block }`). No JavaScript.

**Rationale:** Spec explicitly allowed CSS-only. Avoids a JS event listener, simpler to maintain, and works without any DOM-ready hooks. Dropout appears on hover within 0ms.

**Decision:** Lucide `<i data-lucide="target">` element replaces inline SVG for brand icon.

**Rationale:** Lucide CDN already loaded on every page via `_nav.html`. Using `data-lucide` attribute + `lucide.createIcons()` (called in `icons.js`) keeps markup clean and makes future icon swaps a one-word change. Inline SVG paths are brittle and hard to read.

**Impact:** `app/templates/_nav.html`, `app/static/crm.css`. No backend changes. 99 tests unaffected.

**Note for next related feature:** The Tasks tab is present in the nav but `/crm/tasks` returns 404 until SPEC_tasks-page.md is implemented. This is intentional — nav was built ahead of the route.

## 2026-03-13 — Pipeline Polish: `owner` field for task initials, not `assigned_to`

**Decision:** Used `owner` field (not `assigned_to`) to derive task assignee initials in the pipeline Tasks column.

**Rationale:** The spec referenced `assigned_to` on task objects, but both task sources (`load_tasks_by_org` → `_tasks` and `get_all_prospect_tasks` → `prospect_tasks`) use `owner` as the assignee field. `assigned_to` exists on the prospect itself (the team member managing the deal), not on individual tasks. Implemented against actual data shape.

**Impact:** `app/templates/crm_pipeline.html` (task rendering, initials extraction, `.at-glance-cell` CSS), `app/static/crm.js` (`stripMarkdown()` utility added as global).

---

## 2026-03-13 — Pipeline Polish: `crm.js` not previously loaded in pipeline template

**Decision:** Added `<script src="/static/crm.js">` to `crm_pipeline.html` to expose `stripMarkdown()`.

**Rationale:** `crm.js` was only loaded via `_nav.html` on pages that include the nav partial. The pipeline template does include the nav, but `crm.js` was loaded as a separate explicit tag rather than relying on nav inclusion order — safer and more explicit.

**Impact:** `app/templates/crm_pipeline.html`. Other templates that render nav already have access to `stripMarkdown()` via the same load path.


---

## 2026-03-13 — Prospect Detail Overhaul

**Decision:** Removed the Quick Actions card (Add Task / Quick Note pill toggle) entirely from the prospect detail page rather than keeping it as a secondary entry point.
**Rationale:** The card duplicated functionality already present in the Tasks card (+ Add Task button → modal) and Notes Log (textarea form). Keeping two entry points caused confusion about which one was canonical, especially after notes became auto-attributed and no longer needed an author input.
**Impact:** `app/templates/crm_prospect_detail.html` — HTML card, CSS block, and all JS functions (`switchQA`, `setPriority`, `submitQuickTask`, `submitQuickNote`, etc.) removed.

---

**Decision:** Note author is now auto-populated server-side from `g.user.display_name` (fallback: `g.user.email`) — the Name field was removed from the Notes form entirely.
**Rationale:** With multi-user auth in place, asking the user to type their own name is redundant and error-prone (typos, different spellings). The server has the authoritative identity via `g.user`.
**Impact:** `api_add_prospect_note` in `crm_blueprint.py` no longer reads `author` from the request body. Frontend `submitNote()` no longer sends it. Historical notes in the DB retain whatever author was stored at write time.

---

**Decision:** `collect_relationship_data` is now wrapped in try/except in both `_run_prospect_brief` and `api_prospect_brief` GET. Errors are logged and return empty data rather than propagating as 500s.
**Rationale:** Root cause of "Brief generation unavailable" — the GET /brief endpoint had no error boundary. If `collect_relationship_data` threw (e.g., a DB timeout or missing config), Flask returned 500, which the frontend's catch block turned into the unavailable message. The fix ensures the page always loads even if data collection partially fails.
**Impact:** `crm_blueprint.py` `_run_prospect_brief` and `api_prospect_brief`. Errors now print to server log instead of silently turning into client-visible "unavailable".

---

**Decision:** Scan Email button (in page header) reuses the existing `/email-scan` endpoint (90-day deep scan) rather than adding a new 60-day variant as the spec suggested.
**Rationale:** The existing endpoint is already well-tested, handles dedup, enriches org domains and contact emails, and works correctly. The difference between 60 and 90 days is immaterial in practice. Adding a new route would have duplicated significant logic.
**Impact:** `runScanEmail()` JS function in `crm_prospect_detail.html` calls `/email-scan`, then auto-triggers `refreshBrief()`. No new backend route added.

## 2026-03-13 — Tasks Page: DB-Backed Function Over TASKS.md

**Decision:** Added `get_all_tasks_for_dashboard()` as a new DB-backed function querying `prospect_tasks` directly, rather than reusing the existing `get_all_prospect_tasks()` which reads TASKS.md. The new function joins with `organizations` and `prospects` to enrich each task with deal size and offering.

**Rationale:** The spec explicitly targets the `prospect_tasks` DB table. The existing TASKS.md functions are legacy — they exist because the task system was never fully migrated to PostgreSQL. A clean DB-backed function avoids TASKS.md file access on every page load and enables proper DB queries (filter by status, join for enrichment).

**Known gap:** Prospect detail page task CRUD (`get_tasks_for_prospect`, `add_prospect_task`, `complete_prospect_task`) still read/write TASKS.md. This creates a split-system state: tasks created via the prospect detail page (TASKS.md) won't appear on `/crm/tasks` (DB-only). Resolving this requires migrating the prospect detail task CRUD to use the `prospect_tasks` table — deferred.

**Rejected:** Reusing `get_all_prospect_tasks()` — returns TASKS.md data with no prospect enrichment; would require separate prospect lookups and can't filter by DB status.

**Impact:** `app/sources/crm_db.py` (new function), `app/delivery/crm_blueprint.py` (new route + `g` import), `app/templates/crm_tasks.html` (new file), `app/tests/test_crm_db.py` (2 new tests).

---

## 2026-03-13 — Tasks Page: Row Click → Prospect Detail (Not Modal)

**Decision:** Clicking a task row on `/crm/tasks` navigates to the prospect's detail page rather than opening an inline edit modal.

**Rationale:** The existing task edit API has no `PUT /api/tasks/<id>` endpoint — only create (`POST`) and complete (`PATCH /complete`). Building a modal would require a new API endpoint. The prospect detail page already has full task management UI. Navigation is simpler and doesn't block the spec.

**Impact:** `app/templates/crm_tasks.html`. URLs are pre-computed in the route using `urlquote` (Python) rather than Jinja — Jinja2 has no built-in filter for URL path segment encoding.

---

## 2026-03-13 — Tasks Page: `detail_url` Pre-Computed in Route

**Decision:** `detail_url` for each task (prospect detail page link) is pre-computed in the Python route using `urlquote(org, safe='')` and `urlquote(offering, safe='')`, then passed to the template as part of each task dict.

**Rationale:** Jinja2's built-in `urlencode` filter encodes entire query strings, not individual path segments. Org/offering names contain spaces and special characters. Encoding in Python is explicit and correct.

**Impact:** `app/delivery/crm_blueprint.py` (`crm_tasks` view function), `app/templates/crm_tasks.html`.
