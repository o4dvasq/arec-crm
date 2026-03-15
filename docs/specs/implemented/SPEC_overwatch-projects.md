SPEC: Overwatch Projects
Project: overwatch | Branch: main | Date: 2026-03-15
Status: Ready for implementation

SEQUENCING: Phase 1B. Implement AFTER SPEC_overwatch-people.md (1A) — reuses overwatch_reader.py patterns and shared UI components.
DEPENDS ON: Working Overwatch Flask app on port 3002, data/projects/ directory exists, overwatch_reader.py exists.
BACKEND: All data via overwatch_reader.py and markdown files — NO database, NO SQLAlchemy.

---

## 1. Objective

Build project tracking for Oscar's personal and side projects in Overwatch. Projects are stored as individual markdown files in `data/projects/`. Each project has a status, description, related people, and related tasks. This gives Oscar a structured way to track what he's working on outside of CRM deal pipeline — home improvements, personal investments, travel planning, side ventures, etc.

---

## 2. Scope

### In Scope
- Add project CRUD functions to `overwatch_reader.py`
- Project list page with status filter
- Project detail page with editable fields and rendered markdown body
- Project create form
- Status field: open / closed
- Task ↔ Project linking: tasks in TASKS.md can reference a project tag; project detail shows related tasks
- People ↔ Project linking: project frontmatter lists related people slugs; renders as links on detail page

### Out of Scope
- Gantt charts, timelines, or project scheduling
- Sub-projects or project hierarchy
- Project templates
- Automated project creation from tasks or notes
- Budget or financial tracking on projects

---

## 3. Business Rules

1. **Slug format:** lowercase with hyphens, derived from project name. Example: `kitchen-remodel.md`, `sf-stairways-site.md`.
2. **Status:** `open` or `closed`. Default is `open` on creation. Closed projects remain in the directory, just filtered out of the default list view.
3. **Task linking:** Tasks in TASKS.md can include a project tag in the format `#project:slug` (e.g., `#project:kitchen-remodel`). The project detail page scans TASKS.md for tasks with the matching tag and displays them. This is read-only on the project detail — task editing happens on the Tasks page.
4. **People linking:** Project frontmatter has an optional `People` field listing comma-separated slugs. Each slug links to `/people/<slug>`. If the slug doesn't match an existing person file, render as plain text (not a broken link).
5. **No duplicate slugs.** Same rule as People — error on conflict, don't overwrite.
6. **Closed projects hidden by default.** List page shows open projects by default. A toggle/filter reveals closed projects.

---

## 4. Data Model

### Project file: `data/projects/{slug}.md`

```markdown
- **Status:** open
- **People:** maria-gonzalez, kevin-chen

# Kitchen Remodel

Full gut renovation of the kitchen. Started Feb 2026, targeting May completion.
Contractor is Kevin Chen (recommended by Maria).

## Budget Notes

- Cabinets: ~$12K (ordered from IKEA)
- Countertops: ~$4K (quartz, pending selection)
- Labor: ~$15K (Kevin's quote)

## Timeline

- Feb: Demo + electrical rough-in
- Mar: Cabinets + plumbing
- Apr: Countertops + backsplash
- May: Final touches + appliances
```

### Parser rules
- Frontmatter block at top of file: lines matching `- **FieldName:** Value` before the first `#` heading.
- Recognized fields: `Status`, `People`
- `People` value is comma-separated slugs (trimmed, lowercase).
- Everything from the first `#` heading onward is freeform prose.

### Write rules
- Same pattern as People: update frontmatter block, preserve body content below `#` heading.
- If `People` field is cleared, remove the line entirely.

---

## 5. UI / Interface

### 5.1 Project List Page (`/projects`)

```
┌─────────────────────────────────────────────────────────┐
│  Overwatch    Dashboard | Tasks | People | Projects     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Projects                           [+ New Project]     │
│                                                         │
│  [Show closed]                                          │
│                                                         │
│  Kitchen Remodel             open       2 people        │
│  SF Stairways Site           open       0 people        │
│  Tahoe Trip Planning         open       3 people        │
│  ...                                                    │
└─────────────────────────────────────────────────────────┘
```

- Table/list with columns: Name (link to detail), Status badge (green for open, gray for closed), People count
- [Show closed] toggle — when active, shows all projects; when off (default), shows only open
- Sort: open projects first, then alphabetical
- [+ New Project] button → create form

### 5.2 Project Detail Page (`/projects/<slug>`)

```
┌─────────────────────────────────────────────────────────┐
│  Overwatch    Dashboard | Tasks | People | Projects     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Kitchen Remodel                           open         │
│                                                         │
│  People    Maria Gonzalez, Kevin Chen                   │
│                                              [Edit]     │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  Full gut renovation of the kitchen...                  │
│  (rendered markdown body)                               │
│                                              [Edit]     │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  Related Tasks                                          │
│  ☐ Get countertop samples from supplier  #project:...   │
│  ☐ Schedule plumbing inspection          #project:...   │
│  ☑ Order IKEA cabinets                   #project:...   │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│                                              [Close]    │
│                                             [Delete]    │
└─────────────────────────────────────────────────────────┘
```

- **Header:** Project name + status badge.
- **People row:** Comma-separated links to `/people/<slug>`. If slug doesn't match a file, render as plain text.
- **[Edit] on fields:** Switches to edit mode — Status (dropdown: open/closed), People (text input, comma-separated slugs). Save/Cancel.
- **Body section:** Rendered markdown. [Edit] switches to textarea with raw markdown.
- **Related Tasks section:** Read-only list of tasks from TASKS.md that contain `#project:{slug}`. Shows task text, checkbox status. Clicking a task goes to the Tasks page (or just links to `/tasks`).
- **[Close] button:** Sets status to `closed`. Shows as [Reopen] if already closed.
- **[Delete] button:** Subtle, confirm dialog. Deletes the project file. Does NOT remove `#project:slug` tags from TASKS.md (they become orphaned tags, harmless).

### 5.3 Project Create Form (`/projects/new`)

```
┌─────────────────────────────────────────────────────────┐
│  New Project                                            │
│                                                         │
│  Name           [                              ]        │
│  People         [                              ]        │
│  (comma-separated: maria-gonzalez, kevin-chen)          │
│                                                         │
│  Description (optional)                                 │
│  ┌─────────────────────────────────────────────┐        │
│  │                                             │        │
│  └─────────────────────────────────────────────┘        │
│                                                         │
│                          [Cancel]  [Create Project]     │
└─────────────────────────────────────────────────────────┘
```

- Name is required. Status defaults to `open` (not shown on create form).
- On success: redirect to new project detail page.
- On duplicate slug: inline error.

### 5.4 States

| State | Behavior |
|-------|----------|
| **Project list empty** | "No projects yet" with prominent [+ New Project] |
| **No related tasks** | Related Tasks section shows "No tasks tagged with this project" with hint: "Add `#project:{slug}` to any task in TASKS.md" |
| **No people linked** | People row hidden in display mode, text input shown in edit mode |
| **Closed project** | Status badge is gray. [Close] button becomes [Reopen]. |

---

## 6. Integration Points

### Reads from
- `data/projects/{slug}.md` — project data
- `TASKS.md` — scan for `#project:{slug}` tags to find related tasks
- `data/people/{slug}.md` — verify people slugs resolve (for rendering links vs plain text)

### Writes to
- `data/projects/{slug}.md` — create, update, delete

### Routes needed

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/projects` | Project list page |
| GET | `/projects/new` | Create form |
| POST | `/projects` | Create project (form submit) |
| GET | `/projects/<slug>` | Project detail page |
| POST | `/projects/<slug>/fields` | Update status + people fields (AJAX JSON) |
| POST | `/projects/<slug>/body` | Update body markdown (AJAX JSON) |
| POST | `/projects/<slug>/close` | Toggle open/closed |
| POST | `/projects/<slug>/delete` | Delete project |

### Nav bar
- Add "Projects" link to `_nav.html`, after "People".

---

## 7. Constraints

1. **Extend `overwatch_reader.py`** with project functions. Same module, new section. Do not create a separate reader module.
2. **Task scanning is read-only.** Project detail reads TASKS.md to find related tasks but never writes to it. Task management stays on the Tasks page.
3. **No new Python libraries.**
4. **`DATA_DIR` constant for paths.** Same as People spec.
5. **People slug validation is soft.** If a slug in the People field doesn't match a file, render as plain text — don't error or prevent save.
6. **`#project:slug` tag format.** This is the only recognized format. The tag scanner should use a simple regex: `#project:([a-z0-9-]+)`.

---

## 8. Acceptance Criteria

- [ ] `overwatch_reader.py` has functions: `list_projects()`, `get_project(slug)`, `create_project(name, fields)`, `update_project_fields(slug, fields)`, `update_project_body(slug, markdown)`, `delete_project(slug)`, `close_project(slug)`, `reopen_project(slug)`, `get_project_tasks(slug)`
- [ ] `/projects` page shows all open projects from `data/projects/` with name, status badge, people count
- [ ] [Show closed] toggle reveals closed projects
- [ ] `/projects/<slug>` shows project detail with people links, rendered body, and related tasks from TASKS.md
- [ ] Fields editable inline (status dropdown, people text input)
- [ ] Body editable via textarea
- [ ] `/projects/new` form creates a new project file and redirects to detail page
- [ ] Duplicate slug detection shows error
- [ ] [Close] / [Reopen] toggles status
- [ ] Delete removes the file and redirects to project list
- [ ] Related tasks show tasks from TASKS.md containing `#project:{slug}`
- [ ] People slugs that match existing files render as links; non-matching render as plain text
- [ ] "Projects" appears in the nav bar on all Overwatch pages
- [ ] `python3 -m pytest app/tests/ -v` passes (add tests for project functions in overwatch_reader.py)
- [ ] Feedback loop prompt has been run

---

## 9. Files Likely Touched

| File | Reason |
|------|--------|
| `app/sources/overwatch_reader.py` | Add project CRUD functions, task scanner |
| `app/delivery/projects_blueprint.py` | NEW — all project routes |
| `app/delivery/dashboard.py` | Register projects_blueprint |
| `app/templates/projects/list.html` | NEW — project list page |
| `app/templates/projects/detail.html` | NEW — project detail with related tasks |
| `app/templates/projects/new.html` | NEW — project create form |
| `app/templates/_nav.html` | Add "Projects" link |
| `app/static/overwatch.css` | Styles for project pages (status badges, task list, etc.) |
| `app/static/overwatch.js` | Edit/save/cancel, close/reopen, AJAX calls |
| `app/tests/test_overwatch_reader.py` | Add project CRUD tests, task scanning tests |
