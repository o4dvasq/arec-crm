# SPEC: Tasks Page

**Project:** arec-crm
**Date:** 2026-03-12
**Status:** Ready for implementation
**Priority:** Low (UI polish batch)
**Parallel group:** Can run simultaneously with Nav Redesign, Pipeline Polish, Prospect Detail, Contact Enrichment specs

---

## 1. Objective

Create a dedicated Tasks page/view at `/crm/tasks` that shows the current user's tasks on top (sorted by priority, then descending expected deal size within each priority), followed by team tasks below. Include a search bar to filter tasks by prospect name.

## 2. Scope

**In scope:**
- New template: `crm_tasks.html`
- New route: `GET /crm/tasks`
- "My Tasks" section: tasks assigned to the logged-in user, sorted by priority (High → Medium → Low), then by expected deal size (descending) within each priority
- "Team Tasks" section: tasks assigned to everyone else, same sort order
- Search bar filtering tasks by prospect name (client-side JS filter)
- Each task row shows: task description, prospect name (linked), priority badge, expected deal size, assignee, due date, status
- Clicking a task row opens task detail/edit (inline or modal)

**Out of scope:**
- Task CRUD (create/update/delete) — existing API endpoints handle this
- Changes to the nav bar (see SPEC_nav-redesign.md — it adds the "Tasks" tab)
- Changes to how tasks are stored in the database

## 3. Business Rules

- "My Tasks" = tasks where `assigned_to` matches `g.user.display_name` or `g.user.email`. Use case-insensitive matching.
- "Team Tasks" = all other open/active tasks (assigned to other users or unassigned).
- Sort order within each section: Primary sort by priority (High first, then Medium, then Low/None). Secondary sort by the prospect's expected deal size (`target` field), descending (largest deals first).
- Only show open/active tasks (not completed ones). Provide a toggle to show completed tasks if desired.
- The search bar filters both sections simultaneously by prospect/org name.
- Expected deal size comes from the prospect record's `target` field (stored as BIGINT cents). Display formatted (e.g., `$50M`).

## 4. Data Model / Schema Changes

None. Uses existing `prospect_tasks` table and `prospects` table.

## 5. UI / Interface

### Page Layout
```
[Search bar: "Search by prospect..."]

MY TASKS (count)
┌─────────────────────────────────────────────────────────┐
│ Priority │ Task          │ Prospect    │ Size  │ Due    │
│ HIGH     │ Send term sh… │ Acme Corp   │ $50M  │ Mar 15 │
│ HIGH     │ Follow up on… │ Beta LLC    │ $25M  │ Mar 18 │
│ MEDIUM   │ Schedule call │ Gamma Inc   │ $100M │ Mar 20 │
└─────────────────────────────────────────────────────────┘

TEAM TASKS (count)
┌─────────────────────────────────────────────────────────┐
│ Priority │ Task          │ Prospect    │ Size  │ Assignee │ Due │
│ HIGH     │ Review docs   │ Delta Fund  │ $75M  │ TV       │ Mar 14 │
└─────────────────────────────────────────────────────────┘
```

### Column Definitions

| Column | Source | Notes |
|--------|--------|-------|
| Priority | `prospect_tasks.priority` | Badge with color: High=red, Medium=blue, Low=green |
| Task | `prospect_tasks.description` | Clickable — opens edit modal. Strip markdown. |
| Prospect | `prospects.org` | Linked to prospect detail page |
| Size | `prospects.target` | Formatted with `_format_currency()`. Right-aligned. |
| Due | `prospect_tasks.due_date` | Date formatted. Highlight overdue in red. |
| Assignee | `prospect_tasks.assigned_to` | Shown in Team Tasks section. Initials format. |

### Search Bar
- Positioned at the top of the page, full width of the content area
- Filters both My Tasks and Team Tasks tables
- Client-side filtering (no server round-trip)
- Searches against prospect/org name

### Task Row Click
Clicking a task row should open a task edit modal (same pattern as prospect detail page).

### Empty States
- "My Tasks" empty: "No tasks assigned to you. Tasks can be created from prospect detail pages."
- "Team Tasks" empty: "No team tasks found."

## 6. Integration Points

- **Data:** Calls `get_all_prospect_tasks()` from `crm_db.py` to get all open tasks
- **Prospect data:** Joins with prospect records to get `org`, `offering`, `target` (expected size)
- **User identity:** `g.user.display_name` or `g.user.email` to split My Tasks vs Team Tasks
- **Navigation:** Linked from nav bar "Tasks" tab (added by SPEC_nav-redesign.md)
- **Task edit:** Uses existing `/crm/api/tasks/<id>` endpoints

## 7. Constraints

- Route must include `@login_required` decorator.
- Template follows the same dark theme pattern as other CRM pages (use CSS variables from `crm.css`).
- Include `{% include '_nav.html' %}` with `active_tab = 'tasks'`.
- Deal sizes displayed as formatted currency, right-aligned in the table.
- Priority sort order must be deterministic: High=1, Medium=2, Low=3, None=4.
- Page should load fast — one query for all tasks + one for prospect data, joined server-side before sending to template.

## 8. Acceptance Criteria

- [ ] `/crm/tasks` route exists and renders the tasks page
- [ ] "My Tasks" section shows tasks assigned to the logged-in user
- [ ] "Team Tasks" section shows tasks assigned to others
- [ ] Tasks sorted by priority (High → Low), then by expected deal size (descending) within each priority
- [ ] Expected deal size column is right-aligned and properly formatted (e.g., `$50M`)
- [ ] Search bar filters tasks by prospect name across both sections
- [ ] Clicking a task opens an edit view
- [ ] Prospect names link to the prospect detail page
- [ ] Page uses dark theme consistent with other CRM pages
- [ ] "Tasks" tab in nav bar links to this page (if nav redesign spec has been implemented)
- [ ] All 99+ tests pass (add at least 1 test for the new route)
- [ ] Feedback loop prompt has been run

## 9. Files Likely Touched

| File | Reason |
|------|--------|
| `app/templates/crm_tasks.html` | **New file** — Tasks page template |
| `app/delivery/crm_blueprint.py` | New route: `GET /crm/tasks` with task aggregation logic |
| `app/sources/crm_db.py` | May need a function that returns tasks joined with prospect data (org, offering, target). Or use existing `get_all_prospect_tasks()` + prospect lookup. |
| `app/tests/test_crm_db.py` | Add test for the tasks route |
