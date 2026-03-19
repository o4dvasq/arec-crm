SPEC: Add Primary Contact to Prospect Field Order | Project: arec-crm | Date: 2026-03-19 | Status: Ready for implementation

---

## 1. Objective

Add `Primary Contact` to `PROSPECT_FIELD_ORDER` in `crm_reader.py` so the field persists when prospects are written to disk. Currently, `update_prospect_field('Primary Contact', ...)` appears to succeed but the value is silently dropped by `write_prospect` because the field is not in the serialization list.

## 2. Scope

- **In scope:** Add `Primary Contact` to `PROSPECT_FIELD_ORDER`. Verify it round-trips correctly (read → update → write → read).
- **Out of scope:** UI changes, new API routes, batch script changes. The batch enrichment script (`scripts/batch_primary_contact.py`) will be re-run separately after this fix lands.

## 3. Business Rules

1. `Primary Contact` is a prospect-level field, not an org-level field. Different prospects for the same org can have different primary contacts (e.g., UTIMCO has two prospects with different primary contacts).
2. The field value is a contact name (string) referencing a contact that lives on the org. The prospect does not own contacts — it only identifies which of the org's contacts is primary for this prospect.
3. The field should appear after `Assigned To` and before `Notes` in the serialization order.

## 4. Data Model / Schema Changes

In `app/sources/crm_reader.py`:

```python
# Current:
PROSPECT_FIELD_ORDER = [
    "Stage", "Target",
    "Closing", "Urgent", "Assigned To", "Notes", "Last Touch"
]

# New:
PROSPECT_FIELD_ORDER = [
    "Stage", "Target",
    "Closing", "Urgent", "Assigned To", "Primary Contact", "Notes", "Last Touch"
]
```

No other schema changes. The field already works in `update_prospect_field` — it just needs to survive serialization.

## 5. UI / Interface

No UI changes required for this spec. The Prospect Detail page already renders all fields from the prospect dict. Once the field persists, it will display automatically.

If Primary Contact is not yet rendered on Prospect Detail, that is a separate spec.

## 6. Integration Points

- `write_prospect()` — will now serialize `Primary Contact` in the field order
- `update_prospect_field()` — already works, no changes needed
- `load_prospects()` / `get_prospect()` — already parses any `- **Key:** Value` field, no changes needed
- Batch script (`scripts/batch_primary_contact.py`) — will be re-run after this fix; no code changes needed there

## 7. Constraints

- This is a one-line change. Do not refactor surrounding code.
- Existing prospect files that don't have a `Primary Contact` field will simply serialize with an empty value (`- **Primary Contact:**`), which is the same pattern as other optional fields like `Closing`.

## 8. Acceptance Criteria

- [ ] `Primary Contact` appears in `PROSPECT_FIELD_ORDER` after `Assigned To` and before `Notes`
- [ ] Round-trip test: `update_prospect_field(org, offering, 'Primary Contact', 'Test Name')` → `get_prospect(org, offering)` returns `Primary Contact: 'Test Name'`
- [ ] Existing tests pass (`python3 -m pytest app/tests/ -v`)
- [ ] Feedback loop prompt has been run

## 9. Files Likely Touched

| File | Action |
|------|--------|
| `app/sources/crm_reader.py` | **Edit** — add `"Primary Contact"` to `PROSPECT_FIELD_ORDER` list (line 26) |
