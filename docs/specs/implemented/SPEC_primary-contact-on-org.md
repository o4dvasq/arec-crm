# SPEC: Primary Contact on Organization
**Project:** arec-crm | **Date:** 2026-03-18 | **Status:** Ready for implementation

---

## 1. Objective

Move "primary contact" from the prospect level to the organization level. Currently, each prospect record carries a `"Primary Contact"` string field. In practice the team thinks of primary contacts as belonging to the org — one per org, visible across all that org's prospects. This mismatch causes "TBD" displays on the prospect detail page even when the org has known contacts.

**Example:** Future Fund shows "TBD" as primary contact despite Julia McArdle being a known contact on the org.

---

## 2. Scope

**In scope:**
- Add `Primary: true` frontmatter field to contact markdown files (`memory/people/{slug}.md`) to designate one contact per org as primary
- Remove the `"Primary Contact"` field from prospect records entirely (from `PROSPECT_FIELD_ORDER`, `EDITABLE_FIELDS`, and `update_prospect_field()` auto-linking logic)
- Migration script to promote existing prospect-level Primary Contact strings to `Primary: true` on the matched contact file
- Star toggle on org detail contact cards to set/clear primary
- Prospect detail page resolves primary contact through the org's contacts, not the prospect record
- Pipeline table resolves primary contact through the org
- Auto-primary: when first contact is added to an org, mark them primary
- New API route for the star toggle

**Out of scope:**
- Per-prospect contact override
- Changes to `crm_person_detail.html` (People directory page)
- Brief synthesis changes — **audit confirmed `brief_synthesizer.py` does not use primary contact at all**
- Email auto-capture changes — **audit confirmed `graph_poller.py` does not write to primary_contact**

---

## 3. Business Rules

1. Each organization has at most one primary contact — the contact in its list with `Primary: true` in their file.
2. An org with no contacts, or none designated, displays "TBD" wherever primary contact is shown.
3. Setting a contact as primary automatically clears `Primary: true` from any other contact for the same org (radio behavior — enforced in application code, not file constraints).
4. When the **first** contact is added to an org that currently has zero contacts, that contact is automatically set as primary.
5. When a primary contact is removed from an org's contact list, no automatic reassignment — the org reverts to "TBD" until manually set.
6. All prospects for a given org display the same primary contact. No per-prospect override.
7. Clicking ★ on an already-primary contact **clears** the primary designation (org → no primary).

---

## 4. Data Model / Schema Changes

### 4a. Contact file — add `Primary` field

Contact records live at `memory/people/{slug}.md`. Add an optional `Primary` frontmatter field:

```markdown
- **Name:** Julia McArdle
- **Organization:** Future Fund
- **Role:** Managing Director
- **Email:** julia@futurefund.com
- **Primary:** true          ← NEW (only present/true on one contact per org)
```

`Primary: true` is only written when a contact is designated primary. Absent or `Primary: false` means not primary. The `load_person()` function must parse this field and include it in the returned dict as `is_primary: bool`.

### 4b. Prospect record — remove Primary Contact field

In `crm_reader.py`:
- Remove `'Primary Contact'` from `PROSPECT_FIELD_ORDER` (line ~26)
- Remove `'primary_contact'` from `EDITABLE_FIELDS` (line ~39)
- Remove the auto-linking block in `update_prospect_field()` that calls `ensure_contact_linked()` when `primary contact` is the field being updated (lines ~927–928)

In `crm/prospects.md`:
- Remove the `Primary Contact` field from all existing prospect blocks (the migration script handles this as part of promoting data — see Section 5)

### 4c. New crm_reader.py functions

```python
def get_primary_contact(org: str) -> dict | None:
    """Return the contact dict with Primary: true for this org, or None."""

def set_primary_contact(org: str, contact_name: str) -> bool:
    """
    Mark contact_name as primary for org.
    Clears Primary: true from any other contact in the same org first.
    Returns True on success, False if contact not found.
    """

def clear_primary_contact(org: str) -> None:
    """Remove Primary: true from all contacts for this org."""
```

These functions work by:
1. Calling `get_contacts_for_org(org)` to get the contact list
2. Reading/writing each contact's `memory/people/{slug}.md` file to set or clear the `Primary:` frontmatter field

### 4d. Update `get_contacts_for_org()` and `get_prospect_full()`

- `get_contacts_for_org(org)` — ensure the returned contact dicts include `is_primary: bool` (read from the contact file's `Primary` field)
- `get_prospect_full(org, offering)` — replace the prospect's `"Primary Contact"` string field with a resolved contact dict from `get_primary_contact(org)`. The returned dict should still include a `"Primary Contact"` key (string, contact name) for backward compatibility with templates that read it, until templates are updated.

---

## 5. Migration Script

**Location:** `scripts/migrate_primary_contact_to_org.py`

**Must be idempotent** — safe to run multiple times.

Steps:
1. Scan all prospect records in `crm/prospects.md` for the `Primary Contact` field.
2. For each org, collect all `(offering, primary_contact_name)` pairs.
3. For each org:
   a. If all offerings agree on the same primary contact name → call `set_primary_contact(org, name)`. Log: `"[ORG] → set primary: [NAME]"`.
   b. If offerings disagree (conflict) → pick the contact name from the offering at the most advanced pipeline stage (Stage 5 > 4 > 3 > 2 > 1). Log the conflict: `"[ORG] CONFLICT: [NAME-A] (Stage N) vs [NAME-B] (Stage M) → chose [NAME-A]"`. Call `set_primary_contact()` with the winner.
   c. If the named contact is not found in `memory/people/` → log as warning, skip.
4. After all orgs processed, remove the `Primary Contact:` line from every prospect block in `crm/prospects.md`.
5. Print summary: orgs updated, conflicts resolved, orgs with no primary contact set, contacts not found.

**Pipeline stage lookup:** Use `crm_reader.py`'s existing `get_prospect_full()` or `load_prospects()` to retrieve stage values.

---

## 6. UI / Interface

### 6.1 Org Detail Page — Star Toggle

**Template:** `app/templates/crm_org_detail.html`

In the contacts list, add a star icon to each contact card:

- **★ (filled, gold)** = this contact is the org's primary
- **☆ (outline, muted)** = not primary
- **Click ☆** → call API to set this contact as primary; update all stars on the page (only one ★ at a time)
- **Click ★** → call API to clear primary; all contacts show ☆

Use Lucide icons (`lucide-star`) consistent with the existing icon system in the template. Icon should be small, vertically centered in the contact card header row. Provide immediate visual feedback (swap icon class on success); no toast required unless the existing UI already uses one.

### 6.2 Prospect Detail Page

**Template:** `app/templates/crm_prospect_detail.html`

Lines ~778–785 currently read:
```html
{%- set _pc = prospect.get('Primary Contact', '').split(';')[0].strip() -%}
```

Change the resolution path: read from the org's contacts (resolved server-side and passed in template context as `primary_contact_name`), not from `prospect['Primary Contact']`. If `primary_contact_name` is a non-empty string, render it as a `<span data-person-name>` link. If empty/None → render `—`.

Remove any edit control for primary contact from this template.

### 6.3 Pipeline Table

**Template:** `app/templates/crm_pipeline.html`

Lines ~1776–1778 currently read:
```javascript
const primaryContact = p['Primary Contact'];
```

The backend (via the prospect list API) should resolve primary contact through the org and include it in the prospect data returned to the pipeline. No template logic change required if the backend continues populating `p['Primary Contact']` (string) — just change the data source on the backend side in `get_prospect_full()`.

### 6.4 Prospect Edit Form

**Template:** `app/templates/crm_prospect_edit.html`

Remove the Primary Contact dropdown/field from the edit form entirely. Primary contact is set exclusively on the org detail page.

---

## 7. Integration Points

### API — New route

```
POST /crm/api/org/<org_name>/primary-contact
Content-Type: application/json

Body to SET:   {"contact_name": "Julia McArdle"}
Body to CLEAR: {"contact_name": null}

Response 200:  {"status": "ok", "primary_contact": "Julia McArdle"}
Response 200:  {"status": "ok", "primary_contact": null}
Response 404:  {"error": "contact not found"}
```

`org_name` is URL-encoded. Route calls `set_primary_contact()` or `clear_primary_contact()` accordingly. Requires `@login_required`.

### Auto-primary on first contact added

**Route:** `POST /api/org/<org_name>/contacts` (`api_org_add_contact`, line ~1410)

After successfully adding the new contact, check how many contacts the org now has via `get_contacts_for_org(org)`. If count == 1, call `set_primary_contact(org, new_contact_name)`.

### Existing `update_prospect_field()` trigger — remove

Remove the auto-linking block that fires `ensure_contact_linked()` when the field being updated is `primary contact`. The `ensure_contact_linked()` function itself can remain — it's used by email auto-capture. Only remove the `primary contact` trigger inside `update_prospect_field()`.

### `resolve_primary_contact(org, contact_name)` — keep as-is

This existing function resolves a contact name to a dict within an org. It can be used internally by `set_primary_contact()`. No change needed.

---

## 8. Constraints

- No SQL, no SQLAlchemy, no database. All reads/writes via `crm_reader.py` and markdown files.
- Migration script must be idempotent.
- Migration runs in order: (1) write `Primary: true` to contact files, (2) remove `Primary Contact` lines from `crm/prospects.md`. Never reverse this order.
- No new libraries.
- Do not refactor code unrelated to this feature.
- All existing tests that reference prospect-level `Primary Contact` must be updated to reflect the new resolution path.
- The `memory/people/` directory is inside the arec-crm repo — confirm the exact path before writing. If contacts are in a different location (e.g., `crm/people/`), adjust all file paths accordingly.

---

## 9. Acceptance Criteria

- [ ] `load_person()` returns `is_primary: bool` parsed from the `Primary:` frontmatter field
- [ ] `get_primary_contact(org)` returns the correct contact dict or None
- [ ] `set_primary_contact(org, name)` writes `Primary: true` to the target contact file and clears it from all others in the same org
- [ ] `clear_primary_contact(org)` removes `Primary: true` from all contacts for the org
- [ ] Migration script runs without error on the live dataset; output summary is printed; conflicts are logged
- [ ] After migration, `crm/prospects.md` contains no `Primary Contact:` lines
- [ ] After migration, at least one contact file has `Primary: true` (confirming data was promoted)
- [ ] Org detail page contact cards show ★ for the primary contact and ☆ for others
- [ ] Clicking ☆ sets that contact as primary and updates all stars on the page
- [ ] Clicking ★ clears primary; all contacts show ☆
- [ ] When first contact is added to an org with no contacts, that contact is auto-set as primary
- [ ] Prospect detail page resolves primary contact through org, not prospect record
- [ ] Future Fund prospect detail shows Julia McArdle (assuming she is the sole/marked-primary contact for that org)
- [ ] Pipeline table primary contact column resolves through the org
- [ ] Primary Contact field is absent from the prospect edit form
- [ ] `'Primary Contact'` is removed from `PROSPECT_FIELD_ORDER` and `EDITABLE_FIELDS` in `crm_reader.py`
- [ ] All existing tests pass or are updated; no regressions
- [ ] Feedback loop prompt has been run

---

## 10. Files Likely Touched

| File | Change |
|---|---|
| `app/sources/crm_reader.py` | Add `get_primary_contact()`, `set_primary_contact()`, `clear_primary_contact()`; update `load_person()` to parse `Primary` field; update `get_contacts_for_org()` to include `is_primary`; update `get_prospect_full()` to resolve primary contact from org; remove `Primary Contact` from `PROSPECT_FIELD_ORDER`, `EDITABLE_FIELDS`, and `update_prospect_field()` auto-link trigger |
| `app/delivery/crm_blueprint.py` | Add `POST /api/org/<org_name>/primary-contact` route; update `api_org_add_contact` to auto-set primary on first contact |
| `app/templates/crm_org_detail.html` | Add star icon to contact cards; add JS click handler for toggle; call new API route |
| `app/templates/crm_prospect_detail.html` | Update primary contact resolution to use `primary_contact_name` from context instead of `prospect['Primary Contact']` |
| `app/templates/crm_prospect_edit.html` | Remove Primary Contact field from edit form |
| `app/templates/crm_pipeline.html` | No template change expected if backend populates `p['Primary Contact']` — verify |
| `memory/people/*.md` | Migration writes `Primary: true` to one contact file per org |
| `crm/prospects.md` | Migration removes `Primary Contact:` lines from all prospect blocks |
| `scripts/migrate_primary_contact_to_org.py` | New migration script |
| `app/tests/` | Update any tests that set or assert prospect-level Primary Contact; add tests for new reader functions and API route |
