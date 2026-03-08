# Task 14 — Add "New Prospect" Button to Pipeline Page

## Enhancement
Add a "New Prospect" button to the Pipeline page that opens a modal or inline form to create a new prospect directly.

## Files to Modify
- `app/templates/crm_pipeline.html`

## Current Behavior
Prospects can only be created from the Org Detail page (`crm_org_detail.html`) via the "Add to Offering" form, or via the API (`POST /crm/api/prospect`). There's no way to create a prospect directly from the Pipeline view.

## Required Changes

### crm_pipeline.html — Add button to header area

Near the top of the pipeline page (next to the search/filter bar area), add a "New Prospect" button:

```html
<button class="btn btn-primary" onclick="openNewProspectModal()" style="margin-left:auto;">
  + New Prospect
</button>
```

### crm_pipeline.html — New Prospect Modal HTML

Add a modal overlay (similar pattern to the task edit modal):

```html
<div id="newProspectOverlay" class="modal-overlay" style="display:none">
  <div class="modal-card" style="max-width:480px;">
    <div class="modal-head">
      <span>New Prospect</span>
      <button class="modal-close" onclick="closeNewProspectModal()">&times;</button>
    </div>
    <div class="modal-body">
      <div class="field-row">
        <label>Organization *</label>
        <input type="text" id="npOrgName" placeholder="Organization name" autocomplete="off">
      </div>
      <div class="field-row">
        <label>Stage</label>
        <select id="npStage">
          <!-- Populated from CONFIG.stages -->
        </select>
      </div>
      <div class="field-row">
        <label>Target</label>
        <input type="text" id="npTarget" placeholder="$0" value="$0">
      </div>
      <div class="field-row">
        <label>Urgency</label>
        <select id="npUrgency">
          <option value="">— None —</option>
          <!-- Populated from CONFIG.urgency_levels -->
        </select>
      </div>
      <div class="field-row">
        <label>Assigned To</label>
        <select id="npAssignedTo">
          <option value="">— None —</option>
          <!-- Populated from CONFIG.team -->
        </select>
      </div>
    </div>
    <div class="modal-foot">
      <button class="btn btn-ghost" onclick="closeNewProspectModal()">Cancel</button>
      <button class="btn btn-primary" onclick="submitNewProspect()">Create</button>
    </div>
  </div>
</div>
```

### crm_pipeline.html — JavaScript functions

```javascript
function openNewProspectModal() {
  const overlay = document.getElementById('newProspectOverlay');
  // Populate stage dropdown
  const stageSel = document.getElementById('npStage');
  stageSel.innerHTML = CONFIG.stages.map(s =>
    `<option value="${s}" ${s === '1. Prospect' ? 'selected' : ''}>${s}</option>`
  ).join('');
  // Populate urgency dropdown
  const urgSel = document.getElementById('npUrgency');
  urgSel.innerHTML = '<option value="">— None —</option>' +
    CONFIG.urgency_levels.map(u => `<option value="${u}">${u}</option>`).join('');
  // Populate assigned to dropdown
  const teamSel = document.getElementById('npAssignedTo');
  teamSel.innerHTML = '<option value="">— None —</option>' +
    CONFIG.team.map(t => `<option value="${t}">${t}</option>`).join('');
  // Reset fields
  document.getElementById('npOrgName').value = '';
  document.getElementById('npTarget').value = '$0';
  overlay.style.display = 'flex';
  document.getElementById('npOrgName').focus();
}

function closeNewProspectModal() {
  document.getElementById('newProspectOverlay').style.display = 'none';
}

async function submitNewProspect() {
  const org = document.getElementById('npOrgName').value.trim();
  if (!org) {
    document.getElementById('npOrgName').focus();
    return;
  }
  const body = {
    org: org,
    offering: currentOffering,
    stage: document.getElementById('npStage').value,
    target: document.getElementById('npTarget').value,
  };
  const resp = await fetch('/crm/api/prospect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (resp.ok) {
    closeNewProspectModal();
    reloadProspects();
    // Optionally also set urgency and assigned_to via PATCH calls
    const urgency = document.getElementById('npUrgency').value;
    const assignedTo = document.getElementById('npAssignedTo').value;
    if (urgency) {
      await fetch('/crm/api/prospect/field', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ org, offering: currentOffering, field: 'urgency', value: urgency }),
      });
    }
    if (assignedTo) {
      await fetch('/crm/api/prospect/field', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ org, offering: currentOffering, field: 'assigned_to', value: assignedTo }),
      });
    }
    reloadProspects();
  } else {
    const err = await resp.json().catch(() => ({}));
    alert(err.error || 'Failed to create prospect');
  }
}
```

### CSS for the modal
Use the same modal overlay pattern used elsewhere (dark overlay, centered card). Style to match the dark theme of the pipeline page.

```css
.modal-overlay {
  position:fixed; top:0; left:0; right:0; bottom:0;
  background:rgba(0,0,0,0.6); z-index:1000;
  display:flex; align-items:center; justify-content:center;
}
.modal-card {
  background:#1e293b; border:1px solid #334155; border-radius:10px;
  width:100%; padding:0; color:#e2e8f0;
}
.modal-head {
  padding:14px 20px; border-bottom:1px solid #334155;
  display:flex; justify-content:space-between; align-items:center;
  font-weight:600; font-size:16px;
}
.modal-close { background:none; border:none; color:#94a3b8; font-size:20px; cursor:pointer; }
.modal-body { padding:20px; display:flex; flex-direction:column; gap:14px; }
.modal-body .field-row { display:flex; flex-direction:column; gap:4px; }
.modal-body label { font-size:12px; color:#94a3b8; font-weight:600; text-transform:uppercase; }
.modal-body input, .modal-body select {
  padding:8px 10px; background:#0f172a; border:1px solid #334155;
  border-radius:6px; color:#e2e8f0; font-size:14px; font-family:inherit; outline:none;
}
.modal-body input:focus, .modal-body select:focus { border-color:#2563eb; }
.modal-foot {
  padding:14px 20px; border-top:1px solid #334155;
  display:flex; justify-content:flex-end; gap:10px;
}
```

## Backend Note
The existing `POST /crm/api/prospect` endpoint already handles creation. It accepts `{org, offering, stage, target}` and returns 409 if the prospect already exists. No backend changes needed.

## Testing
1. Open Pipeline page — "New Prospect" button should be visible in header
2. Click it — modal opens with Stage defaulting to "1. Prospect"
3. Enter org name, set target, pick urgency → Create
4. Prospect appears in pipeline table
5. Try creating a duplicate → should show error
6. Verify prospect is written to `crm/prospects.md`
