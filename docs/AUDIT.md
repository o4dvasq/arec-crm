# Codebase Audit

**Project:** ClaudeProductivity
**Root:** `/Users/oscar/Dropbox/Tech/ClaudeProductivity`
**Date:** 2026-03-07
**Auditor:** Claude Code (read-only pass)

---

## 1. Entry Points

### Main Entry Points

**`app/main.py`** (284 lines) — Morning briefing orchestrator
- Invocation: `python main.py` or launchd at 5 AM daily
- Flow:
  1. Authenticate with Microsoft Graph (`get_access_token()`)
  2. Fetch today's calendar events + last 18h of email
  3. Write `dashboard_calendar.json` for web dashboard
  4. Load tasks, memory context, inbox from markdown files
  5. Build Claude prompt via `build_prompt()`
  6. Call Claude API → write `briefing_latest.md`
  7. Run auto-capture (email + calendar → CRM)
  8. Log to `~/Library/Logs/arec-morning-briefing.log`

**`app/drain_inbox.py`** (267 lines) — AI email inbox drain
- Invocation: `python3 drain_inbox.py`
- Reads unread messages from `crm@avilacapllc.com` shared mailbox, parses forwarded emails, appends structured `[AI Inbox]` entries to `inbox.md`

**`app/delivery/dashboard.py`** (2,461 lines) — Flask web app
- Port: 3001
- Key routes:
  - `GET /` → Dashboard with tasks, meetings, calendar
  - `GET /tasks` → Task kanban
  - `GET /crm/pipeline` → Sales pipeline
  - `GET /crm/org/<name>` → Org detail
  - `GET /crm/prospect/<offering>/<org>` → Prospect detail with AI brief

### Production / Automation

- Morning briefing scheduled via macOS launchd (5 AM daily)
- Logs: `~/Library/Logs/arec-morning-briefing.log`
- Outputs: `briefing_latest.md`, `dashboard_calendar.json`, CRM updates

---

## 2. File Map

### Core Application

| File | Lines | Description |
|------|-------|-------------|
| `app/delivery/dashboard.py` | 2,461 | Flask web app; CRM dashboard, tasks, meetings, orgs, prospects, brief gen |
| `app/main.py` | 284 | Morning briefing orchestrator; scheduled entry point |
| `app/drain_inbox.py` | 267 | AI email inbox drain; parses forwarded emails into `inbox.md` |
| `app/briefing/generator.py` | 25 | Calls Claude API with system + user prompts; returns briefing text |
| `app/briefing/prompt_builder.py` | 246 | Assembles Claude prompt from calendar, email, tasks, memory, investor intel |
| `app/auth/graph_auth.py` | 83 | MSAL device code OAuth flow for MS Graph; caches tokens to disk |
| `app/sources/ms_graph.py` | 422 | Graph API fetching; calendar events, emails, Teams chats; pagination + rate limits |
| `app/sources/crm_reader.py` | 1,629 | Low-level CRM I/O; reads/writes all markdown files in `crm/` and `memory/people/` |
| `app/sources/crm_graph_sync.py` | 262 | Auto-capture engine; matches email/calendar participants to CRM orgs |
| `app/sources/memory_reader.py` | 209 | Reads markdown files for briefing; loads tasks, memory summary, inbox |
| `app/sources/relationship_brief.py` | 963 | Aggregates KB data (people, glossary, meetings, tasks) for AI brief synthesis |

### Static Assets

| File | Description |
|------|-------------|
| `app/static/task-edit-modal.js` | Shared task edit modal with assign/priority/status UI |
| `app/static/tasks/tasks.js` | Kanban board rendering; task grouping by assignee, priority |

### Scripts (Migration / One-off)

| File | Description |
|------|-------------|
| `app/scripts/migrate_tasks_status.py` | Adds status field to tasks |
| `app/scripts/migrate_tasks_data_model.py` | Restructures TASKS.md format |
| `app/scripts/migrate_tasks_sections.py` | Reorganizes task sections |
| `app/scripts/migrate_assignee_tasks.py` | Adds assignee field to tasks |
| `app/scripts/migrate_urgency.py` | Adds urgency field |
| `app/scripts/cleanup_org_duplicates.py` | Removes duplicate org entries |
| `app/scripts/bootstrap_contacts_index.py` | Initial bootstrap of contacts index |

> All migration scripts are one-time utilities. Safe to retain but will not be run again.

### Data Layer

| File | Description |
|------|-------------|
| `crm/config.md` | Pipeline stages, org types, AREC team roster |
| `crm/prospects.md` | All prospects grouped by offering; Stage, Target, Notes, Last Touch, Brief |
| `crm/organizations.md` | All prospect orgs with Type, Aliases, Domain, Contacts, Stage, Notes |
| `crm/contacts_index.md` | Index mapping org names to `memory/people/` slugs |
| `crm/offerings.md` | Product offerings with description and terms |
| `crm/interactions.md` | Interaction history log matched to orgs |
| `crm/pending_interviews.json` | Queue of unmatched emails/participants for manual CRM assignment |
| `crm/unmatched_review.json` | Unmatched email/calendar participants to triage |
| `crm/briefs.json` | Persisted AI relationship briefs |
| `crm/prospect_notes.json` | Prospect-specific notes |
| `crm/email_log.json` | Scanned emails from Outlook Archive matched to CRM orgs |
| `crm/meeting_history.md` | Meeting attendance records keyed by org |
| `crm/ai_inbox_queue.md` | **DEAD** — Legacy file superseded by `drain_inbox.py` + `inbox.md` flow |
| `TASKS.md` | Single source of truth for all tasks |
| `inbox.md` | Voice-capture queue from iPhone Shortcuts |
| `config.yaml` | Main app configuration (Graph user email, optional overrides) |

### Memory Layer

| File | Description |
|------|-------------|
| `memory/context/me.md` | Oscar's personal context: people, companies, LPs, deals |
| `memory/context/company.md` | AREC context: team, structure, strategy, tools |
| `memory/glossary.md` | Terms, nicknames, investor universe |
| `memory/projects/arec-fund-ii.md` | Fund II strategy and closing progress |
| `memory/people/*.md` (100+ files) | One file per contact: org, role, email, relationship notes |

### Meeting Summaries

| Directory | Description |
|-----------|-------------|
| `meeting-summaries/` | Active meeting notes (last 7 days); ~30 recent files |
| `meeting-summaries/archive/` | Archived meetings (>7 days); ~18 files |

### Tests

| Path | Description |
|------|-------------|
| `app/tests/` | **DEAD** — Directory exists with `fixtures/` subdirectory; no test files present |

### Dead / Flagged Files

| File | Reason |
|------|--------|
| `crm/ai_inbox_queue.md` | Legacy; superseded by drain_inbox flow |
| `app/tests/` (directory) | No test files; dead structure |
| `app/scripts/migrate_*.py` | One-time migrations; not needed again |
| `dashboard.py:10` — `import glob as globmod` | Imported but never called |

### Duplicate / Near-Duplicate Code

- Brief synthesis logic appears 3x in `dashboard.py` (see Code Smells §4)
- Task line parsing appears in 3 locations with subtle differences (see Code Smells §4)

---

## 3. Dependencies

### `requirements.txt`

| Package | Used? | Where |
|---------|-------|-------|
| `anthropic>=0.25.0` | ✅ | `generator.py`, `dashboard.py` |
| `msal>=1.28.0` | ✅ | `graph_auth.py` |
| `requests>=2.31.0` | ✅ | `ms_graph.py` |
| `pyyaml>=6.0` | ✅ | `crm_graph_sync.py` |
| `python-dotenv>=1.0.0` | ✅ | `main.py`, `drain_inbox.py` |
| `flask>=3.0.0` | ✅ | `dashboard.py` |

All declared dependencies are actively used. No unused or missing entries found.

### Standard Library (All Used)

`os`, `sys`, `json`, `re`, `datetime`, `time`, `logging`, `hashlib`, `glob`, `argparse`

### Dead Import

- `dashboard.py:10` — `import glob as globmod` — Imported, never called.

---

## 4. Code Smells

### A. Large Functions (>100 lines)

| File | Function | Lines |
|------|----------|-------|
| `dashboard.py` | `api_export_pipeline()` | ~245 |
| `dashboard.py` | `api_calendar_refresh()` | ~122 |
| `dashboard.py` | `api_prospect_email_scan()` | ~110 |
| `dashboard.py` | `api_synthesize_brief()` | ~100 |

`api_export_pipeline()` at ~245 lines is the most problematic — deeply nested loops with multiple concerns.

### B. Hardcoded Values

| Location | Value | Severity |
|----------|-------|----------|
| `ms_graph.py:14` | `GRAPH_BASE = "https://graph.microsoft.com/v1.0"` | OK — standard constant |
| `ms_graph.py:141` | `/mailFolders/inbox/messages` | **BUG** — Fetches Inbox only; Oscar uses Archive (Inbox Zero). Briefing misses recent emails. |
| `crm_graph_sync.py:25–29` | `INTERNAL_DOMAINS` set | OK — configuration constant |
| `drain_inbox.py:225` | `ai@avilacapital.com` default | OK — has `.env` override |

### C. Copy-Pasted Logic

**Brief synthesis — 3 implementations:**
1. `dashboard.py` — `_synthesize_and_persist_brief()` (prospect brief)
2. `dashboard.py` — `api_synthesize_brief()` (similar logic, different scope)
3. `dashboard.py` — `api_synthesize_org_brief()` (org-level variant)

All three call Claude, parse JSON, persist to markdown. Bug fixes must be made in all three.

**Task line parsing — 3 implementations:**
1. `dashboard.py:_load_tasks_grouped()` — Section-based, simpler regex
2. `dashboard.py:_parse_task_line()` — Detailed field extraction
3. `memory_reader.py:load_tasks()` — Lightweight version for briefing

Subtle differences in priority/status/assignee extraction between implementations.

### D. Commented-Out Code

No significant commented-out blocks found. Codebase is clean in this regard.

### E. Missing Validation

- `crm_reader.py` write functions (`write_prospect()`, `write_organization()`) do not validate markdown structure before writing — a malformed input could corrupt CRM data.
- `contacts_index.md` is manually maintained with no automatic sync when person files are created/deleted.

---

## 5. Architecture

### Structure

```
app/
├── auth/           → MS Graph OAuth
├── briefing/       → Claude prompt assembly + API call
├── sources/        → Data fetching (Graph, CRM, Memory)
├── delivery/       → Flask web app (dashboard.py)
├── scripts/        → One-time migration utilities
└── static/         → JS for task kanban + modals

crm/                → Markdown + JSON data (prospects, orgs, interactions)
memory/             → Knowledge base (people, context, glossary)
meeting-summaries/  → Per-meeting markdown files
skills/             → Claude Code skill definitions
```

**Pattern:** Layered (auth → sources → briefing/delivery). Single source of truth for each data type. Local-first file storage (no database).

### Main Data Flows

**Morning Briefing:**
```
launchd 5AM → main.py → MS Graph (calendar + email) → build_prompt() → Claude API → briefing_latest.md
                                                      → run_auto_capture() → crm/interactions.md
```

**Task Management:**
```
iPhone Shortcuts → inbox.md → /productivity:update → TASKS.md → Flask dashboard (kanban)
```

**CRM Auto-Capture:**
```
MS Graph (email + calendar, last 24h) → match participants to orgs → crm/interactions.md
                                      → unmatched → crm/pending_interviews.json
```

**Meeting Summaries:**
```
Notion API (Teams meetings) → meeting-summaries/YYYY-MM-DD-slug.md → archive after 7 days
```

**Email Log:**
```
skills/email-scan.md → Outlook Archive + Sent (last 30 days) → domain match → crm/email_log.json
```

### External Service Dependencies

| Service | Auth | Usage |
|---------|------|-------|
| Microsoft Graph | MSAL device code OAuth; cached to `~/.arec_briefing_token_cache.json` | Calendar, email, Teams chats |
| Claude API | `ANTHROPIC_API_KEY` env var | Briefing generation, brief synthesis |
| Notion API | (via Claude Code MCP) | Meeting notes query |
| iPhone Shortcuts | HTTP POST | Voice inbox capture |

**Critical path:** MS Graph + Claude API. Loss of either blocks briefing.

---

## 6. Test Coverage

### Status: Zero tests

`app/tests/` directory exists with a `fixtures/` subdirectory but contains no test files.

### Untested Critical Paths

| Path | Risk |
|------|------|
| `_parse_task_line()` / `load_tasks()` | Complex regex; edge cases untested |
| `_resolve_participant()` | Fuzzy org name matching; no tests |
| `write_prospect()` / `write_organization()` | Markdown round-trip; corruption risk |
| `_synthesize_and_persist_brief()` | Claude API call + JSON parsing; only try/except fallback |
| `parse_forwarded_email()` in drain_inbox.py | Multiple regex patterns; no tests |
| `_get_all_pages()` in ms_graph.py | Rate-limit handling; no tests |

---

## 7. Known Issues Summary

| # | Issue | File | Severity |
|---|-------|------|----------|
| 1 | Briefing scans Inbox only — Archive not included | `ms_graph.py:141` | **High** — briefing misses recent emails (Oscar uses Archive) |
| 2 | Brief synthesis logic duplicated 3× | `dashboard.py` | Medium — maintenance burden |
| 3 | Task parsing logic duplicated 3× | `dashboard.py`, `memory_reader.py` | Medium — risk of divergence |
| 4 | No markdown validation before CRM write | `crm_reader.py` | Medium — corruption risk |
| 5 | `contacts_index.md` manually maintained | `crm/contacts_index.md` | Low — may drift from `memory/people/` |
| 6 | Dead import (`glob as globmod`) | `dashboard.py:10` | Low |
| 7 | Zero test coverage | `app/tests/` | Medium — regression risk |
| 8 | `dashboard.py` is 2,461 lines | `dashboard.py` | Low — readability/maintainability |

---

## 8. Recommended Priorities

1. **Fix email Archive gap** — `ms_graph.py` fetches Inbox only; should scan Archive (or delegate to email-scan skill)
2. **Add tests** — Start with task parsing and email matching (highest ROI)
3. **Consolidate brief synthesis** — Extract shared logic into `briefing/brief_synthesizer.py`
4. **Consolidate task parsing** — Single canonical `_parse_task_line()` used by both dashboard and memory_reader
5. **Split dashboard.py** — CRM, tasks, meetings, briefs as separate Flask blueprints
6. **Remove dead code** — `crm/ai_inbox_queue.md`, dead `glob` import, `app/tests/` skeleton
