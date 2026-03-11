# CRM Phase 5 — Graph Auto-Capture Spec
**For Claude Code**
**Author:** Oscar Vasquez, COO — Avila Real Estate Capital
**Date:** March 2026
**Status:** Ready for Execution
**Depends on:** Phases 1–4 complete

---

## Overview

Scan Microsoft Graph (email + calendar) for interactions with known investor
contacts, automatically log them to `interactions.md`, and update `last_touch`
on matched prospect records. Unknown senders/attendees surface in a "Review"
panel on the pipeline page for manual triage. Runs automatically at 5am with
the morning briefing and can be triggered manually via a button on the pipeline
page.

---

## Environment

- App root: `~/arec-morning-briefing/`
- Existing Graph client: `sources/ms_graph.py` — use as-is, do not modify
- Existing auth: `auth/graph_auth.py` — use as-is, do not modify
- CRM parser: `sources/crm_reader.py` (Phase 1)
- New module: `sources/crm_graph_sync.py`
- Do not break any existing dashboard, briefing, or Phase 2–4 functionality

---

## Step 1 — Build `sources/crm_graph_sync.py`

Create `~/arec-morning-briefing/sources/crm_graph_sync.py`.

This module is the entire auto-capture engine. It has no Flask dependency —
it can be called from `main.py` (scheduled) or from a Flask route (manual trigger).

---

### 1.1 Contact Index

Build a lookup index from all contacts in `contacts.md` at scan time.
The index maps known identifiers → `{org, contact_name, offerings}`.

```python
def build_contact_index() -> dict:
    """
    Returns a lookup structure with two sub-indexes:

    {
      'by_email': {
        'susannah@merseyside.gov.uk': {
          'org': 'Merseyside Pension Fund',
          'contact_name': 'Susannah Friar',
          'offerings': ['AREC Debt Fund II']
        },
        ...
      },
      'by_org_name': {
        'merseyside pension fund': {   # lowercased for matching
          'org': 'Merseyside Pension Fund',
          'offerings': ['AREC Debt Fund II']
        },
        ...
      }
    }

    by_email: built from contacts where email field is non-empty.
    by_org_name: built from all organizations that have at least one
                 active prospect (stage not in terminal/closed stages).
    offerings: list of offering names this org has a prospect in.
    """
```

---

### 1.2 Matching Logic

```python
def match_participant(email: str, display_name: str,
                      index: dict) -> dict | None:
    """
    Try to match a Graph participant (email + display name) to a CRM record.

    Step 1 — Email exact match:
      Look up email (lowercased) in index['by_email'].
      If found → return match.

    Step 2 — Org name fuzzy match on display name:
      If no email match, try to match display_name against known org names.
      Method: for each org in index['by_org_name'], check if the org name
      (lowercased) appears as a substring of display_name (lowercased),
      OR if display_name (lowercased) appears as a substring of org name
      (lowercased), AND the overlap is at least 6 characters.
      If exactly one org matches → return match.
      If multiple orgs match → return None (ambiguous, treat as unmatched).
      If no org matches → return None.

    Returns:
      {
        'org': str,
        'contact_name': str | None,   # None if matched at org level only
        'offerings': [str],
        'match_method': 'email' | 'fuzzy_org'
      }
      or None if no match.
    """
```

---

### 1.3 Deduplication

```python
def is_duplicate(org: str, date: str, interaction_type: str) -> bool:
    """
    Check interactions.md for an existing entry matching:
      org == org (exact)
      date == date (YYYY-MM-DD)
      type == interaction_type (exact)
    Returns True if a duplicate exists, False otherwise.
    Calls load_interactions(org=org) and checks in memory.
    """
```

---

### 1.4 Main Scan Function

```python
def scan_and_capture(days_back: int = 1) -> dict:
    """
    Main entry point. Scans Graph and logs new investor interactions.

    Args:
      days_back: how many days back to scan (default 1 for daily run)

    Returns summary dict:
    {
      'emails_scanned': int,
      'meetings_scanned': int,
      'interactions_logged': int,
      'prospects_touched': int,        # unique prospects where last_touch updated
      'duplicates_skipped': int,
      'unmatched': [                   # list for review panel
        {
          'source': 'email' | 'calendar',
          'date': 'YYYY-MM-DD',
          'participant_email': str,
          'participant_name': str,
          'subject': str,              # email subject or meeting title
          'reason': str                # why it didn't match
        }
      ]
    }

    Algorithm:
    1. Build contact index (build_contact_index())
    2. Fetch emails: get_recent_emails() from ms_graph.py
       Filter to emails received or sent within the last `days_back` days
    3. Fetch calendar: get_todays_events() from ms_graph.py
       For multi-day scans, call with appropriate date range
       Skip events where Oscar is the only attendee (internal/personal)
    4. For each email:
       a. Collect participants: sender + all recipients (to, cc)
       b. Skip participants with Oscar's own email address
       c. For each external participant: call match_participant()
       d. Collect all matches → deduplicate by org
       e. For each matched org:
          - Check is_duplicate(org, email_date, 'Email')
          - If duplicate: increment duplicates_skipped, skip
          - Build interaction entry and call append_interaction()
          - Increment interactions_logged
       f. Unmatched external participants → append to unmatched list
    5. For each calendar event:
       a. Skip if attendee count == 1 (solo/personal event)
       b. Collect attendees, skip Oscar's own email
       c. For each external attendee: call match_participant()
       d. Deduplicate matches by org
       e. For each matched org:
          - Check is_duplicate(org, event_date, 'Meeting')
          - If duplicate: skip
          - Build interaction entry and call append_interaction()
       f. Unmatched external attendees → append to unmatched list
    6. Return summary dict
    """
```

---

### 1.5 Interaction Entry Format

When calling `append_interaction()` (from `crm_reader.py`), build the entry dict:

**For an email:**
```python
{
  'org': matched_org,
  'type': 'Email',
  'offering': offerings[0] if len(offerings) == 1 else '',
  # If org has prospects in multiple offerings, leave offering blank
  # (avoids guessing which offering the email relates to)
  'contact': contact_name or '',
  'subject': email['subject'][:120],  # truncate long subjects
  'summary': f"Auto-captured: {email['from']['name']} → {email['subject'][:80]}",
  'source': 'auto-graph'
}
```

**For a calendar event:**
```python
{
  'org': matched_org,
  'type': 'Meeting',
  'offering': offerings[0] if len(offerings) == 1 else '',
  'contact': contact_name or '',
  'subject': event['subject'][:120],
  'summary': f"Auto-captured meeting: {event['subject'][:80]}",
  'source': 'auto-graph'
}
```

Oscar's email address must be configurable. Read it from `config.yaml` under
a new key `graph.user_email`, or fall back to the `MS_USER_ID` environment
variable. Claude Code should check `config.yaml` first.

---

### 1.6 Unmatched Entry Deduplication

Before appending to the `unmatched` list, check:
- If the same `participant_email` already appears in the list, skip the duplicate
- An unmatched participant may appear in multiple emails — only surface them once

---

## Step 2 — Persist Unmatched for the Review Panel

The unmatched list must persist between runs so the review panel can display
it even after the scan completes. Write it to a JSON file after each scan:

**Path:** `~/Dropbox/Tech/ClaudeProductivity/crm/unmatched_review.json`

**Format:**
```json
{
  "last_scan": "2026-03-01T05:00:00",
  "items": [
    {
      "source": "email",
      "date": "2026-03-01",
      "participant_email": "unknown@example.com",
      "participant_name": "John Unknown",
      "subject": "RE: Fund II materials",
      "reason": "No email match; org name not found in display name"
    }
  ]
}
```

Write behavior:
- On each scan, **merge** new unmatched items with existing ones (by
  `participant_email` dedup key — don't accumulate the same unknown sender
  across multiple days)
- Keep items for a maximum of **14 days** — purge older entries on each write
- If the file doesn't exist, create it

Add a helper function:
```python
def save_unmatched(items: list) -> None
def load_unmatched() -> list   # returns items list, [] if file missing
```

---

## Step 3 — Integrate with `main.py`

**File to modify:** `main.py`

After the morning briefing is generated and sent, add:

```python
# Auto-capture investor interactions from Graph
try:
    from sources.crm_graph_sync import scan_and_capture
    capture_result = scan_and_capture(days_back=1)
    logging.info(
        f"CRM auto-capture: {capture_result['interactions_logged']} logged, "
        f"{capture_result['duplicates_skipped']} dupes skipped, "
        f"{len(capture_result['unmatched'])} unmatched"
    )
except Exception as e:
    logging.error(f"CRM auto-capture failed: {e}")
```

Wrap in try/except so a CRM failure never blocks the morning briefing.

---

## Step 4 — New API Routes

**File to modify:** `delivery/dashboard.py`

Add to the existing `crm_bp` Blueprint:

---

### `POST /crm/api/auto-capture`

Triggers `scan_and_capture(days_back=1)` synchronously.

**No request body needed.**

**Response:**
```json
{
  "ok": true,
  "emails_scanned": 12,
  "meetings_scanned": 3,
  "interactions_logged": 4,
  "prospects_touched": 4,
  "duplicates_skipped": 1,
  "unmatched_count": 2
}
```

On exception:
```json
{"ok": false, "error": "Graph auth token expired — run python3 auth/graph_auth.py --setup"}
```

This route may take 5–15 seconds (Graph API calls). The client must show a
loading state during the request (not a fire-and-forget).

---

### `GET /crm/api/unmatched`

Returns the current unmatched review list from `unmatched_review.json`.

**Response:**
```json
{
  "last_scan": "2026-03-01T05:00:00",
  "items": [
    {
      "source": "email",
      "date": "2026-03-01",
      "participant_email": "unknown@example.com",
      "participant_name": "John Unknown",
      "subject": "RE: Fund II materials",
      "reason": "No email match; org name not found in display name"
    }
  ]
}
```

Returns `{"last_scan": null, "items": []}` if file doesn't exist.

---

### `DELETE /crm/api/unmatched/<email>`

Dismiss a single unmatched item by `participant_email` (URL-encoded).
Removes it from `unmatched_review.json`.

**Response:** `{"ok": true}`

---

### `POST /crm/api/unmatched/resolve`

Resolve an unmatched item by linking it to a known org. This:
1. Removes the item from `unmatched_review.json`
2. Logs a manual interaction for the resolved org

**Request body:**
```json
{
  "participant_email": "unknown@example.com",
  "org": "Merseyside Pension Fund",
  "offering": "AREC Debt Fund II",
  "type": "Email",
  "subject": "RE: Fund II materials",
  "date": "2026-03-01"
}
```

Calls `append_interaction()` with `source: 'manual'` and the provided fields.
Returns `{"ok": true}`.

Optionally, if the user wants to also save the email address to the contact
record to improve future matching, they can do so via the existing
`PATCH /crm/api/contact/<org>/<n>` route separately (not bundled here).

---

## Step 5 — Review Panel on Pipeline Page

**Files to modify:** `templates/crm/pipeline.html`, `static/crm/crm.js`,
`static/crm/crm.css`

Add a collapsible "Unmatched Review" panel to the pipeline page, below the
filter bar and above the prospects table.

### Panel structure

```
┌─────────────────────────────────────────────────────────┐
│ ⚠ 2 Unmatched Interactions — Review ▾   [Run Capture]  │
├─────────────────────────────────────────────────────────┤
│ EMAIL  Mar 1  unknown@example.com (John Unknown)        │
│        "RE: Fund II materials"                          │
│        [Link to org ▼]  [Dismiss]                       │
│                                                         │
│ EMAIL  Feb 28  other@pension.org (Mary Jones)           │
│        "Quarterly update"                               │
│        [Link to org ▼]  [Dismiss]                       │
└─────────────────────────────────────────────────────────┘
```

- Panel is **collapsed by default** if there are 0 unmatched items
- Panel is **expanded by default** if there are 1+ unmatched items
- Header shows count badge; click to toggle expand/collapse
- "Run Capture" button triggers `POST /crm/api/auto-capture`

### "Run Capture" button behavior

1. Button shows spinner and "Running..." text during the request
2. On success: show a toast notification:
   `✓ 4 interactions logged, 2 unmatched` (3 seconds, then fade)
3. Reload the unmatched panel from `GET /crm/api/unmatched`
4. On error: show toast with the error message in red

### Per-item actions

**"Link to org" dropdown:**
- A `<select>` populated with all org names from `load_organizations()`
  (loaded when the page renders — pass as a JS variable)
- Selecting an org reveals a secondary row:
  ```
  Offering: [ ▼ ]   Type: [Email ▼]   [ Confirm ]  [ Cancel ]
  ```
- "Confirm" calls `POST /crm/api/unmatched/resolve` and removes the row
  from the panel on success

**"Dismiss" button:**
- Calls `DELETE /crm/api/unmatched/<email>`
- Removes the row from the panel on success (no page reload)

### Loading the panel

On pipeline page load, call `GET /crm/api/unmatched` in parallel with the
prospects fetch. Render the panel with the results. If the panel would show
0 items, render it collapsed and show the count as "0 Unmatched".

---

## Step 6 — `config.yaml` Addition

Add to the existing `config.yaml`:

```yaml
graph:
  user_email: "oscar@avilacapital.com"   # Oscar's email — used to exclude self from participant matching
```

Claude Code should use the actual email from Oscar's Microsoft account. If
unknown, use a placeholder and note it in a comment.

---

## Step 7 — Verify

```bash
cd ~/arec-morning-briefing
python3 delivery/dashboard.py
```

### Unit test (no Graph credentials needed)

```bash
python3 -c "
from sources.crm_graph_sync import build_contact_index, match_participant

index = build_contact_index()
print(f'Contacts with email: {len(index[\"by_email\"])}')
print(f'Orgs indexed: {len(index[\"by_org_name\"])}')

# Test fuzzy match
result = match_participant('', 'Merseyside Pension Fund Team', index)
print(f'Fuzzy match result: {result}')
"
```

### Manual checks

- [ ] `build_contact_index()` runs without error
- [ ] `match_participant()` returns a match for a known org name in display name
- [ ] `match_participant()` returns None for a clearly unrelated display name
- [ ] `is_duplicate()` correctly detects an existing interaction
- [ ] `POST /crm/api/auto-capture` returns 200 with summary JSON
  (even if Graph returns 0 emails — auth must succeed)
- [ ] After auto-capture, check `interactions.md` for new entries:
  `tail -40 ~/Dropbox/Tech/ClaudeProductivity/crm/interactions.md`
- [ ] After auto-capture, verify `last_touch` updated on matched prospects:
  `grep "Last Touch" ~/Dropbox/Tech/ClaudeProductivity/crm/prospects.md | head -10`
- [ ] `unmatched_review.json` created after first scan
- [ ] `GET /crm/api/unmatched` returns items from JSON file
- [ ] Unmatched panel appears on pipeline page with correct count
- [ ] "Run Capture" button shows spinner during request, toast on completion
- [ ] "Dismiss" removes an item from the panel
- [ ] "Link to org" → resolve logs an interaction and removes the item
- [ ] Running capture twice on same day: duplicate count increments,
  no duplicate entries in `interactions.md`
- [ ] `main.py` runs to completion with auto-capture integrated (check logs)
- [ ] No regressions on any prior phase

---

## What's NOT In This Phase

- No Notion meeting note integration (future)
- No email address auto-save to contact after resolve (manual via Phase 4 PATCH)
- No Teams message scanning (future)
- No interaction timeline on org detail page (deferred — add in a follow-on)
- No analytics (Phase 6)
- No dashboard cleanup (Phase 7)

---

## Files Modified / Created

```
sources/crm_graph_sync.py          ← NEW
main.py                            ← MODIFIED: auto-capture call after briefing
delivery/dashboard.py              ← MODIFIED: 4 new API routes
templates/crm/pipeline.html        ← MODIFIED: unmatched review panel
static/crm/crm.js                  ← MODIFIED: capture button + panel logic
static/crm/crm.css                 ← MODIFIED: panel + toast styles
config.yaml                        ← MODIFIED: add graph.user_email
~/Dropbox/.../crm/unmatched_review.json  ← CREATED at runtime by scan
```

---

*When Phase 5 is complete and all manual checks pass, return for the Phase 6
spec (analytics page — pipeline charts, staleness table, fund progress).*
