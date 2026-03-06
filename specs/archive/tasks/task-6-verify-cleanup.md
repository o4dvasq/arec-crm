# Task 6: Verification — grep for stale references

## What to do

Run a search across all markdown files in the workspace for any remaining references to "Next Action" as a field name. The goal is to confirm the migration is complete.

## Commands to run

```bash
grep -rn "Next Action" *.md crm/*.md memory/*.md 2>/dev/null
```

## Expected results

The ONLY files that should still contain "Next Action" are:
- `tasks/task-*.md` (these instruction files themselves)
- `plan-unify-tasks-crm.md` (the plan document)

If any other file (especially `prospects.md`, `CLAUDE.md`, `update.md`, or `crm-inbox.md`) still contains "Next Action" as a field reference, it was missed in Tasks 2-5 and needs to be fixed.

## Also verify

1. **TASKS.md**: Every open task in Active has `**@Owner**` tag
2. **TASKS.md**: Waiting On tasks have `**@Owner**` tag (not the old "Name —" prefix)
3. **prospects.md**: Zero lines contain `Next Action`
4. **CLAUDE.md**: Contains the new `## TASKS.md Format` section
5. **update.md**: No references to "Next Action" as a prospects.md field
6. **crm-inbox.md**: No references to "Next Action" as a prospects.md field

## If issues found

Fix them inline during this task. These are straightforward find-and-replace corrections.
