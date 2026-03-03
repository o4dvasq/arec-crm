# CRM Intelligence Layer — Architecture & Implementation Spec
**Author:** Oscar Vasquez, COO — Avila Real Estate Capital
**Date:** March 2026
**Status:** Ready for Execution
**Companion to:** CRM Architecture v4 (FINAL), Phases 1–7

---

## 1. Purpose

The mechanical CRM (Phases 1–7) stores and displays investor data. This layer
makes it intelligent — Claude actively reads, reasons over, and enriches that
data as a natural extension of the existing daily productivity workflow.

The goal: replace the "cloud-based Excel table" experience of Juniper Square
with something that accumulates institutional knowledge, surfaces insights
without being asked, and extracts the qualitative context that lives only in
Oscar's head.

---

## 2. Overview: Four Intelligence Touchpoints

```
5:00 AM          Morning briefing enriched with investor intel
                 └── High urgency prospects with meetings today get
                     relationship context, known objections, next steps

Daily (manual)   /productivity:update
                 └── Brief CRM flag: 1-2 pointed observations about
                     High urgency prospects needing attention
                     └── If pending interviews exist → prompt to debrief

On demand        /crm:review
                 └── Full pipeline intelligence review across all
                     High urgency prospects

On demand        /crm:interview <org>
  + automatic    └── Structured interview → writes memory/people/<org>.md
  post-meeting       First session: full intake
                     Follow-up sessions: delta only (what's changed)
```

---

## 3. The Intel File

**Location:** `~/Dropbox/Tech/ClaudeProductivity/memory/people/<org-slug>.md`

Where `<org-slug>` is the org name lowercased, spaces replaced with hyphens,
special characters stripped. Examples:
- `Merseyside Pension Fund` → `merseyside-pension-fund.md`
- `NPS (Korea SWF)` → `nps-korea-swf.md`
- `University of Texas Investment Management Company (UTIMCO)` → `utimco.md`

**Format:**

```markdown
# Merseyside Pension Fund — Investor Intelligence

**Offering:** AREC Debt Fund II
**Stage:** 6. Verbal
**Urgency:** High
**Last interview:** 2026-03-02 (post-meeting debrief)
**Interview type:** delta

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

## 4. Component 1 — Morning Briefing Enrichment

**Files to modify:** `briefing/prompt_builder.py`

### Change to `build_prompt()`

After assembling the PEOPLE CONTEXT section (which currently only surfaces
profiles for attendees in today's meetings), add a new section:

**INVESTOR INTELLIGENCE**

Logic:
1. Load all High urgency prospects from `load_prospects()` filtered to active
   stages (5+)
2. For any of those prospects where the org has a meeting in today's calendar
   (matched by org name appearing in event attendees or event title), load
   their intel file from `memory/people/<org-slug>.md`
3. If intel file exists and is non-empty, include it in the prompt under
   `## INVESTOR INTELLIGENCE`
4. Cap at 800 chars per intel file (truncate at paragraph boundary)
5. If no High urgency prospects have meetings today, omit the section entirely

**System prompt addition:**

Add to the existing SYSTEM_PROMPT:

```
When a meeting today involves a High urgency investor prospect, open the
briefing with a prospect-specific paragraph that synthesizes: what you know
about their decision dynamics and real objections (from the intel file), what
happened last time you interacted (from interactions.md), and what the goal
of today's meeting should be. Be specific and direct — not generic meeting
prep boilerplate.
```

**Expected briefing output (example):**

> **Merseyside Pension Fund — 10:00 AM call with Susannah Friar**
> They're at verbal but the real blocker is board approval timing — Susannah
> told James in February that the investment committee meets quarterly and the
> next window is May. Your goal today is to understand whether they can get on
> the May agenda and what you need to provide by April 15th to make that happen.
> Last interaction: James sent the Credit and Index Comparisons deck on Feb 25th.
> Known objection unresolved: concentration risk in Texas/Southeast markets.

This is categorically different from what Juniper Square can produce.

---

## 5. Component 2 — Productivity Update CRM Hook

**This lives in the Claude Cowork plugin, not in Flask code.**

### 5.1 Add CRM awareness to `/productivity:update`

The productivity update skill currently:
1. Reads inbox.md
2. Processes tasks
3. Updates TASKS.md and memory files

Add a new step **after task processing:**

**Step: CRM Pulse Check**

Claude reads:
- `crm/prospects.md` → filter to High urgency, active stages (5+)
- `crm/interactions.md` → last touch date per org
- `crm/pending_interviews.json` → orgs awaiting post-meeting debrief
- `memory/people/<org-slug>.md` → existence check only (has intel file or not)

Claude then surfaces **at most 2 observations** inline in the update output.
Not a report — 2-3 sentences max, pointed and actionable.

**Examples of good observations:**

> ⚡ **NPS Korea** has been at Stage 5 for 23 days with no Next Action set
> and no interaction logged. Want to add a follow-up task or do a quick
> intel capture?

> ⚡ **Merseyside Pension Fund** intel file is from January — you've had
> 3 interactions since. Worth a 5-minute debrief to update what's changed?

> ⚡ **3 High urgency prospects** have their last touch over 14 days ago:
> Berkshire Hathaway (18d), Abu Dhabi IC (21d), CalPERS (31d).

**Observation selection logic (in priority order):**
1. Pending post-meeting interviews (highest priority — time-sensitive while fresh)
2. High urgency prospects with no Next Action set
3. High urgency prospects with last touch > 14 days
4. High urgency prospects with no intel file
5. High urgency prospects whose intel file is > 30 days old

Never surface more than 2 observations per update. If nothing qualifies,
omit the CRM Pulse section entirely — don't manufacture filler.

### 5.2 Pending interview queue

**File:** `~/Dropbox/Tech/ClaudeProductivity/crm/pending_interviews.json`

Written by `crm_graph_sync.py` (Phase 5) when a meeting with a High urgency
org is detected. Read by the Cowork plugin during `/productivity:update`.

```json
{
  "pending": [
    {
      "org": "Merseyside Pension Fund",
      "offering": "AREC Debt Fund II",
      "meeting_date": "2026-03-02",
      "meeting_title": "Fund II Discussion",
      "detected_at": "2026-03-02T05:00:00"
    }
  ]
}
```

**Write logic in `crm_graph_sync.py`:**
- After logging a Meeting interaction for a High urgency prospect, append
  to `pending_interviews.json`
- Deduplicate by org — if org already in pending list, update
  `meeting_date` and `meeting_title` with the most recent
- Keep pending items for a maximum of 7 days (purge older on each write)

**Consume logic in Cowork plugin:**
- When `/productivity:update` sees pending interviews, it surfaces them as
  the top observation and offers to start the debrief immediately
- After a debrief interview completes and the intel file is written,
  remove the org from `pending_interviews.json`

---

## 6. Component 3 — `/crm:review` Command

**This is a new Cowork plugin command.**

### What it does

A full pipeline intelligence review across all High urgency active prospects.
More thorough than the daily pulse check — meant to be run weekly or before
a board meeting, fundraising sprint, or LP update.

### Output format

```
PIPELINE INTELLIGENCE REVIEW — March 1, 2026
High Urgency Prospects: 8 active

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. MERSEYSIDE PENSION FUND — 6. Verbal — $50M — Last touch: 4 days ago ✅
   Intel: Board approval window is May. Need to get on April 15 committee
   agenda. Key risk: concentration objection unresolved.
   Recommended action: Schedule follow-up with Susannah this week to
   confirm May timeline. Assign James to prepare concentration response.

2. NPS KOREA SWF — 5. Interested — $300M — Last touch: 23 days ago 🔴
   Intel: No intel file. Meeting with John Kim flagged Feb 25.
   Recommended action: Run /crm:interview before next outreach.
   Next action field is blank — needs to be set.

3. BERKSHIRE HATHAWAY — 5. Interested — $100M — Last touch: 18 days ago 🟡
   Intel: [last intel file summary, 2 sentences]
   Recommended action: [specific, not generic]

...
```

### Implementation notes

Claude reads:
- All High urgency prospects from `prospects.md`
- Corresponding intel files from `memory/people/`
- Last 3 interactions per org from `interactions.md`

Claude synthesizes — not summarizes — producing a specific recommended action
for each prospect based on what it knows. If there's no intel file, it says so
and recommends running the interview before the next outreach.

At the end, Claude asks: *"Want me to start an interview for any of these?
Or push any follow-up actions to TASKS.md?"*

---

## 7. Component 4 — `/crm:interview` Command

**This is a new Cowork plugin command.**

### Trigger modes

**Manual:** User types `/crm:interview Merseyside Pension Fund` in Claude Desktop.

**Automatic prompt:** During `/productivity:update`, Claude surfaces a pending
interview and user says yes → interview starts immediately in the same session.

### Pre-interview context load

Before asking anything, Claude silently reads:
- The prospect record from `prospects.md`
- All interactions for this org from `interactions.md`
- Existing intel file from `memory/people/<org-slug>.md` (if exists)
- Any tasks in `TASKS.md` referencing this org name

Claude uses this to:
- Know what it already knows (avoid asking questions it can answer itself)
- Frame its questions around gaps, not from scratch
- For delta sessions: identify which sections of the intel file are stale or
  have had relevant events since the last update

### Session types

**First session (no existing intel file):**
Full intake interview. 6-8 questions covering all sections of the intel file
format. Claude takes 2-3 minutes per section, probing where the answer
reveals depth.

**Delta session (intel file exists):**
Claude opens with a summary of what it already knows:

> *"Last time we talked about Merseyside, you said the key blocker was board
> approval timing and that Susannah was the internal champion. Since then
> you've had 3 interactions including the March 2nd call. I want to focus on
> what's changed. A few questions..."*

Delta session covers only:
- What changed since the last session
- How existing objections have evolved
- Whether the "what would move them" section needs updating
- What the Next 30 Days section should say now

Typically 3-5 questions for a delta session.

### Interview style

Claude asks **one question at a time**. It listens to the answer and probes
where there's depth before moving on. It does not present a list of questions.

Good question examples:
- *"Who is actually making the final decision — is Susannah the decision-maker
  or is she the gatekeeper to someone else?"*
- *"You mentioned concentration risk as an objection. When they raised it, what
  exactly did they say — and did it feel like a genuine concern or a negotiating
  position?"*
- *"If you had to name the one thing that would move them from verbal to
  committed in the next 60 days, what would it be?"*

Bad question examples (avoid):
- *"Can you tell me about your relationship with Merseyside?"* (too open-ended)
- *"What are the objections, decision dynamics, and key history?"* (multiple questions)
- *"Is there anything else you'd like to add?"* (filler)

### Closing the interview

After the last question, Claude says:

> *"Here's what I'm going to write to the intel file. Review this and tell me
> what to change before I save it."*

Claude presents the full draft intel file content — all sections, synthesized
from the interview answers into coherent paragraphs (not bullet-point
transcripts of what Oscar said).

Oscar reviews, requests edits, approves.

Claude then:
1. Writes `memory/people/<org-slug>.md`
2. Removes org from `pending_interviews.json` (if it was there)
3. Confirms: *"Intel file saved for Merseyside Pension Fund. Next update and
   morning briefing will include this context."*

### What Claude does NOT do

- Does not ask more than 8 questions total in a first session
- Does not ask more than 5 questions in a delta session
- Does not write to the file until Oscar explicitly approves the draft
- Does not summarize the interview back as bullet points — synthesizes into
  prose that reads like institutional knowledge, not meeting notes

---

## 8. Cowork Plugin Skill Definitions

Two new skills to add to the ClaudeProductivity plugin:

### Skill: `crm-intelligence`

**Commands:**
- `/crm:interview [org name]` — structured interview → intel file
- `/crm:review` — full pipeline intelligence review

**Files read:**
- `crm/prospects.md`
- `crm/interactions.md`
- `crm/pending_interviews.json`
- `memory/people/*.md` (intel files)
- `TASKS.md` (for org-name cross-reference)

**Files written:**
- `memory/people/<org-slug>.md`
- `crm/pending_interviews.json` (to remove completed interviews)

### Modification to existing skill: `task-management`

Add CRM pulse check as the final step of `/productivity:update` (after task
processing, before session close). Reads CRM files, surfaces ≤2 observations,
prompts for pending interviews.

---

## 9. Flask / Python Changes

### `crm_graph_sync.py` addition (Phase 5 file)

Add `write_pending_interview()` function:

```python
def write_pending_interview(org: str, offering: str,
                             meeting_date: str, meeting_title: str) -> None:
    """
    Append org to pending_interviews.json.
    Only called for High urgency prospects.
    Deduplicates by org name.
    Purges items older than 7 days on each write.
    """
```

Call this after `append_interaction()` for any Meeting interaction where
the matched prospect has urgency == 'High'.

### `briefing/prompt_builder.py` addition

Add `load_investor_intel(events, prospects)` function:

```python
def load_investor_intel(events: list, prospects: list) -> str:
    """
    For each today's event, check if any attendee or event title matches
    a High urgency prospect org name.
    If match found and intel file exists, load and truncate to 800 chars.
    Returns formatted string for prompt injection, or '' if nothing relevant.
    """
```

Call from `build_prompt()`, inject result into the user prompt as a new
section between PEOPLE CONTEXT and the closing instruction.

---

## 10. File Structure Additions

```
~/Dropbox/Tech/ClaudeProductivity/
├── crm/
│   └── pending_interviews.json        ← NEW (written by crm_graph_sync.py)
└── memory/
    └── people/
        ├── merseyside-pension-fund.md ← NEW (written by /crm:interview)
        ├── nps-korea-swf.md           ← NEW
        └── ...one file per High urgency prospect, as interviews are conducted
```

---

## 11. Implementation Sequence

Build in this order. Each step is independently testable.

### Step 1 — Pending interview queue (code change)
Modify `crm_graph_sync.py` to write `pending_interviews.json` after
detecting a meeting with a High urgency org. This is a small addition to
Phase 5 code.

Verify: run auto-capture, check `pending_interviews.json` is created.

### Step 2 — Morning briefing enrichment (code change)
Modify `prompt_builder.py` to load intel files and inject into prompt.
Test with a hand-crafted intel file for a prospect with a meeting today.

Verify: morning briefing output includes investor-specific context paragraph.

### Step 3 — `/crm:interview` skill (Cowork plugin)
Build and test the interview command in Claude Desktop. Run a full first-session
interview for one real prospect. Review the draft intel file output. Approve
and save.

Verify: `memory/people/<org-slug>.md` created with correct format.

### Step 4 — `/crm:review` skill (Cowork plugin)
Build the review command. Run it against current pipeline data.

Verify: output is specific and actionable, not generic.

### Step 5 — CRM pulse in `/productivity:update` (Cowork plugin)
Add the pulse check step to the existing update skill. Tune the observation
selection logic to surface the right things without noise.

Verify: run `/productivity:update` — pulse section appears when relevant,
absent when nothing qualifies.

---

## 12. Success Criteria

The intelligence layer is working when:

1. **Morning briefing** — on a day with a High urgency investor meeting,
   the briefing opens with a paragraph that is specific to that relationship
   and would actually change how Oscar prepares for the meeting

2. **Daily update** — the CRM pulse occasionally (not always) surfaces one
   thing that Oscar would not have noticed otherwise, and is right about it

3. **Interview quality** — after a `/crm:interview` session, the resulting
   intel file contains information that is not anywhere in `prospects.md` or
   `interactions.md` — knowledge that was previously only in Oscar's head

4. **Accumulation** — after 30 days of use, the intel files collectively
   represent a body of institutional knowledge about AREC's top relationships
   that would be valuable to any team member and would survive Oscar's
   departure from a meeting
