# Plan: Unify TASKS.md and CRM Next Actions

## Decisions Made

- **Waiting On:** Keep the section. Tasks there get `**@Owner**` tags (the person Oscar is waiting on).
- **Next Action field:** Remove entirely from `prospects.md`. TASKS.md is sole source of truth.

---

## New TASKS.md Format

```markdown
- [ ] **[Hi]** **@Oscar** Follow up with Jared Brimberry — request second meeting (UTIMCO)
- [ ] **[Med]** **@Truman** Send data room link to Leon (Stoneweg)
```

Rules:
- `**@Name**` = task owner (first name, matches CLAUDE.md People table)
- If owner is omitted, default = Oscar
- `(OrgName)` suffix on CRM-related tasks = links task to a prospect in prospects.md
- CRM Pulse checks for open tasks in TASKS.md tagged with `(OrgName)` instead of reading a Next Action field

---

## Claude Code Tasks (6 sequential steps)

### Task 1: Update TASKS.md format + add owner tags

**File:** `TASKS.md`

**Instructions:**
- Add `**@Oscar**` to all Active tasks (he owns them all currently)
- In "Waiting On" section, change format from `Truman — investigate...` to `**@Truman** Investigate...`
- Do NOT change Personal or Done sections
- Preserve all existing content, priorities, and checkbox states exactly

**Before:**
```
## Active
- [ ] **[Hi]** Follow up with Jared Brimberry (UTIMCO) — request second meeting...
```

**After:**
```
## Active
- [ ] **[Hi]** **@Oscar** Follow up with Jared Brimberry (UTIMCO) — request second meeting...
```

**Before (Waiting On):**
```
- [ ] **[Med]** Truman — investigate Preqin + Juniper Square integration (delegated 3/1)
```

**After:**
```
- [ ] **[Med]** **@Truman** Investigate Preqin + Juniper Square integration (delegated 3/1)
```

---

### Task 2: Remove `Next Action` from all prospect records

**File:** `crm/prospects.md`

**Instructions:**
- Delete every line matching `- **Next Action:**` (with or without trailing content) from the file
- There are ~50+ prospect entries, each with this line. Remove from ALL of them.
- Do NOT touch any other fields (Stage, Target, Committed, Primary Contact, Closing, Urgency, Assigned To, Notes, Last Touch)

---

### Task 3: Update CLAUDE.md — format docs + automation logic

**File:** `CLAUDE.md`

**Instructions — 3 changes:**

**3a.** Add a `## TASKS.md Format` section after the existing `## Preferences` section:

```markdown
## TASKS.md Format
- Standard: `- [ ] **[Priority]** **@Owner** Description`
- Priority: Hi / Med / Low
- Owner: `**@Name**` using first name from People table (default Oscar if omitted)
- CRM tasks: append `(OrgName)` matching the prospect heading in prospects.md
- Sections: Active, Personal, Waiting On, Done
- "Waiting On" = tasks Oscar delegated; owner is the person he's waiting on
- CRM Pulse derives "next action" status by grepping TASKS.md for open tasks with `(OrgName)`
```

**3b.** Update the meeting action items instruction (currently at ~line 275):

Change:
```
Collect all action items from new summaries (both Notion-sourced from Step 3 and manually-captured from Step 4). Cross-reference against TASKS.md (fuzzy match). Present new Oscar-owned items grouped by meeting. Wait for user confirmation before adding to TASKS.md.
```

To:
```
Collect all action items from new summaries (both Notion-sourced from Step 3 and manually-captured from Step 4). Cross-reference against TASKS.md (fuzzy match). Present new items grouped by meeting, including the proposed **@Owner** and **(OrgName)** if CRM-related. Wait for user confirmation before adding to TASKS.md.
```

**3c.** Update the CRM Pulse observation #3 (currently at ~line 301):

Change:
```
3. High urgency prospects with no Next Action set
```

To:
```
3. High urgency prospects with no open task in TASKS.md (grep for (OrgName) in Active section)
```

---

### Task 4: Update update.md — CRM Pulse + task format

**File:** `update.md`

**Instructions — 3 changes:**

**4a.** Around line 237, change:
```
2. **High urgency with no Next Action set**
   > ⚡ **[Org]** is at [stage] with no Next Action set and last touch [N] days ago.
   > Want to add a follow-up task or do a quick intel capture?
```

To:
```
2. **High urgency with no open task in TASKS.md**
   > ⚡ **[Org]** is at [stage] with no open task in TASKS.md and last touch [N] days ago.
   > Want to add a follow-up task or do a quick intel capture?
```

**4b.** Around line 145, where it describes the TASKS.md format for adding tasks, update to:
```
Wait for user confirmation before adding anything to TASKS.md. When adding, follow the format: `- [ ] **[Priority]** **@Owner** Description (OrgName if CRM-related)` — assign priority (Hi/Med/Low) and owner based on context.
```

**4c.** Anywhere the file references "Next Action" as a prospects.md field, change to reference TASKS.md instead. Specifically search for all "Next Action" references and update or remove them.

---

### Task 5: Update crm-inbox.md — task creation format

**File:** `crm-inbox.md`

**Instructions — 2 changes:**

**5a.** Around line 57, change:
```
Update only the specific field(s) mentioned (Next Action, Notes, Stage, Urgency).
```

To:
```
Update only the specific field(s) mentioned (Notes, Stage, Urgency). Tasks go to TASKS.md, not prospects.md.
```

**5b.** Around line 61-62, update the task creation format:

Change:
```
Append to `TASKS.md` under `## Work — IR/Fundraising`:
`- [ ] **[Hi]** [Specific action] — [Org name]`
```

To:
```
Append to `TASKS.md` under `## Active`:
`- [ ] **[Hi]** **@Owner** [Specific action] (OrgName)`
```

---

### Task 6: Verify — grep for stale references

**Instructions:**
- Run: `grep -rn "Next Action" *.md crm/*.md` across the workspace
- The ONLY matches should be in this plan file itself
- If any other file still references "Next Action" as a field to read/write, flag it

---

## Summary of What Changes

| File | Change |
|------|--------|
| TASKS.md | Add `**@Owner**` tags to all tasks |
| crm/prospects.md | Remove `Next Action` field from all ~50+ records |
| CLAUDE.md | Add format docs, update meeting + CRM Pulse logic |
| update.md | Update CRM Pulse + task format references |
| crm-inbox.md | Remove Next Action writes, update task format |
