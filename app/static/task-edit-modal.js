/* task-edit-modal.js — Shared task edit modal for Tasks + Pipeline pages
 *
 * Requires:
 *   - TASK_MODAL_TEAM: array of team member names (set by page before loading this script)
 *   - TASK_MODAL_SECTIONS: array of TASKS.md sections (set by page)
 *   - taskModalOnSave(result): callback after successful save (set by page)
 *   - taskModalOnDelete(result): callback after successful delete (set by page)
 */

'use strict';

(function () {
  // --- State ---
  let _section = '';
  let _index = 0;
  let _org = '';

  // --- Inject modal HTML on first use ---
  let _injected = false;

  function injectModal() {
    if (_injected) return;
    _injected = true;

    const html = `
<div class="task-modal-overlay" id="taskEditModalOverlay">
  <div class="task-modal">
    <div class="task-modal-head">
      <span id="taskModalTitle">Edit Task</span>
      <button class="task-modal-close" id="taskModalCloseBtn">&times;</button>
    </div>
    <div class="task-modal-body">
      <div class="task-modal-field">
        <label class="task-modal-label">Task</label>
        <textarea id="taskModalText" rows="3"></textarea>
      </div>
      <div class="task-modal-row">
        <div class="task-modal-field">
          <label class="task-modal-label">Priority</label>
          <select id="taskModalPriority">
            <option value="Hi">Hi</option>
            <option value="Med">Med</option>
            <option value="Low">Low</option>
          </select>
        </div>
        <div class="task-modal-field">
          <label class="task-modal-label">Assigned To</label>
          <select id="taskModalAssignee"></select>
        </div>
      </div>
      <div class="task-modal-field">
        <label class="task-modal-label">Section</label>
        <select id="taskModalSection"></select>
      </div>
      <div class="task-modal-field">
        <label class="task-modal-label">Prospect</label>
        <select id="taskModalOrg">
          <option value="">— none —</option>
        </select>
      </div>
    </div>
    <div class="task-modal-foot">
      <button class="task-modal-btn task-modal-btn-danger" id="taskModalDeleteBtn">Delete</button>
      <button class="task-modal-btn" id="taskModalCancelBtn">Cancel</button>
      <button class="task-modal-btn task-modal-btn-primary" id="taskModalSaveBtn">Save</button>
    </div>
  </div>
</div>`;

    document.body.insertAdjacentHTML('beforeend', html);

    // Wire events
    document.getElementById('taskModalCloseBtn').addEventListener('click', closeTaskEditModal);
    document.getElementById('taskModalCancelBtn').addEventListener('click', closeTaskEditModal);
    document.getElementById('taskModalSaveBtn').addEventListener('click', saveTaskEdit);
    document.getElementById('taskModalDeleteBtn').addEventListener('click', deleteTaskFromModal);
    document.getElementById('taskEditModalOverlay').addEventListener('click', function (e) {
      if (e.target === this) closeTaskEditModal();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && document.getElementById('taskEditModalOverlay').classList.contains('open')) {
        closeTaskEditModal();
      }
    });
  }

  // --- Public API ---

  window.openTaskEditModal = function (opts) {
    injectModal();

    _section = opts.section || '';
    _index = typeof opts.index === 'number' ? opts.index : 0;
    _org = opts.org || '';

    // Title
    document.getElementById('taskModalTitle').textContent = opts.title || 'Edit Task';

    // Text — strip trailing (OrgName) since org is shown in the dropdown
    let displayText = opts.text || '';
    displayText = displayText.replace(/\s*\([^)]+\)\s*$/, '').trim();
    document.getElementById('taskModalText').value = displayText;

    // Priority
    document.getElementById('taskModalPriority').value = opts.priority || 'Med';

    // Assignee dropdown — uses team_map [{short, full}] for proper @tag matching
    const teamMap = window.TASK_MODAL_TEAM_MAP || [];
    const teamLegacy = window.TASK_MODAL_TEAM || [];
    const assigneeSel = document.getElementById('taskModalAssignee');
    assigneeSel.innerHTML = '<option value="">— unassigned —</option>';
    if (teamMap.length > 0) {
      for (const member of teamMap) {
        const opt = document.createElement('option');
        opt.value = member.short;
        opt.textContent = member.full;
        if (member.short === opts.assigned_to) opt.selected = true;
        assigneeSel.appendChild(opt);
      }
    } else {
      // Fallback for pages that haven't set team_map yet
      for (const name of teamLegacy) {
        const opt = document.createElement('option');
        opt.value = name;
        opt.textContent = name;
        if (name === opts.assigned_to) opt.selected = true;
        assigneeSel.appendChild(opt);
      }
    }

    // Section dropdown
    const sections = window.TASK_MODAL_SECTIONS || ['Fundraising - Me', 'Work', 'Personal'];
    const sectionSel = document.getElementById('taskModalSection');
    sectionSel.innerHTML = '';
    for (const s of sections) {
      const opt = document.createElement('option');
      opt.value = s;
      opt.textContent = s;
      if (s === _section) opt.selected = true;
      sectionSel.appendChild(opt);
    }

    // Prospect / org dropdown
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

    // Show/hide Section and Prospect fields
    const hideFields = opts.hideFields || [];
    document.getElementById('taskModalSection').closest('.task-modal-field').style.display =
      hideFields.includes('section') ? 'none' : '';
    document.getElementById('taskModalOrg').closest('.task-modal-field').style.display =
      hideFields.includes('org') ? 'none' : '';

    // Delete button visibility
    document.getElementById('taskModalDeleteBtn').style.display = opts.showDelete !== false ? '' : 'none';

    document.getElementById('taskEditModalOverlay').classList.add('open');
    document.getElementById('taskModalText').focus();
  };

  window.closeTaskEditModal = function () {
    const overlay = document.getElementById('taskEditModalOverlay');
    if (overlay) overlay.classList.remove('open');
  };

  async function saveTaskEdit() {
    let text = document.getElementById('taskModalText').value.trim();
    const priority = document.getElementById('taskModalPriority').value;
    const assignee = document.getElementById('taskModalAssignee').value;
    const newSection = document.getElementById('taskModalSection').value;
    const newOrg = document.getElementById('taskModalOrg').value;
    if (!text) return;

    // Strip any existing (OrgName) suffix, then re-append the selected one
    text = text.replace(/\s*\([^)]+\)\s*$/, '').trim();
    const taskText = newOrg ? `${text} (${newOrg})` : text;

    let res;
    if (_index < 0) {
      // CREATE mode
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

  async function deleteTaskFromModal() {
    if (!confirm('Delete this task?')) return;

    const res = await fetch(
      `/tasks/api/task/${encodeURIComponent(_section)}/${_index}`,
      { method: 'DELETE' }
    );

    if (res.ok) {
      closeTaskEditModal();
      if (typeof window.taskModalOnDelete === 'function') window.taskModalOnDelete();
      else if (typeof window.taskModalOnSave === 'function') window.taskModalOnSave();
      else location.reload();
    } else {
      alert('Failed to delete task');
    }
  }
})();
