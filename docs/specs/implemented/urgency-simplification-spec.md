# AREC CRM — Urgency Simplification
**Spec Type:** Data model change + UI update  
**Depends on:** CRM Phase 1 (data layer), Phase 2 (pipeline table)  
**Scope:** crm_reader.py, prospects.md, pipeline.html, crm.css, crm.js, PWA (arec-mobile.html)

---

## Summary

Replace the three-value Urgency field (`High`, `Med`, `Low`) with a boolean checkbox.
A prospect is either **Urgent** or it isn't. Urgent rows are visually highlighted in the
Pipeline table with a light yellow row background.

---

## 1. Data Model Change

### 1.1 Field Definition

| Field | Old | New |
|-------|-----|-----|
| Urgency | `High` / `Med` / `Low` / blank | `Yes` / blank |

**Storage rules:**
- Urgent: `- **Urgent:** Yes`
- Not urgent: `- **Urgent:** ` (field present, value blank) — OR omit entirely; parser must handle both

### 1.2 Migration Script

Create `scripts/migrate_urgency.py`:

```
Purpose: One-time migration of prospects.md
Logic:
  - Read prospects.md via crm_reader.py load_prospects()
  - For each prospect:
      if Urgency == "High" → set Urgent = "Yes"
      if Urgency in ("Med", "Low", "") → set Urgent = ""
  - Remove the old Urgency field from each prospect section
  - Write updated record via write_prospect()
  - Print summary: X marked Urgent, Y cleared
```

Run this script once after deploying the code changes. Do not auto-run on import.

---

## 2. Parser Changes — `sources/crm_reader.py`

### 2.1 Remove
- All references to `Urgency` field (High/Med/Low enum)
- `load_crm_config()` urgency levels list (remove from config.md too)

### 2.2 Add
- Parse `- **Urgent:** Value` → store as boolean in prospect dict: `urgent: True/False`
  - `"Yes"` (case-insensitive) → `True`
  - blank or missing → `False`
- Write back: if `urgent == True` → `- **Urgent:** Yes`; if `False` → `- **Urgent:** ` (blank value, field always written)

### 2.3 Existing functions that reference Urgency
Update all references:
- `load_prospects()` — parse new field
- `write_prospect()` — write new field format
- `update_prospect_field()` — accept `urgent` as boolean field
- `get_pipeline_summary()` — remove urgency breakdowns if any

---

## 3. Config Change — `crm/config.md`

Remove the `## Urgency Levels` section entirely:

```markdown
## Urgency Levels     ← DELETE THIS SECTION
- High                ← DELETE
- Med                 ← DELETE
- Low                 ← DELETE
```

---

## 4. API Changes — `delivery/dashboard.py`

### PATCH `/crm/api/prospect/<org>/<offering>/field`
- Accept `urgent` as a valid field name
- Value: `true`/`false` (boolean JSON) or `"Yes"`/`""` (string) — normalize on receipt
- Write `"Yes"` or `""` to file accordingly

### GET `/crm/api/prospects?offering=X`
- Each prospect JSON object: replace `urgency: "High"` with `urgent: true/false`

---

## 5. Pipeline Table — `templates/crm/pipeline.html` + `static/crm/crm.js`

### 5.1 Column Change

Replace the **Urgency** column with an **Urgent** column:

| Old | New |
|-----|-----|
| Color badge (High/Med/Low) | Checkbox (checked = urgent) |

**Column header:** `Urgent`  
**Cell content:** A single checkbox `<input type="checkbox">`  
**Checked state:** `prospect.urgent === true`

### 5.2 Row Highlighting

When a prospect is urgent, apply a light yellow background to the **entire row**:

```css
tr.urgent-row {
  background-color: #fefce8;  /* Tailwind yellow-50 equivalent */
}

tr.urgent-row:hover {
  background-color: #fef9c3;  /* Slightly deeper on hover */
}
```

Apply class in JS when rendering rows:
```javascript
tr.classList.toggle('urgent-row', prospect.urgent);
```

### 5.3 Inline Editing

**Checkbox interaction:**
- Click checkbox → immediately fires PATCH to `/crm/api/prospect/<org>/<offering>/field`
  with `{ field: "urgent", value: <new boolean> }`
- On success: toggle `urgent-row` class on the row (no full table re-render needed)
- On error: revert checkbox state, show error toast

No confirm dialog needed — checkbox is instantly reversible.

### 5.4 Filter Chip

Replace the Urgency dropdown filter with a simple toggle button:

```
[ ⚡ Urgent Only ]   ← inactive state (outlined button)
[ ⚡ Urgent Only ]   ← active state (filled yellow background, bold)
```

**Behavior:**
- Off (default): show all prospects
- On: show only rows where `prospect.urgent === true`
- Toggle state persists in URL query params (`?urgent=1`) and localStorage

**HTML:**
```html
<button id="urgentFilter" class="filter-chip" data-active="false">
  ⚡ Urgent Only
</button>
```

**CSS:**
```css
.filter-chip[data-active="true"] {
  background-color: #fef08a;
  border-color: #ca8a04;
  font-weight: 600;
}
```

### 5.5 Default Sort

Remove Urgency from the default sort order. New default:

```
Stage descending → Target descending
```

Urgent rows will naturally stand out via row color without needing sort priority.

---

## 6. PWA Changes — `arec-mobile.html`

### 6.1 Prospect Card

Replace urgency badge with an urgent indicator:

**Old:** `🔴 High · James Walton`  
**New:** `⚡ Urgent · James Walton` (only shown when urgent) OR just `James Walton` (when not urgent)

### 6.2 Card Highlight

When urgent, apply a left border accent to the card:

```css
.prospect-card.urgent {
  border-left: 4px solid #ca8a04;
  background-color: #fefce8;
}
```

### 6.3 Edit Sheet

Replace Urgency dropdown with a toggle row:

```
Urgent     [ toggle switch ]
```

Use a native-style iOS toggle (`<input type="checkbox">` styled as a pill switch).

On save: writes `Yes` or blank to the `Urgent` field in prospects.md.

### 6.4 Filter

Replace Urgency filter chip with `⚡ Urgent` toggle chip (same behavior as desktop).

### 6.5 Parser Update

```javascript
// Old
prospect.urgency = fields['urgency'] || '';

// New
prospect.urgent = (fields['urgent'] || '').toLowerCase() === 'yes';

// Write back
lines.push(`- **Urgent:** ${prospect.urgent ? 'Yes' : ''}`);
```

---

## 7. Checklist for Claude Code

- [ ] Create `scripts/migrate_urgency.py`
- [ ] Update `sources/crm_reader.py` — parse/write `Urgent` boolean field
- [ ] Update `crm/config.md` — remove Urgency Levels section
- [ ] Update `delivery/dashboard.py` — API accepts/returns `urgent` boolean
- [ ] Update `templates/crm/pipeline.html` — checkbox column, filter chip
- [ ] Update `static/crm/crm.css` — `.urgent-row` yellow highlight, filter chip active state
- [ ] Update `static/crm/crm.js` — checkbox inline edit, row class toggle, filter logic
- [ ] Update `arec-mobile.html` — card style, edit sheet toggle, filter chip, JS parser
- [ ] Run `migrate_urgency.py` once on live data
- [ ] Verify: urgent rows show yellow in desktop table
- [ ] Verify: checkbox click updates file and toggling row color without page reload
- [ ] Verify: Urgent Only filter hides non-urgent rows
- [ ] Verify: PWA urgent cards show left border + yellow tint
- [ ] Verify: Python parsers and JS parsers round-trip `Urgent: Yes` / blank correctly

---

## 8. Files Modified

| File | Change |
|------|--------|
| `scripts/migrate_urgency.py` | NEW — one-time migration |
| `sources/crm_reader.py` | Parse/write `Urgent` boolean |
| `crm/config.md` | Remove Urgency Levels section |
| `crm/prospects.md` | Updated by migration script |
| `delivery/dashboard.py` | API field handling |
| `templates/crm/pipeline.html` | Checkbox column, filter chip |
| `static/crm/crm.css` | Row highlight, chip styles |
| `static/crm/crm.js` | Edit, filter, row class logic |
| `arec-mobile.html` | Card style, edit toggle, parser |

**Do not modify:** `organizations.md`, `contacts.md`, `offerings.md`, `interactions.md`, `memory_reader.py`, existing dashboard columns.
