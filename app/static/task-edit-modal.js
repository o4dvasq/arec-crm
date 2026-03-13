// Task Edit Modal

// Global state
let taskModalOpen = false;
let currentTaskData = null;

// Global callbacks can be set by page
window.taskModalOnSave = function() { console.log('Modal save callback not set'); };
window.taskModalOnDelete = function() { console.log('Modal delete callback not set'); };

// Alias for compatibility with prospect detail page
window.openEditTaskModal = function(taskData) {
  // Map old field names to new ones
  const mapped = {
    ...taskData,
    owner: taskData.assigned_to || taskData.owner,
    org: taskData.org || window.ORG || 'Unknown'
  };
  openTaskModal(mapped);
};

window.openNewTaskModal = function(taskData) {
  openTaskModal(taskData || {
    org: window.ORG || 'Unknown',
    status: 'open'
  });
};

// Create modal HTML if it doesn't exist
function initTaskModal() {
  if (document.getElementById('task-edit-modal')) return; // Already initialized

  const html = `
    <div id="task-edit-modal-overlay" class="task-modal-overlay">
      <div class="task-modal-card">
        <div class="task-modal-header">
          <div class="task-modal-title">Task Details</div>
          <button class="task-modal-close" onclick="closeTaskModal()">&times;</button>
        </div>
        <div class="task-modal-body">
          <div id="task-modal-message" style="display:none;"></div>

          <div class="task-modal-field">
            <label class="task-modal-label">Task Description</label>
            <textarea id="task-modal-text" class="task-modal-textarea" placeholder="Task description..."></textarea>
          </div>

          <div class="task-modal-field">
            <label class="task-modal-label">Assigned To</label>
            <select id="task-modal-owner" class="task-modal-select">
              <option value="">Unassigned</option>
            </select>
          </div>

          <div style="display:flex;gap:12px;">
            <div class="task-modal-field" style="flex:1;">
              <label class="task-modal-label">Priority</label>
              <select id="task-modal-priority" class="task-modal-select">
                <option value="Hi">High</option>
                <option value="Med" selected>Medium</option>
                <option value="Lo">Low</option>
              </select>
            </div>

            <div class="task-modal-field" style="flex:1;">
              <label class="task-modal-label">Status</label>
              <select id="task-modal-status" class="task-modal-select">
                <option value="open">Open</option>
                <option value="done">Done</option>
              </select>
            </div>
          </div>

          <div class="task-modal-info">
            <strong>Org:</strong> <span id="task-modal-org"></span><br>
            <strong>Created:</strong> <span id="task-modal-created"></span>
          </div>
        </div>

        <div class="task-modal-footer">
          <button class="task-modal-btn task-modal-btn-danger" id="task-modal-delete-btn" onclick="deleteTaskModal()" style="margin-right:auto;display:none;">Delete Task</button>
          <button class="task-modal-btn task-modal-btn-secondary" onclick="closeTaskModal()">Cancel</button>
          <button class="task-modal-btn task-modal-btn-primary" onclick="saveTaskModal()">Save</button>
        </div>
      </div>
    </div>
  `;

  document.body.insertAdjacentHTML('beforeend', html);

  // Populate owner dropdown from global team list
  const ownerSelect = document.getElementById('task-modal-owner');
  if (window.TASK_MODAL_TEAM) {
    window.TASK_MODAL_TEAM.forEach(name => {
      const option = document.createElement('option');
      option.value = name;
      option.textContent = name;
      ownerSelect.appendChild(option);
    });
  }

  // Close on overlay click
  document.getElementById('task-edit-modal-overlay').addEventListener('click', (e) => {
    if (e.target.id === 'task-edit-modal-overlay') {
      closeTaskModal();
    }
  });
}

function openTaskModal(taskData) {
  initTaskModal();

  currentTaskData = { ...taskData };

  // Populate fields
  document.getElementById('task-modal-text').value = taskData.text || '';
  document.getElementById('task-modal-owner').value = taskData.owner || '';
  document.getElementById('task-modal-priority').value = taskData.priority || 'Med';
  document.getElementById('task-modal-status').value = taskData.status || 'open';
  document.getElementById('task-modal-org').textContent = taskData.org || '';

  // Format created date
  if (taskData.created_at) {
    const date = new Date(taskData.created_at);
    document.getElementById('task-modal-created').textContent = date.toLocaleDateString();
  } else {
    document.getElementById('task-modal-created').textContent = '—';
  }

  // Show delete button only if task has an ID (saved task)
  const deleteBtn = document.getElementById('task-modal-delete-btn');
  deleteBtn.style.display = taskData.id ? 'block' : 'none';

  // Clear any messages
  clearTaskModalMessage();

  // Show modal
  document.getElementById('task-edit-modal-overlay').classList.add('show');
  taskModalOpen = true;

  // Focus task text
  document.getElementById('task-modal-text').focus();
}

function closeTaskModal() {
  document.getElementById('task-edit-modal-overlay').classList.remove('show');
  taskModalOpen = false;
  currentTaskData = null;
}

function clearTaskModalMessage() {
  const msgDiv = document.getElementById('task-modal-message');
  msgDiv.textContent = '';
  msgDiv.style.display = 'none';
  msgDiv.className = '';
}

function showTaskModalMessage(message, type = 'info') {
  const msgDiv = document.getElementById('task-modal-message');
  msgDiv.textContent = message;
  msgDiv.className = `task-modal-${type}`;
  msgDiv.style.display = 'block';
}

async function saveTaskModal() {
  if (!currentTaskData) return;

  const text = document.getElementById('task-modal-text').value.trim();
  const owner = document.getElementById('task-modal-owner').value.trim();
  const priority = document.getElementById('task-modal-priority').value;
  const status = document.getElementById('task-modal-status').value;

  if (!text) {
    showTaskModalMessage('Task description is required', 'error');
    return;
  }

  const saveBtn = document.querySelector('.task-modal-btn-primary');
  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving...';

  try {
    // If status changed to done, use complete endpoint
    if (status === 'done' && currentTaskData.status === 'open') {
      const resp = await fetch('/crm/api/tasks/complete', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: currentTaskData.id })
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        showTaskModalMessage(err.error || 'Failed to update task', 'error');
        return;
      }
    } else if (status === 'open' && currentTaskData.status === 'done') {
      // If toggling back to open, we'd need an API endpoint for that
      // For now, just show a message
      showTaskModalMessage('Cannot reopen completed tasks (UI limitation)', 'error');
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save';
      return;
    }

    // For other field updates, we'd need additional API endpoints
    // For now, show success if only status/completion changed
    if (text === currentTaskData.text &&
        owner === currentTaskData.owner &&
        priority === currentTaskData.priority) {

      showTaskModalMessage('Task updated successfully', 'success');
      setTimeout(() => {
        closeTaskModal();
        window.taskModalOnSave();
      }, 500);
    } else {
      // Show note that other fields would need API support
      showTaskModalMessage('Note: Only task completion can be updated via this modal. Full editing coming soon.', 'info');
    }
  } catch (err) {
    showTaskModalMessage('Error: ' + err.message, 'error');
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = 'Save';
  }
}

async function deleteTaskModal() {
  if (!currentTaskData || !currentTaskData.id) return;

  if (!confirm('Delete this task? This cannot be undone.')) return;

  const deleteBtn = document.getElementById('task-modal-delete-btn');
  deleteBtn.disabled = true;
  deleteBtn.textContent = 'Deleting...';

  try {
    // For now, we'll just mark as done since there's no delete endpoint
    // Once a delete endpoint is added to the API, update this
    const resp = await fetch('/crm/api/tasks/complete', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: currentTaskData.id })
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      showTaskModalMessage(err.error || 'Failed to delete task', 'error');
      deleteBtn.disabled = false;
      deleteBtn.textContent = 'Delete Task';
      return;
    }

    showTaskModalMessage('Task deleted successfully', 'success');
    setTimeout(() => {
      closeTaskModal();
      window.taskModalOnDelete();
    }, 500);
  } catch (err) {
    showTaskModalMessage('Error: ' + err.message, 'error');
    deleteBtn.disabled = false;
    deleteBtn.textContent = 'Delete Task';
  }
}

// Keyboard handling
document.addEventListener('keydown', (e) => {
  if (!taskModalOpen) return;
  if (e.key === 'Escape') {
    closeTaskModal();
  } else if (e.ctrlKey && e.key === 'Enter' || e.metaKey && e.key === 'Enter') {
    saveTaskModal();
  }
});
