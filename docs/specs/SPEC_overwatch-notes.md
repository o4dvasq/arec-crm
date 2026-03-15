SPEC: Overwatch Notes
Project: overwatch | Branch: main | Date: 2026-03-15
Status: Ready for implementation

SEQUENCING: Phase 1C. Implement AFTER SPEC_overwatch-projects.md (1B) — reuses overwatch_reader.py and shared UI patterns.
DEPENDS ON: Working Overwatch Flask app on port 3002, data/notes/ directory exists, overwatch_reader.py with people + project functions.
BACKEND: All data via overwatch_reader.py and markdown files — NO database, NO SQLAlchemy.

---

## 1. Objective

Build a quick-capture notes system for Overwatch. Notes are individual markdown files in `data/notes/` named by date and slug. Each note can optionally be tagged with people and/or projects, creating lightweight links between entities. This gives Oscar a place to capture thoughts, meeting notes, research, and ideas that don't fit into tasks or project descriptions — with the ability to find them later by date, tag, or search.

---

## 2. Scope

### In Scope
- Add note CRUD functions to `overwatch_reader.py`
- Notes list page with date-sorted display and search
- Note detail page with rendered markdown
- Quick-capture form on the dashboard (text input → creates note file)
- Full note create/edit form on dedicated page
- YAML frontmatter tags: people (list of slugs), projects (list of slugs)
- Tag rendering as links on note detail page

### Out of Scope
- Rich text editor (textarea with raw markdown is fine)
- File attachments or image uploads
- Automatic note creation from inbox.md processing (future)
- Note templates or categories beyond tags
- Full-text search indexing (simple substring search is sufficient)
- Syncing notes to external services (Apple Notes, Google Keep, etc.)

---

## 3. Business Rules

1. **Filename format:** `YYYY-MM-DD-{slug}.md`. Example: `2026-03-15-hiking-route-research.md`. Date is the creation date. Slug is derived from the title.
2. **Title required.** Every note must have a title, which becomes both the `# Heading` in the file and the basis for the slug.
3. **Tags are optional.** A note can have zero or more people tags and zero or more project tags. Tags are stored in YAML frontmatter.
4. **Tag validation is soft.** If a tagged slug doesn't match an existing person or project file, render as plain text on the detail page — don't error or prevent save. People and projects can be deleted without breaking notes that reference them.
5. **Notes are immutable in date.** The creation date in the filename doesn't change on edit. Edits update content and tags only.
6. **Sort order:** Most recent first (by filename date prefix). Notes on the same date sort alphabetically by slug.
7. **Quick capture from dashboard:** A simple text input + submit creates a note with today's date. Title comes from the first line of input. Body is the rest. No tags on quick capture — those can be added by editing the note.

---

## 4. Data Model

### Note file: `data/notes/YYYY-MM-DD-{slug}.md`

```markdown
---
people:
  - maria-gonzalez
  - kevin-chen
projects:
  - kitchen-remodel
---

# Countertop Selection Research

Visited 3 showrooms today. Maria recommended the quartz supplier on Valencia St.

## Options

1. **Caesarstone Calacatta Nuvo** — $65/sqft, 3-week lead time. Clean white with subtle veining.
2. **Silestone Eternal Calacatta Gold** — $72/sqft, 2-week lead time. Warmer tone.
3. **IKEA Kasker** — $40/sqft, in stock. Decent but noticeably less premium.

## Decision

Going with option 1. Kevin said installation takes 2 days once the slab arrives.
```

### Parser rules
- YAML frontmatter between `---` fences at the top of the file.
- Recognized frontmatter keys: `people` (list of strings), `projects` (list of strings).
- If no frontmatter exists, treat tags as empty lists.
- Everything after the closing `---` is the note body (markdown).
- The `# Title` heading is the first line of the body.

### Write rules
- On create: generate file with YAML frontmatter (even if empty tags) + `# Title` + body.
- On edit: update frontmatter and body. Filename does not change.
- If all tags are removed, write empty frontmatter (`---\n---\n`) or omit it entirely — either is fine, just be consistent.
- On quick capture: no frontmatter (or empty frontmatter). Title from first line, body from the rest.

---

## 5. UI / Interface

### 5.1 Notes List Page (`/notes`)

```
┌─────────────────────────────────────────────────────────┐
│  Overwatch    Dashboard | Tasks | People | Projects | Notes │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Notes                                  [+ New Note]    │
│                                                         │
│  [ Search notes...                               ]     │
│                                                         │
│  Mar 15   Countertop Selection Research                 │
│           kitchen-remodel · maria-gonzalez · kevin-chen │
│                                                         │
│  Mar 14   Ideas for Mom's Birthday                      │
│           (no tags)                                     │
│                                                         │
│  Mar 12   SF Stairways — Filbert Steps Photo Notes      │
│           sf-stairways-site                             │
│  ...                                                    │
└─────────────────────────────────────────────────────────┘
```

- Reverse chronological list. Each entry shows: date (abbreviated), title (link to detail), tags below in muted text (people + project slugs as pills/badges).
- Search box: filters by title and body content (client-side substring match).
- [+ New Note] button → full create form.
- No pagination for v1 — all notes rendered. If this becomes slow (100+ notes), add pagination later.

### 5.2 Note Detail Page (`/notes/<filename>`)

```
┌─────────────────────────────────────────────────────────┐
│  Overwatch    Dashboard | Tasks | People | Projects | Notes │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Countertop Selection Research                          │
│  March 15, 2026                                         │
│                                                         │
│  People:    Maria Gonzalez · Kevin Chen                 │
│  Projects:  Kitchen Remodel                             │
│                                              [Edit]     │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  Visited 3 showrooms today...                           │
│  (rendered markdown body, excluding the # title)        │
│                                              [Edit]     │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│                                              [Delete]   │
└─────────────────────────────────────────────────────────┘
```

- **Header:** Title (from `# heading`), date (from filename, formatted nicely).
- **Tags section:** People and Projects listed as links. People link to `/people/<slug>`, Projects link to `/projects/<slug>`. Non-matching slugs render as plain text.
- **[Edit] on tags:** People text input (comma-separated slugs), Projects text input (comma-separated slugs). Save/Cancel.
- **Body section:** Rendered markdown (everything after `# Title`). [Edit] switches to textarea.
- **[Delete]:** Confirm dialog, then delete file and redirect to notes list.

### 5.3 Note Create Form (`/notes/new`)

```
┌─────────────────────────────────────────────────────────┐
│  New Note                                               │
│                                                         │
│  Title          [                              ]        │
│  People         [                              ]        │
│  (comma-separated slugs, optional)                      │
│  Projects       [                              ]        │
│  (comma-separated slugs, optional)                      │
│                                                         │
│  Body                                                   │
│  ┌─────────────────────────────────────────────┐        │
│  │                                             │        │
│  │                                             │        │
│  │                                             │        │
│  └─────────────────────────────────────────────┘        │
│                                                         │
│                            [Cancel]  [Create Note]      │
└─────────────────────────────────────────────────────────┘
```

- Title required. Everything else optional.
- Date is today (auto-set, not user-editable).
- On success: redirect to note detail page.

### 5.4 Dashboard Quick Capture

Add to the existing Overwatch dashboard, below or beside the existing tasks panel:

```
┌─────────────────────────────────────────────────────────┐
│  Quick Note                                             │
│  ┌─────────────────────────────────────────────┐        │
│  │ Type a note... first line becomes the title │  [Save]│
│  └─────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

- Single textarea. First line becomes the title, rest becomes the body.
- [Save] creates the note file with today's date, no tags.
- On success: clear the textarea, show brief "Note saved" confirmation with a link to the new note.
- If the textarea is empty, Save is disabled.

### 5.5 States

| State | Behavior |
|-------|----------|
| **Notes list empty** | "No notes yet" with prominent [+ New Note] and the quick capture box |
| **Search no results** | "No notes match your search" |
| **Note with no tags** | Tags section hidden in display mode. Shown empty in edit mode. |
| **Quick capture empty** | Save button disabled |
| **Quick capture success** | Clear textarea, show "Note saved — [View]" inline confirmation |

---

## 6. Integration Points

### Reads from
- `data/notes/YYYY-MM-DD-{slug}.md` — all note data
- `data/people/{slug}.md` — verify people tag slugs for link rendering
- `data/projects/{slug}.md` — verify project tag slugs for link rendering

### Writes to
- `data/notes/YYYY-MM-DD-{slug}.md` — create, update, delete

### Routes needed

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/notes` | Notes list page |
| GET | `/notes/new` | Create form |
| POST | `/notes` | Create note (form submit) |
| POST | `/notes/quick` | Quick capture from dashboard (AJAX) |
| GET | `/notes/<filename>` | Note detail page |
| POST | `/notes/<filename>/tags` | Update tags (AJAX JSON) |
| POST | `/notes/<filename>/body` | Update body markdown (AJAX JSON) |
| POST | `/notes/<filename>/delete` | Delete note |

### Nav bar
- Add "Notes" link to `_nav.html`, after "Projects".

### Dashboard
- Add quick capture widget to `dashboard.html`.

---

## 7. Constraints

1. **Extend `overwatch_reader.py`** with note functions. Same module, new section.
2. **YAML frontmatter via PyYAML** (`pyyaml` is already in requirements). Use `yaml.safe_load` / `yaml.safe_dump`.
3. **No new Python libraries** beyond what's already in requirements.
4. **Filename is the note ID.** Routes use the full filename (without `.md` extension) as the identifier. Example: `/notes/2026-03-15-countertop-research`.
5. **No filename changes on edit.** The creation date and slug are permanent. If Oscar wants a different title, the filename stays — only the `# heading` in the body changes.
6. **Quick capture is minimal.** No tag selection, no date picker. Just text → file. Oscar can edit to add tags later.

---

## 8. Acceptance Criteria

- [ ] `overwatch_reader.py` has functions: `list_notes()`, `get_note(filename)`, `create_note(title, body, people_tags, project_tags)`, `quick_capture_note(text)`, `update_note_tags(filename, people_tags, project_tags)`, `update_note_body(filename, markdown)`, `delete_note(filename)`, `search_notes(query)`
- [ ] `/notes` page shows all notes reverse-chronologically with title, date, and tag badges
- [ ] Search box filters by title and body content
- [ ] `/notes/<filename>` shows note with rendered markdown, date, and tag links
- [ ] Tags editable inline (people + projects as comma-separated slug inputs)
- [ ] Body editable via textarea
- [ ] `/notes/new` form creates a new note file with today's date and redirects to detail
- [ ] Quick capture on dashboard creates a note from text input (first line = title, rest = body)
- [ ] Quick capture shows confirmation with link to new note
- [ ] People tags render as links to `/people/<slug>` (or plain text if slug doesn't match a file)
- [ ] Project tags render as links to `/projects/<slug>` (or plain text if slug doesn't match a file)
- [ ] Delete removes the file and redirects to notes list
- [ ] "Notes" appears in the nav bar on all Overwatch pages
- [ ] `python3 -m pytest app/tests/ -v` passes (add tests for note functions in overwatch_reader.py)
- [ ] Feedback loop prompt has been run

---

## 9. Files Likely Touched

| File | Reason |
|------|--------|
| `app/sources/overwatch_reader.py` | Add note CRUD functions, YAML frontmatter parsing |
| `app/delivery/notes_blueprint.py` | NEW — all note routes |
| `app/delivery/dashboard.py` | Register notes_blueprint, add quick capture route context |
| `app/templates/notes/list.html` | NEW — notes list page |
| `app/templates/notes/detail.html` | NEW — note detail page |
| `app/templates/notes/new.html` | NEW — note create form |
| `app/templates/dashboard.html` | Add quick capture widget |
| `app/templates/_nav.html` | Add "Notes" link |
| `app/static/overwatch.css` | Styles for notes pages (tag badges, date formatting, quick capture) |
| `app/static/overwatch.js` | Edit/save/cancel, quick capture AJAX, search filter |
| `app/tests/test_overwatch_reader.py` | Add note CRUD tests, YAML parsing tests, quick capture tests |
