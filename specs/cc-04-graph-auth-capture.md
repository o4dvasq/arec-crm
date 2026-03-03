# CC-04: Graph Auth + Auto-Capture Engine (Phase 5)

**Target:** `~/Dropbox/Tech/ClaudeProductivity/app/auth/graph_auth.py` + `~/Dropbox/Tech/ClaudeProductivity/app/sources/crm_graph_sync.py` + `~/Dropbox/Tech/ClaudeProductivity/app/sources/ms_graph.py`
**Depends on:** CC-01 (crm_reader.py)
**Blocks:** CC-05 (morning briefing), CC-06 (Slack)

---

## Purpose

Three modules:
1. **graph_auth.py** — MSAL authentication for Microsoft Graph API
2. **ms_graph.py** — Graph API data fetching (calendar, email, Teams)
3. **crm_graph_sync.py** — Scans last 24h of email + calendar, matches to CRM orgs, logs interactions

## Environment Variables (from .env)

```
AZURE_CLIENT_ID=d58c6152-...
AZURE_TENANT_ID=ebd42ab2-...
MS_USER_ID=<user object ID>
```

## Module 1: auth/graph_auth.py

```python
from msal import PublicClientApplication

SCOPES = [
    "https://graph.microsoft.com/Mail.Read",
    "https://graph.microsoft.com/Calendars.Read",
    "https://graph.microsoft.com/Chat.Read",
    "https://graph.microsoft.com/User.Read"
]

TOKEN_CACHE_PATH = os.path.expanduser("~/.arec_briefing_token_cache.json")
```

**Auth flow:** Device code flow (headless-friendly).
1. Check token cache for valid token
2. If expired, try silent refresh
3. If no token, initiate device code flow (print URL + code to terminal)
4. Cache token to `TOKEN_CACHE_PATH`

**Public API:**
```python
get_access_token() → str  # Returns valid Bearer token
```

## Module 2: sources/ms_graph.py

Fetches data from Microsoft Graph API using the auth token.

```python
# Calendar
get_today_events(token: str) → list[dict]
# Returns: [{subject, start, end, location, attendees: [{email, name}], ...}]

get_events_range(token: str, start: str, end: str) → list[dict]

# Email
get_recent_emails(token: str, hours: int = 18) → list[dict]
# Returns: [{subject, from_email, from_name, received, preview, importance, ...}]

# Teams (chat messages)
get_recent_chats(token: str, hours: int = 24) → list[dict]
# Returns: [{chat_id, sender, content_preview, created, ...}]
```

**Pagination:** Handle `@odata.nextLink` for large result sets.
**Error handling:** Retry on 429 (rate limit) with exponential backoff. Log and skip on 401/403.

## Module 3: sources/crm_graph_sync.py

The auto-capture engine. Scans last 24 hours of Graph data and matches against CRM orgs.

### Matching Logic

For each email sender/recipient and calendar attendee:

1. **Email exact match:** Compare sender/attendee email against all contacts in `contacts_index.md` → `memory/people/<slug>.md` (check email field). If match → resolve to org.

2. **Fallback — org name fuzzy match:** Take display name from Graph, compare against all org names in `organizations.md`. Match criteria: substring overlap ≥ 6 characters, single unambiguous match only. If multiple orgs match, skip (→ unmatched).

### On Match

For each matched interaction:

1. **Dedup check:** Skip if identical `org + date + type` already exists in `interactions.md`
2. **Append interaction** to `interactions.md` via `crm_reader.append_interaction()`:
   ```python
   {
       "org": "Merseyside Pension Fund",
       "type": "Email",  # or "Meeting"
       "offering": "AREC Debt Fund II",  # from prospect lookup
       "contact": "Susannah Friar",
       "subject": "RE: Encore Fund III",
       "summary": "Auto-captured: Susannah Friar → RE: Encore Fund III",
       "source": "auto-graph"
   }
   ```
3. **Update last_touch** on matched prospect (handled by `append_interaction`)
4. **If High urgency + Meeting type:** Add to `pending_interviews.json` via `crm_reader.add_pending_interview()`

### On No Match

Add to `unmatched_review.json` via `crm_reader.add_unmatched()`:
```python
{
    "source": "email",
    "date": "2026-03-02",
    "participant_email": "susannahfriar@wirral.gov.uk",
    "participant_name": "Friar, Susannah L.",
    "subject": "RE: [EXTERNAL]Encore Fund III",
    "reason": "No email match; org name not found in display name"
}
```

Merge across days. Dedupe by email. Purge items > 14 days old.

### Exclusion List

Skip internal AREC emails (`@avilacapllc.com`, `@avilacapital.com`, `@builderadvisorgroup.com`). These are team members, not investor interactions.

### Public API

```python
run_auto_capture(token: str) → dict
# Returns: {"matched": 5, "unmatched": 2, "skipped_dedup": 3, "pending_interviews_added": 1}
```

### Trigger Points

1. Called from `main.py` after morning briefing generation (5 AM)
2. Called from Flask API: `POST /crm/api/auto-capture` (add this route in CC-02)

## Flask Route Addition (for CC-02)

```python
@crm_bp.route('/api/auto-capture', methods=['POST'])
def trigger_auto_capture():
    token = get_access_token()
    result = run_auto_capture(token)
    return jsonify(result)
```

## Testing

1. Mock Graph API responses for unit tests
2. Integration test: run against live Graph with real token, verify interactions.md gets new entries
3. Test dedup: run twice with same data → no duplicate interactions
4. Test unmatched flow: use an email from unknown sender → verify appears in unmatched_review.json
5. Test pending interview: create a meeting with a High urgency org → verify pending_interviews.json entry

## Acceptance Criteria

- `python -c "from auth.graph_auth import get_access_token; print(get_access_token()[:20])"` returns a token
- `python -c "from sources.ms_graph import get_today_events; ..."` returns today's calendar
- `run_auto_capture()` processes email + calendar and writes to interactions.md
- Matched interactions update last_touch on prospects
- High urgency meetings create pending_interviews.json entries
- Unmatched senders appear in unmatched_review.json
- No duplicate interactions on re-run
