# Task 7: Add Tasks and Notes columns to CRM Pipeline screen

## Overview

Replace the now-removed "Next Action" column with a "Tasks" column that pulls open tasks from TASKS.md, and make the "Notes" column visible by default. The Tasks column should show both the task description and owner.

## Files to change

1. `app/sources/crm_reader.py` — add task parser
2. `app/delivery/dashboard.py` — enrich API response
3. `app/templates/crm_pipeline.html` — update frontend columns

---

## Change 1: `app/sources/crm_reader.py` — Add TASKS.md parser

Add a new function after the existing `load_prospects` section (~line 595):

```python
# ---------------------------------------------------------------------------
# Tasks (from TASKS.md)
# ---------------------------------------------------------------------------

def load_tasks_by_org() -> dict[str, list[dict]]:
    """Parse TASKS.md and return open tasks grouped by org name.

    Returns: { 'UTIMCO': [{'task': 'Follow up with Jared...', 'owner': 'Oscar'}, ...], ... }

    Tasks are matched to orgs via the (OrgName) suffix convention.
    Only open tasks (unchecked) are included. Excludes Personal and Done sections.
    """
    tasks_path = os.path.join(PROJECT_ROOT, "TASKS.md")
    if not os.path.exists(tasks_path):
        return {}

    text = _read_file(tasks_path)
    result: dict[str, list[dict]] = {}
    in_section = False

    for line in text.splitlines():
        stripped = line.strip()

        # Track which section we're in — include all except Personal and Done
        if stripped.startswith('## '):
            section_name = stripped[3:].strip()
            in_section = section_name not in ('Personal', 'Done')
            continue

        if not in_section:
            continue

        # Only open (unchecked) tasks
        if not stripped.startswith('- [ ]'):
            continue

        # Extract owner: **@Name**
        owner_match = re.search(r'\*\*@(\w+)\*\*', stripped)
        owner = owner_match.group(1) if owner_match else 'Oscar'

        # Extract org: (OrgName) at end of line
        org_match = re.search(r'\(([^)]+)\)\s*$', stripped)
        if not org_match:
            continue  # Not a CRM task

        org_name = org_match.group(1).strip()

        # Extract task description: everything between owner tag and (OrgName)
        # Remove the prefix "- [ ] **[Pri]** **@Owner** " and the trailing "(OrgName)"
        desc = stripped
        desc = re.sub(r'^- \[ \]\s*\*\*\[\w+\]\*\*\s*', '', desc)  # Remove checkbox + priority
        desc = re.sub(r'\*\*@\w+\*\*\s*', '', desc)  # Remove owner tag
        desc = re.sub(r'\s*\([^)]+\)\s*$', '', desc)  # Remove trailing (OrgName)
        desc = desc.strip(' —-')  # Clean up leftover separators

        result.setdefault(org_name, []).append({
            'task': desc,
            'owner': owner,
        })

    return result
```

Also update `PROSPECT_FIELD_ORDER` (line ~18) to remove `"Next Action"`:

Before:
```python
PROSPECT_FIELD_ORDER = [
    "Stage", "Target", "Committed", "Primary Contact",
    "Closing", "Urgency", "Assigned To", "Notes", "Next Action", "Last Touch"
]
```

After:
```python
PROSPECT_FIELD_ORDER = [
    "Stage", "Target", "Committed", "Primary Contact",
    "Closing", "Urgency", "Assigned To", "Notes", "Last Touch"
]
```

And remove `'next_action'` from `EDITABLE_FIELDS` (line ~23):

Before:
```python
EDITABLE_FIELDS = {
    'stage', 'urgency', 'target', 'assigned_to',
    'next_action', 'notes', 'closing'
}
```

After:
```python
EDITABLE_FIELDS = {
    'stage', 'urgency', 'target', 'assigned_to',
    'notes', 'closing'
}
```

---

## Change 2: `app/delivery/dashboard.py` — Enrich API response with tasks

Update the `api_prospects()` function (~line 244) to attach tasks from TASKS.md to each prospect:

Before:
```python
@crm_bp.route('/api/prospects')
def api_prospects():
    offering = request.args.get('offering', '')
    include_closed = request.args.get('include_closed', 'false').lower() == 'true'
    prospects = load_prospects(offering if offering else None)
    if not include_closed:
        excluded = {'9. Closed', '0. Not Pursuing', 'Declined'}
        prospects = [p for p in prospects if p.get('Stage', '') not in excluded]
    return jsonify(prospects)
```

After:
```python
@crm_bp.route('/api/prospects')
def api_prospects():
    offering = request.args.get('offering', '')
    include_closed = request.args.get('include_closed', 'false').lower() == 'true'
    prospects = load_prospects(offering if offering else None)
    if not include_closed:
        excluded = {'9. Closed', '0. Not Pursuing', 'Declined'}
        prospects = [p for p in prospects if p.get('Stage', '') not in excluded]

    # Enrich with tasks from TASKS.md
    tasks_by_org = load_tasks_by_org()
    for p in prospects:
        org_name = p.get('org', '')
        org_tasks = tasks_by_org.get(org_name, [])
        # Format: "[@Owner] Task description" joined by " | " for multiple
        if org_tasks:
            p['Tasks'] = ' | '.join(
                f"[@{t['owner']}] {t['task']}" for t in org_tasks
            )
        else:
            p['Tasks'] = ''

    return jsonify(prospects)
```

Also add `load_tasks_by_org` to the imports at the top of the file. Find where `crm_reader` functions are imported and add it:

```python
from app.sources.crm_reader import (
    ...,
    load_tasks_by_org,
)
```

---

## Change 3: `app/templates/crm_pipeline.html` — Update frontend columns

### 3a. Replace `next_action` with `tasks` in FIELD_MAP (~line 357)

Before:
```javascript
const FIELD_MAP = {
  org:               'org',
  urgency:           'Urgency',
  stage:             'Stage',
  target_display:    'Target',
  next_action:       'Next Action',
  org_type:          'Type',
  assigned_to:       'Assigned To',
  closing:           'Closing',
  primary_contact:   'Primary Contact',
  last_touch:        'Last Touch',
  committed_display: 'Committed',
  notes:             'Notes',
};
```

After:
```javascript
const FIELD_MAP = {
  org:               'org',
  urgency:           'Urgency',
  stage:             'Stage',
  target_display:    'Target',
  tasks:             'Tasks',
  org_type:          'Type',
  assigned_to:       'Assigned To',
  closing:           'Closing',
  primary_contact:   'Primary Contact',
  last_touch:        'Last Touch',
  committed_display: 'Committed',
  notes:             'Notes',
};
```

### 3b. Replace `next_action` with `tasks` in PATCH_FIELD_MAP (~line 373)

Remove the `next_action` entry entirely (tasks are not editable inline — they live in TASKS.md):

Before:
```javascript
const PATCH_FIELD_MAP = {
  urgency:        'urgency',
  stage:          'stage',
  target_display: 'target',
  next_action:    'next_action',
  assigned_to:    'assigned_to',
  closing:        'closing',
};
```

After:
```javascript
const PATCH_FIELD_MAP = {
  urgency:        'urgency',
  stage:          'stage',
  target_display: 'target',
  assigned_to:    'assigned_to',
  closing:        'closing',
};
```

### 3c. Replace `next_action` with `tasks` in EDITABLE_KEYS (~line 383)

Remove `next_action` (tasks are read-only in the CRM table):

Before:
```javascript
const EDITABLE_KEYS = new Set(['urgency', 'stage', 'target_display', 'next_action', 'assigned_to', 'closing']);
```

After:
```javascript
const EDITABLE_KEYS = new Set(['urgency', 'stage', 'target_display', 'assigned_to', 'closing']);
```

### 3d. Replace `next_action` with `tasks` in DEFAULT_COLUMNS and make both `tasks` and `notes` visible (~line 397)

Before:
```javascript
const DEFAULT_COLUMNS = [
  { key: 'org',              label: 'Organization',    visible: true,  locked: true  },
  { key: 'urgency',          label: 'Urgency',         visible: true,  locked: false },
  { key: 'stage',            label: 'Stage',           visible: true,  locked: false },
  { key: 'target_display',   label: 'Expected',        visible: true,  locked: false },
  { key: 'next_action',      label: 'Next Action',     visible: true,  locked: false },
  { key: 'org_type',         label: 'Type',            visible: false, locked: false },
  { key: 'assigned_to',      label: 'Assigned To',     visible: false, locked: false },
  { key: 'closing',          label: 'Closing',         visible: false, locked: false },
  { key: 'primary_contact',  label: 'Primary Contact', visible: false, locked: false },
  { key: 'last_touch',       label: 'Last Touch',      visible: false, locked: false },
  { key: 'committed_display',label: 'Committed',       visible: false, locked: false },
  { key: 'notes',            label: 'Notes',           visible: false, locked: false },
];
```

After:
```javascript
const DEFAULT_COLUMNS = [
  { key: 'org',              label: 'Organization',    visible: true,  locked: true  },
  { key: 'urgency',          label: 'Urgency',         visible: true,  locked: false },
  { key: 'stage',            label: 'Stage',           visible: true,  locked: false },
  { key: 'target_display',   label: 'Expected',        visible: true,  locked: false },
  { key: 'tasks',            label: 'Tasks',           visible: true,  locked: false },
  { key: 'notes',            label: 'Notes',           visible: true,  locked: false },
  { key: 'org_type',         label: 'Type',            visible: false, locked: false },
  { key: 'assigned_to',      label: 'Assigned To',     visible: false, locked: false },
  { key: 'closing',          label: 'Closing',         visible: false, locked: false },
  { key: 'primary_contact',  label: 'Primary Contact', visible: false, locked: false },
  { key: 'last_touch',       label: 'Last Touch',      visible: false, locked: false },
  { key: 'committed_display',label: 'Committed',       visible: false, locked: false },
];
```

### 3e. Update `buildCellContent` to handle `tasks` column (~line 764)

Replace the `case 'next_action':` block with a `tasks` handler. Find:

```javascript
    case 'next_action':
    case 'notes': {
      if (!val) return '—';
      const display = val.length > 60 ? val.slice(0, 60) + '…' : val;
      return `<span title="${escHtml(val)}">${escHtml(display)}</span>`;
    }
```

Replace with:

```javascript
    case 'tasks': {
      if (!val) return '<span style="color:#94a3b8">—</span>';
      // Tasks come as "[@Owner] description | [@Owner2] description2"
      const parts = val.split(' | ');
      return parts.map(t => {
        const ownerMatch = t.match(/^\[@(\w+)\]\s*/);
        const owner = ownerMatch ? ownerMatch[1] : '';
        const desc = ownerMatch ? t.slice(ownerMatch[0].length) : t;
        const shortDesc = desc.length > 50 ? desc.slice(0, 50) + '…' : desc;
        const ownerBadge = owner
          ? `<span style="background:#eff6ff;color:#2563eb;padding:1px 5px;border-radius:3px;font-size:10px;font-weight:600;margin-right:4px">@${escHtml(owner)}</span>`
          : '';
        return `<span title="${escHtml(t)}">${ownerBadge}${escHtml(shortDesc)}</span>`;
      }).join('<br>');
    }

    case 'notes': {
      if (!val) return '<span style="color:#94a3b8">—</span>';
      const display = val.length > 60 ? val.slice(0, 60) + '…' : val;
      return `<span title="${escHtml(val)}">${escHtml(display)}</span>`;
    }
```

### 3f. Clear localStorage on deploy

Since `DEFAULT_COLUMNS` changed (removed `next_action`, added `tasks`, made `notes` visible), users with saved column configs in localStorage won't see the changes. Add a version bump to force a reset.

Find the `loadColumnConfig` function (~line 419) and add a version check at the top:

```javascript
const COL_CONFIG_VERSION = 2;  // Bump when DEFAULT_COLUMNS changes

function loadColumnConfig() {
  const saved = localStorage.getItem('crm_column_config');
  const savedVersion = parseInt(localStorage.getItem('crm_column_config_version') || '0');
  if (!saved || savedVersion < COL_CONFIG_VERSION) {
    localStorage.setItem('crm_column_config_version', String(COL_CONFIG_VERSION));
    localStorage.removeItem('crm_column_config');
    return DEFAULT_COLUMNS.map(c => ({ ...c }));
  }
  // ... rest of existing logic
```

Also update `saveColumnConfig` to write the version:

```javascript
function saveColumnConfig() {
  const toSave = columnConfig.map(c => ({ key: c.key, visible: c.visible }));
  localStorage.setItem('crm_column_config', JSON.stringify(toSave));
  localStorage.setItem('crm_column_config_version', String(COL_CONFIG_VERSION));
}
```

---

## Verification

After all changes:

1. Start the Flask app and load the CRM pipeline page
2. Confirm "Tasks" and "Notes" columns are visible by default
3. Confirm Tasks column shows `@Owner` badge + task description for prospects with matching tasks in TASKS.md
4. Confirm prospects without tasks show "—"
5. Confirm "Next Action" no longer appears anywhere in the column list
6. Confirm Notes column shows truncated text with hover tooltip
7. Confirm the Column manager panel shows "Tasks" and "Notes" (not "Next Action")
