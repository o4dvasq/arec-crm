# Second Brain — Component Inventory

**Date:** 2026-03-15
**Purpose:** Map every existing component to the Second Brain architecture diagram, identify gaps, and plan the repo split.

---

## Architecture Overview (from diagram)

Two systems, one orchestration hub:

**LEFT SIDE — Overwatch (Personal Productivity)**
- Overwatch UI (web dashboard)
- Overwatch DB (markdown, local): People, Projects, Tasks, Notes
- Inputs: iPhone Shortcuts (voice notes), Gmail (personal email), iCloud (reminders, calendar events)
- Claude Desktop as conversational interface

**RIGHT SIDE — CRM (Investor Pipeline)**
- CRM UI (web dashboard)
- CRM DB (markdown today, Postgres tomorrow): Offerings, Prospects, Orgs, Contacts, Tasks, Meetings
- Inputs: Microsoft Graph (emails, meetings, transcripts, Teams chats)
- Claude Desktop as conversational interface

**CENTER — Claude Productivity /Update (Enhanced Scripts)**
- Pulls from all data sources
- Writes to both DBs with user approval
- Feeds aggregated data to both Claude Desktop sessions

---

## Current State: What Exists

### CRM SIDE (arec-crm repo, markdown-local branch)

| Diagram Component | Status | Implementation | Location |
|---|---|---|---|
| CRM UI | **EXISTS** | Flask + 13 templates, 69 routes | `app/delivery/crm_blueprint.py`, `app/templates/crm_*.html` |
| CRM DB — Offerings | **EXISTS** | Markdown file | `crm/offerings.md` (13 lines) |
| CRM DB — Prospects | **EXISTS** | Markdown file, 75 parser functions | `crm/prospects.md` (1728 lines) |
| CRM DB — Orgs | **EXISTS** | Markdown file | `crm/organizations.md` (754 lines) |
| CRM DB — Contacts | **EXISTS** | Markdown + index file | `crm/contacts_index.md` + `memory/people/*.md` (211 files) |
| CRM DB — Tasks | **PARTIAL** | CRM tasks parse from TASKS.md by org tag | `crm_reader.py: load_tasks_by_org()` |
| CRM DB — Meetings | **PARTIAL** | JSON file (mostly empty) + meeting_history.md | `crm/prospect_meetings.json`, `crm/meeting_history.md` |
| Microsoft Graph → Emails | **EXISTS** | Graph auth + email scan skill | `auth/graph_auth.py`, `skills/email-scan.md`, `crm/email_log.json` |
| Microsoft Graph → Meetings | **EXISTS** | Calendar fetch in main.py | `app/main.py`, `dashboard_calendar.json` |
| Microsoft Graph → Transcripts | **NOT BUILT** | Referenced in diagram but no code | — |
| Microsoft Graph → Teams Chats | **NOT BUILT** | Graph scope exists (`Chat.Read`) but no implementation | — |
| CRM Brief Synthesis | **EXISTS** | Claude API integration | `briefing/brief_synthesizer.py`, `sources/relationship_brief.py` |
| Direct User Updates (CRM UI) | **EXISTS** | Edit forms, API endpoints | All PATCH/POST routes in crm_blueprint |
| User Approved CRM Updates | **EXISTS** | Email scan → match → enrich flow | `skills/email-scan.md` workflow |

### OVERWATCH SIDE (currently mixed into arec-crm)

| Diagram Component | Status | Implementation | Location |
|---|---|---|---|
| Overwatch UI | **PARTIAL** | Dashboard exists but is CRM-centric | `app/templates/dashboard.html` (4 panels: meetings, tasks, email, memory) |
| Overwatch DB — People | **SHARED w/ CRM** | Person files serve both systems | `memory/people/*.md` or `contacts/*.md` (211 files) |
| Overwatch DB — Projects | **NOT BUILT** | No project entity or tracking | — |
| Overwatch DB — Tasks | **EXISTS** | TASKS.md with full parser | `TASKS.md` (161 lines, ~100 tasks), `sources/memory_reader.py` |
| Overwatch DB — Notes | **NOT BUILT** | No standalone notes system | — |
| Voice Notes → iPhone Shortcuts | **PARTIAL** | Setup doc exists, inbox.md is the drop point | `SHORTCUT-SETUP.md`, `inbox.md` |
| Task And Notes Inbox | **EXISTS** | inbox.md + drain_inbox.py | `inbox.md`, `app/drain_inbox.py` |
| Gmail (personal email) | **NOT BUILT** | No Gmail integration code | — |
| iCloud — Reminders | **NOT BUILT** | No iCloud Reminders integration | — |
| iCloud — Calendar Events | **NOT BUILT** | No iCloud Calendar integration | — |
| Morning Briefing | **EXISTS** | 5 AM launchd automation | `app/main.py` (300 lines) |
| Direct User Updates (Overwatch) | **PARTIAL** | Task edit via UI, but no people/project/notes edit | `tasks_blueprint.py` |
| User Approved Overwatch Updates | **PARTIAL** | `/productivity:update` handles task triage | Productivity plugin |

### ORCHESTRATION LAYER (Claude Productivity /Update)

| Diagram Component | Status | Implementation | Location |
|---|---|---|---|
| Claude Productivity /Update | **EXISTS** | Plugin command with --comprehensive flag | `.local-plugins/productivity/1.1.0/` |
| Enhanced Scripts | **EXISTS** | email-scan.md + meeting-debrief.md | `skills/email-scan.md`, `skills/meeting-debrief.md` |
| Initiate Data Pulls (Graph) | **EXISTS** | Graph auth + email/calendar fetch | `auth/graph_auth.py`, `sources/ms_graph.py` |
| Initiate Data Pulls (Gmail) | **NOT BUILT** | — | — |
| Initiate Data Pulls (iCloud) | **NOT BUILT** | — | — |
| Aggregated Data → CRM | **EXISTS** | Email scan enriches CRM data | `skills/email-scan.md` workflow |
| Aggregated Data → Overwatch | **PARTIAL** | Calendar → dashboard, but no deep Overwatch writes | `app/main.py` → `dashboard_calendar.json` |
| Oscar's Calendar (shared data) | **EXISTS** | Graph calendar fetch, shared across both sides | `app/main.py`, `dashboard_calendar.json` |
| Oscar's CRM Tasks (shared data) | **EXISTS** | TASKS.md org-tagged tasks visible in both | `crm_reader.py: load_tasks_by_org()` |

---

## Gap Analysis

### Must Build (Core Overwatch)

1. **Projects entity** — No project tracking at all. Need markdown schema + reader + UI.
2. **Notes entity** — No standalone notes. Meeting summaries exist but no general note capture.
3. **Gmail integration** — Personal email is a blind spot. Need OAuth + fetch + match.
4. **iCloud Reminders** — iPhone reminders not synced. Need AppleScript or Shortcuts bridge.
5. **iCloud Calendar** — Personal calendar events not pulled. Need CalDAV or Shortcuts bridge.
6. **Overwatch UI** — Dashboard exists but is CRM-focused. Need personal productivity views.
7. **Overwatch /update command** — Separate from CRM /update. Pulls Gmail, iCloud, processes notes.

### Should Build (Enhanced CRM)

8. **Teams Chat scanning** — Graph scope exists, no implementation.
9. **Meeting Transcript ingestion** — Diagram shows it, no code exists.

### Nice to Have (Polish)

10. **Voice note transcription** — Currently just text capture via Shortcuts. Could add Whisper.
11. **Project ↔ Task linking** — Tasks reference orgs but not projects.

---

## Shared Components (Need Decision)

These components currently live in arec-crm and serve BOTH systems:

| Component | Current Home | Used By | Split Decision Needed |
|---|---|---|---|
| `memory/people/*.md` (211 files) | arec-crm | CRM contacts + Overwatch people | **Duplicate or symlink?** CRM needs investor contacts; Overwatch needs personal network. Same files. |
| `TASKS.md` | arec-crm root | CRM (org-tagged tasks) + Overwatch (all tasks) | **Keep in Overwatch**, CRM reads via API or shared path |
| `meeting-summaries/` | arec-crm | CRM briefs + Overwatch debrief | **Keep in Overwatch**, CRM references via path |
| `skills/email-scan.md` | arec-crm | CRM email enrichment | **Keep in CRM** |
| `skills/meeting-debrief.md` | arec-crm | Overwatch meeting capture | **Move to Overwatch** |
| `dashboard_calendar.json` | arec-crm root | Both dashboards | **Keep in Overwatch**, CRM reads if needed |
| `inbox.md` | arec-crm root | Overwatch task capture | **Move to Overwatch** |
| `briefing_latest.md` | arec-crm root | Overwatch morning briefing | **Move to Overwatch** |
| `app/main.py` | arec-crm | Morning briefing (both CRM + personal) | **Move to Overwatch**, calls CRM API for investor intel |

---

## Proposed Repo Split

### arec-crm (CRM only)
```
arec-crm/
├── app/
│   ├── delivery/crm_blueprint.py     # CRM routes only
│   ├── sources/crm_reader.py         # CRM markdown parser
│   ├── sources/relationship_brief.py # Brief synthesis
│   ├── briefing/brief_synthesizer.py # Claude API calls
│   ├── auth/graph_auth.py            # Graph auth (shared?)
│   └── templates/crm_*.html          # CRM templates
├── crm/                              # All CRM data files
├── skills/email-scan.md              # CRM email enrichment
└── CLAUDE.md
```

### overwatch (New repo — Personal Productivity)
```
overwatch/
├── app/
│   ├── delivery/dashboard.py         # Overwatch Flask app
│   ├── delivery/tasks_blueprint.py   # Task routes
│   ├── sources/memory_reader.py      # TASKS.md, inbox parser
│   ├── sources/overwatch_reader.py   # NEW: People, Projects, Notes parser
│   └── templates/dashboard.html      # Overwatch dashboard
├── data/
│   ├── people/                       # Person files (211+)
│   ├── projects/                     # NEW: Project files
│   ├── notes/                        # NEW: Notes
│   └── meeting-summaries/            # Meeting notes
├── skills/meeting-debrief.md
├── TASKS.md
├── inbox.md
├── briefing_latest.md
├── main.py                           # Morning briefing
└── CLAUDE.md
```

### Shared concerns:
- **People files**: Overwatch owns them, CRM reads via filesystem path or API
- **Calendar**: Overwatch fetches, CRM accesses via shared JSON or API
- **Graph auth**: Shared token cache (~/.arec_briefing_token_cache.json)
- **Claude Desktop**: Two separate Cowork sessions (one per system), or one unified session with both repos mounted
