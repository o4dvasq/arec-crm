SPEC: Primary Contact Auto-Fill + People Detail Field Display
Project: arec-crm
Date: 2026-03-16
Status: Ready for implementation

---

## 1. Objective

Fix two related gaps in contact display and data quality:

(A) **Primary Contact auto-fill:** If a prospect has no Primary Contact set but the org has at least one contact, auto-assign the most likely primary contact. Run a one-time batch cleanup across all prospects, and enforce the rule going forward so new prospects never show "No Primary Contact" when contacts exist.

(B) **People detail page field display:** Always show Name, Title, Email, and Phone on the person detail page — even when empty. Empty fields display "--" and are editable inline (click to edit, save on blur/enter). This replaces the current behavior where empty fields are hidden entirely.

## 2. Scope

### In scope

- Batch script to auto-fill Primary Contact across all prospects with contacts but no primary
- Heuristic logic to pick the best primary contact when an org has multiple contacts
- `renderPersonCard()` in `crm_person_detail.html`: always render Title, Email, Phone rows (show "--" if empty)
- Inline editing for Title, Email, Phone fields (click field value → input appears → save on blur/enter → PATCH to `/people/api/<slug>/contact`)
- Auto-set Primary Contact when first contact is added to an org (going-forward rule)

### Out of scope

- Changing the Primary Contact dropdown on prospect edit (it already works correctly)
- Bulk contact creation (separate feature)
- Organization-level inline editing (different page)

## 3. Business Rules

### Primary Contact auto-fill heuristics

When a prospect has no Primary Contact but the org has contacts, select using this priority:

1. **Single contact:** If the org has exactly one contact → that person is primary. No ambiguity.
2. **Multiple contacts — relationship brief signal:** If the org has a relationship brief, look for the contact mentioned most frequently or listed first in the brief's narrative. That person is likely the primary relationship.
3. **Multiple contacts — interaction history signal:** The contact with the most recent interaction logged in `crm/interactions.md` for that org is likely the primary.
4. **Multiple contacts — no signal:** If no brief and no interactions distinguish them, pick the first contact listed in `contacts_index.md` for that org. Flag for manual review.

### Going-forward auto-set rule

When a new contact is added to an org (via `add_contact_to_index()`), if the org's prospect(s) have no Primary Contact set, auto-set the new contact as Primary Contact on all of that org's prospects. This covers the common case where someone creates the org first, then adds the contact.

### People detail field display rules

- **Always show:** Title, Email, Phone (and Company, which already shows)
- **Empty value display:** "--" in muted text
- **Editable inline:** Click the "--" or the existing value → transforms to an input field → user types → saves on blur or Enter key → PATCHes to `/people/api/<slug>/contact`
- **Escape to cancel:** pressing Escape reverts to the previous value without saving
- **Validation:** Email field: basic format check (contains @). Phone field: no validation (international formats vary). Title field: no validation.

## 4. Data Model / Schema Changes

No schema changes. All fields already exist:

- Prospect records in `crm/prospects/`: `Primary Contact` field (already in `PROSPECT_FIELDS` at line 23 of `crm_reader.py`)
- Person files in `contacts/`: `Title`, `Email`, `Phone` fields (already handled by the PATCH endpoint at `/people/api/<slug>/contact`)
- `contacts_index.md`: org → slug mappings (already exists)

The batch script reads/writes through existing `crm_reader.py` functions:
- `load_all_prospects()` — get all prospects
- `get_contacts_for_org(org)` — get contacts for an org
- `update_prospect_field(org, offering, 'Primary Contact', name)` — set primary contact
- `load_interactions(org)` — check interaction history for contact frequency

## 5. UI / Interface

### People detail page (crm_person_detail.html)

**Current behavior:** `renderPersonCard()` only renders fields with values. If `profile.email` is falsy, the Email row is not rendered at all.

**New behavior:** Always render all four contact fields. Replace the conditional rendering with:

```javascript
// Always show these fields, even if empty
const fields = [
    { label: 'Title', key: 'title', value: profile.title },
    { label: 'Email', key: 'email', value: profile.email },
    { label: 'Phone', key: 'phone', value: profile.phone },
];

fields.forEach(f => {
    const displayValue = f.value || '--';
    const classes = f.value ? 'contact-value' : 'contact-value muted';
    contactRows.push(
        `<span class="contact-label">${f.label}</span>` +
        `<span class="${classes}" data-field="${f.key}"
              onclick="startInlineEdit(this, '${f.key}')"
              style="cursor:pointer">${displayValue}</span>`
    );
});
```

Company row stays as-is (it links to the org page and has different edit semantics — org reassignment, not simple text edit).

### Inline edit behavior

Clicking a field value replaces the `<span>` with an `<input>`:

```javascript
function startInlineEdit(el, fieldKey) {
    const currentValue = el.textContent === '--' ? '' : el.textContent;
    const input = document.createElement('input');
    input.type = fieldKey === 'email' ? 'email' : 'text';
    input.value = currentValue;
    input.className = 'inline-edit-input';
    input.addEventListener('blur', () => saveInlineEdit(el, input, fieldKey));
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') input.blur();
        if (e.key === 'Escape') { cancelInlineEdit(el, currentValue, fieldKey); }
    });
    el.replaceWith(input);
    input.focus();
    input.select();
}
```

On save, PATCH to `/people/api/${PERSON_SLUG}/contact` with `{ [fieldKey]: newValue }`. On success, re-render the field. On error, show a brief inline error.

### Prospect edit page — no UI changes

The Primary Contact `<select>` dropdown already works. The batch script just pre-fills the value in the markdown. The dropdown will show the auto-selected contact as selected on next page load.

## 6. Integration Points

- **Reads from:** `crm/prospects/`, `crm/contacts_index.md`, `contacts/*.md`, `crm/interactions.md`, relationship briefs (if they exist per org)
- **Writes to:** `crm/prospects/` (Primary Contact field updates via `update_prospect_field()`)
- **API endpoint used:** `PATCH /people/api/<slug>/contact` (already exists, no changes needed)
- **Functions used:** `load_all_prospects()`, `get_contacts_for_org()`, `update_prospect_field()`, `load_interactions()`, `get_prospect()`

## 7. Constraints

- The batch script must be idempotent — running it twice should not change anything the second time
- Do not overwrite an existing Primary Contact value (only fill blanks)
- The inline edit must degrade gracefully — if the PATCH fails, revert the UI and show the previous value
- The "--" placeholder must be visually distinct (muted color) so it's clear the field is empty, not literally "--"
- The auto-set going-forward rule should only fire when Primary Contact is empty, never overwrite an existing selection

## 8. Acceptance Criteria

- [ ] Batch script runs and fills Primary Contact for all prospects where: (a) Primary Contact is blank AND (b) org has at least one contact
- [ ] Single-contact orgs auto-fill with no ambiguity
- [ ] Multi-contact orgs use heuristic (brief → interactions → first in index) and log which heuristic was used
- [ ] Batch script reports: "Updated N prospects. K single-contact (auto), M heuristic (brief/interaction), J flagged for review"
- [ ] People detail page shows Title, Email, Phone at all times (with "--" for empty)
- [ ] Clicking a field value opens inline edit input
- [ ] Blur or Enter saves the edit via PATCH
- [ ] Escape cancels the edit
- [ ] New contacts added to an org auto-set as Primary Contact on that org's prospects (if Primary Contact is currently blank)
- [ ] Existing Primary Contact values are never overwritten by auto-fill
- [ ] Feedback loop prompt has been run

## 9. Files Likely Touched

| File | Change |
|------|--------|
| `app/templates/crm_person_detail.html` | **Modified** — `renderPersonCard()`: always show Title/Email/Phone, add inline edit JS functions, add `.inline-edit-input` CSS |
| `app/delivery/crm_blueprint.py` | **No change** — PATCH endpoint already handles all four fields |
| `app/sources/crm_reader.py` | **Minor** — add auto-set logic in `add_contact_to_index()` to check/fill Primary Contact on that org's prospects |
| `scripts/batch_primary_contact.py` | **New** — one-time batch script to fill Primary Contact across all prospects |
| `crm/prospects/*.md` | **Modified by batch** — Primary Contact field updated |
