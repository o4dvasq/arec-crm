---
description: Full pipeline intelligence review across all High urgency prospects
---

# /crm:review — Pipeline Intelligence Review

A full pipeline intelligence review across all High urgency active prospects.
Run this weekly, before a board meeting, fundraising sprint, or LP update.

---

## Step 0: Check AI Inbox Queue

Before the pipeline review, read `crm/ai_inbox_queue.md`.

Count entries with **Status: pending**.

If any exist, open with:

> "Before the pipeline review — you have [N] pending item(s) in your CRM inbox:
> [list subject lines, one per line]
> Want to clear those first with /crm:inbox, or skip to the pipeline review?"

If Oscar says clear first: run `/crm:inbox`, then continue with the pipeline
review below when done.

If Oscar says skip: proceed directly to Step 1.

If no pending items: skip this step entirely, go straight to Step 1.

---

## Step 1: Load All Data

Read the following files:

1. `crm/prospects.md` — filter to **High urgency** prospects at active stages:
   - 5. Interested, 6. Verbal, 7. Legal / DD, 8. Committed
   - Exclude: 0. Not Pursuing, 1–4 (pre-active), 9. Closed, Declined

2. For each High urgency org:
   - `memory/people/<org-slug>.md` — intel file (if exists)
   - `crm/interactions.md` — last 3 interactions for this org

3. `crm/pending_interviews.json` — orgs awaiting post-meeting debrief

---

## Step 2: Produce the Review

Output format:

```
PIPELINE INTELLIGENCE REVIEW — [Today's date]
High Urgency Prospects: [N] active

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[N]. [ORG NAME] — [Stage] — [Target] — Last touch: [N days ago] [status icon]
   Intel: [2-3 sentence synthesis from intel file, or "No intel file" if missing]
   Last interactions: [brief summary of last 1-2 interactions from interactions.md]
   Recommended action: [specific, concrete, based on what you know]

...
```

**Status icons:**
- ✅ Last touch ≤ 7 days
- 🟡 Last touch 8–21 days
- 🔴 Last touch > 21 days

**Sort order:** By last touch date, most stale first (🔴 at top).

**Recommended action rules:**
- Must be specific — not "follow up" but "Schedule call with Susannah to confirm May IC timeline"
- If no intel file exists: recommended action is always "Run /crm:interview before next outreach"
- If next_action field is blank in prospects.md: flag it explicitly
- Based on what you actually know from the intel file and interactions — not generic advice

---

## Step 3: Staleness and Gaps Summary

After the per-org entries, add a brief summary:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GAPS:
- [N] orgs with no intel file: [list names]
- [N] orgs with next_action blank: [list names]
- [N] orgs with intel file > 30 days old: [list names]

PENDING DEBRIEFS:
- [list any orgs in pending_interviews.json with their meeting date]
```

Only include sections that have entries. Skip sections with zero items.

---

## Step 4: Close with Offer

End with:

> "Want me to start an interview for any of these? Or push any follow-up
> actions to TASKS.md?"

If the user says yes to adding tasks, write them to `TASKS.md` under the
appropriate section (Work — IR/Fundraising) using the format:
`- [ ] **[Hi]** [Specific action] — [Org name]`

If the user wants to start an interview, proceed directly into the
/crm:interview flow for the specified org.
