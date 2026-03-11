# Task 13 — Add "0. Declined" as a Stage

## Enhancement
Rename the "Declined" stage to "0. Declined" so it has a numeric prefix consistent with all other stages. This ensures proper sorting and grouping behavior.

## Files to Modify
- `crm/config.md`
- `crm/prospects.md` (update any prospects with Stage: Declined → 0. Declined)
- `app/templates/crm_pipeline.html` (update collapsed-by-default logic)
- `app/delivery/dashboard.py` (if terminal stage check is string-based)
- `app/sources/crm_reader.py` (if terminal stage check is string-based)

## Current State
In `crm/config.md`:
```
## Pipeline Stages
Declined
1. Prospect
2. Cold
...
8. Closed
```

Terminal Stages section:
```
## Terminal Stages
- Declined
```

## Required Changes

### 1. crm/config.md — Rename stage
```
## Pipeline Stages
0. Declined
1. Prospect
2. Cold
3. Outreach
4. Engaged
5. Interested
6. Verbal
7. Legal / DD
8. Closed

## Terminal Stages
- 0. Declined
```

### 2. crm/prospects.md — Update all prospects with "Declined" stage
Find-and-replace: `**Stage:** Declined` → `**Stage:** 0. Declined`

### 3. crm_pipeline.html — Collapsed stages logic (~line 952)
The current code likely checks for "Declined" in the collapsed set. Update to match "0. Declined":

```javascript
let collapsedStages = new Set(['8. Closed', '0. Declined']);
```

Also check `buildCellContent()` for stage badge coloring — ensure `parseInt('0. Declined')` returns 0, which will fall into the lowest bracket (stage-1 class). This may already work since `parseInt('0. Declined')` → 0.

### 4. dashboard.py + crm_reader.py — Terminal stage checks
Search for any hardcoded `'Declined'` string comparisons and update to `'0. Declined'`, or better, use the config's terminal_stages list dynamically. Key places:
- `api_prospects()` — excludes terminal stage prospects from active count
- `load_tasks_by_org()` — may filter by stage
- Fund summary calculations

## Testing
1. Check `crm/config.md` has `0. Declined` as first stage
2. Pipeline should show "0. Declined" group collapsed by default
3. Badge color for Declined prospects should be lightest/grey
4. Fund summary active count should still exclude Declined prospects
5. Any prospect set to Declined should display correctly
