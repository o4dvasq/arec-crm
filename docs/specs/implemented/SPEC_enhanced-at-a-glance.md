SPEC: Enhanced At a Glance + Prospect Brief Quality Fix | Project: arec-crm | Date: 2026-03-19 | Status: Ready for implementation

---

## 1. Objective

Three related fixes to the prospect brief system:

**A. Brief quality** — The prospect brief prompt produces stale, backwards-looking summaries that reference completed prep items (e.g., "prepare deck for the meeting") even when the meeting has already occurred. The prompt needs temporal awareness and instructions to discard completed items.

**B. At a Glance upgrade** — The pipeline "At a Glance" column currently shows a 10-word status tag. Upgrade it to a 2-sentence condensed version of the prospect brief (~150 chars).

**C. Key format unification + at_a_glance on prospect brief route** — Two routes generate prospect briefs using different storage keys and different JSON contracts. The "focused" prospect brief route (`/prospect-brief`) saves under `prospect_brief:{offering}:{org}` and never generates `at_a_glance`. The relationship brief route (`/brief`) saves under `{org}::{offering}` and generates `at_a_glance`. The pipeline reads from `{org}::{offering}`. This means focused prospect briefs are invisible to the pipeline, and at_a_glance is never updated from the prospect detail page.

## 2. Scope

### In Scope
- Fix prospect brief prompt to produce current-state-aware briefs
- Upgrade at_a_glance prompt from 10-word tag to 2-sentence summary
- Unify brief storage key format so all prospect briefs are visible to the pipeline
- Ensure the focused prospect brief route also generates and stores at_a_glance
- Update pipeline display to accommodate 2-line at_a_glance

### Out of Scope
- Organization briefs
- Brief refresh logic / cache invalidation
- New API endpoints
- Backfilling existing briefs (they'll update on next manual refresh)

## 3. Business Rules

- Prospect briefs must reflect the **current state** as of today's date (passed in context)
- Completed action items must be treated as done — never presented as pending
- Temporal references in notes ("next week" from March 12) must be resolved relative to today
- If a meeting was planned and the date has passed, the brief should note "meeting occurred [date]" and focus on follow-up, not prep
- `at_a_glance` should be a 2-sentence max condensed version of the narrative, not a status tag
- Maximum at_a_glance length: ~150 characters
- All prospect brief routes must store under the same key format and generate at_a_glance

## 4. Data Model / Schema Changes

**No schema changes.** Existing fields in `briefs.json` are reused. Orphaned entries under the old `prospect_brief:` key format can be cleaned up (3 entries exist as of today).

## 5. UI / Interface

### Pipeline table (`crm_pipeline.html`)
- Remove the 60-char truncation logic in the `at_a_glance` cell renderer
- Allow up to 2 lines of display text in the column
- Keep gray italic styling
- Add CSS so text wraps naturally: `white-space: normal; max-width: 300px; line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;`
- Keep the full-text tooltip (`title` attribute) as overflow fallback

## 6. Integration Points

### A. `app/sources/relationship_brief.py` — Prompt quality fix (meeting-centric framing)

Replace the existing `PROSPECT_BRIEF_SYSTEM_PROMPT` rules section with meeting-centric logic. The new prompt must instruct Claude to use meetings as the organizing principle for the brief. Add/replace after the existing audience description:

```
MEETING-CENTRIC PRIORITY FRAMEWORK:
Your brief should be organized around the most important meeting — past or future.

1. IF there is a RECENT PAST MEETING (within the last ~2 weeks):
   - Lead with it: when it happened, who attended, key outcomes
   - Read through meeting notes and summaries carefully
   - Focus on follow-up tasks and next steps that emerged FROM that meeting
   - Any prep tasks that were for this meeting are DONE — never present them as pending

2. IF there is an UPCOMING FUTURE MEETING (scheduled):
   - Lead with it: when, where, who's attending, what format
   - Focus on preparation: what needs to happen before the meeting
   - Surface any notes, comments, or tasks related to meeting prep

3. IF there is NEITHER a recent past nor a scheduled future meeting:
   - Look at open tasks and recent activity to infer what's happening
   - Focus on what outreach or action is needed to GET to a next meeting
   - Note how long since last meaningful contact

TEMPORAL AWARENESS RULES:
- TODAY'S DATE is provided at the top of the context. Use it to determine what is current vs. past.
- If a meeting or call was scheduled and its date has PASSED, treat it as completed. Focus on outcomes and follow-up, not preparation.
- Never present completed action items as pending. If notes say "prepare deck for March 17 meeting" and today is March 19, that meeting happened — do NOT say "prepare deck."
- Resolve relative time references: if notes from March 12 say "meeting next week", that means ~March 17-19.
- Prioritize the MOST RECENT events and their follow-up over historical context.
```

Also update `BRIEF_SYSTEM_PROMPT` (the full relationship brief prompt) with the same meeting-centric framework and temporal awareness rules, adapted for its longer 2-4 paragraph format.

### B. `app/sources/relationship_brief.py` — Add today's date to context

In `build_context_block()`, prepend today's date at the top of the context block:

```python
from datetime import date
context = f"TODAY'S DATE: {date.today().isoformat()}\n\n"
# ... rest of context block
```

### C. `app/briefing/brief_synthesizer.py` — At a Glance upgrade

Update `AT_A_GLANCE_JSON_SUFFIX` prompt:
- Change `"<10 words or fewer: current status>"` to `"<2 sentences max, ~150 chars: condensed version of the narrative — where the relationship stands and what's next>"`
- Update examples:
  - `"Met March 15 to review terms; Viktor sending revised LOI by March 24. $25M target, strong thesis alignment."`
  - `"Verbal $15M commit after March 10 IC approval. Legal reviewing sub docs, targeting April close."`
  - `"March 17 team presentation completed. Awaiting Julia's feedback and follow-up meeting request."`
- Change max length instruction from `"10 words MAX"` to `"150 characters MAX, 2 sentences MAX"`

### D. `app/delivery/crm_blueprint.py` — Unify key format + add at_a_glance to focused route

**`_run_focused_prospect_brief()`** (around line 495):
1. Change `brief_key` from `f"prospect_brief:{offering}:{org}"` to `f"{org}::{offering}"` — same format the pipeline reads
2. Change `want_json=False` to `want_json=True` so Claude returns `{narrative, at_a_glance}`
3. Pass `at_a_glance` to `save_brief()` call
4. Bump `max_tokens` from 600 to 800 to accommodate JSON wrapper

**`api_prospect_brief_focused()` GET handler** (around line 521):
1. Change `brief_key` from `f"prospect_brief:{offering}:{org}"` to `f"{org}::{offering}"`

**`prospect_detail()` route** (around line 383):
1. Change `prospect_brief_key` from `f"prospect_brief:{offering}:{org}"` to `f"{org}::{offering}"`

### E. Cleanup orphaned keys (optional)

Remove 3 orphaned entries from `briefs.json` with `prospect_brief:` prefix. These were created by the old key format and are never read by anything:
- `prospect_brief:AREC Debt Fund II:Texas Permanent School Fund`
- `prospect_brief:AREC Debt Fund II:Future Fund`
- `prospect_brief:AREC Debt Fund II:MetLife Insurance Company`

## 7. Constraints

- `max_tokens` for the focused brief increases from 600→800 to accommodate JSON. Monitor output quality.
- Existing briefs retain old at_a_glance values until manually refreshed. No backfill needed.
- The `BRIEF_SYSTEM_PROMPT` (full relationship brief) should also get the temporal awareness rules and today's date in context, for consistency.

## 8. Acceptance Criteria

- [ ] Prospect brief for an org with a past meeting correctly describes the meeting as having occurred, focuses on follow-up
- [ ] Prospect brief never presents completed action items as pending
- [ ] When a prospect brief is generated via ANY route, `at_a_glance` in `briefs.json` contains a 2-sentence condensed summary
- [ ] Pipeline "At a Glance" column displays up to 2 lines without 60-char truncation
- [ ] Both brief routes store under `{org}::{offering}` key format
- [ ] Pipeline correctly reads and displays at_a_glance from regenerated briefs
- [ ] `GET /api/prospect/.../prospect-brief` returns brief stored under unified key
- [ ] Existing prospects with old at_a_glance values continue to display correctly
- [ ] All existing tests pass (`python3 -m pytest app/tests/ -v`)
- [ ] Feedback loop prompt has been run

## 9. Files Likely Touched

| File | Change |
|------|--------|
| `app/sources/relationship_brief.py` | Add temporal awareness rules to `PROSPECT_BRIEF_SYSTEM_PROMPT` and `BRIEF_SYSTEM_PROMPT`; add today's date to `build_context_block()` |
| `app/briefing/brief_synthesizer.py` | Update `AT_A_GLANCE_JSON_SUFFIX` prompt text and examples |
| `app/delivery/crm_blueprint.py` | Unify `brief_key` format to `{org}::{offering}` in 3 locations; enable `want_json=True` for focused brief |
| `app/templates/crm_pipeline.html` | Update `at_a_glance` cell renderer — remove 60-char truncation, add 2-line clamp CSS |
| `crm/briefs.json` | (optional) Remove 3 orphaned `prospect_brief:` entries |
