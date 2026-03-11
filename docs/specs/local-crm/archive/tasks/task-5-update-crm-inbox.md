# Task 5: Update crm-inbox.md — task creation format

## File
`crm-inbox.md` (root of workspace)

## Two changes required

---

### 5a. Remove Next Action from updatable fields

Find this text (around line 57):

```
Update only the specific field(s) mentioned (Next Action, Notes, Stage, Urgency).
```

Replace with:

```
Update only the specific field(s) mentioned (Notes, Stage, Urgency). Tasks and next actions go to TASKS.md, not prospects.md.
```

---

### 5b. Update task creation format

Find this text (around lines 61-62):

```
Append to `TASKS.md` under `## Work — IR/Fundraising`:
`- [ ] **[Hi]** [Specific action] — [Org name]`
```

Replace with:

```
Append to `TASKS.md` under `## Active`:
`- [ ] **[Hi]** **@Owner** [Specific action] (OrgName)`
```

Note: The section name changed from `## Work — IR/Fundraising` to `## Active` (matching current TASKS.md structure). The format now includes the `**@Owner**` tag and uses `(OrgName)` in parentheses at the end.
