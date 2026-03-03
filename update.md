---
description: Sync tasks and refresh memory from your current activity
argument-hint: "[--comprehensive]"
---

# Update Command

> If you see unfamiliar placeholders or need to check which tools are connected, see [CONNECTORS.md](../CONNECTORS.md).

Keep your task list and memory current. Two modes:

- **Default:** Sync tasks from external tools, process Notion meeting transcripts, triage stale items, check memory for gaps
- **`--comprehensive`:** Deep scan chat, email, calendar, docs — flag missed todos and suggest new memories

## Usage

```bash
/productivity:update
/productivity:update --comprehensive
```

## Default Mode

### 1. Load Current State

Read `TASKS.md` and `memory/` directory. If they don't exist, suggest `/productivity:start` first.

### 2. Sync Tasks from External Sources

Check for available task sources:
- **Project tracker** (e.g. Asana, Linear, Jira) (if MCP available)
- **GitHub Issues** (if in a repo): `gh issue list --assignee=@me`

If no sources are available, skip to Step 3.

**Fetch tasks assigned to the user** (open/in-progress). Compare against TASKS.md:

| External task | TASKS.md match? | Action |
|---------------|-----------------|--------|
| Found, not in TASKS.md | No match | Offer to add |
| Found, already in TASKS.md | Match by title (fuzzy) | Skip |
| In TASKS.md, not in external | No match | Flag as potentially stale |
| Completed externally | In Active section | Offer to mark done |

Present diff and let user decide what to add/complete.

### 3. Sync Notion Meeting Transcripts

This step pulls meeting notes from Notion, summarizes them, extracts action items, and saves summaries as standalone markdown files. It runs every time — the deduplication logic ensures already-processed meetings are skipped.

#### 3a. Query recent meeting notes

Use the `notion-query-meeting-notes` tool to fetch meetings from the last 3 days:

```json
{
  "filter": {
    "operator": "and",
    "filters": [
      {
        "property": "created_time",
        "filter": {
          "operator": "date_is_within",
          "value": {
            "type": "relative",
            "value": "custom",
            "direction": "past",
            "unit": "day",
            "count": 3
          }
        }
      }
    ]
  }
}
```

This returns a list of meeting note pages with titles, URLs, and timestamps.

#### 3b. Check for already-processed meetings

The summary folder lives at `meeting-summaries/` inside the workspace (same directory as TASKS.md). Create it if it doesn't exist.

Before fetching any transcript, check the summary folder for an existing file matching that meeting. Summary filenames follow the pattern `YYYY-MM-DD-meeting-title-slug.md` (e.g., `2026-02-25-rxr-term-sheet-review.md`). If a file already exists for a meeting (match by date + fuzzy title), skip it — it's been processed.

#### 3c. Fetch and summarize each new meeting

For each unprocessed meeting:

1. **Fetch the full page** using `notion-fetch` with the meeting's URL and `include_transcript: true`. The content will contain the full transcript text.

2. **Produce a summary** by reading through the transcript and distilling it into a structured markdown file. The summary should capture what actually matters — not a mechanical list of every topic mentioned, but the key decisions, open questions, and commitments that came out of the meeting. Write it like a briefing for someone who missed the meeting.

   Use the user's memory (CLAUDE.md, memory/) to decode names, acronyms, and deal references so the summary is rich with context. For example, if someone says "DR Horton," note that they're a $50M LP and the largest public builder in the US. If "Jeannie" is mentioned, connect that to Jeanne Roig-Irwin at Clifford Chance.

   The summary file format:

   ```markdown
   # [Meeting Title]

   **Date:** YYYY-MM-DD
   **Source:** [Notion link](url)
   **Attendees:** (extract from transcript — names mentioned, people who spoke)

   ## Summary

   A concise 3-5 paragraph narrative of what was discussed, what was decided, and what's still open. Focus on decisions, context, and next steps rather than a blow-by-blow.

   ## Key Decisions

   - Decision 1
   - Decision 2

   ## Action Items

   - [ ] **[Person]** — Action item description (due date if mentioned)
   - [ ] **[Person]** — Another action item

   ## Open Questions

   - Question that wasn't resolved
   - Item deferred to a future discussion
   ```

3. **Save the summary** to `meeting-summaries/YYYY-MM-DD-meeting-title-slug.md`. Use a URL-friendly slug derived from the meeting title (lowercase, hyphens, no special chars).

#### 3d. Extract and propose action items

After processing all meetings, collect every action item across all new summaries. Cross-reference against TASKS.md to avoid duplicates (fuzzy match on description). Present the new ones to the user grouped by meeting:

```
## New Action Items from Meeting Transcripts

From "RXR Term Sheet Review" (Feb 25):
1. Tony to talk to Todd at Hillwood re: Nomura comfort level
2. Jeannie to respond to Nomura — socializing internally, will follow up
3. Zach to prep open items list for RXR call tomorrow

From "Family Office Partnership Discussion" (Feb 24):
1. Truman to send follow-up materials to prospect

Add these to TASKS.md? (I'll assign priority based on context)
```

Wait for user confirmation before adding anything to TASKS.md. When adding, follow the existing TASKS.md format (`- [ ] **[Priority]** Description`) and assign priority (Hi/Med/Low) based on context — urgency, who it involves, deadlines mentioned.

#### 3e. Report meeting sync results

Include in the final report:
```
- Meetings: 5 found, 3 new summaries saved, 2 already processed
- Action items: 7 extracted, 4 new (3 already tracked)
- Summaries: meeting-summaries/
```

### 4. Triage Stale Items

Review Active tasks in TASKS.md and flag:
- Tasks with due dates in the past
- Tasks in Active for 30+ days
- Tasks with no context (no person, no project)

Present each for triage: Mark done? Reschedule? Move to Someday?

### 5. Decode Tasks for Memory Gaps

For each task, attempt to decode all entities (people, projects, acronyms, tools, links):

```
Task: "Send PSR to Todd re: Phoenix blockers"

Decode:
- PSR → ✓ Pipeline Status Report (in glossary)
- Todd → ✓ Todd Martinez (in people/)
- Phoenix → ? Not in memory
```

Track what's fully decoded vs. what has gaps.

### 6. Fill Gaps

Present unknown terms grouped:
```
I found terms in your tasks I don't have context for:

1. "Phoenix" (from: "Send PSR to Todd re: Phoenix blockers")
   → What's Phoenix?

2. "Maya" (from: "sync with Maya on API design")
   → Who is Maya?
```

Add answers to the appropriate memory files (people/, projects/, glossary.md).

### 7. Capture Enrichment

Tasks often contain richer context than memory. Extract and update:
- **Links** from tasks → add to project/people files
- **Status changes** ("launch done") → update project status, demote from CLAUDE.md
- **Relationships** ("Todd's sign-off on Maya's proposal") → cross-reference people
- **Deadlines** → add to project files

Meeting summaries are a particularly rich source of enrichment. When processing transcripts, also look for:
- **New people** mentioned but not in memory — flag for Step 6
- **Deal updates** (status changes, new terms, decisions) — update project files
- **New relationships** between people and deals — cross-reference

### 8. Report

```
Update complete:
- Tasks: +3 from project tracker (e.g. Asana), 1 completed, 2 triaged
- Meetings: 5 found, 3 new summaries saved to meeting-summaries/
- Action items: 7 extracted from transcripts, 4 new
- Memory: 2 gaps filled, 1 project enriched
- All tasks decoded ✓
```

### 9. CRM Pulse Check

After all task and memory work is done, run a quick CRM check. Read:

- `crm/prospects.md` — filter to **High urgency** prospects at active stages (5–8)
- `crm/interactions.md` — last touch date per org
- `crm/pending_interviews.json` — orgs awaiting post-meeting intel debrief
- `memory/people/` — existence check only (has an intel file or not)

Surface **at most 2 observations** inline in the output. Not a report — 2–3
sentences max, specific and actionable.

**Observation selection priority (use the first 2 that qualify):**

1. **Pending post-meeting debriefs** — highest priority, time-sensitive while fresh
   > ⚡ **[Org]** You had a meeting on [date] — want to do a quick intel debrief
   > while it's fresh? (5–10 min via /crm:interview)

2. **High urgency with no Next Action set**
   > ⚡ **[Org]** is at [stage] with no Next Action set and last touch [N] days ago.
   > Want to add a follow-up task or do a quick intel capture?

3. **High urgency with last touch > 14 days**
   > ⚡ **[N] High urgency prospects** last touched over 14 days ago:
   > [Org1] ([N]d), [Org2] ([N]d), [Org3] ([N]d).

4. **High urgency with no intel file**
   > ⚡ **[Org]** has no intel file. Worth a 5-minute debrief (/crm:interview)
   > before the next outreach?

5. **High urgency with intel file > 30 days old**
   > ⚡ **[Org]** intel file is [N] days old — you've had [N] interactions since.
   > Worth a quick delta update (/crm:interview)?

**Rules:**
- Never surface more than 2 observations per update
- If nothing qualifies, omit the CRM Pulse section entirely — do not manufacture filler
- If pending debriefs exist, always surface them first and offer to start the interview
  immediately in this session
- After a debrief completes and the intel file is written, remove the org from
  `crm/pending_interviews.json`

## Comprehensive Mode (`--comprehensive`)

Everything in Default Mode, plus a deep scan of recent activity.

### Extra Step: Scan Activity Sources

Gather data from available MCP sources:
- **Chat:** Search recent messages, read active channels
- **Email:** Search sent messages
- **Documents:** List recently touched docs
- **Calendar:** List recent + upcoming events

### Extra Step: Flag Missed Todos

Compare activity against TASKS.md. Surface action items that aren't tracked:

```
## Possible Missing Tasks

From your activity, these look like todos you haven't captured:

1. From chat (Jan 18):
   "I'll send the updated mockups by Friday"
   → Add to TASKS.md?

2. From meeting "Phoenix Standup" (Jan 17):
   You have a recurring meeting but no Phoenix tasks active
   → Anything needed here?

3. From email (Jan 16):
   "I'll review the API spec this week"
   → Add to TASKS.md?
```

Let user pick which to add.

### Extra Step: Suggest New Memories

Surface new entities not in memory:

```
## New People (not in memory)
| Name | Frequency | Context |
|------|-----------|---------|
| Maya Rodriguez | 12 mentions | design, UI reviews |
| Alex K | 8 mentions | DMs about API |

## New Projects/Topics
| Name | Frequency | Context |
|------|-----------|---------|
| Starlight | 15 mentions | planning docs, product |

## Suggested Cleanup
- **Horizon project** — No mentions in 30 days. Mark completed?
```

Present grouped by confidence. High-confidence items offered to add directly; low-confidence items asked about.

## Notes

- Never auto-add tasks or memories without user confirmation
- External source links are preserved when available
- Fuzzy matching on task titles handles minor wording differences
- Safe to run frequently — only updates when there's new info
- Meeting summaries are deduplicated by date + title, so repeated runs won't create duplicates
- `--comprehensive` always runs interactively
