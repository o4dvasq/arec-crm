# SPEC: Tony Excel → CRM Sync

**Project:** arec-crm | **Branch:** markdown-local | **Date:** March 13, 2026
**Status:** Future — needs review before implementation
**Author:** Oscar Vasquez / Claude

SEQUENCING: Implement AFTER core CRM is stable (cleanup + tasks page + search bar done). Low priority — Tony can continue using his Excel workflow independently.
DEPENDS ON: SPEC_crm-markdown-cleanup.md, working CRM on markdown-local.
BACKEND: Already uses crm_reader.py for all reads/writes — no scrubbing needed.

---

## 1. Objective

Tony Avila maintains a fundraising tracker in Excel (`AREC Debt Fund II Marketing A List - MASTER as of [Date].xlsx`) stored in Egnyte. He will not use Overwatch directly, but his file is the authoritative source for prospect-level updates from his relationship network. This feature polls that Egnyte folder every morning at 6 AM, detects new or changed versions of his file, parses the changes, and syncs them into `prospects.md` — with a human review step via email before any writes occur.

---

## 2. Scope

**In scope:**
- Poll Egnyte folder for new versions of Tony's file (6 AM daily via launchd)
- Parse the Active sheet; map rows to CRM prospect records
- Fuzzy org name matching with alias lookup, auto-accept above confidence threshold
- Detect three change types: (a) new org not in CRM, (b) changed Assigned To, (c) changed Notes
- Priority `x` in Tony's sheet → stage `0. Declined` in CRM
- New orgs → create as Stage `5. Interested`, Urgency `High`
- Send diff email to Oscar and Paige Kinsey before writing anything
- Write approved changes to `prospects.md`

**Out of scope:**
- Tony's Excel columns D–I (Fund I, Spring Rock, Verbal pool, Lutheran, The Ridge, Mountain House Refi)
- Tony's Priority column (except `x` = Declined signal)
- Next Action field sync (separate spec)
- Paige Kinsey's Overwatch user account and permissions (separate spec)
- Webhook-based triggering (requires public HTTPS endpoint; not available in current local Flask architecture)
- Two-way sync (CRM → Tony's Excel)
- Conflict resolution for Stage, Urgency, Target, Committed (CRM always wins on those fields)

---

## 3. Business Rules

### 3.1 File Detection
- Target folder (Egnyte path): `Shared/AREC/Investor Relations/General Fundraising/`
- Target filename pattern: `AREC Debt Fund II Marketing A List - MASTER as of *.xlsx` (glob match)
- Also match: `AREC Debt Fund II Marketing A List - MASTER v*.xlsx`
- Ignore files in the `Archive/` subfolder
- Track the last-processed file in `crm/tony_sync_state.json` (filename + Egnyte checksum/modified timestamp)
- On each poll: list matching files, sort by modified date descending, take the most recent
- If most recent file == last processed file → no-op, exit silently
- If new file found → process it

### 3.2 Excel Parsing (Active Sheet)
- Row 4 is the header row: `[None, 'Investors', 'AREC Point Person', 'Fund I', 'Fund II', ...]`
- Data rows start at row 6
- Column map:
  - Col A (index 0): Priority — values: `'Closed'`, `1`, `2`, `3`, `'x'`, `None`
  - Col B (index 1): Investor / Org name
  - Col C (index 2): AREC Point Person → maps to Assigned To
  - Col K (index 10): Notes
- Skip rows where Col B is None or blank
- Skip summary/total rows (Col B = 'Total', 'Investors', etc.)
- Rows where Col A = `'x'` → mark as Declined signal (see 3.4)
- All other Priority values are ignored for CRM stage purposes

### 3.3 Org Name Matching
Matching runs in priority order:

**Step 1 — Alias lookup**
- Load `crm/org_aliases.json` (new file, see §4)
- If Tony's org name exactly matches a key in aliases → use the mapped CRM org name
- Case-insensitive match

**Step 2 — Exact match**
- If Tony's org name exactly matches an org in `organizations.md` → accept (confidence 1.0)

**Step 3 — Fuzzy match**
- Use `difflib.SequenceMatcher` ratio against all org names in `organizations.md`
- Also check against alias keys for partial coverage
- Confidence thresholds:
  - ≥ 0.85 → auto-accept, log match with confidence score
  - 0.60–0.84 → flag as "low confidence" in email, include in review queue, do NOT auto-write
  - < 0.60 → flag as "no match found", treat as potential new org

**Step 4 — No match → new org**
- If no match found at ≥ 0.60 → treat as new prospect (see 3.5)

**Parenthetical stripping:** Before matching, strip parenthetical contact names from Tony's org names.
- `"UTIMCO (Matt Saverin)"` → match against `"UTIMCO"`
- `"Khazanah Americas (Malaysia) Cash Ryan Mulligan"` → `"Khazanah Americas"`
- Strip pattern: remove `(...)` substrings, trim whitespace

### 3.4 Change Detection
Compare Tony's parsed data against current CRM state for matching orgs:

**Change type A — Assigned To changed:**
- Tony's Point Person ≠ current CRM Assigned To
- Note: Tony uses names like "Avila", "Reisner/Flynn", "Avila/Vasquez" — map to full names via `config.md` team roster
- Name normalization map (derive from config.md):
  - `Avila` → `Tony Avila`
  - `Vasquez` → `Oscar Vasquez`
  - `Reisner` → `Zach Reisner`
  - `Flynn` → `Truman Flynn`
  - `Albuquerque` → `Anthony Albuquerque`
  - `Fichtner` → `Patrick Fichtner`
  - `Van Gorder` / `KVG` → `Kevin Van Gorder`
  - `Morgan` → `Ian Morgan`
  - `Angeloni` → `Max Angeloni`
  - For slash-separated values (e.g., `Avila/Vasquez`): use the first name as primary Assigned To
- Flag as change only if normalized value differs from CRM

**Change type B — Notes changed:**
- Tony's Notes ≠ current CRM Notes for this prospect/offering combination
- If CRM Notes is empty and Tony has notes → flag as change
- If both have notes and they differ → flag as change (Tony's notes replace CRM notes)
- If Tony's notes are empty → no change (do not clear CRM notes)

**Change type C — Declined/Closed signal:**
- Tony's Col A = `'x'` AND current CRM stage ≠ `Declined` → set stage to `Declined`
- Tony's Col A = `'Closed'` AND current CRM stage ≠ `Closed` AND current CRM stage ≠ `Declined` → set stage to `Closed`

### 3.5 New Org Handling
An org is "new" if no match is found at ≥ 0.60 confidence.

Proposed CRM record:
- **Org name:** Tony's name (stripped of parentheticals), added to `organizations.md` if not present
- **Offering:** AREC Debt Fund II (hardcoded for this sync — Tony's sheet is Fund II only)
- **Stage:** `5. Interested`
- **Urgency:** `High`
- **Assigned To:** normalized from Tony's Point Person
- **Notes:** Tony's Notes (if present)
- **Target:** blank (not sourced from Tony's sheet)
- **Last Touch:** today's date

### 3.6 Conflict Rules (CRM wins)
These CRM fields are **never overwritten** by Tony's sync:
- Stage (except `x` → Declined)
- Urgency
- Target
- Committed
- Closing
- Primary Contact
- Last Touch (CRM auto-capture handles this)

### 3.7 Declined and Closed Stages
- `Declined` and `Closed` already exist as stages in `crm/config.md` — do NOT add new stages
- Tony's Priority = `x` → set stage to `Declined`
- Tony's Priority = `Closed` → set stage to `Closed` (if CRM stage is not already `Closed` or `Declined`)
- Do not delete the prospect record; just update the stage
- CRM wins on all other stage values — only `x` and `Closed` from Tony's Priority column trigger stage changes

---

## 4. Data Model / Schema Changes

### New file: `crm/org_aliases.json`
```json
{
  "UTIMCO": "University of Texas Investment Management Company",
  "UTIMCO (Matt Saverin)": "University of Texas Investment Management Company",
  "Merseyside": "Merseyside Pension Fund",
  "JPMorgan Asset Mgmt": "JPMorgan Asset Management",
  "Mass Mutual": "MassMutual",
  "FutureFund": "Future Fund",
  "Teachers Retirement System (TRS)": "Teachers Retirement System of Texas",
  "NPS (Korea SWF)": "National Pension Service of Korea"
}
```
- This file is **manually editable** — the team adds aliases as new naming discrepancies emerge
- The sync script reads this file on every run; it never writes to it
- Aliases are case-insensitive on the key side

### New file: `crm/tony_sync_state.json`
```json
{
  "last_processed_filename": "AREC Debt Fund II Marketing A List - MASTER as of March 13.xlsx",
  "last_processed_at": "2026-03-13T06:00:00",
  "egnyte_modified": "2026-03-13T14:40:00",
  "rows_processed": 180,
  "changes_detected": 3,
  "changes_applied": 3
}
```

### Modified file: `crm/config.md`
- Add `0. Declined` to the pipeline stages section (insert at top of stages list)

### New script: `app/sources/tony_sync.py`
Primary sync module. See §6.

### Modified file: `app/main.py`
- Add call to `tony_sync.run_sync()` in the update orchestrator sequence

---

## 5. UI / Interface

This feature has **no Overwatch dashboard UI**. All interaction happens via email.

### 5.1 Trigger Email (sent before any writes)
**To:** `ovasquez@avilacapllc.com`, `pkinsey@avilacapllc.com`  
**From:** CRM system (use existing email sender config)  
**Subject:** `Tony updated his CRM file — [N] changes detected`

**Email body structure:**

```
Tony uploaded a new version of his Marketing A List on [date].
File: AREC Debt Fund II Marketing A List - MASTER as of March 13.xlsx

── NEW PROSPECTS ([N]) ──────────────────────────────

  Org: Samsung Fire & Marine Insurance
  Assigned To: Tony Avila
  Stage: 5. Interested  |  Urgency: High
  Notes: Meeting needs to be rescheduled

  Org: Hanwha
  Assigned To: Tony Avila
  Stage: 5. Interested  |  Urgency: High
  Notes: Tony to meet Su Man on March 17

── UPDATED PROSPECTS ([N]) ──────────────────────────

  Org: Merseyside Pension Fund  [HIGH CONFIDENCE 0.97]
  Change: Notes updated
    Was:  Call Feb 3 to get update
    Now:  Need to schedule Q2 follow-up call

  Org: Mass Mutual  [HIGH CONFIDENCE 0.92]
  Change: Assigned To changed
    Was:  Truman Flynn
    Now:  Zach Reisner / Truman Flynn

── DECLINED ([N]) ────────────────────────────────────

  Org: Nomura
  Action: Stage will be set to 0. Declined

── LOW CONFIDENCE MATCHES — REVIEW REQUIRED ([N]) ──

  Tony's name: "ORG Ed Schwartz via Ira Lubert"
  Best match:  "State of Arizona"  (confidence 0.61)
  Action: NO CHANGE APPLIED — please update crm/org_aliases.json manually

── UNMATCHED — NOT IN CRM ([N]) ─────────────────────

  "Repole Family (Body Armor)"  — will be added as new prospect
  "Agnes - Max Angeloni connection"  — will be added as new prospect

──────────────────────────────────────────────────────
Changes above HIGH CONFIDENCE threshold have been applied to the CRM.
Low-confidence matches have NOT been applied. Update crm/org_aliases.json to resolve.

To undo applied changes: crm/tony_sync_state.json records what was changed.
```

### 5.2 No-change Run
If no new file is detected → no email sent, silent exit. Log to `~/Library/Logs/arec_tony_sync.log`.

### 5.3 Error States
- Egnyte API error → log error, send error email to Oscar only: `Subject: Tony CRM Sync Failed — [error summary]`
- Excel parse error → same
- Email send failure → log only (do not retry in same run)

---

## 6. Integration Points

### Reads from:
- Egnyte API: folder listing + file download from `Shared/AREC/Investor Relations/General Fundraising/`
- `crm/org_aliases.json` — alias mapping
- `crm/tony_sync_state.json` — last processed file state
- `crm/prospects.md` — current prospect records (via `crm_reader.py`)
- `crm/organizations.md` — org name list for fuzzy matching
- `crm/config.md` — pipeline stages, team roster for name normalization

### Writes to:
- `crm/prospects.md` — apply approved changes
- `crm/organizations.md` — add new orgs
- `crm/tony_sync_state.json` — update after successful run

### Calls:
- `crm_reader.py` — `get_all_prospects()`, `get_all_orgs()` for current state
- `crm_reader.py` — write-back functions for updating prospect fields
- Egnyte REST API (not MCP) — `GET /pubapi/v1/fs/Shared/AREC/...` for folder listing, file download
- SMTP / existing email sender — send notification email
- `app/main.py` — called from 6 AM launchd job

### Egnyte API calls:
```
List folder:
GET https://avilacapitalllc.egnyte.com/pubapi/v1/fs/Shared/AREC/Investor%20Relations/General%20Fundraising
Headers: Authorization: Bearer {EGNYTE_API_TOKEN}

Download file:
GET https://avilacapitalllc.egnyte.com/pubapi/v1/fs-content/Shared/AREC/.../{filename}
Headers: Authorization: Bearer {EGNYTE_API_TOKEN}
```
- `EGNYTE_API_TOKEN` stored in `app/.env` alongside `ANTHROPIC_API_KEY`

---

## 7. Constraints

- **No new Python libraries** without explicit approval. Use only: `openpyxl` (already available or add if not), `difflib` (stdlib), `fnmatch` (stdlib), `smtplib` (stdlib), `requests` (already used for Graph API)
- Confirm `openpyxl` is in `requirements.txt`; add if missing
- **`crm_reader.py` is the only place CRM markdown is parsed.** `tony_sync.py` must use `crm_reader.py` functions for all reads and writes — do not implement a second parser
- Apply changes immediately after detecting them (no approve/reject link in email — the email is informational; changes at high confidence are auto-applied)
- Low-confidence matches (0.60–0.84) are **never auto-applied** — email flags them for manual resolution
- `tony_sync_state.json` must be updated atomically (write to temp file, rename) to avoid corruption if process is interrupted
- Log all runs (success, no-change, error) to `~/Library/Logs/arec_tony_sync.log` with timestamp
- The sync is additive-by-default: it updates existing records and creates new ones, but never deletes CRM records (even if a row disappears from Tony's sheet)
- `BASE_DIR` constant used for all file paths — never hardcode

---

## 8. Acceptance Criteria

1. ✅ A new file in the Egnyte folder (matching the filename pattern) is detected within one 6 AM poll cycle
2. ✅ If the most recently modified file matches `last_processed_filename` in `tony_sync_state.json`, no email is sent and no changes are applied
3. ✅ Orgs matching at ≥ 0.85 confidence are auto-matched; changes applied and reported in email
4. ✅ Orgs matching at 0.60–0.84 confidence appear in the email as "low confidence — not applied"
5. ✅ Orgs matching via `org_aliases.json` are treated as exact matches (confidence 1.0)
6. ✅ Tony's Priority = `x` triggers a Stage → `Declined` update; Priority = `Closed` triggers Stage → `Closed`; `Declined` and `Closed` stages already exist in config.md and are not re-created
8. ✅ Assigned To normalized correctly from Tony's shorthand (e.g., `Reisner/Flynn` → `Zach Reisner`)
9. ✅ Notes sync: Tony's notes overwrite CRM notes only if Tony's notes are non-empty
10. ✅ CRM fields Stage, Urgency, Target, Committed are never overwritten (except Declined signal)
11. ✅ Email sent to `ovasquez@avilacapllc.com` and `pkinsey@avilacapllc.com` with correct diff summary
12. ✅ No email sent on no-change runs
13. ✅ `tony_sync_state.json` updated after each successful run
14. ✅ `0. Declined` stage added to `crm/config.md`
15. ✅ `crm/org_aliases.json` created with seed aliases from known Tony naming patterns
16. ✅ All runs logged to `~/Library/Logs/arec_tony_sync.log`
17. ✅ Feedback loop prompt has been run

---

## 9. Files Likely Touched

| File | Change |
|------|--------|
| `app/sources/tony_sync.py` | **New** — core sync module |
| `crm/org_aliases.json` | **New** — alias mapping, seeded with known variants |
| `crm/tony_sync_state.json` | **New** — created on first run |
| `app/main.py` | **Modified** — add `tony_sync.run_sync()` to 6 AM job |
| `crm/config.md` | **No change** — `Declined` and `Closed` stages already exist |
| `requirements.txt` | **Modified** — confirm/add `openpyxl` |
| `app/.env` | **Modified** — add `EGNYTE_API_TOKEN` |
| `app/sources/crm_reader.py` | **Possibly modified** — may need new write-back functions for Assigned To, Notes, Stage if not already present |

---

## Kickoff Prompt for Claude Code

```
Read CLAUDE.md, then read docs/specs/SPEC_tony-excel-sync.md.
Do not read other files yet. Confirm you understand the objective
and acceptance criteria, then tell me which files you plan to touch
before writing any code.
```
