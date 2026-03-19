SPEC: Fix Meeting Duplicates | Project: arec-crm | Date: 2026-03-19 | Status: Ready for implementation

## 1. Objective

Eliminate duplicate meetings in the Past Meetings list by fixing three gaps in the deduplication logic.

## 2. Scope

Three targeted code changes — no new features, no UI changes, no schema changes.

## 3. Business Rules

A meeting is a duplicate if it has the same org (case-insensitive, trimmed) AND the same meeting_date (±1 day). Duplicates should be merged, keeping the record with the most data (preferring the one with `graph_event_id`, `notes_raw`, etc.).

## 4. Data Model / Schema Changes

None. Same `crm/meetings.json` structure.

## 5. Changes Required

### Change A: `app/sources/crm_reader.py` — `save_meeting()` (around line 2202)

**Problem:** Tier 2 dedup only matches meetings with `status='scheduled'`. Once a meeting transitions to `completed`, a second insert from a different source bypasses dedup.

**Fix:** Remove the `status='scheduled'` gate. Change merge behavior to only backfill empty fields (not overwrite existing data).

Replace the Tier 2 block (from `# Dedup tier 2:` through the `except ValueError: pass`) with:

```python
    # Dedup tier 2: fuzzy org+date±1 day match (any status)
    try:
        target_date = datetime.strptime(meeting_date, '%Y-%m-%d').date()
        org_lower = org.lower().strip()

        for meeting in meetings:
            if meeting.get('org', '').lower().strip() != org_lower:
                continue

            meeting_date_str = meeting.get('meeting_date', '')
            if not meeting_date_str:
                continue

            try:
                existing_date = datetime.strptime(meeting_date_str, '%Y-%m-%d').date()
                delta = abs((existing_date - target_date).days)
                if delta <= 1:
                    # Found fuzzy match — merge new data into existing
                    if notes_raw and not meeting.get('notes_raw'):
                        meeting['notes_raw'] = notes_raw
                    if meeting.get('status') == 'scheduled' and notes_raw:
                        meeting['status'] = 'completed'
                    if title and not meeting.get('title'):
                        meeting['title'] = title
                    if attendees and not meeting.get('attendees'):
                        meeting['attendees'] = attendees
                    if transcript_url and not meeting.get('transcript_url'):
                        meeting['transcript_url'] = transcript_url
                    if graph_event_id and not meeting.get('graph_event_id'):
                        meeting['graph_event_id'] = graph_event_id
                    meeting['updated_at'] = datetime.utcnow().isoformat() + 'Z'
                    _save_meetings_raw(meetings)
                    return meeting
            except ValueError:
                continue
    except ValueError:
        pass
```

Also update the docstring from:
```
2. Fuzzy match: same org AND meeting_date ±1 day AND status='scheduled' → return existing
```
to:
```
2. Fuzzy match: same org AND meeting_date ±1 day (any status) → return existing
```

### Change B: `app/sources/crm_reader.py` — `load_meetings()` (around line 2116)

**Problem:** No safety net at read time. If a duplicate sneaks in through any code path, it shows forever.

**Fix:** Add a dedup pass before the filter logic. Insert this block right before the `# Apply filters` comment:

```python
    # Deduplicate: keep first meeting per org+date (first = has more data or earlier created)
    seen = {}
    deduped = []
    for m in meetings:
        key = (m.get('org', '').lower().strip(), m.get('meeting_date', ''))
        if key[0] and key in seen:
            # Merge useful fields from duplicate into the keeper
            keeper = seen[key]
            if m.get('graph_event_id') and not keeper.get('graph_event_id'):
                keeper['graph_event_id'] = m['graph_event_id']
            if m.get('notes_raw') and not keeper.get('notes_raw'):
                keeper['notes_raw'] = m['notes_raw']
            if m.get('notes_summary') and not keeper.get('notes_summary'):
                keeper['notes_summary'] = m['notes_summary']
            continue
        seen[key] = m
        deduped.append(m)

    if len(deduped) < len(meetings):
        _save_meetings_raw(deduped)
        meetings = deduped
```

### Change C: `tools/tony_calendar_scan.py` — main loop (around line where it checks `if event_id in existing_gids`)

**Problem:** Tony's scanner only deduplicates by `graph_event_id`. If another source already created the same meeting without a `graph_event_id`, Tony's scanner creates a duplicate.

**Fix:** Add an org+date fallback dedup right after the `graph_event_id` check. Insert this block between the `existing_gids` check and the `# Match external attendee domains to CRM orgs` comment:

```python
        # Dedup fallback: org+date match (catches cross-source duplicates)
        date_str_check = start_dt[:10] if start_dt else ""
        ext_domains_check = extract_external_domains(attendees, organizer)
        matched_orgs_check = [domain_to_org[d] for d in ext_domains_check if d in domain_to_org]
        if date_str_check and matched_orgs_check:
            org_check = matched_orgs_check[0].lower().strip()
            already_exists = False
            for existing in meetings:
                if existing.get('org', '').lower().strip() == org_check:
                    existing_date = existing.get('meeting_date', '')
                    if existing_date == date_str_check:
                        # Backfill graph_event_id on the existing meeting
                        if event_id and not existing.get('graph_event_id'):
                            existing['graph_event_id'] = event_id
                        already_exists = True
                        break
            if already_exists:
                deduped += 1
                continue
```

## 6. Integration Points

- Tony's `tony_calendar_scan.py` runs on Windows via Task Scheduler (Mon/Wed/Fri 7AM)
- Calendar forward-scan skill calls `save_meeting()` from Cowork sessions
- Manual meeting form calls `save_meeting()` from the web dashboard

## 7. Constraints

- Do not change the meeting JSON schema
- Merge behavior must only backfill empty fields, never overwrite existing data
- The `load_meetings()` safety net should auto-clean the JSON file when it finds duplicates

## 8. Acceptance Criteria

- [ ] `save_meeting()` deduplicates regardless of meeting status
- [ ] `save_meeting()` backfills `graph_event_id` on existing meetings missing it
- [ ] `load_meetings()` deduplicates at read time and auto-cleans the file
- [ ] Tony's scanner catches cross-source duplicates by org+date
- [ ] All 15 meetings tests pass (`python3 -m pytest app/tests/test_meetings.py -v`)
- [ ] `test_fuzzy_dedup` still passes (confirms Tier 2 works for completed meetings too)
- [ ] Feedback loop prompt has been run

## 9. Files Likely Touched

- `app/sources/crm_reader.py` — `save_meeting()` and `load_meetings()`
- `tools/tony_calendar_scan.py` — main event processing loop
