# Task 10 — Click Empty Tasks Cell on Pipeline to Add a Task

## Enhancement
When a prospect has no tasks, clicking the empty Tasks cell in the pipeline should open the task edit modal in "create" mode, pre-filled with the prospect's org name.

## Files to Modify
- `app/templates/crm_pipeline.html`

## Current Behavior
The `tasks` column in `buildCellContent()` (~line 887-906) renders each existing task as a clickable span. If there are no tasks, the cell is empty and not interactive.

## Required Changes

### crm_pipeline.html — `buildCellContent()` tasks section (~line 887)

After rendering existing tasks, if there are none (or even if there are — see Task 11 for multi-task), add a clickable "+ Add" element:

```javascript
if (col.key === 'tasks') {
  const tasks = p._tasks || [];
  // Render existing tasks (existing code)
  tasks.forEach(t => {
    // ... existing task rendering ...
  });
  // NEW: Add a "+ Add task" link at the bottom of the cell
  const addBtn = document.createElement('span');
  addBtn.textContent = '+ task';
  addBtn.style.cssText = 'font-size:11px; color:#64748b; cursor:pointer; display:inline-block; margin-top:2px;';
  addBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    openPipelineTaskCreate(p.org);
  });
  cell.appendChild(addBtn);
  return cell;
}
```

### crm_pipeline.html — New function `openPipelineTaskCreate(org)`

Add this function near `openPipelineTaskEdit()` (~line 1259):

```javascript
function openPipelineTaskCreate(org) {
  openTaskEditModal({
    title: 'New Task',
    text: '',
    priority: 'Med',
    assigned_to: 'Oscar',
    section: 'Fundraising - Me',
    index: -1,        // Signal: new task, not editing existing
    org: org,
    showDelete: false,
  });
}
```

### task-edit-modal.js — Handle create mode (index === -1)

In `saveTaskEdit()` (~line 160), detect when `_index === -1` (create mode) and POST to the create endpoint instead of PUT to the update endpoint:

```javascript
async function saveTaskEdit() {
  const text = document.getElementById('taskModalText').value.trim();
  const priority = document.getElementById('taskModalPriority').value;
  const assignee = document.getElementById('taskModalAssignee').value;
  const newSection = document.getElementById('taskModalSection').value;
  if (!text) return;

  let res;
  if (_index < 0) {
    // CREATE mode — new task
    const taskText = _org ? `${text} (${_org})` : text;
    res = await fetch('/tasks/api/task', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        section: newSection,
        text: taskText,
        priority: priority,
        assigned_to: assignee,
      }),
    });
  } else {
    // EDIT mode — existing task (existing code)
    res = await fetch(
      `/tasks/api/task/${encodeURIComponent(_section)}/${_index}`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text,
          priority: priority,
          assigned_to: assignee,
          section: newSection,
        }),
      }
    );
  }

  if (res.ok) {
    closeTaskEditModal();
    if (typeof window.taskModalOnSave === 'function') window.taskModalOnSave();
    else location.reload();
  } else {
    alert('Failed to save task');
  }
}
```

Key detail: When creating a CRM task, the `(OrgName)` suffix must be appended to the task text so `load_tasks_by_org()` can match it back to the prospect.

## Testing
1. Open Pipeline, find a prospect with no tasks
2. Click the empty tasks cell — modal should open with org badge showing, section=Fundraising - Me
3. Type a task description and save
4. Verify task appears in TASKS.md with `(OrgName)` suffix
5. Reload pipeline — task should now appear in that prospect's row
6. Also verify "+ task" link appears below existing tasks for prospects that already have tasks
