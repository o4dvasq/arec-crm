# CRM Column Manager Spec
**For Claude Code**
**Author:** Oscar Vasquez, COO — Avila Real Estate Capital
**Date:** March 2026
**Status:** Ready for Execution
**Depends on:** CRM Phase 2 complete (pipeline table exists)

---

## Overview

Add a column manager panel to the CRM pipeline table. Users can show/hide
any prospect field as a column and drag to reorder columns. Configuration
persists in localStorage per offering. No backend changes required — this
is entirely client-side.

---

## All Available Columns

These are every field available to display. The column key maps directly to
the field name in the prospect JSON returned by the API.

| Key | Label | Default visible |
|-----|-------|----------------|
| `org` | Organization | Yes (always visible, not hideable) |
| `urgency` | Urgency | Yes |
| `stage` | Stage | Yes |
| `target_display` | Expected | Yes |
| `next_action` | Next Action | Yes |
| `org_type` | Type | No |
| `assigned_to` | Assigned To | No |
| `closing` | Closing | No |
| `primary_contact` | Primary Contact | No |
| `last_touch` | Last Touch | No |
| `committed_display` | Committed | No |
| `notes` | Notes | No |

**Organization is always the first column and cannot be hidden or moved.**
All other columns are optional and reorderable.

---

## Step 1 — Column Manager Button

**File to modify:** `templates/crm/pipeline.html`

Add a "Columns" button to the top bar, right-aligned alongside the existing
"Run Capture" and "Add Prospect" (disabled) buttons:

```
[Run Capture]  [Columns ▼]
```

Clicking "Columns ▼" opens the column manager panel (toggle — click again
to close).

---

## Step 2 — Column Manager Panel

The panel is a floating card that appears below the "Columns" button,
right-aligned, and sits above the table (not inline with it).

```
┌─────────────────────────────┐
│ Columns                  ✕  │
├─────────────────────────────┤
│ ≡  ☑  Organization          │  ← locked, always on, no drag handle active
│ ≡  ☑  Urgency               │
│ ≡  ☑  Stage                 │
│ ≡  ☑  Expected              │
│ ≡  ☑  Next Action           │
│ ≡  ☐  Type                  │
│ ≡  ☐  Assigned To           │
│ ≡  ☐  Closing               │
│ ≡  ☐  Primary Contact       │
│ ≡  ☐  Last Touch            │
│ ≡  ☐  Committed             │
│ ≡  ☐  Notes                 │
├─────────────────────────────┤
│ [Reset to defaults]         │
└─────────────────────────────┘
```

**Panel behavior:**
- Width: ~240px
- Max height: 400px with internal scroll if needed
- Click outside panel → close
- Press Escape → close
- "✕" button → close
- "Reset to defaults" → restore default column set and order, save to localStorage

---

## Step 3 — Drag to Reorder

Each row in the panel (except Organization) has a drag handle `≡` on the left.

Use the **HTML5 Drag and Drop API** — no third-party library.

```javascript
// Each panel row
row.setAttribute('draggable', true);
row.addEventListener('dragstart', onDragStart);
row.addEventListener('dragover', onDragOver);
row.addEventListener('drop', onDrop);
row.addEventListener('dragend', onDragEnd);
```

**Visual feedback during drag:**
- Dragged row: `opacity: 0.4`
- Drop target row: `border-top: 2px solid #2563eb` (insertion indicator)

**On drop:**
1. Reorder the internal column config array
2. Re-render the panel rows in new order
3. Re-render the table with new column order
4. Save to localStorage

Organization always stays first — if a drop would place another column
before it, insert after Organization instead.

---

## Step 4 — Show/Hide via Checkbox

Clicking the checkbox next to a column name toggles its visibility.

**On checkbox change:**
1. Update the column config (set `visible: true/false`)
2. Re-render the table (add or remove the column)
3. Save to localStorage

Minimum visible columns: always keep at least 1 column visible beyond
Organization. If user unchecks the last visible column, prevent the action
and briefly shake the checkbox (CSS animation) to indicate it can't be done.

---

## Step 5 — Column Config Data Structure

Maintain a single `columnConfig` array in `crm.js`:

```javascript
// Default config
const DEFAULT_COLUMNS = [
  { key: 'org',              label: 'Organization',    visible: true,  locked: true },
  { key: 'urgency',          label: 'Urgency',         visible: true,  locked: false },
  { key: 'stage',            label: 'Stage',           visible: true,  locked: false },
  { key: 'target_display',   label: 'Expected',        visible: true,  locked: false },
  { key: 'next_action',      label: 'Next Action',     visible: true,  locked: false },
  { key: 'org_type',         label: 'Type',            visible: false, locked: false },
  { key: 'assigned_to',      label: 'Assigned To',     visible: false, locked: false },
  { key: 'closing',          label: 'Closing',         visible: false, locked: false },
  { key: 'primary_contact',  label: 'Primary Contact', visible: false, locked: false },
  { key: 'last_touch',       label: 'Last Touch',      visible: false, locked: false },
  { key: 'committed_display',label: 'Committed',       visible: false, locked: false },
  { key: 'notes',            label: 'Notes',           visible: false, locked: false },
];

let columnConfig = loadColumnConfig(); // from localStorage or DEFAULT_COLUMNS
```

---

## Step 6 — localStorage Persistence

**Storage key:** `crm_column_config`

Save and load as JSON. Store only the array of `{key, visible}` objects plus
order (the array position = column order). Labels and locked status are
always taken from `DEFAULT_COLUMNS` at runtime — don't store them.

```javascript
function saveColumnConfig() {
  const toSave = columnConfig.map(c => ({ key: c.key, visible: c.visible }));
  localStorage.setItem('crm_column_config', JSON.stringify(toSave));
}

function loadColumnConfig() {
  const saved = localStorage.getItem('crm_column_config');
  if (!saved) return [...DEFAULT_COLUMNS];
  try {
    const parsed = JSON.parse(saved);
    // Merge saved order/visibility with DEFAULT_COLUMNS
    // (handles case where new columns were added since last save)
    const savedKeys = parsed.map(c => c.key);
    const merged = parsed.map(c => ({
      ...DEFAULT_COLUMNS.find(d => d.key === c.key),
      visible: c.visible
    })).filter(Boolean);
    // Append any new columns from DEFAULT_COLUMNS not in saved config
    DEFAULT_COLUMNS.forEach(d => {
      if (!savedKeys.includes(d.key)) merged.push({ ...d });
    });
    // Always ensure 'org' is first
    const orgIdx = merged.findIndex(c => c.key === 'org');
    if (orgIdx > 0) merged.unshift(merged.splice(orgIdx, 1)[0]);
    return merged;
  } catch {
    return [...DEFAULT_COLUMNS];
  }
}
```

---

## Step 7 — Table Rendering with Dynamic Columns

**File to modify:** `static/crm/crm.js`

Update the table render function to use `columnConfig` instead of hardcoded
columns:

```javascript
function renderTableHeader() {
  const visibleCols = columnConfig.filter(c => c.visible);
  // Render <th> for each visible column
  // Add sort click handler per column (for sortable columns)
}

function renderTableRow(prospect) {
  const visibleCols = columnConfig.filter(c => c.visible);
  // Render <td> for each visible column key
  // Apply per-column rendering (urgency badge, currency format, staleness dot, etc.)
  // Apply editable class for editable columns (existing Phase 3 logic)
}
```

**Per-column rendering rules:**

| Key | Render as |
|-----|-----------|
| `org` | Bold text, anchor link to `/crm/org/<n>` |
| `urgency` | Color badge (High/Med/Low) |
| `stage` | Plain text |
| `target_display` | Right-aligned text |
| `committed_display` | Right-aligned text |
| `next_action` | Truncated to 60 chars, full text in `title` tooltip |
| `notes` | Truncated to 60 chars, full text in `title` tooltip |
| `last_touch` | Date text + staleness dot (green/yellow/red) |
| `org_type` | Small type badge (same style as org detail page) |
| `assigned_to` | Plain text |
| `closing` | Plain text |
| `primary_contact` | Plain text |

**Editable columns** (Phase 3 inline edit applies when visible):
`stage`, `urgency`, `target_display`, `next_action`, `assigned_to`, `closing`

---

## Step 8 — CSS Additions

**File to modify:** `static/crm/crm.css`

```css
/* Column manager button */
.btn-columns { ... }

/* Column manager panel */
.column-manager-panel {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  width: 240px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  z-index: 100;
}
.column-manager-panel.hidden { display: none; }

/* Panel rows */
.col-row {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  gap: 10px;
  cursor: default;
  user-select: none;
}
.col-row:hover { background: #f8fafc; }
.col-row.dragging { opacity: 0.4; }
.col-row.drag-over { border-top: 2px solid #2563eb; }

/* Drag handle */
.drag-handle {
  color: #94a3b8;
  cursor: grab;
  font-size: 14px;
  padding: 2px 4px;
}
.col-row.locked .drag-handle { cursor: default; color: #e2e8f0; }

/* Shake animation for minimum column enforcement */
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}
.shake { animation: shake 0.3s ease; }

/* Right-aligned numeric columns */
td.col-target_display,
td.col-committed_display { text-align: right; }
th.col-target_display,
th.col-committed_display { text-align: right; }
```

---

## Step 9 — Verify

```bash
cd ~/arec-morning-briefing
python3 delivery/dashboard.py
```

Manual checks:
- [ ] "Columns ▼" button appears in the pipeline top bar
- [ ] Clicking button opens the column manager panel
- [ ] Panel shows all 12 columns with correct default checked states
- [ ] Clicking outside panel closes it; Escape closes it; ✕ closes it
- [ ] Checking "Type" adds Type column to the table
- [ ] Unchecking "Urgency" removes Urgency column from the table
- [ ] Cannot uncheck the last visible non-Organization column (shake animation)
- [ ] Organization checkbox is disabled/locked
- [ ] Drag handle on each non-locked row; Organization handle is inert
- [ ] Dragging "Stage" above "Urgency" reorders the table columns correctly
- [ ] Dragging a column attempts to go before Organization → snaps to second position
- [ ] Column order and visibility persist after page refresh
- [ ] "Reset to defaults" restores original 5 columns in original order
- [ ] Inline editing still works on editable columns after reorder
- [ ] Sort still works on column header click after reorder
- [ ] Notes and Next Action columns truncate long text with tooltip
- [ ] Last Touch column shows staleness dot when visible
- [ ] Type column shows badge styling when visible
- [ ] Expected and Committed columns are right-aligned
- [ ] No regressions on filters, sorting, offering tabs, or inline editing

---

## Files Modified

```
templates/crm/pipeline.html   ← MODIFIED: add Columns button
static/crm/crm.js             ← MODIFIED: columnConfig, panel logic, dynamic render
static/crm/crm.css            ← MODIFIED: panel and drag styles
```

No backend changes. No new API routes.
