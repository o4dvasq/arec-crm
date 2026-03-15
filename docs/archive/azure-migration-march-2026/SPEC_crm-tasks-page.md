SPEC: CRM Tasks Page
Project: arec-crm | Branch: markdown-local | Date: 2026-03-15
Status: Ready for implementation

SEQUENCING: Implement AFTER SPEC_crm-markdown-cleanup.md is complete.
DEPENDS ON: Clean markdown-local branch with no Postgres dead code.
BACKEND: All data via crm_reader.py and memory_reader.py — NO crm_db.py, NO models.py, NO SQLAlchemy.

---

## 1. Objective

The "Tasks" nav link currently points to `/tasks`, which renders the Overwatch task board from TASKS.md. CRM prospect tasks (org-tagged items in TASKS.md + entries in `crm/prospect_notes.json`) are scattered and not surfaced in one place. Create a `/crm/tasks` page that shows all CRM-relevant tasks and update the nav to point there.

## 2. Scope

### In Scope
1. New route `GET /crm/tasks` in `crm_blueprint.py` that renders a tasks page
2. New template `app/templates/crm_tasks.html` — lists all CRM tasks grouped by org
3. Update `_nav.html` to point Tasks link to `/crm/tasks` instead of `/tasks`
4. Task actions from the page: complete, add new
5. Filter/sort by owner, priority, org

### Out of Scope
- The old `/tasks` Overwatch page — leave as-is (will move to Overwatch repo later)
- Changes to `crm_reader.py` task functions (unless needed)
- New data files or schema changes

## 3. Business Rules

- CRM tasks come from two sources:
  1. Org-tagged tasks in TASKS.md: lines containing `(OrgName)` parsed by `crm_reader.load_tasks_by_org()`
  2. Prospect tasks extracted from notes by `extract_tasks_from_notes()` in `brief_synthesizer.py`
- "My Tasks" = tasks where `assigned:Oscar` or no assignee (default to Oscar)
- "Team Tasks" = all other assigned tasks
- Task creation writes to TASKS.md via `memory_reader.append_task_to_section()`
- Task completion updates TASKS.md via `memory_reader.update_task_status()`

## 4. Data Model / Schema Changes

None. All data is in TASKS.md (parsed by memory_reader.py) and crm/prospect_notes.json.

## 5. Implementation

### Route in crm_blueprint.py
```python
@crm_bp.route('/tasks')
def crm_tasks():
    config = load_crm_config()
    return render_template('crm_tasks.html', config=config)
```

Page loads data via AJAX from existing API endpoints.

### Data loading (AJAX)
- `GET /tasks/api/tasks` — returns all tasks grouped by section (existing endpoint in tasks_blueprint.py)
- Client-side: filter to tasks containing `(OrgName)` pattern — these are CRM tasks
- Group by org name, then by owner

### Template: crm_tasks.html
- Use standard `_nav.html` with `{% set active_tab = 'tasks' %}`
- Two-column layout:
  - Left: "MY TASKS" (owner = Oscar or unassigned)
  - Right: "TEAM TASKS" (all other owners)
- Each task card: org name (link to `/crm/org/ORG`), task text, owner, priority badge
- "+ Add Task" button opens inline form with fields: org (dropdown from `/crm/api/orgs`), text, owner, priority
- Complete button (checkmark) on each task

### Nav update in _nav.html
```html
<a href="/crm/tasks" class="nav-tab {% if active_tab == 'tasks' %}nav-tab--active{% endif %}">Tasks</a>
```

### Dashboard link update
Change `/tasks` link in dashboard.html to `/crm/tasks`.

## 6. Constraints

- Use `crm_reader.py` and `memory_reader.py` for all data access — NO database imports
- No new JS libraries — vanilla JS only
- Match existing dark theme CRM styling
- Priority badges: Hi = red, Med = amber, Low = gray

## 7. Acceptance Criteria

1. Clicking "Tasks" in nav goes to `/crm/tasks`
2. Page shows all org-tagged tasks from TASKS.md grouped into My Tasks / Team Tasks
3. Each task shows org name, task text, owner, priority badge
4. Org name links to org detail page
5. Completing a task updates TASKS.md
6. Adding a task via form creates it in TASKS.md with org tag
7. Nav says "AREC CRM" (already updated in rebrand commit)
8. `python3 -m pytest app/tests/ -v` passes

## 8. Files Likely Touched

| File | Action |
|------|--------|
| `app/delivery/crm_blueprint.py` | Add `GET /crm/tasks` route |
| `app/templates/crm_tasks.html` | Create — new tasks page (NOTE: template shell already exists from rebrand cherry-pick, extend it) |
| `app/templates/_nav.html` | Change `/tasks` → `/crm/tasks` |
| `app/templates/dashboard.html` | Change `/tasks` link to `/crm/tasks` |
