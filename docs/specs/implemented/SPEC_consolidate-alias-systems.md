# SPEC: Consolidate Alias Systems
**Project:** arec-crm | **Date:** 2026-03-19 | **Status:** Ready for implementation

---

## 1. Objective

The CRM has two independent alias systems that don't talk to each other:

1. **`Aliases` field on organizations.md** — comma-separated text stored on each org entry, read by `crm_reader.py`, used by search, briefs, merge, and the UI.
2. **`crm/org_aliases.json`** — standalone JSON file `{alias: canonical_name}`, read only by `tony_sync.py` via its own `load_aliases()` function.

This means aliases added via the CRM UI (or org merge) don't help Tony sync matching, and aliases added to `org_aliases.json` don't appear in search or briefs. The fix is to consolidate onto the `Aliases` field as the single source of truth, migrate the JSON entries into org records, and retire the JSON file.

---

## 2. Scope

**In scope:**
- Migrate all entries from `org_aliases.json` into the `Aliases` field on the corresponding org in `organizations.md`
- Update `tony_sync.py` to call `crm_reader.get_org_aliases_map()` instead of its own `load_aliases()` function
- Remove `tony_sync.load_aliases()` and the `ALIASES_PATH` constant
- Delete `crm/org_aliases.json` after migration is verified
- Update tony_sync diff report text that references `org_aliases.json` to say "add alias to the org in the CRM UI" instead

**Out of scope:**
- Adding new aliases to orgs (will be done as a separate data task after this spec ships)
- Changes to how the `Aliases` field is parsed or stored (comma-separated text — no format change)
- Changes to the org edit UI, search, or brief synthesis (they already use the `Aliases` field correctly)
- Creating missing org entries (separate data task)

---

## 3. Business Rules

1. The `Aliases` field on organizations.md is the **single source of truth** for all org aliases.
2. Tony sync uses `crm_reader.get_org_aliases_map()` for alias lookups, same as every other CRM feature.
3. `org_aliases.json` no longer exists after migration. Any process that referenced it must use the Aliases field instead.
4. The combined alias map (from `get_org_aliases_map()`) merges org-name-based aliases from the `Aliases` field with the org's canonical name. No duplicates — first-match wins (existing behavior in `get_org_aliases_map()`).

---

## 4. Data Model / Schema Changes

No schema changes. The `Aliases` field already exists and is already parsed by `crm_reader.py`. The only data change is migrating content from `org_aliases.json` into existing `Aliases` fields.

### Migration map (org_aliases.json → organizations.md Aliases field)

| JSON Alias | JSON Target | Org in organizations.md | Action |
|---|---|---|---|
| `UTIMCO` | University of Texas Investment Management Company | UTIMCO - Hedge Fund / UTIMCO - Real Estate | Add "UTIMCO" as alias to both UTIMCO org entries (or pick one as canonical — see note below) |
| `UTIMCO (Matt Saverin)` | University of Texas Investment Management Company | UTIMCO - Real Estate | Add "UTIMCO (Matt Saverin)" as alias on "UTIMCO - Real Estate" |
| `Merseyside` | Merseyside Pension Fund | Merseyside Pension Fund | Add "Merseyside" as alias |
| `JPMorgan Asset Mgmt` | JPMorgan Asset Management | J.P. Morgan Asset Management | Add "JPMorgan Asset Mgmt" as alias. Note: JSON target says "JPMorgan Asset Management" but CRM org is "J.P. Morgan Asset Management" — use CRM name. |
| `Mass Mutual` | MassMutual | Mass Mutual Life Insurance Co. | Add "Mass Mutual, MassMutual" as aliases |
| `FutureFund` | Future Fund | Future Fund | Add "FutureFund" as alias |
| `Teachers Retirement System (TRS)` | Teachers Retirement System of Texas | Teachers Retirement System of Texas (Texas Teachers) | Add "Teachers Retirement System (TRS), TRS" as aliases |
| `NPS (Korea SWF)` | National Pension Service of Korea | NPS (Korea SWF) | Already the canonical name — no alias needed. Drop from JSON. |

**UTIMCO note:** The CRM has two UTIMCO orgs (Hedge Fund and Real Estate). The JSON maps "UTIMCO" to the pre-split name. For Tony sync purposes, "UTIMCO" as an alias should go on **UTIMCO - Hedge Fund** (Jared Brimberry's division, the active fundraising track). "UTIMCO (Matt Saverin)" should go on **UTIMCO - Real Estate**.

---

## 5. UI / Interface

No UI changes. The org edit page already supports editing the Aliases field inline.

The only visible change: the tony_sync diff report will say "add an alias to the org via the CRM" instead of "update crm/org_aliases.json manually" for low-confidence matches.

---

## 6. Integration Points

### tony_sync.py changes

**Remove:**
```python
ALIASES_PATH = os.path.join(CRM_ROOT, "org_aliases.json")
```

**Remove the entire `load_aliases()` function** (lines ~313–328).

**Replace in `run_sync()`** (line ~796):
```python
# Before:
aliases = load_aliases()

# After:
from app.sources.crm_reader import get_org_aliases_map
aliases = get_org_aliases_map()
```

The return format is identical: `{alias_lower: canonical_org_name}`. No changes needed to `match_org()` or `detect_changes()` — they already accept a generic `aliases: dict` parameter.

**Update diff report text** in `format_diff_report()` (two locations, lines ~648 and ~653):
```python
# Before:
lines.append(f"  Action: NO CHANGE APPLIED — please update crm/org_aliases.json manually")
# ...
lines.append("Low-confidence matches have NOT been applied. Update crm/org_aliases.json to resolve.")

# After:
lines.append(f"  Action: NO CHANGE APPLIED — add an alias to the org in the CRM UI")
# ...
lines.append("Low-confidence matches have NOT been applied. Add aliases via the CRM org edit page to resolve.")
```

### crm_reader.py — no changes

`get_org_aliases_map()` already exists and returns the correct format. No modifications needed.

---

## 7. Constraints

- Migration script must be idempotent — running it twice should not create duplicate aliases
- The `Aliases` field format is comma-separated text (e.g., `Texas PSF, Texas Perm`). New aliases must follow this format.
- `get_org_aliases_map()` is case-insensitive and first-match wins. If the same alias text appears on two different orgs, only the first org (alphabetically by file parse order) gets it. The migration should not introduce collisions.
- Tests in `app/tests/` that reference `org_aliases.json` or `tony_sync.load_aliases()` must be updated.

---

## 8. Acceptance Criteria

1. `crm/org_aliases.json` has been deleted from the repo
2. All 8 aliases from the JSON file are present in the `Aliases` fields of their corresponding orgs in `organizations.md`
3. `tony_sync.py` no longer imports or references `org_aliases.json` or its own `load_aliases()`
4. `tony_sync.py` calls `crm_reader.get_org_aliases_map()` for alias resolution
5. Tony sync diff report text references "CRM org edit page" instead of `org_aliases.json`
6. `python3.12 -m pytest app/tests/ -v --tb=short` passes
7. Manual verification: running tony sync in dry-run mode produces the same alias matches as before (same orgs resolve, same confidence scores)
8. Feedback loop prompt has been run

---

## 9. Files Likely Touched

| File | Change |
|---|---|
| `app/sources/tony_sync.py` | Remove `load_aliases()`, `ALIASES_PATH`. Import and use `get_org_aliases_map()`. Update diff report text. |
| `crm/organizations.md` | Add Aliases to ~7 orgs per migration map in Section 4. |
| `crm/org_aliases.json` | **Delete** after migration verified. |
| `app/tests/test_tony_sync.py` (if exists) | Update any tests that mock `load_aliases()` or reference org_aliases.json. |
