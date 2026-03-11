# arec-crm

Personal productivity + CRM system for Oscar Vasquez (AREC). Generates daily briefings, auto-captures email/calendar to CRM, manages tasks, and synthesizes relationship briefs via Claude.

**Location:** `~/Dropbox/projects/arec-crm/`

---

## Run Commands

```bash
python3 app/main.py                               # Morning briefing (also runs via launchd at 5 AM)
python3 app/drain_inbox.py                        # Drain crm@avilacapllc.com shared mailbox
python3 app/delivery/dashboard.py                 # Web dashboard — http://localhost:3001
python3 -m pytest app/tests/                      # 52 tests across 3 files
python3 scripts/refresh_interested_briefs.py      # Bulk brief refresh for Stage 5 prospects
```

## Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | Morning briefing orchestrator — auth, fetch, prompt, Claude call, write |
| `app/sources/crm_reader.py` | Central CRM parser — single source of truth for all CRM data |
| `app/delivery/crm_blueprint.py` | CRM routes + relationship brief synthesis endpoints |
| `crm/prospects.md` | Live CRM prospect records |
| `memory/CLAUDE.md` | Working memory: identity, inbox config, preferences, post-update extensions |

## Non-Obvious Conventions

- **CRM parsing is centralized**: Never parse `crm/*.md` outside `crm_reader.py`. All callers import from there.
- **Skills are instructional, not executable**: `skills/meeting-debrief.md` and `skills/email-scan.md` are step-by-step guides for Claude + MCP tools, not Python scripts.
- **inbox.md is ephemeral**: Cleared after each `/productivity:update` run. Not a persistent store.
- **Two-tier email matching**: Domain match first (Tier 1), then person email lookup (Tier 2). Unmatched → `crm/unmatched_review.json`.
- **Brief synthesis JSON contract**: Claude must return `{narrative, at_a_glance}`. `brief_synthesizer.py` handles parse fallbacks.
- **memory/CLAUDE.md stays under 80 lines**: People, terms, companies, deals go to `memory/` subdirectories — never in this file.
- **TASKS.md is the only task source of truth**: Notion sync is disabled. Never push tasks to Notion.
- **Notion meetings are always read**: On every `/productivity:update`, query Notion meeting notes and save new ones to `meeting-summaries/YYYY-MM-DD-slug.md`.
- **Post-update extensions always run**: After standard update, run `skills/meeting-debrief.md` then `skills/email-scan.md` in order. `email-scan.md` also scans Tony's delegate mailbox (tony@avilacapllc.com) — Oscar has delegate access. Tony scan runs as Pass 3 (Tony received) + Pass 4 (Tony sent).
- **Briefing filter**: Exclude anything regarding "Settler" from daily briefings.

## Active Constraints

- **Organization field is always a dropdown**: The Organization/Company field on People Detail edit must use a `<select>` from `/crm/api/orgs`. Never render a free-text input for org name anywhere in the app.
- **Prospect task creation uses `/crm/api/tasks` POST**: Never use `/crm/api/followup` to create tasks from the prospect detail page. Tasks are displayed via `/tasks/api/tasks/for-org` and edited via the shared `task-edit-modal.js` (which uses `/tasks/api/task/{section}/{index}` PUT/DELETE).
- **CRM backend mode**: Phase I1+ supports dual backends. Local dev uses markdown (`crm_reader.py`). Azure production uses PostgreSQL (`crm_db.py`). Both have identical function signatures. Import swap controlled in blueprints.
