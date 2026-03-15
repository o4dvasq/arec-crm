SPEC: Second Brain Roadmap
Project: arec-crm + overwatch | Date: 2026-03-15
Status: Planning document (individual items need their own specs)

---

## 1. Objective

Build Oscar's "Second Brain" — two separate systems (CRM for fundraising, Overwatch for personal productivity) with a shared orchestration layer that pulls from Microsoft Graph, Gmail, and iCloud, and writes to both systems with user approval. This roadmap sequences the work from "get the basics working" to "full integration."

## 2. Architecture (from diagram)

```
┌─────────────────────┐                    ┌─────────────────────┐
│    OVERWATCH         │                    │       CRM           │
│                      │                    │                      │
│  Overwatch UI (:3002)│                    │  CRM UI (:3001)     │
│  People (personal)   │                    │  Offerings           │
│  Projects            │                    │  Prospects           │
│  Tasks               │                    │  Orgs                │
│  Notes               │                    │  Contacts            │
│  Markdown, Local     │                    │  Tasks               │
│                      │                    │  Meetings            │
│  ~/projects/overwatch│                    │  Markdown → Postgres │
│                      │                    │  ~/projects/arec-crm │
└────────┬─────────────┘                    └────────┬─────────────┘
         │                                           │
         │  Aggregated Data    ┌──────────────┐      │  Aggregated Data
         └─────────────────────┤  Claude       ├─────┘
           User Approved       │  Productivity │      User Approved
           Overwatch Updates   │  /Update      │      CRM Updates
                               │  Enhanced     │
                               │  Scripts      │
                               └──────┬───────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                  │
              ┌─────┴─────┐   ┌──────┴──────┐   ┌──────┴──────┐
              │  Microsoft │   │    Gmail    │   │   iCloud    │
              │   Graph    │   │  (personal) │   │ Reminders   │
              │            │   │             │   │ Calendar    │
              │ • Emails   │   │ • Personal  │   │             │
              │ • Meetings │   │   email     │   │             │
              │ • Transcpts│   │             │   │             │
              │ • Teams    │   │             │   │             │
              └────────────┘   └─────────────┘   └─────────────┘

              CRM data source   Overwatch source  Overwatch source
```

## 3. Sequencing

### Phase 0: Foundation (DO NOW)
Ship order: 0A → 0B (can overlap)

**0A. CRM Markdown Cleanup**
- Spec: `SPEC_crm-markdown-cleanup.md` (written, ready)
- Strip Postgres/Azure/Entra dead code from markdown-local branch
- Archive lessons learned
- Result: Clean, working CRM on markdown

**0B. Overwatch Repo Scaffold**
- Spec: `SPEC_overwatch-repo-scaffold.md` (written, ready)
- New repo with tasks, people stubs, minimal Flask dashboard
- Copy existing components (memory_reader, tasks_blueprint, briefing)
- Result: Overwatch runs on :3002 with task management

### Phase 1: Overwatch Core (NEXT)
Ship order: 1A → 1B → 1C (sequential)

**1A. Overwatch People**
- Spec needed
- Build `overwatch_reader.py` with person CRUD (create, read, update, list, search)
- People detail page, people list page
- Relationship field (friend, family, colleague, advisor, service-provider)
- Cross-reference: "Also in CRM" indicator if person exists in arec-crm contacts

**1B. Overwatch Projects**
- Spec needed
- Markdown schema for project files (name, status, notes, related tasks, related people)
- Project list + detail pages
- Task ↔ Project linking (tasks can reference a project)

**1C. Overwatch Notes**
- Spec needed
- Markdown files: `data/notes/YYYY-MM-DD-slug.md`
- Quick capture from dashboard (text input → creates note file)
- Notes list page, note detail page
- Optional: Tag notes with people or projects

### Phase 2: Data Source Integrations (AFTER Phase 1)
Ship order: 2A and 2B can be parallel; 2C depends on 2A

**2A. Gmail Integration (Overwatch)**
- Spec needed
- OAuth2 for Gmail API (or IMAP with app password — simpler)
- Scan personal email, match to Overwatch people by email address
- Store in `data/email_log.json` (same format as CRM's)
- Claude Desktop skill: `/gmail-scan`

**2B. iCloud Integration (Overwatch)**
- Spec needed
- Two sub-features:
  - iCloud Reminders → TASKS.md sync (via AppleScript on Mac, or Shortcuts)
  - iCloud Calendar → dashboard_calendar.json (via CalDAV or `icalBuddy` CLI)
- Likely approach: Python `subprocess` calling AppleScript/icalBuddy, not a web API
- This may be simpler as enhanced iPhone Shortcuts rather than Python code

**2C. Overwatch /update Command**
- Spec needed
- New Claude Desktop skill (or plugin command)
- Pulls: Gmail (2A), iCloud Reminders (2B), iCloud Calendar (2B)
- Writes: TASKS.md updates, people enrichment, note creation (with user approval)
- Separate from CRM /update — does not touch CRM data
- Can reference CRM data read-only for cross-system awareness

### Phase 3: Enhanced CRM Intelligence (AFTER Phase 0)
Ship order: 3A and 3B independent

**3A. Teams Chat Scanning**
- Spec needed
- Graph scope `Chat.Read` already authorized
- Scan Teams chats for CRM-relevant mentions (prospect names, org names)
- Append to email_log.json or new `crm/chat_log.json`
- Integrate into relationship briefs

**3B. Meeting Transcript Ingestion**
- Spec needed
- Graph API for meeting transcripts (requires Teams Premium or specific licensing)
- Parse transcript → extract action items, decisions, attendee contributions
- Feed into meeting summaries and relationship briefs
- May require chunking for long transcripts

### Phase 4: Cross-System Awareness (AFTER Phase 2)
Ship order: 4A

**4A. Cross-Repo Intelligence**
- Spec needed
- Overwatch CLAUDE.md knows arec-crm path; CRM CLAUDE.md knows overwatch path
- Claude Desktop can read both repos in a single session
- People dedup: If a person exists in both systems, Claude surfaces this during /update
- Morning briefing (in Overwatch) can pull CRM prospect context for investor meetings
- No shared database, no API between systems — just filesystem reads

### Phase 5: Azure / Multi-User (FUTURE)
Not specced here. See `docs/archive/azure-migration-march-2026/LESSONS_LEARNED.md` for approach.

Branch strategy when ready:
```
postgres-local (DONE) → azure-db → azure-deploy → multi-user
```

## 4. Dependencies Between Phases

```
Phase 0A (CRM cleanup) ──────────────────────────→ Phase 3 (CRM intelligence)
Phase 0B (Overwatch scaffold) → Phase 1 (core) → Phase 2 (data sources) → Phase 4 (cross-repo)
                                                                         ↗
Phase 0A ───────────────────────────────────────────────────────────────
```

Phase 0 is the critical path. Nothing else starts until CRM is clean and Overwatch exists.

## 5. Effort Estimates

| Phase | Effort | Notes |
|-------|--------|-------|
| 0A. CRM Cleanup | 2-3 hours | Mostly file deletion + guarding Graph imports |
| 0B. Overwatch Scaffold | 3-4 hours | Copy + adapt existing code, new Flask app |
| 1A. Overwatch People | 4-6 hours | New reader, templates, CRUD routes |
| 1B. Overwatch Projects | 4-6 hours | New entity, templates, task linking |
| 1C. Overwatch Notes | 2-3 hours | Simple markdown CRUD |
| 2A. Gmail Integration | 6-8 hours | OAuth complexity, email matching |
| 2B. iCloud Integration | 4-6 hours | AppleScript/Shortcuts bridge, two sub-features |
| 2C. Overwatch /update | 4-6 hours | Orchestration skill, user approval flow |
| 3A. Teams Chat | 4-6 hours | Graph API, chat parsing, log storage |
| 3B. Meeting Transcripts | 6-8 hours | Transcript API, chunking, parsing |
| 4A. Cross-Repo Intel | 2-3 hours | CLAUDE.md references, filesystem reads |

**Total: ~40-55 hours of Claude Code work across all phases**

Phase 0 (today's focus): ~5-7 hours total.

## 6. What Oscar Should Hand to Claude Code

### Right now (today)
1. Open Claude Code in `~/Dropbox/projects/arec-crm/`
2. Say: "Read docs/specs/SPEC_crm-markdown-cleanup.md and implement it"
3. Verify: app starts, CRM pages load, tests pass

### Next session
1. Open Claude Code (no project)
2. Say: "Read ~/Dropbox/projects/arec-crm/docs/specs/SPEC_overwatch-repo-scaffold.md and implement it"
3. Verify: new repo exists, dashboard starts on :3002, tasks load

### After that
Come back to Desktop, spec Phase 1A (Overwatch People), hand to Claude Code.
