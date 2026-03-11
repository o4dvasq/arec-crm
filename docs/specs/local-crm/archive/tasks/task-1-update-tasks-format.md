# Task 1: Add @Owner tags to TASKS.md

## File
`TASKS.md` (root of workspace)

## What to do

Add `**@Owner**` tags to every open task in the Active and Waiting On sections. Do NOT modify Personal or Done sections.

## Rules

- Default owner for Active tasks = `**@Oscar**`
- Waiting On tasks: the person named at the start of the task becomes the owner
- Preserve all existing content, priorities, checkbox states, and descriptions exactly
- Place the owner tag immediately after the priority tag: `**[Pri]** **@Owner** Description`
- Completed tasks (checked `[x]`) in Active: still add the tag for consistency

## Specific changes

### Active section — add `**@Oscar**` to all items:

```
- [ ] **[Hi]** **@Oscar** Follow up with Jared Brimberry (UTIMCO) — request second meeting...
- [ ] **[Med]** **@Oscar** Track Matt Saverin move from UTIMCO → TRS...
- [ ] **[Med]** **@Oscar** Simon (Priya) → Matt Saverin intro...
- [x] **[Hi]** **@Oscar** Send Ami (Blackstone TPM) the $300M Mountain House refi...
- [ ] **[Med]** **@Oscar** Wrap up lending intelligence platform and hand over to Adrian and Jake
- [ ] **[Med]** **@Oscar** Update Terrell once NEPC underwriting is complete...
- [ ] **[Hi]** **@Oscar** Create agenda + presentation for Future Fund meeting Mar 17...
- [ ] **[Med]** **@Oscar** Ask Tony about Jim Steinbugl / Penn State relationship...
- [ ] **[Med]** **@Oscar** Follow up with Tim Phillips (Phillips & Co, Portland)...
- [x] **[Low]** **@Oscar** Schedule follow-up SharePoint technical discussion...
```

### Waiting On section — convert name prefix to @Owner tag:

Before:
```
- [ ] **[Med]** Truman — investigate Preqin + Juniper Square integration (delegated 3/1)
```

After:
```
- [ ] **[Med]** **@Truman** Investigate Preqin + Juniper Square integration (delegated 3/1)
```

Note: "Truman —" is removed and replaced with `**@Truman**`. Capitalize the first letter of the description.

### Personal and Done sections — NO CHANGES
