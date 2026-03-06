# Task 15 — Add "Delete Prospect" to Prospect Edit Page

## Enhancement
Add a "Delete Prospect" button to the full-page prospect editor (`crm_prospect_edit.html`) that removes the prospect from `prospects.md`.

## Files to Modify
- `app/templates/crm_prospect_edit.html`
- `app/delivery/dashboard.py` (add DELETE API endpoint)
- `app/sources/crm_reader.py` (expose delete function if not already)

## Current Behavior
`crm_reader.py` already has a `delete_prospect(org, offering)` function (line ~708-735) that removes a prospect block from `prospects.md`. However, there is no API endpoint or UI to trigger it.

## Required Changes

### 1. dashboard.py — Add DELETE endpoint

Add a new route in the CRM blueprint:

```python
@crm_bp.route('/api/prospect', methods=['DELETE'])
def api_prospect_delete():
    data = request.get_json(force=True)
    org = data.get('org', '').strip()
    offering = data.get('offering', '').strip()
    if not org or not offering:
        return jsonify({'error': 'org and offering required'}), 400
    try:
        delete_prospect(org, offering)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

Make sure `delete_prospect` is imported from `crm_reader`.

### 2. crm_prospect_edit.html — Add Delete button

In the form footer (line ~211), add a Delete button on the left side:

```html
<div class="form-footer">
  <button class="btn btn-danger" id="delete-btn" onclick="deleteProspect()">Delete Prospect</button>
  <div style="flex:1"></div>
  <button class="btn btn-cancel" onclick="window.location.href='/crm'">Cancel</button>
  <button class="btn btn-save" id="save-btn" onclick="saveProspect()">Save</button>
</div>
```

Add CSS for the danger button:

```css
.btn-danger {
  background: #450a0a;
  color: #fca5a5;
  border: 1px solid #7f1d1d;
}
.btn-danger:hover {
  background: #7f1d1d;
  color: #fef2f2;
}
```

### 3. crm_prospect_edit.html — JavaScript delete function

```javascript
async function deleteProspect() {
  if (!confirm(`Delete ${ORG} from ${OFFERING}? This cannot be undone.`)) return;

  const btn = document.getElementById('delete-btn');
  btn.disabled = true;
  btn.textContent = 'Deleting…';

  const resp = await fetch('/crm/api/prospect', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ org: ORG, offering: OFFERING }),
  });

  if (resp.ok) {
    window.location.href = '/crm';
  } else {
    const err = await resp.json().catch(() => ({}));
    showError(err.error || 'Delete failed.');
    btn.disabled = false;
    btn.textContent = 'Delete Prospect';
  }
}
```

## Important Notes
- This only deletes the prospect record from `prospects.md`. It does NOT delete the organization from `organizations.md` or contacts from `contacts_index.md`.
- The confirm dialog should clearly state what is being deleted.

## Testing
1. Open Pipeline → click a prospect → click "Prospect" to open edit page
2. "Delete Prospect" button should be visible in red/danger style on left of footer
3. Click Delete → confirm dialog appears
4. Confirm → prospect is removed from `prospects.md`, redirects to Pipeline
5. Verify the prospect no longer appears in Pipeline
6. Verify the org still exists in `organizations.md`
