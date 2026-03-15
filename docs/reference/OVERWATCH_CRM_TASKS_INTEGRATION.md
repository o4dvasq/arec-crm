# Overwatch ↔ CRM Tasks API Integration Reference

**Date:** 2026-03-13
**Context:** The AREC CRM now exposes full CRUD on prospect tasks via API key auth. Overwatch already has a read-only proxy at `/api/crm/tasks` that calls `GET http://localhost:8000/crm/api/tasks/dashboard`. This doc covers what's now available so Overwatch can offer full task management — same capabilities as the CRM UI.

---

## Auth

All endpoints accept an `X-API-Key` header validated against the CRM's `OVERWATCH_API_KEY` env var.

Overwatch should send this on every request:

```
X-API-Key: <value of CRM_API_KEY from Overwatch .env>
```

The CRM base URL is `http://localhost:8000` for local dev, or the Azure production URL for deployed.

---

## Endpoints

### 1. List all open tasks (enriched with prospect data)

```
GET /crm/api/tasks/dashboard
```

Already implemented in Overwatch. Returns all open tasks with org name, offering, and deal size.

**Response:**
```json
{
  "ok": true,
  "count": 34,
  "tasks": [
    {
      "id": 42,
      "text": "Schedule follow-up call with Reid Spears",
      "assignee": "Zach",
      "priority": "Hi",
      "status": "open",
      "org_name": "Texas PSF",
      "created_at": "2026-03-10T14:30:00"
    }
  ]
}
```

### 2. List tasks for a specific prospect

```
GET /crm/api/tasks?org=Texas+PSF
```

Returns open tasks for one org only. The `org` query param is required.

**Response:** Array of task objects (not wrapped in envelope):
```json
[
  {"id": 42, "text": "...", "owner": "Zach", "priority": "Med", "status": "open", "created_at": "2026-03-10T14:30:00"}
]
```

### 3. Create a task

```
POST /crm/api/tasks
Content-Type: application/json
```

**Body:**
```json
{
  "org": "Texas PSF",
  "text": "Schedule follow-up call with Reid Spears",
  "owner": "Zach",
  "priority": "Hi"
}
```

All three of `org`, `text`, `owner` are required. `priority` defaults to `"Med"` if omitted. Valid priorities: `Hi`, `Med`, `Low`.

**Response (201):**
```json
{"ok": true, "task": {"id": 99, "text": "...", "owner": "Zach", "priority": "Hi", "status": "open"}}
```

### 4. Update a task (reassign, reprioritize, edit text, change status)

```
PATCH /crm/api/tasks/<task_id>
Content-Type: application/json
```

**Body (include only fields to change):**
```json
{"owner": "Oscar", "priority": "Med"}
```

Updatable fields: `text`, `owner`, `priority`, `status`.

**Response (200):**
```json
{"ok": true, "task": {"id": 42, "text": "...", "owner": "Oscar", "priority": "Med", "status": "open", "org_name": "Texas PSF", "created_at": "2026-03-13T..."}}
```

### 5. Mark a task complete

```
PATCH /crm/api/tasks/complete
Content-Type: application/json
```

**Body:**
```json
{"id": 42}
```

**Response (200):**
```json
{"ok": true}
```

---

## Error responses

All errors return JSON with `ok: false`:

| Status | Meaning | Example |
|--------|---------|---------|
| 400 | Validation error | `{"ok": false, "error": "org, text, and owner are required"}` |
| 401 | Bad or missing API key | `{"ok": false, "error": "Unauthorized"}` |
| 404 | Task not found | `{"ok": false, "error": "Task not found"}` |
| 500 | Server error | `{"ok": false, "error": "...", "tasks": []}` |

---

## Suggested Overwatch implementation

Overwatch likely already has a proxy pattern for the dashboard GET. Extend it with proxy routes for the write operations, or build a CRM task client module. Example proxy routes:

```
POST   /api/crm/tasks          → POST   http://localhost:8000/crm/api/tasks
PATCH  /api/crm/tasks/:id      → PATCH  http://localhost:8000/crm/api/tasks/:id
PATCH  /api/crm/tasks/complete  → PATCH  http://localhost:8000/crm/api/tasks/complete
```

Each proxy should forward the `X-API-Key` header and `Content-Type: application/json` body as-is.

---

## Priority values reference

| CRM value | Display | Sort order |
|-----------|---------|-----------|
| `Hi` | High | 1 |
| `Med` | Medium | 2 |
| `Low` | Low | 3 |

The CRM also accepts `High`, `Medium`, `Lo` as aliases but normalizes to `Hi`/`Med`/`Low` on read.
