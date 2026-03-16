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

## 2026-03-15 — Tasks Board: Owner-Grouped Kanban (Replace 3-Column Layout)

**Decision:** Replaced the 3-column layout (Fundraising-Me / Fundraising-Team / Other Work) with a single-scroll owner-grouped Kanban. All tasks from all sections are gathered, tagged with `_section`, regrouped by `ownerKey()`, and rendered as stacked owner groups. Oscar (`__oscar__`) always first; others alphabetical.

**Rationale:** The 3-column layout forced a mental model split (section vs. assignee). The primary workflow question is "what does each person own?" not "which bucket is this in?" Section is preserved as a subtle label on each card for context without becoming the organizing axis.

**Rejected:** Keeping columns and adding an owner filter. Adds complexity without fixing the fundamental grouping problem.

**For the next designer:** `ownerKey()` normalizes `''`, `'oscar'`, and `'oscar vasquez'` → `'__oscar__'`. Other owners normalize to lowercase first name. If two people share a first name, they'll merge into one group — a known limitation acceptable for the current team size.

**Impact:** `app/static/tasks/tasks.js` (full rewrite), `app/static/tasks/tasks.css` (full rewrite).

---

## 2026-03-15 — Prospect Detail: CURRENT_USER Injected Server-Side

**Decision:** `config['current_user']` is set in the `prospect_detail` route in `crm_blueprint.py` using `getattr(g, 'user', None) or os.environ.get('DEV_USER', 'Oscar Vasquez')`. The Jinja template exposes it as `const CURRENT_USER = {{ config.current_user | tojson }};`. `submitNote()` uses `CURRENT_USER` directly instead of reading from an author input field.

**Rationale:** `load_crm_config()` does not include the current user — it reads from `config.md` which contains team, stages, and org types. The user identity comes from `g.user` (set by `before_request` from `DEV_USER` env var). Adding it to the config dict in the route was the minimal change with no impact on other callers of `load_crm_config()`.

**Rejected:** Reading author from a form input (removed), fetching from a `/me` endpoint (overkill for single-user), adding `current_user` to `load_crm_config()` itself (wrong layer — config.md is static team config, not runtime user identity).

**Impact:** `app/delivery/crm_blueprint.py` (one line added in `prospect_detail`), `app/templates/crm_prospect_detail.html` (`CURRENT_USER` constant, `submitNote()` simplified).

---

## 2026-03-15 — Brief Initial State: Empty Div, No Spinner

**Decision:** The static HTML for `#relationship-brief` on Prospect Detail is now an empty div. The loading spinner (`brief-loading`) only appears when the user clicks Refresh (triggered by `showBriefLoading()` inside `refreshBrief()`). On page load, `loadBrief(data)` is called after the data fetch completes and directly renders the saved brief or the "Generate Brief" placeholder.

**Rationale:** The spec requires the brief to load "persistent from disk, no loading spinner on page load." The brief data is fetched as part of `loadPageData()` in a single `/brief` GET call — it arrives with the rest of the page data. Showing a spinner for data that's already in the response was misleading UX.

**Impact:** `app/templates/crm_prospect_detail.html` (removed spinner from static HTML only; `showBriefLoading()` and `refreshBrief()` preserved for user-triggered refresh).

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

## 2026-03-14 — postgres-local Branch: Single-User PostgreSQL Without Auth

**Decision:** Created `postgres-local` branch off `deprecated-markdown` (not `azure-migration`) as a clean incremental migration path. Branch 1 scoped to: replace markdown backend with PostgreSQL, no auth, no multi-user, no Azure.

**Key choices:**

1. **No User model, no Enums** — `models.py` uses plain `String` for `urgency`, `closing`, `type`, `source` instead of SQLAlchemy `Enum`. No `User` table, no FK relationships to users. Avoids migration complexity and keeps the branch deployable locally without Azure AD.

2. **Team hardcoded in `load_crm_config()`** — Rather than query a `users` table (which doesn't exist), team members are a hardcoded list in `crm_db.py`. Matches the `deprecated-markdown` branch behavior where team came from `config.md`.

3. **SQLite-aware `db.py`** — `pool_size`/`max_overflow`/`pool_pre_ping` args are PostgreSQL-only. Detect `database_url.startswith('sqlite')` and skip them. Required for CI tests to work with `sqlite:///:memory:`.

4. **`prospect_meetings` stays JSON** — No `prospect_meetings` DB table in Branch 1. `save_prospect_meeting` / `load_prospect_meetings` / `delete_prospect_meeting` remain JSON file wrappers using `crm/prospect_meetings.json`. Avoids expanding scope.

5. **`seed_from_markdown.py` uses `crm_reader.py` as last consumer** — Seed script is the only remaining caller of `crm_reader.py`. All production routes use `crm_db.py`. The script imports `crm_reader` explicitly to parse markdown; writes to DB via direct model inserts (not `crm_db.py` write functions, which require an existing session context).

6. **Prospect auto-creates orgs during seeding** — Some orgs appear in `prospects.md` but not `organizations.md`. `seed_prospects()` auto-creates them with blank type rather than skipping the prospect. Means the second `seed_from_markdown.py` run will also pick up contacts that were skipped on the first run.

7. **Idempotent seed by structural key** — Each seed function checks existence by natural key (name for orgs/offerings, `(name, org_id)` for contacts, `(org_id, offering_id, disambiguator)` for prospects, `(brief_type, key)` for briefs, `message_id` for email log). No `--reset` flag needed; re-runs are safe.

**For the next designer (Branch 2: Azure deploy):**
- `conftest.py` uses `TEST_DATABASE_URL` env var, defaulting to `sqlite:///:memory:`. CI always uses SQLite.
- `test_tasks_api_key.py` is an untracked file leaked from `azure-migration` via Dropbox. It will fail on `postgres-local` because `DEV_USER` and `OVERWATCH_API_KEY` auth don't exist in this branch. Exclude with `--ignore` or delete.
- `auto_migrate.py` runs on every app startup — additive only, never drops columns. Safe to run in production.
- The 4 task DB functions (`load_tasks_by_org`, `get_tasks_for_prospect`, `add_prospect_task`, `complete_prospect_task_by_id`) are DB-backed in `crm_db.py` on this branch, not TASKS.md-backed as in `deprecated-markdown`.

**Impact:**
- `app/models.py` (full rewrite — no User, no Enums)
- `app/sources/crm_db.py` (User/Enum references removed, task functions DB-backed)
- `app/db.py` (SQLite-safe pool args)
- `app/auto_migrate.py` (new)
- `app/delivery/dashboard.py` (DB init, crm_db imports, root → /crm redirect)
- `app/delivery/crm_blueprint.py` (import swapped to crm_db)
- `app/delivery/tasks_blueprint.py` (crm_db for CRM task routes)
- `app/tests/conftest.py` (full rewrite with SQLite in-memory fixtures)
- `app/tests/test_crm_db.py` (new, 52 tests)
- `scripts/seed_from_markdown.py` (new)
- `app/.env.example` (new)

---

## 2026-03-14 — postgres-local Import Cleanup: Short-Circuit Over Swap for Graph API Routes

**Decision:** For the two Graph API routes (`email-scan`, `auto-capture`), replaced the entire route body with a 501 stub rather than swapping the import and letting it fail at the auth step (Option B over Option A from the spec).

**Rationale:** Option A (swap import, fail at Graph auth) would have imported `auth.graph_auth` and `sources.ms_graph` — modules that may not exist cleanly on this branch. Option B avoids any risk of import-time errors on app startup while still returning a clear error message to any caller. The 501 stub is also self-documenting.

**Confirmed present in `crm_db.py`:** All 5 functions required by the spec (`load_prospect_meetings`, `save_prospect_meeting`, `find_person_by_email`, `get_org_domains`, `add_emails_to_log`) already existed. No additions were needed.

**For the next designer (Branch 2):** When re-enabling Graph API features, restore the full `email-scan` and `auto-capture` route bodies from `deprecated-markdown` or `azure-migration` branch. The 501 stubs are intentional placeholders, not permanent behavior.

**Impact:** `app/delivery/crm_blueprint.py` (2 routes short-circuited), `app/sources/relationship_brief.py` (5 imports), `app/briefing/prompt_builder.py` (2 imports).

---

## 2026-03-14 — Task API Auth: require_api_key_or_login Decorator + DEV_USER Bypass

**Decision:** Added `@require_api_key_or_login` to all 5 task API routes. Auth logic lives in `app/auth/decorators.py`. Browser sessions auto-populated via `before_request` hook using `DEV_USER` env var (local dev bypass) or `session['user']` (future SSO).

**Key choices:**

1. **DEV_USER bypass instead of no-auth** — Rather than leaving task routes open (no decorator), or requiring full SSO (not built yet), `DEV_USER=oscar@avilacapllc.com` in `.env` auto-populates `g.user` on every browser request. Tests set `DEV_USER=''` to disable it and test API key paths in isolation.

2. **`OVERWATCH_API_KEY` unset = session required (not open)** — When the env var is unset, the API key path is skipped entirely. Session (`g.user`) is still required. This matches the spec: unset = disabled, not permissive. Consequence: on this branch, if `OVERWATCH_API_KEY` is unset AND `DEV_USER` is unset, all 5 routes return 401. Intentional.

3. **Import aliases for mockability** — Functions are imported with `as` aliases (`get_tasks_for_prospect as get_tasks_for_prospect_db`, etc.) so tests can mock `delivery.crm_blueprint.get_tasks_for_prospect_db` directly. Tests already existed pre-written expecting these names.

4. **`add_prospect_task_and_return` over refactoring `add_prospect_task`** — The original `add_prospect_task` returns `bool`. Callers in `tasks_blueprint.py` and `dashboard.py` treat the return as truthy. Adding a second function that returns a task dict avoids breaking existing callers and keeps the DB layer backward-compatible.

5. **`PATCH /crm/api/tasks/complete` now uses `{id}` not `{org, task_text}`** — The old form did text-substring matching (`ILIKE '%text%'`) which could match wrong tasks. ID-based completion is exact. The `crm_tasks.html` page and the spec both use `{id}`.

**For the next designer:**
- Session auth via `session['user']` dict is the hook for Entra SSO (Branch 2). When SSO is added, `before_request` will set `g.user` from the SSO token instead of (or in addition to) `DEV_USER`.
- `app/auth/decorators.py` is the right place for future decorators (`@require_admin`, `@require_login`, etc.).
- `test_tasks_api_key.py` is now a tracked, first-class test file. Run it with the full suite: `pytest app/tests/ -v` (no `--ignore`).

**Impact:** `app/auth/decorators.py` (new), `app/delivery/dashboard.py` (secret_key, before_request), `app/sources/crm_db.py` (2 new functions), `app/delivery/crm_blueprint.py` (imports, decorators, 2 new routes, envelope standardization), `app/templates/crm_tasks.html` (new), `app/templates/_nav.html` (brand, link), `app/templates/dashboard.html` (link).

---

## 2026-03-14 — Azure Deploy: Root requirements.txt for Oryx antenv Build

**Decision:** Added `requirements.txt` at the repo root (identical copy of `app/requirements.txt`).

**Rationale:** Oryx (Azure App Service's build engine) scans for `requirements.txt` at the repo root to populate the `antenv` virtual environment during the build phase. With `requirements.txt` only at `app/requirements.txt`, Oryx built an empty `antenv`. The `startup.sh` pip install ran against system Python (`/opt/python/3.12.12`), not `antenv`. Gunicorn's PYTHONPATH was set to `antenv/lib/python3.12/site-packages` by Oryx, so none of the system-installed packages were visible. Result: `ModuleNotFoundError: No module named 'dotenv'` on every worker.

**Why the SCM restart error was misleading:** The deployment failure message said "Deployment has been stopped due to SCM container restart." This was a symptom — Azure restarted the container because the app kept crash-looping (gunicorn workers exiting with code 3). The actual error was in the docker log, not the deployment log.

**How we found it:** `az webapp log download` → unpacked zip → tailed `2026_03_14_*_default_docker.log`.

**Why the first boot worked:** The very first deployment succeeded because Oryx found a pre-existing `antenv` with packages already installed. After the failed redeployment, Oryx rebuilt `antenv` from scratch (empty), and the crash loop started.

**Rejected:** Fixing `startup.sh` to activate `antenv` before pip install — this would also work, but the root `requirements.txt` is the canonical fix. Oryx should own the dependency install; `startup.sh` pip install is a safety net, not the primary mechanism.

**For the next designer:** Keep `requirements.txt` at the repo root in sync with `app/requirements.txt`. When adding a new Python dependency, update both files. The root file exists purely for Oryx; the `app/` file is what `startup.sh` uses as its safety-net install.

**Impact:** `requirements.txt` (new at repo root). No code changes.

---

## 2026-03-14 — Rename memory/ to contacts/: Remove Productivity Plugin Data from CRM

**Decision:** Renamed `memory/people/` → `contacts/` (flat, no subdirectory). Removed `memory/context/`, `memory/glossary.md` from the CRM repo. Moved `memory/org-locations.md` → `crm/org-locations.md`, `memory/projects/arec-fund-ii.md` → `projects/arec-fund-ii.md`, and merged `memory/meetings.md` into `crm/meeting_history.md`.

**Rationale:** The `memory/` directory was a holdover from the local productivity plugin. In the CRM context, `memory/people/{name}.md` files are contact profiles — not "memories." The name caused confusion between the deployed CRM app and the local Claude plugin, and was visible in the Azure deployment artifact. Renaming to `contacts/` makes the purpose unambiguous.

**Key choices:**

1. **Flat directory** — `memory/people/{name}.md` → `contacts/{name}.md` (no `contacts/people/` subdirectory). The extra nesting added no value.

2. **Remove, don't migrate, plugin data** — `memory/context/me.md`, `memory/context/company.md`, and `memory/glossary.md` are productivity plugin files. They have no place in the deployed CRM and were removed entirely. They remain in the local plugin's `memory/` directory, which is a separate context.

3. **Filename cleanup** — `darren-sutton-dsuttonsuttoncapitalgroupcom.md` → `darren-sutton.md`. The email domain suffix was historical noise from an auto-naming script.

4. **Glossary path updated to `crm/glossary.md`** — `relationship_brief.py` checked for a glossary file. No glossary exists in CRM; the path now points to `crm/glossary.md` which gracefully returns `None` if absent, rather than silently never finding `memory/glossary.md`.

5. **Deploy pipeline updated** — `.github/workflows/azure-deploy.yml` zip now includes `contacts/` and `projects/` instead of `memory/`. No `memory/` directory will appear in the deployment artifact.

**For the next designer:**
- Email-scan and related skills in `.skills/` (local plugin) may still reference `memory/people/`. Those are in the local plugin codebase and should be updated separately to point to `contacts/` for CRM operations.
- `contacts/{name}.md` files follow the same naming convention: lowercase with hyphens.
- `crm/contacts_index.md` (a flat lookup file) and `contacts/` (a directory of profiles) coexist cleanly — no naming collision.

**Impact:** `contacts/` (211 files, new), `projects/arec-fund-ii.md` (new), `crm/org-locations.md` (new), `crm/meeting_history.md` (merged), `memory/` (deleted), `app/sources/crm_db.py` (`PEOPLE_ROOT`), `app/sources/crm_reader.py` (`MEMORY_ROOT`/`PEOPLE_ROOT`), `app/sources/relationship_brief.py` (3 path joins + glossary path), `app/briefing/prompt_builder.py` (intel file path), `app/delivery/crm_blueprint.py` (4 path joins), `app/scripts/bootstrap_contacts_index.py` (`PEOPLE_DIR`), `scripts/seed_from_markdown.py` (docstring), `scripts/migrate_to_postgres.py` (docstring), `.github/workflows/azure-deploy.yml` (zip contents).

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

---

## 2026-03-15 — Overwatch Repo Scaffold: Task Sections, No CRM Imports, Port 3002

**Decision:** Created `~/Dropbox/projects/overwatch/` as a standalone Flask app with its own TASKS.md, `data/` directory, and briefing system. Task sections are `Work` and `Personal` (not CRM fundraising sections). App runs on port 3002.

**Key implementation choices:**

1. **Copy, don't move** — All source files copied from arec-crm; originals untouched. Cleanup of arec-crm duplicates (meeting-debrief skill, Personal section in TASKS.md) deferred to a later pass after Overwatch is in daily use.

2. **tasks_blueprint.py stripped of CRM routes** — Removed `from sources.crm_reader import load_crm_config, get_tasks_for_prospect, add_prospect_task` and the 4 CRM-specific routes (`/api/tasks/for-org`, `/api/tasks/prospect*`). Overwatch tasks have no concept of prospect orgs.

3. **prompt_builder.py simplified** — Removed investor intelligence section (prospect matching, `load_prospects()`, `load_interactions()`). Overwatch briefing covers schedule + work/personal tasks only. The CRM-flavored SYSTEM_PROMPT replaced with a personal productivity variant.

4. **No shared Python modules** — CLAUDE.md constraint: Overwatch can read arec-crm _data files_ by filesystem path but never imports arec-crm Python modules. Protects against circular dependency and deployment coupling.

5. **Pre-existing Dropbox files committed** — The overwatch directory already had `meeting-summaries/`, `memory/`, `docs/`, and other files from a prior Dropbox-synced prototype. These were included in the initial commit rather than deleted, since they may have context value.

6. **Port 3002** — arec-crm uses 8000 (not 3001 as the spec draft said). Overwatch assigned 3002. CLAUDE.md corrects the port reference.

**For the next designer:**
- `~/Dropbox/projects/overwatch/app/main.py` (inside `app/`) is a legacy file from the Dropbox sync. The canonical entry point is `~/Dropbox/projects/overwatch/main.py` at project root.
- iPhone Shortcut file path needs updating from arec-crm `inbox.md` → `~/Dropbox/projects/overwatch/inbox.md`.
- Personal section still exists in arec-crm TASKS.md — leave until Overwatch is confirmed as daily driver, then delete from arec-crm.
- Overwatch has no GitHub remote yet. Run `/leave-machine` from the overwatch project directory to push.

**Impact:** New repo at `~/Dropbox/projects/overwatch/`. No arec-crm files modified.

---

## 2026-03-16 — `/crm-update` Cowork Skill: 8-Step CRM Intelligence Cycle

**Decision:** Implemented the `/crm-update` Cowork skill as a step-by-step instruction file at `~/.skills/skills/crm-update/SKILL.md`. The skill drives an 8-step interactive workflow: (1) load state, (2) process Overwatch queue, (3) 4-pass email scan, (4) calendar scan, (5) Tony's Excel deferred, (6) meeting summaries, (7) enrichment + stale flagging, (8) summary report.

**Key implementation decisions:**

1. **Skill-as-instructions, not a script** — Consistent with other skills in `~/.skills/`. The operations (MCP email/calendar calls, crm_reader.py writes) are orchestrated interactively. A Python script would require reimplementing MCP access patterns and would lose the interactive triage loop for unmatched items.

2. **Queue takes highest priority (Step 2 before email scan)** — Overwatch queue items are already classified. Processing them first avoids double-counting: if an email was queued by Overwatch AND appears in the 4-pass email scan, the queue entry wins and the email scan skips it (overlap rule in Step 3d).

3. **4 passes, not 5** — The existing `/email-scan` skill runs 5 passes (adds a CRM shared mailbox). `/crm-update` omits that pass for now. Reason: this is an incremental build; adding the 5th pass is a one-line addition when ready.

4. **Tony's delegate access via `recipient:`/`sender:` params** — Tony's email accessed by filtering Oscar's MCP session by `recipient: tony@avilacapllc.com` and `sender: tony@avilacapllc.com`. No separate delegate session required. Confirmed working via the existing email-scan skill.

5. **Omit `query` parameter on email search** — Passing `"*"` to `outlook_email_search` breaks the Microsoft 365 MCP connector. All email scan calls omit `query` entirely. Calendar search uses `query: "*"` (different connector behavior).

6. **5 internal AREC domains, not 2** — Initial spec draft listed only `avilacapllc.com` and `avilacapital.com`. Audit found 3 more: `encorefunds.com` (Tony's alternate), `builderadvisorgroup.com`, `south40capital.com`. All 5 are in the skip rules.

7. **`crm/ai_inbox_queue.md` created as empty skeleton** — File must exist for the skill to work on first run. Overwatch writes entries in queue format. The skill checks for the file and skips Step 2 if absent (defensive for early runs before Overwatch integration is live).

8. **Idempotency via two dedup mechanisms** — Email scan: `email_log.json` messageIds. Queue processing: status check (never re-process `done`/`skipped` items). Calendar: check `crm/interactions.md` for existing entry with same org+date+type before writing a Scheduled Meeting.

9. **Tony's Excel deferred, not removed** — Feature scaffolded as Step 5 with a config-gated skip. When `## Excel Tracker` appears in `crm/config.md`, the step activates. Keeps the skill design stable without requiring Oscar to track the Excel file path now.

**Rejected approaches:**
- Merging with `/email-scan` — email-scan enriches Overwatch `memory/people/` files; crm-update enriches CRM contacts. Different targets, different purposes. They run in different contexts (Overwatch vs. arec-crm).
- Auto-creating CRM records without confirmation — All new org creation and contact creation requires Oscar's confirmation during interactive triage.

**For the next designer:**
- The queue format (`crm/ai_inbox_queue.md`) is a shared contract between Overwatch and arec-crm. If the format changes, update both `SPEC_crm-update-workflow.md` and the Overwatch ingress spec.
- The skill is in `~/.skills/` (local machine), not in the arec-crm repo. It won't appear in git status. After machine switch, check that `~/.skills/skills/crm-update/SKILL.md` exists.
- `crm/email_log.json` `lastScan` is `2026-03-11`. First run of `/crm-update` will scan the 5-day gap since then.

**Impact:** `~/.skills/skills/crm-update/SKILL.md` (new), `crm/ai_inbox_queue.md` (new skeleton).

---

## 2026-03-15 — CRM Markdown Cleanup: Revert to Markdown-Only Local App

**Decision:** Stripped all PostgreSQL, Azure App Service, Entra ID, and multi-user infrastructure from the codebase. The app returns to a clean markdown-only local CRM backed by `crm_reader.py`.

**Rationale:** After ~5 days on the Azure migration, the deployment complexity (Oryx, gunicorn, cold start, Key Vault, Entra SSO) was blocking daily use. For a single-user local tool, the overhead was not justified. See `docs/archive/azure-migration-march-2026/LESSONS_LEARNED.md` for full retrospective.

**Key implementation decisions:**

1. **`require_api_key_or_login` kept as no-op passthrough, not deleted** — All 5 `/crm/api/tasks*` routes retain the decorator so the auth pattern is preserved for a future multi-user scenario. The decorator body is a passthrough; removing it would require editing 5 route definitions.

2. **Graph-dependent routes return 501, not 404 or 200** — `email-scan` and `auto-capture` in-app routes return `501 Not Implemented` with a message directing to the Claude Desktop skill. 501 is semantically correct (server doesn't support the feature in this configuration) and more debuggable than 404 or a silent empty response.

3. **`email_matching.py` extracted, not lost** — The three utility functions (`_fuzzy_match_org`, `_is_internal`, `_resolve_participant`) in the deleted `crm_graph_sync.py` had no Graph dependency and were under test. Rather than delete `test_email_matching.py`, the functions were extracted to `app/sources/email_matching.py`. The email-scan skill uses them via `crm_graph_sync.py` on the Claude Desktop side, not via the Flask app.

4. **`main.py` guarded, not deleted** — The morning briefing script is still useful when Graph credentials are available. Wrapping imports in `try/except ImportError` and gating all Graph calls behind `_GRAPH_AVAILABLE` lets it run gracefully in both modes.

5. **Task routes returning 501 vs. alternative implementations** — The 3 DB-only task operations (`complete_by_id`, `update_by_id`, `add_and_return`) could theoretically be approximated in markdown (e.g., text-based completion, synthetic ID from enumerate). Chose 501 for now because (a) the Overwatch integration isn't live, (b) the spec didn't ask for approximations, and (c) a real solution would need a stable ID scheme.

**Rejected approaches:**
- Keeping `crm_db.py` as a fallback (adds ~2000 lines of dead code with no user)
- Moving to SQLite (same complexity win as just using markdown; adds a file to manage)

**For the next designer:** The branch formerly called `postgres-local` (renamed to `main` on 2026-03-15) still has the full SQLAlchemy schema and 128 tests in git history if a DB layer is ever needed again. The `docs/archive/azure-migration-march-2026/` folder has lessons learned and all archived specs.

**Impact:**
- Deleted: `crm_db.py`, `models.py`, `db.py`, `auto_migrate.py`, `crm_graph_sync.py`, `entra_auth.py`, all migration scripts, `startup.sh`, `DEPLOYMENT.md`, Azure workflow, Postgres test files
- Modified: `dashboard.py`, `crm_blueprint.py`, `tasks_blueprint.py`, `decorators.py`, `main.py`, `requirements.txt` (both), `conftest.py`, `CLAUDE.md`
- New: `app/sources/email_matching.py`
- Archived: Azure/Postgres specs to `docs/archive/azure-migration-march-2026/`


## 2026-03-16 — Shared Inbox Priority Elevation + Multi-User Attribution

**Decision:** All emails forwarded to `crm@avilacapllc.com` write to `crm/ai_inbox_queue.md` (not `inbox.md`) with `Source: crm-shared-mailbox`, `Priority: high`, and `ForwardedBy: {first name or email}`. `inbox.md` returns to voice-capture-only duty.

**Key implementation decisions:**

1. **Unified queue, not a separate intake point** — Before this spec, `drain_inbox.py` wrote to `inbox.md` while Overwatch wrote to `ai_inbox_queue.md`. Two intake points meant `/crm-update` had to check both files. Unifying on `ai_inbox_queue.md` with `Source: crm-shared-mailbox` means a single loop in Step 2 handles all pending items.

2. **`Priority: high` for all shared inbox items** — Forwarding to `crm@` is a deliberate human action; it's a stronger signal than passive email scanning. All shared inbox items get elevated priority regardless of content. Normal-priority items (Overwatch-originated) simply lack the `Priority` field — backward-compatible.

3. **Forwarder from envelope sender, not original From** — The Graph API `message.from.emailAddress` on messages in the shared mailbox is the envelope sender (the person who hit Forward), not the original email's From header. This is the right field for attribution.

4. **Name resolution via `crm/config.md → ## AREC Team`** — Team email → first name mapping is parsed at runtime (not hardcoded) so adding new team members to config.md automatically propagates. Falls back to raw email if unresolved — processing continues either way.

5. **Org matching on original sender, not forwarder** — The forwarder is always an AREC internal address. Matching org on their email would always fail. Org matching uses the original email's From field (the external sender).

6. **Non-forwarded emails to `crm@` still queued** — If someone sends directly to `crm@` (not a forward), the full body becomes the intent note. `is_forward: False`. These are likely teammates writing directly; they're queued with `Org: unknown` for interactive triage.

**Rejected approaches:**
- Writing shared inbox items to a separate high-priority queue file — adds another intake point to check; `Priority` field achieves the same ordering with one file.
- Blocking on forwarder resolution failure — best-effort; unresolved email addresses are recorded and processing continues.

**For the next designer:**
- The `Priority` field is now part of the queue schema. Overwatch items don't include it; `/crm-update` Step 2 treats absent `Priority` as `normal`. Any new queue source should include `Priority: normal` explicitly.
- `inbox.md` still exists for Siri Shortcut voice capture. Do not route any code output there except the iPhone Shortcut.
- `crm/config.md → ## AREC Team` line format is `- First Last | email@domain.com`. Parser splits on ` | ` and takes the first word of the name as the display name.

**Impact:** `app/drain_inbox.py` (modified), `app/tests/test_drain_inbox.py` (new — 17 tests), `skills/email-scan.md` (Pass 5 updated), `~/.skills/skills/crm-update/SKILL.md` (Step 2 priority ordering added), `crm/ai_inbox_queue.md` (new entries target).

---

## 2026-03-16 — Person Detail: Inline Edit Over Full Edit Modal

**Decision:** Title, Email, and Phone on Person Detail are now always rendered and individually editable via click-to-inline-edit (replacing the full Edit form for per-field updates). The full Edit button remains for bulk edits.

**Rationale:** The spec called for inline edit as the primary UX for empty-field discovery and quick fill. The existing full Edit form required loading all fields into a modal, saving all at once — too heavy for the common case of adding a single missing email or phone.

**Key implementation choices:**

1. **Always render all three fields** — `renderPersonCard()` renders Title, Email, Phone unconditionally. Empty fields show `--` in muted italic. Previously, empty fields were omitted entirely, hiding the fact that they could be edited. Card is also always shown (removed the `contactRows.length === 0` hide guard).

2. **Reload full card on save, not optimistic update** — After a successful PATCH, `renderPersonCard()` is re-called with a fresh fetch of person data. This ensures the email/phone display (which linkifies values) is always correct. Considered optimistic update but the linkify logic made it non-trivial.

3. **`saved` flag to prevent double-save** — `blur` fires after `Enter` keydown in some browsers. A `saved` boolean guards against the PATCH being called twice on Enter.

4. **Going-forward auto-set hooks into `add_contact_to_index()`** — Rather than a separate trigger point, the auto-set fires inside `add_contact_to_index()`. This is the single chokepoint for all contact additions (direct calls + `ensure_contact_linked()`), so no case is missed.

5. **Batch heuristic uses `Contact:` field in interactions** — Interactions have a `- **Contact:** Name` bullet. For multi-contact orgs, the batch script iterates interactions newest-first and takes the first one whose Contact field matches a known contact for that org. No brief parsing needed (complex, unreliable).

6. **Batch script lives in `scripts/`, not `app/`** — One-time admin script. No Flask import needed; uses `sys.path.insert` to reach `app/sources/crm_reader`.

**For the next designer:** The inline edit fields (Title, Email, Phone) share CSS class `.inline-edit-input`. Company field is intentionally NOT inline-editable — it's a relational link to an org record and uses a `<select>` dropdown in the full Edit form. Do not add inline edit to Company without thinking through org reassignment implications.

**Impact:** `app/templates/crm_person_detail.html` (CSS, `renderPersonCard()`, new inline edit functions), `app/sources/crm_reader.py` (`add_contact_to_index()` + new `_auto_set_primary_contact_for_org()`), `scripts/batch_primary_contact.py` (new), `crm/prospects.md` (1 record updated).

---
