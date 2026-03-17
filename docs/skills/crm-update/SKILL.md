---
name: crm-update
description: "Full CRM update workflow that processes the shared inbox queue, scans Oscar's and Tony's Outlook email (4 passes), checks calendar for investor meetings, and processes meeting summaries — creating CRM activities, enriching contacts, and surfacing action items. Processes high-priority forwarded emails from crm@avilacapllc.com first. Trigger on: '/crm-update', 'CRM update', 'morning CRM update', 'run CRM update', 'update the CRM', 'process CRM queue', 'CRM morning routine', 'what's new in the pipeline', or any request to pull fresh intelligence into the CRM from email, calendar, and meeting notes. This is the comprehensive CRM refresh — use /email-scan for email-only, or /productivity:update for the full Overwatch cycle."
---

# CRM Update Workflow

Comprehensive CRM intelligence update that pulls from all available sources — the CRM shared mailbox (crm@avilacapllc.com), the Overwatch queue, email (Oscar + Tony), calendar, and meeting summaries — and routes everything into CRM activities, contact updates, meetings, and tasks.

Oscar runs this as his morning CRM refresh or after a batch of meetings/emails to keep the pipeline current.

## When to use this vs other update tools

| Command | What it does | Speed |
|---------|-------------|-------|
| `/crm-update` (this) | Full CRM refresh: shared inbox + queue + email + calendar + meetings → activities, contacts, tasks | ~2-3min |
| `/email-scan` | Email-only scan across Oscar + Tony → log matches silently | ~30s |
| `/email` | Process Oscar's curated `#productivity` folder interactively | ~2min |
| `/productivity:update` | Full Overwatch cycle: email + Notion + calendar + tasks + memory | ~3min |

## Error Reporting Policy

**Never silently skip a step.** If any step fails or is skipped, report it explicitly with:
1. Which step failed
2. The error message or reason
3. What data will be missing as a result

Example: "❌ Step 1 failed: drain_inbox.py returned exit code 1 (token expired). Shared mailbox items were NOT processed. They remain unread and will be picked up on the next run after re-auth."

## Prerequisites

Before starting, load CRM context:

1. Read `crm/config.md` — pipeline stages, AREC team roster (names + emails), delegate mailboxes
2. Build domain→org map: call `get_org_domains()` from `crm_reader.py` (returns `{domain: org_name}`)
3. Read `crm/email_log.json` — note `lastScan` timestamp and existing messageIds for dedup
4. Read `crm/ai_inbox_queue.md` — identify all entries with `Status: pending`
5. Read `crm/calendar_users.json` — list of email addresses for calendar scanning

## Workflow

Run steps 1-7 in order. Each step reports a summary before moving to the next.

---

### Step 1: Drain CRM Shared Mailbox (crm@avilacapllc.com) — HIGHEST PRIORITY

**This step MUST run first.** The shared mailbox contains emails that any AREC team member intentionally forwarded. These are always the highest-priority items. Any teammate — Oscar, Tony, Truman, Paige, anyone — can forward an email to `crm@avilacapllc.com` with a note, and it should be processed here.

**How to run:**
```bash
cd ~/Dropbox/projects/arec-crm && python3 app/drain_inbox.py
```
Or equivalently: `make inbox`

**What it does:**
1. Reads ALL unread messages from the `crm@avilacapllc.com` shared mailbox via Microsoft Graph API
2. For each message, parses the forwarder's intent note (text above the forward delimiter) and the original email content
3. Identifies who forwarded it from the envelope sender (`message.from.emailAddress`)
4. Writes structured entries to `crm/ai_inbox_queue.md` with `Source: crm-shared-mailbox`, `Priority: high`, and `ForwardedBy: {team member name}`
5. Marks each message as read and moves it to the `Processed` folder in the shared mailbox

**After drain completes,** read the newly-written queue entries and process them immediately in Step 2. These are the items that just arrived.

**If drain_inbox.py fails** (auth token expired, network error, running from Cowork instead of local terminal):
- Report: "❌ Step 1 failed: drain_inbox.py [error details]. Shared mailbox NOT processed — items remain unread. Requires local terminal with Graph auth token. Continuing with Step 2."
- Continue with Step 2. Do NOT skip the rest of the update.

Report: "🔴 Shared inbox: drained N new messages → queued for processing"

---

### Step 2: Process Queue (crm/ai_inbox_queue.md)

Process all pending items — both freshly drained shared inbox items (from Step 1) and any Overwatch-originated items.

1. Read all entries with `Status: pending` from `crm/ai_inbox_queue.md`
2. Sort: `Priority: high` items first, then by `Queued` timestamp (oldest first)
3. For each entry:

**High-priority items** (`Source: crm-shared-mailbox`):
- Display prominently: "🔴 **[ForwardedBy]** forwarded: **[Subject]**"
- Show the Summary field (this is the forwarder's intent note — their reason for forwarding)
- **Execute the forwarder's instructions.** The intent note often contains specific directions like "create new prospects," "log this interaction," "follow up with X." Do what it says.
- If `Org` is not "unknown": verify org exists in CRM, then create activity via `append_interaction()`:
  ```python
  append_interaction({
      "org": org_name,
      "type": "Email",
      "offering": best_matching_offering,
      "date": date_field,
      "Contact": contact_name,
      "Subject": subject,
      "Summary": "Forwarded by [ForwardedBy]: [intent note]. Original: [1-2 sentence summary]",
      "Source": "queue"
  })
  ```
- If `Org` is "unknown": ask Oscar — "This was forwarded by [name]. What org does this belong to? Or skip?"
  - If Oscar names an org: check if it exists → create if needed → create activity
  - If Oscar says skip: mark as `skipped`
- Update the entry in the queue file: set `Status: done`, `Processed: [ISO timestamp]`, `CRM Action: [what was done]`

**Normal-priority items** (Overwatch-originated, `Source: outlook-email` etc.):
- Display: "○ [Subject]"
- Same org verification and activity creation flow
- Same interactive triage for unknowns

Report: "Queue: processed N items (K high-priority, M normal, J skipped)"

---

### Step 3: Scan Emails (4-Pass)

Reuses the same patterns as `/email-scan` but additionally creates interaction records.

**Determine scan window:**
- If `lastScan` exists in `email_log.json`: scan from `lastScan` to now
- If `lastScan` is null (first run): scan last 14 days
- Cap at 14 days maximum

**Run four passes:**

| Pass | What | API call |
|------|------|----------|
| 1 | Oscar Archive (incoming) | `outlook_email_search(folderName: "Archive", afterDateTime: "{scanStart}", limit: 50)` |
| 2 | Oscar Sent Items (outgoing) | `outlook_email_search(folderName: "Sent Items", afterDateTime: "{scanStart}", limit: 50)` |
| 3 | Tony received (delegate) | `outlook_email_search(recipient: "tony@avilacapllc.com", afterDateTime: "{scanStart}", limit: 50)` |
| 4 | Tony sent (delegate) | `outlook_email_search(sender: "tony@avilacapllc.com", afterDateTime: "{scanStart}", limit: 50)` |

**Important:** Omit the `query` parameter entirely from all calls. Passing `"*"` causes a syntax error with the Microsoft 365 MCP connector.

**If a pass fails:** Report which pass failed and why, then continue with the next pass. Example: "❌ Pass 3 (Tony received) failed: permission denied. Skipping Tony incoming — those emails won't be scanned this run."

**Dedup across passes:** Same email thread may appear in multiple passes. Dedup by `internetMessageId` — first occurrence wins.

**For each email, apply skip rules (skip silently):**
- Already in `email_log.json` (dedup by messageId)
- All sender AND all recipients are internal AREC domains
- Calendar responses: subjects starting with "Accepted:", "Declined:", "Tentative:", "Canceled:"
- Auto-replies: "Automatic reply:", "Out of Office:"
- Read receipts and delivery failure notifications
- Newsletters/marketing: domains like sailthru, marketo, hubspot, mailchimp, constantcontact, e.inc.com, housingwire.com
- System notifications: Navan, Microsoft security, Juniper Square
- Internal Oscar↔Tony emails with no external participants
- No org match at either tier

**Internal AREC domains (never match as external prospects):**
- avilacapllc.com, avilacapital.com, encorefunds.com, builderadvisorgroup.com, south40capital.com

**Match emails to CRM orgs (two-tier):**

Tier 1 — Domain match (confidence 0.95):
- Extract domain from sender email (for incoming) or TO/CC domains (for sent)
- Check against org domain map from `get_org_domains()`

Tier 2 — Person match (confidence 0.90):
- Look up sender email in `contacts/*.md` via `find_person_by_email()`
- If person found with org → match to that org

No match → skip silently.

**Overlap handling:** If an email was already queued by Overwatch in `ai_inbox_queue.md` and also appears in the email scan, do NOT double-count. Queue processing (Step 2) takes precedence.

**For each matched email:**
1. Read full content via `read_resource(uri: "mail:///messages/{messageId}")`
2. Generate 1-2 sentence summary focused on key decision, commitment, or next step
3. Create interaction via `append_interaction()` with `Source: "email-scan"`
4. Add to email log via `add_emails_to_log()`

**Enrichment (runs after logging, same as /email-scan):**

(a) Org Domain Enrichment: If org has no Domain field, extract from sender email. Skip generic domains (gmail, yahoo) and internal AREC domains.

(b) Email History: Append to person files (`## Email History`) and org records (`**Email History:**`). Format: `- YYYY-MM-DD: Subject (incoming|outgoing)`. Dedup by (date, subject).

(c) Contact Email Discovery: Match display names to existing contacts, set email via `enrich_person_email()` if contact has no email.

Report: "Email: scanned N emails across 4 passes, M new matches (K domain, J person), P skipped"

---

### Step 4: Scan Calendar → Write to meetings.json

Pull Oscar's and Tony's calendars and upsert into the unified meeting store (`crm/meetings.json`). Read `crm/calendar_users.json` for the list of emails to scan.

```
outlook_calendar_search(
  query: "*",
  afterDateTime: "7 days ago",
  beforeDateTime: "30 days from now"
)
```

**For each event, determine if it's investor-relevant:**
1. Extract attendee email domains
2. Match against CRM org domain map (`get_org_domains()`)
3. Skip events where ALL attendees are internal AREC domains (avilacapllc.com, avilacapital.com, encorefunds.com, builderadvisorgroup.com, south40capital.com)
4. Skip obvious non-meetings: "Focus Time", "Lunch", "OOO", calendar holds with no attendees

**For each investor-relevant event, upsert into meetings.json:**
```python
save_meeting(
    org=matched_org_name,           # From domain match; "" if no match
    offering="AREC Debt Fund II",   # Default; adjust if event subject/body indicates otherwise
    meeting_date=event_date,        # YYYY-MM-DD
    meeting_time=event_time,        # HH:MM (24h)
    title=event_subject,
    attendees=comma_separated_names,
    source="calendar",
    graph_event_id=event_id,        # CRITICAL for dedup — the Graph event ID
    created_by="oscar"
)
```

`save_meeting()` handles dedup automatically:
- If `graph_event_id` already exists → returns existing meeting (no-op)
- If fuzzy match (same org + date ±1 day) with a `scheduled` meeting → attaches to it
- Otherwise → creates new meeting with status `scheduled`

**After upserting, report on the meetings:**

**Upcoming meetings (future):**
- Flag for meeting prep: show org status, pipeline stage, open tasks, last interaction
- "📅 Tomorrow: Meeting with Future Fund — Stage: 5. Interested — Last touch: 3 days ago"

**Past meetings without notes:**
- Load from `load_meetings(past_only=True)` where `notes_raw` is empty
- Flag: "⚠️ No debrief: [meeting title] on [date] with [org]. Want to add notes?"

**If `outlook_calendar_search` fails:** Report the error explicitly — do NOT silently skip. Show: "❌ Step 4 failed: outlook_calendar_search returned [error]. Calendar events were NOT synced to meetings.json. The Meetings tab will not reflect latest calendar state. Continuing with Step 5."

Report: "Calendar: N events scanned, M upserted to meetings.json, K upcoming (J need prep), L past without notes"

---

### Step 5: Process Meeting Notes → AI Insights

Check `crm/meetings.json` for meetings with `status: completed` that have `notes_raw` but no `notes_summary` (notes were attached but never AI-processed).

Also scan `meeting-summaries/` for files modified since `lastScan` (or last 14 days on first run). For each file:
1. Parse attendees → match to CRM orgs using domain map
2. Find or create matching meeting in `meetings.json` by org + date (use `save_meeting()` — dedup prevents duplicates)
3. Attach the file content as `notes_raw` via `update_meeting(meeting_id, notes_raw=content)`

**For meetings with unprocessed notes**, offer to run AI processing:
- "Found N meetings with notes but no AI summary. Process them now?"
- If yes: call `process_meeting_notes(meeting_id)` for each → generates summary + insights
- Insights enter the approval queue (visible on the Meetings page)

**For each processed meeting, also create an interaction:**
- `append_interaction()` with `Source: "meeting-summary"` so it appears in the interaction timeline
- Parse action items from notes: `- [ ] **Person** — task description`
- For each action item: offer to create CRM task via `add_prospect_task(org_name, text, owner)`

Report: "Meeting notes: N meetings with unprocessed notes, M processed with AI, K action items surfaced"

---

### Step 6: Stale Org Flagging

After all sources are processed, surface orgs going cold:
1. Load all interactions via `load_interactions()`
2. Find prospect orgs with no activity in 30+ days
3. Report: "⚠️ Stale orgs: [NEPC — 45 days], [Future Fund — 32 days]"

---

### Step 7: Final Summary

Report everything that happened, including any failures. Never omit a step from the summary.

```
CRM Update complete:
  - Shared inbox: N messages drained from crm@avilacapllc.com [or ❌ FAILED: reason]
  - Queue: M items processed (K high-priority, J normal, L skipped)
  - Email: P new matches across 4 passes [list any failed passes]
  - Calendar: Q events scanned, R upserted to meetings.json, S upcoming, T past without notes [or ❌ FAILED: reason]
  - Meeting notes: U with unprocessed notes, V processed with AI, W action items
  - Stale orgs: [list]
```

---

## Key CRM Functions Reference

All functions are in `app/sources/crm_reader.py`:

| Function | Purpose |
|----------|---------|
| `get_org_domains(prospect_only=False)` | Domain→org lookup map |
| `find_person_by_email(email)` | Contact lookup by email |
| `append_interaction(entry)` | Create activity record, auto-updates Last Touch |
| `load_email_log()` | Read email log + lastScan |
| `add_emails_to_log(emails)` | Append to log, handles dedup |
| `add_prospect_task(org, text, owner, priority, section)` | Create CRM task |
| `load_interactions(org, offering, limit)` | Read activity history |
| `get_contacts_for_org(org_name)` | List contacts for an org |
| `create_person_file(name, org, email, role, type)` | Create new contact |
| `enrich_person_email(slug, email)` | Add email to existing contact |
| `save_meeting(org, offering, meeting_date, ...)` | Create/dedup meeting in meetings.json (two-tier dedup) |
| `load_meetings(org, offering, status, future_only, past_only)` | Query meetings with filters |
| `update_meeting(meeting_id, **fields)` | Update meeting fields (notes_raw, status, etc.) |
| `process_meeting_notes(meeting_id)` | AI processing: notes → summary + insights (Claude API) |
| `approve_meeting_insight(meeting_id, insight_id, username)` | Approve insight → writes to prospect Notes |
| `dismiss_meeting_insight(meeting_id, insight_id, username)` | Dismiss insight |

## MCP Tools Used

- `outlook_email_search` — email search (folderName, sender, recipient, afterDateTime, limit)
- `outlook_calendar_search` — calendar search (query, afterDateTime, beforeDateTime)
- `read_resource` — read full email content by resource URI (use sparingly)

## Edge Cases

- **If drain_inbox.py fails:** Report the error with full details. Continue with Step 2. The shared mailbox items remain unread and will be picked up on the next run. Common cause: token expired — tell Oscar to re-auth via `python3 app/auth/graph_auth.py` from local terminal.
- **If Graph API is unavailable for email scan:** Report which passes failed. Process queue and meeting summaries only.
- **If a pass fails:** Report which pass and the error. Continue with remaining passes. Never abort the whole update because one pass failed.
- **If calendar scan fails:** Report the error. meetings.json will not reflect latest calendar. Continue with Step 5 (existing meetings.json data is still valid).
- **First run (14-day window):** May return 100+ emails. Match all, batch summaries 10 at a time.
- **Tony delegate access:** Already configured in `crm/config.md`. If permissions fail, report it and skip Tony passes.
- **Queue entries without Priority field:** Treat as `Priority: normal` (backward compatibility with older Overwatch entries).
- **drain_inbox.py auth:** Requires a valid Graph API token via `get_access_token()`. Only runs from local terminal — NOT from Cowork. If running from Cowork, report: "❌ drain_inbox.py requires local terminal with Graph auth. Skipping Step 1."
- **save_meeting() dedup:** If `graph_event_id` matches an existing meeting, `save_meeting()` returns the existing meeting without modification. This is expected behavior — it means the calendar event was already synced on a prior run.
