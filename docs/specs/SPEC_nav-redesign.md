# SPEC: Navigation Redesign

**Project:** arec-crm
**Date:** 2026-03-12
**Status:** Ready for implementation
**Priority:** Low (UI polish batch)
**Parallel group:** Can run simultaneously with Pipeline Polish, Prospect Detail, Tasks Page, Contact Enrichment specs

---

## 1. Objective

Redesign the top navigation bar to feel more polished and professional. Change the brand icon from a house to a bullseye/target, move the user name to the right with logout on hover, and center the main nav tabs (Pipeline, People, Orgs, Tasks).

## 2. Scope

**In scope:**
- Replace brand icon SVG in `_nav.html` with a bullseye/target icon (Lucide `target` icon)
- Restructure user menu: display name on right, logout appears on hover over the name
- Remove always-visible "Logout" link; show it as a dropdown/tooltip on hover
- Center-align the nav tabs row (Pipeline, People, Orgs, Tasks)
- Add "Tasks" tab to the nav tabs row linking to `/crm/tasks` (new page from separate spec)
- Keep Admin link visible for admin users (can remain in user hover menu or stay inline)

**Out of scope:**
- Creating the Tasks page itself (see SPEC_tasks-page.md)
- Changes to any page content below the nav
- Mobile responsiveness overhaul

## 3. Business Rules

- The "Logout" link must still be accessible — hidden behind a hover/click on the user's name is fine, but it must not require more than one interaction to reach.
- Admin badge/link should remain visible for admin users without requiring hover.
- The Tasks tab should link to `/crm/tasks`. If the route doesn't exist yet, the tab should still render (it'll 404 until the Tasks Page spec is implemented, which is fine for parallel development).

## 4. Data Model / Schema Changes

None.

## 5. UI / Interface

### Brand Bar (Row 1)
**Current:** House icon + "AREC CRM" on left. User name + Admin + Logout on right.
**New:**
- Left: Bullseye/target icon + "AREC CRM" text
- Right: User display name (clickable/hoverable). On hover, show a small dropdown with:
  - Admin link (if admin role)
  - Logout link

Use Lucide `target` icon (already loaded via CDN in `_nav.html`). Replace the inline SVG with:
```html
<i data-lucide="target" class="brand-icon"></i>
```
Then call `lucide.createIcons()` (already called in `icons.js`).

### Nav Tabs (Row 2)
**Current:** Pipeline | People | Orgs left-aligned, with search bar after them.
**New:** Pipeline | People | Orgs | Tasks centered in the row. Search bar stays on the right.

CSS approach: Make `.nav-tabs-inner` use flexbox with `justify-content: center` or use a three-column layout (empty left, tabs center, search right).

### User Menu Hover Dropdown
Simple CSS-only hover dropdown. No JS required:
```
.user-menu:hover .user-dropdown { display: block; }
```
Style the dropdown with the existing dark theme variables (`#1e293b` background, `#334155` border).

## 6. Integration Points

- Reads `g.user` (display_name, role) from Flask context — no changes needed
- Links to `/crm/tasks` (new route from SPEC_tasks-page.md)
- Links to `/admin/users` (existing)
- Links to `/.auth/logout` (existing)

## 7. Constraints

- Must use Lucide icon library (already loaded). Do NOT add new icon libraries.
- CSS changes scoped to `.brand-bar` and `.nav-tabs` classes in `crm.css`. Do not modify styles for page content.
- Keep the `{% if g.user %}` conditional logic intact.
- Do not remove the `search_index_json` script injection or search bar functionality.

## 8. Acceptance Criteria

- [ ] Brand bar shows a bullseye/target icon instead of house icon
- [ ] User name displayed on right side of brand bar
- [ ] Hovering over user name reveals dropdown with Logout (and Admin link if admin)
- [ ] Logout link is NOT visible by default — only on hover
- [ ] Nav tabs (Pipeline, People, Orgs, Tasks) are visually centered in the nav row
- [ ] Tasks tab links to `/crm/tasks`
- [ ] Search bar remains functional and positioned on the right
- [ ] All existing `active_tab` highlighting still works
- [ ] All 99 tests pass
- [ ] Feedback loop prompt has been run

## 9. Files Likely Touched

| File | Reason |
|------|--------|
| `app/templates/_nav.html` | Primary file — icon swap, user menu restructure, add Tasks tab, center tabs |
| `app/static/crm.css` | Nav-specific styles: user dropdown, centered tabs |
