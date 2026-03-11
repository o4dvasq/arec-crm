# Task 3: Update CLAUDE.md — format docs + automation logic

## File
`CLAUDE.md` (root of workspace)

## Three changes required

---

### 3a. Add TASKS.md Format section

Insert a new section **after** the existing `## Preferences` section (which ends around line 127) and **before** the `---` separator that leads into `## Notion Meeting Sync`:

```markdown
## TASKS.md Format
- Standard format: `- [ ] **[Priority]** **@Owner** Description`
- Priority: Hi / Med / Low
- Owner: `**@Name**` using first name from People table (default = Oscar if omitted)
- CRM tasks: append `(OrgName)` at the end, matching the prospect heading in prospects.md
- Sections: Active, Personal, Waiting On, Done
- "Waiting On" = tasks Oscar delegated; owner is the person he's waiting on
- CRM Pulse derives "next action" status by grepping TASKS.md for open tasks with `(OrgName)`
- Next Action field was removed from prospects.md — TASKS.md is the sole source of truth for all tasks and next actions
```

---

### 3b. Update meeting action items instruction

Find this text (around line 275):

```
Collect all action items from new summaries (both Notion-sourced from Step 3 and manually-captured from Step 4). Cross-reference against TASKS.md (fuzzy match). Present new Oscar-owned items grouped by meeting. Wait for user confirmation before adding to TASKS.md.
```

Replace with:

```
Collect all action items from new summaries (both Notion-sourced from Step 3 and manually-captured from Step 4). Cross-reference against TASKS.md (fuzzy match). Present new items grouped by meeting, including the proposed **@Owner** and **(OrgName)** if CRM-related. Wait for user confirmation before adding to TASKS.md using the standard format: `- [ ] **[Priority]** **@Owner** Description (OrgName)`.
```

---

### 3c. Update CRM Pulse observation #3

Find this text (around line 301):

```
3. High urgency prospects with no Next Action set
```

Replace with:

```
3. High urgency prospects with no open task in TASKS.md (grep for (OrgName) in Active/Waiting On sections)
```
