# Overwatch — Master Specification
**Date:** 2026-03-06
**Version:** 2.0
**Status:** Living document — update when features ship or requirements change

---

## Quick Reference — Spec Map

| Document | Location | Status |
|---|---|---|
| **This file** | `specs/Overwatch-Master-Spec-2026-03-06.md` | Master index |
| System architecture (implemented) | `specs/active/Overwatch-Spec-2026-03-04.md` | ✅ Reference |
| Task management cleanup | `specs/active/overwatch-task-cleanup-specs.md` | 🔵 To build |
| Graph auto-capture | `specs/active/CRM-Phase5-Spec.md` | 🔵 To build |
| Intelligence layer | `specs/active/CRM-Intelligence-Layer-Spec.md` | 🟡 Partial |
| Historical / superseded | `specs/archive/` | 📦 Archive |

---

## 1. What Overwatch Is

Overwatch is AREC's internal productivity dashboard — a Flask web app backed by markdown flat files. It provides a unified interface for Fund II fundraising pipeline management, task tracking, calendar integration, and meeting intelligence. No external databases. All data lives in markdown files under `ClaudeProductivity/`.

**App URL (local):** `http://127.0.0.1:3001`
**Stack:** Python 3 / Flask / Jinja2 / vanilla JS. No frontend framework.

---

## 2. Current System State (as of 2026-03-06)

### 2.1 What Is Built and Working

| Component | Status | Notes |
|---|---|---|
| Flask app (main.py, blueprints) | ✅ | Running at :3001 |
| CRM reader / writer (crm_reader.py) | ✅ | Full parser + write-back |
| Dashboard (/) | ✅ | 2-column layout, status pills |
| Tasks kanban (/tasks) | ✅ | 4 columns, priority, inline edit |
| Pipeline (/crm) | ✅ | Tabbed, stage-grouped, inline edit |
| Column manager | ✅ | Show/hide/reorder, localStorage |
| Org detail (/crm/org/<n>) | ✅ | Prospects, contacts, tasks, interactions |
| Shared task edit modal | ✅ | Used across dashboard, tasks, pipeline |
| Task status field (New/In Progress/Complete) | ✅ | Dashboard only; `**[→]**` in TASKS.md |
| People + Orgs drawers | ✅ | Slide-out from pipeline nav |
| MS Graph auth | ✅ | graph_auth.py / MSAL |
| Unmatched contacts panel | ✅ | unmatched_review.json |
| Morning briefing (main.py) | ✅ | Generates briefing_latest.md |
| Mobile PWA (arec-mobile.html) | ✅ | Tasks + Pipeline via Dropbox API |
| Cowork plugin skills | ✅ | /crm:interview, /crm:review, /crm:inbox |
| Meeting summaries pipeline | ✅ | Notion → meeting-summaries/ |

### 2.2 What Is NOT Yet Built

| Component | Spec | Priority |
|---|---|---|
| **Graph auto-capture** (crm_graph_sync.py) | `specs/active/CRM-Phase5-Spec.md` | High |
| **Task status — kanban page** | `specs/active/overwatch-task-cleanup-specs.md` | High |
| **Task status — pipeline page** | same | High |
| **Inline status chip on task cards** | same | High |
| **Full task detail page** | same | High |
| **Assignee searchable dropdown** | same | High |
| **Prospect searchable dropdown** | same | High |
| **Intelligence layer enrichment** (briefing, pending interviews) | `specs/active/CRM-Intelligence-Layer-Spec.md` | Med |
| **Analytics page** (Phase 6) | Not yet specced | Low |

---

## 3. Architecture Summary

### 3.1 Directory Structure

```
ClaudeProductivity/
├── app/
│   ├── main.py                      # Flask app factory + route registration
│   ├── delivery/dashboard.py        # All routes: app, crm_bp, tasks_bp
│   ├── sources/
│   │   ├── crm_reader.py            # Markdown parser/writer for CRM + tasks
│   │   ├── memory_reader.py         # Knowledge base reader (people, glossary)
│   │   └── ms_graph.py              # Microsoft Graph API client
│   ├── auth/graph_auth.py           # MSAL auth for MS Graph
│   ├── briefing/
│   │   ├── generator.py             # Morning briefing generator
│   │   └── prompt_builder.py        # Briefing prompt assembly
│   ├── static/
│   │   ├── task-edit-modal.css
│   │   ├── task-edit-modal.js
│   │   └── tasks/{tasks.css, tasks.js}
│   └── templates/
│       ├── dashboard.html
│       ├── crm_pipeline.html
│       ├── crm_org_detail.html
│       ├── crm_prospect_edit.html
│       └── tasks/tasks.html
├── crm/
│   ├── config.md                    # Stages, team, urgency, closings
│   ├── offerings.md                 # Fund II ($1B), Mountain House ($35M), JVs
│   ├── prospects.md                 # ~1,313 prospect records
│   ├── interactions.md              # Interaction log per org
│   ├── contacts_index.json          # Contact → org lookup
│   ├── ai_inbox_queue.md            # Email triage queue
│   ├── pending_interviews.json      # Post-meeting interview queue
│   └── unmatched_review.json        # Unmatched Graph contacts
├── memory/
│   ├── glossary.md                  # Terms, people, companies
│   └── people/                      # Per-person intel files (*.md)
├── meeting-summaries/               # Processed meeting notes (*.md)
│   └── archive/                     # Meetings > 7 days old
├── skills/
│   ├── meeting-debrief.md           # Meeting debrief skill
│   └── email-scan.md                # Email scan skill
├── specs/
│   ├── Overwatch-Master-Spec-2026-03-06.md   ← THIS FILE
│   ├── active/                      # In-flight and reference specs
│   └── archive/                     # Historical / superseded specs
├── TASKS.md                         # Single source of truth for all tasks
├── CLAUDE.md                        # AI context / memory / instructions
├── inbox.md                         # iPhone voice capture queue
└── update.md                        # /productivity:update skill
```

### 3.2 Pipeline Stages

```
Declined          (terminal — excluded from active counts)
1. Prospect
2. Cold
3. Outreach
4. Engaged
5. Interested
6. Verbal          → counts toward Committed
7. Legal / DD      → counts toward Committed
8. Closed          → counts toward Committed (collapsed by default)
```

### 3.3 Task Format (TASKS.md)

```
- [ ] **[Hi]** **@Oscar** Follow up on NPS meeting (NPS Korea SWF)
      ^^^^^^^  ^^^^^^^^^  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      priority   owner     description + (OrgName for CRM link)
```

Status encoding:
- `New`: `- [ ]` checkbox, no tag
- `In Progress`: `- [ ]` + `**[→]**` immediately after priority
- `Complete`: `- [x]`

Sections: `Fundraising - Me` | `Waiting On` | `Work` | `Personal` | `Done`

---

## 4. Open Build Items

### 4.1 Task Management Cleanup (HIGH — hand to Claude Code now)

**Spec:** `specs/active/overwatch-task-cleanup-specs.md`

Three changes to the entire task surface area:

1. **Strip sub-text from task cards** — Notes/context renders in detail page only, not on cards
2. **Status field on all tasks** — New / Open / In Progress / Complete, with color-coded chip
3. **Inline status change + full detail page** — Chip click = dropdown; card body click = detail page with searchable Assignee and Prospect dropdowns

Applies everywhere tasks appear: board, pipeline, people, orgs, dashboard, search.

**Key decisions for Claude Code:**
- Status enum: `new` (blue) | `open` (gray) | `in_progress` (amber) | `complete` (green)
- Chip show/hide: show on cards ≥ 280px wide; dot indicator on narrow cards
- Assignee selector: single-select, searchable, clearable
- Prospect selector: single-select, searchable, clearable, optional inline create
- Existing tasks without status → migrate to `open` at deploy time

### 4.2 Graph Auto-Capture (HIGH)

**Spec:** `specs/active/CRM-Phase5-Spec.md`

Scans MS Graph (email + calendar) for interactions with known investor contacts. Logs them to `interactions.md`, updates `last_touch`, surfaces unmatched contacts for manual triage. Runs at 5 AM via launchd and on-demand via pipeline UI button.

Key module: `sources/crm_graph_sync.py` (new file).

### 4.3 Intelligence Layer (MEDIUM — partially built)

**Spec:** `specs/active/CRM-Intelligence-Layer-Spec.md`

What's working:
- `/crm:interview` and `/crm:review` Cowork skills
- CRM pulse in `/productivity:update`

Still to build:
- `write_pending_interview()` in crm_graph_sync.py (blocked by 4.2)
- Morning briefing enrichment via `prompt_builder.py`

---

## 5. API Reference (Current)

### 5.1 Dashboard APIs

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Dashboard |
| POST | `/api/task/complete` | Mark task complete (legacy) |
| POST | `/api/task/add` | Add task (legacy) |
| PATCH | `/api/task/status` | Update task status (New/In Progress/Complete) |

### 5.2 CRM APIs

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/crm` | Pipeline page |
| GET | `/crm/org/<name>` | Org detail |
| GET | `/crm/prospect/<offering>/<org>` | Prospect edit |
| GET | `/crm/api/offerings` | List offerings |
| GET | `/crm/api/prospects` | List prospects (enriched with `_tasks`) |
| GET | `/crm/api/fund-summary` | Fund summary stats |
| PATCH | `/crm/api/prospect/field` | Update single prospect field |
| GET | `/crm/api/org/<name>` | Org data (prospects, contacts, tasks, interactions) |
| PATCH | `/crm/api/org/<name>` | Update org contacts |
| POST | `/crm/api/contact` | Add contact |
| PATCH | `/crm/api/contact/<org_and_name>` | Update contact |
| POST | `/crm/api/prospect/save` | Save full prospect record |
| POST | `/crm/api/prospect` | Create new prospect |
| GET | `/crm/api/unmatched` | Unmatched JS contacts |
| POST | `/crm/api/unmatched/resolve` | Resolve unmatched contact |
| DELETE | `/crm/api/unmatched/<email>` | Dismiss unmatched contact |
| GET | `/crm/api/orgs` | All known orgs |
| GET | `/crm/api/kb-people` | KB people for drawer |

### 5.3 Task APIs

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/tasks` | Kanban board |
| GET | `/tasks/api/tasks` | All tasks by section |
| POST | `/tasks/api/task` | Create task |
| PUT | `/tasks/api/task/<section>/<index>` | Update task |
| DELETE | `/tasks/api/task/<section>/<index>` | Delete task |
| POST | `/tasks/api/task/<section>/<index>/complete` | Mark complete |
| POST | `/tasks/api/task/<section>/<index>/restore` | Restore completed task |

---

## 6. Data Model

### 6.1 Prospects (crm/prospects.md)

```markdown
## AREC Debt Fund II

### Merseyside Pension Fund
- **Stage:** 6. Verbal
- **Target:** $50,000,000
- **Primary Contact:** Susannah Friar
- **Closing:** Final
- **Urgency:** High
- **Assigned To:** Oscar Vasquez
- **Notes:** Board approval window is May 2026
- **Last Touch:** 2026-03-03
```

Field order (canonical): Stage, Target, Primary Contact, Closing, Urgency, Assigned To, Notes, Last Touch

### 6.2 Tasks (TASKS.md)

See Section 3.3 above.

### 6.3 Config (crm/config.md)

Defines: Pipeline Stages, Terminal Stages, Org Types, Closing Options, Urgency Levels, AREC Team.

Team roster (current): Tony Avila, Oscar Vasquez, Patrick Fichtner, Zach Reisner, James Walton, Anthony Albuquerque, Ian Morgan, Truman Flynn, Sahil Jethi, Nate Cichon, John Brimberry, Glen Martin, Jake Weintraub, Hamza Mirza, Kevin Van Gorder.

---

## 7. UI Design System

| Element | Value |
|---|---|
| Background | `#f8f9fa` / `#f8fafc` |
| Card surface | `#ffffff` |
| Nav | `#1a1a2e` |
| Accent | `#D97757` (warm terracotta) |
| Primary text | `#1e293b` |
| Secondary text | `#475569` |
| Muted | `#94a3b8` |
| Priority Hi | `#ef4444` |
| Priority Med | `#f59e0b` |
| Priority Low | `#3b82f6` / `#94a3b8` |
| Status New | `#3B82F6` (blue) |
| Status Open | `#6B7280` (gray) |
| Status In Progress | `#F59E0B` (amber) |
| Status Complete | `#10B981` (green) |
| Stage 7+ | green |
| Stage 5-6 | blue |
| Stage 3-4 | yellow |
| Stage 1-2 | gray |
| Last touch ≤7d | green |
| Last touch ≤14d | amber |
| Last touch >14d | red |
| Font | Inter (dashboard/tasks), system (pipeline) |

---

## 8. External Integrations

| System | Purpose |
|---|---|
| Microsoft Graph | Calendar, email, OneDrive |
| Juniper Square | LP/prospect data sync |
| Notion | Meeting transcripts + summaries (via MCP) |
| Outlook | Calendar events, #productivity folder (via MCP) |
| Egnyte | A&D loan documents (via MCP) |
| SharePoint | Vertical loan documents (via MCP) |

---

## 9. Changelog

### 2026-03-06 (this version)
- Reorganized spec folder: obsolete/superseded specs → `specs/archive/`, valid specs → `specs/active/`
- Added task management cleanup spec (`specs/active/overwatch-task-cleanup-specs.md`)
  - Task cards: strip sub-text from display
  - Status field: New / Open / In Progress / Complete across all task surfaces
  - Inline status change chip on cards
  - Full task detail page with searchable Assignee + Prospect dropdowns
- Updated master spec to reflect current build state

### 2026-03-04
- Removed "8. Committed" pipeline stage; "9. Closed" renumbered to "8. Closed"
- Committed formula now sums targets from stages 6 + 7 + 8
- Created shared task edit modal (task-edit-modal.js + .css)
- Integrated modal into dashboard, tasks, and pipeline pages
- Task status (New/In Progress/Complete) implemented on dashboard
- Two-column dashboard layout with Today's Meetings pinned in right column

### 2026-03-02
- Build audit completed: Flask app, CRM UI, Pipeline all confirmed built
- Mobile PWA confirmed working via Dropbox API (Tasks + Pipeline tabs)
- Missing files created: ai_inbox_queue.md, pending_interviews.json
- Deprecated contacts.md deleted
