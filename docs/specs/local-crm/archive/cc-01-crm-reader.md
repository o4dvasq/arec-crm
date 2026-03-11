# CC-01: crm_reader.py — CRM Data Parser Module

**Target:** `~/Dropbox/Tech/ClaudeProductivity/app/sources/crm_reader.py`
**Depends on:** Nothing (first module to build)
**Blocks:** CC-02, CC-03, CC-04, CC-05

---

## Purpose

Single Python module that reads and writes all CRM markdown files in `~/Dropbox/Tech/ClaudeProductivity/crm/`. Every downstream consumer (Flask API, auto-capture, briefing) imports this module. No parsing logic should exist anywhere else.

## Configuration

```python
# App lives at ClaudeProductivity/app/sources/crm_reader.py
# Data lives at ClaudeProductivity/crm/ and ClaudeProductivity/memory/
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../app
PROJECT_ROOT = os.path.dirname(APP_ROOT)  # .../ClaudeProductivity
CRM_ROOT = os.path.join(PROJECT_ROOT, "crm")
MEMORY_ROOT = os.path.join(PROJECT_ROOT, "memory")
```

## File Formats (from live data)

### config.md

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

### offerings.md

```markdown
# Offerings

## AREC Debt Fund II
- **Target:** $1,000,000,000
- **Hard Cap:**

## Mountain House Refi
- **Target:** $35,000,000
- **Hard Cap:** $35,000,000
```

### organizations.md

Two-level: `## Org Name` then `- **Field:** value` lines. ~1,292 orgs.

```markdown
# Organizations

## Merseyside Pension Fund
- **Type:** INSTITUTIONAL
- **Notes:** UK-based pension fund.

## 1900 Wealth
- **Type:** HNWI / FO
- **Notes:**
```

### prospects.md

Three-level: `## Offering` → `### Org Name` → `- **Field:** value`. ~1,313 prospects across 2 offerings, ~15,700 lines.

Disambiguated headings when same org appears twice under same offering:
```markdown
### UTIMCO (Jared Brimberry)
### UTIMCO (Matt Saverin)
```

```markdown
# Prospects

## AREC Debt Fund II

### Merseyside Pension Fund
- **Stage:** 6. Verbal
- **Target:** $50,000,000
- **Committed:** $0
- **Primary Contact:** Susannah Friar
- **Closing:** Final
- **Urgency:** High
- **Assigned To:** James Walton
- **Notes:** Sent Credit and Index Comparisons on 2/25
- **Next Action:** Meeting March 2
- **Last Touch:** 2026-03-01
```

**Field write order (always this order on write):** Stage, Target, Committed, Primary Contact, Closing, Urgency, Assigned To, Notes, Next Action, Last Touch

### interactions.md

Append-only. Grouped by `## Date` → `### Org — Type — Offering`.

```markdown
# Interaction Log

## 2026-03-02

### Tony Avila — Email — AREC Debt Fund II
- **Contact:**
- **Subject:** AREC Debt Fund II Marketing A List
- **Summary:** Auto-captured: Tony Avila → marketing list
- **Source:** auto-graph
```

### contacts_index.md

Maps `## Org Name` → list of person slugs (filenames in `memory/people/`).

```markdown
# Contacts Index

## Tony Avila
- tony-avila

## University of Texas Investment Management Company (UTIMCO) (Jared Brimberry)
- jared-brimberry
```

### unmatched_review.json

```json
{
  "last_scan": "2026-03-02T07:50:16",
  "items": [
    {
      "source": "email",
      "date": "2026-03-02",
      "participant_email": "susannahfriar@wirral.gov.uk",
      "participant_name": "Friar, Susannah L.",
      "subject": "RE: [EXTERNAL]Encore Fund III",
      "reason": "No email match; org name not found in display name"
    }
  ]
}
```

### pending_interviews.json

```json
{
  "pending": [
    {
      "org": "Merseyside Pension Fund",
      "offering": "AREC Debt Fund II",
      "meeting_date": "2026-03-02",
      "meeting_title": "Fund II Discussion",
      "detected_at": "2026-03-02T05:00:00"
    }
  ]
}
```

Dedup: one entry per org (most recent meeting wins). Purge items > 7 days old on each write.

## Required Functions

```python
# --- Config ---
load_crm_config() → dict
# Returns: {'stages': [...], 'terminal_stages': [...], 'org_types': [...],
#           'closing_options': [...], 'urgency_levels': [...], 'team': [...]}

# --- Offerings ---
load_offerings() → list[dict]
get_offering(name: str) → dict | None

# --- Organizations ---
load_organizations() → list[dict]
get_organization(name: str) → dict | None
write_organization(name: str, data: dict) → None
delete_organization(name: str) → None

# --- Contacts (via contacts_index.md + memory/people/) ---
load_contacts_index() → dict  # {org_name: [slug, ...]}
get_contacts_for_org(org_name: str) → list[dict]
load_person(slug: str) → dict | None
find_person_by_email(email: str) → dict | None
create_person_file(name: str, org: str, email: str, role: str, person_type: str) → str  # returns slug
enrich_person_email(slug: str, email: str) → None

# --- Prospects (two-level: offering → org) ---
load_prospects(offering: str = None) → list[dict]
get_prospect(org: str, offering: str) → dict | None
write_prospect(org: str, offering: str, data: dict) → None
delete_prospect(org: str, offering: str) → None
update_prospect_field(org: str, offering: str, field: str, value: str) → None
  # MUST also auto-update last_touch to today's date (YYYY-MM-DD)
get_prospects_for_org(org: str) → list[dict]  # across all offerings

# --- Pipeline ---
get_pipeline_summary(offering: str) → dict
get_fund_summary(offering: str) → dict
get_fund_summary_all() → list[dict]

# --- Interactions ---
load_interactions(org: str = None, offering: str = None, limit: int = None) → list[dict]
append_interaction(entry: dict) → None
  # MUST also call update_prospect_field(..., 'last_touch', today)

# --- Cross-reference ---
get_prospect_full(org: str, offering: str) → dict | None
  # Returns prospect + org data + contacts merged
resolve_primary_contact(org: str, contact_name: str) → dict | None
  # Searches contacts_index → memory/people/ for match

# --- Pending Interviews ---
load_pending_interviews() → list[dict]
add_pending_interview(entry: dict) → None  # dedup by org, purge > 7 days
remove_pending_interview(org: str) → None

# --- Unmatched Review ---
load_unmatched() → list[dict]
add_unmatched(item: dict) → None  # merge, dedupe by email
remove_unmatched(email: str) → None
purge_old_unmatched(days: int = 14) → None

# --- Currency helpers ---
_format_currency(n: float) → str   # 50000000 → "$50M", 1500000000 → "$1.5B"
_parse_currency(s: str) → float    # "$50,000,000" → 50000000.0, "$50M" → 50000000.0
```

## Parser Rules

- All reads are fresh from disk (no caching)
- Write = read full file → mutate in memory → write full file
- Field names: Title Case on write, case-insensitive on read
- Missing fields → empty string `''`, never raise
- Prospect field write order: Stage, Target, Committed, Primary Contact, Closing, Urgency, Assigned To, Notes, Next Action, Last Touch
- Org heading match is case-insensitive
- Handle disambiguated headings: `### UTIMCO (Jared Brimberry)` — the org name is "UTIMCO", the parenthetical is the disambiguator

## Tests

Create `tests/test_crm_reader.py` with:

1. Parse config.md → verify stages list, team roster
2. Parse offerings.md → verify target amounts
3. Parse organizations.md → get a known org, verify type
4. Parse prospects.md → get Merseyside, verify Stage=6. Verbal, Target=$50,000,000
5. Parse interactions.md → load by org, verify fields
6. Write a prospect field → verify last_touch auto-updates
7. Append interaction → verify dedup check
8. Currency round-trip: `_parse_currency(_format_currency(50000000))` == 50000000.0
9. Load contacts_index → verify org→slug mapping
10. Disambiguated headings: parse "UTIMCO (Jared Brimberry)" correctly

Use the actual live files in `~/Dropbox/Tech/ClaudeProductivity/crm/` for integration tests. Create copies in a `tests/fixtures/` directory for unit tests.

## Acceptance Criteria

- All functions above exist and pass tests
- `cd ~/Dropbox/Tech/ClaudeProductivity/app && python -c "from sources.crm_reader import load_prospects; print(len(load_prospects()))"` returns ~1,313
- No external dependencies beyond Python stdlib + pyyaml (already in requirements.txt)
- Module is importable from `~/Dropbox/Tech/ClaudeProductivity/app/`
