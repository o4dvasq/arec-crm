SPEC: Stale Page Cleanup & Add Meetings to Nav | Project: arec-crm | Date: 2026-03-20 | Status: Ready for implementation

---

## 1. Objective

Remove dead/stale pages and routes that are not reachable from the main navigation, consolidate duplicated task endpoints, and add the Meetings page back to the navigation bar.

## 2. Scope

### In Scope

**A. Remove `/tasks/` page and tasks_blueprint.py entirely**
- Delete `app/delivery/tasks_blueprint.py`
- Delete `app/templates/tasks/tasks.html`
- Delete `app/static/tasks/tasks.js`
- Delete `app/static/tasks/tasks.css`
- Remove `from delivery.tasks_blueprint import tasks_bp` and `app.register_blueprint(tasks_bp)` from `dashboard.py`
- The `/crm/tasks` page (crm_tasks.html) is the canonical tasks UI

**B. Migrate task APIs from tasks_blueprint to crm_blueprint**
- The tasks_blueprint currently provides the flat-index task CRUD APIs (`/tasks/api/task`, `/tasks/api/task/<index>`, etc.) that the task-edit-modal.js depends on
- These routes must be moved to crm_blueprint.py (under `/crm/api/task/...`) before deleting tasks_blueprint
- Update `task-edit-modal.js` to call `/crm/api/task/...` instead of `/tasks/api/task/...`
- Migrate the following helper functions from tasks_blueprint to an appropriate location (crm_reader.py or a new task_helpers.py):
  - `_load_tasks_full()` — returns `{open: [...], done: [...]}`
  - `_find_task_line(lines, index, done)` — flat-index line finder
  - `_find_done_insertion_point(lines)` and `_find_open_insertion_point(lines)`
  - `_read_task_lines()` and `_write_task_file(lines)`
  - `_normalize_assigned_to()` — delegates to `normalize_team_name()`
- Consolidate with existing CRM task endpoints where they overlap (e.g., `/crm/api/tasks` GET already exists for org-specific tasks; merge or keep both with clear naming)

**C. Remove legacy task API routes from dashboard.py**
- Delete `/api/task/complete` (POST) — duplicates CRM endpoint
- Delete `/api/task/add` (POST) — duplicates CRM endpoint
- Delete `/api/task/status` (PATCH) — returns 501 already

**D. Remove `/dashboard` page**
- Delete the `/dashboard` route and its `dashboard()` function from `dashboard.py`
- Delete `app/templates/dashboard.html`
- Keep the meeting helper functions (`_load_recent_meetings`, `_render_meeting_markdown`) if they are used by meeting routes; otherwise delete them too

**E. Remove orphaned template**
- Delete `app/templates/crm_org_detail.html` — no route renders it; replaced by `crm_org_edit.html`

**F. Add Meetings to navigation bar**
- Add a "Meetings" tab to `_nav.html` linking to `/crm/meetings`
- Position it after "Tasks" in the tab order: Tasks | Pipeline | People | Orgs | **Meetings**
- The `crm_meetings.html` template should set `active_tab = 'meetings'` (verify it does)
- Individual meeting detail pages (`/meetings/<filename>`) remain accessible from the meetings list — no nav tab needed for those

### Out of Scope

- Changes to meeting CRUD functionality
- Changes to the CRM tasks page UI (`crm_tasks.html`) — covered by SPEC_eliminate-task-sections
- Refactoring crm_blueprint.py (it's large but functional)

## 3. Business Rules

- **No broken links**: Before removing any route, verify no template or JS file references it. The main consumers of the `/tasks/api/...` routes are `task-edit-modal.js` and the pipeline template — update these to use the new `/crm/api/task/...` paths.
- **Prospect detail task panel**: The prospect detail page calls `/tasks/api/tasks/for-org` to load tasks for a specific org. This route must be migrated to `/crm/api/tasks/for-org` or an equivalent CRM endpoint.
- **Pipeline task editing**: The pipeline template (`crm_pipeline.html`) uses `task-edit-modal.js` to edit tasks. Verify it works after the API path change.
- **Redirect safety**: Consider adding a redirect from `/tasks/` → `/crm/tasks` temporarily in case anyone has it bookmarked. Optional — can skip if no external links exist.

## 4. Data Model / Schema Changes

None. All data remains in TASKS.md and crm/ markdown files.

## 5. UI / Interface

### Navigation bar (`_nav.html`)

Before:
```
Tasks | Pipeline | People | Orgs | [Search]
```

After:
```
Tasks | Pipeline | People | Orgs | Meetings | [Search]
```

## 6. Integration Points

### API Route Migration Map

| Old Route (tasks_blueprint) | New Route (crm_blueprint) |
|---|---|
| `GET /tasks/api/tasks` | `GET /crm/api/all-tasks` (new — returns `{open, done}`) |
| `POST /tasks/api/task` | `POST /crm/api/task` (new) |
| `PUT /tasks/api/task/<index>` | `PUT /crm/api/task/<index>` (new) |
| `DELETE /tasks/api/task/<index>` | `DELETE /crm/api/task/<index>` (new) |
| `POST /tasks/api/task/<index>/complete` | `POST /crm/api/task/<index>/complete` (new) |
| `POST /tasks/api/task/<index>/restore` | `POST /crm/api/task/<index>/restore` (new) |
| `PATCH /tasks/api/task/<index>/status` | `PATCH /crm/api/task/<index>/status` (new) |
| `PATCH /tasks/api/task/<index>/priority` | `PATCH /crm/api/task/<index>/priority` (new) |
| `GET /tasks/api/tasks/for-org` | `GET /crm/api/tasks/for-org` (exists, verify) |

### JS Files That Call Task APIs

| File | Current API Path | Update To |
|---|---|---|
| `task-edit-modal.js` | `/tasks/api/task` and `/tasks/api/task/${_index}` | `/crm/api/task` and `/crm/api/task/${_index}` |
| `crm_pipeline.html` (inline JS) | Uses `task-edit-modal.js` | Updated via modal |
| `crm_prospect_detail.html` (inline JS) | `/tasks/api/tasks/for-org` | `/crm/api/tasks/for-org` |
| `crm_tasks.html` (inline JS) | `/crm/api/tasks` (already CRM-prefixed) | No change needed |

## 7. Constraints

- **Order of operations**: Migrate task APIs to crm_blueprint FIRST, update JS references SECOND, delete tasks_blueprint LAST. This prevents any window where the APIs are unreachable.
- **Test all task flows**: After migration, verify task create/edit/delete/complete/restore works from: CRM tasks page, pipeline page task modal, and prospect detail page.
- **Keep meeting routes in dashboard.py**: The `/meetings/<filename>` and `/meetings/<filename>/save` routes can stay in dashboard.py (they're not stale — just not in the nav). Or move them to crm_blueprint if cleaner.

## 8. Acceptance Criteria

- [ ] `/tasks/` returns 404 (or redirects to `/crm/tasks`)
- [ ] `tasks_blueprint.py` is deleted
- [ ] `tasks/tasks.html`, `tasks/tasks.js`, `tasks/tasks.css` are deleted
- [ ] `dashboard.html` and `crm_org_detail.html` are deleted
- [ ] `/dashboard` returns 404
- [ ] Legacy `/api/task/*` routes in dashboard.py are removed
- [ ] All task CRUD APIs work at `/crm/api/task/...`
- [ ] `task-edit-modal.js` calls `/crm/api/task/...`
- [ ] "Meetings" tab appears in nav bar, links to `/crm/meetings`, highlights when active
- [ ] Task editing works from: CRM tasks page, pipeline page, prospect detail page
- [ ] No console errors on any page
- [ ] Existing tests pass (update import paths as needed)
- [ ] Feedback loop prompt has been run

## 9. Files Likely Touched

| File | Change |
|---|---|
| `app/delivery/tasks_blueprint.py` | **DELETE** |
| `app/templates/tasks/tasks.html` | **DELETE** |
| `app/static/tasks/tasks.js` | **DELETE** |
| `app/static/tasks/tasks.css` | **DELETE** |
| `app/templates/dashboard.html` | **DELETE** |
| `app/templates/crm_org_detail.html` | **DELETE** |
| `app/delivery/dashboard.py` | Remove tasks_blueprint import/register, remove `/dashboard` route, remove legacy `/api/task/*` routes |
| `app/delivery/crm_blueprint.py` | Add migrated task CRUD routes from tasks_blueprint |
| `app/sources/crm_reader.py` or new `app/sources/task_helpers.py` | Receive migrated helper functions (`_load_tasks_full`, `_find_task_line`, etc.) |
| `app/static/task-edit-modal.js` | Update API paths from `/tasks/api/task` → `/crm/api/task` |
| `app/templates/_nav.html` | Add "Meetings" tab |
| `app/templates/crm_tasks.html` | Verify `active_tab='tasks'` is set correctly |
| `app/templates/crm_pipeline.html` | Verify task modal still works after API path change |
| `app/templates/crm_prospect_detail.html` | Update `/tasks/api/tasks/for-org` → `/crm/api/tasks/for-org` |
| `app/tests/` | Update any imports of tasks_blueprint |
