# Task 11 — Multiple Tasks per Prospect

## Enhancement
Allow prospects to have multiple tasks. The pipeline already supports rendering multiple tasks per prospect — this task ensures the full create/edit/delete flow works correctly with multiple tasks.

## Current Behavior
The system already supports multiple tasks per prospect:
- `load_tasks_by_org()` in `crm_reader.py` returns a list of tasks per org
- Pipeline `buildCellContent()` iterates over `p._tasks` and renders each
- Each task has a unique `section` + `index` pair for editing

The "+ Add task" link from Task 10 handles creation. This task ensures:
1. The pipeline task cell properly displays multiple tasks with visual separation
2. The task index references remain correct after add/delete operations

## Files to Modify
- `app/templates/crm_pipeline.html` (rendering refinement)

## Required Changes

### crm_pipeline.html — `buildCellContent()` tasks rendering (~line 887-906)

Ensure each task is rendered as a distinct block with a small gap between them:

```javascript
if (col.key === 'tasks') {
  const tasks = p._tasks || [];
  tasks.forEach((t, i) => {
    const taskEl = document.createElement('div');
    taskEl.style.cssText = 'margin-bottom:3px; line-height:1.3;';

    // Owner badge
    if (t.owner) {
      const ownerBadge = document.createElement('span');
      ownerBadge.textContent = `@${t.owner}`;
      ownerBadge.style.cssText = 'font-size:10px; color:#64748b; background:#f1f5f9; padding:1px 4px; border-radius:3px; margin-right:4px;';
      taskEl.appendChild(ownerBadge);
    }

    // Priority dot
    const dot = document.createElement('span');
    const dotColor = t.priority === 'Hi' ? '#ef4444' : t.priority === 'Med' ? '#f59e0b' : '#94a3b8';
    dot.style.cssText = `display:inline-block; width:6px; height:6px; border-radius:50%; background:${dotColor}; margin-right:4px; vertical-align:middle;`;
    taskEl.appendChild(dot);

    // Task text (clickable)
    const textSpan = document.createElement('span');
    textSpan.textContent = t.task.length > 50 ? t.task.slice(0, 50) + '…' : t.task;
    textSpan.style.cssText = 'font-size:12px; cursor:pointer; color:#e2e8f0;';
    textSpan.dataset.section = t.section;
    textSpan.dataset.index = t.index;
    textSpan.dataset.text = t.task;
    textSpan.dataset.priority = t.priority;
    textSpan.dataset.owner = t.owner || '';
    textSpan.dataset.org = p.org;
    textSpan.addEventListener('click', (e) => {
      e.stopPropagation();
      openPipelineTaskEdit(textSpan);
    });
    taskEl.appendChild(textSpan);

    cell.appendChild(taskEl);
  });

  // "+ task" link (from Task 10)
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

This replaces the existing task rendering block entirely. The key improvements:
- Each task is a separate `<div>` with margin spacing
- Visual hierarchy: owner badge → priority dot → truncated text
- The "+ task" link always appears below, even when tasks already exist

## Important Note
The task index (`t.index`) is the 0-based position within its TASKS.md section. After creating or deleting a task, the pipeline calls `reloadProspects()` which re-fetches all data including fresh indices, so stale index references are not a concern.

## Testing
1. Add 2-3 tasks to the same prospect using the "+ task" link
2. Verify all tasks render with clear separation
3. Click each task — edit modal should open with correct data
4. Delete a task — remaining tasks should re-render correctly
5. Verify tasks in TASKS.md all have the correct `(OrgName)` suffix
