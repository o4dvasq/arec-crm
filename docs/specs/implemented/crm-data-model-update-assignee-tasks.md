# CRM Data Model Update — Single Assignee + Prospect Tasks

**Project:** AREC Investor CRM  
**Author:** Oscar Vasquez  
**Status:** Ready for Claude Code  
**Depends on:** CRM Architecture FINAL (all phases)

---

## Summary of Changes

1. **Prospect `Assigned To` → single owner only.** Remove multi-assign support. Run a one-time migration scan that identifies prospects with multiple assignees and prompts for resolution.
2. **Prospect `Next Action` field removed.** Replaced by tasks in TASKS.md.
3. **Prospect tasks live in TASKS.md** alongside regular tasks, tagged with a `[org: Org Name]` context marker so `crm_reader.py` can find them.
4. **Pipeline UI updated** — edit form and table column reflect the new model.

---

## 1. Data Model Changes

### 1.1 prospects.md — field changes

**Remove:** `Next Action` field entirely from all prospect records.  
**Change:** `Assigned To` field — single string value only (one name, no semicolons).

Before:
```markdown
- **Assigned To:** Tony Avila; James Walton
- **Next Action:** Meeting March 2
```

After:
```markdown
- **Assigned To:** Tony Avila
```

### 1.2 TASKS.md — prospect task format

Prospect tasks are written into the appropriate section of TASKS.md using the existing task format with an `[org: ...]` tag appended to the context field:

```
- [ ] **[Med]** Call Susannah re: Fund II terms — [org: Merseyside Pension Fund]
- [ ] **[Hi]** Send PPM draft — [org: Merseyside Pension Fund] [owner: James Walton]
- [x] **[Med]** Intro call completed — [org: Belgravia Management] [owner: Oscar Vasquez]
```

**Tag rules:**
- `[org: Org Name]` — required. Links task to a prospect. Must exactly match `## OrgName` heading in organizations.md.
- `[owner: Name]` — required for prospect tasks. Single name from AREC Team list. Distinct from the prospect's `Assigned To` (prospect ownership vs. task ownership).
- Status: `- [ ]` = open, `- [x]` = done. Standard TASKS.md format.
- Priority: `[Hi]`, `[Med]`, `[Lo]` — standard.
- Prospect tasks can live in any TASKS.md section (typically `## IR / Fundraising`).

---

## 2. Migration Script

### `scripts/migrate_assignee_tasks.py`

One-time script. Run once against the live markdown files.

**Step 1 — Scan for multi-assignee prospects:**

```
1. Load all prospects from prospects.md
2. For each prospect where Assigned To contains ";" or multiple names:
   a. Print prospect org name, offering, and current assignees
   b. Prompt: "Who should own [Org Name] ([Offering])? Options: [list current assignees]"
   c. Read input from stdin
   d. Write single resolved name back to prospect record
3. Report: N prospects updated, M already single-assignee
```

**Step 2 — Remove Next Action fields:**

```
4. For each prospect where Next Action is non-empty:
   a. Print: "Next Action for [Org] ([Offering]): '[current value]'"
   b. Prompt: "Convert to TASKS.md task? [y/n] Owner? Section? Priority?"
   c. If y: append task to TASKS.md in specified section with [org: ...] [owner: ...] tags
   d. Remove Next Action field from prospect record regardless
5. Report: N Next Actions converted to tasks, M dropped
```

**Step 3 — Write updated prospects.md:**

```
6. Write all updated prospect records back to prospects.md
7. Print final summary
```

**Run command:**
```bash
cd ~/arec-morning-briefing
python scripts/migrate_assignee_tasks.py
```

---

## 3. crm_reader.py Changes

### 3.1 Modify `write_prospect()` and `update_prospect_field()`

- Enforce single string for `Assigned To` — strip semicolons, take first name if comma/semicolon present, log a warning.
- Remove `Next Action` from the field list. If encountered on read, ignore silently (backward compat during migration). Never write it.

### 3.2 New task functions (reads TASKS.md)

Add to `crm_reader.py`:

```python
TASKS_MD_PATH = os.path.expanduser("~/Dropbox/Tech/ClaudeProductivity/TASKS.md")

def get_tasks_for_prospect(org_name: str) -> list[dict]:
    """
    Scan TASKS.md for tasks tagged [org: org_name].
    Returns list of dicts: {text, owner, priority, status, section, raw_line}
    Matching is case-insensitive exact match on org name.
    """

def get_all_prospect_tasks() -> list[dict]:
    """
    Scan TASKS.md for all tasks tagged with any [org: ...] tag.
    Returns list of dicts: {org, text, owner, priority, status, section}
    Used for pipeline-level task views.
    """

def add_prospect_task(org_name: str, text: str, owner: str,
                      priority: str = "Med", section: str = "IR / Fundraising") -> bool:
    """
    Append a new prospect task to TASKS.md under the specified section.
    Format: - [ ] **[{priority}]** {text} — [org: {org_name}] [owner: {owner}]
    Creates section if it doesn't exist.
    Returns True on success.
    """

def complete_prospect_task(org_name: str, task_text: str) -> bool:
    """
    Find matching task by org_name + partial text match, change - [ ] to - [x].
    Returns True if found and updated.
    """
```

**Parsing rules for task tags:**
- `[org: Org Name]` — extract org name (strip brackets, strip "org: " prefix)
- `[owner: Name]` — extract owner name
- Tags may appear anywhere in the task line after the main text
- A task line may have both tags, or just `[org:]` (owner defaults to empty string)

---

## 4. API Changes

### 4.1 New routes (add to CRM Blueprint)

```
GET  /crm/api/tasks?org=<name>         → list tasks for a prospect (from TASKS.md)
POST /crm/api/tasks                     → add a prospect task to TASKS.md
PATCH /crm/api/tasks/complete           → mark a task complete
```

**POST /crm/api/tasks body:**
```json
{
  "org": "Merseyside Pension Fund",
  "text": "Send updated PPM",
  "owner": "James Walton",
  "priority": "Hi",
  "section": "IR / Fundraising"
}
```

**PATCH /crm/api/tasks/complete body:**
```json
{
  "org": "Merseyside Pension Fund",
  "task_text": "Send updated PPM"
}
```

### 4.2 Modified routes

**GET /crm/api/prospects?offering=X** — each prospect object now includes:
```json
{
  "assigned_to": "James Walton",
  "open_task_count": 2,
  "tasks": [
    {"text": "Call Susannah re: terms", "owner": "James Walton", "priority": "Hi", "status": "open"},
    {"text": "Send PPM draft", "owner": "Oscar Vasquez", "priority": "Med", "status": "open"}
  ]
}
```
`tasks` array is populated from `get_tasks_for_prospect()`. Include both open and done tasks; let the UI filter.

**PUT/PATCH /crm/api/prospect/.../field** — reject writes to `next_action` field (return 400). Enforce single value for `assigned_to`.

---

## 5. UI Changes

### 5.1 Pipeline Table (`/crm`)

**Column changes:**
- **Remove:** `Next Action` column
- **Keep:** `Assigned To` column — now displays single name (no change in appearance, just enforcement)
- **Add:** `Tasks` column — shows open task count as a badge: `2 open` (blue badge) or `✓` if all done

**Tasks badge behavior:**
- Click badge → opens prospect edit sheet / detail with tasks panel expanded
- Zero open tasks + no tasks at all → show `+` to add first task

### 5.2 Edit Sheet / Prospect Detail

**Remove:** Next Action field entirely.

**Assigned To field:**
- Single `<select>` from AREC Team list (not multi-select)
- Label: "Owner"

**Add: Tasks panel** (below Notes, above Last Touch):

```
Tasks
┌──────────────────────────────────────────┐
│ ☐  Call Susannah re: terms    James W.   │
│ ☐  Send PPM draft             Oscar V.   │
│ ☑  Intro call completed       Zach R.    │  ← done, shown dimmed
└──────────────────────────────────────────┘
[ + Add Task ]
```

**Add Task inline form:**
```
[ Task description...          ] [ Owner ▼ ] [ Hi/Med/Lo ] [ Add ]
```

- Owner dropdown = AREC Team from config.md
- Priority = Hi/Med/Lo toggle, default Med
- Submits to POST /crm/api/tasks
- Clicking ☐ checkbox calls PATCH /crm/api/tasks/complete
- Done tasks shown dimmed with strikethrough, collapsed behind "Show N completed" toggle

### 5.3 Mobile PWA (arec-mobile.html)

**Edit sheet changes:**
- Remove Next Action textarea
- Rename "Assigned To" label to "Owner", change to single `<select>`
- Add Tasks section below Notes:
  - List of open tasks with checkbox + owner initial
  - "Add task" row: text input + owner picker + priority + submit
  - Tapping checkbox calls complete API

---

## 6. Validation & Enforcement

| Rule | Where enforced |
|------|---------------|
| `Assigned To` = single name | `write_prospect()`, PATCH API, UI `<select>` |
| `Next Action` field not written | `write_prospect()` omits it; API returns 400 if sent |
| `[org:]` tag required on prospect tasks | `add_prospect_task()` validates before write |
| `[owner:]` tag required on prospect tasks | `add_prospect_task()` validates before write |

---

## 7. Acceptance Criteria

1. ✅ Migration script scans all prospects, prompts for single assignee where multiple exist, and writes resolved values
2. ✅ Migration script offers to convert existing Next Action values to TASKS.md tasks, then removes the field
3. ✅ `write_prospect()` never writes `Next Action`; enforces single string for `Assigned To`
4. ✅ `get_tasks_for_prospect(org)` returns tasks from TASKS.md tagged `[org: org]`
5. ✅ `add_prospect_task()` writes correctly formatted task to TASKS.md
6. ✅ Pipeline table shows Tasks badge (count of open tasks per prospect)
7. ✅ Edit sheet shows tasks panel with add/complete functionality
8. ✅ Mobile PWA edit sheet reflects same changes (no Next Action, single owner, tasks panel)
9. ✅ GET /crm/api/prospects response includes `assigned_to` (string) and `tasks` (array)
10. ✅ No regressions to existing CRM phases
