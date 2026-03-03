# CC-03a: Org Click Modal + Prospect Edit Page — Deltas

**Applies to:** CC-02 (pipeline table) and CC-03 (org detail)
**Source:** CRM-ENHANCEMENTS-SPEC.md (prior conversation)
**Depends on:** CC-02 and CC-03 already built

---

## What CC-02/CC-03 Already Built

- Pipeline table at `/crm` with row click → navigates to `/crm/org/<name>`
- Org detail page at `/crm/org/<name>` with profile, contacts, prospects
- Inline editing on pipeline table cells (PATCH API)
- Contacts section on org detail reading from contacts_index → memory/people/
- `create_person_file()` and `get_contacts_for_org()` in crm_reader.py

## What's Missing — 4 Deltas

---

### Delta 1: Org Click Modal (2-Button Chooser)

Replace the current direct navigation on org name click with a modal
that asks whether to open the Prospect record or the Org record.

**Modify:** `templates/crm/pipeline.html` + `static/crm/crm.js` + `static/crm/crm.css`

**Step 1 — Update table row org links:**

Add `data-org` and `data-offering` attributes to each org name cell.
Change from `<a href="/crm/org/...">` to a click handler that opens the modal.

```html
<td class="org-cell"
    data-org="Merseyside Pension Fund"
    data-offering="AREC Debt Fund II">
  <a href="#" class="org-link">Merseyside Pension Fund</a>
</td>
```

**Step 2 — Modal HTML (add to pipeline.html):**

```html
<div id="org-click-modal" class="modal-overlay hidden">
  <div class="modal-card">
    <h3 id="modal-org-name"></h3>
    <p>What would you like to update?</p>
    <div class="modal-buttons">
      <a id="modal-prospect-btn" class="modal-btn modal-btn-primary" href="#">
        <strong>Prospect</strong>
        <span>Stage, target, urgency, etc.</span>
      </a>
      <a id="modal-org-btn" class="modal-btn modal-btn-secondary" href="#">
        <strong>Org</strong>
        <span>Contacts, type, notes</span>
      </a>
    </div>
    <button id="modal-cancel" class="modal-cancel">Cancel</button>
  </div>
</div>
```

**Step 3 — Modal JS (add to crm.js):**

```javascript
document.addEventListener('click', function(e) {
  const orgLink = e.target.closest('.org-link');
  if (!orgLink) return;
  e.preventDefault();

  const cell = orgLink.closest('.org-cell');
  const orgName = cell.dataset.org;
  const offering = cell.dataset.offering;

  document.getElementById('modal-org-name').textContent = orgName;
  document.getElementById('modal-prospect-btn').href =
    '/crm/prospect/' + encodeURIComponent(offering) + '/' + encodeURIComponent(orgName);
  document.getElementById('modal-org-btn').href =
    '/crm/org/' + encodeURIComponent(orgName);

  document.getElementById('org-click-modal').classList.remove('hidden');
});

// Close modal
document.getElementById('modal-cancel').addEventListener('click', function() {
  document.getElementById('org-click-modal').classList.add('hidden');
});
document.getElementById('org-click-modal').addEventListener('click', function(e) {
  if (e.target === this) this.classList.add('hidden');
});
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    document.getElementById('org-click-modal').classList.add('hidden');
  }
});
```

**Step 4 — Modal CSS (add to crm.css):**

```css
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}
.modal-overlay.hidden { display: none; }

.modal-card {
  background: #1e1e3a;
  border: 1px solid #2a2a4a;
  border-radius: 12px;
  padding: 24px;
  width: 360px;
  text-align: center;
}
.modal-card h3 {
  color: #fff;
  margin: 0 0 8px;
  font-size: 18px;
}
.modal-card p {
  color: #94a3b8;
  margin: 0 0 20px;
}

.modal-buttons {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.modal-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 12px;
  border-radius: 8px;
  text-decoration: none;
  min-height: 44px;
  transition: background 0.15s;
}
.modal-btn strong { font-size: 15px; }
.modal-btn span { font-size: 12px; color: #94a3b8; margin-top: 4px; }

.modal-btn-primary {
  background: #2563eb;
  color: #fff;
}
.modal-btn-primary:hover { background: #1d4ed8; }

.modal-btn-secondary {
  background: #334155;
  color: #fff;
}
.modal-btn-secondary:hover { background: #475569; }

.modal-cancel {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  font-size: 13px;
}
.modal-cancel:hover { color: #94a3b8; }
```

---

### Delta 2: Prospect Edit Page

New full-page form at `/crm/prospect/<offering>/<org>` for editing all
prospect fields. This does NOT exist in CC-02 or CC-03.

**New route — add to CRM Blueprint in `delivery/dashboard.py`:**

```python
@crm_bp.route('/prospect/<offering>/<path:org>')
def prospect_edit(offering, org):
    prospect = crm_reader.get_prospect(offering, org)
    if not prospect:
        abort(404)
    config = crm_reader.load_config()
    contacts = crm_reader.get_contacts_for_org(org)
    return render_template('crm/prospect_edit.html',
                           prospect=prospect,
                           config=config,
                           contacts=contacts,
                           offering=offering,
                           org=org)

@crm_bp.route('/api/prospect/save', methods=['POST'])
def prospect_save():
    """Save full prospect form (all fields at once)."""
    data = request.json
    org = data['org']
    offering = data['offering']
    fields = data['fields']  # dict of field_name: value

    for field, value in fields.items():
        crm_reader.update_prospect_field(org, offering, field, value)

    # Auto-update last_touch to today
    today = datetime.now().strftime('%Y-%m-%d')
    crm_reader.update_prospect_field(org, offering, 'last_touch', today)

    return jsonify({'status': 'ok'})
```

**New template:** `templates/crm/prospect_edit.html`

Page layout:
```
┌─────────────────────────────────────┐
│  ← Back to Pipeline                 │
│  Merseyside Pension Fund            │
│  AREC Debt Fund II                  │
├─────────────────────────────────────┤
│  Stage          [6. Verbal       ▼] │
│  Urgency        [High            ▼] │
│  Target         [$50,000,000      ] │
│  Committed      [$0               ] │
│  Closing        [Final           ▼] │
│  Assigned To    [James Walton    ▼] │
│  Primary Contact[Susannah Friar  ▼] │
├─────────────────────────────────────┤
│  Next Action                        │
│  ┌───────────────────────────────┐  │
│  │ Meeting March 2               │  │
│  └───────────────────────────────┘  │
│  Notes                              │
│  ┌───────────────────────────────┐  │
│  │ Sent Credit and Index         │  │
│  │ Comparisons on 2/25           │  │
│  └───────────────────────────────┘  │
├─────────────────────────────────────┤
│  Last Touch     2026-02-25          │
│                 (auto-updated)      │
├─────────────────────────────────────┤
│  [ Cancel ]              [ Save ]   │
└─────────────────────────────────────┘
```

**Field specifications:**

| Field | Input Type | Options Source |
|-------|-----------|----------------|
| Stage | `<select>` | `config.md` pipeline stages |
| Urgency | `<select>` | `config.md` urgency levels |
| Target | `<input type="text">` | Free text, stored as `$X,XXX,XXX` |
| Committed | `<input type="text">` | Free text, stored as `$X,XXX,XXX` |
| Closing | `<select>` | `config.md` closing options + blank |
| Assigned To | `<select>` | `config.md` AREC team roster |
| Primary Contact | `<select>` | `get_contacts_for_org(org)` — see Delta 3 |
| Next Action | `<textarea>` | Free text |
| Notes | `<textarea rows="4">` | Free text |
| Last Touch | Read-only display | Auto-set to today on save |

**Save behavior (JS):**

```javascript
document.getElementById('save-btn').addEventListener('click', async function() {
  const fields = {
    stage: document.getElementById('field-stage').value,
    urgency: document.getElementById('field-urgency').value,
    target: document.getElementById('field-target').value,
    committed: document.getElementById('field-committed').value,
    closing: document.getElementById('field-closing').value,
    assigned_to: document.getElementById('field-assigned_to').value,
    primary_contact: document.getElementById('field-primary_contact').value,
    next_action: document.getElementById('field-next_action').value,
    notes: document.getElementById('field-notes').value,
  };

  const resp = await fetch('/crm/api/prospect/save', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      org: '{{ org }}',
      offering: '{{ offering }}',
      fields: fields
    })
  });

  if (resp.ok) {
    window.location.href = '/crm';
  } else {
    const err = await resp.json();
    showError(err.error || 'Save failed');
  }
});
```

**Cancel:** `window.location.href = '/crm'` — no save, no confirm dialog.

**Styling:** Reuse existing dark navy theme from crm.css. Form fields:
white text on dark input backgrounds, consistent with pipeline table aesthetic.

---

### Delta 3: Primary Contact Dropdown

The prospect edit page (Delta 2) includes a Primary Contact `<select>`
that loads contacts from the unified person model.

**Populate from API:**

The `prospect_edit` route already passes `contacts` to the template.
Render as:

```html
<select id="field-primary_contact">
  <option value="">— Select —</option>
  {% for contact in contacts %}
  <option value="{{ contact.name }}"
          {% if prospect.primary_contact == contact.name %}selected{% endif %}>
    {{ contact.name }}{% if contact.role %} ({{ contact.role }}){% endif %}
  </option>
  {% endfor %}
  <option value="__add_new__">+ Add new contact...</option>
</select>
```

**"Add new contact" inline form:**

When `__add_new__` is selected, show an inline form below the dropdown:

```html
<div id="add-contact-form" class="hidden">
  <input id="new-contact-name" placeholder="Full name" required>
  <input id="new-contact-email" placeholder="Email (optional)">
  <button id="add-contact-btn">Add</button>
</div>
```

**Add contact JS:**

```javascript
document.getElementById('add-contact-btn').addEventListener('click', async function() {
  const name = document.getElementById('new-contact-name').value.trim();
  const email = document.getElementById('new-contact-email').value.trim();
  if (!name) return;

  const resp = await fetch('/crm/api/contact', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      name: name,
      org: '{{ org }}',
      email: email,
      role: '',
      type: 'LP Prospect'
    })
  });

  if (resp.ok) {
    const data = await resp.json();
    // Add new option to dropdown, select it
    const select = document.getElementById('field-primary_contact');
    const opt = new Option(name, name, true, true);
    select.add(opt, select.options[select.options.length - 1]);
    // Hide inline form
    document.getElementById('add-contact-form').classList.add('hidden');
  }
});
```

The `POST /crm/api/contact` route should already exist from CC-03.
It calls `crm_reader.create_person_file()` and updates contacts_index.md.

---

### Delta 4: Person Model Functions — Gaps in crm_reader.py

CC-01/CC-03 should have basic people functions. Verify these exist and
add any that are missing:

**Required functions (check crm_reader.py — add if absent):**

```python
find_person_by_email(email: str) -> dict | None
    # Scan all person files in memory/people/ for matching Email field
    # Cache results in module-level dict for process duration
    # Used by crm_graph_sync.py for enrichment matching

enrich_person_email(slug: str, email: str) -> None
    # Read person file, update the **Email:** line in canonical header
    # Preserve ALL other content exactly (Cowork owns everything below header)
    # Used by Graph auto-capture when email discovered for known contact
```

**Update `crm_graph_sync.py` — add email enrichment step:**

After matching an email/meeting to an org, check if the sender's email
can enrich an existing person file:

```python
# In the auto-capture matching loop:
matched_person = crm_reader.find_person_by_email(sender_email)
if matched_person and not matched_person.get('email') and sender_email:
    crm_reader.enrich_person_email(matched_person['slug'], sender_email)
    log.info(f"Enriched {matched_person['name']} with email {sender_email}")
```

**Update "Link to Org" in unmatched review panel:**

When a user resolves an unmatched contact by linking to an org, also
create a stub person file:

```python
# In POST /crm/api/unmatched/resolve handler:
slug = crm_reader.create_person_file(
    name=unmatched_entry['name'],
    org=data['org_name'],
    email=unmatched_entry['email']
)
# Then remove from unmatched_review.json (existing behavior)
```

**Bootstrap script** (one-time migration, if contacts_index.md is sparse):

Create `app/scripts/bootstrap_contacts_index.py`:

```python
#!/usr/bin/env python3
"""
One-time: bootstrap contacts_index.md from High/Med urgency prospects
that have matching person files in memory/people/.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from sources.crm_reader import (
    load_prospects, load_contacts_index, add_contact_to_index
)

def slugify(name):
    return name.lower().strip().replace(' ', '-').replace("'", "")

def main():
    people_dir = os.path.expanduser(
        '~/Dropbox/Tech/ClaudeProductivity/memory/people')
    prospects = load_prospects()
    found = 0
    missing = 0

    for p in prospects:
        if p.get('urgency') not in ('High', 'Med'):
            continue
        contact = p.get('primary_contact', '').strip()
        if not contact:
            continue
        slug = slugify(contact)
        path = os.path.join(people_dir, slug + '.md')
        if os.path.exists(path):
            add_contact_to_index(p['org'], slug)
            found += 1
            print(f"  FOUND: {contact} → {slug}.md → {p['org']}")
        else:
            missing += 1
            print(f"  MISSING: {contact} → {slug}.md")

    print(f"\nDone. Found: {found}, Missing: {missing}")

if __name__ == '__main__':
    main()
```

Run once:
```bash
python3 ~/Dropbox/Tech/ClaudeProductivity/app/scripts/bootstrap_contacts_index.py
```

---

## Files Modified / Created

| File | Action | Delta |
|------|--------|-------|
| `templates/crm/pipeline.html` | MODIFY | Org link → modal trigger + modal HTML |
| `static/crm/crm.js` | MODIFY | Modal open/close logic |
| `static/crm/crm.css` | MODIFY | Modal overlay + card styles |
| `delivery/dashboard.py` | MODIFY | Add `/crm/prospect/<offering>/<org>` route + save API |
| `templates/crm/prospect_edit.html` | CREATE | Full-page prospect edit form |
| `sources/crm_reader.py` | MODIFY | Add `find_person_by_email()`, `enrich_person_email()` if missing |
| `sources/crm_graph_sync.py` | MODIFY | Add email enrichment step in matching loop |
| `scripts/bootstrap_contacts_index.py` | CREATE | One-time migration script |

---

## Acceptance Criteria (delta-only)

1. Clicking org name in pipeline table shows 2-button modal (Prospect / Org)
2. Modal "Prospect" → navigates to `/crm/prospect/<offering>/<org>`
3. Modal "Org" → navigates to existing `/crm/org/<name>` (unchanged)
4. Modal Cancel / click outside / Escape → closes modal
5. Prospect edit page loads all fields pre-populated from prospects.md
6. Save writes all changed fields, auto-updates last_touch, redirects to `/crm`
7. Primary Contact dropdown populated from contacts_index → person files
8. "Add new contact" creates stub person file + updates index + refreshes dropdown
9. `find_person_by_email()` returns correct person or None
10. `enrich_person_email()` updates Email field without corrupting file content
11. "Link to Org" in unmatched panel also creates stub person file
12. `bootstrap_contacts_index.py` runs cleanly, logs found/missing counts
13. No regressions on pipeline table filters, sorting, inline editing, or offering tabs
