# Task 4: Modal Dropdown — Use Short Names as Values

**Status:** DONE
**File:** `app/static/task-edit-modal.js`
**Dependencies:** Task 1 (needs `team_map` data available) and Task 5 (needs templates to pass it)

## Problem

The "Assigned To" dropdown used full names from `TASK_MODAL_TEAM` (e.g., "Tony Avila") as option values. But TASKS.md @tags use short names ("Tony"). Since "Tony" !== "Tony Avila", the dropdown never matched and fell back to "Oscar (default)".

## What Changed

Replace the assignee dropdown builder (around line 103-113):

```javascript
// BEFORE
const team = window.TASK_MODAL_TEAM || [];
const assigneeSel = document.getElementById('taskModalAssignee');
assigneeSel.innerHTML = '<option value="">Oscar (default)</option>';
for (const name of team) {
  const opt = document.createElement('option');
  opt.value = name;
  opt.textContent = name;
  if (name === opts.assigned_to) opt.selected = true;
  assigneeSel.appendChild(opt);
}

// AFTER
const teamMap = window.TASK_MODAL_TEAM_MAP || [];
const teamLegacy = window.TASK_MODAL_TEAM || [];
const assigneeSel = document.getElementById('taskModalAssignee');
assigneeSel.innerHTML = '<option value="">— unassigned —</option>';
if (teamMap.length > 0) {
  for (const member of teamMap) {
    const opt = document.createElement('option');
    opt.value = member.short;        // "Tony" — matches @tag
    opt.textContent = member.full;   // "Tony Avila" — display label
    if (member.short === opts.assigned_to) opt.selected = true;
    assigneeSel.appendChild(opt);
  }
} else {
  for (const name of teamLegacy) {
    const opt = document.createElement('option');
    opt.value = name;
    opt.textContent = name;
    if (name === opts.assigned_to) opt.selected = true;
    assigneeSel.appendChild(opt);
  }
}
```

## Acceptance Criteria

- Editing a task with `assigned_to: "Tony"` shows "Tony Avila" selected in dropdown
- Saving writes `assigned_to: "Tony"` (short name) back to the API
- Default option shows "— unassigned —" instead of "Oscar (default)"
- Graceful fallback if `TASK_MODAL_TEAM_MAP` is not set
