# Task 8: Filter Fundraising Column to Prevent Duplicates

**Status:** DONE
**Files:** `app/static/tasks/tasks.js`, `app/templates/dashboard.html`
**Dependencies:** None

## Problem

Tasks assigned to other team members (e.g., `**@Tony**`) in the `## Fundraising - Me` section appeared in both:

1. The "Fundraising - Me" column (because they live in that markdown section)
2. The "Team Tasks" column (because `assigned_to !== 'Oscar'`)

This caused every team task to show up twice on the board.

## What Changed

### `tasks.js` → `renderColumn()` (around line 118)

```javascript
// BEFORE
function renderColumn(section, tasks) {
  const openTasks = tasks.filter(t => !t.complete);

// AFTER
function renderColumn(section, tasks) {
  // For Fundraising - Me, exclude tasks assigned to other team members (those show in Team Tasks)
  if (section === 'Fundraising - Me') {
    tasks = tasks.filter(t => !t.assigned_to || t.assigned_to === 'Oscar');
  }
  const openTasks = tasks.filter(t => !t.complete);
```

### `dashboard.html` → Jinja loop (around line 259)

```html
<!-- BEFORE -->
{% if not task.done %}

<!-- AFTER -->
{% if not task.done and (not task.assigned_to or task.assigned_to == 'Oscar') %}
```

## Acceptance Criteria

- Task `**@Tony** Connect with CHERN Family Office via Canarelli` appears ONLY in Team Tasks under @Tony
- Task `**@Oscar** Create agenda for Future Fund` appears ONLY in Fundraising - Me
- Untagged tasks (no @tag) appear in Fundraising - Me
- Done tasks with @tags for other people are excluded from Fundraising - Me Done section
