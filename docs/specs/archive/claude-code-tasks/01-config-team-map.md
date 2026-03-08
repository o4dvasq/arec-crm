# Task 1: Config Parser — Add `team_map` Support

**Status:** DONE
**File:** `app/sources/crm_reader.py`
**Function:** `load_crm_config()`
**Dependencies:** None (can run in parallel with tasks 2, 3, 6, 7)

## What Changed

The AREC Team section in `crm/config.md` now uses `Short | Full Name` format:

```
## AREC Team
- Tony | Tony Avila
- Oscar | Oscar Vasquez
- Truman | Truman Flynn
```

The `load_crm_config()` function was updated to parse this format and return both:

- `team` — list of full names (backward-compatible, unchanged behavior)
- `team_map` — list of `{short, full}` dicts for UI dropdowns

## Code Change

In `load_crm_config()`, replace the simple `team` return with:

```python
raw_team = sections.get('AREC Team', [])
team_list = []
team_map = []
for entry in raw_team:
    if '|' in entry:
        short, full = [s.strip() for s in entry.split('|', 1)]
    else:
        full = entry.strip()
        short = full.split()[0]
    team_list.append(full)
    team_map.append({'short': short, 'full': full})

return {
    ...existing keys...,
    'team': team_list,
    'team_map': team_map,
}
```

## Acceptance Criteria

```python
config = load_crm_config()
assert config['team'][0] == 'Tony Avila'
assert config['team_map'][0] == {'short': 'Tony', 'full': 'Tony Avila'}
assert len(config['team_map']) == 15
```
