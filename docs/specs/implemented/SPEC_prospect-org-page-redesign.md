SPEC: Prospect & Org Detail Page Redesign | Project: arec-crm | Date: 2026-03-19 | Status: Ready for implementation

---

## 1. Objective

Redesign the Prospect Detail and Org Detail pages to establish clear ownership boundaries between prospect-level and org-level data. Each page should make it visually obvious which data belongs to the prospect, which belongs to the org, and which is cross-referenced from the other entity. Color-coded card sidebars (blue = prospect, green = org) replace the current ambiguous layout where both pages mix ownership without visual cues.

Additionally: split the current "Relationship Brief" into two distinct briefs — a focused **Prospect Brief** (offering-specific status) and an **Org Brief** (comprehensive relationship narrative) — and formalize meetings and emails as org-owned data displayed on both pages.

---

## 2. Scope

### In Scope

- Restructure Prospect Detail page layout and card order
- Restructure Org Detail page layout and card order
- Add color-coded left-border sidebars to cards (blue = prospect-owned, green = org-owned)
- Add a new "Prospect Brief" section (short, offering-specific status summary)
- Move "Relationship Brief" → rename to "Org Brief" (org-owned, displayed read-only on prospect page)
- Move contacts display to org-owned card on prospect page (read-only)
- Add prospect summary cards to org page (one per offering, with links)
- Formalize meetings and emails as org-owned (displayed on both pages)
- Add org-owned Notes Log to org page
- Prospect-owned Notes Log stays on prospect page

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
| Stage, Target, Closing, Urgent, Assigned To | Prospect | Prospect Detail | Prospect Detail + Org (read-only card) |
| Primary Contact (pointer) | Prospect | Prospect Detail | Prospect Detail + Org (inside prospect card) |
| Type, Domain, Aliases | Org | Org Detail | Org Detail + Prospect (read-only card) |
| Contacts (people) | Org | Org Detail | Org Detail + Prospect (read-only) |

### Primary Contact is a Pointer, Not a Copy

All contacts (people) live on the Org. There is exactly one set of people per org, managed in `contacts_index.md` and `contacts/*.md`. The prospect does NOT store its own contacts — it only stores a **Primary Contact identifier** (a name or slug) that references one of the org's contacts. This is a tag/pointer, not a separate record.

On Prospect Detail, the Primary Contact dropdown should be populated from the org's contacts list. Different prospects under the same org may each designate a different primary contact (e.g., UTIMCO Fund II vs. Mountain House may have different point people). In most cases they'll be the same person, but the flexibility must exist at the prospect level.
| Prospect Brief | Prospect | Prospect Detail (refresh) | Prospect Detail only |
| Org Brief | Org | Org Detail (refresh) | Org Detail + Prospect (read-only) |
| Prospect Notes Log | Prospect | Prospect Detail | Prospect Detail only |
| Org Notes Log | Org | Org Detail | Org Detail only |
| Meeting Summaries | Org | N/A (auto-captured) | Both pages |
| Email History | Org | N/A (auto-captured) | Both pages |
| Active Tasks | Prospect | Prospect Detail | Prospect Detail only |
| Interaction History | Prospect | Prospect Detail | Prospect Detail only |

### Prospect Brief (new)

- Short, focused summary of the current state of this specific offering for this org.
- Content: most recent outreach, next planned meeting/action, current stage context, any blockers.
- Stored in `crm/briefs.json` under a new key format: `prospect_brief:{offering}:{org}` (distinct from the existing `prospect:{offering}:{org}` key used for the old relationship brief).
- Same JSON contract: `{narrative, at_a_glance, generated_at}`.
- Displayed ONLY on Prospect Detail, not on Org Detail.

### Org Brief (replaces current "Relationship Brief")

- Comprehensive relationship narrative at the org level.
- Already exists via the `synthesize-org-brief` endpoint and `org_brief:{org}` key in `briefs.json`.
- Displayed on Org Detail (editable/refreshable) AND on Prospect Detail (read-only, no refresh button).
- On Prospect Detail, the Org Brief card has a green left-border and a small "From Org" badge.

### Color Coding Convention

- **Blue left-border (4px solid #2563eb):** Prospect-owned card — data lives on the prospect, editable here.
- **Green left-border (4px solid #22c55e):** Org-owned card — data lives on the org. If shown on Prospect Detail, it's read-only with a badge ("From Org →" linking to the org page). If shown on Org Detail and displaying prospect data, badge reads "Prospect →" linking to the prospect detail page.

### Cross-Reference Badges

- On Prospect Detail, org-owned cards show a small top-right badge: `From Org →` (links to `/crm/org/{org}/edit`).
- On Org Detail, prospect cards show a small top-right badge: `View Prospect →` (links to `/crm/prospect/{offering}/{org}/detail`).

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

#### 1. Header (unchanged)
- Org name, offering subtitle, back link, action buttons (Scan Email, Edit Org, Edit Prospect).

#### 2. Prospect Card (blue left-border)
- **Fields:** Stage, Assigned To, Target, Closing, Primary Contact, Last Touch, Urgent badge.
- **Primary Contact** is a dropdown populated from the org's contacts list (fetched via `get_contacts_for_org`). It stores a pointer (name/slug) — NOT a separate contact record. The dropdown lets the user select which of the org's existing contacts is the primary for this particular prospect.
- Remove: Org Type (moves to org card below).
- All fields remain inline-editable as today.
- CSS: `border-left: 4px solid #2563eb;`

#### 3. Org Info Card (green left-border, read-only)
- **Fields:** Type, Domain.
- **Contacts sub-section:** List of contacts (name, role, email) — read-only display, no edit controls.
- Top-right badge: `From Org →` linking to `/crm/org/{org}/edit`.
- CSS: `border-left: 4px solid #22c55e;`
- None of the fields are editable on this page. Clicking the badge navigates to org detail for editing.

#### 4. Prospect Brief Card (blue left-border)
- New section. Header: "Prospect Brief".
- Shows cached prospect brief narrative. If none exists, shows "No prospect brief yet." with a "Generate" button.
- "Refresh" button to re-synthesize.
- Brief Refreshed timestamp shown.

#### 5. Org Brief Card (green left-border, read-only)
- Header: "Org Brief" with `From Org →` badge.
- Shows org brief narrative (read-only, no refresh button on this page).
- If no org brief exists, shows "No org brief yet. Generate one from the Org page."
- Brief timestamp shown.

#### 6. Active Tasks (no colored border — prospect-owned but uses existing card style)
- Unchanged from current implementation.

#### 7. Interaction History (collapsible)
- Unchanged from current implementation.

#### 8. Meeting Summaries (green left-border, read-only)
- Org-owned data. Same rendering as today.
- Small `From Org →` badge in header.

#### 9. Notes Log (blue left-border)
- Prospect-owned. Unchanged behavior.
- Add note form at bottom.

#### 10. Email History (green left-border, read-only, collapsible)
- Org-owned data. Same rendering as today.
- Small `From Org →` badge in header.

### B. Org Detail Page — New Layout (top to bottom)

#### 1. Header
- Org name, back link to Organizations list.

#### 2. Org Card (green left-border)
- **Fields:** Type, Domain — inline-editable as today.
- **Contacts sub-section:** Full contacts table (from `_contacts_table.html`), with add/edit/star-primary controls.
- CSS: `border-left: 4px solid #22c55e;`

#### 3. Prospect Cards (blue left-border, one per offering)
- One card per prospect linked to this org.
- Each card shows: Offering name (as card header), Stage badge, Target, Closing, Assigned To, Primary Contact (displayed as the contact's name — this is the pointer stored on the prospect, referencing one of this org's contacts).
- All fields are **read-only** on this page.
- Top-right badge: `View Prospect →` linking to `/crm/prospect/{offering}/{org}/detail`.
- If no prospects exist: "No prospects linked yet."
- CSS: `border-left: 4px solid #2563eb;`

#### 4. Org Brief Card (green left-border)
- Same as current "Relationship Brief" on org page.
- Header: "Org Brief" (rename from "Relationship Brief").
- Refresh button + timestamp.
- Editable/refreshable here (this is the owning page).

#### 5. Meeting Summaries (collapsible)
- Org-owned. Displayed exactly as on prospect detail today.
- No colored border needed (it's on the owning page).

#### 6. Org Notes Log (green left-border)
- New section. Mirrors prospect notes log behavior.
- Add note form at bottom.
- Notes stored under `org:{org}` key in `prospect_notes.json`.

#### 7. Email History (collapsible)
- Org-owned. Same rendering as prospect detail.
- No colored border needed (it's on the owning page).

### C. CSS Changes

Add to shared styles (or inline in each template):

```css
.card-prospect { border-left: 4px solid #2563eb; }
.card-org      { border-left: 4px solid #22c55e; }

.card-badge {
  font-size: 11px;
  font-weight: 500;
  color: #94a3b8;
  text-decoration: none;
  transition: color 0.15s;
}
.card-badge:hover { color: #60a5fa; }

.card-badge-org::before {
  content: '';
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
  margin-right: 4px;
}
.card-badge-prospect::before {
  content: '';
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #2563eb;
  margin-right: 4px;
}
```

---

## 6. Integration Points

- **Brief synthesis endpoints:** Reuse existing `POST /crm/api/prospect/<offering>/<org>/brief` for the old relationship brief. Add new `POST /crm/api/prospect/<offering>/<org>/prospect-brief` for the new focused prospect brief. Reuse existing `POST /crm/api/synthesize-org-brief` for org brief.
- **Prospect brief prompt:** New system prompt emphasizing: "Write a 2-3 sentence summary of where this specific offering stands. Focus on: most recent touchpoint, next planned action, any blockers or pending items. Do not repeat org-level context."
- **Meetings data:** Already keyed by org in `crm/prospect_meetings.json` (field: `org`). No change to storage. Both pages call same endpoint/function to load.
- **Email data:** Already keyed by org in `crm/email_log.json` (field: `org`). No change. Both pages display.
- **Contacts:** Already loaded via `get_contacts_for_org(org)`. Prospect page renders read-only; org page renders with full edit controls via `_contacts_table.html`.

---

## 7. Constraints

- **No new dependencies.** Pure HTML/CSS/JS template changes plus minor Python additions.
- **Backward compatibility:** The old `prospect:{offering}:{org}` brief key in `briefs.json` must not be deleted. It simply stops being displayed on the prospect page (replaced by the new prospect brief and org brief). If an org has no org brief yet but has an old prospect-level relationship brief, the org brief section on prospect detail can show the old brief with a note: "Legacy brief — refresh from Org page for updated version."
- **Contacts read-only on prospect:** Do NOT include `_contacts_table.html` on prospect detail (it has edit controls). Instead, render a simpler read-only contacts list directly in the template.
- **Consistent card class naming:** Use `.card.card-prospect` and `.card.card-org` so existing `.card` styles still apply.
- **Org notes and prospect notes coexist** in the same `prospect_notes.json` file, differentiated by key prefix (`org:` vs `{offering}:`).

---

## 8. Acceptance Criteria

- [ ] Prospect Detail top card shows ONLY: Stage, Assigned To, Target, Closing, Primary Contact, Last Touch, Urgent — with blue left-border
- [ ] Prospect Detail has a green-bordered read-only org info card showing Type, Domain, and contacts list — with "From Org →" badge linking to org detail
- [ ] Prospect Detail shows a new "Prospect Brief" section (blue border) with generate/refresh capability
- [ ] Prospect Detail shows "Org Brief" section (green border, read-only) pulled from org brief cache
- [ ] Prospect Detail: Meetings and Emails sections have green left-border and "From Org →" badges
- [ ] Prospect Detail: Notes Log has blue left-border (prospect-owned)
- [ ] Org Detail top card shows Type, Domain, Contacts (with full edit controls) — green left-border
- [ ] Org Detail shows one blue-bordered prospect card per offering, with read-only fields and "View Prospect →" badge
- [ ] Org Detail has refreshable "Org Brief" section (renamed from "Relationship Brief")
- [ ] Org Detail has an org-level Notes Log with add-note functionality
- [ ] Org Detail shows Meeting Summaries and Email History sections
- [ ] Color coding is consistent: blue = prospect, green = org on both pages
- [ ] All existing inline-edit functionality still works on the owning pages
- [ ] Cross-reference badges navigate correctly between prospect and org pages
- [ ] No regressions in existing tests (`python3 -m pytest app/tests/ -v` passes)
- [ ] Feedback loop prompt has been run

---

## 9. Files Likely Touched

| File | Changes |
|------|---------|
| `app/templates/crm_prospect_detail.html` | Major restructure: reorder cards, add org info card, add prospect brief section, add org brief read-only section, add color-coded borders and badges |
| `app/templates/crm_org_edit.html` | Major restructure: reorder sections, add prospect summary cards, add org notes section, add meeting summaries, add email history, rename brief, add color coding |
| `app/delivery/crm_blueprint.py` | New routes: prospect-brief GET/POST, org notes GET/POST. Pass additional data to templates (org brief for prospect page, meetings for org page) |
| `app/sources/crm_reader.py` | New functions: `load_org_notes()`, `save_org_note()`. Possibly `load_prospect_brief()` / `save_prospect_brief()` if distinct from existing brief functions |
| `app/sources/relationship_brief.py` | New prompt template for prospect-brief synthesis (short, offering-focused) |
| `static/crm.css` | New utility classes: `.card-prospect`, `.card-org`, `.card-badge`, `.card-badge-org`, `.card-badge-prospect` |
