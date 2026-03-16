SPEC: CRM UI Cleanup Round 2
Project: arec-crm | Branch: main | Date: 2026-03-15
Status: Ready for implementation

---

## 1. Objective

A sweep of UX fixes across five CRM pages: Pipeline list, Prospect Detail, Org Detail, Person Detail, and Tasks Board. Removes dead UI, improves readability, and redesigns the Tasks page as a Kanban board grouped by owner. No new API endpoints — all changes are template/JS/CSS only unless noted.

## 2. Scope

### In Scope

**A. Pipeline List (`crm_pipeline.html`)**
- Tasks column: prepend owner initials before task text
- Tasks column: clicking a task opens the task edit modal; clicking anywhere else on the row goes to prospect detail
- At a Glance column: increase text contrast, remove lightning bolt icon

**B. Prospect Detail (`crm_prospect_detail.html`)**
- Delete the Quick Actions card (Add Task / Add Quick Note)
- Relationship Brief: persistent from disk, no loading spinner on page load
- Notes Log: remove author name input, auto-set from DEV_USER

**C. Org Detail (`crm_org_detail.html`)**
- Remove the Notes section (Section 4) entirely
- Move Contacts (Section 3) above the Relationship Brief (Section 2)
- Org Summary Card: keep only Type and Domain (already the case — verify no notes field leaks into the summary grid)

**D. Person Detail (`crm_person_detail.html`)**
- Remove the Person Brief section entirely (the card with "Synthesizing intelligence..." and the Update textarea)
- Keep only: Contact Info card (organization, email, phone, title) + Interaction History + Meeting Summaries + Email History

**E. Tasks Board (`tasks/tasks.html` + `tasks/tasks.js` + `tasks/tasks.css`)**
- Redesign as Kanban board grouped by **owner** (not by section)
- Oscar's tasks first, then other owners alphabetically
- Each task card shows: task text, associated prospect (org name), and urgency/priority
- All three fields (text, prospect, priority) are inline-editable on click
- Keep section info as a subtle label on each card, but the primary grouping is by owner

### Out of Scope
- New API endpoints (existing task PATCH/PUT APIs handle inline edits)
- Changes to crm_reader.py or brief persistence logic
- Changes to data files
- Mobile-specific redesign

## 3. Business Rules

- **Pipeline task initials**: Derive from `assigned_to` field. "Tony Avila" → "(TA)", "Oscar Vasquez" → "(OV)", "Zach Reisner" → "(ZR)". If only first name, use first letter + "·" (e.g., "Tony" → "(T·)"). If unassigned, no initials shown.
- **Pipeline task click**: The task text inside the tasks cell should be wrapped in a clickable element that opens `openPipelineTaskEdit()`. The rest of the row's `onclick` handler navigates to prospect detail as it does now. Use `event.stopPropagation()` on the task text click.
- **Pipeline at a glance**: Change the inline style from `color:#475569` to `color:#94a3b8` (matches the muted variable used elsewhere). Remove the `⚡` emoji prefix. Keep `font-style:italic`.
- **Prospect Detail brief**: The initial HTML of `#relationship-brief` should be a placeholder div (not the loading spinner). After `loadPageData()` fetches the GET brief API, `loadBrief(data)` either renders the saved brief or shows the "Generate Brief" button. No `brief-loading` class animation on initial load.
- **Prospect Detail notes**: Author is auto-set to `CURRENT_USER` JS constant (set from server config). The `submitNote()` function sends `author: CURRENT_USER` instead of reading from an input field.
- **Org Detail notes removal**: Delete the entire Section 4 (Notes card). The `renderNotes()` JS function, `submitNote()`, `openAddNoteForm()`, `closeAddNoteForm()`, and associated HTML/CSS can all be removed.
- **Org Detail section order**: After removal, page order is: Heading → Summary Card (Type + Domain) → Contacts → Brief → Prospects.
- **Person Detail simplification**: Remove the `#brief-card` div and all brief-related JS (`loadBrief()`, `refreshBrief()`, `showBriefPlaceholder()`, `showBriefLoading()`, `showBriefError()`, `submitPersonUpdate()`, `cancelUpdate()`). The Contact Info card (`#person-card`) should always be visible (remove `hidden` class by default or in JS immediately).
- **Tasks Board Kanban**: The API at `/tasks/api/tasks` returns tasks grouped by section. The JS must regroup them by `assigned_to` for display. Oscar's tasks come first (match "Oscar", "Oscar Vasquez", or empty/unassigned). Then other owners alphabetically.

## 4. Data Model / Schema Changes

None.

## 5. UI / Interface

### A. Pipeline List — Tasks Column

Current rendering (line 1716 in `crm_pipeline.html`):
```
<div class="tasks-cell">
  <span class="task-count-badge">+2</span>
  <span class="task-preview-text">Schedule meeting on 18th...</span>
</div>
```

New rendering:
```
<div class="tasks-cell">
  <span class="task-count-badge">+2</span>
  <span class="task-owner-initials">(TA)</span>
  <span class="task-preview-text clickable" onclick="openPipelineTaskEdit(this); event.stopPropagation();"
        data-task='${JSON.stringify(firstTask)}'>Schedule meeting on 18th...</span>
</div>
```

New CSS for `.task-owner-initials`:
```css
.task-owner-initials {
  color: #60a5fa;
  font-size: 11px;
  font-weight: 600;
  margin-right: 4px;
  flex-shrink: 0;
}
```

### B. Pipeline List — At a Glance Column

Current (line 1722):
```js
return `<span title="${escHtml(val)}" style="color:#475569;font-style:italic">⚡ ${escHtml(display)}</span>`;
```

New:
```js
return `<span title="${escHtml(val)}" style="color:#94a3b8;font-style:italic">${escHtml(display)}</span>`;
```

### C. Prospect Detail — See separate SPEC_prospect-detail-cleanup.md
(Already written and saved — covers Quick Actions deletion, brief persistence, notes form simplification.)

### D. Org Detail — Remove Notes, Reorder Sections

In `crm_org_detail.html`:

1. Delete Section 4 (Notes) entirely — the `<div class="card">` block from line ~388 to ~405
2. Move the Contacts card (Section 3, lines ~267–386) ABOVE the Org Brief card (Section 2, lines ~257–265)
3. In the `<script>` section, remove: `renderNotes()` function, `submitNote()`, `openAddNoteForm()`, `closeAddNoteForm()`, and the `renderNotes()` call from the init function
4. Remove `'Notes'` from the `EDITABLE_PROSPECT_FIELDS` array and from the org fields render config

### E. Person Detail — Remove Brief, Keep Contact Info Only

In `crm_person_detail.html`:

1. Delete the `#brief-card` div (lines ~415–437) — the Person Brief card with loading spinner and update textarea
2. Remove all brief-related JS functions
3. Remove brief-related CSS (`.brief-header`, `.brief-narrative`, `.brief-loading`, `.brief-ts`, `.update-area`, etc.)
4. The Contact Info card (`#person-card`) remains and should show: Organization (linked), Title, Email, Phone
5. Keep: Interaction History, Meeting Summaries, Email History sections unchanged

### F. Tasks Board — Kanban by Owner

Replace the current 3-column layout (Fundraising-Me / Fundraising-Team / Other Work) with a single-scroll Kanban grouped by owner.

Layout:
```
┌─────────────────────────────────────────────────────────────┐
│  Oscar Vasquez (12)                                    [+]  │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐   │
│  │ [Hi] Schedule follow-up call with Reid Spears        │   │
│  │      Texas PSF  ·  Fundraising - Me                  │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ [Med] Check in with Nigel Braidy                     │   │
│  │      Emirates NBD  ·  Fundraising - Me               │   │
│  └──────────────────────────────────────────────────────┘   │
│  ...                                                        │
├─────────────────────────────────────────────────────────────┤
│  Tony Avila (8)                                        [+]  │
├─────────────────────────────────────────────────────────────┤
│  ...                                                        │
├─────────────────────────────────────────────────────────────┤
│  Zach Reisner (4)                                      [+]  │
├─────────────────────────────────────────────────────────────┤
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘
```

Each task card shows:
- Priority badge (Hi/Med/Lo) — click to cycle
- Task text — click to open edit modal
- Prospect org name (if any) — links to prospect detail
- Section label (subtle, e.g., "Fundraising - Me") — informational only

Inline editable fields (click to edit):
- **Task text**: Click → inline text input, blur or Enter saves via PUT `/tasks/api/task/{section}/{index}`
- **Priority**: Click badge → cycles Hi→Med→Lo→Hi via PATCH `/tasks/api/task/{section}/{index}/priority`
- **Prospect (org)**: Click → dropdown of all orgs (from `/crm/api/orgs`), saves via PUT

Sort: Within each owner group, sort by priority (Hi first, then Med, then Lo).

## 6. Integration Points

- `GET /tasks/api/tasks` — returns all tasks by section (unchanged)
- `PUT /tasks/api/task/<section>/<index>` — updates task text, priority, org, assigned_to (unchanged)
- `PATCH /tasks/api/task/<section>/<index>/priority` — cycles priority (unchanged)
- `POST /tasks/api/task/<section>/<index>/complete` — marks complete (unchanged)
- `GET /crm/api/orgs` — returns org list for prospect dropdown (unchanged)
- `GET /crm/api/prospect/<offering>/<org>/brief` — returns saved brief (unchanged)
- `POST /crm/api/prospect/<offering>/<org>/add-note` — saves note (unchanged, client auto-sets author)

## 7. Constraints

- Do not modify `crm_reader.py` or `tasks_blueprint.py` API logic
- Do not modify any CRM data files
- Do not add new API endpoints
- Keep the task-edit-modal.js integration working on all pages that use it
- The existing task card action buttons (complete, delete, nudge email, edit) should all survive the Tasks Board redesign

## 8. Acceptance Criteria

### Pipeline List
- [ ] Tasks column shows owner initials in blue before task text, e.g., "(TA) Schedule meeting..."
- [ ] Clicking task text opens the task edit modal (not prospect detail)
- [ ] Clicking anywhere else on the row navigates to prospect detail
- [ ] At a Glance column text is `#94a3b8` (legible), italic, no lightning bolt emoji

### Prospect Detail
- [ ] Quick Actions card is gone
- [ ] Brief loads from disk without spinner; shows "Generate Brief" if none exists, "Refresh" if one does
- [ ] Notes Log has no author field — auto-uses current user
- [ ] All Quick Actions JS/CSS removed

### Org Detail
- [ ] Notes section is completely removed (HTML + JS)
- [ ] Contacts card appears before the Relationship Brief card
- [ ] Org Summary Card shows only Type and Domain

### Person Detail
- [ ] Person Brief section is completely removed (HTML + JS + CSS)
- [ ] Contact Info card shows organization, title, email, phone
- [ ] Interaction History, Meeting Summaries, Email History are unchanged

### Tasks Board
- [ ] Tasks grouped by owner, Oscar first
- [ ] Each card shows task text, prospect name, and priority badge
- [ ] Priority badge is clickable (cycles)
- [ ] Task text is clickable (opens edit modal)
- [ ] Prospect org links to prospect detail
- [ ] `python3 -m pytest app/tests/ -v` passes
- [ ] Feedback loop prompt has been run

## 9. Files Likely Touched

| File | Reason |
|------|--------|
| `app/templates/crm_pipeline.html` | Task initials, task click handler, at-a-glance contrast |
| `app/templates/crm_prospect_detail.html` | Delete QA card, fix brief, simplify notes (see SPEC_prospect-detail-cleanup.md) |
| `app/templates/crm_org_detail.html` | Remove Notes section, reorder Contacts above Brief |
| `app/templates/crm_person_detail.html` | Remove Person Brief section |
| `app/static/tasks/tasks.js` | Complete rewrite — Kanban by owner with inline editing |
| `app/static/tasks/tasks.css` | Updated styles for owner-grouped layout |
| `app/templates/tasks/tasks.html` | Minor — may need updated section constants |
| `app/delivery/crm_blueprint.py` | Ensure config includes `current_user` for prospect detail template |
