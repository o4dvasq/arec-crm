---
description: Review and action queued AI email inbox items flagged for CRM
---

# /crm:inbox — AI Inbox CRM Queue Review

Review items forwarded to the AI email inbox that were flagged as CRM-relevant
during `/productivity:update`. Work through each pending item and take action.

---

## Step 1: Load the Queue

Read `crm/ai_inbox_queue.md`.

Filter to entries with **Status: pending** only.

If no pending entries exist, respond:

> "No pending CRM inbox items. You're caught up."

Stop there — do not continue.

---

## Step 2: Work Through Each Item

For each pending item, present it one at a time:

```
📬 Item [N] of [total] — [Subject line]
Received: [date + time]

Your note: "[sender_note from the entry]"

Summary: [2-3 sentence synthesis of the original email content — not a
transcript, just what matters for the CRM]

Suggested actions:
  a) [Most likely CRM action based on content + your note]
  b) [Second option if applicable]
  c) No action needed — mark as reviewed
```

**Wait for Oscar to respond before moving to the next item.**

Do not present all items at once.

---

## Step 3: Execute the Response

Based on Oscar's response, take one or more of these actions:

**If updating a prospect field:**
Write to `crm/prospects.md` using the appropriate org and offering section.
Update only the specific field(s) mentioned (Next Action, Notes, Stage, Urgency).
Auto-update Last Touch to today.

**If creating a task:**
Append to `TASKS.md` under `## Work — IR/Fundraising`:
`- [ ] **[Hi]** [Specific action] — [Org name]`

**If running an interview:**
Proceed directly into `/crm:interview` for the specified org after finishing
the inbox review. Do not interrupt the current item flow.

**If no action (option c):**
Mark as reviewed without writing anything.

After executing, mark the item in `crm/ai_inbox_queue.md`:
Change `**Status:** pending` → `**Status:** actioned`
Add `**Actioned:** [YYYY-MM-DD] — [one-line summary of what was done]`

---

## Step 4: Close

After working through all items, give a brief summary:

```
Inbox review complete.
  • [N] items actioned
  • [N] tasks added to TASKS.md
  • [N] prospect records updated
  • [N] interviews queued
```

Then ask:
> "Anything else from the inbox you want to dig into, or shall we move on?"

---

## What Not To Do

- Do not present all items at once — one at a time only
- Do not take action until Oscar responds to each item
- Do not rewrite the entire queue file — only update the Status field of actioned items
- Do not manufacture suggested actions — base them strictly on the email content and Oscar's note
- Do not run /crm:interview mid-inbox-review — queue it for after
