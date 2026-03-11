# Task Extraction from Prospect Notes - Implementation Summary

**Date:** 2026-03-09
**Feature:** Extract suggested tasks from prospect Notes field on brief refresh

---

## Files Modified

### 1. Backend: `app/briefing/brief_synthesizer.py`
**Added:**
- `TASK_EXTRACTION_SYSTEM_PROMPT` constant (35 lines)
  - Prompts Claude to extract actionable tasks from freeform notes
  - Rules for priority inference (Hi/Med), assignee matching, and validation
- `extract_tasks_from_notes()` function (73 lines)
  - Takes org name, offering, notes text, and team roster
  - Returns list of task dicts: `{text, assignee, priority, source_snippet}`
  - Handles empty notes, JSON parsing, and error fallback
  - Uses Claude Sonnet 4 (claude-sonnet-4-20250514) with 800 token limit

### 2. Backend: `app/delivery/crm_blueprint.py`
**Modified:**
- Import statement: Added `extract_tasks_from_notes` to imports (line 47)
- `api_prospect_brief()` POST handler (lines 313-326)
  - After successful brief synthesis, extracts tasks from Notes field
  - Loads config to get team roster (full names)
  - Calls `extract_tasks_from_notes()` with prospect notes
  - Adds `suggested_tasks` array to API response

### 3. Frontend: `app/templates/crm_prospect_detail.html`
**Added CSS (90 lines):**
- `.suggested-tasks-section` — section container with top border
- `.suggested-task-card` — individual task card styling (dark theme compatible)
- `.suggested-task-text` — task description text
- `.suggested-task-meta` — assignee and priority badges
- `.priority-hi/med/lo` — color-coded priority badges
- `.suggested-task-snippet` — quoted source text
- `.suggested-task-actions` — button container
- `.btn-accept-task` / `.btn-dismiss-task` — action buttons
- `.task-created-status` — success confirmation text

**Added HTML (12 lines):**
- Suggested Tasks section inserted within `#brief-card`
- Located between Relationship Brief and Active Tasks sections
- Initially hidden, shown only when tasks exist
- Header with count badge
- Body container for task cards

**Added JavaScript (120 lines):**
- `renderSuggestedTasks(tasks)` — renders task cards from array
  - Builds HTML for each task with text, assignee, priority, snippet
  - Shows section, updates count badge
- `acceptTask(idx)` — creates task via `/crm/api/followup` endpoint
  - POSTs task with org, description, priority, assignee
  - Routes to assignee's section in TASKS.md
  - Shows "✓ Created" confirmation
  - Fades out card after 1 second
  - Error handling with retry button
- `dismissTask(idx)` — fades out card without server call
- `updateTaskCount()` — decrements count, hides section when empty
- Updated `refreshBrief()` to call `renderSuggestedTasks()` on response

---

## Data Flow

1. **User clicks "Refresh Brief"** on prospect detail page
2. **Backend**:
   - Synthesizes relationship brief narrative (existing logic)
   - Loads prospect Notes field from `prospects.md`
   - Loads team roster from `crm/config.md`
   - Calls `extract_tasks_from_notes()` → Claude API
   - Returns JSON with `{narrative, at_a_glance, suggested_tasks}`
3. **Frontend**:
   - Renders narrative and at-a-glance status
   - Renders suggested tasks section with cards
   - User clicks **Accept** → POST to `/crm/api/followup` → task written to TASKS.md under assignee's section
   - User clicks **Dismiss** → card fades out (no persistence)
   - When all cards handled → section hides

---

## Task Creation Format

Tasks created via Accept button follow existing format:
```
- [ ] **[{priority}]** **@{short_name}** {description} — {org_name}
```

Example:
```
- [ ] **[Hi]** **@Oscar** Send updated track record to allocation committee — California Pension Fund
```

Routed to assignee's section:
- `## Fundraising - Oscar`
- `## Fundraising - Zach`
- etc.

---

## Edge Cases Handled

| Scenario | Behavior |
|----------|----------|
| Notes field empty | No API call, returns `[]`, section not rendered |
| Notes have no actionable items | Claude returns `[]`, section not rendered |
| Malformed JSON from Claude | Exception caught, returns `[]`, logs error |
| Assignee not on roster | `assignee = ""`, UI shows "Unassigned", defaults to Oscar on Accept |
| Task extraction API fails | Returns `[]`, logs error, does NOT block brief narrative |
| Multiple refreshes | Same tasks may reappear (dismissals not persisted) |
| Accept API call fails | Inline error on card, button re-enabled for retry |

---

## Testing Checklist

- [ ] Refresh brief on prospect with rich Notes → tasks extracted with correct assignees
- [ ] Refresh brief on prospect with empty Notes → no section rendered
- [ ] Refresh brief on prospect with status-only Notes → no tasks extracted
- [ ] Accept task → verify appears in TASKS.md under correct assignee section
- [ ] Dismiss all tasks → section disappears
- [ ] Name matching: "Zach" → "Zach Reisner", "Tony" → "Tony Avila"
- [ ] External names → shows "Unassigned", defaults to Oscar on Accept
- [ ] Priority inference: "before March" → Hi, "follow up" → Med
- [ ] Error resilience: brief loads even if task extraction fails

---

## Configuration

**Team roster source:** `crm/config.md`
```markdown
## AREC Team
- Tony Avila | tony@avilacapllc.com
- Oscar Vasquez | oscar@avilacapllc.com
- Zach Reisner | zachary.reisner@avilacapllc.com
- Patrick Fichtner | patrick@avilacapllc.com
- Truman Flynn | truman@avilacapllc.com
...
```

**Claude model:** `claude-sonnet-4-20250514`
**Max tokens:** 800 (task extraction only)
**Response format:** JSON array of task objects

---

## Next Steps

1. Test with real prospect data
2. Monitor task extraction quality
3. Iterate on system prompt if needed
4. Consider adding persistence for dismissed tasks (future enhancement)
