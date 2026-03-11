---
name: meeting-debrief
description: >
  Calendar gap detection and meeting debrief capture. Checks Outlook calendar for meetings
  the user attended today (or a specified date range), cross-references against Notion meeting
  notes, and quizzes the user on any meetings that don't have notes — capturing key decisions,
  action items, and takeaways. Use this skill whenever the user says things like "debrief my
  meetings", "check for missing meeting notes", "what meetings did I have today", "quiz me on
  my meetings", or during any /productivity:update run. Also trigger when the user mentions
  they had meetings but didn't take notes, or asks about gaps in their meeting summaries.
  This skill should run as part of every productivity update cycle.
---

# Meeting Debrief

This skill closes the gap between "I had meetings today" and "I have written records of what happened." It pulls the user's calendar, checks what already has notes in Notion, and walks them through a quick debrief for anything that's missing.

## Why This Matters

Meeting notes are the single highest-value memory artifact — they contain decisions, commitments, and context that decay fast. Even a 2-minute debrief captured the same day is worth more than a detailed reconstruction a week later. The goal here isn't perfection; it's *something written down* for every meeting that matters.

## The Flow

### Step 1: Pull Today's Calendar

Use `outlook_calendar_search` to get all calendar events for the target date (default: today).

```
Query: "*" (all events)
afterDateTime: start of target day
beforeDateTime: end of target day
limit: 50
```

This gives you the full picture of what the user's day looked like.

### Step 2: Filter Out Noise

Not every calendar event is a "meeting" worth debriefing. Skip events that are clearly:

- **Blocks/holds** — events with titles like "Focus Time", "Block", "Hold", "Lunch", "OOO", "Travel", "Commute", "Personal", "Gym"
- **All-day events** that look like reminders or holidays
- **Cancelled events** (check if status indicates cancelled)
- **Very short events** (< 15 minutes) unless they look substantive

When in doubt, include the event — better to ask and skip than to miss something important.

### Step 3: Check for Existing Notes

For each real meeting from the calendar, check two places:

**Notion meeting notes** — Use `notion-query-meeting-notes` filtered to the target date. Fetch full content for any matches. A Notion note "matches" a calendar event if the titles are reasonably similar (fuzzy match — "Team Meeting" matches "AREC Team Meeting", "Contender call" matches "Contender Cross Anchor Loan Discussion").

**Local meeting-summaries/** — Check the `meeting-summaries/` folder for files dated to the target day. Match by title similarity.

A meeting is "covered" if it has a match in either place.

### Step 4: Present the Scorecard

Show the user a quick overview before diving into debriefs:

```
## Today's Meetings — March 5, 2026

| # | Time    | Meeting                        | Notes? |
|---|---------|--------------------------------|--------|
| 1 | 9:00am  | AREC Team Standup              | ✅ Notion |
| 2 | 10:30am | Northern Trust Diligence Call   | ✅ meeting-summaries/ |
| 3 | 1:00pm  | Contender Legal Review          | ❌ No notes |
| 4 | 3:00pm  | Fund II Investor Pipeline       | ❌ No notes |
| 5 | 4:30pm  | 1:1 with Tony                  | ❌ No notes |

3 meetings need notes. Ready to do a quick debrief?
```

If everything is covered, say so and you're done. If the user wants to skip certain meetings ("skip the standup, nothing happened"), respect that.

### Step 5: Debrief Each Gap — The Quiz

For each meeting without notes, walk the user through a structured but conversational debrief. Ask these questions one meeting at a time:

**Opening context** — Start by telling them what you know from the calendar (title, time, attendees if available from the calendar event). This helps jog their memory.

**The questions** (ask naturally, not as a rigid form):

1. **What was this about?** — "What was the main topic of the Contender Legal Review?" (One sentence is fine.)
2. **Who was there?** — "Who attended?" (If you already have attendees from the calendar invite, confirm: "I see Tony, Mike R, and Patrick were on the invite — anyone else, or did someone not show?")
3. **What got decided?** — "Were there any decisions made?" (Could be none — that's fine.)
4. **What are the action items?** — "Any follow-ups or to-dos that came out of this?" (Try to capture WHO owns each item.)
5. **Anything else worth noting?** — "Anything surprising, any open questions, or context I should remember?"

Adapt based on the meeting type. A quick 1:1 might only need questions 1, 4, and 5. A big deal review might warrant all of them plus follow-up questions. Use your judgment — the goal is to capture the substance without making it feel like an interrogation.

If the user gives terse answers, that's fine — work with what you get. If they give rich detail, capture it all.

### Step 6: Save the Meeting Summary

For each debriefed meeting, create a markdown file in `meeting-summaries/` using the standard format:

```markdown
# Meeting Title

**Date:** YYYY-MM-DD
**Source:** Debrief (calendar event)
**Attendees:** Name1, Name2, Name3

## Summary
Brief narrative summary of the meeting.

## Key Decisions
- Decision one
- Decision two

## Action Items
- [ ] **Person Name** — Task description
- [ ] **Person Name** — Task description

## Open Questions
- Question one
- Question two
```

Note the `**Source:** Debrief (calendar event)` — this distinguishes debrief-captured notes from Notion-sourced notes. The filename follows the same convention: `YYYY-MM-DD-meeting-title-slug.md`.

### Step 7: Surface Action Items for Task Tracking

After all debriefs are complete, collect all action items that belong to the user (Oscar) and present them:

```
## New Action Items for You

From today's debriefs, these look like tasks for your list:

1. From "Contender Legal Review" — Follow up with Mike R on Clifford Chance opinion
2. From "Fund II Investor Pipeline" — Send Northern Trust the updated deck

Add these to TASKS.md?
```

Only add to TASKS.md with the user's confirmation (per existing productivity system rules).

## Integration with /productivity:update

This skill is designed to run as a step within the broader productivity update flow. When `/productivity:update` runs:

1. After syncing tasks and triaging stale items (the existing flow)
2. Run this meeting debrief flow for today
3. Continue with the rest of the update

The update command's CLAUDE.md instructions already say to query Notion meeting notes on every run. This skill extends that by also checking the calendar and catching the gaps.

## Date Range Support

By default, check today only. But the user might say:

- "Debrief my meetings from yesterday" → check yesterday
- "Check the last 3 days for missing notes" → check a range
- "What about Monday?" → check a specific date

Adjust the `outlook_calendar_search` date range accordingly.

## Handling Edge Cases

- **Recurring meetings with the same title**: Match by date AND title, not just title.
- **Meetings the user declined or didn't attend**: If the calendar shows "declined" status, skip them. If unclear, ask: "I see 'Q3 Planning' on your calendar at 2pm — did you actually attend?"
- **Meetings already debriefed in a previous session**: Check `meeting-summaries/` first — if a file already exists for that date+meeting, it's covered.
- **User wants to skip everything**: Totally fine. "No worries — nothing to capture today."
