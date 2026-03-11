# Task 17 — In Edit Task, Allow Assign to a Prospect

## Enhancement
Add a "Prospect" dropdown to the task edit modal that lets the user associate a task with a prospect (org). This replaces the current read-only org badge with an editable dropdown.

## Files to Modify
- `app/static/task-edit-modal.js`
- `app/templates/crm_pipeline.html` (pass prospect list to JS)
- `app/templates/tasks/tasks.html` (pass prospect list to JS)
- `app/delivery/dashboard.py` (task API: handle org in create/update)

## Current Behavior
- The task modal has a read-only "Prospect" badge (`#taskModalOrgBadge`) that shows the org name if the task has an `(OrgName)` suffix
- Users cannot change or set the prospect association from the modal
- CRM tasks are identified by the `(OrgName)` suffix in the task text in TASKS.md

## Required Changes

### 1. task-edit-modal.js — Replace org badge with dropdown

Replace the `taskModalOrgRow` section in the modal HTML (line ~55-58):

```html
<div class="task-modal-field">
  <label class="task-modal-label">Prospect</label>
  <select id="taskModalOrg">
    <option value="">— none —</option>
    <!-- Populated dynamically from prospect list -->
  </select>
</div>
```

Remove the old `taskModalOrgRow` div and `taskModalOrgBadge` span.

### 2. task-edit-modal.js — Populate prospect dropdown in `openTaskEditModal()`

```javascript
// Prospect / Org dropdown
const orgSel = document.getElementById('taskModalOrg');
const prospectOrgs = window.TASK_MODAL_PROSPECT_ORGS || [];
orgSel.innerHTML = '<option value="">— none —</option>';
const seen = new Set();
for (const orgName of prospectOrgs) {
  if (seen.has(orgName)) continue;
  seen.add(orgName);
  const opt = document.createElement('option');
  opt.value = orgName;
  opt.textContent = orgName;
  if (orgName === _org) opt.selected = true;
  orgSel.appendChild(opt);
}
```

### 3. task-edit-modal.js — Include org in save payload

In `saveTaskEdit()`, read the selected org and handle the `(OrgName)` suffix:

```javascript
async function saveTaskEdit() {
  let text = document.getElementById('taskModalText').value.trim();
  const priority = document.getElementById('taskModalPriority').value;
  const assignee = document.getElementById('taskModalAssignee').value;
  const newSection = document.getElementById('taskModalSection').value;
  const newOrg = document.getElementById('taskModalOrg').value;
  if (!text) return;

  // Strip any existing (OrgName) suffix from text before re-adding
  text = text.replace(/\s*\([^)]+\)\s*$/, '').trim();

  let res;
  if (_index < 0) {
    // CREATE mode
    const taskText = newOrg ? `${text} (${newOrg})` : text;
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
    // EDIT mode
    const taskText = newOrg ? `${text} (${newOrg})` : text;
    res = await fetch(
      `/tasks/api/task/${encodeURIComponent(_section)}/${_index}`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: taskText,
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

### 4. crm_pipeline.html — Pass prospect org list to JS

In the `<script>` section, after fetching prospects, expose the list of org names:

```javascript
window.TASK_MODAL_PROSPECT_ORGS = allProspects.map(p => p.org);
```

Update this on every `reloadProspects()` call.

### 5. tasks/tasks.html — Pass prospect org list to JS

On the Tasks page, fetch the prospect org list for the dropdown:

```javascript
// After page load, fetch prospect orgs for the task modal
fetch('/crm/api/orgs')
  .then(r => r.json())
  .then(orgs => { window.TASK_MODAL_PROSPECT_ORGS = orgs; });
```

This requires the existing `GET /crm/api/orgs` endpoint to return org names (verify it exists).

### 6. task-edit-modal.js — Strip (OrgName) from displayed text

When opening the modal, strip the `(OrgName)` suffix from the text field so it's not duplicated:

```javascript
// In openTaskEditModal():
let displayText = opts.text || '';
// Strip trailing (OrgName) since it's now shown in the dropdown
displayText = displayText.replace(/\s*\([^)]+\)\s*$/, '').trim();
document.getElementById('taskModalText').value = displayText;
```

## Important Notes
- The `(OrgName)` suffix in TASKS.md is the canonical way tasks link to prospects. The dropdown just provides a UI for setting it.
- When editing, the existing `(OrgName)` is stripped from display text and shown in the dropdown. On save, it's re-appended.
- Changing the prospect dropdown from "OrgA" to "OrgB" moves the task's CRM association.
- Setting it to "— none —" removes the CRM association (no suffix appended).

## Testing
1. Open Pipeline → click a CRM task → modal should show org in dropdown (pre-selected)
2. Task text should NOT show `(OrgName)` suffix (it's in the dropdown)
3. Change the prospect dropdown to a different org → Save → verify TASKS.md updated
4. Open Tasks page → edit a non-CRM task → Prospect dropdown should show "— none —"
5. Set Prospect to an org → Save → task now has `(OrgName)` suffix in TASKS.md and appears in Pipeline
6. Create a new task from Pipeline "+ task" → Prospect should be pre-selected
7. Create a new task from Tasks page → Prospect dropdown available and defaults to "— none —"
