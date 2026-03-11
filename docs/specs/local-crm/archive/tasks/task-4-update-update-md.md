# Task 4: Update update.md — CRM Pulse + task format

## File
`update.md` (root of workspace)

## Three changes required

---

### 4a. Update CRM Pulse observation #2

Find this text (around line 237):

```
2. **High urgency with no Next Action set**
   > ⚡ **[Org]** is at [stage] with no Next Action set and last touch [N] days ago.
   > Want to add a follow-up task or do a quick intel capture?
```

Replace with:

```
2. **High urgency with no open task in TASKS.md**
   > ⚡ **[Org]** is at [stage] with no open task in TASKS.md and last touch [N] days ago.
   > Want to add a follow-up task or do a quick intel capture?
```

---

### 4b. Update task addition format

Find this text (around line 145):

```
Wait for user confirmation before adding anything to TASKS.md. When adding, follow the existing TASKS.md format (`- [ ] **[Priority]** Description`) and assign priority (Hi/Med/Low) based on context — urgency, who it involves, deadlines mentioned.
```

Replace with:

```
Wait for user confirmation before adding anything to TASKS.md. When adding, use the format: `- [ ] **[Priority]** **@Owner** Description (OrgName if CRM-related)`. Assign priority (Hi/Med/Low) and owner based on context — who the action item belongs to, urgency, deadlines mentioned. Default owner is Oscar if unclear.
```

---

### 4c. Search and replace all remaining "Next Action" references

Search the entire file for any other mention of "Next Action" as a prospect field. For each occurrence:
- If it refers to reading/writing the Next Action field in prospects.md → change to reference TASKS.md instead
- If it refers to "no Next Action set" → change to "no open task in TASKS.md"

Known locations to check:
- The CRM Pulse section (~lines 220-260)
- The comprehensive mode section (~lines 260-300)
- Any task format examples throughout the file
