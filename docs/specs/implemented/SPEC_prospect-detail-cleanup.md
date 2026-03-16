SPEC: Prospect Detail Page Cleanup
Project: arec-crm | Branch: main | Date: 2026-03-15
Status: Ready for implementation

---

## 1. Objective

Clean up the Prospect Detail page (`crm_prospect_detail.html`) to remove redundant UI, make the Relationship Brief persistent and non-regenerating on page load, and simplify the Notes Log form by removing the author name field. These are UX polish fixes — no new features, no new routes.

## 2. Scope

### In Scope
- Delete the "Quick Actions" card (Add Task / Add Quick Note pill toggle box)
- Make the Relationship Brief load from disk on page load with no loading spinner; show a "Generate Brief" button if no brief exists yet, and a "Refresh" button if one does
- Remove the author name input from the Notes Log form; auto-set author to current user (`DEV_USER` env var, passed via config)
- Remove all JS functions related to the deleted Quick Actions card

### Out of Scope
- Changes to the brief synthesis API or Claude prompt
- Changes to any other page (pipeline, org detail, people)
- New features or new API endpoints
- Changes to crm_reader.py or brief persistence logic (already works correctly)

## 3. Business Rules

- The Relationship Brief must persist across page loads. Once generated via the "Generate Brief" or "Refresh" button, the brief narrative and "At a Glance" line are saved to `crm/briefs.json` via `save_brief()`. On next page load, `load_saved_brief()` returns the cached brief — no AI call happens.
- The "Refresh" button triggers a new AI synthesis (POST to brief API). This is the only way to regenerate.
- If no brief has ever been generated, show a static placeholder ("No relationship brief yet.") with a "Generate Brief" button. Do NOT show a loading spinner.
- Notes Log author is always the current DEV_USER. The server already knows this from `g.user` / env var. The client sends the author automatically — no user-facing author field needed.
- The Active Tasks card already has its own "+ Add Task" button with a modal. The Quick Actions card's "Add Task" tab was redundant. The Quick Actions card's "Add Quick Note" tab is replaced by the Notes Log's own form (which is being simplified).

## 4. Data Model / Schema Changes

None.

## 5. UI / Interface

### A. Delete Quick Actions Card
Remove the entire card (HTML id `quick-actions-card`, lines ~912–946 in current template). This includes:
- The pill toggle (`Add Task` / `Add Quick Note`)
- The inline task form with priority toggle and assignee dropdown
- The inline note form with author dropdown

### B. Relationship Brief — No Auto-Load Spinner
Current behavior: On page load, the brief card shows `<div class="brief-loading"><div class="loading-pulse"></div><span>Synthesizing intelligence...</span></div>` while the GET `/brief` API loads. This is misleading — the GET never synthesizes, it just reads from disk.

New behavior:
- The initial HTML inside `#relationship-brief` should be empty or show a minimal "Loading..." text (not "Synthesizing intelligence...")
- `loadBrief(data)` is called after the GET returns. If `saved_brief.narrative` exists → render it immediately with the Refresh button and "Last refreshed" timestamp. If no saved brief → show the placeholder with "Generate Brief" button.
- No loading pulse animation on page load.

### C. Notes Log — Remove Author Field
Current form (lines ~1058–1071):
```
[author name input] [textarea] [Add Note button]
```

New form:
```
[textarea] [Add Note button]
```

- Remove the `<input id="note-author">` element and its CSS class `notes-input-author`
- The `submitNote()` JS function should send `author: CURRENT_USER` (a JS constant set from server-side config) instead of reading from the removed input
- Add a JS constant at the top: `const CURRENT_USER = {{ config.current_user | tojson }};` (the Flask route already has `config` in context; ensure `current_user` is set from `g.user` or `os.environ.get('DEV_USER', 'Oscar Vasquez')`)

## 6. Integration Points

- `GET /crm/api/prospect/<offering>/<org>/brief` — unchanged, already returns `saved_brief` from `briefs.json`
- `POST /crm/api/prospect/<offering>/<org>/brief` — unchanged, generates + persists brief
- `POST /crm/api/prospect/<offering>/<org>/add-note` — unchanged, still expects `{author, text}` in body; client now auto-fills author
- `POST /crm/api/tasks` — unchanged; the Active Tasks card's "+ Add Task" button (which opens the modal) is preserved
- `load_crm_config()` — needs to include `current_user` key in returned dict (or it may already be there; verify)

## 7. Constraints

- Do not modify `crm_reader.py`
- Do not modify any CRM data files
- Do not change URL patterns or API contracts
- Do not modify the brief synthesis prompt or Claude API call
- Keep all other sections of the page intact (Prospect Card, Active Tasks, Contacts, Interaction History, Meeting Summaries, Upcoming Meetings, Email History)
- Preserve the task-edit-modal.js import and its global config variables at the bottom of the template

## 8. Acceptance Criteria

- [ ] Quick Actions card (`#quick-actions-card`) is completely removed from HTML and JS
- [ ] Page loads with no "Synthesizing intelligence..." spinner
- [ ] If a brief exists in `briefs.json`, it renders immediately on page load with narrative text, "Last refreshed" date, and a "Refresh" button
- [ ] If no brief exists, a static placeholder with "Generate Brief" button is shown (no spinner, no animation)
- [ ] Clicking "Refresh" / "Generate Brief" calls POST, shows loading state, then renders the new brief
- [ ] Notes Log form has no author/name input field — just a textarea and "Add Note" button
- [ ] Submitting a note auto-sets author to the current user (DEV_USER)
- [ ] Notes still appear in the log with correct author and timestamp after submission
- [ ] All Quick Actions JS functions removed: `switchQA()`, `setPriority()`, `onQaTaskInput()`, `onQaNoteInput()`, `onQaTaskKey()`, `onQaNoteKey()`, `submitQuickTask()`, `submitQuickNote()`, `qaCurrentPriority` variable
- [ ] All Quick Actions CSS removed: `.quick-actions-section`, `.quick-actions-toggle`, `.task-form`, `.priority-toggle`, `.qa-note-author-select`, `@keyframes taskFlash`, `.task-card-flash`
- [ ] `python3 -m pytest app/tests/ -v` passes
- [ ] Feedback loop prompt has been run

## 9. Files Likely Touched

| File | Reason |
|------|--------|
| `app/templates/crm_prospect_detail.html` | All three changes: delete QA card, fix brief initial state, simplify notes form, remove dead JS/CSS |
| `app/delivery/crm_blueprint.py` | Ensure `config` dict passed to template includes `current_user` |
| `app/delivery/dashboard.py` | Possibly — verify `load_crm_config()` includes user info, or add it in the route |
