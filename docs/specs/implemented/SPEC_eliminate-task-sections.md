SPEC: Eliminate Task Sections | Project: arec-crm | Date: 2026-03-20 | Status: Ready for implementation

---

## 1. Objective

Remove the "section" concept from the task system entirely. Tasks have three meaningful attributes: **owner** (assigned_to), **prospect/org**, and **priority**. Sections ("Fundraising - Me", "Fundraising - Others", "Other Work", "Personal", "IR / Fundraising") are a legacy holdover that adds unnecessary complexity to data storage, API routing, and frontend code. The UI already groups by owner — sections serve no user-facing purpose.

## 2. Scope

### In Scope

- Flatten TASKS.md to a single list (no `## Section` headers, except `## Done` for completed tasks)
- Merge "IR / Fundraising" bracket-format tasks (`[org:] [owner:]`) into the standard `(OrgName) — assigned:Name` format
- Replace `/<section>/<index>` API routing with a line-based or sequential index
- Remove section dropdown from the add-task form
- Remove section label from task card metadata
- Remove `TASK_SECTIONS` constant and all section validation
- Update all CRUD routes, JS, and the edit modal

- Add click-to-edit on the CRM tasks page (`/crm/tasks` — crm_tasks.html): include task-edit-modal.js/CSS, wire click handlers on `.task-item` elements, pass flat task index to each rendered task so the modal can call the correct API routes

### Out of Scope

- Task priority/status/owner logic (unchanged)
- The `## Done` section — keep it as a separator for completed tasks

## 3. Business Rules

- **Single task list**: TASKS.md has two sections only: an implicit "open" section at the top (no header needed) and `## Done` at the bottom. All open tasks live in one flat list.
- **Task identity**: Each task is identified by its 0-based index among all open tasks (line position in the file, excluding blanks and the Done section). This replaces the current `section/index` compound key.
- **Bracket format elimination**: All `[org: OrgName] [owner: Name]` tasks are converted to `(OrgName) — assigned:Name` format. The `_parse_org_tagged_task()` parser remains for backward compatibility but `add_prospect_task()` writes in the standard format.
- **No default section**: `add_prospect_task()` appends to the open task list (before `## Done`), not to a named section.
- **Card metadata**: Each task card shows org name only (linked to prospect detail). No section label.
- **Add form**: The section dropdown is removed. New tasks are appended to the top of the open list.

## 4. Data Model / Schema Changes

### TASKS.md — Before

```markdown
# Tasks

## Fundraising - Me
- [ ] **[Hi]** Task A (OrgX) — assigned:Oscar
- [ ] **[Med]** Task B (OrgY) — assigned:Tony

## Fundraising - Others
- [ ] **[Hi]** Task C (OrgZ) — assigned:Zach

## Other Work
- [ ] **[Med]** Task D — assigned:Oscar

## IR / Fundraising
- [ ] **[High]** Task E — [org: OrgW] [owner: Oscar]

## Done
- [x] **[Med]** Task F — assigned:Oscar — completed 2026-03-11
```

### TASKS.md — After

```markdown
# Tasks

- [ ] **[Hi]** Task A (OrgX) — assigned:Oscar
- [ ] **[Med]** Task B (OrgY) — assigned:Tony
- [ ] **[Hi]** Task C (OrgZ) — assigned:Zach
- [ ] **[Med]** Task D — assigned:Oscar
- [ ] **[High]** Task E (OrgW) — assigned:Oscar

## Done
- [x] **[Med]** Task F — assigned:Oscar — completed 2026-03-11
```

## 5. UI / Interface

### Task Board (`/tasks`)

- No changes to owner-grouped Kanban layout
- Remove section label from card meta line (currently shows "Fundraising - Me" etc. after org)
- Remove section `<select>` from the inline add-task form
- Task edit modal: remove section from save payload (no longer sent to API)

### Task Edit Modal (`task-edit-modal.js`)

- Drop internal `_section` state variable
- Save/delete API calls use index-only URL: `/tasks/api/task/<index>` instead of `/tasks/api/task/<section>/<index>`

### CRM Tasks Page (`/crm/tasks` — crm_tasks.html)

- Include `task-edit-modal.css` and `task-edit-modal.js`
- Set `window.TASK_MODAL_TEAM`, `TASK_MODAL_TEAM_MAP`, `TASK_MODAL_PROSPECT_ORGS` (same pattern as tasks.html and pipeline)
- Each `.task-item` rendered by Jinja must include `data-index="{{ task.flat_index }}"` — the 0-based flat index among all open tasks
- Add CSS `cursor: pointer` on `.task-body`
- Add JS click handler: clicking `.task-body` (but not `.btn-complete` or org links) opens `openTaskEditModal()` with the task's data
- The `crm_tasks()` route in crm_blueprint.py must compute and attach `flat_index` to each task before passing to the template. This requires calling the same flat-index logic used by `_load_tasks_full()` or cross-referencing task text+org against the flat list.

## 6. Integration Points

### API Route Changes

| Current Route | New Route | Notes |
|---|---|---|
| `GET /tasks/api/tasks` | `GET /tasks/api/tasks` | Returns flat array instead of `{section: [tasks]}` dict |
| `POST /tasks/api/task` | `POST /tasks/api/task` | Drop `section` from request body |
| `PUT /tasks/api/task/<section>/<index>` | `PUT /tasks/api/task/<index>` | Drop section from URL and body |
| `DELETE /tasks/api/task/<section>/<index>` | `DELETE /tasks/api/task/<index>` | Drop section from URL |
| `POST …/<section>/<index>/complete` | `POST /tasks/api/task/<index>/complete` | Drop section from URL |
| `POST …/<section>/<index>/restore` | `POST /tasks/api/task/<index>/restore` | Drop section from URL |
| `PATCH …/<section>/<index>/status` | `PATCH /tasks/api/task/<index>/status` | Drop section from URL |
| `PATCH …/<section>/<index>/priority` | `PATCH /tasks/api/task/<index>/priority` | Drop section from URL |

### Response format change for `GET /tasks/api/tasks`

**Before:** `{ "Fundraising - Me": [{...}, ...], "Fundraising - Others": [...], ... }`

**After:** `{ "open": [{...}, ...], "done": [{...}, ...] }`

Each task object keeps its existing fields (`text`, `priority`, `status`, `context`, `assigned_to`, `org`, `complete`, `completion_date`, `index`) but drops `section`.

### Downstream consumers to update

- `crm_reader.py`: `load_tasks_by_org()`, `get_tasks_for_prospect()`, `get_all_prospect_tasks()`, `add_prospect_task()` — remove section tracking, use flat index
- `crm_blueprint.py`: Routes that call task functions and pass section info — remove section from response dicts
- `memory_reader.py`: `load_tasks()`, `update_task_status()`, `append_task_to_section()` — these use section mapping; refactor to flat list. Note: `_parse_task_line()` and `_format_task_line()` already ignore the section parameter (it's accepted but unused) — just remove the parameter.
- `tasks.html` template: Remove `TASK_MODAL_SECTIONS` window variable, remove `SECTIONS` constant

## 7. Constraints

- **Backward compatibility**: The bracket format `[org:] [owner:]` should still be parseable by `_parse_org_tagged_task()` for any manually-edited tasks, but new tasks always write in `(OrgName) — assigned:Name` format.
- **Done section preserved**: `## Done` remains as the only section header — it separates completed tasks. When a task is completed, it moves below `## Done`. When restored, it moves above it.
- **Index stability during session**: Indices shift when tasks are added/deleted/completed (same as today within a section). The frontend reloads the full list after every mutation, so stale indices aren't a risk.
- **No database**: Everything remains markdown-backed.

## 8. Acceptance Criteria

- [ ] TASKS.md contains no section headers except `## Done`
- [ ] All former bracket-format `[org:] [owner:]` tasks converted to standard format
- [ ] `GET /tasks/api/tasks` returns `{ "open": [...], "done": [...] }` flat structure
- [ ] All CRUD routes use `/<index>` instead of `/<section>/<index>`
- [ ] Task edit modal no longer sends section in API calls
- [ ] Add-task form has no section dropdown
- [ ] Task cards show no section label in metadata
- [ ] `TASK_SECTIONS` constant is removed
- [ ] CRM tasks page (`/crm/tasks`): clicking a task opens the edit modal with correct data
- [ ] CRM tasks page: clicking the prospect/org link navigates to prospect detail (not the modal)
- [ ] Existing tests pass (update test expectations as needed)
- [ ] Feedback loop prompt has been run

## 9. Files Likely Touched

| File | Change |
|---|---|
| `TASKS.md` | Flatten structure, merge IR/Fundraising, convert bracket format |
| `app/delivery/tasks_blueprint.py` | Rewrite all routes to use flat index, remove TASK_SECTIONS, update `_load_tasks_full()` and `_find_task_line()` |
| `app/sources/memory_reader.py` | Remove section param from `_parse_task_line()` and `_format_task_line()`, refactor `load_tasks()`, `update_task_status()`, `append_task_to_section()` → `append_task()` |
| `app/sources/crm_reader.py` | Update `load_tasks_by_org()`, `get_tasks_for_prospect()`, `get_all_prospect_tasks()`, `add_prospect_task()` — flat indexing, no section default |
| `app/delivery/crm_blueprint.py` | Remove section from task API responses and `add_prospect_task()` calls |
| `app/static/tasks/tasks.js` | Update `loadTasks()` to consume flat response, remove section from `renderCard()`, `submitAdd()`, and all API call URLs; remove section dropdown from add form |
| `app/static/task-edit-modal.js` | Remove `_section` state, update save/delete URLs to index-only |
| `app/templates/tasks/tasks.html` | Remove `TASK_MODAL_SECTIONS`, remove `SECTIONS` constant |
| `app/templates/crm_tasks.html` | Add task-edit-modal includes, `TASK_MODAL_*` window vars, `data-index` on task items, click handler JS, cursor:pointer CSS |
| `app/delivery/crm_blueprint.py` | `crm_tasks()` route: compute flat_index for each task; remove section from task API responses |
| `app/tests/` | Update any task-related test expectations |
