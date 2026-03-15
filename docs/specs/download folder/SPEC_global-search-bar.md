# SPEC: Global Search Bar

**Project:** arec-crm (Overwatch)
**Date:** March 10, 2026
**Status:** Ready for implementation

---

## 1. Objective

Add a global search bar to the top navigation that lets users quickly find and navigate to any Prospect, Person, or Organization in the CRM. The search provides instant autocomplete results as the user types, with each result linking directly to its detail page. This eliminates the need to navigate to Pipeline/People/Orgs tabs and manually browse or filter.

---

## 2. Scope

### In Scope
- Search input field in the top nav bar (row 2), positioned to the right of the "Orgs" tab
- Client-side autocomplete dropdown showing up to 10 results
- Results sourced from three entity types: Prospects, People, Organizations
- Click/select navigates to the entity's detail page

### Out of Scope
- Full-text search across Notes, Next Action, or other fields (name-only matching)
- Server-side search endpoint (all filtering is client-side against data already loaded)
- Search history or recent searches
- Keyboard-only navigation beyond basic tab/enter (nice-to-have, not required)

---

## 3. Business Rules

### Matching
- Match against **name only** for all three entity types:
  - **Prospects:** match against the organization name on the prospect record
  - **People:** match against the person's name (as it appears in the People index)
  - **Orgs:** match against the organization name
- Matching is **case-insensitive**
- Minimum **2 characters** before showing results (avoid showing everything on single keystroke)

### Relevance Sorting (within the flat result list)
1. **Prefix matches first:** results where the typed text matches the beginning of the name rank above substring matches (e.g., typing "Trav" → "Travelers Insurance" ranks above "John Travers")
2. **Within each tier (prefix vs. substring), sort by entity priority:** Prospects → People → Orgs
3. **Within the same entity type, sort alphabetically** by name
4. **Maximum 10 results** displayed at any time — no "see more" link, just the top 10

### Prospect Deduplication
- A single organization may appear as a prospect under **multiple offerings** (e.g., Travelers Insurance in both "AREC Debt Fund II" and "Mountain House Refi")
- Each prospect-offering combination is a **separate result row**
- The same org also appears as a single Org result
- Example for "Travelers Insurance" with 2 offerings:
  1. **Travelers Insurance** AREC Debt Fund II ← prospect result
  2. **Travelers Insurance** Mountain House Refi ← prospect result
  3. Travelers Insurance ← org result

### Result Display Format
| Entity Type | Display Format |
|-------------|---------------|
| Prospect | **Org Name** (bold) + Offering Name (lighter/smaller text, right of name) |
| Person | **Person Name** (bold) + Org Name (lighter/smaller text, right of name). If no org association, name only. |
| Organization | Org Name (standard weight, no secondary text) |

### Navigation on Select
| Entity Type | Destination |
|-------------|-------------|
| Prospect | `/crm/prospect/<org_name>?offering=<offering_name>` (prospect detail page) |
| Person | `/crm/people/<person_name>` (people detail page) |
| Organization | `/crm/org/<org_name>` (organization detail page) |

---

## 4. Data Model / Schema Changes

None. All data already exists and is loaded by existing routes. The search bar operates client-side against data injected into the page.

---

## 5. UI / Interface

### 5.1 Search Input Placement

The search bar goes in **row 2 of the fixed two-row header**, to the right of the "Orgs" tab link. Layout of row 2 becomes:

```
[ Dashboard | Tasks | Pipeline | People | Orgs ]  [ 🔍 Search...          ]
```

- The search input is **right-aligned** within row 2
- Placeholder text: `Search...` with a magnifying glass icon (🔍) inside the input on the left
- Input width: approximately 200px default, **expands to 300px on focus** (smooth transition)
- Input styling: slightly rounded corners, subtle border, background slightly lighter than the nav bar (`rgba(255,255,255,0.1)` or similar), white/light placeholder text to match nav theme
- On mobile/narrow screens: the search input can wrap below the tabs or collapse to just the magnifying glass icon that expands on tap (implementer's discretion for responsive behavior, but desktop-first is fine)

### 5.2 Autocomplete Dropdown

Appears below the search input when there are matching results:

```
┌──────────────────────────────────────┐
│ 🔍 Trav                             │  ← input with typed text
├──────────────────────────────────────┤
│ Travelers Insurance  AREC Debt Fund II│  ← prospect (bold name + light offering)
│ Travelers Insurance  Mountain House   │  ← prospect
│ John Travers         Pacific RE Group │  ← person (bold name + light org)
│ Travelers Insurance                   │  ← org (no secondary text)
└──────────────────────────────────────┘
```

- Dropdown is absolutely positioned below the search input
- White background (`#ffffff`), subtle box shadow for depth
- Each row: 40px height, full-width hover highlight (`#f0f4ff` or similar light blue)
- Text layout per row:
  - Primary text (entity name): bold, `#1f2937`, left-aligned
  - Secondary text (offering or org): normal weight, `#9ca3af` (muted gray), smaller font size, separated by 2–3 em-spaces or right-aligned
- **No type labels or section headers** — it's a flat list, the visual weight and secondary text differentiate entity types
- Clicking a row navigates to the detail page (standard page navigation, not AJAX)
- Dropdown dismisses on: clicking outside, pressing Escape, clearing the input
- If no results match: show a single muted row: "No results found"

### 5.3 States

| State | Behavior |
|-------|----------|
| Empty/default | Input shows placeholder "Search...", no dropdown |
| Typing (< 2 chars) | No dropdown shown |
| Typing (≥ 2 chars, has matches) | Dropdown appears with up to 10 results |
| Typing (≥ 2 chars, no matches) | Dropdown shows "No results found" in muted text |
| Result selected | Navigate to detail page, clear input, close dropdown |
| Escape pressed | Close dropdown, clear input, blur the field |
| Click outside | Close dropdown (input retains text) |

### 5.4 Keyboard Support (nice-to-have)

- **Arrow Down/Up:** highlight next/previous result in dropdown
- **Enter:** navigate to highlighted result
- **Escape:** close dropdown

---

## 6. Integration Points

### Reads From
- **Prospects data:** the same prospect data already loaded for Pipeline views. Needs org name + offering name per prospect.
- **People data:** list of all people with name and org association. Already available from the People index.
- **Organizations data:** list of all org names. Already available from Orgs data.

### Implementation Approach
The search needs access to all three datasets on every page (since the nav is global). Two options:

**Option A (recommended): Inject search data via Jinja2 into a `<script>` block in the base template.**
- Add a lightweight route or template context processor that provides a JSON array of search entries
- Each entry: `{ name: "...", secondary: "...", type: "prospect|person|org", url: "..." }`
- Injected once on page load, filtered client-side as user types
- This keeps it simple — no additional API calls, no AJAX

**Option B: Dedicated search API endpoint.**
- `/crm/api/search?q=...` returns JSON results
- Requires debounced fetch on each keystroke
- More complex, unnecessary for the data volume in this CRM

**Go with Option A.** The total number of prospects + people + orgs is small enough (likely < 500 entries) that embedding the full search index in the page is fine.

### Writes To
Nothing. Search is read-only.

---

## 7. Constraints

1. **No new JS libraries.** Use vanilla JavaScript. No Fuse.js, no Algolia, no jQuery UI autocomplete.
2. **No new Python dependencies.** The search index is assembled from existing `crm_reader.py` data.
3. **Same CSS file.** Add styles to `crm.css`, not a new stylesheet.
4. **Global availability.** The search bar must appear on every CRM page, so the data injection and JS must live in the base template or a shared partial.
5. **Do not modify the existing tab/nav structure** beyond adding the search input to the right of "Orgs." Tab highlighting, spacing, and behavior must remain unchanged.
6. **Performance.** Filtering should feel instant. Use simple string matching — no regex needed. Run the filter on every `input` event (no debounce necessary for client-side filtering of < 500 items).

---

## 8. Acceptance Criteria

1. ✅ Search input appears in row 2 of the top nav, right of the "Orgs" tab, on every CRM page
2. ✅ Typing 2+ characters shows an autocomplete dropdown with up to 10 matching results
3. ✅ Results include Prospects (bold name + lighter offering), People (bold name + lighter org), and Orgs (name only)
4. ✅ A prospect appearing in multiple offerings shows as separate result rows
5. ✅ Prefix matches rank above substring matches; within each tier, Prospects sort before People sort before Orgs
6. ✅ Clicking a Prospect result navigates to `/crm/prospect/<org_name>?offering=<offering_name>`
7. ✅ Clicking a Person result navigates to `/crm/people/<person_name>`
8. ✅ Clicking an Org result navigates to `/crm/org/<org_name>`
9. ✅ "No results found" appears when no entities match the query
10. ✅ Dropdown dismisses on click outside, Escape, or result selection
11. ✅ Existing nav tabs (Dashboard, Tasks, Pipeline, People, Orgs) are visually and functionally unchanged
12. ✅ No new JS or Python libraries introduced
13. ✅ Feedback loop prompt has been run

---

## 9. Files Likely Touched

| File | Reason |
|------|--------|
| `app/delivery/crm_blueprint.py` | Add context processor or template global that provides search index JSON to all templates |
| `app/templates/crm/base.html` (or equivalent shared nav partial) | Add search input HTML to nav row 2; add `<script>` block with search index JSON and autocomplete JS |
| `app/static/crm/crm.css` | Styles for search input, dropdown, result rows, hover states, transitions |
| `app/static/crm/crm.js` | Autocomplete logic: input listener, filtering, dropdown rendering, navigation, keyboard support |
| `app/sources/crm_reader.py` | May need a helper function to produce the search index (list of all prospects with offering, all people with org, all orgs) — or this can be assembled directly in the blueprint |
