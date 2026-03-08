# CRM Phase 3 — Inline Editing & Write APIs Spec
**For Claude Code**
**Author:** Oscar Vasquez, COO — Avila Real Estate Capital
**Date:** March 2026
**Status:** Ready for Execution
**Depends on:** Phase 1 and Phase 2 complete

---

## Overview

Add inline editing to the prospects table. Users click any editable cell to edit
it in place; saving writes back to the markdown file via a PATCH API. Also adds
a "Next Action" column to the default table view. No Add Prospect, no delete in
this phase — pure field-level editing of existing records.

---

## Environment

- App root: `~/arec-morning-briefing/`
- Flask app: `delivery/dashboard.py`, port 3001
- CRM parser: `sources/crm_reader.py` (Phase 1)
- Static/templates: `static/crm/`, `templates/crm/`
- Do not break any existing dashboard or Phase 2 functionality

---

## Step 1 — Add "Next Action" Column

**File to modify:** `templates/crm/pipeline.html` and `static/crm/crm.js`

Add "Next Action" as the 5th column in the default table view, after "Expected".

Updated column order:

| # | Column | Field | Editable in Phase 3 |
|---|--------|-------|---------------------|
| 1 | Organization | `org` | No |
| 2 | Urgency | `urgency` | Yes — dropdown |
| 3 | Stage | `stage` | Yes — dropdown |
| 4 | Expected | `target_display` | Yes — number input |
| 5 | Next Action | `next_action` | Yes — text input |

The existing sort and filter behavior must continue to work after this column
is added.

---

## Step 2 — New API Route: PATCH Prospect Field

**File to modify:** `delivery/dashboard.py`

Add one new route to the existing `crm_bp` Blueprint:

### `PATCH /crm/api/prospect/field`

**Request body (JSON):**
```json
{
  "org": "Merseyside Pension Fund",
  "offering": "AREC Debt Fund II",
  "field": "stage",
  "value": "7. Legal / DD"
}
```

**Logic:**
1. Validate `org`, `offering`, `field`, `value` are all present — return 400 if any missing
2. Validate `field` is in the allowed editable fields list (see below) — return 400 if not
3. For dropdown fields, validate `value` is a known option — return 400 if not
4. Call `update_prospect_field(org, offering, field, value)` from `crm_reader.py`
   - This also auto-updates `last_touch` to today (per Phase 1 spec)
5. Return the updated prospect record as JSON:

```json
{
  "ok": true,
  "org": "Merseyside Pension Fund",
  "offering": "AREC Debt Fund II",
  "field": "stage",
  "value": "7. Legal / DD",
  "last_touch": "2026-03-01"
}
```

**On error:**
```json
{"ok": false, "error": "Invalid field: primary_contact"}
```

**Allowed editable fields (server-side whitelist):**
```python
EDITABLE_FIELDS = {
    'stage', 'urgency', 'target', 'assigned_to',
    'next_action', 'notes', 'closing'
}
```

**Dropdown validation (server-side):**

| Field | Valid values |
|-------|-------------|
| `stage` | All stages from `load_crm_config()['stages']` |
| `urgency` | `['High', 'Med', 'Low', '']` |
| `closing` | `['1st', '2nd', 'Final', '']` |
| `assigned_to` | All team members from `load_crm_config()['team']`, plus `''` |
| `target` | Any string parseable as a non-negative number (after stripping `$`, commas) |
| `next_action` | Any string (no validation) |
| `notes` | Any string (no validation) |

For `target`: parse the submitted value as a float. Strip any `$`, commas, or
whitespace before parsing. Store as full integer string with `$` prefix:
`"5000000"` → `"$5,000,000"`. Return 400 if value cannot be parsed as a number.

---

## Step 3 — Inline Editing: Client-Side

**File to modify:** `static/crm/crm.js` and `static/crm/crm.css`

### Triggering Edit Mode

- **Click** on any editable cell → enters edit mode for that cell
- Non-editable cells (Organization): no cursor change, no edit behavior
- Only one cell can be in edit mode at a time. If another cell is already
  being edited, save it (blur) before opening the new one.
- Visual indicator: editable cells show a subtle edit cursor (`cursor: text`
  or `cursor: pointer`) on hover, plus a very faint blue left border accent
  or background tint to signal editability. Keep it understated.

### Edit Controls by Field Type

#### Dropdown fields: `stage`, `urgency`, `closing`, `assigned_to`

1. Replace cell content with a `<select>` element
2. Pre-select the current value
3. Populate options from the config data already in memory
   (loaded when the page was rendered — pass config as a JS variable from the template)
4. On `change` event → immediately call `saveField()`, no need to press Enter
5. On `Escape` → cancel, restore original value, exit edit mode

**`assigned_to` special case:** The field may contain multiple team members
separated by `; `. In Phase 3, treat it as a single-select (pick one person).
Multi-select is deferred to a later phase.

#### Number input: `target`

1. Replace cell content with `<input type="text">` (not `type="number"` —
   avoids browser formatting conflicts)
2. Pre-fill with the raw stored value stripped of `$` and commas
   (e.g., `"$5,000,000"` → `"5000000"`)
3. On `Enter` or blur → call `saveField()`
4. On `Escape` → cancel, restore original display value, exit edit mode
5. After successful save, re-render cell with updated `target_display`
   (abbreviated format, e.g. `$5M`)

#### Text input: `next_action`

1. Replace cell content with `<input type="text">`
2. Pre-fill with current value
3. On `Enter` or blur → call `saveField()`
4. On `Escape` → cancel, restore original value, exit edit mode

#### Textarea: `notes`

Notes is not shown as a default column, but the field is editable via the
table row's edit affordance. Defer `notes` editing to Phase 4 (org detail page).
Do not implement notes inline editing in Phase 3.

---

### `saveField(org, offering, field, value, cellElement)`

```
1. Show saving indicator on the cell (subtle spinner or opacity reduction)
2. PATCH /crm/api/prospect/field with {org, offering, field, value}
3. On success:
   a. Update the in-memory allProspects array for this record
   b. Re-render the cell with the new display value
   c. Flash cell green briefly (150ms green background → fade out)
   d. If field was 'stage' or 'urgency', re-sort the table in place
      (the row may move position)
   e. Update last_touch on the in-memory record with the returned value
4. On error:
   a. Flash cell red briefly
   b. Show a small inline error tooltip with the error message
   c. Restore the original value in the cell
   d. Log error to console
5. Exit edit mode regardless of success/failure
```

### Re-sorting After Edit

When `stage` or `urgency` is edited, the row's position in the sort order may
change. After a successful save:
1. Update the record in `allProspects`
2. Re-run the current sort on the full filtered array
3. Re-render the entire table body (not just the row)
4. Briefly highlight the moved row so the user can find it (`background: #fefce8`
   for 1 second, fade out)

---

## Step 4 — Visual Styling for Edit States

**File to modify:** `static/crm/crm.css`

Add these CSS rules:

```css
/* Editable cell hover hint */
td.editable {
  cursor: text;
}
td.editable:hover {
  background: #eff6ff;  /* very faint blue */
}

/* Active edit mode */
td.editing {
  background: #dbeafe;
  padding: 0;  /* input fills the cell */
}
td.editing input,
td.editing select {
  width: 100%;
  border: none;
  background: transparent;
  padding: 8px 10px;
  font: inherit;
  outline: 2px solid #2563eb;
  outline-offset: -2px;
}

/* Save feedback */
td.save-success {
  background: #dcfce7;
  transition: background 0.4s ease;
}
td.save-error {
  background: #fee2e2;
  transition: background 0.4s ease;
}

/* Row highlight after re-sort */
tr.relocated {
  background: #fefce8;
  transition: background 1s ease;
}
```

---

## Step 5 — Pass Config to JavaScript

**File to modify:** `templates/crm/pipeline.html`

The inline edit dropdowns need the config values (stages, urgency levels,
closing options, team members) available in JavaScript without an extra API call.

In the template, emit the config as a JS variable in a `<script>` block:

```html
<script>
  window.CRM_CONFIG = {
    stages: {{ config.stages | tojson }},
    urgency_levels: {{ config.urgency_levels | tojson }},
    closing_options: {{ config.closing_options | tojson }},
    team: {{ config.team | tojson }}
  };
</script>
```

In `crm.js`, read from `window.CRM_CONFIG` when building dropdown options.
The `config` variable is already passed to the template from the `/crm` route
(established in Phase 2).

---

## Step 6 — Verify

```bash
cd ~/arec-morning-briefing
python3 delivery/dashboard.py
```

Manual checks:
- [ ] "Next Action" column appears as 5th column in the table
- [ ] Existing sort and filter behavior still works
- [ ] Clicking an editable cell (Stage, Urgency, Expected, Next Action) enters edit mode
- [ ] Clicking a non-editable cell (Organization) does nothing
- [ ] Stage dropdown shows all pipeline stages; selecting one saves and re-sorts
- [ ] Urgency dropdown shows High/Med/Low/blank; selecting one saves and re-sorts
- [ ] Expected input: entering a plain number saves; cell re-renders as abbreviated ($5M)
- [ ] Next Action input: typing and pressing Enter saves; blur also saves
- [ ] Escape on any edit cancels and restores original value
- [ ] Successful save flashes cell green
- [ ] Failed save flashes cell red and restores original value
- [ ] After Stage/Urgency edit, row re-sorts and relocated row briefly highlights
- [ ] Only one cell in edit mode at a time
- [ ] PATCH /crm/api/prospect/field returns 400 for invalid field names
- [ ] PATCH /crm/api/prospect/field returns 400 for invalid dropdown values
- [ ] PATCH /crm/api/prospect/field returns 400 for non-numeric target values
- [ ] Verify the markdown file was actually updated:
      `grep -A 12 "Merseyside" ~/Dropbox/Tech/ClaudeProductivity/crm/prospects.md`
- [ ] No regressions on existing dashboard or Phase 2 features

---

## What's NOT In This Phase

- No Add Prospect (Phase 4)
- No delete prospect (Phase 4)
- No notes inline editing (Phase 4 — org detail page)
- No Primary Contact editing (Phase 4 — requires contact lookup per org)
- No multi-select for Assigned To (future)
- No interaction logging on edit (deferred by design)
- No org detail page (Phase 4)

---

## Files Modified / Created

```
delivery/dashboard.py           ← MODIFIED: add PATCH /crm/api/prospect/field
templates/crm/pipeline.html     ← MODIFIED: add Next Action column + CRM_CONFIG script block
static/crm/crm.css              ← MODIFIED: add edit state styles
static/crm/crm.js               ← MODIFIED: add inline edit logic + saveField()
```

---

*When Phase 3 is complete and all manual checks pass, return for the Phase 4
spec (organization detail page, Add Prospect, interaction logging).*
