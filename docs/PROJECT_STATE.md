# Project State

> **Overwrite this file completely at the end of every Claude Code session.**
> Capture what was done, what's in progress, and what's next.

---

## Last Updated
2026-03-16 — Primary Contact auto-fill + People Detail inline field editing implemented.

**Active branch:** `main`

---

## What's Built and Working

### Markdown Backend
- `app/sources/crm_reader.py` — Single source of truth for all CRM data. ~1800 lines, 60+ functions. Reads/writes markdown and JSON files directly. All production code imports from here.
- `app/sources/email_matching.py` — Extracted from deleted `crm_graph_sync.py`. Pure utility: `_fuzzy_match_org`, `_is_internal`, `_resolve_participant`. No Graph dependency.

### Web Dashboard (Flask — local dev, port 8000)
- `app/delivery/dashboard.py` — Flask app factory. No DB init. Loads env → registers blueprints → serves. `g.user` set from `DEV_USER` env var.
- `app/delivery/crm_blueprint.py` — All CRM routes backed by `crm_reader.py`. `prospect_detail` route injects `config['current_user']` for the notes form. Graph-dependent routes return 501.
- `app/delivery/tasks_blueprint.py` — Tasks page. Markdown-backed task CRUD.
- `app/auth/decorators.py` — `require_api_key_or_login` is a no-op passthrough for local dev.
- Dark theme throughout. Pipeline, prospect detail, org detail, person detail, tasks pages all functional.
- Brief synthesis via Claude API (`brief_synthesizer.py`).

### Pipeline Page (`crm_pipeline.html`)
- Tasks column shows owner initials in blue before task text (e.g., `(TA) Schedule meeting...`).
- Clicking task text opens the task-edit modal; clicking elsewhere on the row navigates to prospect detail.
- At a Glance column: `#94a3b8` color, italic, no lightning bolt emoji.

### Prospect Detail (`crm_prospect_detail.html`)
- Quick Actions card completely removed.
- Relationship Brief loads from disk on page load — no spinner. JS renders saved brief or "Generate Brief" button.
- Notes Log: no author input field; author auto-set from `CURRENT_USER` JS constant (injected from `DEV_USER`).

### Org Detail (`crm_org_detail.html`)
- Notes section completely removed (HTML + JS).
- Section order: Heading → Summary Card (Type + Domain) → Contacts → Meeting History → Brief → Prospects.

### Person Detail (`crm_person_detail.html`)
- Person Brief section completely removed (CSS + HTML + all brief JS functions).
- Shows: Contact Info card + Interaction History + Meeting Summaries + Email History.
- **Title, Email, Phone always rendered** — shows `--` (muted italic) when empty. Click any field to inline-edit; blur/Enter saves via PATCH, Escape cancels and reverts.
- Contact Info card is always visible (was previously hidden if all fields empty).

### Tasks Board (`app/static/tasks/`)
- Owner-grouped Kanban (single-column, max-width 800px). Oscar first, then others alphabetically.
- Each card: priority badge (Hi/Med/Lo, color-coded), task text, org link, section label.
- Add form per owner group with section dropdown.
- Done footer aggregates all completed tasks at the bottom.

### Task API (Overwatch-compatible)
- `GET /crm/api/tasks/dashboard` — All open tasks, enriched.
- `GET /crm/api/tasks?org=X` — Tasks for specific org.
- `POST /crm/api/tasks` — Create task (markdown-backed, returns synthetic task object).

### Contact Profiles
- `contacts/{name}.md` — 213 contact profile files (formerly `memory/people/`).

### Test Suite
- `app/tests/test_brief_synthesizer.py`, `test_email_matching.py`, `test_task_parsing.py`
- **69 tests passing**. No DB fixtures. No DATABASE_URL required.

### Cowork Skills (Claude Desktop via MCP)
- `~/.skills/skills/crm-update/SKILL.md` — **CRM intelligence update cycle** (8 steps: Overwatch queue, 4-pass email scan, calendar, meeting summaries, enrichment, stale org flagging). Main interactive workflow for keeping the CRM current.
- `~/.skills/skills/meeting-debrief/SKILL.md` — Post-meeting debrief via Notion MCP.
- `~/.skills/skills/productivity-update/SKILL.md` — Overwatch daily briefing cycle.
- `app/auth/graph_auth.py`, `app/sources/ms_graph.py` — preserved for skill use

### Queue + Email Infrastructure
- `crm/ai_inbox_queue.md` — Shared queue between Overwatch and arec-crm. Overwatch writes `pending` entries; `/crm-update` processes them.
- `crm/email_log.json` — Email scan audit trail. Dedup by `internetMessageId`. `lastScan` as of 2026-03-11.

### Primary Contact Auto-Fill
- `scripts/batch_primary_contact.py` — One-time batch script. Ran 2026-03-16; filled 1 prospect (Teachers Retirement System of Texas, single-contact). Idempotent; safe to re-run.
- `_auto_set_primary_contact_for_org()` in `crm_reader.py` — Going-forward rule: when a contact is added to an org via `add_contact_to_index()`, auto-sets Primary Contact on all of that org's prospects where none is set.

### Sister Repo
- `~/Dropbox/projects/overwatch/` — Personal productivity system (tasks, briefing, personal contacts). Separate repo, separate Flask app on port 3002.

---

## What Was Just Completed

**SPEC_primary-contact-autofill-people-detail.md (2026-03-16)**

- **People Detail inline edit** — Title, Email, Phone always shown; `--` in muted italic when empty. Click to edit inline; blur/Enter saves via PATCH to `/crm/people/api/<slug>/contact`; Escape reverts.
- **Contact Info card always visible** — Removed the `contactRows.length === 0` guard that hid the card when all fields were empty. Card now always shows.
- **Going-forward auto-set** — `add_contact_to_index()` now calls `_auto_set_primary_contact_for_org()` after writing the index; auto-fills Primary Contact on prospects with no value set.
- **Batch script** — `scripts/batch_primary_contact.py` with `--dry-run` support. Three-tier heuristic: single contact → interaction history → first in index (flagged for review). Updated 1 prospect; 130 already had Primary Contact.

---

## Known Issues

- **`/api/task/complete` and `/api/tasks/prospect/<id>/complete` return 501** — ID-based task completion doesn't exist in the markdown layer.
- **Personal section in arec-crm TASKS.md** — Still present; Overwatch is now the confirmed home for personal tasks. Clean up when convenient.

---

## Next Up

1. Run `/crm-update` to validate the skill end-to-end (first live run)
2. Clean up Personal section from arec-crm TASKS.md
3. Update iPhone Shortcut file path from `inbox.md` (arec-crm) → `~/Dropbox/projects/overwatch/inbox.md`
4. Check `docs/specs/future/` for next spec candidates

**Local dev setup:**
```bash
echo "DEV_USER=oscar" > app/.env     # First time only
python3 app/delivery/dashboard.py    # http://localhost:8000
python3.12 -m pytest app/tests/ -v  # 69 tests
```

---

## Open Design Questions

<!-- None at this time -->

---

## Deferred / Parked

- Prospect task completion by ID — requires either a DB or a slug/index scheme in the markdown layer
- Graph API features (`email-scan`, `auto-capture`) — work via Claude Desktop skill; disabled as in-app routes (return 501)
- `arec-mobile/` PWA — functional, not actively iterated
- `prospect_meetings` — JSON file-backed (`crm/prospect_meetings.json`); no DB table
- Overwatch cross-repo task display in arec-crm dashboard — out of scope per spec; future read-only integration
- Tony's Excel pipeline tracker — no file found; `/crm-update` skips this step until path is configured in `crm/config.md`
