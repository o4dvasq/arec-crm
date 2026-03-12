# SPEC: EasyAuth SSO & User Management

**Project:** arec-crm
**Date:** March 12, 2026
**Status:** Partially implemented — Basic SSO works (login, logout, session). `@login_required` not enforced on all routes. Review spec for remaining items.

---

## 1. Objective

Add authentication and user management to the AREC CRM so that only `@avilacapllc.com` team members can access the app, each user gets a persistent identity in the database, and an admin role is reserved for future permission gating. Authentication is handled by Azure App Service EasyAuth — Flask does not implement any OAuth flows. The app auto-provisions users on first visit and provides a basic admin page for role management.

---

## 2. Scope

### In Scope
- Flask middleware to read EasyAuth headers and resolve the current user
- Auto-provisioning: create a `users` row on first visit for any authenticated `@avilacapllc.com` user
- `role` column on `users` table (`admin` or `user`), defaulting to `user`
- Oscar Vasquez (`ovasquez@avilacapllc.com`) hardcoded as auto-promoted to `admin` on first provision
- Local dev bypass via `DEV_USER` environment variable
- `@require_admin` decorator for admin-only routes
- Admin page at `/admin/users` — list users, change roles
- `access_denied.html` shown when a non-admin hits an admin-only route
- `g.user` available in all Flask routes and Jinja2 templates after middleware runs

### Out of Scope
- MSAL OAuth flow in Flask (EasyAuth handles login externally)
- API key / token auth for programmatic endpoints (future phase)
- Granular permissions beyond admin/user (future phase)
- Graph API consent per user (already handled by `graph_poller.py`)
- Any changes to Overwatch

---

## 3. Business Rules

1. **EasyAuth is the perimeter.** Azure App Service is configured to require Entra ID login and restrict to the `avilacapllc.com` tenant. No unauthenticated request ever reaches Flask in production.
2. **Auto-provision on first visit.** If a request arrives with a valid EasyAuth identity and no matching `users` row, create one with `role = 'user'`. Exception: if the email is `ovasquez@avilacapllc.com`, set `role = 'admin'`.
3. **Local dev bypass.** When `DEV_USER` is set in the environment, skip EasyAuth header parsing and treat that email as the authenticated user. This is only for local development — `DEV_USER` must never be set in Azure.
4. **Admin role is soft-gated.** In this phase, both `admin` and `user` roles have full CRM access. The `admin` role gates only: (a) the `/admin/users` page, and (b) future config editing. Regular CRM routes do NOT check role.
5. **Last login tracking.** Update `last_login_at` on every request (or at most once per session/hour to avoid write pressure — implementer's choice, document which).

---

## 4. Data Model / Schema Changes

### Modify `users` table

The `users` table should already exist (from `create_schema.py`). Add or ensure these columns:

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'user';
ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW();
```

Existing columns expected: `id` (PK), `email` (unique, not null). If additional columns exist from prior migrations, preserve them.

Create a migration script: `scripts/migrate_add_auth_columns.py`. Idempotent — safe to run multiple times.

### Role values
- `'admin'` — can access `/admin/*` routes
- `'user'` — default, full CRM access, no admin pages

---

## 5. UI / Interface

### 5.1 All Pages — Current User Indicator

Add to the existing nav/header area (all CRM pages):
- Display the current user's name or email, right-aligned in the header
- If admin: show a small "Admin" badge or link to `/admin/users`
- Keep it minimal — a single line of text, not a dropdown menu

### 5.2 Admin Users Page (`/admin/users`)

**Route:** `GET /admin/users`
**Template:** `templates/admin/users.html`
**Protected by:** `@require_admin` decorator

Layout:

```
┌──────────────────────────────────────────────────────────────┐
│  AREC CRM                          Oscar Vasquez (Admin)     │
├──────────────────────────────────────────────────────────────┤
│  ← Back to Pipeline                                          │
│                                                              │
│  Team Members                                                │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ Name              Email                Role   Last Login ││
│  │ Oscar Vasquez     ovasquez@avila...    Admin  Today      ││
│  │ Tony Avila        tavila@avila...      User   Mar 10     ││
│  │ Truman Flynn      tflynn@avila...      User   Mar 8      ││
│  │ [empty state: "No other users have logged in yet"]       ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  Role column: clickable dropdown (admin/user) — saves via    │
│  POST on change. Cannot demote yourself.                     │
└──────────────────────────────────────────────────────────────┘
```

**States:**
- **Loading:** Standard spinner or skeleton
- **Empty:** Only Oscar's row (if no one else has logged in yet). Message: "No other team members have logged in yet."
- **Error:** Flash message if role update fails

**Interactions:**
- Role dropdown inline in table. On change → `POST /admin/users/<id>/role` with `{"role": "admin"}` or `{"role": "user"}`
- Cannot change your own role (dropdown disabled on your own row)
- Success → flash "Role updated" + page refresh
- Link back to pipeline at top

### 5.3 Access Denied Page

**Route:** Any `@require_admin` route hit by a non-admin
**Template:** `templates/access_denied.html` (already exists per handoff doc)

Content: "You don't have permission to view this page. Contact Oscar Vasquez for access." with a link back to the pipeline.

---

## 6. Integration Points

### Reads From
- **Azure EasyAuth headers:** `X-MS-CLIENT-PRINCIPAL-NAME` (email), `X-MS-CLIENT-PRINCIPAL-ID` (Entra object ID), `X-MS-TOKEN-AAD-ID-TOKEN` (optional, for display name extraction)
- **Environment:** `DEV_USER` (local dev only), `DATABASE_URL`
- **PostgreSQL `users` table**

### Writes To
- **PostgreSQL `users` table:** auto-provision new rows, update `last_login_at`, update `role` via admin page

### Calls
- No external API calls. EasyAuth is handled at the Azure infrastructure layer.

---

## 7. Constraints

1. **No new Python libraries.** Use only Flask and psycopg2 (already in the project). No Flask-Login, no Flask-Security, no MSAL.
2. **No JavaScript frameworks.** Admin page uses the same vanilla JS + Jinja2 pattern as the rest of the CRM.
3. **Middleware, not decorators on every route.** The user-resolution logic runs as a Flask `before_request` hook, setting `g.user`. Individual routes do NOT need an auth decorator — they're all behind EasyAuth. Only admin routes get `@require_admin`.
4. **DEV_USER is dev-only.** Add a startup warning log if `DEV_USER` is set: `"WARNING: DEV_USER is set — authentication is bypassed. Do not use in production."`
5. **Idempotent migration.** The migration script must use `IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS` so it's safe to run repeatedly.
6. **Do not modify EasyAuth configuration.** That's an Azure Portal setting, not code. The spec only covers what Flask does with the headers it receives.
7. **Preserve existing routes.** No route paths change. The middleware is additive.

---

## 8. Acceptance Criteria

1. With `DEV_USER=ovasquez@avilacapllc.com` in `.env`, the CRM starts locally and `g.user` is populated on every request with Oscar's user record.
2. On first request with a new email (via EasyAuth header or `DEV_USER`), a `users` row is created with `role='user'` and `created_at` set.
3. Exception: `ovasquez@avilacapllc.com` is auto-provisioned with `role='admin'`.
4. `g.user` is a dict (or object) with at minimum: `id`, `email`, `display_name`, `role`, `last_login_at`.
5. All existing CRM templates display the current user's email or name in the header area.
6. `/admin/users` returns 200 for admin users and shows the user table.
7. `/admin/users` returns 403 + `access_denied.html` for non-admin users.
8. Role dropdown on `/admin/users` saves via POST and persists to the database.
9. An admin cannot demote themselves via the UI.
10. `scripts/migrate_add_auth_columns.py` runs idempotently and adds the required columns.
11. When `DEV_USER` is set, a warning is logged at startup.
12. When `DEV_USER` is NOT set and EasyAuth headers are missing, the middleware returns 401 (safety net — should never happen in production behind EasyAuth).
13. Feedback loop prompt has been run and project docs updated.

---

## 9. Files Likely Touched

| File | Action | Reason |
|------|--------|--------|
| `scripts/migrate_add_auth_columns.py` | **Create** | Add role, display_name, last_login_at, created_at columns |
| `app/auth/auth_middleware.py` | **Create** | `before_request` hook: parse EasyAuth headers or DEV_USER, auto-provision, set `g.user` |
| `app/auth/decorators.py` | **Create** | `@require_admin` decorator |
| `app/delivery/dashboard.py` | **Modify** | Register `before_request` hook, register admin blueprint |
| `app/delivery/admin_blueprint.py` | **Create** | `/admin/users` GET + `/admin/users/<id>/role` POST |
| `templates/admin/users.html` | **Create** | Admin user management page |
| `templates/access_denied.html` | **Modify** | Update copy if needed (already exists) |
| `templates/crm/*.html` | **Modify** | Add current user display to nav/header area |
| `app/.env` | **Modify** | Add `DEV_USER=ovasquez@avilacapllc.com` |
| `CLAUDE.md` | **Modify** | Add auth section documenting EasyAuth pattern and DEV_USER |

---

## 10. Claude Code Kickoff Prompt

```
Read CLAUDE.md, then read docs/specs/SPEC_easyauth-sso.md.
Do not read other files yet. Confirm you understand the objective
and acceptance criteria, then tell me which files you plan to touch
before writing any code.
```
