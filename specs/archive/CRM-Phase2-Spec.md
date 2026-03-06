# CRM Phase 2 — Prospects Table (Read-Only) Spec
**For Claude Code**
**Author:** Oscar Vasquez, COO — Avila Real Estate Capital
**Date:** March 2026
**Status:** Ready for Execution
**Depends on:** Phase 1 complete, all tests passing

---

## Overview

Add a read-only prospects table at `/crm` to the existing Flask dashboard app.
No write operations in this phase — all data flows one direction: markdown files
→ Python parser → JSON API → browser table. Also add a "CRM →" link to the
existing dashboard header.

---

## Environment

- App root: `~/arec-morning-briefing/`
- Existing Flask app: `delivery/dashboard.py`, port 3001
- CRM parser: `sources/crm_reader.py` (Phase 1)
- CRM data: `~/Dropbox/Tech/ClaudeProductivity/crm/`
- Stack: Vanilla HTML, CSS, JavaScript — no npm, no frameworks, no build step
- Existing templates: `templates/dashboard.html`
- Do not break any existing dashboard functionality

---

## Step 1 — Minimal Dashboard Header Change

**File to modify:** `templates/dashboard.html`

Add a single "CRM →" link to the existing dashboard header. Match whatever
styling pattern already exists in the header. If there is no header nav, add
a small fixed link in the top-right corner styled to not conflict with the
existing layout.

Do not touch any other part of `dashboard.html`. Do not touch `dashboard.py`
routes, data loading, or column logic — that is deferred to Phase 7.

---

## Step 2 — Flask Blueprint

**File to modify:** `delivery/dashboard.py`

Add a CRM Blueprint at the bottom of the file, registered with url_prefix `/crm`.
Do not modify any existing routes or functions.

```python
from flask import Blueprint, jsonify, request, render_template
from sources.crm_reader import (
    load_prospects, load_offerings, get_fund_summary, load_crm_config
)

crm_bp = Blueprint('crm', __name__, url_prefix='/crm')
app.register_blueprint(crm_bp)  # register after existing routes
```

### Routes to implement

#### `GET /crm`
Renders `templates/crm/pipeline.html`.
Passes to template:
- `offerings` — result of `load_offerings()`
- `config` — result of `load_crm_config()`

#### `GET /crm/api/offerings`
Returns JSON list of offerings:
```json
[
  {"name": "AREC Debt Fund II", "target": "$1,000,000,000", "hard_cap": ""},
  {"name": "Mountain House Refi", "target": "$35,000,000", "hard_cap": "$35,000,000"}
]
```

#### `GET /crm/api/prospects`
Query params:
- `offering` (required) — filter by offering name
- `include_closed` (optional, default `false`) — if `false`, exclude records
  where stage is `Closed`, `9. Closed`, `0. Not Pursuing`, or `Declined`

Returns JSON array. Each prospect object:
```json
{
  "org": "Merseyside Pension Fund",
  "offering": "AREC Debt Fund II",
  "stage": "6. Verbal",
  "target": "$50,000,000",
  "target_display": "$50M",
  "committed": "$0",
  "committed_display": "$0",
  "primary_contact": "Susannah Friar",
  "closing": "Final",
  "urgency": "High",
  "assigned_to": "James Walton",
  "notes": "Sent Credit and Index Comparisons on 2/25",
  "next_action": "Meeting March 2",
  "last_touch": "2026-02-25",
  "last_touch_days": 3,
  "org_type": "INSTITUTIONAL",
  "_heading_key": "Merseyside Pension Fund"
}
```

`last_touch_days` = integer days since `last_touch` date as of today.
`org_type` = pulled from `load_organizations()` matched by org name — if not
found, return empty string.
`target_display` and `committed_display` = result of `_format_currency()` applied
to the parsed float values.

#### `GET /crm/api/fund-summary`
Query param: `offering` (required)
Returns result of `get_fund_summary(offering)` as JSON:
```json
{
  "offering": "AREC Debt Fund II",
  "total_committed": 0.0,
  "target": 1000000000.0,
  "hard_cap": 0.0,
  "pct_committed": 0.0,
  "prospect_count": 67
}
```

---

## Step 3 — Template & Static Files

### File structure to create

```
templates/
└── crm/
    ├── _layout.html       ← shared base layout
    └── pipeline.html      ← prospects table page

static/
└── crm/
    ├── crm.css
    └── crm.js
```

---

### `templates/crm/_layout.html`

Base layout shared by all CRM pages (pipeline, org detail, analytics in later phases).

**Top navigation bar:**
```
[AREC CRM]          [Dashboard ↗]  [Pipeline]  [Analytics]
```
- "AREC CRM" — left-aligned wordmark/logo text, links to `/crm`
- "Dashboard ↗" — links to `/` (existing dashboard), opens in same tab
- "Pipeline" — links to `/crm`, active state highlighted when on this page
- "Analytics" — links to `/crm/analytics` (greyed out / disabled for now,
  page doesn't exist until Phase 6)

**Visual style:**
- The CRM can have its own feel — it does not need to match `dashboard.html` exactly
- Dark navy nav bar (`#0f172a`) with white text works well for a professional CRM
- Clean white content area, subtle borders, readable table typography
- Color palette for reference:
  - Nav: `#0f172a`
  - Background: `#f8fafc`
  - Card/panel: `#ffffff`
  - Border: `#e2e8f0`
  - Primary accent: `#2563eb`
  - Urgency High: `#dc2626`
  - Urgency Med: `#d97706`
  - Urgency Low: `#6b7280`
  - Staleness green: `#16a34a`, yellow: `#ca8a04`, red: `#dc2626`
  - Text primary: `#0f172a`
  - Text muted: `#64748b`
- Font: system-ui / -apple-system stack (no web fonts)
- Block extends: `{% block content %}{% endblock %}`

---

### `templates/crm/pipeline.html`

Extends `crm/_layout.html`. The prospects table page.

#### Offering Tabs

Horizontal tab bar below the nav. One tab per offering from `offerings`.
Clicking a tab:
1. Updates active tab style
2. Fetches `/crm/api/prospects?offering=<name>` via JS
3. Fetches `/crm/api/fund-summary?offering=<name>` via JS
4. Re-renders the fund progress bar and table
5. Saves selected offering to `localStorage` key `crm_selected_offering`

On page load, restore last selected offering from `localStorage`, defaulting
to the first offering.

#### Fund Progress Bar

Below the offering tabs. Shows for the currently selected offering:

```
AREC Debt Fund II          $0 committed of $1B target (0%)   67 active prospects
[========================================] 0%
```

- Left: offering name
- Right: committed / target (abbreviated), percentage, prospect count
- Progress bar: filled portion = pct_committed, color `#2563eb`
- If hard_cap exists, show a subtle marker on the bar at the hard_cap position

#### Filter Bar

A single row of filter controls, always visible:

| Filter | Type | Options |
|--------|------|---------|
| Stage | Multi-select dropdown | All stages from config + "All Stages" |
| Urgency | Multi-select dropdown | High, Med, Low, (blank) + "All" |
| Assigned To | Multi-select dropdown | Team members from config + "All" |
| Type | Multi-select dropdown | Org types from config + "All" |
| Include Closed | Toggle checkbox | Default OFF |
| Clear Filters | Link/button | Resets all filters to default |

Filtering is **client-side** — all prospect data is loaded once on offering
selection, then JS filters the in-memory array and re-renders the table body.

Active filter state is reflected in the filter controls. "Clear Filters" resets
everything and re-renders.

#### Prospects Table

Columns (in this order):

| Column | Field | Notes |
|--------|-------|-------|
| Organization | `org` | Bold; future phases will make this a link |
| Urgency | `urgency` | Color badge |
| Stage | `stage` | Plain text |
| Expected | `target_display` | Right-aligned |

These are the **only default visible columns** — no hidden columns in Phase 2.
Additional columns (Next Action, Last Touch, etc.) will be added in later phases
or via a column picker.

**Urgency badge styling:**
- High → red pill (`#dc2626` background or border, white/dark text)
- Med → amber pill (`#d97706`)
- Low → gray pill (`#6b7280`)
- Blank → no badge, empty cell

**Default sort:** Urgency first (High → Med → Low → blank), then Stage
descending by stage number (6. Verbal before 5. Interested, etc.).

**Column header click → sort:**
- Click once → sort ascending
- Click again → sort descending
- Arrow indicator (↑ / ↓) on active sort column
- Sort state stored in JS variables (no URL params needed in Phase 2)

**Stage sort order:** Extract the leading number from stage strings
(`"6. Verbal"` → 6) for numeric sort. Stages without a number sort after
numbered stages.

**Urgency sort order:** High=0, Med=1, Low=2, blank=3 (so High sorts first
in ascending, which is the default).

**Row count:** Show total visible row count below the table:
`Showing 847 prospects` (updates as filters change)

**Empty state:** If no prospects match the current filters:
```
No prospects match the current filters.
[Clear filters]
```

#### Mobile Layout (< 768px)

At narrow widths, collapse to a simplified 3-column table:

| Org | Stage | Urgency |
|-----|-------|---------|

- Hide the Expected column
- Filter bar collapses behind a "Filters ▼" toggle button
- Table uses smaller font, tighter padding
- Urgency badge shrinks to a colored dot (●) instead of text pill

---

### `static/crm/crm.css`

Write all CRM styles here. Do not embed styles in HTML templates.

Key rules to implement:
- Nav bar, tab bar, filter bar layout
- Table: sticky header, alternating row shading (very subtle, `#f8fafc` on
  even rows), hover highlight
- Urgency badges (pill shape, color variants)
- Progress bar
- Responsive breakpoint at 768px
- Filter dropdowns (styled `<select>` elements, consistent appearance)
- Active sort column header indicator
- Empty state styling
- `crm-loading` class for the table body during data fetch (show a simple
  "Loading..." row)

---

### `static/crm/crm.js`

All client-side logic. No inline JS in HTML.

#### On DOM ready:

1. Read `localStorage` for `crm_selected_offering`, default to first offering tab
2. Activate that tab
3. `fetchProspects(offeringName)` — fetch and render

#### `fetchProspects(offeringName)`

```
1. Show loading state in table body
2. Fetch /crm/api/prospects?offering={name}&include_closed=false in parallel with
   /crm/api/fund-summary?offering={name}
3. Store raw prospect array in module-level variable: allProspects
4. Call applyFiltersAndRender()
5. Update fund progress bar with summary data
```

#### `applyFiltersAndRender()`

```
1. Read current filter values from DOM
2. Filter allProspects array in memory:
   - Stage: if any stages selected, keep only matching
   - Urgency: if any urgencies selected, keep only matching
   - Assigned To: if any assigned selected, keep only matching
   - Type: if any types selected, keep only org_type matches
3. Sort the filtered array per current sort state
4. Render filtered+sorted array into table body
5. Update row count text
```

#### Sort logic

```javascript
function sortProspects(prospects, column, direction) {
  // column: 'org' | 'urgency' | 'stage' | 'target'
  // direction: 'asc' | 'desc'
  // urgency sort order: High=0, Med=1, Low=2, blank=3
  // stage sort: parse leading integer, fallback to string compare
  // target sort: parse float from target field
}
```

#### Tab switching

On tab click:
1. Update active tab class
2. Save offering name to `localStorage`
3. Call `fetchProspects(offeringName)`
4. Reset filters to defaults (don't carry filter state across offering switches)

#### Filter controls

Each filter control (Stage, Urgency, Assigned To, Type) dispatches a change event
that calls `applyFiltersAndRender()`. No API call — purely client-side.

"Include Closed" checkbox: when toggled ON, re-fetch with
`include_closed=true`. When toggled OFF, re-fetch with `include_closed=false`.
(This requires a new API fetch since closed records weren't in the original payload.)

"Clear Filters" resets all `<select>` elements to their default (All) option
and unchecks "Include Closed", then calls `applyFiltersAndRender()`.

---

## Step 4 — Verify

```bash
# Start the dashboard
cd ~/arec-morning-briefing
python3 delivery/dashboard.py

# In browser:
# - http://localhost:3001           → existing dashboard, "CRM →" link visible
# - http://localhost:3001/crm       → prospects table loads
# - http://localhost:3001/crm/api/prospects?offering=AREC+Debt+Fund+II
#     → JSON array returned
# - http://localhost:3001/crm/api/fund-summary?offering=AREC+Debt+Fund+II
#     → fund summary JSON returned
```

Manual checks:
- [ ] Existing dashboard loads with no regressions
- [ ] "CRM →" link appears in dashboard header and navigates to `/crm`
- [ ] Offering tabs render and switch correctly
- [ ] Fund progress bar shows for selected offering
- [ ] Table loads with prospects, correct column order
- [ ] Default sort: High urgency first, then stage descending
- [ ] Stage/Urgency/Assigned To/Type filters narrow the table client-side
- [ ] "Include Closed" toggle re-fetches and shows closed records
- [ ] Column header click sorts, arrow indicator updates
- [ ] Row count updates as filters change
- [ ] Mobile (375px): 3-column table, filter bar collapses
- [ ] No JS console errors

---

## What's NOT In This Phase

- No clickable org names (Phase 4)
- No inline editing (Phase 3)
- No "Add Prospect" button (Phase 3)
- No auto-capture (Phase 5)
- No analytics page (Phase 6)
- No Column 4 removal from dashboard (Phase 7)

---

## Files Modified / Created

```
templates/dashboard.html          ← MODIFIED: add CRM link to header only
delivery/dashboard.py             ← MODIFIED: add crm_bp Blueprint + 4 routes
templates/crm/_layout.html        ← NEW
templates/crm/pipeline.html       ← NEW
static/crm/crm.css                ← NEW
static/crm/crm.js                 ← NEW
```

---

*When Phase 2 is complete and all manual checks pass, return for the Phase 3
spec (inline editing and full CRUD write APIs).*
