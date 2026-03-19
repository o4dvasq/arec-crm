# SPEC: Meeting Detail Modal + Row Click Behavior + Remove Time Field
**Project:** arec-crm | **Date:** 2026-03-18 | **Status:** Ready for implementation

---

## 1. Objective

The `/crm/meetings` page currently shows a placeholder `alert()` when any meeting row is clicked. This spec replaces that placeholder with real behavior:

1. **Rename** the "Organization" column to "Prospect" — on the table header and in the Add Meeting modal label/dropdown
2. **Prospect cell click** (when a prospect link exists) → navigates to the prospect detail page
3. **Click anywhere else on the row** (or on a `—` Prospect cell) → opens the existing Add Meeting modal in **edit mode**, pre-populated from the selected meeting
4. **Delete** capability with inline confirmation, visible only in edit mode
5. **Remove the Meeting Time field** from the modal entirely (both Add and Edit modes)

---

## 2. Scope

**In scope:**
- Rename "Organization" → "Prospect" on the meetings table column header, modal field label, and modal dropdown placeholder text
- Replace `openMeetingDetail()` stub with edit modal behavior
- Reuse the existing `add-meeting-modal` for edit mode (no second modal)
- Pre-populate all modal fields from the selected meeting's data in edit mode
- Add Delete with inline confirmation (no `confirm()` dialog)
- Remove `form-time` input from the modal HTML

**Out of scope:**
- New fields or schema changes to `meetings.json`
- Meeting notes/intelligence extraction or AI processing
- Changes to how meetings are created or stored beyond removing time collection
- The `meeting_detail.html` page (separate template for individual meeting viewing — not touched)

---

## 3. Business Rules

### Column Rename

Every visible instance of "Organization" on the meetings page becomes "Prospect":
- Table column header: `ORGANIZATION` → `PROSPECT`
- Modal field label: `Organization` → `Prospect`
- Modal dropdown placeholder: `— Select Organization —` → `— Select Prospect —`

The underlying field on the meeting record remains `org` — this is a display rename only.

### Row Click Behavior

The current implementation assigns `row.onclick = () => openMeetingDetail(m.id)` to every row. The org cell's `<a>` link already calls `event.stopPropagation()`, which prevents row clicks when a prospect link exists. This behavior is preserved. The only change is replacing the `openMeetingDetail()` stub with edit modal logic.

| Click target | Behavior |
|---|---|
| Prospect cell — linked name (`<a>` tag) | Navigate to prospect detail page (existing link behavior — no change) |
| Prospect cell — `—` (no org/offering) | Row click fires → open edit modal |
| Any other cell (Date, Title, Attendees, Notes) | Row click fires → open edit modal |

The Prospect name link is already constructed in `renderTable()` as:
```javascript
`/crm/prospect/${encodeURIComponent(m.offering)}/${encodeURIComponent(m.org)}/detail`
```
This is only rendered when both `m.org` and `m.offering` are non-empty. The condition and URL pattern are unchanged.

### Modal: Add vs. Edit Mode

The same modal (`add-meeting-modal`) serves both modes. Mode is controlled by a new JS variable (e.g., `currentEditMeetingId`) — `null` for Add mode, the meeting UUID for Edit mode.

| Aspect | Add Mode | Edit Mode |
|---|---|---|
| Trigger | "Add Meeting" button (existing) | Row click |
| Modal header | "Add Meeting" | "Edit Meeting" |
| Fields | Empty / defaults | Pre-populated from meeting record |
| Primary button text | "Add Meeting" | "Save Changes" |
| Primary button action | POST to `/crm/api/meetings` | PATCH to `/crm/api/meetings/<id>` |
| Delete link | Hidden | Visible (bottom-left of footer) |

### Pre-Population (Edit Mode)

When `openMeetingDetail(meetingId)` fires, look up the meeting from the `allMeetings` array already in memory (no additional API call needed). Populate the modal fields:

| Field | DOM ID | Source field |
|---|---|---|
| Prospect (org) dropdown | `form-org` | `m.org` — select the matching `<option>` by value |
| Offering | `form-offering` | `m.offering` |
| Meeting Date | `form-date` | `m.meeting_date` (YYYY-MM-DD — compatible with `<input type="date">`) |
| Title | `form-title` | `m.title` |
| Attendees | `form-attendees` | `m.attendees` |
| Notes | `form-notes` | `m.notes_raw` |

`form-time` is removed entirely — do not populate it.

If `m.org` has no matching `<option>` in the dropdown (e.g., org was deleted), leave the dropdown at its default (do not error).

Set `currentEditMeetingId = m.id` before opening. Clear it to `null` when the modal closes.

### Save (Edit Mode)

On form submit in edit mode, PATCH to `/crm/api/meetings/<currentEditMeetingId>` with the form fields (same payload shape as the existing POST, minus `meeting_time`). On success: reload and re-render the table, close the modal.

### Delete

- **Placement:** Red text link — "Delete Meeting" — at the bottom-left of the modal footer. The existing Save/Cancel buttons remain on the right.
- **Visibility:** Only shown in edit mode. Hidden (or absent) in add mode.
- **First click:** Replace link text inline with: `Are you sure? Yes · No` — both words clickable. No browser dialog.
- **"Yes":** DELETE to `/crm/api/meetings/<currentEditMeetingId>`. On success: remove the row from the DOM (or reload the table), close the modal.
- **"No":** Restore the "Delete Meeting" link text.

### Remove Meeting Time

- Remove the `form-time` `<input type="time">` and its `<label>` from the modal HTML entirely — not hidden, deleted.
- The `meeting_time` field remains in `meetings.json` for existing records — do not touch stored data.
- The POST and PATCH handlers already allow `meeting_time` to be absent — no backend changes needed for this.

---

## 4. Data Model / Schema Changes

**No schema changes.** The `meetings.json` record structure is unchanged. The `meeting_time` field continues to exist on existing records; it is simply no longer collected or displayed.

**Existing meeting record shape** (for reference):
```json
{
  "id": "<uuid>",
  "org": "Alpha Curve",
  "offering": "Avila Debt Fund II",
  "meeting_date": "2026-03-16",
  "meeting_time": "09:15 PT",
  "title": "Initial intro call",
  "attendees": "Oscar, Tony",
  "notes_raw": "...",
  "notes_summary": null,
  "status": "completed",
  "source": "manual",
  "created_by": "oscar",
  "created_at": "2026-03-16T...",
  "updated_at": "2026-03-16T..."
}
```

---

## 5. UI / Interface

### Modal Footer Layout (Edit Mode)

```
[ Delete Meeting (red, left) ]          [ Cancel ]  [ Save Changes ]
```

### Delete Confirmation (inline)

When "Delete Meeting" is clicked, replace the link text in-place with:

```
Are you sure?  Yes  ·  No
```

"Yes" is styled red, "No" is styled gray/muted. Neither uses a `<button>` — inline `<span>` elements with click handlers are fine. "No" restores the original "Delete Meeting" link.

### Meetings Table

- Column header changes: `ORGANIZATION` → `PROSPECT` (no other column changes)
- Prospect cell: existing rendering logic unchanged — link when both `org` and `offering` present, `—` otherwise

### Modal Fields After This Change

The modal (both modes) contains these fields in order:
1. Prospect (org dropdown) — renamed label
2. Offering (text)
3. Meeting Date (date)
4. Title (text)
5. Attendees (text)
6. Notes (textarea)
7. Process with AI checkbox (conditional, existing behavior)

`Meeting Time` is removed entirely.

---

## 6. Integration Points

### Backend — `crm_reader.py`

Both needed functions already exist:

| Function | Signature | Location |
|---|---|---|
| `update_meeting` | `update_meeting(meeting_id: str, **fields) -> dict \| None` | `crm_reader.py` line ~2189 |
| `delete_meeting` | `delete_meeting(meeting_id: str) -> bool` | `crm_reader.py` line ~2230 |

`update_meeting` accepts arbitrary keyword fields and protects `id`, `created_by`, `created_at` from overwrite. It auto-transitions status to `completed` if `notes_raw` is added.

### Backend — API Routes (`crm_blueprint.py`)

Verify that PATCH and DELETE routes for meetings exist. They are expected at:
- `PATCH /crm/api/meetings/<meeting_id>` — calls `update_meeting()`
- `DELETE /crm/api/meetings/<meeting_id>` — calls `delete_meeting()`

If either route is missing, add it following the same pattern as the existing POST `/crm/api/meetings` route (line ~1937). Both routes should return JSON and respect the `@login_required` decorator.

### Frontend — `crm_meetings.html`

All JS logic lives inline in `crm_meetings.html`. The `allMeetings` array (populated at page load from `/crm/api/meetings`) is the data source for pre-population — no additional fetch is needed in the edit flow.

**Key existing JS to modify:**

`openMeetingDetail(meetingId)` — currently lines 409–411, the stub. Replace entirely:
```javascript
function openMeetingDetail(meetingId) {
  const m = allMeetings.find(x => x.id === meetingId);
  if (!m) return;
  currentEditMeetingId = meetingId;
  // Set modal to edit mode, populate fields, open modal
}
```

`closeAddMeetingModal()` — clear `currentEditMeetingId = null` and reset modal to add mode when called.

Form submit handler — branch on `currentEditMeetingId`: if set, PATCH; if null, POST (existing behavior).

---

## 7. Constraints

- Reuse `add-meeting-modal` — do not create a second modal
- No new JS libraries or dependencies
- Prospect links must use the existing URL pattern: `/crm/prospect/<offering>/<org>/detail`
- `form-time` input must be fully removed from the HTML — not hidden with CSS
- Existing `meetings.json` records with `meeting_time` data must not be altered
- Delete confirmation must be inline — no `confirm()` dialog, no `alert()`
- Dark theme styling must be consistent with the rest of the page
- `add-meeting-modal` modal ID and `add-meeting-form` form ID are preserved (other code may reference them)
- Both `requirements.txt` files kept in sync if any Python deps change (none expected here)

---

## 8. Acceptance Criteria

- [ ] "Organization" column header reads "PROSPECT" on the meetings table
- [ ] Modal field label and dropdown placeholder read "Prospect" / "— Select Prospect —"
- [ ] Clicking a linked Prospect name navigates to `/crm/prospect/<offering>/<org>/detail`
- [ ] Clicking a `—` Prospect cell opens the edit modal
- [ ] Clicking any non-Prospect cell opens the edit modal
- [ ] Edit modal header reads "Edit Meeting"
- [ ] All fields (Prospect, Offering, Date, Title, Attendees, Notes) are pre-populated from the meeting record
- [ ] Primary button reads "Save Changes" in edit mode
- [ ] Saving in edit mode PATCHes the meeting and reflects the update in the table
- [ ] "Delete Meeting" red text link is visible only in edit mode, bottom-left of footer
- [ ] Clicking "Delete Meeting" shows inline "Are you sure? Yes · No" — no browser dialog
- [ ] Confirming delete removes the meeting and its row from the table
- [ ] "No" on delete confirmation restores the "Delete Meeting" link
- [ ] Meeting Time field (`form-time` and its label) are fully absent from the modal HTML
- [ ] Existing meetings with `meeting_time` in `meetings.json` are unaffected
- [ ] The `alert()` placeholder is gone
- [ ] Add mode still works correctly (empty fields, "Add Meeting" header and button, no Delete link)
- [ ] All existing tests pass
- [ ] Feedback loop prompt has been run

---

## 9. Files Likely Touched

| File | Change |
|---|---|
| `app/templates/crm_meetings.html` | Rename column header; rename modal label + placeholder; remove `form-time` field; add edit mode header/button switching; add Delete link + inline confirmation; rewrite `openMeetingDetail()`; add `currentEditMeetingId` variable; branch form submit on edit vs. add mode; update `closeAddMeetingModal()` |
| `app/delivery/crm_blueprint.py` | Verify PATCH and DELETE routes for `/crm/api/meetings/<id>` exist; add if missing |
| `app/sources/crm_reader.py` | No changes expected — `update_meeting()` and `delete_meeting()` already exist |
| `app/tests/` | Add or update tests for meeting update and delete API routes if not already covered |
