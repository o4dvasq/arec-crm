# Task 3: Always Write @Tag in `_format_task_line`

**Status:** DONE
**File:** `app/delivery/dashboard.py`
**Function:** `_format_task_line()`
**Dependencies:** None (can run in parallel with tasks 1, 2, 6, 7)

## Problem

The formatter only wrote `**@Name**` tags for tasks in the "Waiting On" section. Tasks in "Fundraising - Me" lost their @tag on save, breaking team task grouping.

## What Changed

```python
# BEFORE
def _format_task_line(text, priority, context, assigned_to, section, done=False, completion_date=None):
    checkbox = '- [x] ' if done else '- [ ] '
    line = f'**[{priority}]** '
    # For Waiting On, embed owner as **@Name** prefix
    if section == 'Waiting On' and assigned_to:
        line += f'**@{assigned_to}** '
    ...

# AFTER
def _format_task_line(text, priority, context, assigned_to, section, done=False, completion_date=None):
    checkbox = '- [x] ' if done else '- [ ] '
    line = f'**[{priority}]** '
    # Always embed owner as **@Name** prefix when assigned
    if assigned_to:
        line += f'**@{assigned_to}** '
    ...
```

## Acceptance Criteria

```python
result = _format_task_line("Connect with CHERN", "Hi", "", "Tony", "Fundraising - Me")
assert result == "- [ ] **[Hi]** **@Tony** Connect with CHERN\n"

result = _format_task_line("Investigate Preqin", "Med", "", "Truman", "Waiting On")
assert result == "- [ ] **[Med]** **@Truman** Investigate Preqin\n"
```
