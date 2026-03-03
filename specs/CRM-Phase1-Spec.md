# CRM Phase 1 — Data Layer Spec
**For Claude Code**
**Author:** Oscar Vasquez, COO — Avila Real Estate Capital
**Date:** March 2026
**Status:** Ready for Execution

---

## Overview

Build the complete data layer for the AREC Investor CRM. This phase has no UI.
Deliverables are: two config/offering markdown files (manually created), an import
script that seeds the CRM from two Juniper Square CSV exports, a parser module
(`crm_reader.py`), and a full unit test suite.

---

## Environment

- App root: `~/arec-morning-briefing/`
- CRM data files: `~/Dropbox/Tech/ClaudeProductivity/crm/`
- Python: 3.9+ (existing constraint)
- No new pip dependencies (stdlib + `pyyaml`, `python-dotenv` already installed)
- **Do not modify any existing files**

---

## Step 1 — Create Config File (Manual)

Create `~/Dropbox/Tech/ClaudeProductivity/crm/config.md` with exactly this content:

```markdown
# CRM Configuration

## Pipeline Stages
0. Not Pursuing
1. Prospect
2. Cold
3. Outreach
4. Engaged
5. Interested
6. Verbal
7. Legal / DD
8. Committed
9. Closed

## Terminal Stages
- Declined

## Organization Types
- INSTITUTIONAL
- HNWI / FO
- BUILDER
- INTRODUCER

## Closing Options
- 1st
- 2nd
- Final

## Urgency Levels
- High
- Med
- Low

## AREC Team
- Tony Avila
- Oscar Vasquez
- Zach Reisner
- James Walton
- Anthony Albuquerque
- Ian Morgan
- Kevin Van Gorder
- Andrea Tecson
```

---

## Step 2 — Create Offerings File (Manual)

Create `~/Dropbox/Tech/ClaudeProductivity/crm/offerings.md` with exactly this content:

```markdown
# Offerings

## AREC Debt Fund II
- **Target:** $1,000,000,000
- **Hard Cap:**

## Mountain House Refi
- **Target:** $35,000,000
- **Hard Cap:** $35,000,000
```

---

## Step 3 — Build `scripts/import_prospects.py`

Create `~/arec-morning-briefing/scripts/import_prospects.py`.

### Input Files

| File | Path |
|------|------|
| Main CSV (prospects + status) | `~/Downloads/AREC_Debt_Fund_II_prospects_2.csv` |
| Expected CSV (target amounts) | `~/Downloads/AREC_Debt_Fund_II_prospects_with_EXPECTED.csv` |

Both files have a `Prospect ID` column — join them on this key to get the `Expected`
amount for each prospect.

**Expected CSV columns:** `Prospect ID`, `Organization`, `Contacts`, `Expected`

The Expected CSV has 1,303 rows; the main CSV has 1,380. For the ~79 prospects
without a matching Expected row, set `Target` to `$0`.

### Output Files (all in `~/Dropbox/Tech/ClaudeProductivity/crm/`)

The script creates/overwrites these four files. It never touches `offerings.md`
or `config.md`.

| File | Created by |
|------|-----------|
| `organizations.md` | import script |
| `contacts.md` | import script |
| `prospects.md` | import script |
| `interactions.md` | import script |

### Row Filtering

**Include** rows where `Prospect Status` is one of:
- `0. Not Pursuing`
- `1. Prospect`
- `2. Cold`
- `3. Outreach`
- `4. Engaged`
- `5. Interested`
- `6. Verbal`
- `7. Legal / DD`
- `8. Committed`
- `9. Closed`
- `Closed` ← legacy format from Juniper, treat as equivalent to `9. Closed`, store as-is

**Exclude** rows where `Prospect Status` is:
- `Declined`
- Empty/blank
- Any value not in the known list above — print a warning to stdout and skip the row

### Organization Name Resolution

- If `Organization` column is non-empty → use it as the org name
- If `Organization` is empty → use the first contact name (before any `;`) as org name
- Trim all leading/trailing whitespace from names

### Contact Parsing

- Split the `Contacts` column on `;`, trim each name
- Preserve parentheticals in contact names: `Marty Connor (formerly Toll)` → keep as-is
- Preserve quoted nicknames: `Ahmad Aqasyah "Cash" Mohd Noor` → keep as-is
- If `Contacts` is empty for a row, skip contact creation (org still gets created)

### Expected (Target) Amount Parsing

- Join main CSV to Expected CSV on `Prospect ID`
- Parse `Expected` field: strip `$` and commas, strip trailing `.00` → store as full integer string
  - `"$1,000,000.00"` → `$1,000,000`
  - `"$5,000,000.00"` → `$5,000,000`
- If no match in Expected CSV, use `$0`
- If `Expected` value is empty/blank, use `$0`

### Duplicate Org Handling

When the same org name appears on **multiple rows** in the CSV:

1. **Merge contacts** across all rows for that org (union, no duplicates)
2. Create **one prospect record per row** (they are separate pipeline entries)
3. Disambiguate prospect headings by appending `(primary_contact_name)` in parens:
   - `### University of Texas Investment Management Company (UTIMCO) (Jared Brimberry)`
   - `### University of Texas Investment Management Company (UTIMCO) (Matt Saverin)`
4. Apply disambiguation **only** when there are 2+ rows for the same org.
   Single-row orgs use plain `### OrgName` (no parens)

### Prospect Record Fields

All records are placed under `## AREC Debt Fund II` in `prospects.md`.

| Field | Source |
|-------|--------|
| Stage | `Prospect Status` column, stored as-is |
| Target | `Expected` from join, parsed to full integer with `$` prefix |
| Committed | `$0` (hardcoded for all imports) |
| Primary Contact | First name from `Contacts` column (before first `;`) |
| Closing | `Closing` column, blank if empty |
| Urgency | `Urgency` column, blank if empty |
| Assigned To | `Assigned to` column, blank if empty |
| Notes | `Notes/History/Last Update` column, blank if empty |
| Next Action | `Next Action` column, blank if empty |
| Last Touch | `2026-02-28` (hardcoded for all imports) |

### Output File Formats

**`organizations.md`**
```markdown
# Organizations

## OrgName
- **Type:** INSTITUTIONAL
- **Notes:**

## AnotherOrg
- **Type:** HNWI / FO
- **Notes:**
```

**`contacts.md`**
```markdown
# Contacts

## OrgName

### ContactName
- **Title:**
- **Email:**
- **Phone:**
- **Notes:**

### AnotherContact
- **Title:**
- **Email:**
- **Phone:**
- **Notes:**
```

**`prospects.md`**
```markdown
# Prospects

## AREC Debt Fund II

### OrgName
- **Stage:** 3. Outreach
- **Target:** $5,000,000
- **Committed:** $0
- **Primary Contact:** Jane Smith
- **Closing:**
- **Urgency:** High
- **Assigned To:** James Walton
- **Notes:** Some notes here
- **Next Action:** Send deck
- **Last Touch:** 2026-02-28

### AnotherOrg (Disambiguated) (Contact A)
- **Stage:** 6. Verbal
- **Target:** $50,000,000
- **Committed:** $0
- **Primary Contact:** Contact A
- **Closing:** Final
- **Urgency:** High
- **Assigned To:** Tony Avila
- **Notes:**
- **Next Action:**
- **Last Touch:** 2026-02-28
```

**`interactions.md`**
```markdown
# Interaction Log
```
(Empty log — just the header, no entries.)

### Script Output (stdout summary)

```
Import complete.
  Rows processed:              XXXX
  Rows skipped (Declined):     XXXX
  Rows skipped (unknown status): XX
  Rows skipped (blank status):    X
  Organizations created:       XXXX
  Contacts created:            XXXX
  Prospects created:           XXXX
    └── Disambiguated headings:   X
  Target amounts joined:       XXXX
  Target amounts defaulted $0:   XX
```

---

## Step 4 — Run the Import Script

```bash
cd ~/arec-morning-briefing
python3 scripts/import_prospects.py
```

Verify output:

```bash
# Check files were created and are non-empty
ls -lh ~/Dropbox/Tech/ClaudeProductivity/crm/

# Count prospect headings (should be ~1300+)
grep -c "^### " ~/Dropbox/Tech/ClaudeProductivity/crm/prospects.md

# Count org headings
grep -c "^## " ~/Dropbox/Tech/ClaudeProductivity/crm/organizations.md

# Spot-check first 50 lines of prospects
head -50 ~/Dropbox/Tech/ClaudeProductivity/crm/prospects.md

# Confirm no Declined records made it in
grep -i "declined" ~/Dropbox/Tech/ClaudeProductivity/crm/prospects.md || echo "Clean — no declined records"
```

---

## Step 5 — Build `sources/crm_reader.py`

Create `~/arec-morning-briefing/sources/crm_reader.py`.

Base path for all CRM files: `~/Dropbox/Tech/ClaudeProductivity/crm/`
Use `os.path.expanduser` — this must work on any of Oscar's Macs.

### Internal Parsing Utilities

These are private helper functions (prefix `_`):

```python
def _crm_path(filename: str) -> str:
    """Resolve filename to full path under the crm/ directory."""

def _read_file(filename: str) -> str:
    """Read a CRM markdown file. Returns empty string if file doesn't exist."""

def _write_file(filename: str, content: str) -> None:
    """Write content to a CRM markdown file."""

def _parse_sections_l1(content: str) -> dict[str, str]:
    """
    Parse level-1 sections from markdown content.
    ## Heading → {heading_text: body_text}
    heading_text has leading/trailing whitespace stripped.
    body_text is everything until the next ## heading or end of file.
    """

def _parse_sections_l2(content: str) -> dict[str, dict[str, str]]:
    """
    Parse two-level sections from markdown content.
    ## L1 Heading → ### L2 Heading → {l1: {l2: body_text}}
    Used for contacts.md (## Org → ### Contact) and
    prospects.md (## Offering → ### Org).
    """

def _parse_fields(body: str) -> dict[str, str]:
    """
    Parse key-value fields from a section body.
    Matches lines like: - **Field Name:** Value
    Returns {field_name_lowercase: value_stripped}
    Returns empty string for missing fields, never raises.
    Preserves unrecognized lines (non-field lines) in a '_raw' key as a list.
    """

def _fields_to_markdown(data: dict, field_order: list[str]) -> str:
    """
    Serialize a dict to markdown field lines.
    - **Field Name:** Value
    field_order controls the output order (Title Case field names).
    Fields not in field_order but present in data are appended at end.
    """

def _format_currency(n: float) -> str:
    """
    Format a number as abbreviated currency string for display.
    1_500_000_000 → "$1.5B"
    50_000_000    → "$50M"
    500_000       → "$500K"
    1_000         → "$1K"
    0             → "$0"
    """

def _parse_currency(s: str) -> float:
    """
    Parse a currency string to float.
    "$50,000,000" → 50000000.0
    "$50M"        → 50000000.0
    "$500K"       → 500000.0
    "$1.5B"       → 1500000000.0
    ""            → 0.0
    Never raises — returns 0.0 on any parse error.
    """
```

### Config

```python
def load_crm_config() -> dict:
    """
    Parse config.md and return:
    {
      'stages': ['0. Not Pursuing', '1. Prospect', ...],
      'terminal_stages': ['Declined'],
      'org_types': ['INSTITUTIONAL', 'HNWI / FO', ...],
      'closing_options': ['1st', '2nd', 'Final'],
      'urgency_levels': ['High', 'Med', 'Low'],
      'team': ['Tony Avila', 'Oscar Vasquez', ...]
    }
    """
```

### Offerings

```python
def load_offerings() -> list[dict]:
    """
    Parse offerings.md.
    Each dict: {'name': str, 'target': str, 'hard_cap': str}
    target and hard_cap are raw strings as stored in file (e.g. "$1,000,000,000").
    """

def get_offering(name: str) -> dict | None:
    """Return single offering dict or None if not found."""
```

### Organizations

```python
def load_organizations() -> list[dict]:
    """
    Parse organizations.md.
    Each dict: {'name': str, 'type': str, 'notes': str}
    """

def get_organization(name: str) -> dict | None:
    """Return single org dict or None. Case-sensitive match."""

def write_organization(name: str, data: dict) -> None:
    """
    Create or update an organization.
    If org exists: update only the fields present in data, preserve others.
    If org doesn't exist: append new ## section at end of file.
    data keys: 'type', 'notes' (any subset)
    """

def delete_organization(name: str) -> None:
    """Remove the ## OrgName section and its body from organizations.md."""
```

### Contacts

```python
def load_contacts(org: str = None) -> list[dict]:
    """
    Parse contacts.md (two-level: ## Org → ### Contact).
    Each dict: {'name': str, 'organization': str, 'title': str,
                'email': str, 'phone': str, 'notes': str}
    If org is provided, return only contacts for that org.
    """

def get_contact(name: str, org: str) -> dict | None:
    """Return single contact dict. Matches by name and org."""

def get_contacts_for_org(org: str) -> list[dict]:
    """Return all contacts for a given org."""

def write_contact(name: str, org: str, data: dict) -> None:
    """
    Create or update a contact.
    If org section doesn't exist in contacts.md, create it.
    If contact exists under that org, update fields in data, preserve others.
    If contact doesn't exist, append new ### section under org.
    data keys: 'title', 'email', 'phone', 'notes' (any subset)
    """

def delete_contact(name: str, org: str) -> None:
    """Remove the ### ContactName section under the given org."""
```

### Prospects

```python
def load_prospects(offering: str = None) -> list[dict]:
    """
    Parse prospects.md (two-level: ## Offering → ### Org).
    Each dict:
      {
        'org': str,               # Org name (without disambiguator)
        'offering': str,          # Offering name
        'stage': str,
        'target': str,            # Raw string as stored, e.g. "$5,000,000"
        'committed': str,
        'primary_contact': str,
        'closing': str,
        'urgency': str,
        'assigned_to': str,
        'notes': str,
        'next_action': str,
        'last_touch': str,        # YYYY-MM-DD
        '_heading_key': str       # The actual ### heading text (includes disambiguator if any)
      }
    If offering is provided, filter to that offering only.
    'org' is the heading text stripped of any trailing (ContactName) disambiguator.
    """

def get_prospect(org: str, offering: str) -> dict | None:
    """
    Return a single prospect dict.
    Matches where _heading_key starts with org (handles disambiguation).
    If multiple matches (disambiguated), returns the first one.
    Use get_prospects_for_org() when you need all records for an org.
    """

def write_prospect(org: str, offering: str, data: dict) -> None:
    """
    Create or update a prospect.
    Matches existing record by: offering section + heading starts with org.
    If prospect exists: update fields in data, preserve unrecognized fields.
    If offering section doesn't exist in prospects.md: create it.
    If prospect doesn't exist in the offering: append new ### section.
    New prospects use plain ### OrgName heading (no disambiguator).
    data keys: any subset of prospect fields.
    """

def delete_prospect(org: str, offering: str) -> None:
    """Remove the ### section for this org under the given offering."""

def update_prospect_field(org: str, offering: str, field: str, value: str) -> None:
    """
    Update a single field on a prospect.
    Also updates 'last_touch' to today's date (YYYY-MM-DD)
    unless the field being updated IS 'last_touch'.
    """

def get_prospects_for_org(org: str) -> list[dict]:
    """
    Return all prospect records across all offerings where org name matches.
    Matches by: _heading_key starts with org.
    """
```

### Pipeline & Fund Summary

```python
def get_pipeline_summary(offering: str) -> dict:
    """
    Returns pipeline breakdown for a given offering.
    {
      '6. Verbal': {'count': 4, 'total_target': 155000000.0, 'total_committed': 0.0},
      '5. Interested': {'count': 12, ...},
      ...
    }
    Sorted by stage number (stages without a number sort to end).
    Uses _parse_currency() to convert target/committed strings to floats.
    """

def get_fund_summary(offering: str) -> dict:
    """
    Returns:
    {
      'offering': str,
      'total_committed': float,
      'target': float,
      'hard_cap': float,
      'pct_committed': float,   # total_committed / target * 100
      'prospect_count': int
    }
    """

def get_fund_summary_all() -> list[dict]:
    """One get_fund_summary() dict per offering in offerings.md."""
```

### Interactions

```python
def load_interactions(org: str = None, offering: str = None,
                      limit: int = None) -> list[dict]:
    """
    Parse interactions.md (grouped by ## YYYY-MM-DD date sections).
    Each dict:
      {
        'date': str,         # YYYY-MM-DD from section heading
        'org': str,
        'type': str,         # Email, Meeting, Call, Note, etc.
        'offering': str,
        'contact': str,
        'subject': str,
        'summary': str,
        'source': str        # manual, auto-graph, auto-notion
      }
    Returns newest first (reverse date order).
    Optional filters: org (exact match), offering (exact match).
    Optional limit: return only the first N results after filtering.
    """

def append_interaction(entry: dict) -> None:
    """
    Append an interaction to interactions.md.
    entry keys: org, type, offering, contact, subject, summary, source

    Format appended:
      ## YYYY-MM-DD       ← today; creates section if it doesn't exist
      
      ### {org} — {type} — {offering}
      - **Contact:** {contact}
      - **Subject:** {subject}
      - **Summary:** {summary}
      - **Source:** {source}

    After appending, if offering is provided and non-empty:
      call update_prospect_field(org, offering, 'last_touch', today)
    """
```

### Cross-Reference Helpers

```python
def get_prospect_full(org: str, offering: str) -> dict | None:
    """
    Returns a prospect dict enriched with:
      'org_record': get_organization(org)          # may be None
      'contact_record': resolve_primary_contact(org, prospect['primary_contact'])  # may be None
      'recent_interactions': load_interactions(org=org, offering=offering, limit=10)
    Returns None if prospect not found.
    """

def resolve_primary_contact(org: str, contact_name: str) -> dict | None:
    """Return contact dict from contacts.md matching name and org. None if not found."""
```

### Implementation Notes

- All file reads are **fresh on every call** — no module-level caching
- Write operations use **read-modify-write**: read full file → mutate in memory → write full file
- Field names are **Title Case on write**, **case-insensitive on read**
- Write operations **preserve field order** for known fields and preserve unrecognized fields
- `_parse_fields` must never raise — missing fields return `''`
- Prospect field order for writes (always use this order):
  `Stage, Target, Committed, Primary Contact, Closing, Urgency,
   Assigned To, Notes, Next Action, Last Touch`

---

## Step 6 — Build `tests/test_crm_reader.py`

Create `~/arec-morning-briefing/tests/test_crm_reader.py`.

Use Python's built-in `unittest`. All tests use a **temporary directory**
(`tempfile.mkdtemp`) with small in-memory fixture files — never touch real
Dropbox files. Patch `crm_reader._crm_path` to point to the temp dir.

### Required Test Cases

```
TestCurrencyHelpers
  test_format_currency_billions          # 1_500_000_000 → "$1.5B"
  test_format_currency_millions          # 50_000_000 → "$50M"
  test_format_currency_thousands         # 500_000 → "$500K"
  test_format_currency_zero              # 0 → "$0"
  test_parse_currency_full_number        # "$50,000,000" → 50000000.0
  test_parse_currency_abbreviated_M      # "$50M" → 50000000.0
  test_parse_currency_abbreviated_K      # "$500K" → 500000.0
  test_parse_currency_abbreviated_B      # "$1.5B" → 1500000000.0
  test_parse_currency_empty_string       # "" → 0.0
  test_parse_currency_no_crash_on_junk   # "N/A" → 0.0

TestConfig
  test_load_crm_config_returns_all_keys
  test_load_crm_config_stages_count
  test_load_crm_config_team_members

TestOfferings
  test_load_offerings_count
  test_get_offering_found
  test_get_offering_not_found

TestOrganizations
  test_load_organizations
  test_get_organization_found
  test_get_organization_not_found
  test_write_organization_create_new
  test_write_organization_update_preserves_existing_fields
  test_delete_organization

TestContacts
  test_load_contacts_all
  test_load_contacts_filtered_by_org
  test_get_contact_found
  test_get_contact_not_found
  test_get_contacts_for_org
  test_write_contact_create_under_existing_org
  test_write_contact_create_with_new_org_section
  test_write_contact_update_preserves_fields
  test_delete_contact

TestProspects
  test_load_prospects_all
  test_load_prospects_filtered_by_offering
  test_get_prospect_simple_heading           # plain ### OrgName
  test_get_prospect_disambiguated_heading    # ### OrgName (Contact)
  test_write_prospect_create_new
  test_write_prospect_update_existing_preserves_fields
  test_write_prospect_creates_offering_section_if_missing
  test_update_prospect_field_updates_field
  test_update_prospect_field_sets_last_touch_automatically
  test_update_prospect_field_last_touch_no_double_update
  test_delete_prospect
  test_get_prospects_for_org_across_offerings

TestPipeline
  test_get_pipeline_summary_stage_counts
  test_get_pipeline_summary_sorted_by_stage_number
  test_get_fund_summary_fields_present
  test_get_fund_summary_pct_calculation
  test_get_fund_summary_all_returns_all_offerings

TestInteractions
  test_load_interactions_all
  test_load_interactions_filter_by_org
  test_load_interactions_limit
  test_load_interactions_newest_first
  test_append_interaction_creates_date_section
  test_append_interaction_adds_to_existing_date_section
  test_append_interaction_updates_prospect_last_touch

TestCrossReference
  test_get_prospect_full_returns_enriched_dict
  test_get_prospect_full_not_found_returns_none
  test_resolve_primary_contact_found
  test_resolve_primary_contact_not_found
```

### Run Tests

```bash
cd ~/arec-morning-briefing

# Using pytest (preferred)
python3 -m pytest tests/test_crm_reader.py -v

# Using unittest (no extra deps)
python3 -m unittest tests/test_crm_reader.py -v
```

**All tests must pass before Phase 1 is considered complete.**

---

## Deliverables Checklist

```
[ ] ~/Dropbox/Tech/ClaudeProductivity/crm/config.md          ← manual (Step 1)
[ ] ~/Dropbox/Tech/ClaudeProductivity/crm/offerings.md        ← manual (Step 2)
[ ] ~/arec-morning-briefing/scripts/import_prospects.py       ← Step 3
[ ] ~/Dropbox/Tech/ClaudeProductivity/crm/organizations.md    ← generated (Step 4)
[ ] ~/Dropbox/Tech/ClaudeProductivity/crm/contacts.md         ← generated (Step 4)
[ ] ~/Dropbox/Tech/ClaudeProductivity/crm/prospects.md        ← generated (Step 4)
[ ] ~/Dropbox/Tech/ClaudeProductivity/crm/interactions.md     ← generated (Step 4)
[ ] ~/arec-morning-briefing/sources/crm_reader.py             ← Step 5
[ ] ~/arec-morning-briefing/tests/test_crm_reader.py          ← Step 6
[ ] All unit tests passing                                     ← Step 6
```

---

## What's NOT In This Phase

- No Flask routes or UI (Phase 2)
- No inline editing (Phase 3)
- No org detail page (Phase 4)
- No Microsoft Graph auto-capture (Phase 5)
- No analytics charts (Phase 6)
- No dashboard changes (Phase 7)

---

*When Phase 1 is complete and all tests pass, return for the Phase 2 spec
(read-only prospects table at `/crm`).*
