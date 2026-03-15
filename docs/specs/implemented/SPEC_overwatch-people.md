SPEC: Overwatch People
Project: overwatch | Branch: main | Date: 2026-03-15
Status: Ready for implementation

SEQUENCING: Phase 1A. Implement AFTER Overwatch scaffold is running (SPEC_overwatch-repo-scaffold.md).
DEPENDS ON: Working Overwatch Flask app on port 3002, data/people/ directory exists.
BACKEND: All data via overwatch_reader.py and markdown files — NO database, NO SQLAlchemy.

---

## 1. Objective

Build person management for Oscar's personal network in Overwatch. People are stored as individual markdown files in `data/people/`. This gives Oscar a place to track personal contacts (friends, family, advisors, service providers) separately from investor contacts in the CRM. Each person has a profile with contact info, relationship type, and freeform notes.

---

## 2. Scope

### In Scope
- New `overwatch_reader.py` module with person CRUD (create, read, update, list, search)
- People list page with search/filter
- Person detail page with editable fields
- Person create form
- Relationship type field (friend, family, colleague, advisor, service-provider)
- Manual "Also in CRM" tag (boolean, not a live filesystem check)
- People blueprint with all routes

### Out of Scope
- Live cross-repo lookup against arec-crm/contacts/ (future — Phase 4)
- Email integration or automatic enrichment (future — Phase 2)
- Importing contacts from Gmail, iCloud, or vCards
- Merging or deduplicating people across CRM and Overwatch
- Organization/company entity in Overwatch (CRM concept only)

---

## 3. Business Rules

1. **Slug format:** `{firstname}-{lastname}` lowercase with hyphens. Example: `maria-gonzalez.md`. For single names or unusual names, use whatever makes a readable slug.
2. **Relationship types:** `friend`, `family`, `colleague`, `advisor`, `service-provider`. These are the only valid values. Stored in the markdown frontmatter block. A person has exactly one relationship type.
3. **Also in CRM tag:** Optional boolean field `crm_contact: true` in the frontmatter. This is a manual tag Oscar sets — Overwatch does not check the CRM filesystem. Display as a subtle badge on the person detail and list pages.
4. **Empty fields hidden in display mode.** If email, phone, or notes are empty, don't render those rows. All fields visible in edit mode.
5. **Search matches against name, relationship type, and notes content.** Case-insensitive substring match.
6. **No duplicate slugs.** If Oscar creates "Maria Gonzalez" and `maria-gonzalez.md` already exists, show an error rather than overwriting.

---

## 4. Data Model

### Person file: `data/people/{slug}.md`

```markdown
- **Relationship:** friend
- **Email:** maria@gmail.com
- **Phone:** +1-415-555-1234
- **CRM Contact:** true

# Maria Gonzalez

Met at the SF hiking meetup in 2024. Works in product management at Stripe.
Introduced me to Kevin for the real estate advisory project.

## Notes

- 2026-03-10: Caught up over coffee, she's considering a move to LA
- 2026-02-15: Recommended her dentist — Dr. Park in the Mission
```

### Parser rules
- Contact block at the top of the file: lines matching `- **FieldName:** Value` before the first `#` heading.
- Recognized fields: `Relationship`, `Email`, `Phone`, `CRM Contact`
- Everything from the first `#` heading onward is freeform prose/notes.
- `CRM Contact` value is `true` or absent (no `false` — just omit the line).

### Write rules
- On save, write/update the contact block at the top of the file.
- Preserve all content from the `#` heading onward unchanged.
- If a field is cleared, remove that line from the block.
- On create, generate the file with the contact block + a `# Name` heading + empty body.

---

## 5. UI / Interface

### 5.1 People List Page (`/people`)

```
┌─────────────────────────────────────────────────────────┐
│  Overwatch    Dashboard | Tasks | People | Projects     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  People                              [+ New Person]     │
│                                                         │
│  [ Search people...              ]  [Filter: All ▼]     │
│                                                         │
│  Maria Gonzalez          friend              CRM        │
│  Dr. James Park          service-provider               │
│  Kevin Chen              colleague           CRM        │
│  Mom                     family                         │
│  ...                                                    │
└─────────────────────────────────────────────────────────┘
```

- Table/list with columns: Name (link to detail), Relationship type (styled as pill/badge), CRM indicator (small badge, only if tagged)
- Filter dropdown: All, friend, family, colleague, advisor, service-provider
- Search box: filters list as user types (client-side, same pattern as CRM search bar)
- Sort: alphabetical by name (default)
- [+ New Person] button → person create form

### 5.2 Person Detail Page (`/people/<slug>`)

```
┌─────────────────────────────────────────────────────────┐
│  Overwatch    Dashboard | Tasks | People | Projects     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Maria Gonzalez                    friend    CRM        │
│                                                         │
│  Email      maria@gmail.com                             │  ← mailto: link
│  Phone      +1-415-555-1234                             │  ← tel: link
│                                              [Edit]     │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  Met at the SF hiking meetup in 2024. Works in product  │
│  management at Stripe. Introduced me to Kevin for the   │
│  real estate advisory project.                          │
│                                                         │
│  ## Notes                                               │
│  - 2026-03-10: Caught up over coffee...                 │
│  - 2026-02-15: Recommended her dentist...               │
│                                              [Edit]     │
└─────────────────────────────────────────────────────────┘
```

- **Top section:** Name as heading, relationship badge, CRM badge (if tagged). Contact fields below (same inline style as CRM contact box — label left, value right).
- **[Edit] on contact fields:** Switches to inline edit mode for Relationship (dropdown), Email (text), Phone (text), CRM Contact (checkbox). Save/Cancel buttons.
- **Body section:** Rendered markdown from the `#` heading onward. Displayed as HTML.
- **[Edit] on body:** Switches to a textarea with raw markdown. Save/Cancel. On save, write back to the file preserving the contact block at the top.
- **Delete button:** Subtle, at the bottom. Confirm dialog before deleting the file.

### 5.3 Person Create Form (`/people/new`)

```
┌─────────────────────────────────────────────────────────┐
│  New Person                                             │
│                                                         │
│  Name           [                              ]        │
│  Relationship   [friend              ▼]                 │
│  Email          [                              ]        │
│  Phone          [                              ]        │
│  CRM Contact    [ ]                                     │
│                                                         │
│  Notes (optional)                                       │
│  ┌─────────────────────────────────────────────┐        │
│  │                                             │        │
│  └─────────────────────────────────────────────┘        │
│                                                         │
│                           [Cancel]  [Create Person]     │
└─────────────────────────────────────────────────────────┘
```

- Name is required. All other fields optional.
- Slug auto-generated from name on submit.
- On success: redirect to the new person's detail page.
- On duplicate slug: show inline error, don't overwrite.

### 5.4 States

| State | Behavior |
|-------|----------|
| **People list empty** | Show "No people yet" message with prominent [+ New Person] button |
| **Search no results** | Show "No people match your search" |
| **Person detail, all fields empty** | Only name + relationship shown. No contact info rows. |
| **Save in progress** | Save button shows "Saving..." — disable double-click |
| **Save success** | Return to display mode, brief green flash |
| **Save error** | Stay in edit mode, inline error message |
| **Delete confirm** | Browser confirm dialog: "Delete {name}? This cannot be undone." |

---

## 6. Integration Points

### Reads from
- `data/people/{slug}.md` — all person data

### Writes to
- `data/people/{slug}.md` — create, update, delete

### Routes needed

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/people` | People list page |
| GET | `/people/new` | Create form |
| POST | `/people` | Create person (form submit) |
| GET | `/people/<slug>` | Person detail page |
| POST | `/people/<slug>/contact` | Update contact fields (AJAX JSON) |
| POST | `/people/<slug>/body` | Update body/notes markdown (AJAX JSON) |
| POST | `/people/<slug>/delete` | Delete person |
| GET | `/api/people` | JSON list of all people (for search index, nav search if added later) |

### Nav bar
- Add "People" link to the Overwatch nav bar (`_nav.html`), between "Tasks" and "Projects".

---

## 7. Constraints

1. **New module `overwatch_reader.py`** for all people file I/O. Do not add person logic to `memory_reader.py` (that's for tasks/inbox).
2. **No new Python libraries.** Use existing Flask, Jinja2, standard library. Markdown rendering via the `markdown` package already in requirements.
3. **Match CRM inline field style** for the contact info box. Keep the Overwatch UI visually consistent with CRM patterns.
4. **`DATA_DIR` constant for paths.** Never hardcode `data/people/`. Use a constant derived from the app root.
5. **Preserve file content on contact-field save.** The body section below the contact block must not be altered when saving contact fields.
6. **No filesystem reads to arec-crm.** The CRM Contact tag is manual — do not attempt to check arec-crm paths.

---

## 8. Acceptance Criteria

- [ ] `overwatch_reader.py` exists with functions: `list_people()`, `get_person(slug)`, `create_person(name, fields)`, `update_person_contact(slug, fields)`, `update_person_body(slug, markdown)`, `delete_person(slug)`, `search_people(query)`
- [ ] `/people` page shows all people from `data/people/` with name, relationship badge, CRM badge
- [ ] Filter dropdown filters by relationship type
- [ ] Search box filters by name, relationship, and notes content
- [ ] `/people/<slug>` shows person detail with contact fields and rendered markdown body
- [ ] Contact fields editable inline (Relationship dropdown, Email, Phone, CRM Contact checkbox)
- [ ] Body/notes editable via textarea with raw markdown
- [ ] `/people/new` form creates a new person file and redirects to detail page
- [ ] Duplicate slug detection shows error, does not overwrite
- [ ] Delete removes the file and redirects to people list
- [ ] Email renders as `mailto:` link, Phone as `tel:` link
- [ ] "People" appears in the nav bar on all Overwatch pages
- [ ] `python3 -m pytest app/tests/ -v` passes (add tests for overwatch_reader.py)
- [ ] Feedback loop prompt has been run

---

## 9. Files Likely Touched

| File | Reason |
|------|--------|
| `app/sources/overwatch_reader.py` | NEW — all people CRUD and file I/O |
| `app/delivery/people_blueprint.py` | NEW — all people routes |
| `app/delivery/dashboard.py` | Register people_blueprint |
| `app/templates/people/list.html` | NEW — people list page |
| `app/templates/people/detail.html` | NEW — person detail page |
| `app/templates/people/new.html` | NEW — person create form |
| `app/templates/_nav.html` | Add "People" link |
| `app/static/overwatch.css` | Styles for people pages (relationship badges, contact box, etc.) |
| `app/static/overwatch.js` | Edit/save/cancel toggle, search filter, AJAX calls |
| `app/tests/test_overwatch_reader.py` | NEW — unit tests for people CRUD |
