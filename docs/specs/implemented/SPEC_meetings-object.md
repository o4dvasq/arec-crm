# SPEC: Meetings Object (First-Class)

**Project:** arec-crm
**Date:** 2026-03-15
**Status:** Ready for implementation (future)
**Branch:** main

---

## 1. Objective

Promote meetings from a lightweight JSON blob and flat markdown history into a first-class CRM object with a full lifecycle (scheduled → completed → reviewed), AI-powered notes processing, a human-reviewed insights queue, and a calendar-scan pipeline that auto-creates meeting shells from Graph API events. This replaces the existing `prospect_meetings.json` (upcoming only, no status, no notes) and `meeting_history.md` (flat text, no structure) with a unified `crm/meetings.json` store, upgrades the existing Prospect Detail meeting sections, and adds a standalone `/crm/meetings` list view. Calendar scanning runs as a Claude Desktop skill (like email-scan), supporting multiple consented Graph API users.

---

## 2. Scope

**In scope:**

- New unified `crm/meetings.json` file replacing both `prospect_meetings.json` and `meeting_history.md`
- Meeting status lifecycle: `scheduled` → `completed` → `reviewed`
- Calendar scan Claude Desktop skill: 30-day forward lookahead across all consented users, auto-creates `scheduled` meeting shells
- Deduplication: primary key = Graph calendar event ID; fallback = fuzzy match (org + date ±24h)
- Meeting notes ingestion: manual entry via UI and email-sourced notes attached to a meeting record
- AI pipeline: Claude summarizes notes → extracts prospect-relevant insights → queues for human review → user approves → writes to prospect notes
- Interaction log breadcrumb: when a meeting completes, a one-line entry is appended to `interactions.md` with `type = Meeting`
- Prospect Detail page: upgrade existing "Upcoming Meetings" and "Meeting Summaries" sections to use the new data model
- Standalone `/crm/meetings` list view with filters
- Migration script to convert existing `prospect_meetings.json` and `meeting_history.md` data into `meetings.json`

**Out of scope:**

- Teams transcript auto-ingestion (future phase — `transcript_url` field is stubbed in the schema)
- Notion meeting notes sync
- Recording storage or playback
- Meeting-triggered stage progression (no automatic stage changes from a meeting)
- Multi-prospect meetings (each meeting is linked to exactly one org; if multiple orgs attend, create separate records)

---

## 3. Business Rules

1. **One meeting, one org.** A meeting belongs to exactly one organization (keyed by org name, consistent with the rest of the CRM). If multiple prospect orgs attend the same call (rare), create separate meeting records per org.

2. **Status lifecycle:**
   - `scheduled` — calendar event found or manually created, meeting has not occurred yet and has no notes
   - `completed` — meeting date has passed OR notes have been manually attached; AI processing may or may not have run
   - `reviewed` — AI has processed notes AND all queued insights have been approved or dismissed by a user

3. **Deduplication — two-tier:**
   - **Tier 1 (exact):** If `graph_event_id` is present, it is the unique key. No duplicate with the same `graph_event_id` can be created.
   - **Tier 2 (fuzzy):** When meeting notes arrive without an event ID (e.g., from email or manual entry), attempt to match against existing `scheduled` or `completed` meetings by: same org AND `meeting_date` within ±24 hours. If match found, attach notes to existing record. If no match, create a new `completed` meeting record.

4. **AI insights queue:** When notes are processed by Claude, extracted insights are stored as objects in the meeting's `insights` array, each with `status: "pending"`. A user must explicitly approve or dismiss each insight. Approved insights are appended to the prospect's `Notes` field (in `prospects.md`) with a datestamp prefix: `[Meeting YYYY-MM-DD] {insight text}`. Dismissed insights are marked `"dismissed"` and never written.

5. **Interaction log breadcrumb:** When a meeting moves to `completed` (notes attached), a one-line entry is appended to `interactions.md` using the existing `append_interaction()` function:
   ```
   ## YYYY-MM-DD

   ### Org Name — Meeting — Offering
   - **Subject:** {meeting title}
   - **Summary:** Meeting with {attendees} — {first 100 chars of notes_summary or "Notes pending"}
   - **Source:** meeting
   ```
   The meeting record itself is the authoritative source — the interaction entry is a breadcrumb only.

6. **Calendar scan scope:** The skill scans calendars for all users listed in `crm/calendar_users.json`. A meeting shell is only created if the calendar event can be matched to an existing prospect org (via attendee email domain or org name fuzzy match against the event title/subject). Unmatched events are ignored.

7. **Prospect matching from calendar events:** Attempt to link a calendar event to an org by:
   (a) Matching any attendee email domain against org domains (using `get_org_domains()` from `crm_reader.py`)
   (b) Fuzzy matching event title/subject against org names (threshold: ≥ 0.75 similarity via `difflib.SequenceMatcher`)
   First match wins. If no match, skip the event.

8. **Notes are append-only once set.** Edits to meeting notes after AI processing require re-triggering the AI pipeline. New insights replace old `pending` items; already-`approved` items are preserved.

9. **Automatic status transitions:** A nightly or on-load sweep should mark any `scheduled` meeting whose `meeting_date` is in the past as `completed` (unless it already has notes, in which case it stays at whatever status the notes pipeline set).

---

## 4. Data Model / Schema Changes

### New file: `crm/meetings.json`

Top-level array of meeting objects:

```json
[
  {
    "id": "uuid-v4-string",
    "org": "Texas Permanent School Fund",
    "offering": "AREC Debt Fund II",
    "meeting_date": "2026-03-20",
    "meeting_time": "14:00",
    "title": "Q1 Portfolio Update",
    "attendees": "Tony, Oscar, Jared Brimberry",
    "graph_event_id": "AAMkAGQ3...",
    "source": "calendar",
    "status": "scheduled",
    "notes_raw": null,
    "notes_summary": null,
    "transcript_url": null,
    "insights": [],
    "created_by": "oscar",
    "created_at": "2026-03-15T10:30:45Z",
    "updated_at": "2026-03-15T10:30:45Z"
  }
]
```

**Field definitions:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string (UUID4) | yes | Generated on creation. Primary key. |
| `org` | string | yes | Organization name. Must match an org in `organizations.md`. |
| `offering` | string | yes | Offering name (e.g., "AREC Debt Fund II"). Used for prospect lookup. |
| `meeting_date` | string (YYYY-MM-DD) | yes | Date of the meeting. |
| `meeting_time` | string (HH:MM) | no | Time in 24h format. Null for all-day or unknown. |
| `title` | string | no | From calendar event subject or manual entry. |
| `attendees` | string | no | Comma-separated display names or emails. |
| `graph_event_id` | string | no | Graph API calendar event ID. Unique constraint enforced in code. |
| `source` | string | yes | One of: `"calendar"`, `"email"`, `"manual"`. Default `"manual"`. |
| `status` | string | yes | One of: `"scheduled"`, `"completed"`, `"reviewed"`. Default `"scheduled"`. |
| `notes_raw` | string | no | Raw meeting notes / transcript text. |
| `notes_summary` | string | no | Claude-generated summary (1–3 paragraphs). |
| `transcript_url` | string | no | Link to Teams recording or transcript (stubbed for future). |
| `insights` | array | yes | Array of insight objects (see below). Default `[]`. |
| `created_by` | string | yes | Username (e.g., `"oscar"`, `"tony"`). |
| `created_at` | string (ISO 8601) | yes | UTC timestamp. |
| `updated_at` | string (ISO 8601) | yes | UTC timestamp. Updated on any write. |

**Insight object schema (nested in `insights` array):**

```json
{
  "id": "uuid-v4-string",
  "text": "Investor expressed concern about fund leverage ratio exceeding 65%",
  "status": "pending",
  "reviewed_by": null,
  "reviewed_at": null,
  "created_at": "2026-03-20T16:45:00Z"
}
```

| Field | Type | Notes |
|-------|------|-------|
| `id` | string (UUID4) | Per-insight unique key. |
| `text` | string | Claude-extracted insight. |
| `status` | string | `"pending"`, `"approved"`, or `"dismissed"`. |
| `reviewed_by` | string or null | Username who reviewed. Null until reviewed. |
| `reviewed_at` | string (ISO 8601) or null | Null until reviewed. |
| `created_at` | string (ISO 8601) | When the AI pipeline generated this insight. |

### New file: `crm/calendar_users.json`

Config file for the calendar scan skill:

```json
[
  {
    "email": "oscar@avilacapllc.com",
    "display_name": "Oscar",
    "active": true
  },
  {
    "email": "tony@avilacapllc.com",
    "display_name": "Tony",
    "active": true
  }
]
```

### Migration

A one-time migration script (`scripts/migrate_meetings.py`) converts:

1. **`prospect_meetings.json`** → Each entry becomes a meeting with `status: "scheduled"`, `source: "manual"`. The `purpose` field maps to `title`. The `org::offering` key is split into `org` and `offering` fields. The old timestamp `id` maps to `created_at`; a new UUID is generated for `id`.

2. **`meeting_history.md`** → Each `## date — title` section becomes a meeting with `status: "reviewed"` (historical meetings are considered fully processed), `source: "manual"`. Key points and action items are concatenated into `notes_raw`. The `notes_summary` is left null (or optionally populated from existing content).

After migration, the old files are renamed to `prospect_meetings.json.bak` and `meeting_history.md.bak`.

---

## 5. UI / Interface

### 5a. Prospect Detail Page — Upgrade Existing Meeting Sections

**Upcoming Meetings section** (replaces existing `renderUpcomingMeetings`):
- Data source changes from `load_prospect_meetings()` to `load_meetings(org, offering, status="scheduled", future_only=True)`
- Each row: date/time, title, attendees (truncated), source badge (Calendar / Email / Manual), delete button
- "Add Meeting" form stays the same but now writes to `meetings.json` via the new functions
- Empty state: "No upcoming meetings scheduled." (existing behavior)

**Past Meetings section** (replaces existing `renderMeetings` which reads markdown files):
- Data source changes from `find_meeting_summaries()` to `load_meetings(org, offering, status=["completed", "reviewed"], past_only=True)`
- Each row: date, title, status badge (Completed = amber, Reviewed = green), summary preview (first 100 chars of `notes_summary`, or "No notes yet"), "View" link
- Collapsed to 3 most recent by default; "Show all (N)" expander
- Empty state: hidden entirely (existing pattern)

**Meeting Detail Panel (modal or slide-in):**
Triggered by "View" link on a past meeting. Shows:
- Date, title, attendees, source, transcript URL (if present)
- Notes Summary (Claude-generated, or "Not yet processed")
- Raw Notes (collapsed, expandable)
- Insights Review Queue (if any insights with `status: "pending"`):
  - Each insight shown as a card with text + [Approve] [Dismiss] buttons
  - Approving writes `[Meeting YYYY-MM-DD] {insight}` appended to prospect `Notes` field in `prospects.md`
  - Counter: "3 insights pending review"
- If `status = "scheduled"` or `status = "completed"` with no notes: "Add Notes" textarea + "Process with AI" button

### 5b. Standalone Meetings List View — `/crm/meetings`

New route and template `crm_meetings.html`. Add "Meetings" to the nav bar.

**Layout:**
- Page title: "Meetings"
- Filter bar: Status (All / Scheduled / Completed / Reviewed), Date range, Search (org name or title)
- Table columns: Date | Org | Title | Attendees | Source | Status | Notes
  - Date: formatted, upcoming meetings sorted first
  - Org: links to prospect detail page
  - Status: badge (Scheduled = blue, Completed = amber, Reviewed = green)
  - Notes: "Pending review (N)" link if insights in queue, else "View" or "—"
- Empty state: "No meetings found."
- "Add Meeting" button top-right → same form as prospect detail, but with an Org/Offering searchable dropdown (since no context org)

### 5c. Add Meeting Form (shared between 5a and 5b)

Fields:
- Org + Offering (pre-filled on prospect detail; searchable dropdown on standalone view — required)
- Meeting Date (date input — required)
- Meeting Time (time input — optional)
- Title (text input — optional)
- Attendees (text input, comma-separated — optional)
- Transcript URL (text input — optional)
- Notes (textarea — optional; if provided, "Process with AI" checkbox defaults to checked)
- Source: auto-set to `"manual"`

On submit: creates meeting record in `meetings.json`. If notes provided and "Process with AI" checked → triggers AI pipeline (see Section 6).

---

## 6. Integration Points

### Calendar Scan Skill (`skills/calendar-scan.md` — new Claude Desktop skill)

Modeled after `skills/email-scan.md`. Runs as a Claude Desktop skill via MCP tools.

**Trigger:** Manual via "scan calendar", "calendar scan", "check calendar for meetings", or automatic as part of `/productivity:update`.

**Config:** Reads `crm/calendar_users.json` for the list of users to scan.

**Workflow:**
```
1. Load crm/meetings.json — build set of existing graph_event_ids for dedup
2. Load org domains via get_org_domains(prospect_only=True) from crm_reader.py
3. For each user in calendar_users.json WHERE active = true:
     Use outlook_calendar_search MCP tool:
       startDateTime = now()
       endDateTime = now() + 30 days
     For each event:
       If graph_event_id already in meetings.json → skip (Tier 1 dedup)
       Attempt prospect match:
         (a) Match attendee email domains against org domains
         (b) Fuzzy match event subject against org names (≥ 0.75)
       If match found:
         Create meeting record: status="scheduled", source="calendar"
         Determine offering from prospect lookup (org → active prospect → offering)
       If no match → skip, log to scan summary
4. Write updated meetings.json
5. Report summary: N new meetings created, M events skipped (no org match), K duplicates skipped
```

**Multi-user note:** Oscar has delegate access to Tony's calendar. The skill uses `outlook_calendar_search` with the appropriate user context per the MCP tool's capabilities (same pattern as email-scan passes for Tony's mailbox).

### AI Notes Pipeline (new functions in `crm_reader.py`)

**Trigger:** Called when notes are attached to a meeting via the UI "Process with AI" action, or when the calendar-scan skill attaches email-sourced notes.

**Implementation:** New function `process_meeting_notes(meeting_id)` in `crm_reader.py` that:

1. Loads the meeting record from `meetings.json`
2. Calls Claude API (same pattern as `brief_synthesizer.py`) with the prompt:

```
System: You are an analyst extracting intelligence from meeting notes for a real estate
private equity fundraising CRM.

User:
Meeting: {title} with {org} on {meeting_date}
Attendees: {attendees}

NOTES:
{notes_raw}

Return JSON only:
{
  "summary": "2-3 paragraph narrative summary of the meeting",
  "insights": [
    "Specific actionable insight about this investor's interest, concerns, or next steps",
    ...
  ]
}
Insights should be specific, concise (1–2 sentences each), and relevant to fundraising
relationship management. Do not include generic observations. Max 5 insights.
```

3. Parses the response (with fallback handling, same pattern as `brief_synthesizer.py`)
4. Writes `notes_summary` to the meeting record
5. Creates insight objects in the meeting's `insights` array, each with `status: "pending"` and a generated UUID
6. Updates meeting `status` to `"completed"` if it was `"scheduled"`
7. Writes the interaction log breadcrumb to `interactions.md` via `append_interaction()`
8. Saves `meetings.json`

### Interaction Log Breadcrumb

When a meeting transitions to `completed` (notes attached or date passed), `append_interaction()` is called with:
```python
{
    "date": meeting["meeting_date"],
    "org": meeting["org"],
    "type": "Meeting",
    "offering": meeting["offering"],
    "Subject": meeting["title"] or "Meeting",
    "Summary": f"Meeting with {meeting['attendees']} — {(meeting.get('notes_summary') or 'Notes pending')[:100]}",
    "Source": "meeting"
}
```

This uses the existing `append_interaction()` function with no modifications needed.

### Prospect Notes Write (on insight approval)

New function `approve_meeting_insight(meeting_id, insight_id, username)` in `crm_reader.py`:

1. Loads meeting from `meetings.json`
2. Finds insight by `insight_id` in the meeting's `insights` array
3. Sets `status: "approved"`, `reviewed_by: username`, `reviewed_at: now()`
4. Constructs prefix: `[Meeting YYYY-MM-DD] `
5. Appends `prefix + insight.text` to the prospect's `Notes` field in `prospects.md` via existing prospect field update functions
6. Checks if all insights are now `"approved"` or `"dismissed"` → if so, sets meeting `status: "reviewed"`
7. Saves `meetings.json`

Similarly, `dismiss_meeting_insight(meeting_id, insight_id, username)`:
- Sets insight `status: "dismissed"`, `reviewed_by`, `reviewed_at`
- Does NOT write to prospect notes
- Checks if all insights reviewed → updates meeting status if so

---

## 7. Constraints

- Use `claude-sonnet-4-6`, max_tokens 1000 for meeting note processing (notes are bounded; same model as brief synthesis)
- Fuzzy org name matching: use `difflib.SequenceMatcher` (already available). Threshold ≥ 0.75. Can also reuse `_fuzzy_match_org()` from `email_matching.py`.
- Calendar scan must be idempotent — running twice must not create duplicate meeting records. `graph_event_id` uniqueness check is the guard.
- No new Python dependencies. No new JS libraries. Insights review UI uses vanilla JS (existing pattern in prospect detail).
- All new web routes under `crm_blueprint.py`. No new blueprint.
- All data access functions in `crm_reader.py`. No new data layer files. AI notes processing also lives in `crm_reader.py` (same pattern as other Claude API calls go through existing modules).
- `meetings.json` writes use the same file I/O patterns as other JSON files in the CRM (`prospect_notes.json`, `email_log.json`).
- Empty sections on Prospect Detail are hidden (zero DOM nodes), consistent with existing pattern.
- The calendar scan skill follows the same structure as `skills/email-scan.md`: MCP tool calls, match against CRM orgs, write to JSON, report summary.
- No database. No ORM. No `models.py`. No `crm_db.py`. Everything goes through `crm_reader.py` and markdown/JSON files.

---

## 8. Acceptance Criteria

1. `crm/meetings.json` exists and is the single source of truth for all meeting data (replaces both `prospect_meetings.json` and `meeting_history.md`).
2. `scripts/migrate_meetings.py` converts existing `prospect_meetings.json` entries and `meeting_history.md` entries into `meetings.json` format. Old files are renamed to `.bak`.
3. Calendar scan skill (`skills/calendar-scan.md`): running the skill for consented users creates `scheduled` meeting shells for calendar events in the next 30 days that match a prospect org, and is fully idempotent.
4. A calendar event already in `meetings.json` (same `graph_event_id`) is never duplicated on re-scan.
5. A new meeting notes submission (no event ID) that matches an existing meeting by org + ±24h date is attached to that record, not a new one.
6. Manual "Add Meeting" form creates a meeting record and optionally triggers AI processing.
7. AI processing produces a `notes_summary` on the meeting and one or more insight objects with `status: "pending"`.
8. Approving an insight appends `[Meeting YYYY-MM-DD] {text}` to the prospect's `Notes` field in `prospects.md` and marks the insight `"approved"`.
9. Dismissing an insight marks it `"dismissed"` and does not write to the prospect.
10. When all insights on a meeting are approved or dismissed, meeting `status` updates to `"reviewed"`.
11. Completing a meeting writes a breadcrumb entry to `interactions.md` via `append_interaction()`.
12. Prospect Detail page shows upgraded "Upcoming Meetings" section (scheduled future meetings) and "Past Meetings" section (completed/reviewed), both hidden when empty.
13. Meeting detail panel shows notes summary, raw notes, and insights review queue with working approve/dismiss buttons.
14. `/crm/meetings` route renders the meetings list view with working Status filter, date range filter, and org name/title search.
15. "Meetings" link appears in the nav bar.
16. All new `crm_reader.py` functions have corresponding tests in `app/tests/test_meetings.py`.
17. Existing tests still pass (52+).
18. Feedback loop prompt has been run and `PROJECT_STATE.md`, `DECISIONS.md` updated.

---

## 9. Files Likely Touched

| File | Reason |
|------|--------|
| `crm/meetings.json` | **New file.** Unified meeting data store. |
| `crm/calendar_users.json` | **New file.** Config for calendar scan skill — list of users to scan. |
| `app/sources/crm_reader.py` | New functions: `load_meetings()`, `save_meeting()`, `delete_meeting()`, `get_meeting()`, `update_meeting()`, `process_meeting_notes()`, `approve_meeting_insight()`, `dismiss_meeting_insight()`, `_find_meeting_by_fuzzy()`. Deprecate: `load_prospect_meetings()`, `save_prospect_meeting()`, `delete_prospect_meeting()`, `load_meeting_history()`, `add_meeting_entry()`. |
| `app/delivery/crm_blueprint.py` | New routes: `GET /crm/meetings` (page), `GET /crm/api/meetings` (list API), `POST /crm/api/meetings` (create), `GET /crm/api/meetings/<id>` (detail), `POST /crm/api/meetings/<id>/notes` (attach notes + trigger AI), `POST /crm/api/meetings/<id>/insights/<iid>/approve`, `POST /crm/api/meetings/<id>/insights/<iid>/dismiss`, `DELETE /crm/api/meetings/<id>`. Update prospect detail data endpoint to use new meeting functions. |
| `app/templates/crm_meetings.html` | **New template.** Standalone meetings list view. |
| `app/templates/crm_prospect_detail.html` | Upgrade `renderUpcomingMeetings()` and `renderMeetings()` to use new data model. Add meeting detail panel/modal. Add insights review queue UI. |
| `app/templates/_nav.html` or equivalent nav include | Add "Meetings" nav item. |
| `app/static/crm.js` | Insights approve/dismiss AJAX calls. Meeting detail panel open/close. Meeting form submit for standalone view. |
| `skills/calendar-scan.md` | **New file.** Claude Desktop skill for calendar scanning (modeled on `skills/email-scan.md`). |
| `scripts/migrate_meetings.py` | **New file.** One-time migration from `prospect_meetings.json` + `meeting_history.md` → `meetings.json`. |
| `app/tests/test_meetings.py` | **New file.** Tests for meeting CRUD, dedup logic, insight approval/dismissal, status transitions, interaction breadcrumb. |

---

## 10. Existing Code Being Replaced

This spec replaces and unifies three separate systems:

| Current | Location | Limitation | Replaced by |
|---------|----------|-----------|-------------|
| Upcoming meetings | `crm/prospect_meetings.json` | No status, no notes, no AI, timestamp-as-ID | `crm/meetings.json` with `status: "scheduled"` |
| Meeting history | `crm/meeting_history.md` | Flat markdown, no structured fields, no insights | `crm/meetings.json` with `status: "completed"` or `"reviewed"` |
| Meeting summaries | `find_meeting_summaries()` reads loose `.md` files | Unstructured, no connection to meeting records | `notes_summary` field on meeting object |
| `load_prospect_meetings()` | `crm_reader.py` line 1852 | Returns raw JSON blobs, no lifecycle | `load_meetings()` with filtering |
| `save_prospect_meeting()` | `crm_reader.py` line 1867 | Writes to flat JSON, no UUID, no status | `save_meeting()` |
| `delete_prospect_meeting()` | `crm_reader.py` line 1899 | Deletes by timestamp ID | `delete_meeting()` by UUID |
| `load_meeting_history()` | `crm_reader.py` line 1365 | Parses markdown pipes, read-only | `load_meetings(status=["completed", "reviewed"])` |
| `add_meeting_entry()` | `crm_reader.py` line 1405 | Appends markdown, basic dedup | `save_meeting()` with two-tier dedup |

After migration, the old functions should be deprecated (kept briefly for backward compatibility, then removed in a follow-up cleanup pass).

---

## 11. Implementation Sequencing (Suggested)

**Phase A — Data layer + migration:**
- New `crm_reader.py` functions for meeting CRUD (load, save, get, update, delete)
- `meetings.json` schema
- Migration script (`scripts/migrate_meetings.py`)
- Tests for data layer
- Deprecation wrappers on old functions

**Phase B — UI upgrade on Prospect Detail:**
- Replace existing `renderUpcomingMeetings()` and `renderMeetings()` with new data source
- Update API endpoints to serve new meeting format
- Meeting detail panel (modal)
- "Add Notes" textarea + "Process with AI" button

**Phase C — AI pipeline + insights review:**
- `process_meeting_notes()` function with Claude API call
- Insights review queue UI (approve/dismiss buttons)
- Prospect notes write-back on approval
- Status transition to `reviewed`
- Interaction log breadcrumb on completion

**Phase D — Standalone meetings list view:**
- `/crm/meetings` route and template
- Filters and search
- Nav bar update

**Phase E — Calendar scan skill:**
- `skills/calendar-scan.md` (Claude Desktop skill)
- `crm/calendar_users.json` config file
- Org matching via email domains + fuzzy name match
- Integration with `/productivity:update`
