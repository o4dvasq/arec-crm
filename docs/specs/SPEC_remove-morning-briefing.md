SPEC: Remove Morning Briefing — Fold Remaining Functionality into /update Workflow
Project: arec-crm
Date: 2026-03-12
Status: Ready for implementation

---

## 1. Objective

Remove the standalone morning briefing pipeline (`main.py`, launchd cron job, Claude API briefing generation) and fold its remaining useful functionality into the `/update` Cowork workflow. The morning briefing was a Python script that ran at 5 AM via launchd, authenticated with Microsoft Graph via MSAL, fetched calendar/email data, generated a written briefing via Claude API, wrote `dashboard_calendar.json`, and ran auto-capture. All of this is now handled interactively by the `/update` workflow using MCP tools (Outlook, Notion) — except for three gaps this spec closes.

## 2. Scope

### In scope

- Delete `app/main.py` (the morning briefing orchestrator)
- Delete `app/briefing/generator.py` (Claude API briefing generator)
- Delete `app/briefing/prompt_builder.py` (prompt assembly for briefing)
- Delete `app/sources/crm_graph_sync.py` (auto-capture engine)
- Remove the dashboard's `/api/calendar/refresh` Graph API dependency — replace with a simple file-read endpoint
- Remove the dashboard's `/api/auto-capture` endpoint (no longer needed)
- Update `update.md` (the /update skill definition) to add investor intelligence matching
- Update `update.md` to add calendar-based interaction capture to `email_log.json`
- Ensure `dashboard_calendar.json` includes `end_time` field for past-meeting styling
- Update `CLAUDE.md` run commands and references
- Update `docs/PROJECT_STATE.md` to remove briefing references
- Remove or update `briefing_latest.md` references

### Out of scope

- `app/briefing/brief_synthesizer.py` — stays (used by CRM blueprint for relationship briefs)
- `app/auth/graph_auth.py` — stays (used by CRM blueprint for email deep search, device flow auth)
- `app/sources/ms_graph.py` — stays (used by `drain_inbox.py` and CRM blueprint email search)
- `app/sources/memory_reader.py` — stays (used by dashboard task loading)
- `app/drain_inbox.py` — stays (independent shared-mailbox drainer)
- The launchd plist file itself — Oscar will unload it manually; it's not in the repo
- Test files for `brief_synthesizer.py` — stays
- Test files for `crm_graph_sync.py` (`test_email_matching.py`) — remove, since the module is deleted

## 3. Business Rules

- The `/update` workflow is now the **sole entry point** for all daily productivity operations. There is no background cron job.
- `dashboard_calendar.json` is written every time `/update` runs (Step 0, already documented in `update.md`). The dashboard refresh button should read this file, not call Graph API.
- Calendar-based interaction capture now writes to `crm/email_log.json` (not `crm/interactions.md`). This consolidates all auto-captured interactions into one store.
- The written briefing file (`briefing_latest.md`) is no longer generated. The interactive `/update` output replaces it.
- Investor intelligence (matching today's calendar events to high-urgency CRM prospects) is surfaced interactively during `/update`, not written to a file.

## 4. Data Model / Schema Changes

### `crm/email_log.json` — add calendar-based entries

Calendar interaction entries use the same schema as email entries but with `matchType: "calendar"`:

```json
{
  "messageId": "cal-2026-03-12-meritz-arec-mountain-house",
  "date": "2026-03-12",
  "timestamp": "2026-03-12T17:00:00-07:00",
  "subject": "Meritz / AREC - Mountain House",
  "from": "jin-ho.lee@meritz.co.kr",
  "fromName": "Jin-ho Lee",
  "to": ["oscar@avilacapllc.com", "tony@avilacapllc.com"],
  "orgMatch": "Meritz Securities (Korea)",
  "matchType": "calendar",
  "confidence": 0.95,
  "summary": "Meeting with Jinho Lee (Meritz) re Mountain House co-investment"
}
```

The `messageId` for calendar entries uses format `cal-{date}-{title-slug}` for dedup.

### `dashboard_calendar.json` — ensure `end_time` field

Each event object MUST include an `end_time` field (ISO 8601 with timezone) so the dashboard can style past meetings. This field already exists in the format spec but wasn't reliably written by the old code. Example:

```json
{
  "time": "9:00 AM – 9:30 AM",
  "title": "Standup",
  "attendees": "Tony Avila",
  "location": "Microsoft Teams",
  "end_time": "2026-03-12T09:30:00-07:00",
  "day": "today"
}
```

### Files deleted (no longer generated)

- `briefing_latest.md` — delete the file if it exists; remove all references

## 5. UI / Interface

### Dashboard `/api/calendar/refresh` endpoint — simplified

**Current behavior:** Calls Microsoft Graph API via MSAL token to fetch calendar events. Fails when token is expired (which is always, since the morning briefing no longer refreshes it).

**New behavior:** Simply re-reads `dashboard_calendar.json` from disk and returns its contents. No Graph API call. No authentication check. The file is written by the `/update` workflow.

```python
@app.route('/api/calendar/refresh', methods=['POST'])
def api_calendar_refresh():
    """Re-read dashboard_calendar.json from disk."""
    if not os.path.exists(CALENDAR_PATH):
        return jsonify({'ok': True, 'events': [], 'count': 0})
    try:
        with open(CALENDAR_PATH, encoding='utf-8') as f:
            events = json.load(f)
        return jsonify({'ok': True, 'events': events, 'count': len(events)})
    except (json.JSONDecodeError, IOError) as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
```

The `_load_calendar()` function's staleness check (comparing file mtime to today) remains unchanged — it still shows the "Calendar data is from Mar 10" warning when the file is old, prompting the user to run `/update`.

### Dashboard `/api/auto-capture` endpoint — remove

Remove the `/api/auto-capture` route from `crm_blueprint.py` (lines 1313-1330). If any frontend JS calls this endpoint, remove those calls too. Auto-capture is now handled by the `/update` workflow's email-scan and the new calendar capture step.

## 6. Integration Points

### `/update` workflow — new Step 0b.5: Calendar Interaction Capture

After writing `dashboard_calendar.json` (Step 0b) and before task sync (Step 1), add a step that captures calendar-based interactions to `email_log.json`.

Add this section to `update.md` after Step 0b:

---

**Step 0c. Capture Calendar Interactions**

For each event fetched in Step 0a, check if any external (non-AREC) attendees match a CRM organization:

1. Extract all attendee email addresses from the event
2. Skip internal AREC domains: `avilacapllc.com`, `avilacapital.com`, `encorefunds.com`, `builderadvisorgroup.com`, `south40capital.com`, `angeloniandco.com`
3. For each external attendee email, extract the domain and check against the org domain map from `crm/organizations.md`
4. If domain matches an org, create a calendar log entry in `crm/email_log.json`
5. Dedup by `messageId` (format: `cal-{date}-{title-slug}`) — skip if already in log
6. Skip calendar responses (subjects starting with "Accepted:", "Declined:", "Tentative:", "Canceled:")

This captures meeting interactions the same way email-scan captures email interactions — both write to `email_log.json`.

---

### `/update` workflow — new Step 0d: Investor Intelligence Check

After calendar capture, cross-reference today's calendar against high-urgency CRM prospects to surface pre-meeting intelligence. This replaces the morning briefing's investor intel section.

Add this section to `update.md`:

---

**Step 0d. Investor Intelligence Check**

Cross-reference today's calendar events against CRM prospects with `Urgent: Yes` or `Urgent: High` status at Stages 4-8 (Engaged through Closed):

1. Load all prospects from `crm/prospects.md` where Urgent field is populated
2. For each today's calendar event, check if any attendee email domain matches a prospect org's domain, OR if the prospect org name (≥6 chars) appears in the event subject
3. For each match, surface a pre-meeting intel block in the update output:

```
## Pre-Meeting Intelligence

### [Org Name] — [Time] [Meeting Title]
Stage: [X] | Target: [Y] | Assigned: [Z]
Last touch: [date] | [N] interactions logged

[2-3 sentence context from the prospect record — what's the current status,
what was discussed last time, what should be the goal of today's meeting]
```

4. Load the last 3 entries from `crm/email_log.json` for that org to provide recent interaction context
5. If the org has a file in `memory/people/`, include a 1-sentence excerpt of the most relevant intel

This step only produces output when there are matches. If no calendar events match high-urgency prospects, skip silently.

---

### Renumber existing steps

After adding Steps 0c and 0d, the existing steps shift:
- Current Step 0c (Report) becomes Step 0e
- Steps 1-9 remain unchanged

## 7. Constraints

- Do NOT delete `app/auth/graph_auth.py` — it's used by `crm_blueprint.py` for email deep search and device flow auth for the dashboard
- Do NOT delete `app/sources/ms_graph.py` — it's used by `drain_inbox.py` and `crm_blueprint.py` for email deep search
- Do NOT delete `app/briefing/brief_synthesizer.py` — it's used by `crm_blueprint.py` for relationship brief synthesis
- Do NOT delete `app/briefing/__init__.py` — needed for the package to remain importable
- Do NOT modify the email-scan skill (`skills/email-scan/`) — it already handles email capture correctly
- The `test_email_matching.py` tests import from `crm_graph_sync.py`. Since that module is being deleted, either delete the test file or migrate the still-useful test cases (like `_fuzzy_match_org` and `_is_internal` tests) to a new home if those utility functions are preserved elsewhere
- `interactions.md` continues to exist and be readable by the dashboard — but nothing new writes to it. It becomes a read-only historical artifact.

## 8. Acceptance Criteria

1. `python3 app/main.py` no longer exists — running it produces a file-not-found error
2. `app/briefing/generator.py` and `app/briefing/prompt_builder.py` are deleted
3. `app/sources/crm_graph_sync.py` is deleted
4. `app/tests/test_email_matching.py` is deleted (or migrated if utility functions are preserved)
5. The dashboard's `/api/calendar/refresh` endpoint returns the contents of `dashboard_calendar.json` without calling Microsoft Graph API — verify by checking the endpoint code has no `graph_auth` or `ms_graph` imports
6. The dashboard's `/api/auto-capture` endpoint is removed from `crm_blueprint.py`
7. `update.md` contains new Steps 0c (Calendar Interaction Capture) and 0d (Investor Intelligence Check) with the content specified in Section 6
8. `dashboard_calendar.json` format includes `end_time` field — verify by checking Step 0b in `update.md` specifies this field
9. `CLAUDE.md` run commands section no longer references `python3 app/main.py` or morning briefing
10. `docs/PROJECT_STATE.md` no longer references morning briefing, launchd, or 5 AM cron
11. `briefing_latest.md` is deleted if it exists in the repo
12. `python3 -m pytest app/tests/` passes — existing tests for `brief_synthesizer.py` and `crm_reader.py` still pass
13. No remaining Python imports reference `crm_graph_sync` — verify with: `grep -r "crm_graph_sync" app/`
14. No remaining Python imports reference `briefing.generator` or `briefing.prompt_builder` — verify with: `grep -r "briefing.generator\|briefing.prompt_builder" app/`
15. Feedback loop prompt has been run

## 9. Files Likely Touched

| File | Action | Reason |
|------|--------|--------|
| `app/main.py` | DELETE | Morning briefing orchestrator — fully replaced by /update |
| `app/briefing/generator.py` | DELETE | Claude API briefing generation — no longer needed |
| `app/briefing/prompt_builder.py` | DELETE | Prompt assembly for briefing — investor intel logic moves to update.md |
| `app/sources/crm_graph_sync.py` | DELETE | Auto-capture engine — email capture replaced by email-scan skill, calendar capture moves to update.md |
| `app/tests/test_email_matching.py` | DELETE | Tests import from deleted crm_graph_sync module |
| `app/delivery/dashboard.py` | EDIT | Simplify `/api/calendar/refresh` to file-read only (lines 299-420) |
| `app/delivery/crm_blueprint.py` | EDIT | Remove `/api/auto-capture` route (lines 1313-1330) |
| `update.md` | EDIT | Add Steps 0c (calendar interaction capture) and 0d (investor intelligence check) |
| `CLAUDE.md` | EDIT | Remove `python3 app/main.py` from run commands, remove morning briefing references |
| `docs/PROJECT_STATE.md` | EDIT | Remove morning briefing, launchd, and cron references |
| `briefing_latest.md` | DELETE | Output artifact of deleted morning briefing |
| `app/auth/graph_auth.py` | EDIT | Remove the error message referencing `main.py` on line 93 — update to say "re-authenticate via the dashboard" |
| `docs/ARCHITECTURE.md` | EDIT | Remove morning briefing from architecture diagram / component list |
| `docs/AUDIT.md` | EDIT | Remove morning briefing references, update system flow |
| `docs/DECISIONS.md` | EDIT | Add decision entry: "Morning briefing removed — functionality folded into /update workflow (2026-03-12)" |

Note: Archived specs in `docs/specs/local-crm/archive/` (e.g., `cc-05-morning-briefing.md`) are historical and should NOT be modified or deleted.
