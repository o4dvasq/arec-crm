# SPEC: Person Name Linking (App-Wide)

**Project:** arec-crm
**Date:** 2026-03-12
**Status:** Ready for implementation
**Priority:** Low (UI polish batch)
**Parallel group:** Run AFTER Nav Redesign, Pipeline Polish, Prospect Detail, Tasks Page, and Contact Enrichment specs (depends on their template changes being merged first)

---

## 1. Objective

Scan the entire app and ensure that anytime a person's name is displayed, clicking it navigates to that person's detail page (`/crm/people/<slug>`). This creates a consistent, app-wide pattern of clickable person names.

## 2. Scope

**In scope:**
- Audit every template for person name display
- Make person names clickable links to `/crm/people/<slug>` everywhere they appear:
  - Pipeline table (Primary Contact column)
  - Prospect detail page (Primary Contact, contacts list, notes author, task assignee)
  - Organization detail page (contacts list)
  - People list page (already linked — verify)
  - Tasks page (assignee column, if implemented)
  - Any other location where a person's name renders
- Add a shared CSS class for person name links (subtle styling — not disruptive)
- Handle the case where a person name doesn't have a matching person record (no link, or graceful fallback)

**Out of scope:**
- Creating new person records for unmatched names
- Changes to person detail page content itself
- Email/interaction history person linking

## 3. Business Rules

- **Name → slug resolution:** Person slugs are generated from names (e.g., "John Smith" → "john-smith"). The `load_all_persons()` function returns all persons with their slugs. Build a JS lookup table from this data.
- **Unmatched names:** If a displayed name doesn't match any known person, render it as plain text (no link). Do NOT show a broken link or error.
- **Case-insensitive matching:** "john smith", "John Smith", and "JOHN SMITH" should all resolve to the same person.
- **Partial names / initials:** If only initials are shown (e.g., "OV" in the tasks column), do NOT attempt to link them. Only link full names.

## 4. Data Model / Schema Changes

None.

## 5. UI / Interface

### Person Name Link Style
```css
.person-link {
  color: #60a5fa;
  text-decoration: none;
  cursor: pointer;
  transition: color 0.15s;
}
.person-link:hover {
  color: #93c5fd;
  text-decoration: underline;
}
```

Subtle blue link that matches the app's accent color. No bold, no background change — just a color shift.

### Implementation Approach

**Option A (Preferred): Server-side linking**
In each template, where a person name is rendered, wrap it in an `<a>` tag with the person's slug URL. This requires the backend to pass person slug data to each template.

**Option B: Client-side linking**
Add a JS function that runs on page load, finds all elements with a `data-person-name` attribute, looks up the slug from a preloaded person index, and wraps the text in a link. This is less invasive to templates but requires the search index (already injected as `window.SEARCH_INDEX`).

**Recommendation:** Use Option B (client-side) to minimize template changes and avoid conflicts with other specs that are modifying the same templates. The `SEARCH_INDEX` already contains person entries with slugs and URLs.

### Client-Side Implementation
In `crm.js`, add a function:
```javascript
function linkifyPersonNames() {
  const personIndex = (window.SEARCH_INDEX || [])
    .filter(e => e.type === 'person')
    .reduce((map, e) => {
      map[e.name.toLowerCase()] = e.url;
      return map;
    }, {});

  document.querySelectorAll('[data-person-name]').forEach(el => {
    const name = el.textContent.trim();
    const url = personIndex[name.toLowerCase()];
    if (url && !el.closest('a')) {
      const link = document.createElement('a');
      link.href = url;
      link.className = 'person-link';
      link.textContent = name;
      el.replaceWith(link);
    }
  });
}

document.addEventListener('DOMContentLoaded', linkifyPersonNames);
```

Then, in each template, add `data-person-name` attributes to elements displaying person names. This is a lightweight change to each template.

## 6. Integration Points

- Uses `window.SEARCH_INDEX` (already injected by `_nav.html` context processor) for person name → URL resolution
- Links to `/crm/people/<slug>` (existing routes)
- The `linkifyPersonNames()` function in `crm.js` is the shared implementation

## 7. Constraints

- **Run this spec AFTER the other 5 polish specs.** It touches all templates and should be the final pass to avoid merge conflicts.
- Use `data-person-name` attribute approach to minimize invasiveness.
- Do not break any existing click handlers (e.g., pipeline row click → prospect detail, task click → task edit).
- Person links should NOT interfere with table row click handlers. Use `event.stopPropagation()` on person link clicks if needed.
- The `SEARCH_INDEX` is already loaded on every page via `_nav.html`. No additional data fetching required.

## 8. Acceptance Criteria

- [ ] Person names are clickable links to person detail pages on the pipeline view
- [ ] Person names are clickable on prospect detail page (Primary Contact, contacts, etc.)
- [ ] Person names are clickable on organization detail page
- [ ] Person names are clickable on the tasks page (if implemented)
- [ ] Clicking a person name navigates to `/crm/people/<slug>`
- [ ] Unrecognized names render as plain text (no broken links)
- [ ] Person links have consistent, subtle styling (`.person-link` class)
- [ ] Person link clicks do not trigger parent row click handlers
- [ ] All 99+ tests pass
- [ ] Feedback loop prompt has been run

## 9. Files Likely Touched

| File | Reason |
|------|--------|
| `app/static/crm.js` | Add `linkifyPersonNames()` function + `.person-link` click handler |
| `app/static/crm.css` | Add `.person-link` styles |
| `app/templates/crm_pipeline.html` | Add `data-person-name` to Primary Contact cells |
| `app/templates/crm_prospect_detail.html` | Add `data-person-name` to contact names, task assignees, note authors |
| `app/templates/crm_org_detail.html` | Add `data-person-name` to contact names |
| `app/templates/crm_tasks.html` | Add `data-person-name` to assignee column (if spec implemented) |
| `app/templates/crm_people.html` | Verify names are already linked (should be) |
