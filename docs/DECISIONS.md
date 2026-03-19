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

## 2026-03-18 — Tony Excel Sync: Egnyte API Integration with Fuzzy Matching + Alias Support

**Decision:** Implemented daily sync from Tony Avila's Excel fundraising tracker in Egnyte to CRM prospects using three-tier org name matching (alias lookup → exact match → fuzzy match) with confidence-based auto-apply.

**Rationale:** Tony maintains an authoritative Excel file (`AREC Debt Fund II Marketing A List - MASTER as of [Date].xlsx`) in Egnyte with prospect updates from his relationship network. He will not use the CRM dashboard directly. Auto-syncing his updates eliminates manual data entry while preserving data quality through confidence thresholds and email notification before writes.

**Key implementation choices:**

1. **Egnyte API polling, not webhooks** — Runs daily at 6 AM via `app/main.py` after auto-capture step. Polls folder for new file versions, compares against `crm/tony_sync_state.json`. Webhook-based triggering requires public HTTPS endpoint (not available in local Flask).

2. **Three-tier org name matching** — (1) Alias lookup in `crm/org_aliases.json` (exact, confidence 1.0), (2) Exact match against `organizations.md`, (3) Fuzzy match using `difflib.SequenceMatcher`. High confidence ≥0.85 auto-applies; 0.60–0.84 flags for manual review; <0.60 treats as new org.

3. **Parenthetical stripping before matching** — Tony's Excel has org names like "UTIMCO (Matt Saverin)" and "Khazanah Americas (Malaysia) Cash Ryan Mulligan". Strips `(...)` substrings before matching to avoid false negatives.

4. **Name normalization for Assigned To** — Tony uses shorthand ("Avila", "Reisner/Flynn"). `NAME_MAP` converts to full names. Slash-separated values → first name as primary.

5. **Priority 'x' → Declined, 'Closed' → Closed** — CRM stages `0. Declined` and `8. Closed` already exist in config.md. Sync sets stage only for these signals; all other priority values ignored.

6. **Email notification via MS Graph API** — Sends diff summary to Oscar and Paige (`ovasquez@avilacapllc.com`, `pkinsey@avilacapllc.com`) before applying changes. Uses same Graph auth as morning briefing.

7. **Unmatched orgs auto-created** — New orgs added to `organizations.md` and `prospects.md` as Stage 5 Interested, Urgency High. No manual provisioning step required.

8. **State file prevents re-processing** — `crm/tony_sync_state.json` tracks last processed file (filename + modified timestamp). No email or changes on no-op runs.

**Rejected approaches:**

- **Two-way sync (CRM → Excel)** — Would require complex conflict resolution. CRM always wins on Stage, Urgency, Target, Committed. One-way is simpler.
- **Webhook-based triggering** — Requires public HTTPS endpoint + Egnyte developer app setup. Daily poll via `main.py` is simpler for local Flask app.
- **Manual approval for all changes** — Would create review bottleneck. High-confidence threshold (0.85) is safe; Oscar can adjust aliases if mismatches occur.

**For the next designer:**

- `EGNYTE_API_TOKEN` must be obtained from Egnyte developer console and added to `app/.env` before first run.
- Aliases in `crm/org_aliases.json` are manually editable — add new entries as Tony naming patterns emerge.
- Low-confidence matches (0.60–0.84) require manual resolution. Check email diff, add alias if name is close but not exact.
- Tony's Excel columns D–I (Fund I, Spring Rock, Verbal pool, etc.) are out of scope — sync only reads Col A (Priority), Col B (Org), Col C (Point Person), Col K (Notes).

**Impact:**
- `app/sources/tony_sync.py` (NEW, ~700 lines)
- `crm/org_aliases.json` (NEW, seed aliases)
- `crm/tony_sync_state.json` (created on first run)
- `app/main.py` (added sync call after auto-capture)
- `app/.env` (documented EGNYTE_API_TOKEN)
- `docs/specs/implemented/SPEC_tony-excel-sync.md` (moved from specs/)

---

## 2026-03-18 — Pipeline Polish: Already Fully Implemented

**Decision:** SPEC_pipeline-polish.md was discovered to be already fully implemented during `/code-start` invocation. All acceptance criteria (At a Glance styling, Tasks column width, assignee initials, markdown stripping) were already present in the codebase. Spec moved to `docs/specs/implemented/`.

**Rationale:** The features were implemented in a prior session but the spec was not moved to implemented/. During investigation, confirmed all UI features working: `.at-glance-cell` CSS (lines 146-157), Tasks column 350px width (line 140), `getInitials()` function (lines 1723-1738), `stripMarkdown()` calls (lines 1734, 1749), and the utility function in `crm.js` (lines 46-53).

**Decision: Do Not Re-Implement Already Working Features.** Discovered 6 unrelated test failures in `test_tasks_api_key.py` (task grouping API bugs). Created detailed test failure report (`TEST_FAILURES_REPORT.md`) documenting root causes, expected vs actual behavior, and specific fixes needed for future work.

**Impact:**
- `docs/specs/SPEC_pipeline-polish.md` — should be moved to `docs/specs/implemented/`
- `TEST_FAILURES_REPORT.md` — NEW: complete diagnostic report on 6 failing tests (unrelated to pipeline polish)
- No code changes made (all features already working)

---
## 2026-03-18 — Person Name Linking: Client-Side `linkifyPersonNames()` Implementation

**Decision:** Person names throughout the app are made clickable using a client-side JavaScript approach: elements with `data-person-name` attribute are converted to links by the `linkifyPersonNames()` function, which reads person data from `window.SEARCH_INDEX`.

**Rationale:** Most of the implementation was already in place from a previous session (`linkifyPersonNames()` in `crm.js`, `.person-link` CSS, most `data-person-name` attributes). This session completed the implementation by adding the attribute to task assignees on prospect detail and ensuring the function is called after dynamic task rendering. Client-side approach minimizes template changes and avoids server-side slug lookup overhead.

**Key implementation details:**

1. **Existing infrastructure:** `linkifyPersonNames()` function (crm.js:9-37) processes `[data-person-name]` elements, matches names case-insensitively against `window.SEARCH_INDEX`, wraps in `<a class="person-link">` with `stopPropagation()` to prevent row click conflicts.

2. **Coverage:** Primary Contact on pipeline and prospect detail, note authors, task assignees (added this session), org contacts (already linked via `.contact-name-link`), people list (already linked).

3. **Unmatched names render as plain text** — No broken links for names not in the knowledge base.

4. **Partial names (initials) NOT linked** — Assignee initials on tasks page ("OV") are rendered as pills without `data-person-name`, per spec rule: "If only initials are shown, do NOT attempt to link them."

**Impact:**
- `app/templates/crm_prospect_detail.html` — Added `data-person-name` to task assignees (line 1222), added `linkifyPersonNames()` call after rendering (line 1228)
- `app/static/crm.js` — No changes (function already exists)
- `app/static/crm.css` — No changes (`.person-link` styles already exist)
- `docs/specs/implemented/SPEC_person-name-linking.md` — Spec moved from `docs/specs/`

---

## 2026-03-18 — Task Grouping API: Target-Based Sorting + Priority Normalization

**Decision:** Rewrote `get_tasks_grouped_by_prospect()` and `get_tasks_grouped_by_owner()` in `crm_reader.py` to implement filtering (done tasks, empty owners), priority normalization (high→Hi, normal→Med, low→Lo), and target-based sorting.

**Rationale:** Both functions were stubs that grouped tasks but applied no business logic. Tests were failing because:
1. Prospect groups sorted alphabetically instead of by target amount descending
2. Done tasks included in results when they should be filtered
3. Tasks without owner included when they should be filtered
4. Priority values stored as raw strings (`high`, `normal`, `low`) instead of normalized display values (`Hi`, `Med`, `Lo`)
5. Owner groups missing `max_target` field (KeyError in tests)
6. Owner groups sorted alphabetically instead of by max_target descending

**Implementation choices:**

1. **Load prospect data once per call** — Both functions call `load_prospects()` once at the top, build an `org_targets` dict keyed by org name, convert currency strings to integers using `_parse_currency()` for comparison.

2. **Priority normalization map** — `get_tasks_grouped_by_prospect()` normalizes priority on the fly before appending to group: `{'high': 'Hi', 'hi': 'Hi', 'normal': 'Med', 'med': 'Med', 'medium': 'Med', 'low': 'Lo', 'lo': 'Lo'}`. Handles both raw stored values and already-normalized values.

3. **Filtering rules** — Both functions skip tasks where `status == 'done'` or `owner.strip()` is empty. Prospect grouping also skips tasks with empty `org` field.

4. **Target-based sorting (prospect groups)** — Groups sorted by `target` descending. Orgs with no matching prospect record default to `target=0` and sort last.

5. **Max target calculation (owner groups)** — For each owner, iterate their tasks, look up org target for each task, track the highest value. This becomes `max_target` field on the group dict.

6. **Priority-based task sorting (owner groups)** — Within each owner's task list, sort by priority order: `{'Hi': 0, 'Med': 1, 'Lo': 2}`. Hi tasks appear first.

**Rejected approaches:**
- **Load prospect data per-group** — Would call `load_prospects()` repeatedly in a loop. Loading once and building a dict is O(n+m) instead of O(n*m).
- **Server-side priority normalization on write** — Would require backfilling all existing tasks. Normalizing on read is backward-compatible.

**Test results:** All 82 tests passing (was 76/82 before this fix). All 6 failing tests in `test_tasks_api_key.py` now pass.

**Impact:**
- `app/sources/crm_reader.py` — Rewrote `get_tasks_grouped_by_prospect()` (lines 2527-2582) and `get_tasks_grouped_by_owner()` (lines 2585-2636)
- `docs/specs/implemented/SPEC_task-grouping-api-fixes.md` — Spec moved from `docs/specs/`

---

## 2026-03-18 — Organization Merge: Atomic-ish Multi-File Migration

**Decision:** Implemented org merge as a coordinated sequence of 9 migration steps in `crm_reader.py`, with all migrations completing before the source org is deleted. If any migration fails, the source org is NOT deleted (atomic-ish behavior).

**Rationale:** Since the backend is file-based (not database), true ACID transactions aren't possible. But the spec requires that "if any step fails, stop and return an error — do not delete the source org on partial failure." The coordinator function (`merge_organizations()`) calls each migration helper in sequence and only calls `delete_organization(source)` as the final step if all prior steps succeed.

**Migration sequence:**
1. Combine org fields (aliases union, notes concatenate, add source name as alias)
2. Re-parent prospects (change `### OrgName` headings in `prospects.md`)
3. Move contacts (relocate slugs in `contacts_index.md`)
4. Update people files (change Company field in `memory/people/*.md`)
5. Re-attribute email log (update `orgMatch` field in `email_log.json`)
6. Re-key briefs (`OrgName::FundName` composite keys in `briefs.json`)
7. Re-key prospect notes (`prospect_notes.json`)
8. Re-key prospect meetings (`prospect_meetings.json`)
9. Delete source org (only if all prior steps succeeded)

**Key implementation choices:**

1. **Case-insensitive org matching throughout** — All lookups use `.lower()` to handle "SMBC" vs "Sumitomo Mitsui Banking Corporation" variations.

2. **Composite key re-keying for JSON stores** — Briefs, notes, and meetings use `OrgName::FundName` keys. Re-keying splits on `::`, checks if first part matches source (case-insensitive), then rebuilds key with target name.

3. **Source org name added as alias on target** — Ensures old name still resolves in future email scans, meeting notes, and manual searches. Uses existing alias infrastructure (`get_org_by_alias()`).

4. **No rollback on partial failure** — If step 5 succeeds but step 6 fails, steps 1-5 remain applied. Error is returned to user, source org NOT deleted, user must manually inspect/retry. Acceptable tradeoff for single-user file-based system.

5. **Preview endpoint is read-only** — `get_merge_preview()` only counts data, never modifies files. Prevents accidental writes during UI preview step.

**Rejected alternatives:**

- **Database with transactions** — Would require full PostgreSQL migration (out of scope, staying with markdown).
- **Git-based rollback** — Would require committing before merge, then `git reset --hard` on failure. Too complex for user-facing feature.
- **Two-phase commit** — Overkill for single-user system with no concurrent access.

**For the next designer:**

- If a merge fails partway, manually inspect the files listed in the error message. The source org will still exist in `organizations.md` (it was not deleted). You may need to manually undo partial changes or re-run the merge after fixing the error.
- Test merges on non-critical orgs first. Once deleted, the source org cannot be recovered except via git history.
- The merge does NOT update interactions.md directly (interactions are contact-based, not org-keyed, so they follow contacts automatically).

**Impact:**
- `app/sources/crm_reader.py` — Added `merge_organizations()` + 8 helper functions (~300 lines)
- `app/delivery/crm_blueprint.py` — Added imports for `get_merge_preview`, `merge_organizations`
- `app/templates/crm_org_edit.html` — Added merge button, modal UI, client-side flow
- `docs/specs/implemented/SPEC_merge-orgs.md` — Spec moved from `docs/specs/`

---
## 2026-03-18 — Tasks Page: Prospect-Enriched Task Rendering

**Decision:** Implemented `/crm/tasks` route to enrich tasks with prospect data (target, offering) and split into "My Tasks" and "Team Tasks" sections sorted by priority then deal size.

**Rationale:** The route and template existed but the route didn't load prospect data. Tasks displayed with `—` for deal size and no prospect links because `target`, `target_display`, and `offering` fields were missing. Users need context about which tasks are tied to high-value prospects vs low-value ones.

**Implementation choices:**

1. **Load prospects once per request** — Builds `org_prospect_map` dict at route entry, indexed by `org.lower()` for case-insensitive lookup.

2. **Enrich tasks with prospect data** — Loops through all tasks, looks up prospect by org name, adds:
   - `target` (float, parsed via `_parse_currency()` for sorting)
   - `target_display` (string, formatted like "$50M" for display)
   - `offering` (string, for building prospect detail URL)
   - `detail_url` (constructed from offering + org)

3. **Filter out incomplete tasks** — Excludes tasks with `status == 'done'` or empty `owner` field (same business rules as grouping APIs).

4. **Sort by priority then deal size** — Primary sort: Hi=1, Med=2, Lo=3 (lower is higher priority). Secondary sort: target descending (higher value first). Uses tuple sort key: `(priority_num, -target)`.

5. **Split by owner** — Compares `task.owner.lower()` against `g.user.display_name.lower()` and `g.user.email.lower()` to determine My Tasks vs Team Tasks.

**Rejected approaches:**

- **Join in template** — Would require passing full prospect list to template and doing O(n*m) lookup in Jinja. Doing it in Python is faster and keeps template simple.
- **Separate API call** — Could make template fetch `/crm/api/tasks?enriched=true` but that adds HTTP overhead. Server-side render is simpler for this page.

**Test coverage:**

- Created `app/tests/test_crm_blueprint.py` with 7 tests:
  - Route renders with correct sections
  - Tasks enriched with prospect data (target, size display)
  - My Tasks filters to current user
  - Team Tasks shows other users
  - Sort order correct (priority > size)
  - Done tasks excluded
  - Tasks without owner excluded

**Impact:**
- `app/delivery/crm_blueprint.py` — Rewrote `crm_tasks()` route (lines 1159-1218)
- `app/tests/test_crm_blueprint.py` — NEW FILE (7 tests)
- `app/templates/crm_tasks.html` — No changes (already compatible with enriched data)
- `docs/specs/implemented/SPEC_tasks-page.md` — Spec moved from `docs/specs/`

---


## 2026-03-18 — Tony Excel Sync Revised: Notes via prospect_notes.json, Proper Email Reporting

**Decision:** Updated Tony Excel sync to use `save_prospect_note()` API for all note writes (instead of inline `Notes` field in prospects.md), split new prospect reporting into Case A (existing orgs) vs Case B (new orgs), and changed new prospect stage from `5. Interested` to `3. Outreach`.

**Rationale:** The spec was revised after initial implementation to align with the CRM's notes architecture. Notes stored in `prospect_notes.json` persist across brief refreshes and integrate directly with the briefing system. Inline `**Notes:**` field in prospects.md is legacy and not actively used by the brief synthesizer. Case A vs Case B separation clarifies email reporting — "New Fund II entries for existing orgs" (JPMorgan, UTIMCO, etc.) should never be labeled "New Prospect" since the org already exists in the CRM.

**Key changes:**

1. **Notes handling:** All note writes now call `save_prospect_note(org, offering, author="Tony Avila", text=...)`. The function appends to `prospect_notes.json` with timestamp and author. Deduplication check (case-insensitive, stripped text match) prevents duplicate notes across sync runs.

2. **Email reporting split:** `detect_changes()` now returns `new_prospects_existing_orgs` (Case A) and `new_orgs` (Case B) as separate lists. Email body builder formats them under distinct section headers:
   - "NEW FUND II ENTRIES — EXISTING ORGS (N)" — Org already in CRM; new Fund II prospect record created
   - "NEW ORGS + FUND II ENTRIES (N)" — Brand new to CRM — org and prospect record both created

3. **Stage change:** `NEW_PROSPECT_STAGE = "3. Outreach"` (was `5. Interested`). All new Fund II entries (Case A and Case B) start at Outreach; Oscar manually promotes to higher stages.

4. **Low-confidence queue accumulation:** Added `load_pending_queue()` / `save_pending_queue()` functions. On each sync run, new low-confidence matches (0.60–0.84 confidence) are appended to `crm/tony_sync_pending.json` (deduped by `tony_org` name). This file accumulates entries until manually resolved via a separate Desktop/CoWork workflow (not part of the automated sync).

5. **Removed "UNMATCHED" email section:** The old email format had "UNMATCHED — NOT IN CRM" listing orgs that would be auto-created. This was confusing (they weren't truly unmatched — they were being matched as new). Now folded into "NEW ORGS + FUND II ENTRIES" section with clearer messaging.

**Rejected approaches:**

- **Keep inline Notes field** — Would require duplicating note text into both `prospects.md` and `prospect_notes.json`. Single source of truth (prospect_notes.json) is cleaner.
- **Auto-resolve low-confidence matches** — Would risk incorrect aliases. Manual review via `tony_sync_pending.json` ensures data quality.
- **Combine Case A and Case B in email** — Would lose signal about whether an org is genuinely new to the CRM. Oscar needs to know if "JPMorgan" is a new Fund II entry for a known org vs a truly unknown org appearing for the first time.

**For the next designer:**

- Notes are NEVER written to the inline `**Notes:**` field in `prospects.md` by this sync. All notes go to `prospect_notes.json` via `save_prospect_note()`.
- If Tony's Excel has a note that already exists in `prospect_notes.json` (exact match after strip + lowercase), it will not be re-added.
- The pending queue (`crm/tony_sync_pending.json`) accumulates indefinitely until manually resolved. Check the email for count and resolve when convenient — no urgency.

**Impact:**
- `app/sources/tony_sync.py` — Updated imports, constants, detect_changes(), apply_changes(), build_email_body(), run_sync() (~150 lines changed)
- `crm/tony_sync_pending.json` — NEW FILE (empty array)
- All 89 tests passing (no new tests; sync tested via manual runs)

---

## 2026-03-18 — Meetings Row Click: Reuse Add Modal for Edit Mode

**Decision:** The existing `add-meeting-modal` doubles as the edit modal. Mode is controlled by a `currentEditMeetingId` JS variable (null = add, UUID = edit). No second modal created.

**Rationale:** The spec required exactly this. Reusing the modal avoids duplicating HTML structure and keeping two modals in sync. The mode-switching approach (swapping header text, button text, showing/hiding delete section) is straightforward and keeps the DOM minimal.

**Impact:** `app/templates/crm_meetings.html` only. No backend changes — PATCH and DELETE routes already existed.

---

## 2026-03-18 — Prospect Cell: Conditional Link Rendering

**Decision:** In the meetings table, the Prospect cell renders an `<a>` tag (with `stopPropagation`) only when both `m.org` and `m.offering` are non-empty. When either is absent, a plain `—` text node is rendered instead.

**Rationale:** The old code always rendered an `<a>` (pointing to `#` when no org/offering) and called `event.stopPropagation()` unconditionally. This prevented row clicks on `—` cells from opening the edit modal. The fix: only attach the link and its stopPropagation when there's actually a destination to navigate to.

**Impact:** `renderTable()` in `crm_meetings.html`.

---

## 2026-03-19 — Primary Contact Moved to Org Level (contact file `Primary: true`)

**Decision:** Primary contact is now a property of the organization's contact list, not the prospect record. One contact per org may have `- **Primary:** true` in their `contacts/{slug}.md` file. The `Primary Contact` field is removed from `crm/prospects.md` entirely.

**Rationale:** Primary contacts belong to organizations, not individual fund offerings. An org like "Future Fund" has one primary contact (Julia McArdle) regardless of whether it has one or three prospect records. The old model caused "TBD" to display on the prospect detail page even when the org had known contacts, because the prospect-level field was never kept in sync.

**Key implementation choices:**

1. **`Primary: true` in contact file** — Written as `- **Primary:** true` using the existing `- **Field:** Value` format. `load_person()` parses it and returns `is_primary: bool`. Absent = false; only one contact per org should have it.

2. **Radio behavior enforced in code** — `set_primary_contact(org, name)` clears `Primary: true` from all other contacts for that org before setting it on the target. File constraints do not enforce this (any `.md` file could have the field) — application code is the enforcer.

3. **Backward-compatible `Primary Contact` string in `get_prospect_full()`** — The pipeline template reads `p['Primary Contact']` as a string. Rather than touching the pipeline template, `get_prospect_full()` resolves the primary contact through the org and populates the `Primary Contact` key before returning. This keeps the pipeline working without template changes.

4. **Migration: highest stage wins on conflict** — 4 orgs had disagreeing primary contact names across their prospect records. The contact linked to the highest-stage offering was chosen. Conflicts logged to console during migration.

5. **33 orgs could not be migrated** — Their prospect `Primary Contact` field contained informal descriptions ("TBD", "London office head (name TBD)", email-appended names). These orgs show "—" for primary contact until manually set via the star toggle on the org detail page.

6. **Auto-primary on first contact added** — When `api_org_add_contact()` adds a contact and the org now has exactly 1 contact, that contact is automatically set as primary. No manual star required for new orgs.

**Impact:**
- `app/sources/crm_reader.py` — Fixed `PEOPLE_ROOT = contacts/`; updated `load_person()` for `is_primary`; added `get_primary_contact()`, `set_primary_contact()`, `clear_primary_contact()`, `_set_contact_primary_field()`; removed `Primary Contact` from `PROSPECT_FIELD_ORDER`/`EDITABLE_FIELDS`; removed auto-link trigger from `update_prospect_field()`; updated `get_prospect_full()` to resolve from org
- `app/delivery/crm_blueprint.py` — Added `POST /crm/api/org/<org>/primary-contact`; fixed `people_dir` to `contacts/`; auto-primary logic in `api_org_add_contact()`; removed `'Primary Contact': ''` from new prospect creation
- `app/templates/crm_org_detail.html` — Star toggle on contact cards; `togglePrimary()` JS function
- `app/templates/crm_prospect_detail.html` — `primary_contact_name` from route context replaces prospect-record lookup
- `app/templates/crm_prospect_edit.html` — Primary Contact field and all related JS removed
- `contacts/*.md` — 98 files updated with `- **Primary:** true` (via migration script)
- `crm/prospects.md` — 200 `Primary Contact:` lines removed (via migration script)
- `scripts/migrate_primary_contact_to_org.py` — NEW migration script (idempotent)

---

## 2026-03-19 — Drain Inbox Hardening: Dedup Before Mark-as-Read

**Decision:** `drain_seen_ids.json` is written (message ID recorded) **before** the `mark_as_read` call, not after. The seen-IDs file is also saved once per run (after the full message loop), not per-message.

**Rationale:** The failure mode we're protecting against is: message written to `inbox.md`, but mark-as-read fails (403 or network error), so the message stays unread in the mailbox. On next run, Graph returns it again as unread. Without dedup, it gets appended to `inbox.md` a second time. By recording the ID before calling mark-as-read, we ensure the dedup check catches the message even if the mailbox write fails. A message that was written-but-not-marked is better than a message written twice.

**Rationale for Mail.ReadWrite.Shared scope:** `mark_as_read` and `move_message` in `ms_graph.py` already use the correct `users/{mailbox}/messages/{id}` URL. The 403 was entirely a permission scope issue — the delegated token only had `Mail.Read.Shared`, which covers reads but not writes. Adding `Mail.ReadWrite.Shared` to `DELEGATED_SCOPES` in `graph_auth.py` fixes this. Re-auth (delete `~/.arec_briefing_token_cache.json`) required to pick up new scope.

**Impact:**
- `app/drain_inbox.py` — Added `_load_seen_ids()`, `_save_seen_ids()`, `_prune_seen_ids()`, `_write_last_run()`; updated `drain_inbox()` with dedup logic and last-run write on all exit paths
- `app/auth/graph_auth.py` — Added `Mail.ReadWrite.Shared` to `DELEGATED_SCOPES`
- `.gitignore` — Added `crm/drain_last_run.json` and `crm/drain_seen_ids.json`

---

## 2026-03-19 — Consolidate Org Alias Systems: Aliases Field as Single Source of Truth

**Decision:** Retired `crm/org_aliases.json` as a separate alias store. All org aliases now live exclusively in the `Aliases` field on each org entry in `organizations.md`. `tony_sync.py` now calls `crm_reader.get_org_aliases_map()` instead of its own `load_aliases()` function.

**Rationale:** Two parallel alias systems caused silent divergence — aliases added via the CRM UI didn't help Tony sync matching, and aliases added to the JSON file didn't appear in search or briefs. Consolidating onto the `Aliases` field (which `crm_reader.py` already parsed correctly) eliminates the split, ensures all CRM features see the same aliases, and removes a maintenance burden.

**Impact:**
- `crm/org_aliases.json` — **Deleted**
- `crm/organizations.md` — 7 orgs updated with new/additional Aliases entries
- `app/sources/tony_sync.py` — Removed `ALIASES_PATH`, `load_aliases()`. Now imports `get_org_aliases_map` from `crm_reader`. Diff report text updated to reference CRM UI instead of JSON file.

---


## 2026-03-19 — Pipeline Type Column: Pull from Org, Not Prospect

**Decision:** The `/api/prospects` endpoint now enriches each prospect with the `Type` field from its linked org before returning JSON. The Type filter on the pipeline (`?type=...`) now filters prospects correctly by org Type.

**Rationale:** Type is an org-level attribute stored in `organizations.md`, not a prospect-level field. The pipeline's Type column was empty because the API never looked up the org's Type when building the response. The `/api/export` endpoint already did this correctly; applying the same pattern to `/api/prospects` fixes the column.

**Implementation:**
1. Load organizations dict once at the start of the request (`orgs = {o['name']: o for o in load_organizations()}`)
2. Apply type filter from query params before enriching prospects (same pattern as `/api/export`)
3. Inject `Type` field from org record onto each prospect in the tasks loop (empty string for orgs without Type or prospects without org)

**Impact:**
- `app/delivery/crm_blueprint.py` — `api_prospects()` function (8 lines added)
- Pipeline Type column now displays correctly
- Type filter dropdown on pipeline now works
- No changes to stored data (read-path enrichment only)

---

## 2026-03-19 — Meeting Deduplication: Three-Tier Strategy with Any-Status Matching

**Decision:** Fixed three gaps in the meeting deduplication system: (1) `save_meeting()` Tier 2 dedup now works regardless of meeting status (removed `status='scheduled'` gate), (2) added read-time dedup safety net in `load_meetings()` that auto-cleans the JSON file when duplicates exist, (3) verified Tony's calendar scanner already implements org+date fallback dedup with `graph_event_id` backfill.

**Rationale:** The original Tier 2 dedup logic only matched meetings with `status='scheduled'`. Once a meeting transitioned to `completed`, a second insert from a different source (e.g., manual entry after a calendar scan) bypassed dedup and created a duplicate. Additionally, there was no safety net at read time — if a duplicate sneaked in through any code path, it would show forever in the UI.

**Key implementation choices:**

1. **Status-agnostic fuzzy matching** — Tier 2 dedup now matches meetings with the same org (case-insensitive, trimmed) AND meeting_date ±1 day, regardless of current status. This catches cross-source duplicates even after status transitions.

2. **Backfill-only merge behavior** — When Tier 2 finds a match, it only updates empty fields on the existing meeting. Never overwrites `notes_raw`, `title`, `attendees`, `transcript_url`, or `graph_event_id` if they already have values. This preserves data regardless of which source wrote first.

3. **Read-time dedup safety net** — `load_meetings()` now includes a dedup pass before filter logic. Groups meetings by `(org.lower().strip(), meeting_date)`, keeps the first occurrence, merges `graph_event_id`, `notes_raw`, and `notes_summary` from duplicates into the keeper, then auto-saves the cleaned list back to `meetings.json`.

4. **Tony's scanner already correct** — `tony_calendar_scan.py` lines 368-386 implement the org+date fallback dedup after the `graph_event_id` check. If a meeting already exists with the same org and date (from any source), the scanner skips creating a new record and backfills the `graph_event_id` if missing.

**Rejected alternatives:**
- **Delete duplicates without merging** — Would lose `graph_event_id` or notes from the duplicate record. Merging useful fields preserves all data.
- **Leave read-time dedup out** — Would require all write paths to be perfect. The safety net ensures duplicates never persist in the UI even if a bug sneaks through.

**For the next designer:**
- If you see duplicate meetings in the UI, they will auto-clean on the next page load (next `load_meetings()` call).
- The `graph_event_id` backfill is opportunistic — if Tony's scanner sees a meeting that was manually created (no `graph_event_id`), it will add the ID on next scan. This connects manual entries to the calendar source for future updates.

**Impact:**
- `app/sources/crm_reader.py` — Updated `save_meeting()` docstring and Tier 2 dedup block (~35 lines); added dedup safety net in `load_meetings()` (~25 lines)
- `tools/tony_calendar_scan.py` — Already correct (no changes needed)
- All 67 existing tests passing

---

## 2026-03-19 — Remove Deep Scan Button: Cowork Skill Replaces Per-Prospect Scanning

**Decision:** Removed the "Deep Scan (90d)" button from the prospect detail page. Email scanning is now exclusively handled by the `/email-scan` Cowork skill, which performs a 6-pass scan across all mailboxes in a single run.

**Rationale:** The per-prospect scan button called `api_prospect_email_scan()` in `crm_blueprint.py`, which invoked `search_emails_deep()` in `ms_graph.py` and summarized each email with Haiku (per-email Claude API cost). The Cowork skill replaced this with a comprehensive scan that covers all orgs at once. Keeping both created confusion about which mechanism was authoritative and wasted API credits on single-org scans.

**Impact:**
- `app/templates/crm_prospect_detail.html` — Removed `.btn-scan` CSS, button HTML, `runDeepEmailScan()` JS function. `.scan-status` CSS kept (used by header "Scan Email" button).
- `app/delivery/crm_blueprint.py` — Removed `api_prospect_email_scan()` route (~200 lines)
- `app/sources/ms_graph.py` — Removed `search_emails_deep()` function (~105 lines)
- Route `/crm/api/prospect/{offering}/{org}/email-scan` now returns 404

---

## 2026-03-19 — Prospect/Org Page Redesign: Context-Dependent Color Coding

**Decision:** Updated prospect detail and org edit pages to use context-dependent color coding: green left-border for native/editable sections, blue right-border for cross-reference/read-only sections. Removed Edit Prospect, Edit Org, and Scan Email buttons from prospect header. Standardized button styling across both pages.

**Rationale:** The previous implementation used entity-type coloring (blue=prospect, green=org) which was confusing because it didn't communicate whether data was editable. The spec required context-dependent coloring where the same data element could be green on one page (native) and blue on another (cross-reference). This makes ownership boundaries immediately clear: "green left = you're in the right place to edit", "blue right = this lives somewhere else."

**Key implementation choices:**

1. **Context-dependent CSS classes** — `.card-native` (green left-border), `.card-crossref` (blue right-border). Applied based on which page you're viewing, not the data type. Org Info Card is blue (cross-ref) on prospect page but would be green if it existed on org page as a top card.

2. **Cross-reference badges updated** — Changed from `.card-badge-org` / `.card-badge-prospect` to unified `.crossref-badge` class with blue dot indicator. Always points to the owning page.

3. **Header simplification** — Removed three buttons from prospect detail header (Edit Prospect, Edit Org, Scan Email). Prospect fields are inline-editable, org editing happens on org page via cross-reference badge.

4. **Button standardization** — `.btn-add-note` class added to CSS with consistent blue styling. Applied to both prospect and org note forms (was white/outlined on org page before).

5. **Notes field removed from org card** — Org Notes moved to standalone Notes Log card lower on page, matching the prospect page pattern.

6. **Brief renamed** — "Relationship Brief" → "Org Brief" on org edit page for clarity.

**Rejected alternatives:**

- **Entity-type coloring** — Would have required users to remember "blue=prospect, green=org" mapping. Context-dependent coloring is more intuitive.
- **Keep header buttons** — Would add visual clutter when fields are already inline-editable.
- **Three-tier coloring** — Would add cognitive load. Two colors (native vs cross-ref) is sufficient.

**For the next designer:**

- Color classes are template-only — no backend logic depends on them.
- The "From Org →" and "View Prospect →" badges are functional links, not just indicators.
- All cross-reference sections are read-only by design — users must navigate to the owning page to edit.

**Impact:**
- `app/static/crm.css` — Replaced `.card-prospect`/`.card-org` with `.card-native`/`.card-crossref`, added `.crossref-badge`, standardized `.btn-add-note`
- `app/templates/crm_prospect_detail.html` — Updated all card classes, removed three header buttons, updated all badge classes to `.crossref-badge`
- `app/templates/crm_org_edit.html` — Updated all card classes, removed Notes from org card, updated Add Note button class, renamed brief to "Org Brief"
- All 67 tests passing

---

## 2026-03-19 — Primary Contact Field Persistence: Added to PROSPECT_FIELD_ORDER

**Decision:** Added `"Primary Contact"` to `PROSPECT_FIELD_ORDER` in `crm_reader.py` between `"Assigned To"` and `"Notes"`. The field now persists through write/read round trips.

**Rationale:** `update_prospect_field('Primary Contact', ...)` appeared to succeed but the value was silently dropped by `write_prospect()` because the field was not in the serialization list. Different prospects for the same org can have different primary contacts (e.g., UTIMCO has two prospects with different primary contacts), so this prospect-level override mechanism needs to work alongside the org-level primary contact system.

**Impact:**
- `app/sources/crm_reader.py` — Added `"Primary Contact"` to `PROSPECT_FIELD_ORDER` list (line 26)
- Enables batch enrichment script `scripts/batch_primary_contact.py` to populate primary contacts across all prospects
- Supports dual-model architecture: orgs have org-level primary contact (star toggle), prospects can optionally override with prospect-level primary contact

---
