---
description: Structured investor intelligence interview → writes intel file
argument-hint: "[org name]"
---

# /crm:interview — Investor Intelligence Interview

Conduct a structured intelligence interview about an investor prospect and write
the result to `memory/people/<org-slug>.md`.

**Org name from argument:** $ARGUMENTS

---

## Pre-Interview: Load Context

Before asking anything, silently read:

1. `crm/prospects.md` — find all prospect records for this org
2. `crm/interactions.md` — find all interactions for this org (last 10)
3. `memory/people/<org-slug>.md` — existing intel file if it exists
   - Slug: org name lowercased, spaces→hyphens, special chars stripped
   - Example: "Merseyside Pension Fund" → `merseyside-pension-fund.md`
4. `TASKS.md` — find any tasks referencing this org name

Use this context to:
- Identify what you already know (avoid asking questions you can answer yourself)
- Determine whether this is a **first session** (no intel file) or **delta session** (file exists)
- For delta sessions: identify which sections are stale based on interaction dates since last interview

---

## Session Types

### First Session (no existing intel file)

Full intake. Cover all six sections of the intel file format.
Ask 6–8 questions total. Take time to probe where an answer reveals depth.

Open with:

> "I've read through [org]'s prospect record and your interaction history. Before I start
> asking, here's what I already know: [1-2 sentence summary of what the CRM data shows].
> I want to go deeper on the things that aren't in the data — the stuff that only lives
> in your head. Ready?"

### Delta Session (intel file exists)

Focus only on what's changed. Ask 3–5 questions max.

Open with a summary of what you already know from the existing file:

> "Last time we talked about [org], you said [key point from intel file]. Since then
> you've had [N] interactions, including [most recent]. I want to focus on what's changed.
> A few questions..."

Cover only:
- What changed since last session
- How existing objections have evolved
- Whether "What Would Move Them" needs updating
- What the Next 30 Days should say now

---

## Interview Style

**Ask one question at a time.** Listen to the answer and probe where there's depth
before moving on. Do not present a list. Do not rush.

**Good questions:**
- "Who is actually making the final decision — is [name] the decision-maker or the gatekeeper to someone else?"
- "You mentioned [objection] as a concern. When they raised it, what exactly did they say — and did it feel like a genuine concern or a negotiating position?"
- "If you had to name the one thing that would move them from [current stage] to committed in the next 60 days, what would it be?"
- "Is there anything they've said off the record that changes how you read the situation?"

**Bad questions (avoid):**
- "Can you tell me about your relationship with [org]?" (too open-ended)
- "What are the objections, decision dynamics, and key history?" (multiple questions at once)
- "Is there anything else you'd like to add?" (filler)

**Question limit:** Max 8 questions for first session, max 5 for delta.

---

## Intel File Format

After completing the interview, synthesize answers into prose — not bullet-point
transcripts of what Oscar said. Write it like institutional knowledge, readable by
any team member.

```markdown
# [Org Name] — Investor Intelligence

**Offering:** [offering name]
**Stage:** [current stage]
**Urgency:** [High / Med / Low]
**Last interview:** [YYYY-MM-DD] ([first intake / delta])
**Interview type:** [first / delta]

## Relationship
Who we know, relationship tenure, tone, rapport moments that matter.
Who at AREC has the strongest relationship and why.

## Decision Dynamics
Who the real decision-maker is vs. who we talk to.
Internal champion (if any). Internal skeptic (if any).
Committee structure or approval process we know about.

## Real Objections
What they say vs. what they actually mean.
Known concerns, stated and unstated.
What's been tried to address each objection and how it landed.

## What Would Move Them
Specific, concrete things that would accelerate a decision:
- A reference call with a specific type of LP
- A particular data point or comparison
- A meeting with Tony or a specific team member
- A structural accommodation (co-investment right, fee break, etc.)

## Key History
Timeline of moments that matter — not a log (that's in interactions.md),
but the turning points, commitments made, things said that revealed something.

## Next 30 Days
What needs to happen. Who needs to do what.
What we're watching for as a signal of progress or stall.

## Notes
[Freeform — anything that doesn't fit above]
```

---

## Closing the Interview

After the last question, present the full draft:

> "Here's what I'm going to write to the intel file. Review this and tell me
> what to change before I save it."

Show the complete draft. Wait for Oscar to review and approve. Make any
requested edits before saving.

**Do NOT write the file until Oscar explicitly approves.**

Once approved:

1. Write `memory/people/<org-slug>.md` with the final content
2. Check `crm/pending_interviews.json` — if this org is in the pending list,
   remove it by rewriting the file with that entry filtered out
3. Confirm: "Intel file saved for [org]. The next morning briefing will include
   this context when you have a meeting with them."

---

## What Not To Do

- Do not ask more than 8 questions in a first session
- Do not ask more than 5 questions in a delta session
- Do not write to the file until Oscar explicitly approves the draft
- Do not summarize as bullet points — synthesize into prose
- Do not re-ask questions the existing CRM data already answers
