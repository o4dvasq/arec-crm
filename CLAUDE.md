# arec-crm

CRM and fundraising platform for the AREC team. Manages investor pipeline, relationship briefs, and contact intelligence backed by markdown files. Single-user local deployment.

**Location:** `~/Dropbox/projects/arec-crm/`
**Branch:** `main`
**Sister repo:** `~/Dropbox/projects/overwatch/` (personal productivity — tasks, briefings, personal contacts)

---

## ⚠️ Architecture — READ THIS FIRST

**NO DATABASE. NO SQL. NO ORM. NO CLOUD HOSTING.**

This is a **markdown-and-JSON-file CRM** running locally on Oscar's Mac. Every spec, design, and code change must respect these hard constraints:

- **Storage:** All data lives in flat files under `crm/` — markdown (`.md`) and JSON (`.json`). There is no SQLite, Postgres, or any database.
- **Backend:** `app/sources/crm_reader.py` is the sole data access layer (70+ functions). All reads and writes go through it. Never parse data files directly from routes or scripts.
- **No ORM / No Models:** `crm_db.py`, `models.py`, `db.py`, `auto_migrate.py` do not exist. Never reference them. There are no "db sessions", no "migrations", no "ALTER TABLE".
- **Deployment:** Runs locally at `http://localhost:8000` on Oscar's Mac. Not on Azure, AWS, or any cloud. No WebJobs, no App Service. Scheduled tasks use macOS `launchd`.
- **Auth:** `login_required` in `crm_blueprint.py` is a no-op passthrough. No real authentication.

### Data Files (under `crm/`)

| File | Format | Key Fields | Notes |
|------|--------|------------|-------|
| `prospects.md` | Markdown: `## Offering` → `### OrgName` → bullet fields | Stage, Target, Assigned To, Primary Contact, Notes, Last Touch | Prospects keyed by (org, offering) — NOT integer IDs |
| `organizations.md` | Markdown: `## OrgName` → bullet fields | Type, Location, Domain, AUM, Notes | |
| `meetings.json` | JSON array of objects | org, offering, meeting_date, status, notes_raw, attendees, source | Status lifecycle: scheduled → completed → reviewed |
| `email_log.json` | JSON: `{emails: [...], lastScan: ...}` | from, fromName, orgMatch, date, subject, summary | No "direction" field — infer from `from` domain |
| `interactions.md` | Markdown: `## Date` → `### Org — Type — Offering` → bullet fields | Contact, Subject, Summary, Source | No direction field. Type = Email/Meeting/Call |
| `briefs.json` | JSON keyed by org | narrative, at_a_glance, updated | AI-synthesized relationship briefs |
| `org_notes.json` | JSON keyed by org | notes array with text, source, date | |
| `prospect_notes.json` | JSON keyed by `org|offering` | notes array | |

### Prospect Identity

Prospects are identified by the tuple `(org_name, offering_name)` — string pair, not an integer ID. URLs use `/crm/prospect/<org>/<offering>` (URL-encoded). The `load_prospects()` function returns dicts with keys like `Org`, `Offering`, `Stage`, `Target`, etc. Stage values are strings like `"5. Interested"`, `"8. Closed"`, `"0. Declined"`.

### Email Direction

`email_log.json` has no explicit direction field. Infer direction from the `from` address domain:
- **Outbound:** domain ∈ `{avilacapllc.com, arecllc.com}`
- **Inbound:** domain ∉ those AREC domains

Match emails to prospects via the `orgMatch` field (case-insensitive org name match).

### Removed Fields

`next_action` was removed from the data model. `crm_reader.py` silently rejects writes to it. A few vestigial references remain in `crm_blueprint.py` (reject guard + Excel export column) — these are tracked for cleanup.

---

## Run Commands

```bash
echo "DEV_USER=oscar" > app/.env                       # First time only
python3 app/delivery/dashboard.py                     # Web dashboard — http://localhost:8000
python3 -m pytest app/tests/ -v                       # 84 tests
```

## Key Files

| File | Purpose |
|------|---------|
| `app/sources/crm_reader.py` | Markdown backend — single source of truth (70+ functions, includes org_notes + brief attribution) |
| `app/delivery/dashboard.py` | Flask app factory (load env → register blueprints, meeting file routes) |
| `app/delivery/crm_blueprint.py` | CRM routes + relationship brief synthesis + flat task CRUD endpoints |
| `app/auth/decorators.py` | `require_api_key_or_login` — no-op passthrough for local dev |
| `app/tests/conftest.py` | pytest path setup (no DB fixtures) |
| `app/sources/email_matching.py` | Org/participant fuzzy matching utilities |
| `app/drain_inbox.py` | Shared mailbox drain — writes to `crm/ai_inbox_queue.md` with Priority + ForwardedBy |
| `app/auth/graph_auth.py` | Graph token auth — used by email-scan Claude Desktop skill only |
| `app/sources/ms_graph.py` | MS Graph API calls — used by email-scan Claude Desktop skill only |

## Non-Obvious Conventions

- **Markdown-only**: All production code reads/writes through `crm_reader.py`. No database.
- **No auth**: `require_api_key_or_login` is a no-op passthrough. `g.user` is set by `before_request` via `DEV_USER` env var.
- **Currency as floats in markdown**: `_format_currency()` / `_parse_currency()` in `crm_reader.py`.
- **Brief synthesis JSON contract**: Claude must return `{narrative, at_a_glance}`. `brief_synthesizer.py` handles parse fallbacks.
- **Graph-dependent routes return 501**: Email scan and auto-capture routes return 501 with a message pointing to the Claude Desktop skill.
- **Update orchestrator (`main.py`) degrades gracefully**: If Graph dependencies are unavailable, it skips calendar/email fetch and proceeds with local data only. NOTE: "Morning briefing" refers ONLY to a future scheduled report delivery feature (see `docs/FUTURE_FEATURES.md`) — it is NOT the interactive update flow.
- **Meetings are organization-primary**: `crm/meetings.json` is the unified store. Meetings are associated with an Organization (optional), with optional Offering link. Meetings can exist with org+offering, org only, or neither. Offering requires org (validated). Two-tier dedup (graph_event_id exact + fuzzy org+date ±1 day). Status lifecycle: scheduled → completed → reviewed. Full CRUD via `/crm/meetings` UI.
- **Calendar users config**: `crm/calendar_users.json` lists emails for Graph calendar scanning. Update when team members change.

## Active Constraints

- **No database imports in production code**: `crm_db.py`, `models.py`, `db.py`, `auto_migrate.py` do not exist on this branch.
- **Organization field is always a dropdown**: The Organization field on People Detail edit uses `<select>` from `/crm/api/orgs`. Never free-text.
- **Task API routes use `@require_api_key_or_login`**: Decorator is a passthrough but must stay on all 5 `/crm/api/tasks*` routes so the pattern is preserved for future auth.
- **Keep both `requirements.txt` files in sync**: `app/requirements.txt` and root `requirements.txt` must match. Update both when adding a dependency.
- **`inbox.md` is voice-capture-only**: `drain_inbox.py` and all code writes shared mailbox output to `crm/ai_inbox_queue.md`. Never write to `inbox.md` from code — it is the Siri Shortcut target only.

## Spec Lifecycle

Specs live in `docs/specs/` and follow this flow:

```
docs/specs/              ← TO DO: specs ready for implementation
docs/specs/future/       ← BACKLOG: deferred features, not ready yet
docs/specs/implemented/  ← DONE: specs that have been fully implemented
```

**After completing a spec:** Move the spec file from `docs/specs/` to `docs/specs/implemented/`. This keeps the specs directory clean — anything in `docs/specs/` is work that hasn't been done yet. Do not delete specs after implementation; the implemented folder serves as a history of what's in the codebase.
