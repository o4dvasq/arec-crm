SPEC: CRM Update Workflow
Project: arec-crm
Date: 2026-03-15
Updated: 2026-03-16 (audit pass — verified all dependencies, enhanced skip rules and email-scan overlap guidance)
Status: Ready for implementation

---

## 1. Objective

Build a `/crm-update` Cowork skill for arec-crm that processes incoming intelligence from multiple sources — the Overwatch ingress queue, Microsoft Graph (Oscar's and Tony's Outlook email + calendar), and meeting summaries — and routes them into the CRM as org activities, contact updates, pipeline events, and tasks. This is the CRM-side counterpart to Overwatch's `/update` ingress pipeline.

## 2. Scope

### In scope

- Consume the shared queue (`crm/ai_inbox_queue.md`) written by Overwatch's ingress pipeline
- Pull Microsoft Graph email for Oscar (Archive, Sent Items) — overlaps with Overwatch but applies CRM-specific processing
- Pull Microsoft Graph email for Tony (delegate access — received and sent) — CRM-only source
- Pull Microsoft Graph calendar for Oscar — identify investor meetings for meeting prep and follow-up
- Read meeting summaries from `meeting-summaries/` directory
- Match all items to CRM orgs and contacts
- Create/update CRM activities, contact notes, pipeline events
- Mark queue items as processed (`done` or `skipped`)
- Maintain `crm/email_log.json` as an audit trail of all processed emails
- Interactive triage for unmatched items (new orgs, unknown contacts)
- Enrich CRM org files with new domains, contacts, and email history

### Out of scope

- Overwatch ingress pipeline (see SPEC_multi-source-ingress.md)
- iCloud or Gmail scanning (personal sources — Overwatch only)
- Direct writes to Overwatch TASKS.md (one-way queue; Overwatch owns its own tasks)
- Automated CRM record creation without user confirmation
- Tony's CRM Excel tracker (DEFERRED — no Excel file found; see §4 note)
- Building a web UI for the CRM update (this is a Cowork skill / interactive workflow)
- People files in Overwatch's `memory/people/` — this skill enriches CRM contacts only, not Overwatch people files

## 3. Business Rules

### Sources and what they provide

| Source | Auth | What's pulled |
|--------|------|---------------|
| Overwatch queue (`crm/ai_inbox_queue.md`) | Filesystem (Dropbox sync) | Pre-classified CRM items from Overwatch ingress |
| Oscar's Outlook email | Microsoft 365 MCP connector | Oscar's Archive + Sent Items with investor/deal content |
| Tony's Outlook email | Microsoft 365 MCP (delegate: tavila@avilacapllc.com) | Tony's investor outreach, meeting scheduling, deal comms |
| Oscar's Outlook calendar | Microsoft 365 MCP connector | Investor meetings for prep/follow-up detection |
| Meeting summaries | Filesystem (`meeting-summaries/`) | Post-meeting notes with action items |

### Queue consumption rules

- Read `crm/ai_inbox_queue.md` for all entries with `Status: pending`
- For each entry:
  1. Look up the `Org` field against CRM org records
  2. If org found: create activity record on the org, update contact if identified
  3. If org NOT found: present to Oscar — "New org? Create it?" or "Skip?"
  4. Update entry status to `done` (processed) or `skipped` (user chose to ignore)
- Never delete queue entries — status changes only (audit trail)

### Email scanning (4-pass model)

| Pass | Mailbox | Direction | API call |
|------|---------|-----------|----------|
| 1 | Oscar Archive | Incoming | `outlook_email_search(folderName: "Archive", afterDateTime: scanStart, limit: 50)` |
| 2 | Oscar Sent Items | Outgoing | `outlook_email_search(folderName: "Sent Items", afterDateTime: scanStart, limit: 50)` |
| 3 | Tony received | Incoming | `outlook_email_search(recipient: "tony@avilacapllc.com", afterDateTime: scanStart, limit: 50)` |
| 4 | Tony sent | Outgoing | `outlook_email_search(sender: "tony@avilacapllc.com", afterDateTime: scanStart, limit: 50)` |

**Important API notes:**
- Omit the `query` parameter entirely from all calls. Passing `"*"` causes errors with the Microsoft 365 MCP connector.
- If any pass fails (permissions, timeout), log a warning and continue with partial results. Never abort the whole scan because one pass failed.

**Note:** Oscar has been granted delegate access to Tony's mailbox (confirmed in `crm/config.md` → `## Delegate Mailboxes`). No additional setup required.

### Relationship to existing `/email-scan` skill

An existing `/email-scan` skill at `~/.skills/skills/email-scan/SKILL.md` already implements a 5-pass email scan (the 4 passes above plus a CRM shared mailbox pass) with matching, logging, and enrichment. The `/crm-update` skill should **reuse the same patterns** from `/email-scan` for Step 3 (email scanning) and Step 7 (enrichment). Key differences:

- `/crm-update` runs 4 passes (no CRM shared mailbox — out of scope for this iteration)
- `/crm-update` creates `interactions.md` activities for matched emails (email-scan only logs)
- `/crm-update` additionally processes queue items, calendar, and meeting summaries
- `/email-scan` enriches Overwatch `memory/people/` email history; `/crm-update` does NOT touch Overwatch files

### Email matching tiers (CRM-specific)

**Tier 1: Domain match (confidence 0.95)**
- Match sender/recipient domain against `crm/organizations.md` Domain field via `get_org_domains()`
- Example: `mtreveloni@nepc.com` → domain `nepc.com` → org "NEPC"

**Tier 2: Person match (confidence 0.90)**
- Match sender email against `contacts/*.md` via `find_person_by_email()`
- Example: contact file with `Email: susannahfriar@wirral.gov.uk` → org "Merseyside Pension Fund"

**No match → skip.** Only log emails with a clear CRM org match.

### Skip rules (comprehensive — aligned with /email-scan)

Skip these silently — no logging, no reporting:

- All sender AND all recipients are internal AREC domains (internal coordination)
- messageId already exists in `email_log.json` (dedup)
- Calendar responses: subjects starting with "Accepted:", "Declined:", "Tentative:", "Canceled:"
- Auto-replies: subjects starting with "Automatic reply:", "Out of Office:"
- Read receipts and delivery failure notifications
- Newsletters and marketing: domains like sailthru.com, marketo.org, hubspot, mailchimp, constantcontact, e.inc.com, housingwire.com, etc.
- Automated system notifications: Navan expense notifications, Microsoft security alerts, Juniper Square automated notifications
- Internal Tony↔Oscar emails with no external participants
- No org match at either tier — skip unknowns silently

**Internal domains (all are AREC-internal, not external prospect matches):**
- avilacapllc.com
- avilacapital.com
- encorefunds.com (Tony also uses tony@encorefunds.com)
- builderadvisorgroup.com
- south40capital.com

**Dedup across passes:** Same thread may appear in multiple passes. Dedup by `internetMessageId` — first occurrence wins.

### Meeting summary processing

- Scan `meeting-summaries/` for files modified since last email scan (or last 14 days)
- Parse each summary for: org names (from attendees field), action items (from `## Action Items`)
- For each identified org: append interaction to `crm/interactions.md`
- For each action item (`- [ ] **Person** — task`): offer to create CRM task via `add_prospect_task()`

## 4. Data Model

### Queue contract (shared with Overwatch — MUST stay in sync)

The queue file at `crm/ai_inbox_queue.md` uses this format:

```markdown
# AI Inbox Queue

Items classified as CRM-relevant by Overwatch ingress. Processed by `/crm-update`.

## YYYY-MM-DD

### [Subject Line]
- **Source:** outlook-email | outlook-calendar | icloud-reminder | gmail-email
- **From:** [Sender Name] <[email]>
- **To:** [recipient1], [recipient2]
- **Date:** [ISO 8601 timestamp]
- **Org:** [matched org name or "unknown"]
- **Contact:** [matched contact name or "(unknown — needs CRM lookup)"]
- **Match:** [domain | person | keyword | ai | manual] (confidence: [0.0-1.0])
- **Summary:** [1-2 sentence summary of content]
- **Status:** pending | processing | done | skipped
- **Queued:** [ISO 8601 timestamp — when Overwatch wrote this entry]
- **Processed:** [ISO 8601 timestamp — when CRM processed, blank if pending]
- **CRM Action:** [what CRM did — blank if pending]
```

Status lifecycle: `pending` → `processing` → `done` or `skipped`
- Only Overwatch writes `pending` entries
- Only arec-crm transitions to `processing`, `done`, or `skipped`

### Email log: `crm/email_log.json`

Managed by crm_reader.py functions: `load_email_log()`, `add_emails_to_log(emails)`, `find_email_by_message_id(id)`.

```json
{
  "version": 1,
  "lastScan": "2026-03-11T13:00:00Z",
  "emails": [
    {
      "messageId": "<message-id-string>",
      "date": "2026-03-15",
      "timestamp": "2026-03-15T12:59:04Z",
      "subject": "UTIMCO request",
      "from": "tony@avilacapllc.com",
      "fromName": "Tony Avila",
      "to": ["oscar@avilacapllc.com"],
      "cc": [],
      "orgMatch": "UTIMCO",
      "matchType": "domain",
      "confidence": 0.95,
      "summary": "Brief 1-2 sentence summary of email content.",
      "outlookUrl": "https://outlook.office365.com/mail/id/{encoded-id}"
    }
  ]
}
```

**Current state:** `lastScan` is `2026-03-11T13:00:00Z`. The log already contains entries from prior `/email-scan` runs.

### Org record structure

Location: `crm/organizations.md`
Format: `## Org Name` sections with bullet fields

```markdown
## NEPC
- **Type:** Investment Consultant
- **Aliases:** New England Pension Consultants
- **Domain:** @nepc.com
- **Contacts:** Matt Treveloni, Emily Andrews
- **Stage:** (pipeline stage — optional, usually on prospect record)
- **Notes:** Free-text notes, email history entries
```

Read via: `load_organizations()`, `get_organization(name)`
Write via: `write_organization(name, data)` — canonical field order: Type, Aliases, Domain, Contacts, Stage, Notes
Domain map: `get_org_domains(prospect_only=False)` → `{"nepc.com": "NEPC", ...}`

### Contact record structure

Location: `contacts/<slug>.md` (e.g., `contacts/susannah-friar.md`)
Format:

```markdown
# Susannah Friar

## Overview
- **Organization:** Merseyside Pension Fund
- **Role:** Investment Officer
- **Email:** susannahfriar@wirral.gov.uk
- **Phone:**
- **Type:** investor
```

Index: `crm/contacts_index.md` — maps org names to contact slugs:
```markdown
- Merseyside Pension Fund: susannah-friar, dragos-serbanica
```

Read via: `load_person(slug)`, `get_contacts_for_org(org_name)`, `find_person_by_email(email)`
Write via: `create_person_file(name, org, email, role, person_type)` → returns slug
       `enrich_person_email(slug, email)` — update email only
       `add_contact_to_index(org, slug)` — add to index

### Activity (Interaction) record structure

Location: `crm/interactions.md`

```markdown
## 2026-03-10

### UTIMCO - Hedge Fund — Meeting — AREC Debt Fund II
- **Contact:** Jared Brimberry
- **Subject:** Reference call with Hillwood's Fred Balda
- **Summary:** Tony introduced Hillwood as a due diligence reference to address UTIMCO's left-tail risk concerns. Jared and Danny Ellis will meet at Executive Forum Mar 24.
- **Source:** meeting-summary
```

Fields: Contact, Subject, Summary, Source
Types: Email, Meeting, Call, Note
Source values: `email-scan`, `meeting-summary`, `queue`, `manual`
Write via: `append_interaction(entry)` — auto-updates prospect's `Last Touch`

`entry` dict keys: `org`, `type`, `offering`, `date`, `Contact`, `Subject`, `Summary`, `Source`

### Task record structure

Location: `TASKS.md` at project root

```
- [ ] **[Med]** Follow up on deck request (NEPC) — assigned:Oscar
- [ ] **[Hi]** Schedule call [org: UTIMCO - Hedge Fund] [owner: Tony]
```

Two formats coexist; prefer the tagged format for new entries:
```
- [ ] **[{priority}]** {text} — [org: {org_name}] [owner: {owner}]
```

Write via: `add_prospect_task(org_name, text, owner, priority="Med", section="IR / Fundraising")`
Priority values: Hi, Med (default), Lo
Owner values: first name of any AREC team member from `crm/config.md` → `## AREC Team` (Oscar, Tony, Truman, Zach, Nate, Patrick, Mike, Sahil, Jake, Kevin, Jane, Anthony, Ian, James, Paige)

### Pipeline stages (from `crm/config.md`)

```
0. Declined       (terminal — excluded from active pipeline)
1. Prospect
2. Cold
3. Outreach
4. Engaged
5. Interested
6. Verbal         } committed stages — count toward fund totals
7. Legal / DD     }
8. Closed         }
```

Stage update: `update_prospect_field(org, offering, 'Stage', "4. Engaged")`
Offering examples: "AREC Debt Fund II" (from `crm/offerings.md`)

### Tony's Excel tracker — DEFERRED

**Finding:** No Excel pipeline tracker found in the repo. "Tony All Contacts.CSV" in the project root is an Outlook contacts export, not a deal tracking sheet.

**Resolution:** This feature is deferred until Tony's Excel file path is identified. If a path is configured in `crm/config.md` under `## Excel Tracker`, the skill will read it. Otherwise this step is skipped with a note.

**Placeholder config format (for when available):**
```markdown
## Excel Tracker
- Path: /path/to/tony-pipeline-tracker.xlsx
- Sheet: Pipeline
```

## 5. UI / Interface

This is a Cowork skill (`/crm-update`), not a web UI feature. The interface is the interactive conversation.

### Update flow

```
/crm-update
  │
  ├── 1. Load CRM state
  │   ├── Read crm/config.md (pipeline stages, team, delegate mailboxes)
  │   ├── Build domain→org map via get_org_domains()
  │   ├── Read crm/email_log.json (lastScan + processed IDs)
  │   └── Read crm/ai_inbox_queue.md (pending items from Overwatch)
  │
  ├── 2. Process queue (crm/ai_inbox_queue.md)
  │   ├── Sort pending items: Priority: high first, then by Queued timestamp
  │   │
  │   ├── For each high-priority item (Source: crm-shared-mailbox, Priority: high):
  │   │   ├── Display: "🔴 [ForwardedBy] forwarded: [Subject]"
  │   │   ├── Show intent note (Summary field) prominently
  │   │   ├── Verify org exists in CRM (Org field); if unknown: ask Oscar
  │   │   ├── Create activity via append_interaction(), update contact
  │   │   └── Mark as done/skipped with timestamp + CRM Action
  │   │
  │   ├── For each normal-priority item (Source: outlook-email etc., Priority: normal or absent):
  │   │   ├── Display: "○ [Subject]"
  │   │   ├── Verify org exists in CRM
  │   │   ├── If yes: create activity via append_interaction(), update contact
  │   │   ├── If no: ask Oscar — "New org? Create? Skip?"
  │   │   └── Mark as done/skipped with timestamp + CRM Action
  │   │
  │   └── Report: "Processed N queue items (K high-priority, M normal)"
  │
  ├── 3. Scan emails (4-pass)
  │   ├── Scan window: lastScan → now (cap 14 days; default 14d if first run)
  │   ├── Pass 1: Oscar Archive (incoming)
  │   ├── Pass 2: Oscar Sent Items
  │   ├── Pass 3: Tony received (delegate)
  │   ├── Pass 4: Tony sent (delegate)
  │   ├── Dedup across passes by internetMessageId
  │   │
  │   ├── For each email:
  │   │   ├── Skip if already in email_log.json
  │   │   ├── Skip per comprehensive skip rules (§3)
  │   │   ├── Match: domain → person → skip (no match)
  │   │   ├── If matched: read content, summarize, append_interaction(), add_emails_to_log()
  │   │   └── Enrich: org domains, contact emails
  │   └── Report: "Scanned 145 emails: 23 matched, 122 skipped"
  │
  ├── 4. Scan calendar for meetings
  │   ├── Pull Oscar's calendar: 7 days back + 7 days forward
  │   │   └── Use: outlook_calendar_search(afterDateTime: 7daysAgo, beforeDateTime: 7daysForward)
  │   ├── Identify investor meetings (external attendees from CRM domains)
  │   ├── For upcoming: flag for meeting prep (org status, open tasks)
  │   ├── For past: check for meeting summary in meeting-summaries/
  │   │   ├── If summary exists: process → step 6
  │   │   └── If no summary: flag — "No debrief for [meeting]. Want to add notes?"
  │   └── Report: "3 upcoming investor meetings, 1 missing debrief"
  │
  ├── 5. Tony's Excel — DEFERRED
  │   └── Skip: "Tony's Excel tracker path not configured. Step skipped."
  │
  ├── 6. Process meeting summaries
  │   ├── Scan meeting-summaries/ for files modified since lastScan (or last 14 days)
  │   ├── 33 meeting summary files currently exist in directory
  │   ├── For each new summary:
  │   │   ├── Parse attendees → match to CRM orgs
  │   │   ├── Create interaction via append_interaction()
  │   │   └── Parse Action Items → offer to create tasks via add_prospect_task()
  │   └── Report: "2 meeting summaries processed, 4 action items surfaced"
  │
  ├── 7. Enrichment + stale org flagging
  │   ├── Org domains: new domains from email scan already added inline
  │   ├── Contact emails: new addresses already enriched inline
  │   └── Stale orgs: load_interactions() + find orgs with no activity in 30+ days
  │
  └── 8. Report summary
      "CRM Update complete:
       - Queue: 12 items processed (10 activities, 2 skipped)
       - Email: 23 new matches across 4 passes
       - Calendar: 3 upcoming investor meetings, 1 debrief missing
       - Pipeline: Tony's Excel deferred
       - Meeting summaries: 2 processed, 4 action items
       - Stale orgs: [NEPC — 45 days], [Future Fund — 32 days]"
```

## 6. Integration Points

- **Reads from:** `crm/ai_inbox_queue.md`, Microsoft 365 MCP connector (Oscar + Tony email/calendar), `meeting-summaries/`, `crm/organizations.md`, `crm/contacts_index.md`, `crm/email_log.json`, `crm/config.md`
- **Writes to:** `crm/interactions.md` (activities), `crm/email_log.json`, `crm/ai_inbox_queue.md` (status updates only), `crm/organizations.md` (domain enrichment), `contacts/*.md` (email enrichment), `TASKS.md` (new tasks)
- **Never writes to:** Overwatch TASKS.md, Overwatch data/ directory, Overwatch memory/ (including memory/people/)
- **Consumed by:** CRM dashboard, org detail pages, pipeline reports
- **Depends on:** Overwatch writing queue entries (but functions independently if queue is empty)

### MCP tool names (Microsoft 365 connector)

The skill uses the Microsoft 365 MCP connector already installed in Cowork. The tool names are:
- `outlook_email_search` — email search with folderName, sender, recipient, afterDateTime, limit params
- `outlook_calendar_search` — calendar search with afterDateTime, beforeDateTime params
- `read_resource` — read full email content by resource URI (use sparingly, only when metadata summary is insufficient)

## 7. Constraints

- arec-crm should not import Overwatch Python modules
- The queue file is the ONLY shared writable surface between the two repos
- Tony's email access requires Microsoft Graph delegate permissions (already configured in `crm/config.md`)
- All CRM record creation/updates require user confirmation during interactive triage
- The skill must be idempotent — running `/crm-update` twice should not create duplicate records
- Email deduplication via `email_log.json` messageIds
- Queue deduplication via entry status (never re-process `done` or `skipped` items)
- Overlap handling: if an email was already queued by Overwatch (in ai_inbox_queue.md) AND appears in the email scan, do not double-count — the queue processing in Step 2 takes precedence

## 8. Acceptance Criteria

- [ ] `/crm-update` skill exists at `~/.skills/skills/crm-update/SKILL.md`
- [ ] Reads and processes all `pending` items from `crm/ai_inbox_queue.md`
- [ ] Creates CRM activities for matched org/contact items
- [ ] Prompts Oscar for unmatched items (new org creation or skip)
- [ ] Marks queue items as `done` or `skipped` with timestamps and CRM action descriptions
- [ ] 4-pass email scan works for Oscar's and Tony's mailboxes
- [ ] Email deduplication via `email_log.json` prevents reprocessing
- [ ] Overlap handling: items already in queue from Overwatch are not double-processed in email scan
- [ ] Calendar scan identifies investor meetings and flags missing debriefs
- [ ] Meeting summaries are parsed for org activities and action items
- [ ] Org domain enrichment: new domains discovered from emails are added to `crm/organizations.md`
- [ ] Contact enrichment: new email addresses discovered are added to contact records
- [ ] Stale org flagging: orgs with no activity in 30+ days are surfaced
- [ ] Summary report covers all source passes with counts
- [ ] Skill is idempotent — repeated runs do not create duplicates
- [ ] Feedback loop prompt has been run

## 9. Files Touched

| File | Reason |
|------|--------|
| `~/.skills/skills/crm-update/SKILL.md` | **New** — Cowork skill definition |
| `crm/ai_inbox_queue.md` | Read + status updates (shared with Overwatch) — **created 2026-03-16** |
| `crm/email_log.json` | Read + append (email scan audit trail) — **exists, lastScan: 2026-03-11** |
| `crm/organizations.md` | Read (domain lookup) + write (domain enrichment) — **exists** |
| `crm/contacts_index.md` | Read (contact lookup) + write (contact enrichment) — **exists** |
| `contacts/*.md` | Write (email enrichment via enrich_person_email) — **213 files exist** |
| `crm/interactions.md` | Write (new activities via append_interaction) — **exists** |
| `TASKS.md` | Write (new tasks via add_prospect_task) — **exists** |
| `meeting-summaries/*.md` | Read (parse for org activities and action items) — **33 files exist** |
| `crm/config.md` | Read (team, delegate mailboxes, pipeline stages) — **exists** |

## 10. Verified Dependencies

All functions referenced in this spec have been verified present in `app/sources/crm_reader.py`:

| Function | Line | Signature |
|----------|------|-----------|
| `load_organizations()` | 238 | `() -> list[dict]` |
| `get_organization(name)` | 257 | `(name: str) -> dict \| None` |
| `write_organization(name, data)` | 264 | `(name: str, data: dict) -> None` |
| `get_org_domains(prospect_only)` | 1527 | `(prospect_only: bool = False) -> dict` |
| `load_person(slug)` | 375 | `(slug: str) -> dict \| None` |
| `find_person_by_email(email)` | 446 | `(email: str) -> dict \| None` |
| `create_person_file(...)` | 469 | `(name, org, email, role, person_type) -> str` |
| `enrich_person_email(slug, email)` | 539 | `(slug: str, email: str) -> None` |
| `get_contacts_for_org(org_name)` | 430 | `(org_name: str) -> list[dict]` |
| `add_contact_to_index(org, slug)` | 552 | `(org: str, slug: str) -> None` |
| `append_interaction(entry)` | 1004 | `(entry: dict) -> None` |
| `load_interactions(org, offering, limit)` | 951 | `(org=None, offering=None, limit=None) -> list[dict]` |
| `update_prospect_field(org, offering, field, value)` | 864 | `(org, offering, field, value) -> None` |
| `load_email_log()` | 1476 | `() -> dict` |
| `add_emails_to_log(emails)` | 1511 | `(emails: list[dict]) -> int` |
| `find_email_by_message_id(message_id)` | 1490 | `(message_id: str) -> dict \| None` |
| `add_prospect_task(...)` | 1300 | `(org_name, text, owner, priority="Med", section="IR / Fundraising") -> bool` |

## 11. Open Questions — Resolved

1. **CRM data model:** Fully documented in §4 above. Markdown-only.
2. **Tony's Excel:** No Excel tracker found. Feature deferred (§4 Tony's Excel note).
3. **Delegate permissions:** Already configured. `tavila@avilacapllc.com` in `crm/config.md`.
4. **CRM shared mailbox:** Out of scope for this iteration. The existing `/email-scan` skill handles it as a 5th pass, but `/crm-update` uses 4 passes only.
5. **Activity schema:** `crm/interactions.md` format — fully documented in §4.
6. **Pipeline stages:** 0–8 as listed in §4. Stage updates via `update_prospect_field()`.
7. **CRM tasks:** `TASKS.md` with `add_prospect_task()` function. Documented in §4.
8. **Meeting summary format:** Standardized YAML-frontmatter-free markdown format documented in §4.
9. **Email-scan overlap:** The existing `/email-scan` skill covers the email scanning and enrichment patterns. `/crm-update` should reuse those patterns but additionally creates interaction records and processes queue/calendar/meeting-summaries.
10. **Internal domains:** Full list verified: avilacapllc.com, avilacapital.com, encorefunds.com, builderadvisorgroup.com, south40capital.com.
