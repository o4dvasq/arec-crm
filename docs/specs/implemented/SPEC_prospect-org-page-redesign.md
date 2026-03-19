SPEC: Prospect & Org Detail Page Redesign | Project: arec-crm | Date: 2026-03-19 | Status: Ready for implementation

---

## 1. Objective

Redesign the Prospect Detail and Org Detail pages to establish clear ownership boundaries between prospect-level and org-level data. Each page uses color-coded card sidebars to signal whether a section is native (editable here) or cross-referenced (lives on the other page):

- **Green left-border:** Native section — this data belongs to and is editable on this page.
- **Blue right-border:** Cross-reference section — this data lives on the other entity's page. Read-only here, with a navigation link to the owning page.

Additionally: split the current "Relationship Brief" into two distinct briefs — a focused **Prospect Brief** (offering-specific status) and an **Org Brief** (comprehensive relationship narrative) — and formalize meetings and emails as org-owned data displayed on both pages.

---

## 2. Scope

### In Scope

- Restructure Prospect Detail page layout and card order
- Restructure Org Detail page layout and card order
- Add context-dependent color-coded sidebars (green left = native, blue right = cross-reference)
- Add a new "Prospect Brief" section (short, offering-specific status summary)
- Move "Relationship Brief" → rename to "Org Brief" (org-owned, displayed read-only on prospect page)
- Move contacts display to org-owned card on prospect page (read-only)
- Add prospect summary cards to org page (one per offering, with links)
- Formalize meetings and emails as org-owned (displayed on both pages)
- Add org-owned Notes Log as a standalone card on org page (remove Notes from org top card)
- Prospect-owned Notes Log stays on prospect page
- Remove Edit Prospect, Edit Org, and Scan Email buttons from prospect detail header
- Standardize Add Note button styling across both pages

### Out of Scope

- Changes to the brief synthesis AI prompt or Claude API contract
- Changes to the pipeline list view or pipeline card layout
- New API endpoints for brief generation (reuse existing endpoints)
- Changes to how meetings or emails are stored in JSON (already org-keyed)
- Changes to People list/detail pages
- Mobile-specific layout (current responsive behavior is acceptable)

---

## 3. Business Rules

### Ownership Model

| Data | Owner | Editable on | Displayed on |
|------|-------|-------------|--------------|
| Stage, Target, Closing, Urgent, Assigned To | Prospect | Prospect Detail | Prospect Detail (native) + Org (cross-ref) |
| Primary Contact (pointer) | Prospect | Prospect Detail | Prospect Detail (native) + Org (inside prospect cross-ref card) |
| Type, Domain, Aliases | Org | Org Detail | Org Detail (native) + Prospect (cross-ref) |
| Contacts (people) | Org | Org Detail | Org Detail (native) + Prospect (cross-ref) |
| Prospect Brief | Prospect | Prospect Detail (refresh) | Prospect Detail only |
| Org Brief | Org | Org Detail (refresh) | Org Detail (native) + Prospect (cross-ref) |
| Prospect Notes Log | Prospect | Prospect Detail | Prospect Detail only |
| Org Notes Log | Org | Org Detail | Org Detail only |
| Meeting Summaries | Org | N/A (auto-captured) | Both pages (native on org, cross-ref on prospect) |
| Email History | Org | N/A (auto-captured) | Both pages (native on org, cross-ref on prospect) |
| Active Tasks | Prospect | Prospect Detail | Prospect Detail only |
| Interaction History | Prospect | Prospect Detail | Prospect Detail only |

### Primary Contact is a Pointer, Not a Copy

All contacts (people) live on the Org. There is exactly one set of people per org, managed in `contacts_index.md` and `contacts/*.md`. The prospect does NOT store its own contacts — it only stores a **Primary Contact identifier** (a name or slug) that references one of the org's contacts. This is a tag/pointer, not a separate record.

On Prospect Detail, the Primary Contact dropdown should be populated from the org's contacts list (fetched via `get_contacts_for_org`). Different prospects under the same org may each designate a different primary contact (e.g., UTIMCO Fund II vs. Mountain House may have different point people). In most cases they'll be the same person, but the flexibility must exist at the prospect level.

### Prospect Brief (new)

- Short, focused summary of the current state of this specific offering for this org.
- Content: most recent outreach, next planned meeting/action, current stage context, any blockers.
- Stored in `crm/briefs.json` under a new key format: `prospect_brief:{offering}:{org}` (distinct from the existing `prospect:{offering}:{org}` key used for the old relationship brief).
- Same JSON contract: `{narrative, at_a_glance, generated_at}`.
- Displayed ONLY on Prospect Detail, not on Org Detail.

### Org Brief (replaces current "Relationship Brief")

- Comprehensive relationship narrative at the org level.
- Already exists via the `synthesize-org-brief` endpoint and `org_brief:{org}` key in `briefs.json`.
- Displayed on Org Detail (native, refreshable) AND on Prospect Detail (cross-reference, read-only, no refresh button).

### Color Coding Convention

Color coding is **context-dependent**, not tied to a specific entity type:

- **Green left-border (4px solid #22c55e):** "You're in the right place." This section is native to this page. Data is editable here (where applicable).
- **Blue right-border (4px solid #2563eb):** "This lives somewhere else." This section is a cross-reference from the other entity's page. Data is read-only here, with a navigation badge/link to the owning page.

On Prospect Detail: the prospect card gets green (native), the org info card gets blue-right (cross-ref). On Org Detail: the org card gets green (native), the prospect summary cards get blue-right (cross-ref).

### Cross-Reference Badges

Cross-reference cards (blue right-border) include a small navigation badge in the card header:

- On Prospect Detail, org-owned cross-ref cards: badge with blue dot + `From Org →` linking to `/crm/org/{org}/edit`.
- On Org Detail, prospect cross-ref cards: badge with blue dot + `View Prospect →` linking to `/crm/prospect/{offering}/{org}/detail`.

The blue dot in the badge visually ties to the blue right-border, reinforcing the "go there" affordance.

---

## 4. Data Model / Schema Changes

### New brief key in briefs.json

Add a new key format for prospect-specific briefs:

```
"prospect_brief:{offering}:{org}": {
  "narrative": "...",
  "at_a_glance": "...",
  "generated_at": "2026-03-19T..."
}
```

The existing keys remain:
- `prospect:{offering}:{org}` — legacy relationship brief (migrate to org brief if no org brief exists)
- `org_brief:{org}` — org-level brief (already exists)

### New: Org Notes in prospect_notes.json

Add org-level notes alongside prospect notes. Key format:

```
"org:{org}": [
  {"ts": "2026-03-19T...", "user": "oscar", "text": "..."}
]
```

Existing prospect notes key format unchanged: `"{offering}:{org}"`.

### crm_reader.py additions

```python
def load_org_notes(org: str) -> list[dict]:
    """Load org-level notes from prospect_notes.json under key 'org:{org}'."""

def save_org_note(org: str, user: str, text: str) -> dict:
    """Append a note to org-level notes log. Returns the new note dict."""
```

### New API endpoint for Prospect Brief

```
POST /crm/api/prospect/<offering>/<org>/prospect-brief
```

Triggers synthesis of a short, offering-specific brief. Uses a focused prompt emphasizing recent activity and next steps for this specific offering only.

```
GET /crm/api/prospect/<offering>/<org>/prospect-brief
```

Returns cached prospect brief from `briefs.json` under `prospect_brief:{offering}:{org}`.

### New API endpoints for Org Notes

```
GET  /crm/api/org/<name>/notes      → returns org notes list
POST /crm/api/org/<name>/notes      → appends a new org note
```

---

## 5. UI / Interface

### A. Prospect Detail Page — New Layout (top to bottom)

#### 1. Header
- Org name as h1, offering subtitle below.
- "← Back to Pipeline" breadcrumb link.
- **Remove:** Edit Prospect, Edit Org, and Scan Email buttons. These are no longer needed — prospect fields are inline-editable directly on the card, and org editing happens on the org page via the cross-reference badge.

#### 2. Prospect Card (GREEN left-border — native)
- **Fields:** Stage, Assigned To, Target, Closing, Primary Contact, Last Touch, Urgent badge.
- **Primary Contact** is a dropdown populated from the org's contacts list (fetched via `get_contacts_for_org`). It stores a pointer (name/slug) — NOT a separate contact record.
- Remove: Org Type (moves to org info card below).
- All fields remain inline-editable as today.
- CSS: `border-left: 4px solid #22c55e;`

#### 3. Org Info Card (BLUE right-border — cross-reference, read-only)
- **Fields:** Type, Domain.
- **Contacts sub-section:** List of contacts (name, role, email) — read-only display, no edit controls.
- Header badge: blue dot + `From Org →` linking to `/crm/org/{org}/edit`.
- CSS: `border-right: 4px solid #2563eb;` (NO left border)
- None of the fields are editable on this page. Clicking the badge navigates to org detail for editing.

#### 4. Prospect Brief Card (GREEN left-border — native)
- New section. Header: "PROSPECT BRIEF" (uppercase label, matches existing brief header style).
- Shows cached prospect brief narrative loaded from `briefs.json` on page load. **Do not auto-synthesize.** If no cached brief exists, show "No prospect brief yet." with a "Generate" button. If cached brief exists, show narrative + "Refresh" button + timestamp.
- No loading spinner on page load — just render from cache or show the empty state.
- CSS: `border-left: 4px solid #22c55e;`

#### 5. Org Brief Card (BLUE right-border — cross-reference, read-only)
- Header: "ORG BRIEF" with blue dot + `From Org →` badge.
- Shows org brief narrative loaded from cache on page load (read-only, no refresh button on this page).
- If no org brief exists, show "No org brief yet. Generate one from the Org page." with the `From Org →` link.
- **Do not auto-synthesize.** Load from `briefs.json` cache only. No loading spinner.
- Brief timestamp shown.
- CSS: `border-right: 4px solid #2563eb;`

#### 6. Active Tasks (no colored border — prospect-owned, uses existing card style)
- Unchanged from current implementation.

#### 7. Interaction History (collapsible)
- Unchanged from current implementation.

#### 8. Meeting Summaries (BLUE right-border — cross-reference from org)
- Org-owned data. Same rendering as today.
- Header badge: blue dot + `From Org →`.
- CSS: `border-right: 4px solid #2563eb;`

#### 9. Notes Log (GREEN left-border — native)
- Prospect-owned. Unchanged behavior.
- Add note form at bottom (existing styling).
- CSS: `border-left: 4px solid #22c55e;`

#### 10. Email History (BLUE right-border — cross-reference from org, collapsible)
- Org-owned data. Same rendering as today.
- Header badge: blue dot + `From Org →`.
- CSS: `border-right: 4px solid #2563eb;`

### B. Org Detail Page — New Layout (top to bottom)

#### 1. Header
- Org name as h1, "← Back to Organizations" breadcrumb link.

#### 2. Org Card (GREEN left-border — native)
- **Fields:** Type, Domain — inline-editable as today.
- **Contacts sub-section:** Full contacts table (from `_contacts_table.html`), with add/edit/star-primary controls.
- **Remove Notes from this card.** Notes move to a standalone Notes Log card below (section 6).
- CSS: `border-left: 4px solid #22c55e;`

#### 3. Prospect Cards (BLUE right-border — cross-reference, one per offering)
- One card per prospect linked to this org.
- Each card shows: Offering name (as card header), Stage badge, Target, Closing, Assigned To, Primary Contact (displayed as the contact's name — this is the pointer stored on the prospect, referencing one of this org's contacts).
- All fields are **read-only** on this page.
- Header badge: blue dot + `View Prospect →` linking to `/crm/prospect/{offering}/{org}/detail`.
- If no prospects exist: "No prospects linked yet."
- CSS: `border-right: 4px solid #2563eb;` (NO left border)

#### 4. Org Brief Card (GREEN left-border — native)
- Header: "ORG BRIEF" (rename from "Relationship Brief").
- Refresh button + timestamp.
- Editable/refreshable here (this is the owning page).
- Same load behavior: read from cache on page load, no auto-synthesize, "Generate" button if none exists.
- CSS: `border-left: 4px solid #22c55e;`

#### 5. Meeting Summaries (GREEN left-border — native to org, collapsible)
- Org-owned. Displayed exactly as on prospect detail today.
- CSS: `border-left: 4px solid #22c55e;`

#### 6. Org Notes Log (GREEN left-border — native, standalone card)
- **New standalone card** — moved out of the org top card. Identical layout and styling to the Prospect Detail Notes Log card.
- Header: "NOTES LOG" (uppercase label).
- Chronological list of org-level notes with timestamp and author.
- Add Note form at bottom — **same styling as prospect detail** (blue "Add Note" button, not white).
- Notes stored under `org:{org}` key in `prospect_notes.json`.
- CSS: `border-left: 4px solid #22c55e;`

#### 7. Email History (GREEN left-border — native to org, collapsible)
- Org-owned. Same rendering as prospect detail.
- CSS: `border-left: 4px solid #22c55e;`

### C. CSS Changes

Add to `static/crm.css` (or inline in each template):

```css
/* Native section — data belongs here, editable */
.card-native {
  border-left: 4px solid #22c55e;
}

/* Cross-reference section — data lives elsewhere, read-only */
.card-crossref {
  border-right: 4px solid #2563eb;
  border-left: none;
}

/* Cross-reference navigation badge */
.crossref-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 500;
  color: #60a5fa;
  text-decoration: none;
  transition: color 0.15s;
}
.crossref-badge:hover {
  color: #93bbfc;
}
.crossref-badge::before {
  content: '';
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #2563eb;
  flex-shrink: 0;
}
```

### D. Button Styling Standardization

The "Add Note" button on the Org Detail Notes Log must match the existing prospect detail Notes Log button:
- Blue background (`#2563eb`), white text, rounded corners, same padding.
- NOT white/outlined as the current org page uses for other buttons.
- Both pages should use the same `.btn-add-note` class.

---

## 6. Integration Points

- **Brief synthesis endpoints:** Reuse existing `POST /crm/api/prospect/<offering>/<org>/brief` for the old relationship brief. Add new `POST /crm/api/prospect/<offering>/<org>/prospect-brief` for the new focused prospect brief. Reuse existing `POST /crm/api/synthesize-org-brief` for org brief.
- **Prospect brief prompt:** New system prompt emphasizing: "Write a 2-3 sentence summary of where this specific offering stands. Focus on: most recent touchpoint, next planned action, any blockers or pending items. Do not repeat org-level context."
- **Brief loading behavior (CRITICAL):** Both Prospect Brief and Org Brief must load from `briefs.json` cache on page load. **No auto-synthesis.** If no cached brief exists, show a static empty state with a "Generate" button. The loading spinner / "Synthesizing intelligence..." / "Loading brief..." patterns must NOT appear on page load. This prevents the "still loading" problem seen in the current implementation.
- **Meetings data:** Already keyed by org in `crm/prospect_meetings.json` (field: `org`). No change to storage. Both pages call same endpoint/function to load.
- **Email data:** Already keyed by org in `crm/email_log.json` (field: `org`). No change. Both pages display.
- **Contacts:** Already loaded via `get_contacts_for_org(org)`. Prospect page renders read-only; org page renders with full edit controls via `_contacts_table.html`.

---

## 7. Constraints

- **No new dependencies.** Pure HTML/CSS/JS template changes plus minor Python additions.
- **Backward compatibility:** The old `prospect:{offering}:{org}` brief key in `briefs.json` must not be deleted. It simply stops being displayed on the prospect page (replaced by the new prospect brief and org brief). If an org has no org brief yet but has an old prospect-level relationship brief, the org brief section on prospect detail can show the old brief with a note: "Legacy brief — refresh from Org page for updated version."
- **Contacts read-only on prospect:** Do NOT include `_contacts_table.html` on prospect detail (it has edit controls). Instead, render a simpler read-only contacts list directly in the template.
- **Consistent card class naming:** Use `.card.card-native` and `.card.card-crossref` so existing `.card` styles still apply.
- **Org notes and prospect notes coexist** in the same `prospect_notes.json` file, differentiated by key prefix (`org:` vs `{offering}:`).
- **No auto-synthesis on page load** for any brief section. Always load from cache. Show empty state + Generate button if no cached brief exists.
- **Org Notes field removed from org top card.** The old inline Notes field in the org summary card is replaced by the standalone Notes Log card. Existing org notes content (from `organizations.md` Notes field) should be preserved — migrate to the first entry in the org notes log if non-empty, or keep as a read-only legacy field until migration is run.

---

## 8. Acceptance Criteria

- [ ] Prospect Detail top card shows ONLY: Stage, Assigned To, Target, Closing, Primary Contact (dropdown from org contacts), Last Touch, Urgent — with GREEN left-border
- [ ] Prospect Detail has a BLUE right-bordered read-only org info card showing Type, Domain, and contacts list — with blue dot + "From Org →" badge linking to org detail
- [ ] Prospect Detail shows a new "Prospect Brief" section (GREEN left-border) with generate/refresh capability, loaded from cache (no auto-synthesize)
- [ ] Prospect Detail shows "Org Brief" section (BLUE right-border, read-only) loaded from cache (no auto-synthesize, no loading spinner)
- [ ] Prospect Detail: Meetings and Emails sections have BLUE right-border and "From Org →" badges
- [ ] Prospect Detail: Notes Log has GREEN left-border (prospect-owned, native)
- [ ] Prospect Detail: Edit Prospect, Edit Org, and Scan Email buttons are REMOVED from the header
- [ ] Org Detail top card shows Type, Domain, Contacts (with full edit controls) — GREEN left-border. Notes field removed from this card.
- [ ] Org Detail shows one BLUE right-bordered prospect card per offering, with read-only fields and "View Prospect →" badge
- [ ] Org Detail has refreshable "Org Brief" section (GREEN left-border, renamed from "Relationship Brief"), loaded from cache (no auto-synthesize)
- [ ] Org Detail has a standalone Org Notes Log card (GREEN left-border) with Add Note button styled identically to prospect detail (blue button, not white)
- [ ] Org Detail shows Meeting Summaries (GREEN left-border) and Email History (GREEN left-border) sections
- [ ] Color coding is context-dependent: green left = native/editable, blue right = cross-reference/read-only
- [ ] Blue right-border cards always include a blue-dot navigation badge linking to the owning page
- [ ] All existing inline-edit functionality still works on native (green) sections
- [ ] No brief auto-synthesis on page load anywhere — always load from cache, show Generate button if empty
- [ ] No regressions in existing tests (`python3 -m pytest app/tests/ -v` passes)
- [ ] Feedback loop prompt has been run

---

## 9. Files Likely Touched

| File | Changes |
|------|---------|
| `app/templates/crm_prospect_detail.html` | Major restructure: reorder cards, remove header buttons, add org info cross-ref card, add prospect brief section, add org brief read-only section, add green/blue border classes, fix brief loading (no auto-synthesize) |
| `app/templates/crm_org_edit.html` | Major restructure: reorder sections, remove Notes from top card, add standalone Notes Log card, add prospect summary cross-ref cards, add meeting summaries section, add email history section, rename brief to "Org Brief", add green/blue border classes, fix Add Note button styling |
| `app/delivery/crm_blueprint.py` | New routes: prospect-brief GET/POST, org notes GET/POST. Pass additional data to templates (org brief for prospect page, meetings for org page, emails for org page) |
| `app/sources/crm_reader.py` | New functions: `load_org_notes()`, `save_org_note()`. Possibly `load_prospect_brief()` / `save_prospect_brief()` if distinct from existing brief functions |
| `app/sources/relationship_brief.py` | New prompt template for prospect-brief synthesis (short, offering-focused) |
| `static/crm.css` | New utility classes: `.card-native`, `.card-crossref`, `.crossref-badge`. Standardize `.btn-add-note` styling |
