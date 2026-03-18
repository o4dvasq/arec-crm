# SPEC: Email Backfill, Polling Verification & Thread Collapsing

**Project:** arec-crm
**Date:** 2026-03-17
**Status:** Ready for implementation

---

## 1. Objective

Establish a reliable, complete email interaction history in the CRM by:

(a) Running a one-time 90-day backfill from Oscar's and Tony's mailboxes into `email_log.json`
(b) Verifying that the `/email-scan` skill correctly captures new emails going forward
(c) Collapsing email threads in the prospect detail UI so conversations display cleanly
(d) Removing the non-functional Deep Scan button

---

## 2. Scope

**In scope:**

- New backfill script: `scripts/backfill_emails.py`
- Schema evolution: add 3 new fields to `email_log.json` records (`conversationId`, `direction`, `mailboxSource`)
- Verification checklist for `/email-scan` Claude Desktop skill (manual run, confirm capture)
- Thread grouping in Email History section on prospect detail page
- Remove Deep Scan button and helper text from prospect detail UI

**Out of scope:**

- Scheduling email scans (cron/Azure Function) — deferred
- AI thread summarization — deferred (latest message is the preview for now)
- CRM shared mailbox (`crm@avilacapllc.com`) scanning
- Any other mailboxes beyond Oscar + Tony
- Any SQL/database additions — this project is markdown/JSON only

---

## 3. Business Rules

### 3.1 Backfill

- Wipe ALL existing entries in `email_log.json` where the email was originally captured via automated scan (not manually created interactions in `interactions.md` — those are untouched).
- Scan 90 days back from today for both mailboxes.
- Both sent AND received emails for both Oscar and Tony.
- Match to CRM orgs using existing two-tier logic: domain match via `get_org_domains()` in `crm_reader.py` (Tier 1), then person email match via `email_matching.py` (Tier 2).
- Dedup by `messageId` — if the same email appears in both Oscar's and Tony's mailbox (e.g., both were recipients), store it once. First-seen wins; set `mailboxSource` to the first mailbox that encountered it.
- Skip internal-only emails (all participants are `@avilacapllc.com`, `@avilacapital.com`, `@builderadvisorgroup.com`). Reuse the skip list already in `crm_reader.py` (`_SERVICE_PROVIDER_ORGS` pattern or equivalent internal domain check).
- `date` field = email sent date from Graph (`receivedDateTime`).
- After backfill completes, update `Last Touch` on affected prospect records in `prospects.md` to the most recent email date for that org.

### 3.2 Thread Collapsing (Display Only)

- Store every email as its own record in `email_log.json`. No collapsing at write time.
- In the Email History UI section on prospect detail, group emails by `conversationId`.
- Display: show one row per thread. The row shows the **latest** email in the thread as the preview (subject, date, summary snippet). Badge shows thread count (e.g., "3 emails").
- Expand: clicking a thread row expands to show all emails in the thread, newest first.
- Emails with no `conversationId` (e.g., older entries captured before this feature) display as standalone rows, ungrouped.

### 3.3 Ongoing Polling Verification

- After backfill, run the `/email-scan` Claude Desktop skill manually.
- Confirm: new emails from the past 24h that match CRM orgs are captured with correct `conversationId`, `direction`, `messageId`, and `mailboxSource` fields.
- No scheduling — just prove the pipeline works end-to-end with the new fields.

---

## 4. Data Model / Schema Changes

### 4.1 New fields on `email_log.json` records

Each email object in `email_log.json["emails"]` gains three new optional fields:

```json
{
  "messageId": "AAMk...",
  "conversationId": "AAQk...",
  "direction": "received",
  "mailboxSource": "ovasquez@avilacapllc.com",
  "date": "2026-03-05",
  "timestamp": "2026-03-05T07:38:18Z",
  "subject": "...",
  "from": "alexandra@diamondcapital.ch",
  "fromName": "Alexandra",
  "to": [],
  "cc": [],
  "orgMatch": "Diamond Capital",
  "matchType": "domain",
  "confidence": 0.95,
  "summary": "...",
  "outlookUrl": "..."
}
```

New fields:

- `conversationId` (string, nullable): Graph API's `conversationId` field. Groups thread members. Null for legacy entries.
- `direction` (string): `"sent"` or `"received"`. Determined by whether `from` address matches the scanned mailbox UPN.
- `mailboxSource` (string): Which mailbox this was scanned from — `"ovasquez@avilacapllc.com"` or `"tavila@avilacapllc.com"`. Null for legacy entries.

### 4.2 Update `crm_reader.py`

- `add_emails_to_log()`: Already deduplicates by `messageId`. No structural change needed — the new fields flow through naturally as dict keys.
- New function `get_emails_for_org_grouped(org_name) -> list[dict]`: Returns emails grouped by `conversationId` with thread metadata (count, latest date, latest subject). Used by the UI endpoint.
- Update `get_emails_for_org()` to include the new fields in returned records (they're already there as dict values — just ensure the endpoint passes them to the frontend).

---

## 5. UI / Interface

### 5.1 Remove Deep Scan Button

- Remove the "Deep Scan (90d)" button (`#deep-scan-btn`) from the Email History section header in `crm_prospect_detail.html`.
- Remove the `runDeepEmailScan()` function and associated scan status elements from the template JS.
- The section header should just show "Email History" with the count badge and collapse toggle. No buttons, no helper text.

### 5.2 Thread-Grouped Email History

Replace the flat email list with a threaded view:

```
┌──────────────────────────────────────────────────────┐
│ Email History  (47)                                  │
├──────────────────────────────────────────────────────┤
│ ▶ Re: Fund II - Updated Terms Sheet    3 emails      │
│   Mar 15 · sent · via Oscar                          │
├──────────────────────────────────────────────────────┤
│ ▶ Q1 Performance Update               1 email        │
│   Mar 12 · received · via Tony                       │
├──────────────────────────────────────────────────────┤
│ ▼ Introduction - AREC Debt Fund II     5 emails      │
│   Mar 10 · sent · via Oscar                          │
│  ┌────────────────────────────────────────────────┐  │
│  │ Mar 10 · sent · Oscar → John Kim               │  │
│  │ Following up on our conversation...            │  │
│  ├────────────────────────────────────────────────┤  │
│  │ Mar 8 · received · John Kim → Oscar            │  │
│  │ Thanks for sending the materials...            │  │
│  ├────────────────────────────────────────────────┤  │
│  │ Mar 5 · sent · Oscar → John Kim                │  │
│  │ John, great meeting you at the...              │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

- Collapsed row: subject (from latest email), thread count badge, date of latest, direction indicator, mailbox source.
- Expanded: nested list of all emails in thread, newest first. Each shows date, direction, participants snippet, summary/subject.
- Single-email "threads" display the same way but with "1 email" and no expand arrow.
- Direction indicator: "sent" / "received" label or subtle arrow icon.
- Mailbox source: "via Oscar" / "via Tony" — subtle, secondary text.

### 5.3 Sort Order

- Threads sorted by most recent email date, descending (newest thread activity at top).
- Within an expanded thread, emails sorted newest first.

---

## 6. Integration Points

### 6.1 Microsoft Graph API

- Backfill queries: `GET /users/{upn}/messages` with `$filter=receivedDateTime ge {90_days_ago}` and `$orderby=receivedDateTime desc`.
- For sent items: `GET /users/{upn}/mailFolders/sentitems/messages` with same date filter.
- Fields to retrieve: `id`, `conversationId`, `subject`, `bodyPreview`, `receivedDateTime`, `from`, `toRecipients`, `ccRecipients`.
- Auth: Use existing `graph_auth.py` token acquisition (`get_access_token()`) with `Mail.Read` + `Mail.Read.Shared` scopes.
- Rate limiting: respect Graph throttling (429 responses). Add retry with exponential backoff.
- Pagination: Graph returns max 1000 per page. Follow `@odata.nextLink` for full results.
- Reference `ms_graph.py` for existing Graph call patterns (`get_recent_emails()` etc.).

### 6.2 Existing Matching Logic

- Use `crm_reader.get_org_domains()` for domain-based matching (Tier 1).
- Use `email_matching.py` functions for person-email matching (Tier 2).
- Reuse internal domain skip list from `crm_reader.py`.
- Dedup via `messageId` field — `add_emails_to_log()` already handles this.

### 6.3 Last Touch Update

- After backfill completes, for each org that received new emails, recalculate last touch date as `MAX(date)` across all email_log entries for that org.
- Use `crm_reader.py` functions to update `Last Touch` field on the matching prospect record in `prospects.md`.
- Follow existing patterns for prospect field updates (likely `update_prospect()` or similar).

### 6.4 Email-Scan Skill Update

- The `/email-scan` Claude Desktop skill (which calls `add_emails_to_log()`) must be updated to include `conversationId`, `direction`, and `mailboxSource` in the email dicts it passes to `crm_reader.py`. This ensures ongoing scans populate the new fields.

---

## 7. Constraints

- Backfill script runs locally. Requires local `.env` with Graph credentials (same as existing email-scan skill).
- No new libraries — use existing `msal`, `requests` (already in `requirements.txt`).
- No SQL, no ORM, no database. All storage is `email_log.json` + markdown files via `crm_reader.py`.
- Backfill must be idempotent: running it twice should not create duplicates (`add_emails_to_log()` deduplicates by `messageId`).
- Backfill should log progress to stdout: "Scanning Oscar received... 342 emails found. 156 matched to CRM orgs. Scanning Oscar sent..." etc.
- Thread grouping is purely a display-time operation in the frontend JS — no new files, no pre-computation.
- The JS thread grouping must handle the case where `conversationId` is null (legacy entries shown ungrouped).

---

## 8. Acceptance Criteria

1. Backfill script wipes existing auto-scanned emails from `email_log.json`, then scans Oscar + Tony mailboxes (sent + received), 90 days
2. Backfill populates `conversationId`, `direction`, and `mailboxSource` on every new email record
3. Backfill matches emails to CRM orgs using existing two-tier logic (domain → person email)
4. Backfill deduplicates by `messageId` (same email in both mailboxes stored once)
5. Backfill skips internal-only emails
6. Backfill logs progress to stdout (mailbox, direction, count found, count matched)
7. `Last Touch` updated on all affected prospects in `prospects.md` after backfill
8. Manual run of `/email-scan` skill captures new emails with all three new fields populated
9. Deep Scan button, `runDeepEmailScan()` function, and helper text removed from prospect detail page
10. Email History section groups emails by `conversationId` with thread count badge
11. Collapsed thread shows latest email's subject, date, direction, mailbox source
12. Clicking a thread expands to show all emails, newest first
13. Emails with null `conversationId` display as ungrouped standalone rows
14. No regressions to existing interaction history, relationship briefs, or other prospect detail features
15. Feedback loop prompt has been run

---

## 9. Files Likely Touched

**New files:**

- `scripts/backfill_emails.py` — one-time 90-day email backfill script

**Modified files:**

- `app/sources/crm_reader.py` — add `get_emails_for_org_grouped()` function; ensure `add_emails_to_log()` passes new fields through cleanly
- `app/sources/ms_graph.py` — ensure `get_recent_emails()` returns `conversationId` from Graph response (add to `$select` if not already included); add sent-items query variant if not present
- `app/templates/crm_prospect_detail.html` — remove Deep Scan button + helper text + `runDeepEmailScan()`; replace `renderEmails()` with thread-grouped email history UI
- `app/static/crm.js` (or inline JS in template) — client-side thread grouping logic (group by `conversationId`, sort, expand/collapse)
- `app/delivery/crm_blueprint.py` — ensure email history endpoint returns the new fields from `email_log.json` to the frontend (via `collect_relationship_data()` or direct)
- `app/sources/relationship_brief.py` — ensure `collect_relationship_data()` passes new email fields through to the frontend
- `crm/email_log.json` — existing records untouched; new records gain `conversationId`, `direction`, `mailboxSource` fields
