# SPEC: CRM Tasks Dashboard API Endpoint

**Project:** arec-crm
**Date:** 2026-03-13
**Status:** Ready for implementation

---

## Objective

Build a REST endpoint `GET /api/tasks/dashboard` on the AREC CRM that returns open prospect tasks as JSON. This endpoint is consumed by the Overwatch personal dashboard (port 3001) to display CRM fundraising tasks alongside Oscar's local tasks. Read-only, no auth required for local dev (API key for production).

---

## Context

Overwatch (Oscar's personal productivity dashboard) was split from the CRM on 2026-03-12. Fundraising tasks used to live in TASKS.md alongside personal tasks. Now they live in the CRM's PostgreSQL database (`prospect_tasks` table). Overwatch needs a lightweight API to pull these tasks for display — it already has a proxy route wired up at `/api/crm/tasks` that calls `http://localhost:8000/api/tasks/dashboard` and currently gets a 404.

---

## Route

```
GET /api/tasks/dashboard
```

No request body. Optional query params for future filtering, but v1 returns all open tasks.

## Auth

Use `X-API-Key` header, validated against the `CRM_API_KEY` environment variable. For local dev, skip auth if no key is configured. The Overwatch proxy already sends this header when `CRM_API_KEY` is set in its `.env`.

If the CRM already has an API key check pattern on other routes (e.g., `@require_api_key` decorator), reuse it. If not, add a simple check:

```python
api_key = request.headers.get('X-API-Key', '')
expected = os.environ.get('CRM_API_KEY', '')
if expected and api_key != expected:
    return jsonify({'ok': False, 'error': 'Unauthorized'}), 401
```

## Response Schema

```json
{
  "ok": true,
  "tasks": [
    {
      "id": 42,
      "text": "Schedule follow-up call with Reid Spears",
      "priority": "Hi",
      "status": "open",
      "assignee": "Zach",
      "org_name": "Texas PSF",
      "due_date": null,
      "created_at": "2026-03-10T14:30:00Z",
      "updated_at": "2026-03-12T09:15:00Z"
    }
  ],
  "count": 34
}
```

### Field mapping

Map from whatever the `prospect_tasks` table columns are. The critical fields Overwatch needs:

| JSON field | Source | Notes |
|------------|--------|-------|
| `id` | Primary key | Integer |
| `text` | Task description/title column | The task text |
| `priority` | Priority column | Return as "Hi", "Med", or "Low" to match Overwatch conventions |
| `status` | Status column | Filter to open/active tasks only (exclude completed/archived) |
| `assignee` | Assignee column | Person name string |
| `org_name` | Join to organizations/prospects table | The prospect org this task belongs to |
| `due_date` | Due date column if exists | ISO 8601 string or null |
| `created_at` | Created timestamp | ISO 8601 |
| `updated_at` | Updated timestamp | ISO 8601 |

If the table schema uses different names or structures, adapt accordingly — the JSON field names above are what Overwatch expects.

## Filtering

Return only tasks where:
- Status is open/active (not completed, not archived)
- Order by: priority desc (Hi first), then updated_at desc

## Where to Put It

Look for the existing blueprint or route file that handles API routes. Likely candidates:
- `app/delivery/crm_blueprint.py`
- `app/routes/api.py`
- `app/api/tasks.py`

If there's already a `crm_blueprint` (the CLAUDE.md for Overwatch references `crm_blueprint.py` → `api_tasks_dashboard()`), the route may already be partially stubbed — check there first.

Add the route to whichever file handles `/api/` routes. Do NOT add `@login_required` — this endpoint is for machine-to-machine calls from Overwatch.

## Implementation Notes

- Keep it simple — one query, one JSON response
- No pagination needed for v1 (task count will be under 100)
- If the database query fails, return `{"ok": false, "error": "...", "tasks": []}` with a 500 status
- The endpoint should respond in under 500ms

## Acceptance Criteria

- [ ] `GET /api/tasks/dashboard` returns 200 with JSON matching the schema above
- [ ] Only open/active tasks are returned (no completed tasks)
- [ ] Tasks include `org_name` from the related organization/prospect record
- [ ] Response includes `ok: true` and `count` field
- [ ] API key validation works when `CRM_API_KEY` is set
- [ ] Endpoint works without `@login_required` (no session/cookie needed)
- [ ] Overwatch proxy at `localhost:3001/api/crm/tasks` successfully returns data from this endpoint

## Files Likely Touched

| File | Action | Reason |
|------|--------|--------|
| Route file (crm_blueprint.py or similar) | Edit | Add the new endpoint |
| Models file (if query needs a join) | Read | Understand table relationships |
| `.env` | Edit | Add CRM_API_KEY if not present |
