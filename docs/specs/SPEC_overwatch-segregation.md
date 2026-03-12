SPEC: Overwatch Segregation
Project: arec-crm → overwatch (new project)
Date: 2026-03-11
Status: ✅ COMPLETE — Segregated March 12, 2026. Overwatch at ~/Dropbox/projects/overwatch/

---

## 1. Objective

Extract Oscar's personal productivity layer from the arec-crm codebase into a standalone project called "Overwatch." Overwatch is Oscar's private intelligence and task management tool — it handles on-demand briefings, mixed personal/work tasks, and maintains its own separate people knowledge base (family, contractors, personal network). The AREC CRM will become a clean multi-user fundraising platform with no personal productivity features baked in.

## 2. Scope

### In Scope

- Create new `overwatch/` project directory (sibling to `arec-crm/` in `~/Dropbox/projects/`)
- Move morning briefing orchestrator (`app/main.py`) and all briefing-related modules
- Move task management (TASKS.md, task-related dashboard routes, task blueprint)
- Move meeting summaries system (`meeting-summaries/`, meeting routes)
- Move memory system (`memory/CLAUDE.md`, `memory/context/`, `memory/projects/`, `memory/glossary.md`)
- Create Overwatch's own people knowledge base (initially empty — personal contacts only)
- Move dashboard home page (calendar widget, task columns, meeting list) into Overwatch
- Move `briefing_latest.md` and `dashboard_calendar.json` output files
- Move Cowork skills that are Oscar-only: `skills/meeting-debrief.md`, `skills/email-scan.md` (the instructional guides, not executable code)
- Remove the launchd-scheduled 5 AM briefing entirely (per architecture decision)
- Keep Overwatch as a local-only Flask app on Oscar's machine (no Azure deployment)
- Preserve the on-demand calendar refresh capability in Overwatch's dashboard
- Note: `app/briefing/brief_synthesizer.py` stays in AREC CRM (powers relationship brief synthesis). Overwatch copies `generator.py` and `prompt_builder.py` for future on-demand briefings.

### Out of Scope

- Overwatch does NOT get its own Azure deployment (local only, single user)
- Overwatch does NOT ingest Oscar's personal email yet (future phase)
- No migration of `memory/people/*.md` — those are CRM contacts and stay in AREC CRM's canonical knowledge base; Overwatch starts with an empty personal people directory
- No changes to the AREC CRM's PostgreSQL schema or Azure infrastructure
- No new authentication for Overwatch (Oscar runs it locally, no SSO needed)

## 3. Business Rules

- Overwatch is single-user (Oscar only). No auth middleware needed.
- TASKS.md is the sole task source of truth for Overwatch. Sections: "Fundraising - Me", "Fundraising - Others", "Other Work", "Personal", "Done". All five sections move to Overwatch.
- The morning briefing (`main.py`) is removed entirely — not moved, not refactored. The briefing prompt builder, generator, and Claude API call modules can be preserved in Overwatch for future on-demand use, but the scheduled 5 AM run and launchd integration are deleted.
- `dashboard_calendar.json` is written by the on-demand calendar refresh endpoint; Overwatch's dashboard reads it at startup.
- The "Settler" filter (exclude from briefings) no longer applies since briefings are removed, but preserve the convention in comments for future on-demand pulls.
- Overwatch's people knowledge base is entirely separate from the CRM's canonical contacts. Individuals can exist in both (e.g., "Adrian" as son in Overwatch, colleague in AREC CRM). No sync between them.

## 4. Data Model / Schema Changes

No database changes. Overwatch is file-based (markdown + JSON), same as the current local setup.

### Overwatch File Structure

```
overwatch/
├── CLAUDE.md                     # Project instructions for Claude Code
├── TASKS.md                      # Moved from arec-crm root
├── briefing_latest.md            # Last generated briefing (future use)
├── dashboard_calendar.json       # Calendar data for dashboard
├── memory/
│   ├── context/                  # Company context (moved from arec-crm/memory/)
│   ├── projects/                 # Project notes (moved)
│   └── glossary.md               # Terms and acronyms (moved)
├── people/                       # NEW: Overwatch-only personal contacts
│   └── (empty initially)
├── meeting-summaries/            # Moved from arec-crm root
│   └── YYYY-MM-DD-slug.md
├── skills/                       # Instructional guides for Cowork
│   ├── meeting-debrief.md
│   └── email-scan.md
├── app/
│   ├── main.py                   # Stripped to on-demand briefing only (no schedule)
│   ├── auth/
│   │   └── graph_auth.py         # Device code flow for Graph API (copied)
│   ├── briefing/
│   │   ├── generator.py          # Claude API call (copied)
│   │   └── prompt_builder.py     # Prompt construction (copied)
│   ├── delivery/
│   │   ├── dashboard.py          # Overwatch dashboard (tasks, calendar, meetings)
│   │   └── tasks_blueprint.py    # Task CRUD routes (moved)
│   ├── sources/
│   │   ├── memory_reader.py      # TASKS.md + memory loader (copied)
│   │   └── ms_graph.py           # Calendar/email fetch (copied)
│   ├── static/                   # Dashboard CSS/JS (copied, trimmed of CRM assets)
│   ├── templates/
│   │   ├── dashboard.html        # Main dashboard (tasks + calendar + meetings)
│   │   ├── meeting_detail.html   # Meeting summary view/edit
│   │   └── tasks/
│   │       └── tasks.html        # Full task board
│   └── tests/
│       └── test_task_parsing.py  # Task parsing tests (moved)
└── requirements.txt              # Flask, msal, anthropic, python-dotenv
```

## 5. UI / Interface

### Overwatch Dashboard (port 3001)

Overwatch keeps the current dashboard layout:

- **Left column**: Task sections (Fundraising - Me, Fundraising - Others, Other Work, Personal) with priority badges, status chips, inline complete/edit
- **Right column**: Today's calendar (with refresh button), recent meeting summaries
- **Top bar**: "Overwatch" branding, no user menu (single user)

### States

- **Loading**: Spinner while calendar refreshes via Graph API
- **Empty calendar**: "No events today" message with manual refresh button
- **Stale calendar**: Warning banner showing last-fetched date (existing behavior)
- **Auth expired**: Message directing Oscar to re-authenticate via terminal (`python3 app/main.py --auth`)

### Removed from Overwatch

- All `/crm` routes and CRM navigation
- Pipeline table, prospect detail, org detail, relationship briefs
- People search (CRM contacts)
- Email log viewer

## 6. Integration Points

- **Reads from**: Microsoft Graph API (calendar events, emails via device code token)
- **Reads from**: TASKS.md (local file)
- **Reads from**: `meeting-summaries/*.md` (local files)
- **Reads from**: `memory/` directory (local files)
- **Writes to**: `dashboard_calendar.json` (on calendar refresh)
- **Writes to**: TASKS.md (on task CRUD operations)
- **Writes to**: `meeting-summaries/*.md` (on meeting edit/save)
- **Calls**: Claude API (for future on-demand briefing generation)
- **Does NOT read/write**: Any CRM files, PostgreSQL, or Azure services

## 7. Constraints

- Overwatch must run independently — zero imports from arec-crm. Copy shared modules (`graph_auth.py`, `ms_graph.py`, `memory_reader.py`) rather than creating a shared library.
- Port 3001 for Overwatch dashboard. AREC CRM dashboard should move to port 3002 (or be Azure-only).
- Graph API token cache stays at `~/.arec_briefing_token_cache.json` — shared between Overwatch and any local dev CRM usage. This is fine since both use Oscar's credentials.
- Do not create a Python package or monorepo structure. Two separate project directories.
- Preserve the existing task line format: `- [ ] **[Pri]** text @assigned (context) [org:OrgName] — completed YYYY-MM-DD`

## 8. Acceptance Criteria

- [ ] `overwatch/` project directory exists at `~/Dropbox/projects/overwatch/`
- [ ] `python3 app/delivery/dashboard.py` starts Overwatch dashboard on port 3001
- [ ] Dashboard displays tasks from TASKS.md grouped by section
- [ ] Calendar refresh button fetches today's events from Graph API and updates display
- [ ] Meeting summaries list renders with clickable detail pages
- [ ] Task CRUD works: create, edit priority/status/section, complete, delete, restore
- [ ] All `/crm` routes are absent from Overwatch
- [ ] `arec-crm/` no longer contains: TASKS.md, `meeting-summaries/`, `memory/CLAUDE.md`, `memory/context/`, `memory/projects/`, `memory/glossary.md`, `briefing_latest.md`, `dashboard_calendar.json`
- [ ] `arec-crm/app/main.py` is deleted (morning briefing removed entirely)
- [ ] `arec-crm/` still has `memory/people/*.md` (CRM canonical contacts stay)
- [ ] `python3 -m pytest app/tests/` passes in both projects
- [ ] Overwatch has its own `CLAUDE.md` with project instructions
- [ ] Feedback loop prompt has been run

## 9. Files Likely Touched

### Moved to Overwatch (delete from arec-crm)

| File | Reason |
|------|--------|
| `app/main.py` | Morning briefing orchestrator → gut scheduled logic, keep on-demand shell |
| `app/delivery/tasks_blueprint.py` | Task CRUD routes |
| `app/sources/memory_reader.py` | TASKS.md + memory loader |
| `app/tests/test_task_parsing.py` | Task parsing tests |
| `TASKS.md` | Task source of truth |
| `meeting-summaries/` | All meeting summary files |
| `memory/context/` | Company context (me.md, company.md) |
| `memory/projects/` | Project notes |
| `memory/glossary.md` | Terms and acronyms |
| `memory/meetings.md` | Meeting tracking |
| `memory/org-locations.md` | Organization locations |
| `briefing_latest.md` | Last briefing |
| `dashboard_calendar.json` | Calendar cache |
| `skills/meeting-debrief.md` | Cowork skill guide |
| `skills/email-scan.md` | Cowork skill guide |

### Copied to Overwatch (keep in arec-crm too)

| File | Reason |
|------|--------|
| `app/auth/graph_auth.py` | Device code flow — Overwatch needs its own copy |
| `app/briefing/generator.py` | Claude API call — for future on-demand briefings |
| `app/briefing/prompt_builder.py` | Prompt construction — for future on-demand briefings |
| `app/sources/ms_graph.py` | Graph API wrapper — calendar/email fetch |

### Modified in arec-crm

| File | Reason |
|------|--------|
| `app/delivery/dashboard.py` | Remove task loading, meeting loading, calendar refresh, meeting routes. Dashboard becomes a redirect to `/crm` |
| `app/delivery/crm_blueprint.py` | No changes needed — already self-contained |
| `CLAUDE.md` | Update project instructions: remove references to briefings, TASKS.md, meeting-summaries, memory/ |
