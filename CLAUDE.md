# arec-crm

Multi-user CRM and fundraising platform for the AREC team. Manages investor pipeline, relationship briefs, and contact intelligence backed by PostgreSQL and Entra ID SSO.

**Location:** `~/Dropbox/projects/arec-crm/`

---

## Run Commands

```bash
python3 app/drain_inbox.py                        # Drain crm@avilacapllc.com shared mailbox
python3 app/delivery/dashboard.py                 # Web app — http://localhost:8000 (dev)
python3 -m pytest app/tests/                      # PostgreSQL-backed tests
python3 scripts/refresh_interested_briefs.py      # Bulk brief refresh for Stage 5 prospects
python3 scripts/seed_user.py                      # Add a new user to the users table
```

## Key Files

| File | Purpose |
|------|---------|
| `app/sources/crm_db.py` | PostgreSQL CRM data layer — single source of truth for all CRM data |
| `app/delivery/crm_blueprint.py` | CRM routes + relationship brief synthesis endpoints |
| `app/briefing/brief_synthesizer.py` | Claude API caller for relationship brief generation |
| `memory/people/*.md` | Canonical people knowledge base (AI-maintained + manual contact info) |

## Non-Obvious Conventions

- **PostgreSQL-only**: No markdown CRM files. All data reads/writes go through `crm_db.py`. Local dev uses local Postgres or Azure dev DB.
- **Multi-user authentication**: Entra ID SSO required for all routes. Only `@avilacapllc.com` accounts. Users must be seeded in `users` table before first login.
- **Two-tier email matching**: Domain match first (Tier 1), then person email lookup (Tier 2). Unmatched → `unmatched_emails` table.
- **Brief synthesis JSON contract**: Claude must return `{narrative, at_a_glance}`. `brief_synthesizer.py` handles parse fallbacks.
- **People knowledge base is AI-maintained**: `contacts` table stores relationship context, email history, intelligence notes. Users can manually edit: name, email, phone, org. AI-only fields: type, email_history, relationship_context, intelligence_notes.
- **Graph API email polling**: Hourly background job scans each user's mailbox (where `graph_consent_granted = True`), creates interactions, enriches contacts.
- **Personal productivity moved to Overwatch**: Tasks, briefings, meeting summaries, personal calendar — all moved to `~/Dropbox/projects/overwatch/`. AREC CRM is fundraising-only.

## Active Constraints

- **Organization field is always a dropdown**: The Organization/Company field on People Detail edit must use a `<select>` from `/crm/api/orgs`. Never render a free-text input for org name anywhere in the app.
- **Prospect task creation uses `/crm/api/tasks` POST**: Never use `/crm/api/followup` to create tasks from the prospect detail page.
- **Root route redirects to CRM**: `/` redirects to `/crm` (pipeline view). No dashboard home page.
- **Assigned To filter on pipeline**: Pipeline view has dropdown to filter prospects by `assigned_to` field.
- **No markdown fallback**: App assumes PostgreSQL is available. No `crm_reader.py` imports allowed.
- **User provisioning is manual**: New users added to Entra ID tenant + seeded in `users` table via `scripts/seed_user.py`.
