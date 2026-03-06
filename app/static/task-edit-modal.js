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
          <label class="task-modal-label">Status</label>
          <select id="taskModalStatus">
            <option value="New">New</option>
            <option value="In Progress">In Progress</option>
            <option value="Complete">Complete</option>
          </select>
        </div>
      </div>
      <div class="task-modal-field">
        <label class="task-modal-label">Assigned To</label>
        <div class="task-modal-assignee-wrap">
          <input type="text" id="taskModalAssigneeSearch" autocomplete="off" placeholder="Search team members…">
          <div class="task-modal-assignee-dropdown" id="taskModalAssigneeDropdown"></div>
        </div>
      </div>
      <div class="task-modal-field" id="taskModalOrgField">
        <label class="task-modal-label">Prospect</label>
        <div class="task-modal-org-wrap" id="taskModalOrgWrap">
          <input type="text" id="taskModalOrgSearch" autocomplete="off" placeholder="Search prospects…">
          <div class="task-modal-org-dropdown" id="taskModalOrgDropdown"></div>
        </div>
      </div>
      <div class="task-modal-field">
        <label class="task-modal-label">Notes / Context</label>
        <textarea id="taskModalContext" rows="3" placeholder="Additional context or notes…"></textarea>
      </div>
    </div>
    <div class="task-modal-foot">
      <button class="task-modal-btn task-modal-btn-secondary" id="taskModalNudgeBtn" style="display:none">📧 Send Nudge</button>
      <div style="flex:1"></div>
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
    document.getElementById('taskModalNudgeBtn').addEventListener('click', sendNudgeFromModal);
    document.getElementById('taskEditModalOverlay').addEventListener('click', function (e) {
      if (e.target === this) closeTaskEditModal();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && document.getElementById('taskEditModalOverlay').classList.contains('open')) {
        closeTaskEditModal();
      }
    });

    // Assignee search input wiring
    const assigneeSearch = document.getElementById('taskModalAssigneeSearch');
    const assigneeDropdown = document.getElementById('taskModalAssigneeDropdown');
    assigneeSearch.addEventListener('input', function () {
      renderAssigneeDropdown(this.value);
      assigneeDropdown.style.display = '';
    });
    assigneeSearch.addEventListener('focus', function () {
      // Show all team members on focus (don't filter by current value)
      renderAssigneeDropdown('');
      assigneeDropdown.style.display = '';
    });
    assigneeSearch.addEventListener('blur', function () {
      setTimeout(() => { assigneeDropdown.style.display = 'none'; }, 150);
    });

    // Prospect search input wiring
    const orgSearch = document.getElementById('taskModalOrgSearch');
    const orgDropdown = document.getElementById('taskModalOrgDropdown');
    orgSearch.addEventListener('input', function () {
      renderOrgDropdown(this.value);
      orgDropdown.style.display = '';
    });
    orgSearch.addEventListener('focus', function () {
      renderOrgDropdown(this.value);
      orgDropdown.style.display = '';
    });
    orgSearch.addEventListener('blur', function () {
      // Delay hide so click on option registers first
      setTimeout(() => { orgDropdown.style.display = 'none'; }, 150);
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

    // Status
    document.getElementById('taskModalStatus').value = opts.status || 'New';

    // Context
    document.getElementById('taskModalContext').value = opts.context || '';

    // Assignee search field — set current value
    const assignedTo = opts.assigned_to || '';
    document.getElementById('taskModalAssigneeSearch').value = assignedTo;
    document.getElementById('taskModalAssigneeDropdown').style.display = 'none';

    // Prospect search field — set current value
    const hideFields = opts.hideFields || [];
    document.getElementById('taskModalOrgField').style.display =
      hideFields.includes('org') ? 'none' : '';
    document.getElementById('taskModalOrgSearch').value = _org;
    document.getElementById('taskModalOrgDropdown').style.display = 'none';

    // Delete button visibility
    document.getElementById('taskModalDeleteBtn').style.display = opts.showDelete !== false ? '' : 'none';

    // Nudge button visibility (only if there's an assignee)
    const nudgeBtn = document.getElementById('taskModalNudgeBtn');
    if (opts.assigned_to && opts.assigned_to.trim() !== '') {
      nudgeBtn.style.display = 'inline-block';
    } else {
      nudgeBtn.style.display = 'none';
    }

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
    const status = document.getElementById('taskModalStatus').value;
    const assignee = document.getElementById('taskModalAssigneeSearch').value.trim();
    const context = document.getElementById('taskModalContext').value.trim();
    const newSection = _section;
    const newOrg = document.getElementById('taskModalOrgSearch').value.trim();
    if (!text) return;

    // Strip any existing (OrgName) suffix - backend will handle adding it back
    text = text.replace(/\s*\([^)]+\)\s*$/, '').trim();

    let res;
    if (_index < 0) {
      // CREATE mode
      res = await fetch('/tasks/api/task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          section: newSection,
          text: text,
          priority: priority,
          status: status,
          context: context,
          assigned_to: assignee,
          org: newOrg,
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
            text: text,
            priority: priority,
            status: status,
            context: context,
            assigned_to: assignee,
            section: newSection,
            org: newOrg,
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

  function renderAssigneeDropdown(query) {
    const dropdown = document.getElementById('taskModalAssigneeDropdown');
    const teamMap = window.TASK_MODAL_TEAM_MAP || [];
    const teamLegacy = window.TASK_MODAL_TEAM || [];
    const team = teamMap.length > 0
      ? teamMap.map(m => ({ value: m.short, label: m.full }))
      : teamLegacy.map(name => ({ value: name, label: name }));

    const q = (query || '').toLowerCase();
    const matches = q
      ? team.filter(t => t.label.toLowerCase().includes(q) || t.value.toLowerCase().includes(q))
      : team;

    if (!matches.length) {
      dropdown.innerHTML = '<div class="task-modal-assignee-option task-modal-assignee-none">No matches</div>';
      return;
    }
    dropdown.innerHTML = [{ value: '', label: '— unassigned —' }]
      .concat(matches)
      .map(item => `<div class="task-modal-assignee-option" data-value="${item.value}">${item.label}</div>`)
      .join('');
    dropdown.querySelectorAll('.task-modal-assignee-option').forEach(el => {
      el.addEventListener('mousedown', function () {
        const val = this.dataset.value;
        document.getElementById('taskModalAssigneeSearch').value = val;
        dropdown.style.display = 'none';
      });
    });
  }

  function renderOrgDropdown(query) {
    const dropdown = document.getElementById('taskModalOrgDropdown');
    const orgs = window.TASK_MODAL_PROSPECT_ORGS || [];
    const q = (query || '').toLowerCase();
    const matches = q
      ? orgs.filter(o => o.toLowerCase().includes(q))
      : orgs;
    if (!matches.length) {
      dropdown.innerHTML = '<div class="task-modal-org-option task-modal-org-none">No matches</div>';
      return;
    }
    dropdown.innerHTML = [{ value: '', label: '— none —' }]
      .concat(matches.map(o => ({ value: o, label: o })))
      .map(item => `<div class="task-modal-org-option" data-value="${item.value}">${item.label}</div>`)
      .join('');
    dropdown.querySelectorAll('.task-modal-org-option').forEach(el => {
      el.addEventListener('mousedown', function () {
        const val = this.dataset.value;
        document.getElementById('taskModalOrgSearch').value = val;
        _org = val;
        dropdown.style.display = 'none';
      });
    });
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

  // ---------------------------------------------------------------------------
  // Send Nudge from Modal
  // ---------------------------------------------------------------------------

  function sendNudgeFromModal() {
    const assignee = document.getElementById('taskModalAssigneeSearch').value.trim();
    const taskText = document.getElementById('taskModalText').value.trim();
    const org = _org || '';

    if (!assignee) {
      alert('Please assign this task to someone first.');
      return;
    }

    showModalNudgeOptions(assignee, org, taskText);
  }

  function showModalNudgeOptions(assignedTo, org, taskText) {
    document.querySelectorAll('.task-nudge-dropdown').forEach(d => d.remove());

    const dropdown = document.createElement('div');
    dropdown.className = 'task-nudge-dropdown';
    dropdown.innerHTML = `
      <div class="task-nudge-option" data-template="confirm">Confirm task</div>
      <div class="task-nudge-option" data-template="followup">Follow up</div>
      <div class="task-nudge-option" data-template="new">New assignment</div>
    `;

    const nudgeBtn = document.getElementById('taskModalNudgeBtn');
    const rect = nudgeBtn.getBoundingClientRect();
    dropdown.style.position = 'fixed';
    dropdown.style.top = (rect.bottom + 4) + 'px';
    dropdown.style.left = rect.left + 'px';
    dropdown.style.zIndex = '10000';

    document.body.appendChild(dropdown);

    dropdown.querySelectorAll('.task-nudge-option').forEach(opt => {
      opt.addEventListener('click', (e) => {
        e.stopPropagation();
        const template = opt.dataset.template;
        dropdown.remove();
        buildModalNudgeEmail(template, assignedTo, org, taskText);
      });
    });

    setTimeout(() => {
      document.addEventListener('click', closeNudgeDropdown);
    }, 0);

    function closeNudgeDropdown(e) {
      if (!dropdown.contains(e.target)) {
        dropdown.remove();
        document.removeEventListener('click', closeNudgeDropdown);
      }
    }
  }

  function buildModalNudgeEmail(template, assignedTo, org, taskText) {
    const teamMap = window.TASK_MODAL_TEAM_MAP || [];

    let teamMember = teamMap.find(m =>
      m.full.toLowerCase() === assignedTo.toLowerCase() ||
      m.short.toLowerCase() === assignedTo.toLowerCase() ||
      assignedTo.toLowerCase().includes(m.full.toLowerCase()) ||
      m.full.toLowerCase().includes(assignedTo.toLowerCase())
    );

    if (!teamMember || !teamMember.email) {
      alert(`No email found for ${assignedTo}`);
      return;
    }

    const assignedEmail = teamMember.email;
    const firstName = assignedTo.split(' ')[0];
    let subject, body;

    const orgContext = org ? ` for ${org}` : '';
    const taskContext = taskText ? `"${taskText}"` : 'this task';

    switch (template) {
      case 'confirm':
        subject = `Task Confirmation${orgContext}`;
        body = `Hey ${firstName},\n\nI wanted to confirm that you have this on your plate${orgContext}:\n\n${taskContext}\n\nLet me know if anything has changed or if you need support.\n\nThanks,\nOscar`;
        break;

      case 'followup':
        subject = `Status Check${orgContext}`;
        body = `Hey ${firstName},\n\nWanted to check in on the status of this${orgContext}:\n\n${taskContext}\n\nAny updates?\n\nThanks,\nOscar`;
        break;

      case 'new':
        subject = `New Task${orgContext}`;
        body = `Hey ${firstName},\n\nCan you please take this on${orgContext}:\n\n${taskContext}\n\nLet me know if you have any questions.\n\nThanks,\nOscar`;
        break;

      default:
        return;
    }

    const mailto = `mailto:${encodeURIComponent(assignedEmail)}`
      + `?subject=${encodeURIComponent(subject)}`
      + `&body=${encodeURIComponent(body)}`;

    window.open(mailto, '_self');
  }

})();
