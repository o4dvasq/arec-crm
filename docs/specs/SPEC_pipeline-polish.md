# SPEC: Pipeline View Polish

**Project:** arec-crm
**Date:** 2026-03-12
**Status:** Ready for implementation
**Priority:** Low (UI polish batch)
**Parallel group:** Can run simultaneously with Nav Redesign, Prospect Detail, Tasks Page, Contact Enrichment specs

---

## 1. Objective

Polish the pipeline list view for better readability. Make the "At a Glance" text lighter and allow it to wrap to 2 lines, widen the Tasks column, and show assignee initials in parentheses after each task.

## 2. Scope

**In scope:**
- Adjust "At a Glance" column styling: lighter font color/weight, allow word wrap to max 2 rows with ellipsis overflow
- Widen the Tasks column and show assignee initials (e.g., `Follow up with LP (OV)`)
- Strip any markdown formatting symbols (`**`, `*`, `_`, etc.) from displayed text in the pipeline table (at_a_glance, notes, tasks)

**Out of scope:**
- Changes to the nav bar (see SPEC_nav-redesign.md)
- Changes to prospect detail page (see SPEC_prospect-detail-overhaul.md)
- Adding/removing columns from the pipeline table
- Changes to fund summary bar or filter bar

## 3. Business Rules

- Assignee initials are derived from the `assigned_to` field on the task. Extract first letter of first name + first letter of last name. If `assigned_to` is empty/null, show no initials.
- At a glance text should show a maximum of 2 lines (roughly ~120 chars depending on column width). Overflow is hidden with ellipsis.
- Markdown symbols to strip: `**`, `*`, `__`, `_` (bold/italic wrappers). Do NOT strip hyphens or other punctuation that might be legitimate content.

## 4. Data Model / Schema Changes

None.

## 5. UI / Interface

### At a Glance Column
**Current:** Single line, truncated, same weight as other text, can be hard to read.
**New:**
- Font color: `#94a3b8` (muted) instead of `#cbd5e1` (brighter)
- Font weight: 400 (normal) instead of any bold
- Font size: 12px (slightly smaller than the 13px body text)
- Line clamp: 2 lines max using `-webkit-line-clamp: 2` with `overflow: hidden`
- Strip markdown before display

CSS:
```css
.at-glance-cell {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 400;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.4;
  max-width: 300px;
  white-space: normal;
}
```

### Tasks Column
**Current:** `max-width: 250px`, shows task text only, truncated to single line.
**New:**
- Increase `max-width` to `350px`
- After each task description, append assignee initials in parens: `Follow up with LP (OV)`
- Keep the task count badge behavior

The pipeline template already renders tasks via JavaScript. The task data comes from the `tasks` field on each prospect row. Modify the rendering to append initials.

### Markdown Stripping
Add a JS utility function (or Jinja filter) that strips markdown bold/italic markers:
```javascript
function stripMarkdown(text) {
  if (!text) return '';
  return text.replace(/\*\*(.+?)\*\*/g, '$1')
             .replace(/\*(.+?)\*/g, '$1')
             .replace(/__(.+?)__/g, '$1')
             .replace(/_(.+?)_/g, '$1');
}
```

Apply this to at_a_glance and task text in the pipeline table render.

## 6. Integration Points

- Reads prospect data from existing `/crm` pipeline route (no route changes)
- Task data already includes `assigned_to` field from `get_all_prospect_tasks()` — verify this is passed to the template
- If `assigned_to` is not currently sent to the pipeline template, add it to the task data in `crm_blueprint.py` pipeline route

## 7. Constraints

- All CSS changes must be within `crm_pipeline.html` `<style>` block or clearly scoped classes. Do NOT modify `crm.css` for pipeline-specific styles (the pipeline template has its own extensive `<style>` block).
- Markdown stripping should be a reusable function in `crm.js` (it will be needed by other specs too).
- Do not change the column order or remove any existing columns.

## 8. Acceptance Criteria

- [ ] At a Glance text in pipeline table is lighter (muted color, normal weight, 12px)
- [ ] At a Glance text wraps to maximum 2 lines with ellipsis on overflow
- [ ] Tasks column is wider (350px max-width)
- [ ] Each task in the Tasks column shows assignee initials in parens (e.g., `(OV)`)
- [ ] Tasks with no assignee show no initials
- [ ] No markdown bold/italic symbols visible in at_a_glance or task text
- [ ] Pipeline table still sorts, filters, and inline-edits correctly
- [ ] All 99 tests pass
- [ ] Feedback loop prompt has been run

## 9. Files Likely Touched

| File | Reason |
|------|--------|
| `app/templates/crm_pipeline.html` | Primary — At a Glance styling, Tasks column width, initials rendering, markdown strip |
| `app/static/crm.js` | Add reusable `stripMarkdown()` utility function |
| `app/delivery/crm_blueprint.py` | May need to include `assigned_to` in task data sent to pipeline template (verify first) |
