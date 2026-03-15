# Phase I1 Prerequisites — Local CRM Audit

**Date:** March 8, 2026
**Purpose:** Everything Claude Code needs to build the Phase I1 spec for the AREC Intelligence Platform (Azure migration).

---

## 1. Directory Layout

```
ClaudeProductivity/
├── CLAUDE.md                          # Project instructions / run commands
├── TASKS.md                           # Task tracking (stays local, not migrated)
├── inbox.md                           # Ephemeral inbox (cleared each update)
├── config.yaml
├── app/
│   ├── .env                           # Environment variables (secrets)
│   ├── .env.example
│   ├── requirements.txt
│   ├── main.py                        # Morning briefing orchestrator
│   ├── drain_inbox.py                 # Drain crm@ shared mailbox
│   ├── __init__.py
│   ├── auth/
│   │   ├── __init__.py
│   │   └── graph_auth.py              # MSAL auth for Microsoft Graph
│   ├── briefing/
│   │   ├── __init__.py
│   │   ├── brief_synthesizer.py       # Claude API brief synthesis
│   │   ├── generator.py               # Briefing generation
│   │   └── prompt_builder.py          # Prompt construction
│   ├── delivery/
│   │   ├── __init__.py
│   │   ├── dashboard.py               # Flask app entry point (port 3001)
│   │   ├── crm_blueprint.py           # /crm routes (pipeline, orgs, prospects)
│   │   └── tasks_blueprint.py         # /tasks routes
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── crm_reader.py              # Central CRM parser (58KB, ~1620 lines)
│   │   ├── crm_graph_sync.py          # Graph sync utilities
│   │   ├── memory_reader.py           # Memory/people file reader
│   │   ├── ms_graph.py                # Microsoft Graph API client
│   │   └── relationship_brief.py      # Brief data collection + prompts
│   ├── templates/
│   │   ├── _nav.html                  # Shared navigation partial
│   │   ├── dashboard.html             # Main dashboard (tasks, meetings, calendar)
│   │   ├── crm_pipeline.html          # Pipeline table (73KB — the big one)
│   │   ├── crm_org_detail.html        # Organization detail page
│   │   ├── crm_orgs.html              # Organization list
│   │   ├── crm_prospect_detail.html   # Prospect detail with briefs
│   │   ├── crm_prospect_edit.html     # Prospect edit form
│   │   ├── crm_people.html            # People list
│   │   ├── crm_person_detail.html     # Person detail
│   │   ├── meeting_detail.html        # Meeting summary viewer/editor
│   │   └── tasks/
│   │       └── tasks.html             # Task management page
│   ├── static/
│   │   ├── crm.css                    # CRM styles
│   │   ├── task-edit-modal.css        # Task edit modal styles
│   │   ├── task-edit-modal.js         # Task edit modal logic
│   │   └── tasks/
│   │       ├── tasks.css              # Task page styles
│   │       └── tasks.js               # Task page logic
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_brief_synthesizer.py
│   │   ├── test_email_matching.py
│   │   └── test_task_parsing.py
│   └── scripts/
│       ├── bootstrap_contacts_index.py
│       ├── cleanup_org_duplicates.py
│       └── migrate_*.py               # Various migration scripts
├── crm/
│   ├── prospects.md                   # Live prospect records
│   ├── organizations.md               # Organization records
│   ├── contacts_index.md              # Contact → org mapping
│   ├── config.md                      # Pipeline stages, org types, etc.
│   ├── offerings.md                   # Fund offerings
│   ├── interactions.md                # Interaction log
│   ├── meeting_history.md             # Meeting history per org
│   ├── briefs.json                    # Cached relationship briefs
│   ├── prospect_notes.json            # Prospect notes (timestamped)
│   ├── email_log.json                 # Email scan log
│   ├── pending_interviews.json        # Pending interviews queue
│   └── unmatched_review.json          # Unmatched email senders
├── memory/                            # People KB, terms, companies (stays local)
├── meeting-summaries/                 # YYYY-MM-DD-slug.md files
├── skills/                            # Instructional skill docs (not code)
├── scripts/
│   └── refresh_interested_briefs.py
└── docs/
    ├── ARCHITECTURE.md
    ├── PROJECT_STATE.md
    └── specs/                         # Historical phase specs (archive)
```

---

## 2. crm_reader.py — Public Function Signatures

All downstream consumers import from `app/sources/crm_reader.py`. Phase I1's `crm_db.py` must be a **drop-in replacement** with these same signatures.

### Config & Offerings
```python
def load_crm_config() -> dict
def get_team_member_email(name: str) -> str
def load_offerings() -> list[dict]
def get_offering(name: str) -> dict | None
```

### Organizations
```python
def load_organizations() -> list[dict]
def get_organization(name: str) -> dict | None
def write_organization(name: str, data: dict) -> None
def delete_organization(name: str) -> None
```

### Contacts / People
```python
def load_contacts_index() -> dict
def load_person(slug: str) -> dict | None
def get_contacts_for_org(org_name: str) -> list[dict]
def find_person_by_email(email: str) -> dict | None
def create_person_file(name: str, org: str, email: str, role: str, person_type: str) -> str
def load_all_persons() -> list[dict]
def enrich_person_email(slug: str, email: str) -> None
def add_contact_to_index(org: str, slug: str) -> None
def update_contact_fields(org: str, name: str, fields: dict) -> bool
```

### Prospects
```python
def load_prospects(offering: str = None) -> list[dict]
def get_prospect(org: str, offering: str) -> dict | None
def get_prospects_for_org(org: str) -> list[dict]
def write_prospect(org: str, offering: str, data: dict) -> None
def delete_prospect(org: str, offering: str) -> None
def update_prospect_field(org: str, offering: str, field: str, value: str) -> None
def get_prospect_full(org: str, offering: str) -> dict | None
def resolve_primary_contact(org: str, contact_name: str) -> dict | None
```

### Fund Summaries
```python
def get_fund_summary(offering: str) -> dict
def get_fund_summary_all() -> list[dict]
def get_pipeline_summary(offering: str) -> dict
```

### Interactions
```python
def load_interactions(org: str = None, offering: str = None, limit: int = None) -> list[dict]
def append_interaction(entry: dict) -> None
```

### Prospect Tasks
```python
def load_tasks_by_org() -> dict[str, list[dict]]
def get_tasks_for_prospect(org_name: str) -> list[dict]
def get_all_prospect_tasks() -> list[dict]
def add_prospect_task(org_name: str, text: str, owner: str, ...) -> ...
def complete_prospect_task(org_name: str, task_text: str) -> bool
```

### Meeting History
```python
def load_meeting_history(org: str) -> list[dict]
def add_meeting_entry(org: str, date: str, title: str, attendees: str, source: str, notion_url: str = '') -> None
```

### Email Log
```python
def load_email_log() -> dict
def save_email_log(data: dict) -> None
def find_email_by_message_id(message_id: str) -> dict | None
def get_emails_for_org(org_name: str) -> list[dict]
def add_emails_to_log(emails: list[dict]) -> int
```

### Domain Matching
```python
def get_org_domains(prospect_only: bool = False) -> dict
def get_org_by_domain(domain: str) -> str | None
```

### Unmatched / Pending
```python
def load_pending_interviews() -> list[dict]
def add_pending_interview(entry: dict) -> None
def remove_pending_interview(org: str) -> None
def load_unmatched() -> list[dict]
def add_unmatched(item: dict) -> None
def remove_unmatched(email: str) -> None
def purge_old_unmatched(days: int = 14) -> None
```

### Briefs & Notes
```python
def save_brief(brief_type: str, key: str, narrative: str, content_hash: str, ...) -> ...
def load_saved_brief(brief_type: str, key: str) -> dict | None
def load_all_briefs() -> dict
def load_prospect_notes(org: str, offering: str) -> list
def save_prospect_note(org: str, offering: str, author: str, text: str) -> dict
```

### Currency Helpers (public)
```python
def _parse_currency(s: str) -> float   # Imported by crm_blueprint.py
def _format_currency(n: float) -> str
```

---

## 3. Flask Routes

### CRM Blueprint (`/crm` prefix) — crm_blueprint.py

#### Page Routes
| Route | Method | Purpose |
|-------|--------|---------|
| `/crm/` and `/crm` | GET | Pipeline table page |
| `/crm/people` | GET | People list page |
| `/crm/people/<slug>` | GET | Person detail page |
| `/crm/person/<slug>` | GET | Person detail (alt URL) |
| `/crm/orgs` | GET | Organization list page |
| `/crm/org/<name>` | GET | Organization detail page |
| `/crm/org/<name>/edit` | GET | Organization edit page |
| `/crm/prospect/<offering>/<org>` | GET | Prospect redirect/summary |
| `/crm/prospect/<offering>/<org>/detail` | GET | Prospect detail page |

#### API Routes
| Route | Method | Purpose | Key crm_reader calls |
|-------|--------|---------|---------------------|
| `/crm/api/offerings` | GET | List offerings | `load_offerings` |
| `/crm/api/prospects` | GET | List prospects (filterable) | `load_prospects`, `load_crm_config` |
| `/crm/api/fund-summary` | GET | Fund commitment summary | `get_fund_summary`, `get_fund_summary_all` |
| `/crm/api/prospect/field` | PATCH | Inline field edit | `update_prospect_field` |
| `/crm/api/prospect/save` | POST | Full prospect save | `write_prospect` |
| `/crm/api/prospect` | POST | Create prospect | `write_prospect` |
| `/crm/api/prospect` | DELETE | Delete prospect | `delete_prospect` |
| `/crm/api/org/<name>` | GET | Org data + contacts + prospects | `get_organization`, `get_contacts_for_org`, `get_prospects_for_org` |
| `/crm/api/org/<name>` | PATCH | Update org fields | `write_organization` |
| `/crm/api/org` | POST | Create organization | `write_organization` |
| `/crm/api/org/<name>/meetings` | GET | Meeting history for org | `load_meeting_history` |
| `/crm/api/org/<name>/meetings` | POST | Add meeting entry | `add_meeting_entry` |
| `/crm/api/orgs` | GET | All organizations | `load_organizations` |
| `/crm/api/contact` | POST | Create contact | `create_person_file`, `add_contact_to_index` |
| `/crm/api/contact/<org_and_name>` | PATCH | Update contact fields | `update_contact_fields` |
| `/crm/api/kb-people` | GET | Knowledge base people | `load_all_persons` |
| `/crm/api/person-data` | GET | Person data for brief | `load_person` |
| `/crm/api/person-update` | POST | Update person fields | various |
| `/crm/people/api/<slug>/contact` | PATCH | Update person contact info | `update_contact_fields` |
| `/crm/api/synthesize-brief` | POST | Claude API brief synthesis | `collect_relationship_data`, Claude API |
| `/crm/api/synthesize-org-brief` | POST | Org-level brief synthesis | various, Claude API |
| `/crm/api/synthesize-person-brief` | POST | Person brief synthesis | various, Claude API |
| `/crm/api/prospect/<offering>/<org>/brief` | GET/POST | Get/save prospect brief | `load_saved_brief`, `save_brief` |
| `/crm/api/prospect/<offering>/<org>/add-note` | POST | Add prospect note | `save_prospect_note` |
| `/crm/api/prospect/<offering>/<org>/email-scan` | POST | Scan emails for prospect | `get_emails_for_org`, Claude API |
| `/crm/api/emails/<org>` | GET | Emails for org | `get_emails_for_org` |
| `/crm/api/email/<message_id>` | GET | Single email detail | `find_email_by_message_id` |
| `/crm/api/tasks` | GET | Prospect tasks | `get_all_prospect_tasks` |
| `/crm/api/tasks` | POST | Add prospect task | `add_prospect_task` |
| `/crm/api/tasks/complete` | PATCH | Complete task | `complete_prospect_task` |
| `/crm/api/unmatched` | GET | Unmatched emails | `load_unmatched` |
| `/crm/api/unmatched/resolve` | POST | Resolve unmatched | `remove_unmatched`, `create_person_file` |
| `/crm/api/unmatched/<email>` | DELETE | Delete unmatched | `remove_unmatched` |
| `/crm/api/auto-capture` | POST | Auto-capture email to CRM | various |
| `/crm/api/export` | GET | Export pipeline as XLSX | `load_prospects` |
| `/crm/api/followup` | POST | Log follow-up action | `append_interaction` |

### Dashboard Routes — dashboard.py
| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Main dashboard (tasks, meetings, calendar) |
| `/meetings/<filename>` | GET | Meeting detail viewer |
| `/meetings/<filename>/save` | POST | Save edited meeting |
| `/api/calendar/refresh` | POST | Refresh calendar from Graph |
| `/api/task/complete` | POST | Mark task complete |
| `/api/task/add` | POST | Add task |
| `/api/task/status` | PATCH | Update task status |

---

## 4. Templates & Static Files

### CRM-Specific Templates
| Template | Size | Purpose |
|----------|------|---------|
| `crm_pipeline.html` | 73KB | Pipeline table — sorts, filters, inline editing, offering tabs |
| `crm_org_detail.html` | 39KB | Org detail — contacts, prospects, meetings, briefs |
| `crm_prospect_detail.html` | 50KB | Prospect detail — brief, notes, emails, tasks |
| `crm_prospect_edit.html` | 18KB | Prospect create/edit form |
| `crm_person_detail.html` | 41KB | Person detail — brief, contact info |
| `crm_orgs.html` | 11KB | Organization list |
| `crm_people.html` | 4KB | People list |

### Non-CRM Templates
| Template | Purpose |
|----------|---------|
| `dashboard.html` | Main dashboard (tasks, meetings, calendar) — NOT migrated |
| `meeting_detail.html` | Meeting summary viewer — NOT migrated |
| `tasks/tasks.html` | Task management — NOT migrated |
| `_nav.html` | Shared nav partial — MIGRATED (updated for SSO) |

### Static Files
| File | Purpose |
|------|---------|
| `crm.css` | All CRM styling — MIGRATED |
| `task-edit-modal.css` | Task modal styles — shared |
| `task-edit-modal.js` | Task modal logic — shared |
| `tasks/tasks.css` | Task page styles — NOT migrated |
| `tasks/tasks.js` | Task page logic — NOT migrated |

---

## 5. Config / Environment

### Environment Variables (`app/.env`)
```
ANTHROPIC_API_KEY=sk-ant-api03-...    # Claude API key
AZURE_CLIENT_ID=d58c6152-...         # Existing local CRM app registration
AZURE_TENANT_ID=ebd42ab2-...         # Oscar's personal tenant (NOT the Avila Capital LLC tenant)
MS_USER_ID=422b3092-...              # Oscar's user object ID
AI_INBOX_EMAIL=ai@avilacapital.com   # AI inbox email address
```

### Important Tenant Note
The existing `.env` uses tenant `ebd42ab2-7f1c-4d40-8b44-f5ecc51d2659` (Oscar's personal). The new Azure subscription is under Avila Capital LLC tenant `064d6342-5dc5-424e-802f-53ff17bc02be`. Phase I1 needs a NEW app registration in the Avila Capital LLC tenant.

### Runtime Config
- Entry point: `python app/delivery/dashboard.py`
- Port: `3001` (configurable via `DASHBOARD_PORT` env var)
- Debug: controlled by `FLASK_DEBUG` env var (defaults to true)
- Uses `python-dotenv` to load `app/.env`

---

## 6. Markdown File Samples

### prospects.md
```markdown
# Prospects

## AREC Debt Fund II

### Robert Young
- **Stage:** 8. Closed
- **Target:** $1,000,000
- **Primary Contact:** Robert Young
- **Closing:** 1st
- **Urgency:**
- **Assigned To:** Oscar Vasquez
- **Notes:**
- **Last Touch:** 2026-02-28

### Toll Brothers
- **Stage:** 8. Closed
- **Target:** $5,000,000
- **Primary Contact:** Marty Connor (formerly Toll); Ben Jogodnik; Ryan Mckenna
- **Closing:** 2nd
...
```
Structure: `# Prospects` → `## {Offering Name}` → `### {Org Name}` → bullet fields

### organizations.md
```markdown
# Organizations

## 1900 Wealth
- **Type:** HNWI / FO
- **Notes:**

## AEW
- **Type:** Asset Manager
- **Notes:**
...
```
Structure: `# Organizations` → `## {Org Name}` → bullet fields (Type, Notes)

### config.md
```markdown
# CRM Configuration

## Pipeline Stages
0. Declined
1. Prospect
2. Cold
3. Outreach
4. Engaged
5. Interested
6. Verbal
7. Legal / DD
8. Closed

## Terminal Stages
- 0. Declined

## Organization Types
- INSTITUTIONAL
- HNWI / FO
- BUILDER
```

### offerings.md
```markdown
# Offerings

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

### TASKS.md (stays local — format reference only)
```markdown
# Tasks

## Fundraising - Me
- [ ] **[Hi]** Meet on 3/10 (UTIMCO - Hedge Fund) — assigned:Tony Avila
- [ ] **[Med]** F/U week of 3/16 (Mass Mutual Life Insurance Co.) — assigned:Zach Reisner
- [x] **[Hi]** Schedule call with Partha [STATUS:complete] — assigned:Oscar Vasquez — completed 2026-03-06
```
Format: `- [ ] **[Priority]** Task text (Org Name) — assigned:Name — completed YYYY-MM-DD`

---

## 7. Entra ID & Deployment Decisions

| Question | Answer |
|----------|--------|
| App registered in Entra ID? | **No, not yet.** Need new registration in Avila Capital LLC tenant (`064d6342-5dc5-424e-802f-53ff17bc02be`) |
| Public or restricted access? | **Public internet + Entra ID SSO.** Team members access from anywhere. |
| Custom domain? | **Default Azure URL for now** (`arec-crm.azurewebsites.net` or similar). Custom domain later. |
| Azure subscription? | Created under Avila Capital LLC tenant. No resource group yet. |
| Azure CLI auth? | Oscar logged in under tenant `ebd42ab2-...` (personal). Will need to switch to `064d6342-...` for deployment. |

---

## 8. Migration Scope Summary

### What Gets Migrated to Postgres
| Source File | Target Table(s) |
|-------------|-----------------|
| `crm/prospects.md` | `prospects`, `pipeline_stages` |
| `crm/organizations.md` | `organizations` |
| `crm/contacts_index.md` + `memory/people/*.md` | `contacts` |
| `crm/offerings.md` | `offerings` |
| `crm/interactions.md` | `interactions` |
| `crm/config.md` | `pipeline_stages` (enums) |
| `crm/email_log.json` | `email_scan_log` |
| `crm/briefs.json` | (Phase I3 — intelligence_notes) |
| `crm/prospect_notes.json` | (Phase I3 — intelligence_notes) |
| `crm/meeting_history.md` | `interactions` |

### What Stays Local
| Item | Reason |
|------|--------|
| `TASKS.md` | Stays in Dropbox, not migrated |
| `memory/` directory | Local KB for Cowork |
| `meeting-summaries/` | Local Notion workflow |
| `main.py` (briefing) | Stays local, will read from Azure API later |
| `dashboard.html` | Non-CRM dashboard, not migrated |
| `skills/` | Instructional docs for Cowork |

### What Gets Replaced
| Local | Azure |
|-------|-------|
| `crm_reader.py` | `crm_db.py` (SQLAlchemy, same function signatures) |
| File-based markdown parsing | PostgreSQL queries |
| No auth | Entra ID SSO (MSAL) |
| `localhost:3001` | Azure App Service |

---

## 9. Live Data — Actual Enum Values

The architecture doc defines clean enums, but the live markdown data uses a wider set of values. The migration script and Postgres schema **must accommodate these**, not the architecture doc's idealized enums.

### Organization Types (19 distinct values in organizations.md)
```
Asset Manager
Bank
Broker/Advisor
BUILDER
Corporate Pension
Endowment
Family Office
Fund of Funds / Advisor
HNWI / FO
HNWI/FO                          ← duplicate of above (missing space)
Insurance
INSTITUTIONAL
INTRODUCER
Investment Consultant
Multi-Family Office / RIA
Private Credit
Public Pension
Public Pension / Endowment
Sovereign Wealth Fund
Sovereign Wealth Fund (Australia)
```
**DECIDED:** Use `VARCHAR(100)`, not ENUM. Migrate all 19 types as-is. Normalize `HNWI/FO` → `HNWI / FO` (add space).

### Pipeline Stages (actual vs. config.md)
```
config.md says:              prospects.md actually uses:
─────────────                ────────────────────────────
0. Declined                  0. Declined
1. Prospect                  1. Prospect
2. Cold           ←          2. Qualified          ← DIFFERENT
3. Outreach                  3. Outreach
                             3. Presentation       ← EXTRA (same number!)
4. Engaged                   4. Engaged
5. Interested                5. Interested
6. Verbal                    6. Verbal
7. Legal / DD                7. Legal / DD
8. Closed                    8. Closed
```
**DECIDED:** "2. Cold" is canonical — remap all "2. Qualified" → "2. Cold". Delete "3. Presentation" — remap to "3. Outreach". Canonical stage list:
```
0. Declined  |  1. Prospect  |  2. Cold  |  3. Outreach  |  4. Engaged
5. Interested  |  6. Verbal  |  7. Legal / DD  |  8. Closed
```

### Closing Values
```
1st, 2nd, Final
```
Matches the architecture enum. No issues.

### Urgency Values
```
High, Med, Low
```
Architecture says `'High', 'Med', 'Low'`. Matches.

### Assigned To — Multi-Value Pattern
```
Oscar Vasquez                     ← single
Tony Avila; Oscar Vasquez         ← semicolon-separated multi
Ian Morgan; Zach Reisner; Tony Avila  ← three assignees
```
**DECIDED:** Single owner. Keep `assigned_to INTEGER REFERENCES users(id)`. Migration picks the **first name** from semicolon-separated values; others are dropped.

---

## 10. Live Data — Record Counts

| Entity | Count | Notes |
|--------|-------|-------|
| Organizations | 129 | In `organizations.md` |
| Prospects | 161 | Across 3 offerings |
| Offerings | 3 | AREC Debt Fund II, Mountain House Refi, JVs and Finance |
| Contacts (index entries) | ~18 orgs with indexed contacts | Many orgs have no indexed contacts |
| People files (`memory/people/`) | varies | Richer than contacts_index — includes meeting notes, bio |
| Interactions | ~15+ entries | Sparse — mostly auto-graph captures from March 2026 |
| Email log entries | varies | JSON dict with `{version, lastScan, emails}` |
| Prospect notes | 0 | `prospect_notes.json` is empty `{}` |
| Meeting history | 0 entries | `meeting_history.md` has header only |
| Briefs (cached) | varies | `briefs.json` — relationship brief cache |

**Migration volume is small** — this is a <200 record migration. The complexity is in the format parsing, not scale.

---

## 11. Data Format Samples — Detailed

### contacts_index.md
```markdown
# Contacts Index

- Berkshire Hathaway: partha-manchiraju, chuck-chang
- Brightside Capital Partners: ashton-newhall
- Crestline Investors: john-cochran, rahul-vaid, brenda-diaz, michael-benard, thomas-aniol, jonathan-morgan
```
Format: `- {Org Name}: {slug-1}, {slug-2}, ...`
Slugs correspond to files in `memory/people/{slug}.md`.

### interactions.md
```markdown
# Interaction Log

## 2026-03-02

### Tony Avila — Email — AREC Debt Fund II
- **Contact:**
- **Subject:** AREC Debt Fund II Marketing A List - MASTER as of Feb 27.xlsx
- **Summary:** Auto-captured: Tony Avila → AREC Debt Fund II Marketing A List - MASTER as of Feb 27.xlsx
- **Source:** auto-graph
```
Structure: `# Interaction Log` → `## {Date}` → `### {Team Member} — {Type} — {Offering}` → bullet fields.
Note: `Contact` is often empty for auto-graph entries.

### email_log.json
```json
{
  "version": 1,
  "lastScan": "2026-03-07T...",
  "emails": {
    "{message_id}": {
      "from": "sender@example.com",
      "to": ["recipient@avilacapllc.com"],
      "subject": "Re: Fund II discussion",
      "date": "2026-03-05",
      "org": "Merseyside Pension Fund",
      "matched": true,
      "snippet": "..."
    }
  }
}
```

### meeting_history.md
```markdown
# Meeting History
```
Currently empty (header only). Format when populated would follow interaction patterns.

---

## 12. Key Architecture Notes for Claude Code

1. **`crm_reader.py` is 58KB / ~1620 lines.** The replacement `crm_db.py` must match every public function signature so `crm_blueprint.py` imports don't change.

2. **Currency is stored as display strings in markdown** (`$50M`, `$1,000,000`). Migration script must parse these to BIGINT cents for Postgres. Helper `_parse_currency()` already exists.

3. **Prospects are keyed by (org_name, offering_name)** in the markdown. The Postgres schema uses `(organization_id, offering_id, disambiguator)` unique constraint.

4. **Organization types: VARCHAR(100), not ENUM.** 19 distinct types in live data. Normalize `HNWI/FO` → `HNWI / FO`. See Section 9.

5. **Pipeline stages: canonical list is 9 stages (0–8).** Remap "2. Qualified" → "2. Cold", delete "3. Presentation" → "3. Outreach". See Section 9.

6. **Assigned To: single owner.** Migration picks first name from semicolon-separated values. See Section 9.

7. **crm_blueprint.py imports ~40 functions from crm_reader.py** (see the import block at the top). This is the exact contract `crm_db.py` must satisfy.

8. **Templates are vanilla HTML/CSS/JS** (no React, no build step). They make fetch() calls to the `/crm/api/*` endpoints. The templates port directly — only the backend data layer changes.

9. **Inline editing** uses PATCH to `/crm/api/prospect/field` with `{org, offering, field, value}`. This pattern must be preserved.

10. **Brief synthesis** calls Claude API directly from `crm_blueprint.py`. In Azure, the `ANTHROPIC_API_KEY` moves to Key Vault.

11. **The existing app has 52 tests** across 3 files. These test the markdown parsing and briefing logic — they'll need Azure equivalents.

12. **Parallel pilot**: Both local and Azure systems run simultaneously. No bridge needed. Oscar cuts over when confident.

---

## 13. Decisions — Resolved (March 9, 2026)

| # | Decision | Resolution | Migration Action |
|---|----------|------------|-----------------|
| 1 | Org type storage | **VARCHAR(100)** — no enum | Schema uses `type VARCHAR(100) NOT NULL`. Migrate all 19 types as-is. Normalize `HNWI/FO` → `HNWI / FO` (add space). |
| 2 | Multi-assignee handling | **Single owner per prospect** | Schema keeps `assigned_to INTEGER REFERENCES users(id)`. Migration picks **first name** from semicolon-separated values. Others are dropped. |
| 3 | Stage "2. Cold" vs "2. Qualified" | **"2. Cold" is canonical** | Migration remaps all `2. Qualified` → `2. Cold`. Fix in `prospects.md` too. |
| 4 | Stage "3. Presentation" | **Delete — migrate to "3. Outreach"** | Migration remaps all `3. Presentation` → `3. Outreach`. |
| 5 | People files → contacts | **Keep rich context in `memory/`** — contacts table gets basics only | Migration pulls name, org, email, title from `contacts_index.md` + people files into `contacts` table. Full bios/meeting notes stay in `memory/people/*.md` (local Cowork KB, not migrated). Enrich `memory/people/*.md` files with org name and email from contacts_index if not already present. |
