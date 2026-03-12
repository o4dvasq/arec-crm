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
