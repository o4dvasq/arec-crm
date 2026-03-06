# CRM Phase 4 — Organization Detail Page Spec
**For Claude Code**
**Author:** Oscar Vasquez, COO — Avila Real Estate Capital
**Date:** March 2026
**Status:** Ready for Execution
**Depends on:** Phases 1, 2, and 3 complete

---

## Overview

Add a full organization detail page at `/crm/org/<name>`. Make org names in the
prospects table clickable links to this page. The page shows the org profile
(editable), all contacts for the org (editable), and all prospects for that org
across offerings (editable inline). Also adds "Add Prospect" for existing orgs,
and the ability to add/edit contacts. Interaction timeline and follow-up task
creation are deferred to Phase 5+.

---

## Environment

- App root: `~/arec-morning-briefing/`
- Flask app: `delivery/dashboard.py`, port 3001
- CRM parser: `sources/crm_reader.py` (Phase 1)
- Existing templates: `templates/crm/`
- Do not break any existing dashboard, Phase 2, or Phase 3 functionality

---

## Step 1 — Make Org Names Clickable in the Prospects Table

**File to modify:** `static/crm/crm.js`

When rendering the Organization cell in the table, wrap the org name in an
anchor tag:

```html
<a href="/crm/org/Merseyside Pension Fund" class="org-link">
  Merseyside Pension Fund
</a>
```

URL-encode the org name for the href:
```javascript
`/crm/org/${encodeURIComponent(prospect.org)}`
```

**File to modify:** `static/crm/crm.css`

```css
.org-link {
  color: #0f172a;
  text-decoration: none;
  font-weight: 600;
}
.org-link:hover {
  color: #2563eb;
  text-decoration: underline;
}
```

---

## Step 2 — New API Routes

**File to modify:** `delivery/dashboard.py`

Add the following routes to the existing `crm_bp` Blueprint.

---

### `GET /crm/api/org/<name>`

URL-decode `name`. Returns full org data:

```json
{
  "name": "Merseyside Pension Fund",
  "type": "INSTITUTIONAL",
  "notes": "UK-based pension fund.",
  "contacts": [
    {
      "name": "Susannah Friar",
      "organization": "Merseyside Pension Fund",
      "title": "",
      "email": "",
      "phone": "",
      "notes": ""
    }
  ],
  "prospects": [
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
      "last_touch_days": 4,
      "_heading_key": "Merseyside Pension Fund"
    }
  ]
}
```

Returns 404 JSON `{"ok": false, "error": "Organization not found"}` if org
does not exist in `organizations.md`.

---

### `PATCH /crm/api/org/<name>`

Update org profile fields.

**Request body (JSON):**
```json
{"type": "INSTITUTIONAL", "notes": "Updated notes here."}
```

Allowed fields: `type`, `notes`. Returns 400 for unknown fields.
Validates `type` against `load_crm_config()['org_types']`.

Calls `write_organization(name, data)`.

**Response:**
```json
{"ok": true, "name": "Merseyside Pension Fund", "type": "INSTITUTIONAL", "notes": "Updated notes here."}
```

---

### `POST /crm/api/contact`

Create a new contact under an existing org.

**Request body (JSON):**
```json
{
  "org": "Merseyside Pension Fund",
  "name": "John Smith",
  "title": "CIO",
  "email": "john@merseyside.gov.uk",
  "phone": "",
  "notes": ""
}
```

Validates: `org` and `name` required. `org` must exist in `organizations.md`.
Returns 400 if org not found or name blank.
Calls `write_contact(name, org, data)`.

**Response:**
```json
{"ok": true, "name": "John Smith", "org": "Merseyside Pension Fund"}
```

---

### `PATCH /crm/api/contact/<org>/<name>`

Update a contact's fields. URL-decode both `org` and `name`.

**Request body (JSON):** any subset of `title`, `email`, `phone`, `notes`.

Calls `write_contact(name, org, data)`.

**Response:**
```json
{"ok": true, "name": "John Smith", "org": "Merseyside Pension Fund"}
```

---

### `POST /crm/api/prospect`

Create a new prospect for an existing org under an existing offering.

**Request body (JSON):**
```json
{
  "org": "Merseyside Pension Fund",
  "offering": "AREC Debt Fund II",
  "stage": "1. New Lead",
  "target": "5000000",
  "primary_contact": "Susannah Friar",
  "closing": "",
  "urgency": "High",
  "assigned_to": "James Walton",
  "next_action": "",
  "notes": ""
}
```

**Validation:**
- `org` required, must exist in `organizations.md` — return 400 if not
- `offering` required, must exist in `offerings.md` — return 400 if not
- `stage` required, must be a known stage — return 400 if not
- A prospect for this org+offering must NOT already exist — return 409
  `{"ok": false, "error": "Prospect already exists for this org and offering"}`
- `target` parsed same as Phase 3 PATCH (strip `$`, commas → float → store
  as `"$X,XXX,XXX"`)

Calls `write_prospect(org, offering, data)`. Sets `committed` to `$0` and
`last_touch` to today automatically (not from request body).

**Response:** full prospect dict (same shape as `GET /crm/api/org/<name>`
prospects array entry).

---

## Step 3 — Page Route

**File to modify:** `delivery/dashboard.py`

```python
@crm_bp.route('/org/<path:name>')
def org_detail(name):
    import urllib.parse
    org_name = urllib.parse.unquote(name)
    config = load_crm_config()
    offerings = load_offerings()
    return render_template('crm/organization.html',
                           org_name=org_name,
                           config=config,
                           offerings=offerings)
```

Note: use `<path:name>` (not `<name>`) to handle org names with slashes or
special characters. The page loads the org data via JS on mount (calls
`GET /crm/api/org/<name>`), not server-side render. This keeps the pattern
consistent with the pipeline page.

---

## Step 4 — Create `templates/crm/organization.html`

Extends `crm/_layout.html`.

Pass `window.CRM_CONFIG` and `window.CRM_OFFERINGS` as JS variables in a
`<script>` block (same pattern as pipeline.html):

```html
<script>
  window.ORG_NAME = {{ org_name | tojson }};
  window.CRM_CONFIG = { ... };
  window.CRM_OFFERINGS = {{ offerings | tojson }};
</script>
```

The page has three sections stacked vertically. On load, call
`GET /crm/api/org/<name>` to populate all sections.

---

### Page Header

```
← Pipeline          Merseyside Pension Fund          INSTITUTIONAL
```

- "← Pipeline" — left-aligned back link to `/crm`
- Org name — centered, large heading
- Type badge — right-aligned, same badge style as the pipeline table

---

### Section 1 — Org Profile

A compact editable card.

**Fields:**

| Field | Type | Edit behavior |
|-------|------|---------------|
| Type | Dropdown | Click → `<select>` → blur/change saves via PATCH `/crm/api/org/<name>` |
| Notes | Textarea | Click → `<textarea>` → blur saves via PATCH `/crm/api/org/<name>` |

Display when not editing:
```
Type:   INSTITUTIONAL
Notes:  UK-based pension fund. [click to edit]
```

Empty Notes field shows a placeholder: `Click to add notes...` in muted gray.

Save feedback: same green flash / red flash pattern as Phase 3.

---

### Section 2 — Contacts

A compact table of all contacts for this org.

**Columns:** Name | Title | Email | Phone | Actions

**Each row is inline-editable:**
- Title, Email, Phone: click cell → text input → blur saves via
  `PATCH /crm/api/contact/<org>/<name>`
- Name: not editable inline (changing a contact's name risks breaking
  cross-references; defer to a future phase)
- Actions column: a small "×" delete button — **Phase 4 does not implement
  contact delete**; render the button as disabled/greyed out with tooltip
  "Delete available in future update"

**"Add Contact" button** below the table opens an inline form row at the
bottom of the contacts table:

```
[ Name* ]  [ Title ]  [ Email ]  [ Phone ]  [Add]  [Cancel]
```

- Name is required (show inline validation error if blank on submit)
- Submit calls `POST /crm/api/contact`
- On success: append new row to contacts table, clear the form
- On cancel: hide the form row

If the org has no contacts, show:
```
No contacts on file.   [+ Add Contact]
```

---

### Section 3 — Prospects Across Offerings

A table showing all prospect records for this org, one row per offering.

**Columns:**

| Column | Field | Editable |
|--------|-------|----------|
| Offering | `offering` | No |
| Stage | `stage` | Yes — dropdown |
| Expected | `target_display` | Yes — number input |
| Urgency | `urgency` | Yes — dropdown |
| Closing | `closing` | Yes — dropdown |
| Assigned To | `assigned_to` | Yes — dropdown |
| Next Action | `next_action` | Yes — text input |
| Last Touch | `last_touch` | No — auto-updated |

Inline editing uses the **exact same `saveField()` function** from Phase 3
(calls `PATCH /crm/api/prospect/field`). Re-use `crm.js` logic — do not
duplicate it.

Last Touch cell displays: `YYYY-MM-DD` + staleness dot (green/yellow/red,
same thresholds as pipeline table: <7d green, 8–14d yellow, 15+d red).

**"Add to Offering" button** below the table:

Opens a compact inline form:

```
Offering: [ dropdown of offerings not yet represented for this org ▼ ]
Stage:    [ 1. New Lead ▼ ]
Expected: [ $________ ]
Urgency:  [ ▼ ]   Assigned To: [ ▼ ]   Contact: [ dropdown of org's contacts ▼ ]
[ Add ]  [ Cancel ]
```

- Offering dropdown: shows only offerings where this org does NOT already
  have a prospect (i.e., not yet in the prospects table above)
- If the org already has a prospect for every offering, hide the button and
  show: `Prospect exists for all offerings.`
- Contact dropdown: populated from the contacts already loaded for this org
- Submit calls `POST /crm/api/prospect`
- On success: append new row to the prospects table, clear the form
- On cancel: hide the form

If the org has no prospects at all, show:
```
No prospects on file.   [+ Add to Offering]
```

---

## Step 5 — JavaScript: `static/crm/crm.js`

Add the following to the existing `crm.js` file. Do not create a separate JS
file.

### On org detail page load

```javascript
// Detect we're on the org detail page
if (window.ORG_NAME) {
  fetchOrgDetail(window.ORG_NAME);
}
```

### `fetchOrgDetail(orgName)`

```
1. GET /crm/api/org/<encoded org name>
2. On success: renderOrgProfile(), renderContacts(), renderProspects()
3. On 404: show full-page error "Organization not found"
4. On network error: show "Failed to load — try refreshing"
```

### `renderOrgProfile(orgData)`

Populate Section 1 with org type and notes. Wire up click-to-edit.

### `renderContacts(contacts)`

Render contacts table (Section 2). Wire up:
- Inline editing for Title, Email, Phone via `PATCH /crm/api/contact/<org>/<name>`
- "Add Contact" button → inline form row
- Use same green/red flash save feedback as Phase 3

### `renderProspects(prospects)`

Render prospects table (Section 3). Wire up inline editing using the existing
`saveField()` from Phase 3. Wire up "Add to Offering" button → inline form.

---

## Step 6 — CSS Additions

**File to modify:** `static/crm/crm.css`

Add styles for:

```css
/* Org detail page layout */
.org-detail-header { ... }   /* back link + name + type badge row */
.org-section { ... }         /* card wrapper for each section */
.org-section h2 { ... }      /* section heading */

/* Contacts table */
.contacts-table { ... }
.add-contact-form-row { ... }  /* inline form at bottom of contacts table */

/* Notes placeholder */
.notes-placeholder {
  color: #94a3b8;
  font-style: italic;
  cursor: text;
}

/* "Add to Offering" form */
.add-prospect-form { ... }

/* Disabled action button */
.btn-disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
```

---

## Step 7 — Verify

```bash
cd ~/arec-morning-briefing
python3 delivery/dashboard.py
```

Manual checks:
- [ ] Org names in the pipeline table are now clickable links
- [ ] Clicking an org name navigates to `/crm/org/<name>` (URL-encoded)
- [ ] Page header shows org name, type badge, and "← Pipeline" back link
- [ ] Section 1: Type dropdown edits and saves via PATCH org
- [ ] Section 1: Notes textarea edits and saves via PATCH org
- [ ] Section 1: Empty notes shows placeholder text
- [ ] Section 2: Contacts table shows all contacts for the org
- [ ] Section 2: Title, Email, Phone are inline-editable and save
- [ ] Section 2: "Add Contact" button opens inline form
- [ ] Section 2: New contact appears in table after successful add
- [ ] Section 2: Name field is not editable
- [ ] Section 2: Delete button renders but is visibly disabled
- [ ] Section 3: All prospects for this org shown across offerings
- [ ] Section 3: Stage, Expected, Urgency, Closing, Assigned To, Next Action editable
- [ ] Section 3: Last Touch updates after any field edit (auto, from saveField)
- [ ] Section 3: "Add to Offering" dropdown shows only offerings without existing prospect
- [ ] Section 3: New prospect appears in table after successful add
- [ ] Section 3: If org has prospects for all offerings, button is hidden
- [ ] 404 handling: navigate to `/crm/org/DoesNotExist` → clean error message
- [ ] POST /crm/api/prospect returns 409 if prospect already exists for org+offering
- [ ] No regressions on pipeline table, inline editing, or dashboard

---

## What's NOT In This Phase

- No interaction timeline (deferred — Phase 5+)
- No follow-up task creation / TASKS.md integration (deferred)
- No new org creation (Add Prospect for existing orgs only)
- No contact delete (deferred)
- No prospect delete (deferred)
- No Graph auto-capture (Phase 5)
- No analytics (Phase 6)

---

## Files Modified / Created

```
delivery/dashboard.py              ← MODIFIED: 4 new API routes + org_detail page route
templates/crm/organization.html    ← NEW
static/crm/crm.js                  ← MODIFIED: org detail page logic
static/crm/crm.css                 ← MODIFIED: org detail page styles
```

---

*When Phase 4 is complete and all manual checks pass, return for the Phase 5
spec (Microsoft Graph auto-capture of investor interactions).*
