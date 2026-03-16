/* tasks.js — Owner-grouped Kanban board for AREC Tasks */

'use strict';

let allTasks = {};
let toastTimer = null;

const PRIORITY_LABELS = ['Hi', 'Med', 'Low'];
const PRIORITY_ORDER = { 'Hi': 0, 'Med': 1, 'Low': 2, 'Lo': 2 };

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  loadTasks();

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
// Render board — owner-grouped, Oscar first
// ---------------------------------------------------------------------------

function renderBoard() {
  const board = document.getElementById('board');
  board.innerHTML = '';

  // Gather all tasks tagged with their section
  const openTasks = [];
  const doneTasks = [];
  for (const [section, tasks] of Object.entries(allTasks)) {
    for (const task of tasks) {
      const tagged = { ...task, _section: section };
      if (task.complete) {
        doneTasks.push(tagged);
      } else {
        openTasks.push(tagged);
      }
    }
  }

  // Group open tasks by owner key
  const byOwner = {};
  for (const task of openTasks) {
    const key = ownerKey(task.assigned_to);
    if (!byOwner[key]) byOwner[key] = [];
    byOwner[key].push(task);
  }

  // Sort each owner's tasks by priority
  for (const key of Object.keys(byOwner)) {
    byOwner[key].sort((a, b) => (PRIORITY_ORDER[a.priority] || 1) - (PRIORITY_ORDER[b.priority] || 1));
  }

  // Oscar first, then other owners alphabetically
  const oscarKey = '__oscar__';
  const otherKeys = Object.keys(byOwner)
    .filter(k => k !== oscarKey)
    .sort((a, b) => a.localeCompare(b));
  const ownerOrder = byOwner[oscarKey] ? [oscarKey, ...otherKeys] : otherKeys;

  for (const key of ownerOrder) {
    board.appendChild(renderOwnerGroup(key, byOwner[key]));
  }

  if (ownerOrder.length === 0) {
    const empty = document.createElement('div');
    empty.style.cssText = 'padding:40px;color:#94a3b8;font-size:14px;text-align:center';
    empty.textContent = 'No open tasks.';
    board.appendChild(empty);
  }

  // Done footer at bottom (all done tasks)
  if (doneTasks.length > 0) {
    board.appendChild(renderDoneFooter(doneTasks));
  }
}

function ownerKey(assignedTo) {
  const a = (assignedTo || '').toLowerCase().trim();
  if (!a || a === 'oscar' || a === 'oscar vasquez') return '__oscar__';
  return a.split(/\s+/)[0];
}

function ownerDisplayName(key) {
  if (key === '__oscar__') return 'Oscar Vasquez';
  return key.charAt(0).toUpperCase() + key.slice(1);
}

// ---------------------------------------------------------------------------
// Owner group
// ---------------------------------------------------------------------------

function renderOwnerGroup(key, tasks) {
  const displayName = ownerDisplayName(key);
  const initial = displayName.charAt(0).toUpperCase();

  const group = document.createElement('div');
  group.className = 'owner-group';
  group.dataset.ownerKey = key;

  const header = document.createElement('div');
  header.className = 'owner-group-header';
  header.innerHTML = `
    <div class="avatar">${escHtml(initial)}</div>
    <span class="owner-name">${escHtml(displayName)}</span>
    <span class="owner-count">${tasks.length}</span>
    <button class="owner-add-btn">+ Add</button>
  `;
  group.appendChild(header);

  header.querySelector('.owner-add-btn').addEventListener('click', (e) => {
    e.stopPropagation();
    const ownerName = key === '__oscar__' ? 'Oscar Vasquez' : displayName;
    showAddFormForOwner(group, null, ownerName);
  });

  const taskContainer = document.createElement('div');
  taskContainer.className = 'owner-tasks';

  for (const task of tasks) {
    taskContainer.appendChild(renderCard(task, task._section));
  }

  group.appendChild(taskContainer);
  return group;
}

// ---------------------------------------------------------------------------
// Task card
// ---------------------------------------------------------------------------

function renderCard(task, section) {
  const card = document.createElement('div');
  const pri = task.priority || 'Med';
  const priorityCls = 'pri-' + pri.toLowerCase();
  card.className = 'task-card ' + priorityCls + (task.complete ? ' done' : '');
  card.dataset.index = task.index;
  card.dataset.section = section;

  const orgHtml = task.org
    ? `<a href="/crm/org/${encodeURIComponent(task.org)}" class="org-link" onclick="event.stopPropagation()">${escHtml(task.org)}</a>`
    : '';

  const sectionLabel = section ? escHtml(section) : '';
  const metaParts = [orgHtml, sectionLabel].filter(Boolean);
  const metaHtml = metaParts.length
    ? `<div class="task-meta-line">${metaParts.join(' · ')}</div>`
    : '';

  const showNudge = task.assigned_to && task.assigned_to.trim() !== '';

  card.innerHTML = `
    <div class="task-card-top">
      <span class="pri-badge pri-badge-${pri.toLowerCase()}">${escHtml(pri)}</span>
      <div class="task-text">${escHtml(task.text)}</div>
    </div>
    ${metaHtml}
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

function renderDoneFooter(doneTasks) {
  const footer = document.createElement('div');
  footer.className = 'done-footer';

  const toggle = document.createElement('button');
  toggle.className = 'done-toggle';
  toggle.innerHTML = `<span>Done (${doneTasks.length})</span><i data-lucide="chevron-down"></i>`;
  lucide.createIcons();

  const list = document.createElement('div');
  list.className = 'done-list';

  for (const task of doneTasks) {
    list.appendChild(renderCard(task, task._section));
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

function showAddFormForOwner(groupEl, defaultSection, ownerName) {
  groupEl.querySelectorAll('.inline-form').forEach(f => f.remove());

  const sections = window.TASK_MODAL_SECTIONS || ['Fundraising - Me', 'Fundraising - Others', 'Other Work'];
  const slugId = slugify(ownerName);

  const form = document.createElement('div');
  form.className = 'inline-form';
  form.innerHTML = `
    <div class="form-label">New task for ${escHtml(ownerName)}</div>
    <textarea placeholder="Task description..." rows="2" id="form-text-${slugId}"></textarea>
    <div class="form-row">
      <select id="form-pri-${slugId}">
        ${PRIORITY_LABELS.map(p => `<option value="${p}"${p === 'Med' ? ' selected' : ''}>${p}</option>`).join('')}
      </select>
      <select id="form-section-${slugId}">
        ${sections.map(s => `<option value="${s}"${s === defaultSection ? ' selected' : ''}>${s}</option>`).join('')}
      </select>
    </div>
    <div class="form-actions">
      <button class="form-btn primary" id="form-submit-${slugId}">Add</button>
      <button class="form-btn">Cancel</button>
    </div>
  `;

  form.querySelector('.form-btn:not(.primary)').addEventListener('click', () => form.remove());
  form.querySelector(`#form-submit-${slugId}`).addEventListener('click', async () => {
    const text = form.querySelector('textarea').value.trim();
    const priority = form.querySelector(`#form-pri-${slugId}`).value;
    const section = form.querySelector(`#form-section-${slugId}`).value;
    if (!text) return;
    await submitAdd(section, { text, priority, context: '', assigned_to: ownerName });
  });

  const header = groupEl.querySelector('.owner-group-header');
  header.insertAdjacentElement('afterend', form);
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
    const done = sectionTasks.filter(t => t.complete);
    if (done.length > 0) {
      await restoreTask(section, done[done.length - 1].index);
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

// ---------------------------------------------------------------------------
// Email Nudge
// ---------------------------------------------------------------------------

function showTaskNudgeOptions(assignedTo, org, taskText, section) {
  document.querySelectorAll('.task-nudge-dropdown').forEach(d => d.remove());

  if (!assignedTo || assignedTo.trim() === '') {
    alert('No assignee for this task.');
    return;
  }

  const dropdown = document.createElement('div');
  dropdown.className = 'task-nudge-dropdown';
  dropdown.innerHTML = `
    <div class="task-nudge-option" data-template="confirm">Confirm task</div>
    <div class="task-nudge-option" data-template="followup">Follow up</div>
    <div class="task-nudge-option" data-template="new">New assignment</div>
  `;

  dropdown.style.position = 'fixed';
  dropdown.style.top = (event.clientY + 4) + 'px';
  dropdown.style.left = event.clientX + 'px';
  dropdown.style.zIndex = '1000';

  document.body.appendChild(dropdown);

  dropdown.querySelectorAll('.task-nudge-option').forEach(opt => {
    opt.addEventListener('click', (e) => {
      e.stopPropagation();
      const template = opt.dataset.template;
      dropdown.remove();
      buildTaskNudgeEmail(template, assignedTo, org, taskText, section);
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

function buildTaskNudgeEmail(template, assignedTo, org, taskText, section) {
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
