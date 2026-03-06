---
name: Email Log Update
trigger: Post-update extension (automatic)
description: Scan Archive + Sent Items since lastScan, match emails to CRM orgs via domain/person lookup, append to crm/email_log.json with summaries + Outlook links.
---

# Email Log Update (Post-Update Extension 2)

## When This Runs
- Automatically after every `/productivity:update` (default and `--comprehensive`)
- Can also be triggered manually: "scan emails for CRM", "update email log"

## Deep Scan (Per-Org, On-Demand)
A separate 90-day deep scan per org is available via the **⟳ Deep Scan (90d)** button on each prospect's detail page in the dashboard. Use that for thorough historical backfill. This skill handles the incremental daily scan only.

## Prerequisites
- CRM context loaded (organizations with Domain field, contacts_index, people files)
- `crm/email_log.json` exists (created on first run if missing)

## Workflow

### Step 1: Load Context
1. Read `crm/email_log.json` — note `lastScan` timestamp
2. Load org domains for prospect orgs only: Use `get_org_domains(prospect_only=True)` from `crm_reader.py`
   - Returns only orgs with active prospects AND a Domain field
   - Excludes service providers (law firms, placement agents, fund admin)
   - Excludes generic domains (gmail, yahoo, etc.) and internal AREC domains
   - Build lookup map: `{domain: org_name}` (e.g., `{"nepc.com": "NEPC"}`)
3. Load `crm/contacts_index.md` and `memory/people/` for person-to-org mapping fallback

### Step 2: Determine Scan Window
- If `lastScan` is null (first run): scan last 14 days
- If `lastScan` exists: scan from `lastScan` date to now
- Cap at 14 days maximum to keep incremental scans fast

### Step 3: Broad Scan (Two Passes)
Do a single broad pull — do NOT query per org/domain. Let the matching step handle attribution.

**Pass 1 — Archive (incoming):**
```
outlook_email_search(
  query: "*",
  folderName: "Archive",
  afterDateTime: "{scanStart}",
  limit: 50
)
```

**Pass 2 — Sent Items (outgoing):**
```
outlook_email_search(
  query: "*",
  folderName: "Sent Items",
  afterDateTime: "{scanStart}",
  limit: 50
)
```

Collect all email metadata (subject, sender, recipients, date, messageId URI).

### Step 4: Match Emails to Orgs (Two-Tier)

For each email, try matching in this order:

**Tier 1 — Domain Match (fast, ~95% confidence):**
1. Extract domain from sender email: `mtreveloni@nepc.com` → `nepc.com`
2. Check against org domain map
3. If match found: `matchType = "domain"`, `confidence = 0.95`
4. For sent emails, match TO/CC recipient domains instead

**Tier 2 — Person Match (medium, ~90% confidence):**
1. If no domain match, look up sender email in `memory/people/` via `find_person_by_email()`
2. If person found and has an org: `matchType = "person"`, `confidence = 0.90`

**No match → Skip.** Only log emails with a clear CRM org match.

**Skip rules:**
- Skip if sender domain is internal (avilacapllc.com, avilacapital.com) AND no external recipient matches
- Skip if messageId already exists in email_log.json (dedup)
- Skip calendar invites, read receipts, automated notifications (subjects: "Accepted:", "Declined:", "Automatic reply:", delivery failures)

### Step 5: Enrich Matched Emails

For each matched email:

1. **Read full content** via MCP:
```
read_resource(uri: "mail:///messages/{messageId}")
```

2. **Generate summary** (1-2 sentences):
   - "Summarize this fundraising/investor email in 1-2 sentences. Focus on the key decision, commitment, concern, or next step."

3. **Build Outlook web URL:**
```
https://outlook.office365.com/mail/id/{URL-encoded messageId}
```

4. **Construct log entry:**
```json
{
  "messageId": "...",
  "date": "2026-03-04",
  "timestamp": "2026-03-04T09:15:00Z",
  "subject": "Re: AREC Fund II Follow-up",
  "from": "mtreveloni@nepc.com",
  "fromName": "Matt Treveloni",
  "to": ["oscar@avilacapllc.com"],
  "orgMatch": "NEPC",
  "matchType": "domain",
  "confidence": 0.95,
  "summary": "NEPC declining to re-engage on Fund II due to capacity; will revisit Q3.",
  "outlookUrl": "https://outlook.office365.com/mail/id/..."
}
```

### Step 6: Save to Log
- Call `add_emails_to_log(new_entries)` — handles dedup by messageId
- Updates `lastScan` timestamp automatically

### Step 7: Report
```
Email scan complete:
- Window: {scanStart} to now
- New matches: {count_added} ({domain_matches} domain, {person_matches} person)
- Skipped (already logged): {dedup_count}
- Email log total: {total_in_log} entries
```

## Edge Cases
- **Archive folder:** Oscar keeps Inbox Zero — all received emails are in Archive, not Inbox.
- **Rate limits:** If `outlook_email_search` returns errors, log warning and continue with partial results.
- **First run (14-day window):** May return 100+ emails. Match all, batch summaries 10 at a time.
- **Per-org deep history:** Use the ⟳ Deep Scan button on the Prospect detail page (searches 90 days back using Microsoft Graph KQL search across Archive + Sent Items).
