# Task 2: Fix @Tag Regex to Support Multi-Word Names

**Status:** DONE
**Files:** `app/delivery/dashboard.py`, `app/sources/crm_reader.py`
**Dependencies:** None (can run in parallel with tasks 1, 3, 6, 7)

## Problem

The regex `\*\*@(\w+)\*\*` only matches single-word names. Team members like "Mike R", "Kevin V", and "Max Angeloni" fail to parse because `\w+` stops at the space.

## What Changed

Changed regex from `\*\*@(\w+)\*\*` to `\*\*@([^*]+)\*\*` with `.strip()` on the match group.

Three locations:

### Location 1: `dashboard.py` → `_load_tasks_grouped()` (line ~88)

```python
# BEFORE
owner_m = re.match(r'\*\*@(\w+)\*\*\s*', text)
if owner_m:
    assigned_to = owner_m.group(1)

# AFTER
owner_m = re.match(r'\*\*@([^*]+)\*\*\s*', text)
if owner_m:
    assigned_to = owner_m.group(1).strip()
```

### Location 2: `dashboard.py` → `_parse_task_line()` (line ~617)

```python
# BEFORE
om = re.match(r'\*\*@(\w+)\*\*\s*', text)

# AFTER
om = re.match(r'\*\*@([^*]+)\*\*\s*', text)
```

### Location 3: `crm_reader.py` → `load_tasks_by_org()` (line ~1053)

```python
# BEFORE
owner_match = re.search(r'\*\*@(\w+)\*\*', stripped)
owner = owner_match.group(1) if owner_match else 'Oscar'

# AFTER
owner_match = re.search(r'\*\*@([^*]+)\*\*', stripped)
owner = owner_match.group(1).strip() if owner_match else 'Oscar'
```

## Acceptance Criteria

Parsing these lines should extract the correct `assigned_to`:

```
- [ ] **[Med]** **@Mike R** Send Clifford Chance email     → assigned_to = "Mike R"
- [ ] **[Med]** **@Kevin V** Follow up on Cayman feeder    → assigned_to = "Kevin V"
- [ ] **[Med]** **@Max Angeloni** Share email contacts      → assigned_to = "Max Angeloni"
- [ ] **[Hi]** **@Tony** Connect with CHERN                → assigned_to = "Tony"
```
