/* tasks.js — Kanban board for AREC Tasks */

'use strict';

let allTasks = {};
let toastTimer = null;

const PRIORITY_LABELS = ['Hi', 'Med', 'Low'];
const PRIORITY_ORDER = { 'Hi': 0, 'Med': 1, 'Low': 2 };

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', loadTasks);

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
  for (const section of SECTIONS) {
    if (section === 'Team Tasks') {
      board.appendChild(renderTeamColumn());
    } else {
      const tasks = allTasks[section] || [];
      board.appendChild(renderColumn(section, tasks));
    }
  }
}

// ---------------------------------------------------------------------------
// Team Tasks column — collects all non-Oscar tasks, grouped by person
// ---------------------------------------------------------------------------

function renderTeamColumn() {
  // Gather all open tasks with an assigned_to that isn't Oscar
  const teamTasks = [];
  for (const section of Object.keys(allTasks)) {
    if (section === 'Done') continue;
    for (const t of (allTasks[section] || [])) {
      if (!t.complete && t.assigned_to && t.assigned_to !== 'Oscar') {
        teamTasks.push({ ...t, _section: section });
      }
    }
  }

  // Group by person
  const byPerson = {};
  for (const t of teamTasks) {
    const name = t.assigned_to;
    if (!byPerson[name]) byPerson[name] = [];
    byPerson[name].push(t);
  }
  // Sort each person's tasks by priority
  for (const name of Object.keys(byPerson)) {
    byPerson[name].sort((a, b) => (PRIORITY_ORDER[a.priority] || 1) - (PRIORITY_ORDER[b.priority] || 1));
  }
  const personNames = Object.keys(byPerson).sort();

  const col = document.createElement('div');
  col.className = 'column';
  col.dataset.section = 'Team Tasks';

  // Header
  const header = document.createElement('div');
  header.className = 'col-header';
  header.innerHTML = `
    <span>Team Tasks</span>
    <span class="col-count">${teamTasks.length}</span>
  `;
  col.appendChild(header);

  // Task list
  const taskList = document.createElement('div');
  taskList.className = 'col-tasks';

  for (const name of personNames) {
    // Person sub-header
    const personHeader = document.createElement('div');
    personHeader.className = 'team-person-header';
    personHeader.innerHTML = `<span class="team-person-badge">@${escHtml(name)}</span><span class="team-person-count">${byPerson[name].length}</span>`;
    taskList.appendChild(personHeader);

    for (const task of byPerson[name]) {
      taskList.appendChild(renderCard(task, task._section || task.section));
    }
  }

  if (personNames.length === 0) {
    const empty = document.createElement('div');
    empty.style.cssText = 'padding:16px;color:#94a3b8;font-size:13px;text-align:center';
    empty.textContent = 'No team tasks';
    taskList.appendChild(empty);
  }

  col.appendChild(taskList);
  return col;
}

// ---------------------------------------------------------------------------
// Standard column
// ---------------------------------------------------------------------------

function renderColumn(section, tasks) {
  const isOscarCol = section === 'Fundraising - Me';

  // Exclude tasks assigned to other team members (those show in Team Tasks)
  if (isOscarCol) {
    tasks = tasks.filter(t => !t.assigned_to || t.assigned_to === 'Oscar');
  }
  const openTasks = tasks.filter(t => !t.complete);
  const doneTasks = tasks.filter(t => t.complete);

  const col = document.createElement('div');
  col.className = 'column';
  col.dataset.section = section;

  // Header — rename Fundraising - Me to Oscar Tasks
  const displayName = isOscarCol ? 'Oscar Tasks' : section;
  const header = document.createElement('div');
  header.className = 'col-header';
  header.innerHTML = `
    <span>${displayName}</span>
    <span class="col-count">${openTasks.length}</span>
  `;
  col.appendChild(header);

  // Add button
  const addBtn = document.createElement('button');
  addBtn.className = 'col-add-btn';
  addBtn.textContent = '+ Add task';
  addBtn.addEventListener('click', () => showAddForm(col, section));
  col.appendChild(addBtn);

  // Task list
  const taskList = document.createElement('div');
  taskList.className = 'col-tasks';

  if (isOscarCol) {
    // Group open tasks by priority
    const groups = { Hi: [], Med: [], Low: [] };
    for (const task of openTasks) {
      const p = groups[task.priority] ? task.priority : 'Med';
      groups[p].push(task);
    }
    let firstGroup = true;
    for (const pri of PRIORITY_LABELS) {
      if (groups[pri].length === 0) continue;
      const groupHeader = document.createElement('div');
      groupHeader.className = 'priority-group-header' + (firstGroup ? ' first' : '');
      groupHeader.innerHTML = `
        <span class="priority-group-badge ${pri.toLowerCase()}">
          <span class="dot"></span>${pri}
        </span>
        <span class="priority-group-count">${groups[pri].length}</span>
      `;
      taskList.appendChild(groupHeader);
      firstGroup = false;
      for (const task of groups[pri]) {
        taskList.appendChild(renderCard(task, section));
      }
    }
  } else {
    for (const task of openTasks) {
      taskList.appendChild(renderCard(task, section));
    }
  }

  col.appendChild(taskList);

  // Done footer
  if (doneTasks.length > 0) {
    col.appendChild(renderDoneFooter(doneTasks, section));
  }

  return col;
}

function renderCard(task, section) {
  const card = document.createElement('div');
  card.className = 'task-card' + (task.complete ? ' done' : '');
  card.dataset.index = task.index;
  card.dataset.section = section;

  const priorityCls = (task.priority || 'Med').toLowerCase();
  const dotTitle = task.complete ? 'Restore' : `Complete (${task.priority})`;
  const orgLink = task.org
    ? ` <a href="/crm/org/${encodeURIComponent(task.org)}" class="org-link" onclick="event.stopPropagation()">${escHtml(task.org)}</a>`
    : '';

  card.innerHTML = `
    <div class="task-card-top">
      <div class="priority-dot ${priorityCls}" title="${dotTitle}"></div>
      <span class="task-text">${escHtml(task.text)}${orgLink}</span>
    </div>
    ${task.context ? `<div class="task-context">${escHtml(task.context)}</div>` : ''}
    <div class="task-actions">
      ${task.complete
        ? `<button class="action-btn" data-action="restore">Restore</button>`
        : `<button class="action-btn" data-action="complete">Complete</button>`
      }
      <button class="action-btn" data-action="edit">Edit</button>
      <button class="action-btn danger" data-action="delete">Delete</button>
    </div>
  `;

  card.querySelector('.priority-dot').addEventListener('click', () => {
    if (task.complete) {
      restoreTask(section, task.index);
    } else if (task.priority === 'Hi') {
      if (confirm(`Complete "${task.text}"?`)) completeTask(section, task.index, task);
    } else {
      completeTask(section, task.index, task);
    }
  });

  card.querySelector('[data-action="complete"]')?.addEventListener('click', () => {
    completeTask(section, task.index, task);
  });
  card.querySelector('[data-action="restore"]')?.addEventListener('click', () => {
    restoreTask(section, task.index);
  });
  card.querySelector('[data-action="edit"]')?.addEventListener('click', () => {
    openTaskEditModal({
      title: 'Edit Task',
      text: task.text,
      priority: task.priority || 'Med',
      assigned_to: task.assigned_to || '',
      section: section,
      index: task.index,
      org: task.org || '',
      showDelete: true,
    });
  });
  card.querySelector('[data-action="delete"]')?.addEventListener('click', () => {
    if (confirm(`Delete "${task.text}"?`)) deleteTask(section, task.index);
  });

  return card;
}

function renderDoneFooter(doneTasks, section) {
  const footer = document.createElement('div');
  footer.className = 'done-footer';

  const toggle = document.createElement('button');
  toggle.className = 'done-toggle';
  toggle.innerHTML = `<span>Done (${doneTasks.length})</span><span>&#9660;</span>`;

  const list = document.createElement('div');
  list.className = 'done-list';

  for (const task of doneTasks) {
    list.appendChild(renderCard(task, section));
  }

  toggle.addEventListener('click', () => {
    list.classList.toggle('open');
    const arrow = toggle.querySelector('span:last-child');
    arrow.innerHTML = list.classList.contains('open') ? '&#9650;' : '&#9660;';
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

  const isWaiting = section === 'Waiting On';

  form.innerHTML = `
    <div class="form-label">New task</div>
    <textarea placeholder="Task description..." rows="2" id="form-text-${slugify(section)}"></textarea>
    <div class="form-row">
      <select id="form-pri-${slugify(section)}">
        ${PRIORITY_LABELS.map(p => `<option value="${p}"${p === 'Med' ? ' selected' : ''}>${p}</option>`).join('')}
      </select>
    </div>
    ${isWaiting ? `
    <div class="form-label">Waiting on</div>
    <input type="text" list="team-list" id="form-owner-${slugify(section)}" placeholder="Person name...">
    <datalist id="team-list">
      ${(CONFIG.team || []).map(t => `<option value="${t}">`).join('')}
    </datalist>
    ` : ''}
    <div class="form-actions">
      <button class="form-btn primary" id="form-submit-${slugify(section)}">Add</button>
      <button class="form-btn">Cancel</button>
    </div>
  `;

  form.querySelector('.form-btn:not(.primary)').addEventListener('click', () => form.remove());
  form.querySelector(`#form-submit-${slugify(section)}`).addEventListener('click', async () => {
    const text = form.querySelector('textarea').value.trim();
    const priority = form.querySelector('select').value;
    const owner = isWaiting ? (form.querySelector(`#form-owner-${slugify(section)}`)?.value.trim() || '') : '';
    const context = isWaiting && owner ? `for: ${owner}` : '';
    if (!text) return;
    await submitAdd(section, { text, priority, context, assigned_to: owner });
  });

  const addBtn = col.querySelector('.col-add-btn');
  addBtn.insertAdjacentElement('afterend', form);
  form.querySelector('textarea').focus();
}

// (Edit form replaced by shared task-edit-modal.js)

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

async function submitEdit(section, index, data) {
  const res = await fetch(`/tasks/api/task/${encodeURIComponent(section)}/${index}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (res.ok) await loadTasks();
  else showError('Failed to save task');
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
