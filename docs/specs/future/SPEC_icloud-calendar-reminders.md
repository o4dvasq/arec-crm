# SPEC: iCloud Calendar & Reminders Integration
**Project:** Overwatch | **Date:** March 2026
**Status:** Future — belongs in Overwatch repo, not arec-crm

SEQUENCING: Implement AFTER Overwatch repo scaffold (SPEC_overwatch-repo-scaffold.md) is complete. This spec lives here temporarily until the Overwatch repo exists, then should be moved there.
DEPENDS ON: Overwatch repo with Flask dashboard running on port 3002.
NOTE: This is CalDAV-based with no database — clean for markdown-local architecture. No CRM dependencies.

---

## 1. Objective

Add a live iCloud data panel to the Overwatch dashboard that shows today's Apple Calendar events and iCloud Reminders side-by-side with the existing TASKS.md task board. Data is fetched on page load via CalDAV using an iCloud app-specific password. This gives Oscar a unified daily view without leaving the Overwatch dashboard.

---

## 2. Scope

**In scope:**
- Fetch today's events from one iCloud Calendar account via CalDAV on page load
- Fetch incomplete reminders from one iCloud Reminders list via CalDAV on page load
- Render a two-column section on the dashboard: left = iCloud data (calendar + reminders), right = existing TASKS.md board
- Graceful error state if iCloud is unreachable (e.g. offline, bad credentials)
- Credentials stored in a local `.env` file (never committed)

**Out of scope:**
- Write-back / creating events or reminders from the dashboard
- Multiple iCloud Reminders lists
- Non-today calendar events (no week view, no month view)
- Any sync to disk (vdirsyncer, .ics files)
- Scheduled background refresh — on page load only
- Multi-user, auth, or deployment to Azure

---

## 3. Business Rules

- **Today's events** = events whose start date falls on the current local date (Oscar's system timezone). All-day events are included.
- **Reminders** = all incomplete reminders in the target list, regardless of due date. Sort: overdue first (by due date asc), then no-due-date items at the bottom.
- **TASKS.md** rendering is unchanged — this spec does not touch the existing task board logic.
- iCloud credentials must never be hardcoded. They are read from environment variables at app startup.
- If CalDAV returns an error or times out (5s timeout), the iCloud panel shows a non-blocking error message and the rest of the dashboard loads normally.
- The CalDAV fetch is synchronous on page load (acceptable for a local single-user tool). No async worker needed.

---

## 4. Data Model / Schema Changes

No database. No new files persisted to disk.

Two new environment variables added to `.env`:

```
ICLOUD_APPLE_ID=oscar@icloud.com         # or Apple ID email
ICLOUD_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx  # app-specific password from appleid.apple.com
```

These are read in `dashboard.py` via `os.environ` or `python-dotenv`.

---

## 5. UI / Interface

### Dashboard Layout Change

Current layout (assumed single-column or existing sections) gains a new **"Today" panel** at the top or prominent position. Two columns inside it:

**Left column — iCloud**
- Sub-header: `📅 Today's Events` — list of events with time + title. If none: "No events today."
- Sub-header: `🔔 Reminders` — list of incomplete reminders with title and due date if set. Overdue items shown in red or with a warning indicator. If none: "No reminders."
- Loading state: spinner or "Loading iCloud…" text while fetch is in progress
- Error state: yellow warning box — "iCloud unavailable — check credentials or connection."

**Right column — Tasks**
- Existing TASKS.md board rendered as-is. No changes to this column.

### States to handle
| State | Behavior |
|---|---|
| Loading | Show spinner in left column |
| Success | Render events + reminders lists |
| Empty (no events/reminders) | Show "none" messages, don't hide the column |
| Error / timeout | Show warning box, right column still loads |
| Offline | Same as error |

---

## 6. Integration Points

### New dependency: `caldav` Python library
```
pip install caldav
```
Add to `requirements.txt`.

### New module: `app/integrations/icloud.py`

Expose two functions:

```python
def get_todays_events() -> list[dict]:
    # Returns list of {title, start_time, end_time, all_day}
    # Sorted by start_time asc

def get_reminders() -> list[dict]:
    # Returns list of {title, due_date, is_overdue}
    # Sorted: overdue first, no-due-date last
```

Both functions:
- Connect to iCloud CalDAV at `https://caldav.icloud.com`
- Authenticate with `ICLOUD_APPLE_ID` + `ICLOUD_APP_PASSWORD`
- Raise a custom `ICloudUnavailableError` on any connection/auth failure
- Have a 5-second timeout

### CalDAV endpoints (iCloud)
- Calendar: principal URL auto-discovered from `https://caldav.icloud.com`
- Reminders: iCloud exposes Reminders as a CalDAV calendar with `VTODO` components (not `VEVENT`)

### `dashboard.py` changes
- Import and call both functions at route handler time (not at startup)
- Pass results (or error flag) into the Jinja template context
- Wrap calls in try/except for `ICloudUnavailableError`

### Template changes
- Update the main dashboard Jinja template to render the two-column layout described above
- iCloud data passed as `icloud_events`, `icloud_reminders`, `icloud_error` template variables

---

## 7. Constraints

- **Local only** — no proxy, no Azure, no external service. CalDAV calls go directly from Oscar's Mac to iCloud servers.
- **App-specific password required** — iCloud accounts with 2FA (all modern accounts) cannot use the Apple ID password directly. Oscar must generate one at [appleid.apple.com](https://appleid.apple.com) → Security → App-Specific Passwords.
- **No caching** — fetch is live on every page load. If this becomes slow, a manual refresh button can be added later.
- **Single iCloud account** — no multi-account support.
- **`caldav` library version** — use `caldav>=1.3` which has stable iCloud support.
- **Do not use `icalendar` directly** — let the `caldav` library handle parsing.

---

## 8. Acceptance Criteria

- [ ] `.env` contains `ICLOUD_APPLE_ID` and `ICLOUD_APP_PASSWORD`; app reads them at startup and fails with a clear message if missing
- [ ] Dashboard loads and iCloud panel appears without errors when credentials are valid and Mac is online
- [ ] Today's calendar events are listed in the left column with correct times
- [ ] All-day events appear correctly (no time shown, just title)
- [ ] Incomplete reminders appear in the left column, sorted overdue-first
- [ ] Overdue reminders are visually distinguished (e.g. red text or icon)
- [ ] If iCloud is unreachable, a non-blocking warning renders in the left column and TASKS.md still loads normally
- [ ] TASKS.md right column is visually and functionally unchanged
- [ ] `ICLOUD_APP_PASSWORD` is in `.gitignore` / `.env` and not committed
- [ ] `caldav` is added to `requirements.txt`
- [ ] "Feedback loop prompt has been run" (Claude Code review pass completed)

---

## 9. Files Likely Touched

| File | Reason |
|---|---|
| `app/integrations/icloud.py` | **New file** — CalDAV fetch logic |
| `app/delivery/dashboard.py` | Import icloud module, pass data to template |
| `templates/dashboard.html` (or equivalent) | Two-column layout, iCloud panel |
| `requirements.txt` | Add `caldav>=1.3` |
| `.env` | Add `ICLOUD_APPLE_ID`, `ICLOUD_APP_PASSWORD` |
| `.env.example` | Document new vars (no real values) |
| `.gitignore` | Ensure `.env` is excluded |
