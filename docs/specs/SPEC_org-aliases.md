# SPEC: Organization Aliases (AKA)

**Project:** arec-crm
**Date:** March 11, 2026
**Status:** Ready for implementation

> **⚠️ MIGRATION NOTE (March 12, 2026):** This spec was written before the Azure migration. The app now runs on PostgreSQL only — `crm_reader.py` is deleted. All references to `crm_reader.py` below should be read as `crm_db.py`. The `organizations` table in PostgreSQL has an `aliases` column (TEXT, nullable). Implement alias functions in `crm_db.py`. Do NOT create or import `crm_reader.py`. Work on `azure-migration` branch.

---

## 1. Objective

Surface and leverage the existing but dormant Aliases field on organizations so that alternate names (abbreviations, acronyms, common nicknames) are visible in the UI, editable by the user, and used throughout the system for matching. This closes a gap where context about an org gets lost when emails, meeting notes, or conversations refer to it by an alias (e.g., "SMBC" instead of "Sumitomo Mitsui Banking Corporation").

---

## 2. Scope

**In scope:**
- Display Aliases field on the org edit page (`crm_org_edit.html`)
- Make Aliases inline-editable (same click-to-edit pattern as Type/Domain/Notes)
- Accept Aliases in the `PATCH /crm/api/org/<name>` endpoint
- New `get_org_by_alias(alias: str) -> str | None` lookup function in `crm_reader.py`
- New `get_org_aliases_map() -> dict` function returning `{alias_lower: org_name}` for all orgs
- Include aliases in the global search index so searching "SMBC" finds "Sumitomo Mitsui Banking Corporation"
- Update `email-scan.md` skill instructions to add a Tier 1.5 alias-matching step for email subject/body text

**Out of scope:**
- Automatic alias detection or suggestion (user manages aliases manually)
- Changes to how `memory/people/*.md` files reference org names
- Aliases on person records (people do not have aliases)
- Fuzzy/phonetic matching — aliases are exact string matches (case-insensitive)
- Migration script to backfill aliases for existing orgs (can be done manually or in a follow-up)

---

## 3. Business Rules

1. **Aliases are comma-separated strings.** Stored as `- **Aliases:** SMBC, Sumitomo Mitsui` in `organizations.md`. Parsed by splitting on commas and trimming whitespace.
2. **Alias matching is case-insensitive and exact.** "SMBC" matches "smbc" or "Smbc" but not "SMBC Capital" (substring matching is not supported to avoid false positives).
3. **Aliases must be unique across all orgs.** If two orgs claim the same alias, the system should log a warning but not crash. First match wins during lookup.
4. **Aliases do not replace the canonical org name.** The org name (the `## Heading` in organizations.md) remains the primary identifier everywhere. Aliases are lookup shortcuts only.
5. **Empty aliases field is hidden.** If no aliases exist, the field row should not render on the org edit page (consistent with project-wide empty-field pattern). However, clicking an "Add Aliases" link or a placeholder should allow the user to start editing.
6. **The Aliases field already exists in `_FIELD_ORDER`** in `write_organization()` at position index 1 (between Type and Domain). No changes needed to the write logic — it already persists Aliases when present.

---

## 4. Data Model / Schema Changes

### No schema changes required.

The Aliases field is already part of the canonical field order in `crm_reader.py` line 268:

```python
_FIELD_ORDER = ['Type', 'Aliases', 'Domain', 'Contacts', 'Stage', 'Notes']
```

It is already parsed by `_parse_bullet_fields()` and written by `write_organization()`. The field just needs to be wired into the UI and matching logic.

### Existing format in `crm/organizations.md`:

```markdown
## Texas Permanent School Fund
- **Type:** Endowment
- **Aliases:** Texas PSF, Texas Perm
- **Domain:** @texaspsf.org
- **Notes:**
```

---

## 5. UI / Interface

### Org Edit Page (`crm_org_edit.html`)

**Current summary grid:** Type | Domain | (spacer)

**New summary grid:** Type | Domain | Aliases

The Aliases cell replaces the empty spacer `<div>` in the third column of `.summary-grid`.

- **Label:** "ALIASES" (uppercase, matching existing field-label style)
- **Display value:** Comma-separated alias list, e.g., "SMBC, Sumitomo Mitsui"
- **Empty state:** Muted dash `—` (same as other fields), clickable to start editing
- **Edit mode:** Click-to-edit text input (same pattern as Domain). Placeholder text: `e.g. SMBC, Sumitomo Mitsui`
- **Save trigger:** Blur or Enter key, same as Domain field
- **Save endpoint:** `PATCH /crm/api/org/<name>` with `{"aliases": "SMBC, Sumitomo Mitsui"}`

### Global Search

The `inject_search_index()` context processor in `crm_blueprint.py` (line 58) builds the search index. For org entries, add aliases to the `secondary` field (currently empty string for orgs):

```python
'secondary': org.get('Aliases', ''),
```

This way, typing "SMBC" in the search bar surfaces "Sumitomo Mitsui Banking Corporation" with "SMBC, Sumitomo Mitsui" shown as secondary text.

---

## 6. Integration Points

### Reads from:
- `crm/organizations.md` — Aliases field parsed by `load_organizations()` / `get_organization()`

### Writes to:
- `crm/organizations.md` — via `write_organization()` (already handles Aliases in field order)

### Called by:
- **Email scan skill** (`skills/email-scan.md`) — new Tier 1.5 step: after domain match fails, check email subject line against alias map before falling back to person match
- **Global search index** — aliases included in secondary search text
- **Relationship brief synthesis** — when collecting context for an org, mention known aliases so Claude can correlate references in meeting notes and emails
- **`get_organization()`** — currently only matches on canonical name; add fallback to alias lookup

---

## 7. Constraints

1. **`crm_reader.py` is the only parser.** All alias parsing and lookup must go through `crm_reader.py`. No ad-hoc parsing of `organizations.md` elsewhere.
2. **Performance is not a concern.** There are ~200 orgs. Building the alias map on every call is fine — no caching needed.
3. **Alias lookup returns the canonical org name, not the alias.** All downstream code continues to use canonical names.
4. **Do not modify `get_org_domains()` or `get_org_by_domain()`.** Alias matching is a separate lookup path, not a modification to domain matching.

---

## 8. Acceptance Criteria

1. Aliases field is visible and editable on the org edit page for orgs that have aliases.
2. Clicking the aliases placeholder on an org with no aliases opens the inline editor.
3. Saving aliases via the inline editor persists to `organizations.md` in the correct field position.
4. `get_org_by_alias("SMBC")` returns `"Sumitomo Mitsui Banking Corporation"` (assuming that alias is set).
5. `get_org_by_alias("smbc")` also returns the same result (case-insensitive).
6. `get_org_aliases_map()` returns a complete `{alias_lower: org_name}` dict for all orgs with aliases.
7. Global search for "SMBC" returns the correct org in results.
8. `PATCH /crm/api/org/<name>` accepts `aliases` key and persists it.
9. Existing org fields (Type, Domain, Notes) are unaffected by the change.
10. `email-scan.md` skill instructions include a Tier 1.5 alias-matching step.
11. Feedback loop prompt has been run.

---

## 9. Files Likely Touched

| File | Reason |
|------|--------|
| `app/sources/crm_reader.py` | Add `get_org_by_alias()`, `get_org_aliases_map()`. Optionally update `get_organization()` to fall back to alias lookup. |
| `app/delivery/crm_blueprint.py` | Accept `aliases` in `api_org_patch()`. Add aliases to `inject_search_index()` secondary field. |
| `app/templates/crm_org_edit.html` | Add Aliases cell to summary grid. Add aliases to `orgData` JS object. Add startEdit/save handling for aliases field. |
| `skills/email-scan.md` | Add Tier 1.5 alias-matching instructions between Tier 1 (domain) and Tier 2 (person). |
| `app/sources/relationship_brief.py` | Include org aliases in the context block passed to Claude for brief synthesis. |
