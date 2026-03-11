# Overwatch — Task Management Cleanup: Engineering Specs

**Prepared for:** Claude Code handoff
**Date:** 2026-03-06
**Scope:** Task card display, status field, inline status change, detail page, assignee + prospect selectors

---

## 1. Overview

Three areas of work:

1. **Strip sub-text from task cards** — context notes should not render on the board view
2. **Add a `status` field** to all tasks with a defined enum and visual treatment
3. **Inline status change** on cards (space-permitting) and a **full detail page** with assignee + prospect selectors backed by searchable dropdowns

All changes must be applied consistently everywhere tasks appear in the app (board view, pipeline, people pages, org pages, dashboard widgets).

---

## 2. Task Card Display Changes

### 2.1 Remove Sub-text / Context Notes from Cards

**Current behavior:** Each task card renders a secondary line of smaller gray text beneath the task title (e.g., "follow-up from 2/17 intro call", "key blocker for Rahn + Bodmer and other Swiss prospects", "awaiting Tony's approval on list").

**New behavior:** Task cards display **title only** (plus the colored tag pill if present). No sub-text, no notes, no secondary context lines rendered on the card surface.

**Where sub-text lives instead:** Sub-text / notes remain fully editable and visible inside the **Task Detail page** (see Section 4).

**Implementation note:** This is a display suppression only — do not delete the underlying `notes` / `context` field from the data model. Simply do not render it in card view.

---

## 3. Status Field

### 3.1 Data Model

Add a `status` field to the task schema:

```
status: enum
  - "new"         // default for newly created tasks
  - "open"        // acknowledged, not yet started
  - "in_progress" // actively being worked
  - "complete"    // done
```

**Default:** `"new"` on creation.

**Backward compatibility:** All existing tasks without a status should be migrated to `"open"` at deploy time.

### 3.2 Visual Treatment (Status Chips)

| Status | Label | Color |
|---|---|---|
| New | NEW | Blue (#3B82F6) |
| Open | OPEN | Gray (#6B7280) |
| In Progress | IN PROGRESS | Amber (#F59E0B) |
| Complete | COMPLETE | Green (#10B981) |

Render as a small pill/chip (all-caps label, rounded, filled or outlined — match existing tag pill style in the app).

---

## 4. Inline Status Change (Card Level)

### 4.1 When to Show

Show the inline status control **conditionally based on card width**:

- **Wide cards** (board columns ≥ 280px wide): show the status chip directly on the card with a click-to-change dropdown
- **Narrow cards** (< 280px): show only a small color-coded dot indicator; clicking the dot opens the dropdown

### 4.2 Interaction

- **Single click on chip or dot** → opens a compact dropdown with all four status options
- Selecting an option updates status immediately (optimistic UI — no save/cancel needed)
- Dropdown closes on selection or outside click
- No page navigation triggered by status chip interaction

### 4.3 Dropdown Design

Compact popover (not a full modal), anchored to the chip:

```
┌─────────────────┐
│ ○  New          │
│ ○  Open         │
│ ●  In Progress  │  ← current (highlighted)
│ ○  Complete     │
└─────────────────┘
```

Each row has the status color dot on the left. Current status is highlighted.

---

## 5. Task Detail Page

### 5.1 Trigger

Clicking anywhere on the task card **except** the inline status chip opens the Task Detail page (slide-over panel or full modal — match existing app pattern).

### 5.2 Fields on Detail Page

All fields are editable inline (click to edit / auto-save on blur):

| Field | Type | Notes |
|---|---|---|
| **Title** | Text input | Single line, required |
| **Status** | Dropdown | Same 4-value enum as Section 3 |
| **Assigned To** | Searchable dropdown | See Section 6 |
| **Prospect / Org** | Searchable dropdown | See Section 7 |
| **Notes / Context** | Rich text or multi-line text | This is where sub-text from cards lives |
| **Priority** | Dropdown | Hi / Med / Low — match existing system |
| **Due Date** | Date picker | Optional |
| **Created** | Timestamp | Read-only |
| **Last Updated** | Timestamp | Read-only |

### 5.3 Layout Sketch

```
┌─────────────────────────────────────────────────────────┐
│  [← Back]                               [Delete Task]   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Schedule call with Bob - offer talk to Brim...  │   │  ← editable title
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  Status       [● IN PROGRESS ▾]                         │
│  Priority     [● HI ▾]                                  │
│  Assigned To  [Oscar Vasquez ▾]    [search...]          │
│  Prospect     [Travelers Insurance ▾]  [search...]      │
│  Due Date     [Mar 17, 2026]                            │
│                                                         │
│  Notes                                                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │  multi-family office, very interested in Fund II │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  Created: Feb 28, 2026 · Updated: Mar 5, 2026           │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Assignee Selector

### 6.1 Data Source

Pull from the existing team/people list already in the app. The people visible in the board groupings (Anthony, Ian, Max, Oscar, Tony, Glenn, Mike, Nate, Paige, Truman, etc.) are the known set.

### 6.2 Component Behavior

- Text input with live search filter (client-side, no API call needed if list is small)
- Displays avatar initial + full name in dropdown rows
- Allows selection of one person (single-select)
- Selected person shows avatar + name as the field value
- Clearable (×) to unassign

### 6.3 Typeahead

Filter on first name, last name, or both as user types. Minimum 1 character to trigger filtering. Show all options when field is focused and empty.

---

## 7. Prospect / Org Selector

### 7.1 Data Source

Pull from the existing orgs/prospects list in the app (the colored tag pills visible on current cards — e.g., "Travelers Insurance", "Berkshire Hathaway", "Heritage Holdings", "Pressboro", etc.).

### 7.2 Component Behavior

- Text input with live search filter
- Displays org name (+ logo or color chip if available) in dropdown rows
- Single-select
- Selected org shows as colored pill matching existing tag style
- Clearable (×) to detach

### 7.3 Typeahead

Same rules as Assignee Selector. Filter on org name. If the org does not exist, optionally allow inline creation with a "+ Create [typed name]" row at the bottom of the dropdown.

---

## 8. Global Application Rule

> **These changes apply wherever tasks are rendered in the app.**

Known task surface areas to update:

- **Tasks board** (current view in screenshot)
- **Pipeline view** — tasks associated with deals
- **People page** — tasks listed under a specific person
- **Orgs page** — tasks listed under a specific org
- **Dashboard widgets** — any task list or task count widget
- **Search results** — if tasks appear in search

Each surface area must:
1. Suppress sub-text/notes on card display
2. Render the status chip (or dot, if narrow)
3. Support inline status change via chip click
4. Navigate to the detail page on card body click
5. Use the same Assignee and Prospect selector components (shared, not duplicated)

---

## 9. API / Backend Changes

If the app has a backend API:

- `PATCH /tasks/:id` — add `status` to the allowed update fields
- `GET /tasks` response — include `status` in the task object
- Migration: set `status = "open"` for all existing tasks where status is null

If using local state / a JSON store, apply equivalent changes to the schema and persistence layer.

---

## 10. Out of Scope (for this sprint)

- Bulk status change across multiple tasks
- Status-based filtering on the board
- Status history / audit log
- Automated status transitions (e.g., auto-complete on date)

These can be addressed in a follow-on sprint once the core model is in place.

---

## 11. Acceptance Criteria

- [ ] Task cards on all views show title and tag only — no sub-text visible
- [ ] All tasks have a status field defaulting to "New" on creation, "Open" for migrated tasks
- [ ] Status chip renders on card with correct color per status value
- [ ] Clicking the chip opens a 4-option inline dropdown; selection updates status without page reload
- [ ] Clicking card body opens detail page / slide-over
- [ ] Detail page exposes all fields in Section 5.2 as editable
- [ ] Assignee selector: searchable, single-select, clearable
- [ ] Prospect selector: searchable, single-select, clearable, optional inline create
- [ ] All task surfaces in the app apply the same rules (board, pipeline, people, orgs, dashboard)
- [ ] No data loss — notes/context field preserved in data model and visible in detail page
