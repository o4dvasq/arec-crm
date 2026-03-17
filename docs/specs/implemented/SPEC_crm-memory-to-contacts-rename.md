SPEC: Rename memory/ to contacts/ in AREC CRM
Project: arec-crm | Branch: markdown-local | Date: 2026-03-14
Status: Ready for implementation

SEQUENCING: Implement AFTER SPEC_crm-markdown-cleanup.md is complete.
DEPENDS ON: Working CRM on markdown-local branch.
BACKEND: All data via crm_reader.py and filesystem — NO crm_db.py, NO models.py, NO SQLAlchemy.
NOTE: Originally written for Azure branch. Scrubbed 2026-03-15 to remove deployment artifact references.

---

## Objective

The AREC CRM codebase contains a `memory/` directory that is a holdover from the productivity plugin's memory management system. In the CRM context, `memory/people/{name}.md` files are contact profiles — not "memories." The `memory/` naming is confusing, blurs the boundary between the local productivity plugin and the deployed CRM application, and should not appear in the deployment artifact. Rename `memory/` to `contacts/` and remove any subdirectories that don't belong in the CRM at all.

## Scope

### In scope

- Rename `memory/people/{name}.md` → `contacts/{name}.md` (flatten — no `people/` subdirectory needed)
- Remove `memory/context/` from CRM entirely (this is productivity-plugin data, not CRM data)
- Remove `memory/glossary.md` from CRM entirely (belongs to productivity plugin)
- Relocate or remove `memory/projects/` — if project data is needed in CRM, move to `projects/` at root level; if it duplicates CRM pipeline data, remove it
- Relocate or remove `memory/meetings.md` — if distinct from `crm/meeting_history.md`, merge; otherwise remove
- Relocate or remove `memory/org-locations.md` — move to `crm/org-locations.md` if needed
- Update all code references across the codebase to reflect new paths
- Update `.gitignore`, deployment scripts, and any path constants

### Out of scope

- Changes to the local productivity plugin's memory system (that stays as `memory/` in the plugin)
- Changes to the `crm/` directory structure itself (e.g., `crm/contacts_index.md` stays as-is)
- Renaming within the productivity plugin codebase — that's a separate concern

## Business Rules

- `contacts/{name}.md` files use the same naming convention: lowercase with hyphens (e.g., `darren-sutton.md`)
- The email-scan skill currently checks `memory/people/` filenames to determine which contacts have profile files for enrichment. After rename, it must check `contacts/` instead.
- The email-scan skill appends email history to `memory/people/{name}.md`. After rename, it appends to `contacts/{name}.md`.
- `crm/contacts_index.md` remains separate — it's the person-email-to-org lookup table. `contacts/{name}.md` files are rich profiles. No naming collision because one is a directory, the other is a file under `crm/`.

## Data Model / Schema Changes

Directory restructure:

```
BEFORE:
memory/
  ├── glossary.md                    ← REMOVE from CRM
  ├── org-locations.md               ← MOVE to crm/org-locations.md
  ├── meetings.md                    ← MERGE into crm/meeting_history.md or REMOVE
  ├── people/
  │   ├── joseph-lyn.md              ← MOVE to contacts/
  │   ├── mike-righetti.md
  │   ├── patrick-fichtner.md
  │   ├── truman-flynn.md
  │   ├── christopher-aiken.md
  │   ├── darren-sutton-dsuttonsuttoncapitalgroupcom.md
  │   ├── max-angeloni.md
  │   ├── kevin-van-gorder.md
  │   ├── ubs-dig.md
  │   ├── partha-manchiraju.md
  │   └── ...
  ├── projects/
  │   └── arec-fund-ii.md            ← MOVE to projects/ or REMOVE if redundant
  └── context/
      ├── company.md                 ← REMOVE from CRM
      └── me.md                      ← REMOVE from CRM

AFTER:
contacts/
  ├── joseph-lyn.md
  ├── mike-righetti.md
  ├── patrick-fichtner.md
  ├── truman-flynn.md
  ├── christopher-aiken.md
  ├── darren-sutton.md               ← also clean up filename
  ├── max-angeloni.md
  ├── kevin-van-gorder.md
  ├── ubs-dig.md
  ├── partha-manchiraju.md
  └── ...
crm/
  ├── org-locations.md               ← moved from memory/
  ├── meeting_history.md             ← merged if needed
  └── (existing files unchanged)
projects/                            ← if kept
  └── arec-fund-ii.md
```

## UI / Interface

N/A — backend/data restructure only.

## Integration Points

### Reads from `memory/people/` (must update to `contacts/`):

1. **Email-scan skill** — checks filenames in `memory/people/` for enrichment targets
2. **Email skill** — may reference contact profiles during email processing
3. **Productivity update command** — loads `memory/` directory for task decoding (BUT this is the local plugin copy, not the CRM deployment — verify whether the deployed CRM app also runs this path)

### Writes to `memory/people/` (must update to `contacts/`):

1. **Email-scan skill** — appends email history to `memory/people/{name}.md`
2. **Any CRM enrichment workflow** that creates or updates contact profiles

### Local config:

1. **`.gitignore`** — if `memory/` has any ignore rules, replicate for `contacts/`

## Constraints

- Do NOT modify the productivity plugin's own `memory/` system — that naming is correct in its own context
- The email-scan skill is shared between the local productivity system and the CRM. Path references in the skill files under `.skills/skills/email-scan/` need to point to `contacts/` for CRM operations.
- Filenames like `darren-sutton-dsuttonsuttoncapitalgroupcom.md` should be cleaned up to just `darren-sutton.md` during migration (the email domain suffix is noise in the filename)
- Preserve all content within the `.md` files — this is a path rename, not a content rewrite

## Acceptance Criteria

- [ ] No `memory/` directory exists in the CRM repo working tree
- [ ] All contact profiles live under `contacts/{name}.md` with clean filenames
- [ ] `memory/context/`, `memory/glossary.md`, and `memory/context/me.md` are not present in the CRM repo
- [ ] `crm/org-locations.md` exists if org-location data was preserved
- [ ] Email-scan skill references `contacts/` instead of `memory/people/`
- [ ] Email skill references updated if applicable
- [ ] `crm/contacts_index.md` unchanged (no collision with `contacts/` directory)
- [ ] All Python code references updated (`crm_reader.py`, `crm_blueprint.py`, etc.)
- [ ] All existing contact data preserved (no data loss)
- [ ] `python3 -m pytest app/tests/ -v` passes
- [ ] Feedback loop prompt has been run

## Files Likely Touched

| File | Reason |
|------|--------|
| `memory/people/*.md` | Move to `contacts/` |
| `memory/org-locations.md` | Move to `crm/` |
| `memory/meetings.md` | Merge or remove |
| `memory/projects/arec-fund-ii.md` | Move to `projects/` or remove |
| `memory/context/*` | Remove from CRM |
| `memory/glossary.md` | Remove from CRM |
| Email-scan SKILL.md (local) | Update path references |
| Email SKILL.md (local) | Update path references if applicable |
| `.gitignore` | Add `contacts/` rules if needed |
| `app/sources/crm_reader.py` | Update all `memory/people/` path references to `contacts/` |
| `app/delivery/crm_blueprint.py` | Update any `memory/people/` route path references |
| `scripts/refresh_interested_briefs.py` | Check for memory/ references |
