# Overwatch — Complete System Specification

**Date:** 2026-03-04
**Version:** 1.0
**Author:** Oscar Vasquez / Claude

---

## 1. Overview

Overwatch is an internal productivity dashboard for Avila Real Estate Capital (AREC). It provides a unified web interface for managing the Fund II fundraising pipeline, task management, calendar integration, and meeting summaries. Built as a Flask application backed by markdown files as the data store.

**Stack:** Python 3 / Flask / Jinja2 templates / vanilla JavaScript. No frontend framework. All data persisted in markdown files under the `crm/`, `memory/`, and project root (`TASKS.md`).

---

## 2. Architecture

### 2.1 Directory Structure

```
ClaudeProductivity/
├── app/
│   ├── main.py                      # Flask app factory, route registration
│   ├── delivery/
│   │   └── dashboard.py             # All routes: app, crm_bp, tasks_bp
│   ├── sources/
│   │   ├── crm_reader.py            # Markdown parser/writer for CRM + tasks
│   │   ├── crm_graph_sync.py        # Juniper Square sync via MS Graph
│   │   ├── memory_reader.py         # Knowledge base reader (people, glossary)
│   │   └── ms_graph.py              # Microsoft Graph API client
│   ├── auth/
│   │   └── graph_auth.py            # MSAL auth for MS Graph
│   ├── briefing/
│   │   ├── generator.py             # Morning briefing generator
│   │   └── prompt_builder.py        # Briefing prompt assembly
│   ├── static/
│   │   ├── task-edit-modal.css       # Shared task edit modal styles
│   │   ├── task-edit-modal.js        # Shared task edit modal component
│   │   └── tasks/
│   │       ├── tasks.css             # Tasks kanban page styles
│   │       └── tasks.js              # Tasks kanban page logic
│   ├── templates/
│   │   ├── dashboard.html            # Dashboard (3-column: tasks, calendar, meetings)
│   │   ├── crm_pipeline.html         # Pipeline table with stage grouping
│   │   ├── crm_org_detail.html       # Organization detail page
│   │   ├── crm_prospect_edit.html    # Prospect field editor
│   │   └── tasks/
│   │       └── tasks.html            # Kanban board for task management
│   └── scripts/
│       ├── bootstrap_contacts_index.py
│       └── migrate_tasks_sections.py
├── crm/
│   ├── config.md                     # Pipeline stages, team, urgency, closings
│   ├── offerings.md                  # Fund offerings (Debt Fund II, Mountain House, JVs)
│   ├── prospects.md                  # All prospect records (markdown key-value)
│   ├── interactions.md               # Interaction log per org
│   ├── contacts_index.json           # Contact → org lookup
│   ├── pending_interviews.json       # Post-meeting interview queue
│   └── ai_inbox_queue.md             # Email triage queue
├── memory/
│   ├── glossary.md                   # Terms, people, companies reference
│   └── people/                       # Per-person intel files (*.md)
├── meeting-summaries/                # Processed Notion meeting notes (*.md)
├── TASKS.md                          # Single source of truth for all tasks
├── CLAUDE.md                         # AI context / memory / instructions
└── specs/                            # Specification documents
```

### 2.2 Flask Blueprints

| Blueprint | Prefix | Purpose |
|-----------|--------|---------|
| `app` | `/` | Dashboard, legacy task APIs |
| `crm_bp` | `/crm` | Pipeline, org detail, prospect CRUD, contacts |
| `tasks_bp` | `/tasks` | Kanban board, task CRUD |

---

## 3. Pages

### 3.1 Dashboard (`/`)

Three-column layout: Fundraising Tasks, Today's Calendar, Recent Meetings.

**Fundraising Tasks panel:**
- Shows open tasks from the "Fundraising - Me" section of TASKS.md
- Grouped by priority (Hi → Med → Low) with colored dots
- Inline add form (text + priority selector)
- Each task has a checkbox (complete), edit pencil icon, and org link badge
- Edit opens the shared task edit modal (section, priority, assignee, text)
- Completing a task marks it done via `POST /api/task/complete`

**Today's Calendar panel:**
- Rendered server-side from `calendar` context variable
- Shows time, title, attendees, location for each event

**Recent Meetings panel:**
- Lists meeting summaries from `meeting-summaries/` directory
- Grouped by date, clickable to open source URL
- Shows title and attendees

**Navigation bar:** Dashboard (active) | Tasks | Pipeline — centered "Overwatch" brand logo — right-aligned date

### 3.2 Tasks Kanban (`/tasks`)

Four-column kanban board: "Fundraising - Me" | "Team Tasks" | "Work" | "Personal"

**Standard columns** (Fundraising, Work, Personal):
- "+ Add task" button opens inline form (text, priority, owner for Waiting On)
- Open tasks sorted by priority, each rendered as a card
- Cards show: priority dot, task text, org link (if CRM-linked), context line
- Card actions: Complete, Edit (opens shared modal), Delete
- Priority dot click: completes task (with confirm for Hi priority)
- Done tasks collapsed in footer toggle ("Done (N)")

**Team Tasks column:**
- Aggregates all non-Oscar tasks from non-Done sections
- Grouped by person with `@Name` badge headers
- Each person's tasks sorted by priority
- Cards are read-only views (same card format but from other sections)

**Shared task edit modal** (`task-edit-modal.js`):
- Text textarea, Priority dropdown (Hi/Med/Low), Assigned To dropdown (team list), Section dropdown
- Org badge display (non-editable, shown when task is CRM-linked)
- Save calls `PUT /tasks/api/task/<section>/<index>`
- Delete calls `DELETE /tasks/api/task/<section>/<index>` with confirm

### 3.3 Pipeline (`/crm`)

Tabbed pipeline table with stage-grouped rows, fund summary bar, and column manager.

**Tabs:** One per offering (AREC Debt Fund II, Mountain House Refi, JVs and Finance). Stored in `crm/offerings.md`.

**Fund Summary Bar:**
- Shows: prospect count, total pipeline target, committed amount, fund target
- **Committed = sum of Targets from stages 6. Verbal + 7. Legal / DD + 8. Closed**
- Visual progress bar (committed / fund target)

**Pipeline Table:**
- Default columns: Org (linked), Urgency, Stage, Target, Tasks, Assigned To, Notes, Last Touch
- Additional hideable columns: Committed (legacy, hidden by default), Org Type, Closing, Primary Contact
- Column manager (gear icon) to show/hide and reorder columns, persisted in localStorage
- Stage-grouped rows with subtotal rows showing count and sum of targets
- "8. Closed" and "Declined" stages collapsed by default
- "Include Closed" toggle in header
- Inline field editing: click Stage/Urgency/Target/Assigned To/Notes/Closing cells to edit in-place
- Stage/Urgency edit via dropdown, Target via text input, Notes via textarea

**Tasks column (interactive):**
- Each task rendered as a clickable item with priority dot, owner badge, and description
- Clicking a task opens the shared task edit modal with pre-filled data
- Hover highlight on task items
- Tasks include `section`, `index`, `priority`, `owner`, and `org` metadata from backend

**People Drawer** (slide-out from nav):
- Lists all KB people from `memory/people/` with role, org, type badge
- Search/filter by name
- Click to navigate to org detail page

**Orgs Drawer** (slide-out from nav):
- Lists all known organizations from `crm/contacts_index.json`
- Click to navigate to org detail page

**Unmatched Contacts panel:**
- Shows contacts from Juniper Square sync that don't match existing orgs
- Resolve (assign to org) or dismiss actions

### 3.4 Organization Detail (`/crm/org/<name>`)

Single-org view with prospects, contacts, tasks, interactions, and intel.

**Prospect cards:** Each offering shows the prospect record with editable fields (Stage, Urgency, Target, Assigned To, Notes, Closing). Click field to edit inline.

**Contacts table:** Name, email, phone, type — with add/edit capability.

**Tasks section:** Open CRM tasks linked to this org via `(OrgName)` suffix in TASKS.md.

**Interactions feed:** Chronological log from `crm/interactions.md`.

**Intel panel:** Contents of `memory/people/<org-slug>.md` if it exists.

### 3.5 Prospect Edit (`/crm/prospect/<offering>/<org>`)

Full-page prospect editor for all fields. Used for detailed editing beyond inline table edits.

---

## 4. Pipeline Stages

```
Declined          (terminal — excluded from active counts)
1. Prospect
2. Cold
3. Outreach
4. Engaged
5. Interested
6. Verbal          → counts toward Committed
7. Legal / DD      → counts toward Committed
8. Closed          → counts toward Committed (collapsed in UI by default)
```

**Removed stages:** "8. Committed" was removed (2026-03-04). "9. Closed" was renumbered to "8. Closed".

---

## 5. Data Model

### 5.1 Prospects (`crm/prospects.md`)

```markdown
## [Offering Name]

### [Organization Name]
- **Stage:** 6. Verbal
- **Target:** $50,000,000
- **Primary Contact:** Susannah Friar
- **Closing:** Final
- **Urgency:** High
- **Assigned To:** Oscar Vasquez
- **Notes:** Sent Credit and Index Comparisons on 2/25
- **Last Touch:** 2026-03-02
```

Field order (PROSPECT_FIELD_ORDER): Stage, Target, Primary Contact, Closing, Urgency, Assigned To, Notes, Last Touch.

Editable fields: stage, urgency, target, assigned_to, notes, closing.

Some legacy prospects may have additional fields (Org Type) that are stored but not in the standard field order.

### 5.2 Tasks (`TASKS.md`)

```markdown
## Fundraising - Me
- [ ] **[Hi]** **@Oscar** Follow up with Jared on UTIMCO materials (UTIMCO)
- [ ] **[Med]** Schedule call with Zoe at WTW (Willis Towers Watson)
- [x] **[Med]** Send quarterly update to LPs

## Waiting On
- [ ] **[Med]** **@Truman** Prepare investor deck updates (Merseyside Pension Fund)

## Work
- [ ] **[Hi]** Review Built Technologies implementation plan

## Personal
- [ ] **[Low]** Schedule dentist appointment

## Done
- [x] **[Med]** Complete BDR update for February
```

**Sections:** Fundraising - Me, Waiting On, Work, Personal, Done
**Format:** `- [ ] **[Priority]** **@Owner** Description (OrgName)`
- Priority: Hi / Med / Low
- Owner: defaults to Oscar if omitted
- (OrgName): suffix links task to CRM prospect
- Task index: 0-based within each section, counting all tasks (open + done)

### 5.3 Configuration (`crm/config.md`)

Defines: Pipeline Stages, Terminal Stages, Organization Types, Closing Options, Urgency Levels, AREC Team members.

### 5.4 Offerings (`crm/offerings.md`)

```markdown
## AREC Debt Fund II
- **Target:** $1,000,000,000
- **Hard Cap:**

## Mountain House Refi
- **Target:** $35,000,000
- **Hard Cap:** $35,000,000

## JVs and Finance
- **Target:**
- **Hard Cap:**
```

---

## 6. API Reference

### 6.1 Dashboard APIs

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Dashboard page (server-rendered) |
| POST | `/api/task/complete` | Mark task complete (legacy, body: `{text}`) |
| POST | `/api/task/add` | Add task (legacy, body: `{text, priority}`) |

### 6.2 CRM / Pipeline APIs

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/crm` | Pipeline page |
| GET | `/crm/org/<name>` | Organization detail page |
| GET | `/crm/prospect/<offering>/<org>` | Prospect edit page |
| GET | `/crm/api/offerings` | List all offerings |
| GET | `/crm/api/prospects?offering=&include_closed=` | List prospects (enriched with `_tasks`) |
| GET | `/crm/api/fund-summary?offering=` | Fund summary stats |
| PATCH | `/crm/api/prospect/field` | Update single prospect field inline |
| GET | `/crm/api/org/<name>` | Organization data (prospects, contacts, tasks, interactions, intel) |
| PATCH | `/crm/api/org/<name>` | Update org contacts |
| POST | `/crm/api/contact` | Add contact to org |
| PATCH | `/crm/api/contact/<org_and_name>` | Update contact |
| POST | `/crm/api/prospect/save` | Save full prospect record |
| POST | `/crm/api/prospect` | Create new prospect |
| GET | `/crm/api/unmatched` | List unmatched JS contacts |
| POST | `/crm/api/unmatched/resolve` | Resolve unmatched contact |
| DELETE | `/crm/api/unmatched/<email>` | Dismiss unmatched contact |
| GET | `/crm/api/orgs` | List all known organizations |
| GET | `/crm/api/kb-people` | List KB people for drawer |

### 6.3 Tasks APIs

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/tasks` | Kanban board page |
| GET | `/tasks/api/tasks` | All tasks by section (with index) |
| POST | `/tasks/api/task` | Create task (body: `{section, text, priority, context, assigned_to}`) |
| PUT | `/tasks/api/task/<section>/<index>` | Update task (body: `{text, priority, assigned_to, section}`) |
| DELETE | `/tasks/api/task/<section>/<index>` | Delete task |
| POST | `/tasks/api/task/<section>/<index>/complete` | Mark task complete |
| POST | `/tasks/api/task/<section>/<index>/restore` | Restore completed task |

---

## 7. Shared Components

### 7.1 Task Edit Modal (`task-edit-modal.js` + `task-edit-modal.css`)

A shared modal component used across Dashboard, Tasks, and Pipeline pages for editing tasks.

**Setup (per page):**
```javascript
window.TASK_MODAL_TEAM = CONFIG.team || [];
window.TASK_MODAL_SECTIONS = ['Fundraising - Me', 'Work', 'Personal'];
window.taskModalOnSave = function() { /* reload data */ };
window.taskModalOnDelete = function() { /* reload data */ };
```

**Usage:**
```javascript
openTaskEditModal({
  title: 'Edit Task',
  text: 'Follow up with Jared',
  priority: 'Hi',
  assigned_to: 'Oscar',
  section: 'Fundraising - Me',
  index: 3,
  org: 'UTIMCO',
  showDelete: true,
});
```

**Fields:** Task text (textarea), Priority (Hi/Med/Low dropdown), Assigned To (team dropdown), Section (dropdown), Org badge (read-only).

**API calls:** PUT for save, DELETE for remove. Both use `/tasks/api/task/<section>/<index>`.

**Injection:** Self-executing IIFE that injects modal HTML into DOM on first use. Includes Escape key and overlay click to close.

### 7.2 Navigation Bar

Consistent across all pages:
```
Dashboard | Tasks | Pipeline          [Overwatch logo]          [date / People / Orgs buttons]
```
Active page highlighted. Pipeline page adds People and Orgs drawer buttons in nav-right.

---

## 8. Data Flow

### 8.1 Prospect → Task Linkage

Tasks in TASKS.md link to prospects via `(OrgName)` suffix. The function `load_tasks_by_org()` in `crm_reader.py` parses TASKS.md, extracts org-linked tasks with their section, index, priority, and owner, then groups them by org name. The `/crm/api/prospects` endpoint enriches each prospect with both a flat `Tasks` string (for display) and a structured `_tasks` array (for modal editing).

### 8.2 Fund Summary Calculation

`get_fund_summary()` in `crm_reader.py`:
- **Active prospects:** all prospects NOT in terminal stages or "0. Not Pursuing" or "Declined"
- **Total pipeline:** sum of Target amounts from active prospects
- **Committed:** sum of Target amounts from prospects in stages 6. Verbal, 7. Legal / DD, 8. Closed
- **Fund target:** from offerings.md Target field

### 8.3 Task Indexing

Tasks are indexed 0-based within each TASKS.md section. Both open (`- [ ]`) and done (`- [x]`) tasks count toward the index. This matches the Tasks API which uses `_find_task_line()` to locate tasks by section + index for PUT/DELETE/complete/restore operations.

---

## 9. External Integrations

| System | Purpose | Module |
|--------|---------|--------|
| Microsoft Graph | Calendar, email, OneDrive | `ms_graph.py`, `graph_auth.py` |
| Juniper Square | LP/prospect data sync | `crm_graph_sync.py` |
| Notion | Meeting transcripts + summaries | Via CLAUDE.md meeting sync workflow |
| Outlook | Calendar events, #productivity folder | Via MCP connectors |
| Egnyte | Document storage (A&D loans) | Via MCP connectors |
| SharePoint | Document storage (Vertical loans) | Via MCP connectors |

---

## 10. UI Design

**Color palette:**
- Background: `#f8f9fa` / `#f8fafc`
- Cards: `#ffffff`
- Nav: `#1a1a2e`
- Accent: `#D97757` (warm terracotta)
- Text: `#1e293b` (primary), `#475569` (secondary), `#94a3b8` (muted)
- Priority dots: Hi = `#ef4444`, Med = `#f59e0b`, Low = `#3b82f6` or `#94a3b8`
- Stage badges: 7+ = green, 5-6 = blue, 3-4 = yellow, 1-2 = gray
- Urgency badges: High = red, Med = amber, Low = gray
- Last Touch dots: ≤7d = green, ≤14d = amber, >14d = red

**Typography:** Inter (Google Fonts) for Dashboard/Tasks, system fonts for Pipeline.

**Interactions:** Inline editing, modal dialogs, collapsible sections, hover states, toast notifications for task completion with undo.

---

## 11. Changelog

### 2026-03-04
- Removed "8. Committed" pipeline stage
- Renamed "9. Closed" to "8. Closed" across all files
- Updated Committed formula: now sums targets from stages 6. Verbal + 7. Legal / DD + 8. Closed
- Removed "Committed" field from prospect records (PROSPECT_FIELD_ORDER, prospects.md, org detail)
- Created shared task edit modal component (`task-edit-modal.js` + `task-edit-modal.css`)
- Integrated shared modal into Tasks kanban page (replaced inline edit form)
- Integrated shared modal into Pipeline page (clickable task items with metadata)
- Refactored Dashboard to use shared modal (removed custom modal HTML/CSS/JS)
- Updated `load_tasks_by_org()` to include section, index, and priority per task
- Added structured `_tasks` array to prospects API response for modal editing
- Added "JVs and Finance" offering
- Renamed "CRM" to "Pipeline" across all navigation links
