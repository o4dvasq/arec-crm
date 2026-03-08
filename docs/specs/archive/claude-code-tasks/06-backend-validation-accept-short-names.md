# Task 6: Backend Validation — Accept Short Names

**Status:** DONE
**File:** `app/delivery/dashboard.py`
**Function:** `api_patch_prospect_field()`
**Dependencies:** Task 1 (config parser must return `team_map`)

## Problem

The `assigned_to` field validator only accepted full names from `config['team']`. Short names like "Tony" were rejected with "Invalid team member".

## What Changed

```python
# BEFORE
if field == 'assigned_to' and value not in config['team'] and value != '':
    return jsonify({'error': f'Invalid team member: {value}'}), 400

# AFTER
if field == 'assigned_to' and value != '':
    valid_names = set(config['team'])
    valid_names.update(m['short'] for m in config.get('team_map', []))
    if value not in valid_names:
        return jsonify({'error': f'Invalid team member: {value}'}), 400
```

## Acceptance Criteria

```bash
curl -X PATCH /crm/api/prospect/field \
  -d '{"org":"UTIMCO","offering":"Fund II","field":"assigned_to","value":"Tony"}'
# Should return 200, not 400
```
