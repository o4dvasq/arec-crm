---
name: email-scan
description: "Quick incremental scan of Oscar's and Tony's Outlook email against CRM prospect orgs. Runs 5 passes (Oscar Archive, Oscar Sent, Tony received, Tony sent, CRM shared mailbox), matches to orgs via domain/person lookup, logs to crm/email_log.json, enriches org domains + people email history + contact emails, and reports a summary table. Much faster than /productivity:update — no Notion, no calendar, no task triage. Trigger on: '/email-scan', 'scan emails', 'email scan', 'check emails for CRM', 'fold emails into context', 'process recent emails', 'quick email sweep', 'email refresh for CRM', or any request to scan recent Outlook email for CRM intelligence without running a full update. Do NOT confuse with /email which processes the #productivity folder interactively."
---

# Email Scan — Lightweight CRM Email Logger

Fast, focused email scan that logs CRM-relevant emails and enriches contact data. This is the email-only slice of `/productivity:update` — no Notion queries, no calendar checks, no task triage.

Oscar uses this after processing a batch of important emails or when he wants to quickly fold recent email activity into CRM context without the overhead of a full update cycle.

## When to use this vs other email tools

| Command | What it does | Speed |
|---------|-------------|-------|
| `/email-scan` (this) | Broad scan of all recent email across Oscar + Tony mailboxes → log matches silently | ~30s |
| `/email` | Process Oscar's curated `#productivity` folder — interactive quiz on unknowns | ~2min |
| `/productivity:update` | Full cycle: email + Notion + calendar + tasks + memory | ~3min |

## Workflow

### Step 1: Load Context

Read these files to build the matching context:

1. `crm/email_log.json` — note `lastScan` timestamp
2. `crm/organizations.md` — extract org names + Domain fields for prospect orgs
   - Build lookup map: `{domain: org_name}` (e.g., `{"nepc.com": "NEPC"}`)
   - Skip generic email domains (gmail.com, yahoo.com, outlook.com, hotmail.com, icloud.com)
   - Skip internal domains: avilacapllc.com, avilacapital.com, encorefunds.com, builderadvisorgroup.com
3. `crm/contacts_index.md` — for person-email-to-org fallback
4. Scan `memory/people/` filenames — know which people have files for enrichment

### Step 2: Determine Scan Window

- If `lastScan` is null (first run): scan last 14 days
- If `lastScan` exists: scan from `lastScan` to now
- Cap at 14 days maximum to keep it fast

### Step 3: Run Five Passes

Launch these in parallel when the tool allows it. The five passes cover Oscar's, Tony's, and the shared CRM mailboxes.

**Pass 1 — Oscar Archive (incoming):**
```
outlook_email_search(
  folderName: "Archive",
  afterDateTime: "{scanStart}",
  limit: 50
)
```
Important: omit the `query` parameter entirely. Passing `"*"` causes errors with this API.

**Pass 2 — Oscar Sent Items (outgoing):**
```
outlook_email_search(
  folderName: "Sent Items",
  afterDateTime: "{scanStart}",
  limit: 50
)
```

**Pass 3 — Tony received:**
Oscar has delegate access to tony@avilacapllc.com.
```
outlook_email_search(
  recipient: "tony@avilacapllc.com",
  afterDateTime: "{scanStart}",
  limit: 50
)
```

**Pass 4 — Tony sent:**
```
outlook_email_search(
  sender: "tony@avilacapllc.com",
  afterDateTime: "{scanStart}",
  limit: 50
)
```

**Pass 5 — CRM shared mailbox (crm@avilacapllc.com):**
This is a shared mailbox. Oscar may not yet have the permissions configured for API access — if this pass fails, log a warning and move on.
```
outlook_email_search(
  recipient: "crm@avilacapllc.com",
  afterDateTime: "{scanStart}",
  limit: 50
)
```

If any pass fails (permissions, timeout), log a warning and continue with partial results. Never abort the whole scan because one pass failed.

### Step 4: Match Emails to Orgs

For each email across all four passes, try matching in order:

**Tier 1 — Domain Match (confidence 0.95):**
Extract domain from sender email (or recipient domains for sent items). Look up in org domain map.

**Tier 2 — Person Match (confidence 0.90):**
If no domain match, look up sender/recipient email in `contacts_index.md` or `memory/people/`. If person has a known org, use that.

**Skip these silently — no logging, no reporting:**
- Both sender AND all recipients are internal AREC domains (internal coordination)
- Calendar responses: subjects starting with "Accepted:", "Declined:", "Tentative:", "Canceled:"
- Auto-replies: subjects starting with "Automatic reply:", "Out of Office:"
- Read receipts and delivery failures
- Newsletters and marketing: domains like sailthru.com, marketo.org, hubspot, mailchimp, constantcontact, e.inc.com, housingwire.com, etc.
- Navan expense notifications, Microsoft security alerts, Juniper Square automated notifications
- messageId already exists in email_log.json (dedup)
- No org match at either tier — skip unknowns silently

**Dedup across passes:** Same thread may appear in multiple passes. Dedup by `internetMessageId` — first occurrence wins.

### Step 5: Build Log Entries

For each matched email, construct a log entry:

```json
{
  "messageId": "...",
  "date": "2026-03-11",
  "timestamp": "2026-03-11T09:15:00Z",
  "subject": "Re: Fund II Follow-up",
  "from": "mtreveloni@nepc.com",
  "fromName": "Matt Treveloni",
  "to": ["oscar@avilacapllc.com"],
  "orgMatch": "NEPC",
  "matchType": "domain",
  "confidence": 0.95,
  "summary": "NEPC declining to re-engage on Fund II due to capacity; will revisit Q3."
}
```

For the summary field: write 1-2 sentences focused on the key decision, commitment, concern, or next step. If the email metadata summary is clear enough, use that rather than reading the full email body — this keeps the scan fast.

Only read full email content via `read_resource(uri)` when the metadata summary is too vague to write a useful CRM summary (e.g., just a signature block, or the summary is truncated mid-sentence).

### Step 6: Save to Log

Append new entries to `crm/email_log.json` entries array. Update `lastScan` to current timestamp (ISO 8601 UTC).

### Step 7: Enrichment

Three idempotent enrichment passes — safe to run repeatedly:

**(a) Enrich Org Domains:**
For each matched org where `organizations.md` has no `Domain` field, extract the domain from the external sender email and add it. Skip generic domains.

**(b) Append Email History to People Files:**
For each matched email, if the sender/recipient has a file in `memory/people/`:
- Find or create a `## Email History` section
- Append: `- 2026-03-11: Re: Fund II Follow-up (incoming)`
- Dedup by (date, subject) — don't add duplicates

**(c) Discover Contact Emails:**
For each email address in matched emails:
1. Extract domain — if it matches the org's Domain in organizations.md
2. Check if any contacts for that org are missing email addresses
3. Try matching display name to existing contacts by first/last name
4. If match found and contact has no email, add it

### Step 8: Report

Present a concise summary:

```
Email scan complete:
- Window: Mar 11 02:00 → now
- Passes: 5/5 succeeded (or N/5 if CRM shared mailbox not yet permissioned)
- New matches: 4 (3 domain, 1 person)
- Skipped: 12 already logged, 38 no match/internal
- Enrichment: 1 domain added, 2 history entries, 0 contact emails
- Log total: 19 entries
```

Then a table of new matches (the most important part):

| Date | Org | From/To | Subject | Dir |
|------|-----|---------|---------|-----|
| 03-11 | Mass Mutual | Jessica Li | RE: AREC Debt Fund II | ← |
| 03-11 | Alpha Group | Benjamin Southgate | RE: Avila / Alpha Group | ← |

If zero new matches: "No new CRM-relevant emails since last scan ({lastScan})."

## Edge Cases

- **First run (14-day window):** May return 100+ emails. Match all, but batch enrichment 10 at a time.
- **Rate limits:** If outlook_email_search returns errors, continue with partial results and note in report.
- **Tony delegate access:** Passes 3-4 use recipient/sender filters rather than folderName. If permissions fail, skip those passes and warn.
- **CRM shared mailbox:** Pass 5 scans crm@avilacapllc.com. This requires shared mailbox permissions which may not be configured yet. If it fails, log a warning and continue — don't retry or prompt Oscar about it.
- **Large threads:** If multiple emails share a thread, log only the most recent one.
- **Encore emails:** Tony also uses tony@encorefunds.com — emails from encorefunds.com domains are internal, not external prospect matches.
