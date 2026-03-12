SPEC: Calendar Forward-Scan — Auto-Discovered Prospect Meetings
Project: arec-crm
Date: 2026-03-11
Status: Ready for implementation

> **⚠️ MIGRATION NOTE (March 12, 2026):** This spec was written before the Azure migration. The app now runs on PostgreSQL only — `crm_reader.py` is deleted. All references to `crm_reader.py` below should be read as `crm_db.py`. Do NOT create or import `crm_reader.py`. Do NOT implement "both markdown and PostgreSQL modes" — PostgreSQL only. Work on `azure-migration` branch.

---

## 1. Objective

Add a 30-day forward calendar scan to the daily Graph API polling cycle. When the poller finds a future calendar event whose attendees or subject match a known CRM organization, it writes that meeting to the existing `prospect_meetings` store so it appears in the Meetings section of the Prospect Detail page. This gives the team automatic visibility into upcoming org-related meetings without manual entry.

## 2. Scope

### In Scope

- Extend the Graph API poller to fetch calendar events 30 days into the future for all team members
- Match future events against known CRM organizations using the existing two-tier matching logic (domain match, then person/contact match, then org-name-in-subject)
- Write matched events into the existing `prospect_meetings` data store with a `source: "auto-graph"` field to distinguish from manual entries
- Deduplicate on append: skip events whose Graph `iCalUId` (or `id`) already exists in `prospect_meetings` for that prospect
- Display auto-discovered meetings in the Prospect Detail Meetings section with a visual indicator (e.g., "Auto" badge)
- Scan all team members' calendars (not just the assigned user) — any AREC team member with a meeting involving the org surfaces it on the prospect

### Out of Scope

- Modifying the existing manual meeting add/delete UI (those flows stay as-is)
- Scanning calendars of external contacts
- Meeting debrief or notes generation from auto-discovered meetings
- Real-time calendar webhooks (polling only)
- Overwatch calendar features (separate project)

## 3. Business Rules

- **Match scope is all team members**: If Tony has a meeting with StepStone, that meeting appears on every StepStone prospect regardless of who is `assigned_to`. The team needs full visibility into org touchpoints.
- **Dedup on append**: Each run checks whether an event's `graph_event_id` (the Graph API's `iCalUId`) already exists in `prospect_meetings` for the matched prospect. If it does, skip. If the event details have changed (time, attendees), update the existing entry in place.
- **Auto-discovered meetings are editable**: Users can delete auto-discovered meetings from the Prospect Detail page (same delete button as manual meetings). Deleted auto-discovered meetings should not reappear on the next scan — track deletions via a `dismissed_event_ids` list per prospect key.
- **Stale cleanup**: On each scan, remove auto-discovered meetings whose `meeting_date` is in the past and older than 7 days. This keeps the Meetings section forward-looking.
- **Org matching reuses existing logic**: The matching algorithm from `crm_graph_sync.py` (`_resolve_participant` domain match → `_fuzzy_match_org` name match) applies to calendar attendees. Additionally, check if the org name (≥6 chars) appears in the event subject, matching the `_matches_event` pattern from `prompt_builder.py`.
- **Multi-prospect resolution**: If an org has multiple prospects (e.g., Fund I and Fund II), write the meeting to all active prospects for that org. Active = stage not in `{8. Closed, 0. Not Pursuing, 0. Declined}`.
- **Internal-only meetings are excluded**: If all attendees are `@avilacapllc.com` (or other internal domains), skip the event. At least one external attendee must match a known org.
- **All-day events are excluded**: Skip events where `isAllDay` is true.
- **"Settler" filter applies**: Exclude events matching the existing Settler exclusion convention.

## 4. Data Model / Schema Changes

### Existing `prospect_meetings` Store

Currently stored in `crm/prospect_meetings.json` (local markdown mode) or the `prospect_meetings` table (PostgreSQL mode). The existing entry shape is:

```json
{
  "id": "2026-03-11T14:30:00Z",
  "meeting_date": "2026-03-20",
  "meeting_time": "10:00 AM",
  "attendees": "John Smith, Jane Doe",
  "purpose": "Fund II pitch meeting",
  "created_at": "2026-03-11T14:30:00Z"
}
```

### New Fields Added to Meeting Entries

```json
{
  "id": "2026-03-11T14:30:00Z",
  "meeting_date": "2026-03-20",
  "meeting_time": "10:00 AM - 11:00 AM",
  "attendees": "John Smith (StepStone), Jane Doe (StepStone)",
  "purpose": "Fund II Discussion — from Oscar's calendar",
  "created_at": "2026-03-11T14:30:00Z",
  "source": "auto-graph",
  "graph_event_id": "AAMkAGI2TG93AAA=",
  "scanned_from": "oscar@avilacapllc.com",
  "location": "Zoom"
}
```

New fields:

| Field | Type | Purpose |
|-------|------|---------|
| `source` | string | `"auto-graph"` for auto-discovered, `"manual"` (or absent) for user-created |
| `graph_event_id` | string | Graph API `iCalUId` for dedup. Null for manual entries. |
| `scanned_from` | string | Email of the team member whose calendar this came from |
| `location` | string | Meeting location from Graph event (room, Zoom link, etc.) |

### New: Dismissed Events Tracking

Add a `dismissed_graph_events` key at the top level of `prospect_meetings.json` (or a column on the DB table):

```json
{
  "StepStone::Fund II": [ ... meetings ... ],
  "__dismissed_graph_events": ["AAMkAGI2TG93AAA=", "AAMkBBB="]
}
```

For PostgreSQL mode, add a simple table:

```sql
CREATE TABLE dismissed_graph_events (
    id SERIAL PRIMARY KEY,
    prospect_key VARCHAR(255) NOT NULL,  -- "OrgName::Offering"
    graph_event_id VARCHAR(500) NOT NULL,
    dismissed_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (prospect_key, graph_event_id)
);
```

### No Changes to Existing Fields

Manual meeting entries continue to work exactly as before. The `source` field is optional — absence or `"manual"` means user-created.

## 5. UI / Interface

### Prospect Detail — Meetings Section

Currently shows manually added meetings with date, time, attendees, purpose, and a delete button.

**Changes:**

- Auto-discovered meetings display with an "Auto" badge (small pill, muted color) next to the date
- Show `scanned_from` as "via Oscar" or "via Tony" in a secondary text line
- Show `location` if present (e.g., "Zoom", "Conference Room 3")
- Sort all meetings (manual + auto) by `meeting_date` ascending
- Auto-discovered meetings use the same delete button. Clicking delete adds the `graph_event_id` to the dismissed list and removes the entry.
- Past auto-discovered meetings (older than 7 days) are automatically hidden

### States

- **No meetings (manual or auto)**: "No upcoming meetings" message with "Add Meeting" button (existing behavior)
- **Only auto-discovered meetings**: Show them with Auto badges. "Add Meeting" button still visible.
- **Mix of manual and auto**: Interleaved by date, badges distinguish source
- **Auto meeting deleted by user**: Removed from UI, added to dismissed list, does not reappear on next scan

## 6. Integration Points

- **Reads from**: Microsoft Graph API `calendarView` endpoint for each team member (30-day window)
- **Reads from**: CRM organizations list (for org matching), contacts list (for email/domain matching)
- **Writes to**: `prospect_meetings` store (JSON or PostgreSQL, depending on backend mode)
- **Reads from**: `dismissed_graph_events` (to skip previously dismissed events)
- **Called by**: The daily Graph API poller (`graph_poller.py` or `crm_graph_sync.py`, depending on which runs)
- **Displayed by**: Prospect Detail page template (`crm_prospect_detail.html`)
- **Uses**: Existing org matching logic from `crm_graph_sync.py` (`_resolve_participant`, `_fuzzy_match_org`, domain lookups, contact email lookups)

## 7. Constraints

- **Graph API pagination**: Calendar views for 30 days can return many events. Use the existing `_paginated_get` pattern from `ms_graph.py` which follows `@odata.nextLink`.
- **Rate limiting**: Graph API returns 429 with `Retry-After` header. Use existing exponential backoff from `ms_graph.py`.
- **Token scope**: Requires `Calendars.Read` (already in the existing scope list for both device code flow and application permissions).
- **Scan window**: Always 30 days forward from today. Do not make this configurable in Phase 1.
- **Performance**: The forward scan adds one Graph API call per team member per poll cycle. With 8 team members and ~50 events each over 30 days, this is ~400 events to match. Keep matching logic efficient — pre-build the org domain and contact email indexes once per scan, not per event.
- **Backend mode**: Must work in both markdown (`crm_reader.py`) and PostgreSQL (`crm_db.py`) modes. Add `save_prospect_meeting` calls that include the new fields. The existing function signature accepts `meeting_date, meeting_time, attendees, purpose` — extend it to accept optional `source`, `graph_event_id`, `scanned_from`, `location` kwargs.
- **Existing `save_prospect_meeting` contract**: The function returns the new entry dict. Callers in `crm_blueprint.py` rely on this. Do not break it — new fields are additive.

## 8. Acceptance Criteria

- [ ] Graph poller fetches calendar events 30 days forward for all team members where `graph_consent_granted = True`
- [ ] Events with at least one external attendee matching a known CRM org are written to `prospect_meetings`
- [ ] Auto-discovered meetings have `source: "auto-graph"`, `graph_event_id`, `scanned_from`, and `location` fields
- [ ] Duplicate events (same `graph_event_id` + prospect key) are not re-inserted on subsequent runs
- [ ] Updated events (same `graph_event_id`, different time/attendees) are updated in place
- [ ] Events matching multiple active prospects for the same org are written to all of them
- [ ] Internal-only meetings (all attendees `@avilacapllc.com`) are skipped
- [ ] All-day events are skipped
- [ ] Events matching "Settler" are skipped
- [ ] Prospect Detail Meetings section shows auto-discovered meetings with "Auto" badge
- [ ] "via Oscar" / "via Tony" attribution is displayed
- [ ] Deleting an auto-discovered meeting adds its `graph_event_id` to `dismissed_graph_events` and it does not reappear
- [ ] Past auto-discovered meetings older than 7 days are cleaned up on each run
- [ ] Manual meetings are unaffected — no regressions in add/delete manual meeting flows
- [ ] Existing `save_prospect_meeting` callers in `crm_blueprint.py` still work (backward-compatible signature)
- [ ] Feedback loop prompt has been run

## 9. Files Likely Touched

### Modified

| File | Reason |
|------|--------|
| `app/sources/crm_graph_sync.py` | Add `scan_future_calendar()` function. Build org/domain/contact indexes. Match events → prospect meetings. Call `save_prospect_meeting` with new fields. Clean up stale auto-discovered meetings. |
| `app/sources/crm_reader.py` | Extend `save_prospect_meeting()` to accept optional `source`, `graph_event_id`, `scanned_from`, `location` kwargs. Add `load_dismissed_graph_events()`, `dismiss_graph_event()`. Add dedup-aware save logic. Add `update_prospect_meeting()` for in-place updates. Add `cleanup_stale_auto_meetings()`. |
| `app/sources/crm_db.py` | Same extensions as `crm_reader.py` for PostgreSQL backend. Add `DismissedGraphEvent` model if using PostgreSQL. |
| `app/models.py` | Add `DismissedGraphEvent` table (PostgreSQL mode). Add optional columns to prospect meetings if stored in DB. |
| `app/sources/ms_graph.py` | Add `get_future_events(token, days=30)` function that calls `calendarView` for a 30-day forward window. Optionally add `get_future_events_for_user(token, user_email, days=30)` for scanning other team members' calendars. |
| `app/delivery/crm_blueprint.py` | Update `api_delete_prospect_meeting` to also call `dismiss_graph_event()` when the deleted meeting has a `graph_event_id`. Pass `source` field when loading meetings for template rendering. |
| `app/templates/crm_prospect_detail.html` | Add "Auto" badge for meetings where `source == "auto-graph"`. Show `scanned_from` as "via {name}". Show `location` field. |
| `app/static/crm.css` | Style for "Auto" badge pill (small, muted background, uppercase text) |

### New Files

| File | Reason |
|------|--------|
| `scripts/migrate_add_dismissed_events.py` | Migration to create `dismissed_graph_events` table (PostgreSQL mode) |

### Not Touched

| File | Reason |
|------|--------|
| `app/delivery/tasks_blueprint.py` | No task changes |
| `app/briefing/` | Briefing system not involved |
| `app/auth/` | Auth unchanged — existing scopes cover `Calendars.Read` |
