# Task 5: Pass `team_map` to Frontend Templates

**Status:** DONE
**Files:** `app/templates/dashboard.html`, `app/templates/tasks/tasks.html`
**Dependencies:** Task 1 (config parser must return `team_map`)

## What Changed

Add one line to each template's `<script>` block to expose `team_map` to the JS.

### `dashboard.html` (around line 335-336)

```javascript
// BEFORE
window.TASK_MODAL_TEAM = {{ config.team | tojson }};

// AFTER
window.TASK_MODAL_TEAM = {{ config.team | tojson }};
window.TASK_MODAL_TEAM_MAP = {{ config.team_map | tojson }};
```

### `tasks/tasks.html` (around line 33-34)

```javascript
// BEFORE
window.TASK_MODAL_TEAM = CONFIG.team || [];

// AFTER
window.TASK_MODAL_TEAM = CONFIG.team || [];
window.TASK_MODAL_TEAM_MAP = CONFIG.team_map || [];
```

## Acceptance Criteria

In the browser console on both `/` and `/tasks`:

```javascript
console.log(TASK_MODAL_TEAM_MAP[0])
// → {short: "Tony", full: "Tony Avila"}
```
