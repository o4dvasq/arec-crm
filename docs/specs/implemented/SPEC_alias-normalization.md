# SPEC: Alias Normalization & Org Detail Display
**Project:** arec-crm | **Date:** 2026-03-19 | **Status:** Ready for implementation

---

## 1. Objective

The alias system is consolidated and functional for *reads* (lookup, search, brief synthesis, tony sync matching), but *write paths* don't normalize org names through aliases before storing data. This causes name drift — meetings, prospects, and notes get saved with variant names (e.g., "MassMutual" instead of "Mass Mutual Life Insurance Co."), creating broken links, orphaned records, and manual cleanup. Additionally, aliases are invisible on the Org Detail screen, so users can't see or manage them without editing the raw markdown.

This spec adds two things:
1. **Write-path normalization** — a single `resolve_org_name()` function called at every write point to canonicalize org names before storage.
2. **Aliases display on Org Detail** — show the Aliases field inline on the org detail screen with edit support.

---

## 2. Scope

**In scope:**
- New `resolve_org_name(name: str) -> str` function in `crm_reader.py`
- Call `resolve_org_name()` at all write-path endpoints: meeting create/update, prospect create, contact add, org notes add
- Display Aliases field on the Org Detail page with inline editing (same pattern as Type, Domain, Notes)
- Update `email_matching._fuzzy_match_org()` to check aliases in addition to org names

**Out of scope:**
- Changes to the alias storage format (stays comma-separated in organizations.md)
- Batch retroactive cleanup of existing data (manual or separate task)
- Alias collision detection UI (first-match-wins is acceptable for now)
- Changes to tony_sync.py (already uses `get_org_aliases_map()` correctly)
- Merge orgs feature (separate spec in `docs/specs/future/`)

---

## 3. Business Rules

1. **Canonical name always wins.** When a write-path receives an org name, `resolve_org_name()` checks: (a) exact match against org names, (b) alias lookup. If an alias matches, the canonical org name is stored instead.
2. **Case-insensitive matching.** "massmutual" resolves to "Mass Mutual Life Insurance Co." just like "MassMutual" does.
3. **Unknown names pass through.** If no org or alias matches, the original name is stored as-is. This preserves the ability to create meetings for orgs not yet in the CRM.
4. **Normalization is silent.** The API doesn't error or warn when it normalizes — it just stores the canonical name. The response includes the resolved name so the UI can reflect it.
5. **Aliases are editable on Org Detail.** Comma-separated text field, same inline-edit pattern as Type and Domain.

---

## 4. Data Model / Schema Changes

No schema changes. The `Aliases` field already exists in `organizations.md` and is parsed by `crm_reader.py`.

---

## 5. UI / Interface

### Org Detail Page — Aliases Field

Add an **Aliases** row to the org summary card, between Domain and Notes. Display as a comma-separated list of alias names, using the same inline-edit pattern as the existing fields.

**Layout within the existing summary card:**

```
Type:     [Pension Fund]
Domain:   [merseyside.org.uk]
Aliases:  [Merseyside]                    ← NEW — click to edit
Notes:    [UK pension fund, Tier 2...]
```

**Empty state:** Show muted dash ("—") with a "click to edit" hint, same as other fields.

**Edit mode:** Clicking transforms into a text input. User types comma-separated aliases. Save via the existing PATCH `/crm/api/org/<name>` endpoint which already accepts `aliases`.

---

## 6. Integration Points

### A. New function: `resolve_org_name()` in `crm_reader.py`

```python
def resolve_org_name(name: str) -> str:
    """Return the canonical org name if the input matches an org or alias.

    Returns the original name unchanged if no match is found (allows
    meetings/prospects for orgs not yet in the CRM).
    """
    if not name or not name.strip():
        return name
    name = name.strip()
    # 1. Exact match against org names (case-insensitive)
    orgs = load_organizations()
    for org in orgs:
        if org['name'].lower() == name.lower():
            return org['name']  # Return with canonical casing
    # 2. Alias lookup
    canonical = get_org_by_alias(name)
    if canonical:
        return canonical
    # 3. No match — pass through
    return name
```

### B. Write-path endpoints to update in `crm_blueprint.py`

Each of these endpoints should call `resolve_org_name()` on the org name before passing it to the data layer:

| Endpoint | Method | Current code | Change |
|----------|--------|-------------|--------|
| `/api/meetings` | POST | `org = data.get('org', '').strip()` | Add `org = resolve_org_name(org)` |
| `/api/meetings/<id>` | PUT | `org = data.get('org', '').strip()` | Add `org = resolve_org_name(org)` |
| `/api/prospect` | POST | `org = data.get('org', '').strip()` | Add `org = resolve_org_name(org)` |
| `/api/org/<name>/contacts` | POST | Uses `org_name` from URL | Add `org_name = resolve_org_name(org_name)` |
| `/api/org/<name>/notes` | POST | Uses `name` from URL | Add `name = resolve_org_name(name)` |

### C. Email matching enhancement

Update `email_matching._fuzzy_match_org()` to also check aliases when doing substring matching. This lets the fuzzy matcher find orgs by their aliases, not just their canonical names.

```python
def _fuzzy_match_org(display_name: str, org_names: list[str]) -> str | None:
    # Existing logic: check org_names for substring match
    # NEW: also build a combined list that includes aliases
    from sources.crm_reader import get_org_aliases_map
    alias_map = get_org_aliases_map()
    # Check aliases as well — if alias matches, return the canonical name
    ...
```

The exact implementation should maintain the existing 6-char minimum threshold and single-match-only rule (return None if ambiguous).

### D. Org Detail template (`crm_org_edit.html`)

Add the Aliases field to the summary card. The org data is already available via `org_data` template variable, and `org_data.Aliases` contains the raw comma-separated string.

The inline edit should PATCH to `/crm/api/org/<name>` with `{"aliases": "..."}` — this endpoint already handles the field (lines 1264-1265 of crm_blueprint.py).

---

## 7. Constraints

- `resolve_org_name()` must be fast — it's called on every write. `load_organizations()` should be cached or lightweight (it already reads from a single file, so this is fine for single-user local deployment).
- The function must be idempotent: `resolve_org_name(resolve_org_name(x)) == resolve_org_name(x)`.
- Do not normalize org names in URL routes that *read* data — `get_organization()` already handles alias fallback for reads. Normalization is only for *writes*.
- Existing data is not retroactively cleaned by this spec (we already did a manual cleanup of meetings.json today). This spec prevents future drift.
- `email_matching` changes should not break existing tests — the 6-char threshold and single-match-only rules must be preserved.
- **Canonical name question:** Some org canonical names in organizations.md include parenthetical descriptors (e.g., "Khazanah (Malaysia Sovereign Wealth Fund)"), while prospects.md and meetings.json currently use the shorter alias form ("Khazanah"). `resolve_org_name()` would normalize new writes to the full canonical name, which may look inconsistent alongside older records using the short form. Two approaches: (a) accept the inconsistency and let alias-based reads handle it, or (b) do a one-time data cleanup to align prospects.md and meetings.json to canonical names after this spec ships. Recommend (a) for now — the alias system handles reads correctly regardless of which form is stored.

---

## 8. Acceptance Criteria

1. `resolve_org_name("MassMutual")` returns `"Mass Mutual Life Insurance Co."`
2. `resolve_org_name("StepStone Group")` returns `"StepStone"` (if "StepStone Group" is an alias on the StepStone org)
3. `resolve_org_name("Unknown Corp")` returns `"Unknown Corp"` (passthrough)
4. Creating a meeting with org "MassMutual" stores "Mass Mutual Life Insurance Co." in meetings.json
5. Creating a prospect with org "PSERS" stores "Pennsylvania Public School Employees' Retirement System"
6. Aliases field is visible and editable on the Org Detail page
7. Email matching can find orgs by alias (e.g., display name containing "MassMutual" resolves to "Mass Mutual Life Insurance Co.")
8. `python3 -m pytest app/tests/ -v` passes with new tests for `resolve_org_name()`
9. Feedback loop prompt has been run

---

## 9. Files Likely Touched

| File | Change |
|------|--------|
| `app/sources/crm_reader.py` | Add `resolve_org_name()` function |
| `app/delivery/crm_blueprint.py` | Call `resolve_org_name()` at 5 write-path endpoints |
| `app/sources/email_matching.py` | Enhance `_fuzzy_match_org()` to include aliases in candidate list |
| `app/templates/crm_org_edit.html` | Add Aliases row to summary card with inline edit |
| `app/tests/test_resolve_org_name.py` | New test file for `resolve_org_name()` |
| `app/tests/test_email_matching.py` | Add tests for alias-based fuzzy matching |
