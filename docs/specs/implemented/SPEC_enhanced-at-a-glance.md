SPEC: Enhanced At a Glance Brief | Project: arec-crm | Date: 2026-03-19 | Status: Ready for implementation

---

## 1. Objective

Upgrade the "At a Glance" column on the pipeline view from a 10-word status tag to a meaningful 2-line condensed version of the prospect brief. When a prospect brief is generated, Claude should produce two outputs: the full narrative brief (existing behavior) and a shorter pipeline summary that captures the key relationship context in ≤2 lines.

## 2. Scope

- Modify the Claude prompt/JSON contract to request a richer `at_a_glance` field
- Update the pipeline display to accommodate 2 lines instead of truncating at 60 chars
- No new fields, no new storage — `at_a_glance` in `briefs.json` already exists and flows through to the pipeline

### Out of scope
- Organization briefs (only prospect briefs are affected)
- Brief refresh logic / cache invalidation (unchanged)
- Any new API endpoints

## 3. Business Rules

- `at_a_glance` should be a 2-sentence max condensed version of the prospect narrative brief, not a status tag
- It should include the most actionable context: where the relationship stands, what's next, any blockers
- It should use specific names and dates (same rule as the full brief)
- Maximum length: ~150 characters (roughly 2 lines in the pipeline column at typical width)
- When a prospect brief is generated (via any route), the `at_a_glance` is always regenerated alongside it

## 4. Data Model / Schema Changes

**No schema changes.** The `at_a_glance` field already exists in `briefs.json` under `prospect` entries. It will simply contain longer content (up to ~150 chars vs. the current ~60 chars).

## 5. UI / Interface

### Pipeline table (`crm_pipeline.html`)
- Remove the 60-char truncation logic in the `at_a_glance` case of the cell renderer
- Allow up to 2 lines of display text in the column
- Keep gray italic styling
- Add `max-width` or `white-space` CSS so text wraps naturally within the column rather than truncating
- Keep the full-text tooltip (`title` attribute) as a fallback for any overflow
- Suggested CSS: `white-space: normal; max-width: 300px; line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;`

## 6. Integration Points

### `app/briefing/brief_synthesizer.py`
- Update `AT_A_GLANCE_JSON_SUFFIX` prompt:
  - Change from `"<10 words or fewer: current status>"` to `"<2 sentences max, ~150 chars: condensed version of the narrative brief — where the relationship stands and what's next>"`
  - Update examples to show 2-sentence summaries instead of status tags:
    - Old: `"Follow-up meeting scheduled for March 24"`
    - New: `"Met March 15 to review terms; Viktor sending revised LOI by March 24. $25M target, strong alignment on fund thesis."`
    - Old: `"Verbal commit; sub docs outstanding"`
    - New: `"Verbal $15M commit after March 10 IC approval. Legal reviewing sub docs, targeting April close."`
  - Keep the `"Use specific dates and names"` instruction
  - Change max length instruction from `"10 words MAX"` to `"150 characters MAX, 2 sentences MAX"`

### `app/delivery/crm_blueprint.py`
- No route changes needed. The `_run_prospect_brief()` flow already saves `at_a_glance` from the JSON response to `briefs.json`, and the pipeline API already injects it.

### `app/sources/crm_reader.py`
- No changes needed. `save_brief()` and `load_all_briefs()` handle `at_a_glance` as a plain string field.

## 7. Constraints

- The Claude API call already uses `want_json=True` for prospect briefs — no change to the call pattern
- `max_tokens` may need a small bump (currently 1600 for JSON responses) if the longer `at_a_glance` causes issues, but 150 chars is marginal — likely fine as-is. Monitor and adjust if needed.
- Existing briefs in `briefs.json` will retain their old short `at_a_glance` until regenerated. This is acceptable — no backfill needed.

## 8. Acceptance Criteria

- [ ] When a prospect brief is generated, `at_a_glance` in `briefs.json` contains a 2-sentence condensed summary (not a status tag)
- [ ] Pipeline "At a Glance" column displays up to 2 lines of text without truncation at 60 chars
- [ ] Text wraps cleanly and is clamped at 2 lines with ellipsis overflow
- [ ] Full text remains available on hover (tooltip)
- [ ] Existing prospects with old short `at_a_glance` values continue to display correctly
- [ ] All existing tests pass (`python3 -m pytest app/tests/ -v`)
- [ ] Feedback loop prompt has been run

## 9. Files Likely Touched

| File | Change |
|------|--------|
| `app/briefing/brief_synthesizer.py` | Update `AT_A_GLANCE_JSON_SUFFIX` prompt text and examples |
| `app/templates/crm_pipeline.html` | Update `at_a_glance` cell renderer — remove 60-char truncation, add 2-line clamp CSS |
