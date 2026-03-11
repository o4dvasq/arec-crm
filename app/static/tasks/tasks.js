/* tasks.js — Kanban board for AREC Tasks */

'use strict';

let allTasks = {};
let toastTimer = null;

const PRIORITY_LABELS = ['Hi', 'Med', 'Low'];
const PRIORITY_ORDER = { 'Hi': 0, 'Med': 1, 'Low': 2 };

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  loadTasks();

  // Close mobile action menus on outside click
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.task-card')) {
      document.querySelectorAll('.task-card.active').forEach(c => c.classList.remove('active'));
    }
  });
});

async function loadTasks() {
  try {
    const res = await fetch('/tasks/api/tasks');
    allTasks = await res.json();
    renderBoard();
  } catch (err) {
    document.getElementById('board').innerHTML =
      '<div style="padding:32px;color:#ef4444">Failed to load tasks.</div>';
  }
}

// ---------------------------------------------------------------------------
// Render
// ---------------------------------------------------------------------------

function renderBoard() {
  const board = document.getElementById('board');
  board.innerHTML = '';
  board.appendChild(renderFundraisingMeColumn());
  board.appendChild(renderFundraisingOthersColumn());
  board.appendChild(renderOtherWorkColumn());
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isOscarTask(t) {
  const a = (t.assigned_to || '').toLowerCase().trim();
  return !t.assigned_to || a === 'oscar' || a === 'oscar vasquez';
}

function firstName(name) {
  // Normalize "Tony Avila", "tony", "@Tony" → "Tony"
  return (name || '').trim().replace(/^@/, '').split(/\s+/)[0];
}

function buildAssigneeGroups(tasks) {
  // Group open tasks by first name (normalizes "Tony Avila" and "Tony" into one group).
  const byPerson = {};
  for (const t of tasks) {
    if (t.complete) continue;
    const raw = t.assigned_to || '';
    const name = raw ? firstName(raw) : '';
    if (!byPerson[name]) byPerson[name] = [];
    byPerson[name].push(t);
  }
  // Sort each person's tasks by priority
  for (const name of Object.keys(byPerson)) {
    byPerson[name].sort((a, b) => (PRIORITY_ORDER[a.priority] || 1) - (PRIORITY_ORDER[b.priority] || 1));
  }
  // Named assignees alphabetically, unassigned last
  const named = Object.keys(byPerson).filter(n => n !== '').sort();
  const names = byPerson[''] ? [...named, ''] : named;
  return { byPerson, names };
}

function renderAssigneeGroups(taskList, byPerson, names, sectionHint) {
  for (const name of names) {
    const personHeader = document.createElement('div');
    personHeader.className = 'team-person-header' + (names.indexOf(name) === 0 ? ' first' : '');
    const label = name === '' ? 'Unassigned' : escHtml(name);
    const initial = name === '' ? '?' : name.charAt(0).toUpperCase();
    personHeader.innerHTML = `
      <div class="avatar ${name === '' ? 'unassigned' : ''}">${initial}</div>
      <span class="assignee-name">${label}</span>
      <span class="team-person-count">${byPerson[name].length}</span>
    `;
    taskList.appendChild(personHeader);

    for (const task of byPerson[name]) {
      taskList.appendChild(renderCard(task, task._section || sectionHint));
    }
  }
}

// ---------------------------------------------------------------------------
// Column: Fundraising - Me  (Oscar-assigned tasks only, priority-grouped)
// ---------------------------------------------------------------------------

function renderFundraisingMeColumn() {
  const section = 'Fundraising - Me';
  const allSectionTasks = allTasks[section] || [];
  const oscarTasks = allSectionTasks.filter(t => isOscarTask(t));
  const openTasks = oscarTasks.filter(t => !t.complete);
  const doneTasks = allSectionTasks.filter(t => t.complete);

  const col = document.createElement('div');
  col.className = 'column';
  col.dataset.section = section;

  col.innerHTML = `
    <div class="col-header">
      <div class="col-title-row">
        <span>Fundraising — Me</span>
        <span class="col-count">${openTasks.length}</span>
      </div>
      <div class="pri-bar"></div>
      <div class="pri-summary"></div>
    </div>
  `;

  const addBtn = document.createElement('button');
  addBtn.className = 'col-add-btn';
  addBtn.textContent = '+ Add task';
  addBtn.addEventListener('click', () => showAddForm(col, section));
  col.appendChild(addBtn);

  const taskList = document.createElement('div');
  taskList.className = 'col-tasks';

  // Group by priority
  const groups = { Hi: [], Med: [], Low: [] };
  for (const task of openTasks) {
    const p = groups[task.priority] ? task.priority : 'Med';
    groups[p].push(task);
  }
  let firstGroup = true;
  for (const pri of PRIORITY_LABELS) {
    if (groups[pri].length === 0) continue;
    const groupHeader = document.createElement('div');
    groupHeader.className = 'priority-group-header pri-' + pri.toLowerCase() + (firstGroup ? ' first' : '');
    groupHeader.innerHTML = `
      <i data-lucide="chevron-down" style="width:14px;height:14px;" class="chevron"></i>
      <span>${pri.toUpperCase()}</span>
      <span class="group-count">${groups[pri].length}</span>
    `;
    lucide.createIcons();

    const groupBody = document.createElement('div');
    groupBody.className = 'priority-group-body';

    // Check localStorage for collapsed state
    const collapseKey = `pri-group-collapsed-${section}-${pri}`;
    const isCollapsed = localStorage.getItem(collapseKey) === 'true';
    if (isCollapsed) {
      groupHeader.classList.add('collapsed');
      groupBody.classList.add('collapsed');
      groupBody.style.maxHeight = '0';
    } else {
      groupBody.style.maxHeight = 'none';
    }

    taskList.appendChild(groupHeader);

    for (const task of groups[pri]) {
      groupBody.appendChild(renderCard(task, section));
    }
    taskList.appendChild(groupBody);

    // Add click handler
    groupHeader.addEventListener('click', () => {
      groupHeader.classList.toggle('collapsed');
      groupBody.classList.toggle('collapsed');
      const collapsed = groupHeader.classList.contains('collapsed');
      localStorage.setItem(collapseKey, collapsed);
      if (collapsed) {
        groupBody.style.maxHeight = '0';
      } else {
        groupBody.style.maxHeight = 'none';
      }
    });

    firstGroup = false;
  }

  if (openTasks.length === 0) {
    const empty = document.createElement('div');
    empty.style.cssText = 'padding:16px;color:#94a3b8;font-size:13px;text-align:center';
    empty.textContent = 'No tasks';
    taskList.appendChild(empty);
  }

  col.appendChild(taskList);

  if (doneTasks.length > 0) {
    col.appendChild(renderDoneFooter(doneTasks, section));
  }

  // Render priority bar
  renderPriorityBar(col, openTasks);

  return col;
}

// ---------------------------------------------------------------------------
// Column: Fundraising - Others  (non-Oscar tasks from Fundraising - Me
//                                + all tasks from Fundraising - Others)
// ---------------------------------------------------------------------------

function renderFundraisingOthersColumn() {
  // Collect non-Oscar open tasks from Fundraising - Me
  const meSection = allTasks['Fundraising - Me'] || [];
  const othersSection = allTasks['Fundraising - Others'] || [];

  const teamFundraisingTasks = meSection
    .filter(t => !t.complete && !isOscarTask(t))
    .map(t => ({ ...t, _section: 'Fundraising - Me' }));

  const othersSectionOpen = othersSection
    .filter(t => !t.complete)
    .map(t => ({ ...t, _section: 'Fundraising - Others' }));

  const allOpen = [...teamFundraisingTasks, ...othersSectionOpen];
  const doneTasks = othersSection.filter(t => t.complete);

  const { byPerson, names } = buildAssigneeGroups(allOpen.map(t => ({ ...t, complete: false })));
  // Rebuild with _section preserved
  const byPersonWithSection = {};
  for (const t of allOpen) {
    const name = t.assigned_to ? firstName(t.assigned_to) : '';
    if (!byPersonWithSection[name]) byPersonWithSection[name] = [];
    byPersonWithSection[name].push(t);
  }
  for (const name of Object.keys(byPersonWithSection)) {
    byPersonWithSection[name].sort((a, b) => (PRIORITY_ORDER[a.priority] || 1) - (PRIORITY_ORDER[b.priority] || 1));
  }

  const col = document.createElement('div');
  col.className = 'column';
  col.dataset.section = 'Fundraising - Others';

  col.innerHTML = `
    <div class="col-header">
      <div class="col-title-row">
        <span>Fundraising — Team</span>
        <span class="col-count">${allOpen.length}</span>
      </div>
      <div class="pri-bar"></div>
      <div class="pri-summary"></div>
    </div>
  `;

  const addBtn = document.createElement('button');
  addBtn.className = 'col-add-btn';
  addBtn.textContent = '+ Add task';
  addBtn.addEventListener('click', () => showAddForm(col, 'Fundraising - Others'));
  col.appendChild(addBtn);

  const taskList = document.createElement('div');
  taskList.className = 'col-tasks';

  renderAssigneeGroups(taskList, byPersonWithSection, names, 'Fundraising - Others');

  if (allOpen.length === 0) {
    const empty = document.createElement('div');
    empty.style.cssText = 'padding:16px;color:#94a3b8;font-size:13px;text-align:center';
    empty.textContent = 'No team tasks';
    taskList.appendChild(empty);
  }

  col.appendChild(taskList);

  if (doneTasks.length > 0) {
    col.appendChild(renderDoneFooter(doneTasks, 'Fundraising - Others'));
  }

  // Render priority bar
  renderPriorityBar(col, allOpen);

  return col;
}

// ---------------------------------------------------------------------------
// Column: Other Work  (all tasks from Other Work, assignee-grouped)
// ---------------------------------------------------------------------------

function renderOtherWorkColumn() {
  const section = 'Other Work';
  const tasks = allTasks[section] || [];
  const openTasks = tasks.filter(t => !t.complete);
  const doneTasks = tasks.filter(t => t.complete);

  const { byPerson, names } = buildAssigneeGroups(openTasks);

  const col = document.createElement('div');
  col.className = 'column';
  col.dataset.section = section;

  col.innerHTML = `
    <div class="col-header">
      <div class="col-title-row">
        <span>Other Work</span>
        <span class="col-count">${openTasks.length}</span>
      </div>
      <div class="pri-bar"></div>
      <div class="pri-summary"></div>
    </div>
  `;

  const addBtn = document.createElement('button');
  addBtn.className = 'col-add-btn';
  addBtn.textContent = '+ Add task';
  addBtn.addEventListener('click', () => showAddForm(col, section));
  col.appendChild(addBtn);

  const taskList = document.createElement('div');
  taskList.className = 'col-tasks';

  renderAssigneeGroups(taskList, byPerson, names, section);

  if (openTasks.length === 0) {
    const empty = document.createElement('div');
    empty.style.cssText = 'padding:16px;color:#94a3b8;font-size:13px;text-align:center';
    empty.textContent = 'No tasks';
    taskList.appendChild(empty);
  }

  col.appendChild(taskList);

  if (doneTasks.length > 0) {
    col.appendChild(renderDoneFooter(doneTasks, section));
  }

  // Render priority bar
  renderPriorityBar(col, openTasks);

  return col;
}

// ---------------------------------------------------------------------------
// Priority bar helper
// ---------------------------------------------------------------------------

function renderPriorityBar(columnEl, tasks) {
  const hi = tasks.filter(t => t.priority === 'Hi').length;
  const med = tasks.filter(t => t.priority === 'Med').length;
  const lo = tasks.length - hi - med;
  const total = tasks.length || 1;

  const bar = columnEl.querySelector('.pri-bar');
  bar.innerHTML = `
    <div class="pri-bar-hi" style="width:${(hi/total)*100}%"></div>
    <div class="pri-bar-med" style="width:${(med/total)*100}%"></div>
    <div class="pri-bar-low" style="width:${(lo/total)*100}%"></div>
  `;

  const summary = columnEl.querySelector('.pri-summary');
  const parts = [];
  if (hi) parts.push(`${hi} Hi`);
  if (med) parts.push(`${med} Med`);
  if (lo) parts.push(`${lo} Lo`);
  summary.textContent = parts.join(' · ');
}

// ---------------------------------------------------------------------------
// Task card
// ---------------------------------------------------------------------------

function renderCard(task, section) {
  const card = document.createElement('div');
  const priorityCls = 'pri-' + (task.priority || 'Med').toLowerCase();
  card.className = 'task-card ' + priorityCls + (task.complete ? ' done' : '');
  card.dataset.index = task.index;
  card.dataset.section = section;

  const orgHtml = task.org
    ? `<div class="task-org"><a href="/crm/org/${encodeURIComponent(task.org)}" class="org-link" onclick="event.stopPropagation()">${escHtml(task.org)}</a></div>`
    : '';

  // Show nudge button only if task has an assignee
  const showNudge = task.assigned_to && task.assigned_to.trim() !== '';

  card.innerHTML = `
    <div class="task-text">${escHtml(task.text)}</div>
    ${orgHtml}
    <div class="task-actions">
      ${task.complete
        ? `<button class="task-action-btn" data-action="restore" title="Restore"><i data-lucide="undo"></i></button>`
        : `<button class="task-action-btn complete" data-action="complete" title="Complete"><i data-lucide="check"></i></button>`
      }
      <button class="task-action-btn" data-action="priority" title="Cycle priority"><i data-lucide="arrow-up-down"></i></button>
      ${showNudge ? `<button class="task-action-btn" data-action="nudge" title="Send email nudge"><i data-lucide="mail"></i></button>` : ''}
      <button class="task-action-btn" data-action="edit" title="Edit"><i data-lucide="pencil"></i></button>
      <button class="task-action-btn delete" data-action="delete" title="Delete"><i data-lucide="trash-2"></i></button>
    </div>
  `;
  lucide.createIcons();

  // Mobile tap to reveal
  card.addEventListener('click', (e) => {
    if (window.innerWidth <= 768 && !e.target.closest('.task-actions')) {
      document.querySelectorAll('.task-card').forEach(c => c.classList.remove('active'));
      card.classList.add('active');
    }
  });

  card.querySelector('[data-action="complete"]')?.addEventListener('click', (e) => {
    e.stopPropagation();
    completeTask(section, task.index, task);
  });
  card.querySelector('[data-action="restore"]')?.addEventListener('click', (e) => {
    e.stopPropagation();
    restoreTask(section, task.index);
  });
  card.querySelector('[data-action="priority"]')?.addEventListener('click', (e) => {
    e.stopPropagation();
    cyclePriority(section, task.index, task.priority);
  });
  card.querySelector('[data-action="nudge"]')?.addEventListener('click', (e) => {
    e.stopPropagation();
    showTaskNudgeOptions(task.assigned_to, task.org || '', task.text, section);
  });
  card.querySelector('[data-action="edit"]')?.addEventListener('click', (e) => {
    e.stopPropagation();
    openTaskEditModal({
      title: 'Edit Task',
      text: task.text,
      priority: task.priority || 'Med',
      status: task.status || 'New',
      context: task.context || '',
      assigned_to: task.assigned_to || 'Oscar',
      section: section,
      index: task.index,
      org: task.org || '',
      showDelete: true,
    });
  });
  card.querySelector('[data-action="delete"]')?.addEventListener('click', (e) => {
    e.stopPropagation();
    if (confirm(`Delete "${task.text}"?`)) deleteTask(section, task.index);
  });

  return card;
}

function renderDoneFooter(doneTasks, section) {
  const footer = document.createElement('div');
  footer.className = 'done-footer';

  const toggle = document.createElement('button');
  toggle.className = 'done-toggle';
  toggle.innerHTML = `<span>Done (${doneTasks.length})</span><i data-lucide="chevron-down"></i>`;
  lucide.createIcons();

  const list = document.createElement('div');
  list.className = 'done-list';

  for (const task of doneTasks) {
    list.appendChild(renderCard(task, section));
  }

  toggle.addEventListener('click', () => {
    list.classList.toggle('open');
    const arrow = toggle.querySelector('i');
    arrow.dataset.lucide = list.classList.contains('open') ? 'chevron-up' : 'chevron-down';
    lucide.createIcons();
  });

  footer.appendChild(toggle);
  footer.appendChild(list);
  return footer;
}

// ---------------------------------------------------------------------------
// Add form
// ---------------------------------------------------------------------------

function showAddForm(col, section) {
  col.querySelectorAll('.inline-form').forEach(f => f.remove());

  const form = document.createElement('div');
  form.className = 'inline-form';

  form.innerHTML = `
    <div class="form-label">New task</div>
    <textarea placeholder="Task description..." rows="2" id="form-text-${slugify(section)}"></textarea>
    <div class="form-row">
      <select id="form-pri-${slugify(section)}">
        ${PRIORITY_LABELS.map(p => `<option value="${p}"${p === 'Med' ? ' selected' : ''}>${p}</option>`).join('')}
      </select>
      <select id="form-owner-${slugify(section)}">
        <option value="">— unassigned —</option>
        ${(CONFIG.team || []).map(t => `<option value="${t.name}">${t.name}</option>`).join('')}
      </select>
    </div>
    <div class="form-actions">
      <button class="form-btn primary" id="form-submit-${slugify(section)}">Add</button>
      <button class="form-btn">Cancel</button>
    </div>
  `;

  form.querySelector('.form-btn:not(.primary)').addEventListener('click', () => form.remove());
  form.querySelector(`#form-submit-${slugify(section)}`).addEventListener('click', async () => {
    const text = form.querySelector('textarea').value.trim();
    const priority = form.querySelector('select').value;
    const owner = form.querySelector(`#form-owner-${slugify(section)}`)?.value.trim() || '';
    if (!text) return;
    await submitAdd(section, { text, priority, context: '', assigned_to: owner });
  });

  const addBtn = col.querySelector('.col-add-btn');
  addBtn.insertAdjacentElement('afterend', form);
  form.querySelector('textarea').focus();
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

async function submitAdd(section, data) {
  const res = await fetch('/tasks/api/task', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ section, ...data }),
  });
  if (res.ok) await loadTasks();
  else showError('Failed to add task');
}

async function completeTask(section, index, task) {
  const res = await fetch(`/tasks/api/task/${encodeURIComponent(section)}/${index}/complete`, {
    method: 'POST',
  });
  if (res.ok) {
    await loadTasks();
    showUndoToast(task.text, section, index);
  } else {
    showError('Failed to complete task');
  }
}

async function restoreTask(section, index) {
  const res = await fetch(`/tasks/api/task/${encodeURIComponent(section)}/${index}/restore`, {
    method: 'POST',
  });
  if (res.ok) await loadTasks();
  else showError('Failed to restore task');
}

async function deleteTask(section, index) {
  const res = await fetch(`/tasks/api/task/${encodeURIComponent(section)}/${index}`, {
    method: 'DELETE',
  });
  if (res.ok) await loadTasks();
  else showError('Failed to delete task');
}

async function cyclePriority(section, index, currentPriority) {
  const cycle = { 'Hi': 'Med', 'Med': 'Low', 'Low': 'Hi' };
  const newPriority = cycle[currentPriority] || 'Med';

  const res = await fetch(`/tasks/api/task/${encodeURIComponent(section)}/${index}/priority`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ priority: newPriority }),
  });
  if (res.ok) await loadTasks();
  else showError('Failed to update priority');
}

// ---------------------------------------------------------------------------
// Toast
// ---------------------------------------------------------------------------

function showUndoToast(taskText, section, index) {
  const toast = document.getElementById('toast');
  toast.className = 'toast';
  toast.innerHTML = `
    <span>Completed: ${escHtml(truncate(taskText, 40))}</span>
    <button class="toast-undo" id="toast-undo-btn">Undo</button>
  `;

  if (toastTimer) clearTimeout(toastTimer);

  document.getElementById('toast-undo-btn').addEventListener('click', async () => {
    clearTimeout(toastTimer);
    toast.className = 'toast hidden';
    await loadTasks();
    const sectionTasks = allTasks[section] || [];
    const doneTasks = sectionTasks.filter(t => t.complete);
    if (doneTasks.length > 0) {
      const lastDone = doneTasks[doneTasks.length - 1];
      await restoreTask(section, lastDone.index);
    }
  });

  toastTimer = setTimeout(() => {
    toast.className = 'toast hidden';
  }, 5000);
}

function showError(msg) {
  const toast = document.getElementById('toast');
  toast.className = 'toast';
  toast.innerHTML = `<span style="color:#fca5a5">${escHtml(msg)}</span>`;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.className = 'toast hidden'; }, 3000);
}

// Status dropdown removed in redesign - status management moved to edit modal

// ---------------------------------------------------------------------------
// Email Nudge
// ---------------------------------------------------------------------------

function showTaskNudgeOptions(assignedTo, org, taskText, section) {
  // Close any existing dropdowns
  document.querySelectorAll('.task-nudge-dropdown').forEach(d => d.remove());

  if (!assignedTo || assignedTo.trim() === '') {
    alert('No assignee for this task.');
    return;
  }

  // Create dropdown
  const dropdown = document.createElement('div');
  dropdown.className = 'task-nudge-dropdown';
  dropdown.innerHTML = `
    <div class="task-nudge-option" data-template="confirm">Confirm task</div>
    <div class="task-nudge-option" data-template="followup">Follow up</div>
    <div class="task-nudge-option" data-template="new">New assignment</div>
  `;

  // Position dropdown
  dropdown.style.position = 'fixed';
  dropdown.style.top = (event.clientY + 4) + 'px';
  dropdown.style.left = event.clientX + 'px';
  dropdown.style.zIndex = '1000';

  document.body.appendChild(dropdown);

  // Handle option clicks
  dropdown.querySelectorAll('.task-nudge-option').forEach(opt => {
    opt.addEventListener('click', (e) => {
      e.stopPropagation();
      const template = opt.dataset.template;
      dropdown.remove();
      buildTaskNudgeEmail(template, assignedTo, org, taskText, section);
    });
  });

  // Close on outside click
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

function buildTaskNudgeEmail(template, assignedTo, org, taskText, section) {
  // Look up assignee's email from CONFIG
  const teamMember = CONFIG.team.find(m =>
    m.name.toLowerCase() === assignedTo.toLowerCase() ||
    assignedTo.toLowerCase().includes(m.name.toLowerCase()) ||
    m.name.toLowerCase().includes(assignedTo.toLowerCase())
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

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function slugify(str) {
  return str.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

function truncate(str, n) {
  return str.length > n ? str.slice(0, n) + '…' : str;
}
