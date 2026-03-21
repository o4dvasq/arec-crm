SPEC: Teams Meeting Transcript Retrieval | Project: arec-crm | Date: 2026-03-20 | Status: Ready for implementation

---

## 1. Objective

Add automatic Teams meeting transcript retrieval to the CRM update calendar scan (Step 4 of `/crm-update`). When a past Teams meeting has a transcript available, pull it, convert it to readable text, store it as the meeting's `notes_raw`, and trigger AI processing for insights and action items. This eliminates the manual step of someone writing up meeting notes after calls.

## 2. Scope

- Modify the `/crm-update` skill's Step 4 (Calendar Scan) to check for and retrieve transcripts on past meetings
- Add a new Step 4b between the existing Step 4 and Step 5
- No changes to the Flask app, crm_reader.py, or meetings.json schema (the existing `transcript_url` and `notes_raw` fields already support this)

## 3. Business Rules

- Only pull transcripts for meetings that occurred in the past (completed meetings, not scheduled future ones)
- Only pull transcripts for meetings that don't already have `notes_raw` content (don't overwrite manually-entered notes)
- Store the `meetingTranscriptUrl` value from the calendar event on the meeting record's `transcript_url` field
- Convert the WEBVTT transcript to readable speaker-labeled text before storing as `notes_raw`
- If a transcript is unavailable (not all Teams meetings have transcription enabled), skip silently — this is expected
- If transcript retrieval fails with an error, report but don't abort the update

## 4. Data Model / Schema Changes

None. The existing `meetings.json` schema already has:
- `transcript_url` — stores the meeting-transcript:// URI
- `notes_raw` — stores the readable transcript text
- `notes_summary` — populated by `process_meeting_notes()` in Step 5

## 5. How It Works — The Retrieval Pattern

This is the exact pattern discovered and validated on 2026-03-20 against the "AREC Fundraising Weekly Update" call. It should be followed precisely by the `/crm-update` skill.

### Step A: Calendar event → transcript URI

When `outlook_calendar_search` returns an event, the event metadata includes a `meetingTranscriptUrl` field if a Teams transcript exists. This field is NOT present on the lightweight search results — you must call `read_resource` on the calendar event URI to get it.

```
# 1. Search calendar (already done in Step 4)
event = outlook_calendar_search(query="*", afterDateTime="7 days ago", ...)

# 2. For past meetings without notes, read the full event detail
full_event = read_resource(uri=event.uri)
#    ↪ full_event now includes: meetingTranscriptUrl (if available)
```

The `meetingTranscriptUrl` looks like:
```
meeting-transcript:///events/https%3A%2F%2Fteams.microsoft.com%2Fl%2Fmeetup-join%2F19%253ameeting_...
```

### Step B: Transcript URI → raw WEBVTT

Call `read_resource` with the `meetingTranscriptUrl` value directly:

```
transcript_data = read_resource(uri=full_event.meetingTranscriptUrl)
```

This returns a JSON object with structure:
```json
{
  "meeting": {
    "id": "...",
    "subject": "AREC Fundraising Weekly Update",
    "startDateTime": "2026-03-20T15:00:00.000Z",
    "endDateTime": "2026-03-20T16:00:00.000Z",
    "joinWebUrl": "https://teams.microsoft.com/..."
  },
  "transcripts": [
    {
      "id": "...",
      "content": "WEBVTT\r\n\r\n00:00:12.080 --> 00:00:12.320\r\n<v Speaker Name>Hello.</v>\r\n..."
    }
  ]
}
```

**Important:** The result may be very large (200K+ characters for a 1-hour call). The MCP tool may save it to a temp file rather than returning inline. The skill must handle both cases.

### Step C: WEBVTT → readable text

Parse the WEBVTT content into speaker-labeled readable text. The format is:

```
WEBVTT

00:00:12.080 --> 00:00:12.320
<v Speaker Name>Spoken text here.</v>

00:00:14.000 --> 00:00:16.500
<v Another Speaker>Their spoken text.</v>
```

Conversion rules:
1. Extract timestamp from the `HH:MM:SS.mmm --> HH:MM:SS.mmm` line (use the start time)
2. Extract speaker name and text from `<v Name>Text</v>` tags
3. Consolidate consecutive lines from the same speaker into one block
4. Output format per speaker change: `\n**Speaker Name** [HH:MM:SS]\nText text text`

This produces clean, readable text that works well as `notes_raw` for AI summarization in Step 5.

### Step D: Store on the meeting record

```python
update_meeting(meeting_id,
    transcript_url=meetingTranscriptUrl,     # The meeting-transcript:// URI
    notes_raw=readable_transcript_text,       # The converted text
    status="completed"                        # Mark as completed if still "scheduled"
)
```

## 6. Integration into /crm-update Skill

### Modified Step 4 flow:

After upserting calendar events into meetings.json (existing behavior), add:

**Step 4b: Pull Transcripts for Past Meetings**

```
For each calendar event that was:
  - In the past (meeting_date < today)
  - Already in meetings.json (just upserted or previously existed)
  - Has NO notes_raw content on the meeting record

  1. read_resource(uri=event.uri) → get full event with meetingTranscriptUrl
  2. If meetingTranscriptUrl exists:
     a. read_resource(uri=meetingTranscriptUrl) → get WEBVTT
     b. Parse WEBVTT → readable text (per Step C above)
     c. update_meeting(meeting_id, transcript_url=..., notes_raw=..., status="completed")
     d. Report: "📝 Transcript pulled: [meeting title] on [date]"
  3. If meetingTranscriptUrl is absent or null: skip silently (not all meetings have transcription)
  4. If read_resource fails: report error, continue with next meeting
```

### Updated Step 4 report line:

```
Calendar: N events scanned, M upserted to meetings.json, K upcoming, L past without notes, T transcripts pulled
```

Meetings that received transcripts will then be picked up by Step 5 (Process Meeting Notes → AI Insights) automatically, since they now have `notes_raw` but no `notes_summary`.

## 7. Constraints

- Transcript access requires that Teams transcription was enabled for the meeting (organizer setting). Not all meetings will have transcripts — this is normal, not an error.
- Transcript content can be very large (200K+ chars for a 1-hour call). The MCP `read_resource` tool may save results to a temp file. The skill must handle reading from the temp file path.
- The `meetingTranscriptUrl` field is only available on the full event detail (via `read_resource`), not on the lightweight search results from `outlook_calendar_search`. This means one extra API call per past meeting to check for transcripts.
- Rate limiting: if there are many past meetings, process them sequentially to avoid hitting Graph API rate limits.
- The WEBVTT parser should be tolerant of formatting variations (missing speakers, overlapping timestamps, etc.).

## 8. Acceptance Criteria

- [ ] `/crm-update` Step 4 checks for transcripts on all past meetings that lack `notes_raw`
- [ ] When a transcript exists, it is retrieved, converted to readable text, and stored on the meeting record
- [ ] The `transcript_url` field is populated with the `meeting-transcript://` URI
- [ ] Step 5 (AI processing) automatically picks up these transcript-enriched meetings
- [ ] Meetings without transcription enabled are skipped silently (no error reported)
- [ ] Transcript retrieval errors are reported but don't abort the update
- [ ] Report line includes count of transcripts pulled
- [ ] Feedback loop prompt has been run

## 9. Files Likely Touched

| File | Change |
|------|--------|
| `mnt/.skills/skills/crm-update/SKILL.md` | Add Step 4b transcript retrieval instructions + WEBVTT parsing logic |
| No application code changes needed | The skill orchestrates via MCP tools + existing crm_reader.py functions |
