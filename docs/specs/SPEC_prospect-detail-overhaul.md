# SPEC: Prospect Detail Page Overhaul

**Project:** arec-crm
**Date:** 2026-03-12
**Status:** Ready for implementation
**Priority:** Low (UI polish batch)
**Parallel group:** Can run simultaneously with Nav Redesign, Pipeline Polish, Tasks Page, Contact Enrichment specs

---

## 1. Objective

Clean up and enhance the prospect detail page by removing redundant UI elements, fixing bugs, improving the notes/tasks UX, adding a "Scan Email" button for deep email scanning + auto brief refresh, and stripping all markdown formatting from displayed content.

## 2. Scope

**In scope:**
1. Remove the 2nd action box (Add Task / Quick Note box — redundant with inline actions)
2. Bug fix: "Brief generation unavailable" error when clicking Refresh Brief
3. Notes log: remove the "Name" field from the Add Note form. Make "Add Note" button visually match "Add a Task" button
4. Task click behavior: clicking on a task opens task detail/edit (modal or inline). Clicking anywhere else on the prospect card navigates to pipeline detail.
5. "Scan Email" button: triggers a 60-day deep email scan for this prospect's org, then auto-refreshes the relationship brief
6. Bug fix: strip all markdown symbols from displayed text (e.g., `**Stonehill Capital**` should show as `Stonehill Capital`)

**Out of scope:**
- Changes to the navigation bar (see SPEC_nav-redesign.md)
- Changes to the pipeline list view (see SPEC_pipeline-polish.md)
- Creating a standalone Tasks page (see SPEC_tasks-page.md)
- Person/contact enrichment (see SPEC_contact-enrichment.md)

## 3. Business Rules

- **Brief generation bug:** Investigate why the brief generation shows "unavailable". Likely causes: (a) missing ANTHROPIC_API_KEY in environment, (b) the brief synthesis route returns an error that's caught silently, (c) the frontend JS doesn't properly call the refresh endpoint. Debug and fix.
- **Scan Email:** The scan should look back 60 days for emails matching this prospect's organization domain(s). Use the existing `crm_graph_sync` auto-capture infrastructure. After the scan completes, automatically trigger a relationship brief refresh.
- **Markdown stripping:** Apply globally within the prospect detail page. All text rendered from database fields (at_a_glance, narrative, notes, task descriptions) must be cleaned of `**`, `*`, `__`, `_` markdown wrappers before display.
- **Notes:** The "Name" field was used to attribute who wrote the note, but with multi-user auth, the note author should be automatically set to `g.user.display_name` (or `g.user.email`). Remove the Name input field entirely. Auto-populate from the logged-in user.

## 4. Data Model / Schema Changes

None. The `prospect_notes` table already has a structure that can accommodate auto-attribution. If there's a `created_by` or `author` column, use it. If not, the existing `name` field can be auto-populated server-side from `g.user.display_name`.

## 5. UI / Interface

### Remove 2nd Action Box
**Current:** There is a secondary card/box below the main prospect card with "Add Task" and "Quick Note" shortcuts.
**New:** Remove this entire box. The "Add Note" and "Add Task" actions live within their respective sections (Notes section and Tasks section).

### Notes Section
**Current:** "Add Note" form has a Name field (text input) and a Note field (textarea).
**New:**
- Remove the Name field entirely. Author is auto-set from logged-in user.
- "Add Note" button: style it identically to the "Add a Task" button (same `.btn` class, same size, same colors).
- Note form: just a textarea + submit button, no name input.

### Task Click Behavior
**Current:** Clicking a task item may or may not do anything specific.
**New:**
- Clicking on a task description text → opens the task edit modal (already exists as `task-edit-modal.css` is loaded)
- The task edit modal should allow editing: description, priority, assigned_to, due_date, status
- If a task edit modal doesn't exist yet, create one similar to the inline edit pattern used elsewhere

### Scan Email Button
**New element** in the prospect detail header (next to "Refresh Brief" button):
- Button label: "Scan Email"
- Icon: Lucide `mail-search` or `scan`
- On click: POST to `/crm/api/prospect/<offering>/<org>/scan-email`
- Show loading spinner while scanning
- On completion, auto-trigger brief refresh
- Display scan results summary (e.g., "Found 12 emails, 3 new interactions logged. Brief updated.")

### Markdown Stripping
Apply `stripMarkdown()` to all text rendering in the template:
- At a Glance bullets
- Relationship Brief narrative
- Notes content
- Task descriptions
- Org name in header (if rendered from a field that might contain markdown)

Use a Jinja filter or apply via JavaScript on page load.

### Brief Generation Bug Fix
Debug the "Brief generation unavailable" message. Check:
1. Does the `/crm/prospect/<offering>/<org>/refresh-brief` endpoint exist and work?
2. Is the AJAX call in the template JS correct (URL, method, CSRF)?
3. Does the server-side brief synthesis have access to ANTHROPIC_API_KEY?
4. Is there an error in `brief_synthesizer.py` or `relationship_brief.py` that's being swallowed?

Fix the root cause. If the API key is missing in dev, provide a clear error message instead of "unavailable".

## 6. Integration Points

- **Scan Email** calls into `crm_graph_sync.run_auto_capture()` or a variant that accepts a date range parameter (60 days back) and filters to a specific org's domains
- **Brief refresh** calls existing `brief_synthesizer.call_claude_brief()` after scan completes
- **Notes** POST to existing `/crm/api/notes` endpoint — modify to auto-populate author from `g.user`
- **Task edit** uses existing `/crm/api/tasks/<id>` PUT endpoint (or create one if missing)
- The `stripMarkdown()` JS utility should be the same function added in `crm.js` by the Pipeline Polish spec. If that spec hasn't run yet, add it here.

## 7. Constraints

- All CSS changes stay within the `crm_prospect_detail.html` `<style>` block. Do NOT modify `crm.css` for prospect-specific styles.
- Scan Email must work with the existing Graph API token infrastructure. If the current user doesn't have `graph_consent_granted=True`, show a message: "Email scanning requires Graph API consent. Contact an admin."
- Brief refresh after scan should be async — don't block the UI. Show a spinner, then update the brief section when done.
- New routes added to `crm_blueprint.py` should include `@login_required` decorator.

## 8. Acceptance Criteria

- [ ] 2nd action box (Add Task / Quick Note) is removed from prospect detail page
- [ ] "Brief generation unavailable" bug is fixed — brief refresh works
- [ ] Notes form has no Name field — author auto-populated from logged-in user
- [ ] "Add Note" button styled identically to "Add a Task" button
- [ ] Clicking a task opens a task edit view/modal
- [ ] "Scan Email" button visible on prospect detail page
- [ ] Scan Email triggers a 60-day lookback email scan for the prospect's org
- [ ] After scan, relationship brief auto-refreshes
- [ ] No markdown symbols (`**`, `*`, `__`, `_`) visible in any displayed text
- [ ] All 99 tests pass
- [ ] Feedback loop prompt has been run

## 9. Files Likely Touched

| File | Reason |
|------|--------|
| `app/templates/crm_prospect_detail.html` | Primary — remove action box, notes form, task clicks, scan button, markdown strip |
| `app/delivery/crm_blueprint.py` | New route: `/crm/api/prospect/<offering>/<org>/scan-email`. Fix brief refresh route if broken. Modify notes POST to auto-populate author. |
| `app/static/crm.js` | Add `stripMarkdown()` if not already present (shared with Pipeline Polish spec) |
| `app/sources/crm_graph_sync.py` | May need a targeted scan function that accepts org domains + date range |
| `app/sources/crm_db.py` | Verify `save_prospect_note()` signature — may need to accept author from caller |
| `app/briefing/brief_synthesizer.py` | Debug brief generation issue |
| `app/sources/relationship_brief.py` | Debug brief generation issue |
