SPEC: Meetings Object (First-Class, Markdown-Backed)
Project: arec-crm | Branch: markdown-local | Date: 2026-03-15
Status: Future — needs review before implementation

SEQUENCING: Implement AFTER core CRM is stable (cleanup + tasks page + search bar done).
DEPENDS ON: SPEC_crm-markdown-cleanup.md, working CRM on markdown-local.
BACKEND: All data via crm_reader.py and JSON files — NO crm_db.py, NO models.py, NO SQLAlchemy.
NOTE: Originally written for Postgres branch. Scrubbed 2026-03-15 to remove all database references.

---

## 1. Objective

Promote meetings to a first-class object in the CRM. Today, meeting data is scattered across `crm/prospect_meetings.json` (mostly empty) and `crm/meeting_history.md`. This spec introduces structured JSON storage, manual meeting entry, an AI-powered notes ingestion pipeline with human review, and two UI surfaces: meetings sections on Prospect Detail and a standalone Meetings list view.

## 2. Scope

**In scope:**
- Structured meetings storage in `crm/meetings.json`
- Meeting insights storage in `crm/meeting_insights.json`
- Manual meeting creation form
- AI pipeline: Claude summarizes notes → extracts insights → queues for human review → approved insights append to prospect notes
- Prospect Detail: "Upcoming Meetings" and "Past Meetings" sections
- Standalone `/crm/meetings` list view

**Out of scope:**
- Calendar scan job (requires Graph auth — future, see FUTURE_FEATURES.md)
- Teams transcript ingestion (future)
- Graph event ID deduplication (no calendar scan = no event IDs needed)
- Multi-prospect meetings
- Notion meeting notes sync

## 3. Business Rules

1. One meeting, one prospect (org + offering pair).
2. Status lifecycle: `scheduled` → `completed` → `reviewed`.
3. AI insights queue: Claude extracts insights stored with `status: 'pending'`. User approves or dismisses each. Approved insights append to prospect_notes.json with `[Meeting YYYY-MM-DD]` prefix.
4. Meeting identity: UUID generated on creation.
5. All meetings manually created in this spec. Calendar scan is future.
6. Notes are append-only once set. Re-processing replaces pending insights but preserves approved ones.

## 4. Data Model

### crm/meetings.json
```json
[
  {
    "id": "uuid-string",
    "org": "Texas PSF",
    "offering": "AREC Debt Fund II",
    "meeting_date": "2026-03-20T14:00:00",
    "title": "Q2 Follow-up Call",
    "attendees": "Oscar Vasquez, John Smith",
    "source": "manual",
    "status": "scheduled",
    "notes_raw": null,
    "notes_summary": null,
    "created_at": "2026-03-15T10:00:00"
  }
]
```

### crm/meeting_insights.json
```json
[
  {
    "id": "uuid-string",
    "meeting_id": "meeting-uuid",
    "insight_text": "Texas PSF interested in co-investment alongside the fund",
    "status": "pending",
    "reviewed_at": null,
    "created_at": "2026-03-20T15:00:00"
  }
]
```

### New crm_reader.py functions
- `load_meetings(org=None, offering=None, status=None) -> list[dict]`
- `get_meeting(meeting_id) -> dict | None`
- `save_meeting(data) -> dict`
- `update_meeting(meeting_id, fields) -> dict`
- `load_meeting_insights(meeting_id=None, status=None) -> list[dict]`
- `save_meeting_insight(data) -> dict`
- `approve_meeting_insight(insight_id) -> dict` — marks approved, appends to prospect notes
- `dismiss_meeting_insight(insight_id) -> dict` — marks dismissed

## 5. UI / Interface

### Prospect Detail — Meetings Sections
**Upcoming:** status = 'scheduled', date >= today. Row: date/time, title, attendees, "Add Notes" button.
**Past:** status in ('completed', 'reviewed') or past date. Row: date, title, status badge, summary preview. Collapsed to 3 recent.
**Detail modal:** date, title, attendees, summary, raw notes (expandable), insights queue with Approve/Dismiss.

### Standalone /crm/meetings
Filter: status, date range, org search. Table: Date, Org, Title, Status, Notes indicator.

### Add Meeting Form
Prospect (dropdown), Date+Time, Title, Attendees, Notes (optional), "Process with AI" checkbox.

## 6. Integration Points

### AI Pipeline (briefing/meeting_processor.py — new)
Claude prompt: given meeting context + raw notes → return `{summary, insights[]}` JSON.
Model: claude-sonnet-4-6, max_tokens 1000.

### Reads from: crm/meetings.json, crm/meeting_insights.json, crm/prospects.md
### Writes to: crm/meetings.json, crm/meeting_insights.json, crm/prospect_notes.json

## 7. Constraints

- Use `crm_reader.py` for all file I/O — no direct JSON reads in routes
- `uuid.uuid4()` for IDs
- No new JS libraries
- No Graph API calls
- No database imports (no models.py, no crm_db.py, no SQLAlchemy)

## 8. Acceptance Criteria

1. `crm/meetings.json` and `crm/meeting_insights.json` created on first use
2. Manual "Add Meeting" creates a record
3. AI processing produces notes_summary + insights with status = 'pending'
4. Approving an insight appends to prospect notes
5. Dismissing marks as dismissed, no write
6. All insights reviewed → meeting status = 'reviewed'
7. Prospect Detail shows Upcoming/Past sections (hidden when empty)
8. `/crm/meetings` renders with filters
9. All tests pass

## 9. Files Likely Touched

| File | Reason |
|------|--------|
| `app/sources/crm_reader.py` | Add meeting + insight CRUD functions |
| `app/briefing/meeting_processor.py` | New — Claude API for notes processing |
| `app/delivery/crm_blueprint.py` | Add meeting routes |
| `app/templates/crm_meetings.html` | New — meetings list |
| `app/templates/crm_prospect_detail.html` | Add meetings sections |
| `app/templates/_nav.html` | Add "Meetings" nav item |
| `crm/meetings.json` | New data file |
| `crm/meeting_insights.json` | New data file |
