SPEC: Overwatch Repo Scaffold
Project: overwatch (new repo) | Date: 2026-03-15
Status: Ready for implementation

---

## 1. Objective

Create a new `overwatch` repository for Oscar's personal productivity system — separate from the CRM. This is a scaffold: stand up the repo structure, move existing components that belong to Overwatch, create a minimal Flask app, and verify it runs. No new features in this spec.

## 2. Scope

### In Scope
- Create new repo at `~/Dropbox/projects/overwatch/`
- Scaffold Flask app with task management (migrated from arec-crm)
- Move personal productivity files: TASKS.md, inbox.md, briefing system, meeting-debrief skill
- Create Overwatch data directories: people/, projects/, notes/
- Create CLAUDE.md with Overwatch conventions
- Create minimal Overwatch dashboard (tasks + calendar view)
- Ensure arec-crm still works after files are moved (any shared files get copied, not moved)

### Out of Scope
- Gmail integration (future — try Gmail MCP first, see FUTURE_FEATURES.md)
- iCloud Reminders/Calendar integration (future — spec exists)
- Custom Overwatch /update command (future — use native `/productivity:update` with Overwatch repo first)
- New features (Projects, Notes entities)
- Voice note transcription
- CRM task display in Overwatch dashboard (future — read-only cross-repo, see FUTURE_FEATURES.md)
- iPhone Shortcuts → CRM task routing (future — see FUTURE_FEATURES.md)

## 3. Business Rules

- Overwatch is Oscar-only. No multi-user, no auth. `DEV_USER=oscar` in .env.
- Overwatch has its own TASKS.md. CRM has its own task tracking. They do not share a task file.
- Overwatch has its own people/ directory for personal contacts. CRM keeps contacts/ or memory/people/ for investor contacts. 95%+ of people will be in CRM. Overwatch people are personal network.
- Meeting summaries stay exclusively in CRM. Overwatch does not have meeting-summaries/.
- The meeting-debrief skill moves to Overwatch (it's about calendar gap detection + personal capture, not CRM data).
- Both systems should "know the other exists" — CLAUDE.md in each repo references the other repo's location and purpose.
- Morning briefing moves to Overwatch. It can read CRM data via filesystem path for investor intel, but the briefing engine lives in Overwatch.

## 4. Data Model

All markdown/JSON, no database.

### People (personal contacts)
```
overwatch/data/people/{slug}.md
```
Format: Same as arec-crm memory/people/*.md
```markdown
# Person Name

## Overview
- **Relationship:** friend | family | colleague | advisor | service-provider
- **Email:** person@gmail.com
- **Phone:** +1-555-1234
- **Notes:** How Oscar knows them
```

### Tasks
```
overwatch/TASKS.md
```
Format: Same as arec-crm TASKS.md (sections, priorities, assignees, org tags)

### Projects (stub — empty for now)
```
overwatch/data/projects/{slug}.md
```
Format TBD in future spec.

### Notes (stub — empty for now)
```
overwatch/data/notes/{date}-{slug}.md
```
Format TBD in future spec.

## 5. Repo Structure

```
overwatch/
├── app/
│   ├── __init__.py
│   ├── delivery/
│   │   ├── __init__.py
│   │   ├── dashboard.py              # Flask app (port 3001)
│   │   └── tasks_blueprint.py        # Task routes (copied from arec-crm)
│   ├── sources/
│   │   ├── __init__.py
│   │   └── memory_reader.py          # TASKS.md + inbox parser (copied from arec-crm)
│   ├── briefing/
│   │   ├── __init__.py
│   │   ├── generator.py              # Claude API call (copied from arec-crm)
│   │   └── prompt_builder.py         # Briefing prompt assembly (copied from arec-crm)
│   ├── templates/
│   │   ├── _nav.html                 # Overwatch nav bar
│   │   ├── dashboard.html            # Main dashboard (tasks + calendar)
│   │   └── tasks/tasks.html          # Task management page
│   ├── static/                        # CSS (can copy from arec-crm, retheme later)
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   └── test_task_parsing.py      # Copied from arec-crm
│   └── requirements.txt
├── data/
│   ├── people/                        # Personal contacts (starts empty)
│   ├── projects/                      # Project files (starts empty)
│   └── notes/                         # Notes (starts empty)
├── skills/
│   └── meeting-debrief.md            # Moved from arec-crm
├── main.py                            # Morning briefing entry point (moved from arec-crm/app/main.py)
├── TASKS.md                           # Oscar's personal task list (NEW — starts with Personal section from arec-crm TASKS.md)
├── inbox.md                           # Voice capture drop point
├── .env.example
├── CLAUDE.md
└── .gitignore
```

## 6. Migration Steps

### Copy from arec-crm (do NOT delete originals yet)
1. `app/sources/memory_reader.py` → `overwatch/app/sources/memory_reader.py`
2. `app/delivery/tasks_blueprint.py` → `overwatch/app/delivery/tasks_blueprint.py`
3. `app/briefing/generator.py` → `overwatch/app/briefing/generator.py`
4. `app/briefing/prompt_builder.py` → `overwatch/app/briefing/prompt_builder.py`
5. `app/templates/tasks/tasks.html` → `overwatch/app/templates/tasks/tasks.html`
6. `app/templates/dashboard.html` → `overwatch/app/templates/dashboard.html`
7. `app/tests/test_task_parsing.py` → `overwatch/app/tests/test_task_parsing.py`
8. `skills/meeting-debrief.md` → `overwatch/skills/meeting-debrief.md`
9. `inbox.md` → `overwatch/inbox.md`
10. `SHORTCUT-SETUP.md` → `overwatch/SHORTCUT-SETUP.md`

### iPhone Shortcuts Capture (preserve existing flow)
The existing iOS Shortcut appends voice-captured notes to `inbox.md`. After the Overwatch repo is created:
- Update the Shortcut's file path to point to `~/Dropbox/projects/overwatch/inbox.md`
- The native `/productivity:update` command (when run with Overwatch as the working directory) will read TASKS.md and memory/ — but it does NOT automatically read inbox.md
- For now: Oscar manually reviews inbox.md during update sessions and Claude processes it conversationally
- Future: Build a custom pre-update step that parses inbox.md → TASKS.md before `/productivity:update` runs

### Extract from arec-crm TASKS.md
- Copy the "Personal" section from arec-crm TASKS.md into overwatch TASKS.md
- Leave the "Personal" section in arec-crm TASKS.md for now (cleanup later)

### Create new
- `overwatch/app/delivery/dashboard.py` — minimal Flask app, mounts tasks_blueprint
- `overwatch/app/templates/_nav.html` — Overwatch-branded nav (not AREC CRM)
- `overwatch/CLAUDE.md` — Overwatch project instructions
- `overwatch/.env.example`
- `overwatch/.gitignore`

## 7. Dashboard (minimal)

The initial Overwatch dashboard shows:
- Tasks panel (from TASKS.md, grouped by section)
- Calendar panel (placeholder — reads dashboard_calendar.json from arec-crm via filesystem path if it exists, otherwise shows "No calendar connected")
- No email panel, no memory panel (future)

Port: 3001 (arec-crm runs on 3001 too, so one at a time — or change one of them). Recommend Overwatch on 3002.

## 8. CLAUDE.md Content

```markdown
# overwatch

Personal productivity system for Oscar Vasquez. Manages tasks, people (personal network), projects, notes, and daily briefings. Markdown-backed, single-user, local deployment.

**Location:** `~/Dropbox/projects/overwatch/`
**Branch:** `main`
**Sister repo:** `~/Dropbox/projects/arec-crm/` (CRM — investor pipeline, fundraising)

---

## Run Commands

python3 app/delivery/dashboard.py                 # Web dashboard — http://localhost:3002
python3 main.py                                    # Morning briefing
python3 -m pytest app/tests/ -v                    # Tests

## Key Files

| File | Purpose |
|------|---------|
| app/sources/memory_reader.py | TASKS.md + inbox parser |
| app/delivery/dashboard.py | Flask app (dashboard + tasks) |
| app/delivery/tasks_blueprint.py | Task routes |
| main.py | Morning briefing orchestrator |
| TASKS.md | Task list (sections, priorities, assignees) |
| data/people/ | Personal contact files |

## Non-Obvious Conventions

- Markdown is the data layer. No database.
- CRM is a separate repo. Overwatch can read CRM files via filesystem path for cross-reference.
- People in data/people/ are personal contacts. Investor contacts live in arec-crm.
- Meeting summaries live exclusively in arec-crm. Overwatch does not store meetings.
- Skills are instructional guides for Claude Desktop, not executable scripts.

## Active Constraints

- Do not import from arec-crm Python modules. Read arec-crm data files via filesystem path only.
- No database. No SQLAlchemy. No migrations.
- Port 3002 (arec-crm uses 3001).
```

## 9. Constraints

- Do not break arec-crm. Copy files, don't move them. arec-crm cleanup of duplicates happens in a separate step after both repos are verified.
- No new features. This is a scaffold — existing code in a new home.
- Keep the same task line format (priority, status, assignee, org tag, completion date).
- Morning briefing can degrade gracefully if arec-crm data files aren't available.

## 10. Acceptance Criteria

- `overwatch/` repo exists at `~/Dropbox/projects/overwatch/`
- `git init` with initial commit
- `python3 app/delivery/dashboard.py` starts on port 3002 without errors
- Tasks page loads and displays TASKS.md content
- Dashboard loads (calendar panel shows placeholder if no calendar data)
- `python3 -m pytest app/tests/ -v` passes
- CLAUDE.md exists and references arec-crm as sister repo
- `data/people/`, `data/projects/`, `data/notes/` directories exist (empty is fine)
- arec-crm still starts and works independently

## 11. Files Likely Touched

All files are new (new repo). Source files copied from arec-crm:
- `app/sources/memory_reader.py`
- `app/delivery/tasks_blueprint.py`
- `app/briefing/generator.py`, `prompt_builder.py`
- `app/templates/dashboard.html`, `tasks/tasks.html`
- `app/tests/test_task_parsing.py`
- `skills/meeting-debrief.md`
