---
name: email
description: "Deep scan of Oscar's Outlook '#productivity' email folder for CRM-relevant emails. Reads unprocessed emails, matches them against prospects/contacts, queues to crm/ai_inbox_queue.md, quizzes Oscar on unknowns, and archives processed emails. Trigger on: '/email', 'check my email folder', 'process productivity emails', 'scan inbox for CRM', 'email refresh', 'check #productivity', or any request to process saved emails for CRM intelligence."
---

# Email — CRM Email Processor

Scan Oscar's Outlook `#productivity` folder, extract CRM intelligence from saved emails, queue them for review, quiz Oscar on anything ambiguous, and archive after processing.

Oscar manually saves important investor/deal/CRM-related emails to a top-level Outlook folder called `#productivity`. This skill processes that folder — it's the bridge between his email triage and the CRM knowledge base.

## Why this matters

Emails saved to `#productivity` are Oscar's signal that something is CRM-relevant — an investor reply, a placement agent intro, a deal update. Without processing, these pile up and the CRM goes stale. This skill turns that signal into structured intelligence.

## Workflow

### Step 1: Load CRM context

Before touching emails, load the context needed to match senders/subjects to known entities:

1. Read `CLAUDE.md` — for the People table, Companies & LPs, and Terms
2. Read `crm/prospects.md` — to match orgs/contacts to pipeline stages
3. Read `crm/ai_inbox_queue.md` — to check what's already been queued (avoid duplicates)
4. Read `crm/contacts_index.md` — for email-to-person matching

Store this context in working memory. You'll use it to auto-match emails to known orgs/people.

### Step 2: Fetch emails from `#productivity`

Use `outlook_email_search` to pull emails from the `#productivity` folder:

```
outlook_email_search(
  query: "*",
  folderName: "#productivity",
  limit: 50
)
```

If the folder returns 0 results, tell Oscar the folder is empty and stop.

### Step 3: Read and classify each email

For each email returned:

1. **Read the full email** using `read_resource` with the email URI
2. **Extract key fields:**
   - Subject line
   - Sender (name + email)
   - Date
   - Recipients (to/cc — useful for seeing who else is in the loop)
   - Body summary (first ~200 words, enough to understand intent)
   - Any attachments (note filenames, don't download)

3. **Match against CRM:**
   - Check sender email against `contacts_index.md` and the CLAUDE.md People table
   - Check subject line and body for org names from `prospects.md`
   - Check for known deal names (Mountain House, Murata Tampa, etc.)

4. **Classify the email into one of these buckets:**

   | Bucket | Meaning | Example |
   |--------|---------|---------|
   | **Auto-match** | Sender or org clearly maps to a known prospect/contact | Email from `nigelb@emiratesnbd.com` → Emirates NBD |
   | **Likely match** | Strong signal but not definitive — name overlap, org mentioned in body | Subject mentions "Willis Towers" but sender is unknown |
   | **Unknown** | Can't confidently match to any CRM entity | New sender, no org keywords |
   | **Internal** | From an AREC team member — still valuable for context/action items | Email from Truman about a prospect follow-up |

### Step 4: Queue to ai_inbox_queue.md

For each email (regardless of bucket), append an entry to `crm/ai_inbox_queue.md`:

```markdown
## YYYY-MM-DD

### [Subject Line]
- **From:** [Sender Name] <[email]>
- **Intent:** [1-line summary of what the email is about — inferred from body]
- **Org:** [matched org name, or "Unknown — needs review"]
- **Status:** pending
- **Action Taken:**
- **Match Confidence:** [Auto-match | Likely match | Unknown | Internal]
- **Key Detail:** [The single most important fact — e.g. "Confirmed $5M commitment", "Requesting DDQ", "Intro to new contact"]
```

Group entries under the same date header if multiple emails share a date. Don't duplicate entries that already exist in the queue (match by subject + sender + date).

### Step 5: Quiz Oscar

This is the interactive part. After processing all emails, present findings grouped by confidence:

**Auto-matched emails** — present as a summary table, no questions needed:
```
✓ 3 emails auto-matched and queued:
  - Emirates NBD (Nigel Burton) — "Re: Fund II Documentation" → queued
  - South40 (Ian Morgan) — "Placement update Q1" → queued
  - Truman Flynn — "NT follow-up notes" → queued as Internal
```

**Likely matches** — present with your best guess and ask for confirmation:
```
? 2 emails need confirmation:
  1. "Re: Investment Committee Update" from sarah.chen@wellsfargo.com
     → I think this maps to Wells Fargo (not in prospects yet). Correct?
     → Should I add Wells Fargo as a new prospect?

  2. "Fwd: Land parcel analysis" from unknown@gmail.com
     → Subject mentions "Canarelli" — is this related to the Canarelli family LP?
```

**Unknown emails** — present the key details and ask what they are:
```
? 1 email I couldn't place:
  1. "Introduction: James and Tony" from max@angeloniandco.com
     → Max Angeloni forwarding an intro. Who is James in this context?
     → Should this go into the CRM as a new contact?
```

Wait for Oscar to respond to all questions before proceeding. Use his answers to:
- Update the queue entries with correct org names
- Note any new contacts for potential KB enrichment (flag but don't auto-create — suggest adding via `/productivity:update` contact enrichment flow)
- Update match confidence to "Confirmed" for anything Oscar validates

### Step 6: Archive processed emails

After Oscar has reviewed and confirmed, move processed emails out of `#productivity`. Since Outlook email operations through the current tools are read-only, instruct Oscar:

> **Ready to archive:** I've processed N emails from #productivity.
> Since I can't move emails directly, you'll want to select all in #productivity and move them to your archive folder (or create one called `#productivity-archive` if it doesn't exist).
>
> Alternatively, if you'd like me to just mark them as read so you know what's been processed, I can do that.

If the tools support moving emails in the future, do it automatically to `#productivity-archive`.

### Step 7: Report

Summarize what was done:

```
Email scan complete:
- Folder: #productivity
- Emails found: N
- Auto-matched: N (queued to ai_inbox_queue.md)
- Confirmed by Oscar: N
- New contacts flagged: N
- Run /crm:inbox to process the queue
```

## Edge Cases

- **Empty folder:** "Your #productivity folder is empty — nothing to process."
- **Duplicate emails:** If an email's subject + sender + date already exists in `ai_inbox_queue.md`, skip it and note "N duplicates skipped."
- **Thread/reply chains:** If multiple emails are part of the same thread, queue only the most recent one but note the thread depth (e.g., "3-email thread — latest queued").
- **Attachments:** Note attachment filenames in the queue entry's Key Detail field. Don't download unless Oscar asks.
- **Very large batch (20+):** Process in batches of 10, pausing between batches for Oscar to review the quiz questions. Don't dump 30 questions at once.

## Notes

- This skill is READ from Outlook, WRITE to local CRM files only
- Never auto-create prospect records — only queue and flag
- The quiz step is mandatory — always present unknowns to Oscar, even if you're fairly confident
- Respects the same CRM config (stages, urgency, team) defined in `crm/config.md`
