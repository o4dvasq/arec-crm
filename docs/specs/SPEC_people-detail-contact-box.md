# SPEC: People Detail — Contact Info Box

**Project:** arec-crm  
**Date:** March 10, 2026  
**Status:** ✅ COMPLETE — Implemented March 10, 2026

---

## 1. Objective

Add an editable contact information box at the top of the People Detail page displaying Company, Title, Email, and Phone for the selected person. These fields are read from and written back to the person's `memory/people/{name}.md` file. This gives the fundraising team immediate access to core contact details without scrolling or opening a separate file.

---

## 2. Scope

**In scope:**
- New contact info box UI component on People Detail page
- Read Company, Title, Email, Phone from the person's `memory/people/*.md` file
- Inline editing of all four fields
- Save edits back to the person's `memory/people/*.md` file
- Empty fields hidden (consistent with project-wide pattern)

**Out of scope:**
- Changes to the Person Brief or other existing sections on the page
- Adding new fields beyond Company, Title, Email, Phone
- Changes to `contacts_index.md` or any other data store
- Bulk editing across multiple people

---

## 3. Business Rules

1. **Data source:** Each person's data lives in `memory/people/{firstname-lastname}.md`. These are freeform markdown intel files. The four contact fields should be parsed from a structured block at the top of the file (see Data Model below).
2. **Empty fields are hidden.** If a field has no value, do not render its row. If all four fields are empty, do not render the contact box at all. This matches the project-wide "empty fields never rendered" pattern.
3. **Email is a mailto link.** When displayed (non-edit mode), the email value should be a clickable `mailto:` link.
4. **Phone is a tel link.** When displayed (non-edit mode), the phone value should be a clickable `tel:` link.
5. **Company should match org names where possible** but is free-text (not a dropdown). Some contacts work at firms not in `organizations.md`.
6. **No validation beyond non-empty.** These are free-text fields. No format enforcement on phone or email — the user knows what they're entering.

---

## 4. Data Model / Schema Changes

### Existing format in `memory/people/*.md`

These files are freeform markdown intel files. Contact fields may or may not already be present. The parser should look for a structured contact block using the following format at the **top** of the file (before any prose content):

```markdown
- **Company:** Merseyside Pension Fund
- **Title:** Director of Private Markets
- **Email:** john.smith@merseyside.gov.uk
- **Phone:** +44 151 555 0123
```

### Parser rules

- Look for lines matching the pattern `- **FieldName:** Value` at the top of the file (before the first `##` heading or first paragraph of prose).
- Recognized field names (case-insensitive match): `Company`, `Title`, `Email`, `Phone`
- If a field line exists but has no value after the colon, treat as empty.
- If the structured block doesn't exist at all, treat all four fields as empty.

### Write rules

- On save, write/update the structured contact block at the very top of the file.
- Preserve all existing content below the contact block unchanged.
- If a field is cleared (set to empty), remove that line from the block entirely (don't write `- **Email:**` with no value).
- If all four fields are cleared, remove the contact block entirely.
- If the file previously had no contact block, insert one at the top followed by a blank line before existing content.

---

## 5. UI / Interface

### Placement

The contact info box appears at the **top** of the People Detail page, directly below the person's name heading and above the existing Person Brief section.

### Display mode (default)

```
┌──────────────────────────────────────────────┐
│  Company    Merseyside Pension Fund          │
│  Title      Director of Private Markets      │
│  Email      john.smith@merseyside.gov.uk     │  ← mailto: link
│  Phone      +44 151 555 0123                 │  ← tel: link
│                                    [Edit]    │
└──────────────────────────────────────────────┘
```

- Style: same inline field style used on Prospect Detail (label left, value right — NOT a bordered sub-section). Match the existing person card aesthetic.
- Field labels are muted/gray. Values are normal text weight.
- `[Edit]` link/button in the bottom-right corner of the box, subtle styling (text link, not a primary button).
- Only non-empty fields are rendered.

### Edit mode (after clicking Edit)

```
┌──────────────────────────────────────────────┐
│  Company    [Merseyside Pension Fund      ]  │
│  Title      [Director of Private Markets  ]  │
│  Email      [john.smith@merseyside.gov.uk ]  │
│  Phone      [+44 151 555 0123            ]  │
│                          [Cancel]  [Save]    │
└──────────────────────────────────────────────┘
```

- Each value becomes a text `<input>` field.
- All four fields are shown in edit mode (even if currently empty) so the user can populate them.
- `[Save]` is the primary action button. `[Cancel]` reverts to display mode with no changes.
- On save success: return to display mode, show brief success indicator (green checkmark or flash).
- On save error: stay in edit mode, show error message inline.

### States

| State | Behavior |
|-------|----------|
| **Loading** | Contact box area shows nothing (loads with the rest of the page) |
| **All fields empty** | Contact box is not rendered at all |
| **Some fields empty** | Only populated fields shown in display mode; all four shown in edit mode |
| **Save in progress** | Save button shows spinner or "Saving..." — disable double-click |
| **Save success** | Return to display mode, brief green flash |
| **Save error** | Stay in edit mode, inline error message below Save button |

---

## 6. Integration Points

### Reads from
- `memory/people/{firstname-lastname}.md` — parse contact block at top of file

### Writes to
- `memory/people/{firstname-lastname}.md` — update/insert contact block at top of file, preserve all other content

### Route needed
- **`POST /crm/person/<name>/contact`** — accepts JSON `{company, title, email, phone}`, reads the person's md file, updates the contact block, writes back. Returns success/error JSON.

### Existing infrastructure used
- The People Detail page already loads the person's data. The contact fields should be parsed during the existing page load (add parsing logic to whatever function currently reads the person's md file).
- File I/O pattern: same as existing `memory/people/*.md` read/write (use `BASE_DIR` constant for paths, never hardcode).

---

## 7. Constraints

1. **Surgical change only.** Do not restructure the People Detail page. Add the contact box above existing content.
2. **No new libraries.** Use existing vanilla JS patterns from `crm.js`.
3. **Inline field style.** Match the Prospect Detail inline field aesthetic (label + value on same row, no bordered box). Do NOT use a card or bordered sub-section.
4. **`BASE_DIR` for all file paths.** Never hardcode paths to `memory/people/`.
5. **Preserve file content.** The write operation must not alter any content in the md file below the contact block. These files contain accumulated intelligence — data loss is unacceptable.
6. **Exclude `--exclude-dir=venv` and `--exclude-dir=__pycache__`** from any grep searches.

---

## 8. Acceptance Criteria

1. People Detail page shows Company, Title, Email, Phone at the top when populated in the person's `memory/people/*.md` file.
2. Empty fields are not displayed. If all four are empty, the contact box is not rendered.
3. Clicking Edit shows all four fields as editable inputs (including empty ones).
4. Save writes changes back to the person's `memory/people/*.md` file.
5. Existing content in the md file below the contact block is unchanged after save.
6. Email renders as a clickable `mailto:` link in display mode.
7. Phone renders as a clickable `tel:` link in display mode.
8. A person file with no prior contact block gains one after save, with a blank line separating it from existing content.
9. Clearing all four fields and saving removes the contact block from the file.
10. Feedback loop prompt has been run.

---

## 9. Files Likely Touched

| File | Reason |
|------|--------|
| `app/sources/memory_reader.py` or equivalent | Add parsing for contact block at top of people md files |
| `app/delivery/crm_blueprint.py` | Add `POST /crm/person/<name>/contact` route; pass contact data to template |
| `templates/crm/person_detail.html` (or equivalent) | Add contact info box HTML above existing brief section |
| `static/crm/crm.css` | Styling for contact info box (inline field style) |
| `static/crm/crm.js` | Edit/Save/Cancel toggle logic, AJAX call to save endpoint |
