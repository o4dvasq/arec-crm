# SPEC: Tasks Screen Overhaul
**Project:** arec-crm | **Date:** 2026-03-17 | **Status:** Ready for implementation

---

## 1. Objective

Redesign the CRM Tasks page to enforce that every task is tied to exactly one prospect and one owner. Remove all non-prospect task concepts from the CRM (personal/ops tasks live exclusively in Overwatch). Replace the single flat list with two sub-tab views of the same data: **By Prospect** (default) and **By Owner**, both grouped by descending prospect target commitment amount.

---

## 2. Scope

**In scope:**

- Enforce `[org:]` and `[owner:]` tags as required on all CRM tasks written to `TASKS.md`
- Remove "Fundraising - Me" section concept and any category-derived labels from the UI
- New sub-tab navigation: "By Prospect" | "By Owner" under the Tasks top-level nav tab
- Grouped card layout in both views, sorted by prospect `target` descending
- Orphan task audit: a one-time script that flags tasks missing `[org:]` or `[owner:]` tags
- "+ Add" button on each group header, pre-filling owner or prospect from context
- Update task card subtitle to show contextual info per view

**Out of scope:**

- Overwatch task management (separate project)
- Task creation from other pages (prospect detail, pipeline)
- Bulk task operations
- Task due dates (not currently in the model)

---

## 3. Business Rules

1. Every CRM task MUST have exactly one `[org: OrgName]` tag and one `[owner: Name]` tag in `TASKS.md`. Both are required on create.
2. The concept of task `section` / `category` (e.g., "Fundraising - Me") is removed from the UI. All CRM tasks are prospect-related by definition. `TASKS.md` sections still exist structurally for Overwatch compatibility, but the Tasks UI ignores the section label.
3. **By Prospect view (default):** Tasks grouped under prospect name headers. Groups sorted by prospect `target` amount descending (largest commitment first). Within each group, tasks sorted by priority (Hi → Med → Lo), then by order of appearance in `TASKS.md`.
4. **By Owner view:** Tasks grouped under owner display name headers. Groups sorted by the largest `target` among that owner's assigned prospects, descending. Within each group, tasks sorted by priority, then order of appearance.
5. The "+ Add" button appears on each group header. In By Prospect view, it pre-fills the prospect. In By Owner view, it pre-fills the owner. The user fills in the remaining field.
6. Task card subtitle varies by view:
   - **By Prospect view:** shows owner name (since the prospect is the group header)
   - **By Owner view:** shows prospect name (since the owner is the group header)
7. The priority badge (Hi/Med/Lo), task title, and action icons (reorder, email, edit, delete) remain unchanged from current implementation.
8. Sub-tab selection persists in the URL query string (`?view=prospect` or `?view=owner`) so it survives page refresh and is shareable.

---

## 4. Data Model

### 4.1 Task storage — TASKS.md

Tasks are stored as markdown checklist lines in `TASKS.md`. CRM tasks use the `[org:]` and `[owner:]` tag format, parsed by `_parse_org_tagged_task()` in `crm_reader.py`.

**Required task line format:**

```
- [ ] **[Med]** Task description text [org: Merseyside Pension Fund] [owner: Oscar]
```

Fields:
- `**[Hi]**` / `**[Med]**` / `**[Lo]**` — priority badge (required)
- Task description — free text before the tags
- `[org: OrgName]` — links the task to a CRM org/prospect (required for CRM tasks)
- `[owner: Name]` — the person responsible (required for CRM tasks)

**No schema migration is needed.** `crm_reader.py` already reads and writes this format via `add_prospect_task()`, `get_tasks_for_prospect()`, and `complete_prospect_task()`.

### 4.2 Orphan task audit: `scripts/audit_orphan_tasks.py`

A one-time read-only script to surface existing tasks that are missing `[org:]` or `[owner:]` tags before the new UI is deployed.

Behavior:

1. Parse `TASKS.md`, scanning all open tasks across all sections except "Personal" and "Done".
2. Flag any task line that is missing an `[org:]` tag OR an `[owner:]` tag.
3. Write a report to `docs/orphan_tasks_report.md` with columns: line number, task text, missing field(s).
4. Print summary to stdout: `"X tasks flagged — review docs/orphan_tasks_report.md before deploying"`
5. Exit without modifying `TASKS.md`.

The script is idempotent — safe to run multiple times. Oscar reviews the report and manually adds the missing tags before the new UI goes live.

### 4.3 `crm_reader.py` additions

**New function: `get_all_prospect_tasks() -> list[dict]`**

Returns all open CRM tasks that have both `[org:]` and `[owner:]` tags, enriched with prospect `target` for sorting. Each dict:

```python
{
    'text': str,          # task description
    'org': str,           # from [org:] tag
    'owner': str,         # from [owner:] tag
    'priority': str,      # 'Hi' | 'Med' | 'Lo'
    'target': float,      # prospect target in $M, 0.0 if not found
    'status': 'open',
}
```

Logic: call `_parse_org_tagged_task()` for all open task lines, then for each `org`, look up `target` from `load_prospects()`. If no matching prospect found, `target = 0.0`.

**New function: `get_tasks_grouped_by_prospect() -> list[dict]`**

Groups output of `get_all_prospect_tasks()` by `org`, sorted by `target` descending. Returns:

```python
[
    {
        'org': 'NPS (Korea SWF)',
        'target': 300.0,
        'tasks': [...]   # sorted Hi → Med → Lo
    },
    ...
]
```

**New function: `get_tasks_grouped_by_owner() -> list[dict]`**

Groups output of `get_all_prospect_tasks()` by `owner`, sorted by the maximum `target` across that owner's tasks. Returns:

```python
[
    {
        'owner': 'Oscar',
        'max_target': 300.0,
        'tasks': [...]   # sorted Hi → Med → Lo
    },
    ...
]
```

### 4.4 Task creation enforcement

`add_prospect_task()` already requires `org_name` and `owner`. The API route (`POST /crm/api/tasks`) must return a 400 error if either field is missing or empty. This enforces the constraint at the API layer without any schema change.

---

## 5. UI / Interface

### 5.1 Sub-tab bar

Directly below the main nav "Tasks" tab, render a secondary tab bar:

```
[ By Prospect ]  [ By Owner ]
```

- Styled as pill-shaped toggles or underline tabs (match existing CRM nav aesthetic)
- Active tab visually distinguished (filled/underlined)
- "By Prospect" is the default when no `?view=` param present
- Clicking a tab updates `?view=` query param without full page reload (JS `history.pushState`)

### 5.2 By Prospect view

```
┌─────────────────────────────────────────────────┐
│  NPS (Korea SWF)                    [+ Add]     │  ← Group header (prospect name)
├─────────────────────────────────────────────────┤
│  Hi   Schedule follow-up call with...           │
│       Zach Reisner                              │  ← Subtitle: owner name
├─────────────────────────────────────────────────┤
│  Med  Prepare co-investment memo                │
│       Oscar Vasquez                             │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  Merseyside Pension Fund            [+ Add]     │
├─────────────────────────────────────────────────┤
│  Med  Send updated deck to Trent K.             │
│       James Walton                              │
└─────────────────────────────────────────────────┘
```

Groups ordered by prospect `target` descending. Prospects with no open tasks are not shown.

### 5.3 By Owner view

```
┌─────────────────────────────────────────────────┐
│  MAX                                [+ Add]     │  ← Group header (owner display name)
├─────────────────────────────────────────────────┤
│  Hi   Schedule follow-up call with...           │
│       NPS (Korea SWF)                           │  ← Subtitle: prospect name
├─────────────────────────────────────────────────┤
│  Med  Follow up with Martin Ash                 │
│       Plurimi                                   │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  IAN                                [+ Add]     │
├─────────────────────────────────────────────────┤
│  Med  Follow up with Matt Sopp                  │
│       Steyn Group                               │
└─────────────────────────────────────────────────┘
```

Groups ordered by the largest prospect `target` among that owner's tasks, descending. Owners with no open tasks are not shown.

### 5.4 Add Task (from group header "+ Add")

Clicking "+ Add" opens the existing add-task UI (modal or inline form) with one field pre-filled:

- **By Prospect view:** prospect is pre-filled, user selects owner + enters title/priority
- **By Owner view:** owner is pre-filled, user selects prospect + enters title/priority

### 5.5 Task card actions

Unchanged from current: hover reveals reorder (↕), email (✉), edit (✏), delete (🗑) icons. All behave as they do today.

---

## 6. Integration Points

- **Overwatch API key auth:** Task API routes (`@require_api_key_or_login`) remain unchanged. Overwatch can still read/write tasks via API key. The required-field enforcement (missing `org` or `owner` → 400) applies to API-created tasks as well.
- **Prospect detail page:** The tasks panel on prospect detail continues to work. It implicitly has `org` from context — no changes needed there beyond removing any category display.
- **Pipeline table:** If the pipeline shows a task count badge, it continues to work — `get_tasks_for_prospect(org)` is unchanged.

---

## 7. Constraints

- Surgical change only — do not reorganize task-related code beyond what's needed for this spec.
- No new libraries. Sub-tab switching is vanilla JS.
- The audit script MUST NOT auto-delete or auto-assign orphan tasks. It only reports.
- `crm_reader.py` grouping functions load tasks + prospects into memory and group in Python — no new file formats, no pre-computation.
- All existing task API key tests (`test_tasks_api_key.py`) must continue to pass. Add new tests for missing-field enforcement.

---

## 8. Acceptance Criteria

1. `scripts/audit_orphan_tasks.py` generates `docs/orphan_tasks_report.md` listing tasks without `[org:]` or `[owner:]` tags
2. `POST /crm/api/tasks` returns 400 if `org` or `owner` is missing/empty
3. Tasks page shows two sub-tabs: "By Prospect" (default) and "By Owner"
4. By Prospect view groups tasks under prospect names, sorted by target descending
5. By Owner view groups tasks under owner names, sorted by largest prospect target descending
6. Task card subtitle shows owner name (By Prospect view) or prospect name (By Owner view)
7. "+ Add" on group header pre-fills prospect (By Prospect) or owner (By Owner)
8. No "Fundraising - Me" or category labels appear anywhere in the Tasks UI
9. `?view=prospect` and `?view=owner` query params control active tab and survive refresh
10. All existing tests pass; new tests cover missing-field enforcement and both view grouping functions
11. Feedback loop prompt has been run

---

## 9. Files Likely Touched

| File | Change |
|------|--------|
| `app/sources/crm_reader.py` | Add `get_all_prospect_tasks()`, `get_tasks_grouped_by_prospect()`, `get_tasks_grouped_by_owner()` |
| `app/delivery/crm_blueprint.py` | Update `/crm/tasks` route to accept `?view=` param; pass grouped data to template; enforce required fields on task create |
| `app/templates/crm_tasks.html` | Full rewrite: sub-tab bar, grouped card layout, view-dependent subtitles, pre-fill "+ Add" |
| `app/static/crm.js` | Sub-tab switching via `history.pushState`, "+ Add" pre-fill logic |
| `app/static/crm.css` | Sub-tab styles (if not already covered by existing nav patterns) |
| `scripts/audit_orphan_tasks.py` | New: one-time orphan task report |
| `app/tests/test_tasks_api_key.py` | Update: ensure task create rejects missing `org` or `owner` |
