# SPEC: Engagement Heatmap | Project: arec-crm | Date: 2026-03-21 | Status: Ready for Implementation

---

## 1. Objective

Add a new "Health" screen to the CRM that renders a color-coded engagement heatmap for all Stage 5 prospects. The screen gives the team an at-a-glance view of relationship health ranked by the firmness and recency of engagement — from a scheduled future meeting (best) to no contact at all (worst).

This spec also includes cleanup of the three remaining `next_action` references in production code.

---

## 2. Scope

**In scope:**
- New route `GET /crm/health` with dedicated template `crm_health.html`
- New "Health" nav item in `_nav.html`
- New function `get_heatmap_prospects()` in `crm_reader.py`
- Cleanup of 3 remaining `next_action` references in `crm_blueprint.py`

**Out of scope:**
- Mobile / PWA version
- Historical trend tracking or export
- Database migration (there is no database — this is a markdown-only CRM)

---

## 3. Business Rules

### 3.1 Prospect Filter
Include all prospects whose Stage field starts with `5.` (i.e., "5. Interested"), regardless of offering, assigned-to, urgency, or target size.

### 3.2 Engagement Signal Hierarchy
Signals are evaluated in priority order. A prospect receives the status of the **highest-ranked signal that applies**:

| Rank | Status Key | Display Label | Color |
|------|-----------|---------------|-------|
| 1 | `scheduled` | Meeting Scheduled | Green `#22c55e` |
| 2 | `held` | Meeting Held | Light Green `#86efac` |
| 3 | `inbound` | Inbound Reply | Yellow `#f59e0b` |
| 4 | `outbound_only` | Outbound — No Reply | Orange `#f97316` |
| 5 | `no_contact` | No Contact | Red `#ef4444` |

### 3.3 Data Sources for Engagement Signals

The CRM has three relevant data stores. Claude Code must use these — there is no SQL database:

1. **`crm/meetings.json`** — Unified meeting store. Each entry has `org`, `offering`, `meeting_date`, `status` (scheduled/completed/reviewed). Use `load_meetings()` from `crm_reader.py`.
   - **Scheduled:** `meeting_date > today` OR `status == 'scheduled'`
   - **Held:** `meeting_date <= today` AND `status` in (`completed`, `reviewed`)

2. **`crm/email_log.json`** — Email scan results. Each entry has `from`, `fromName`, `orgMatch`, `date`, `summary`. Use `load_email_log()` from `crm_reader.py`.
   - **Inbound:** `from` address domain does NOT match AREC domains (`avilacapllc.com`, `arecllc.com`)
   - **Outbound:** `from` address domain DOES match AREC domains
   - Match to prospect via `orgMatch` field (case-insensitive match against prospect's org name)

3. **`crm/interactions.md`** — Interaction log. Each entry has `org`, `type`, `date`, and fields like Contact, Subject, Summary, Source. Use `load_interactions()` from `crm_reader.py`.
   - Type field contains strings like "Email", "Meeting", "Call" — use these to distinguish interaction types
   - No explicit direction field; treat all interactions as supplementary engagement evidence (any interaction within window = at minimum `outbound_only`)

### 3.4 Staleness Thresholds
For statuses `held`, `inbound`, and `outbound_only`, the qualifying interaction must fall within these windows or the prospect drops to `no_contact`:

| Days Since Interaction | Effect |
|------------------------|--------|
| ≤ 7 days | Full color — fresh |
| 8–14 days | Slightly muted — apply `opacity: 0.75` to color chip |
| 15–21 days | Further muted — apply `opacity: 0.5` to color chip |
| 21+ days | Treat as `no_contact` (Red) regardless of interaction type |

Status `scheduled` is never muted — a future meeting is always fully green.

### 3.5 Sort Order
Default: worst health first (Red → Orange → Yellow → Light Green → Green).
Within each color tier: sort by Target descending (largest at-risk deals at top of each tier).

### 3.6 Next Action Field — Cleanup

> **Implementation instruction:** Run a project-wide `grep -rn "next_action\|Next Action"` before writing any removal code. Confirm every location. The following 3 references are known to remain:

Remove `next_action` from:
- `crm_blueprint.py` line ~1039 — the `if field == 'next_action'` reject guard in the inline-edit route (remove the 2-line guard; the `EDITABLE_FIELDS` check on the next line already rejects unknown fields)
- `crm_blueprint.py` line ~1765–1766 — the Excel export writes a `Next Action` column. Remove these 2 lines and adjust column references if needed
- Any other straggler references found by grep (exclude `docs/specs/` and `docs/archive/`)

Do NOT touch:
- `crm_reader.py` line ~1037–1039 — the `update_prospect_field()` silent reject for `next_action` is a safety guard. Leave it as-is.

---

## 4. Data Model / Schema Changes

### 4.1 No Schema Changes
There is no database. All data lives in markdown files and JSON. No migration scripts needed.

### 4.2 New Function in `crm_reader.py`

Add to `crm_reader.py`:

```python
def get_heatmap_prospects() -> list[dict]:
    """
    Returns all Stage 5 prospects with engagement status computed.

    Each dict contains:
      org               str   — organization name
      offering          str   — offering name (e.g., "AREC Debt Fund II")
      target            float — target amount (raw number, not formatted)
      target_display    str   — formatted target (e.g., "$50M")
      assigned_to       str or None
      primary_contact   str or None
      status            str   — 'scheduled' | 'held' | 'inbound' | 'outbound_only' | 'no_contact'
      status_date       str or None  — ISO date of most recent qualifying interaction
      days_since        int or None  — days since status_date
      next_meeting_date str or None  — ISO date of next future meeting
      staleness         str   — 'fresh' | 'aging' | 'stale' (for CSS class selection)
    """
```

**Scoring pseudocode:**
```
AREC_DOMAINS = {'avilacapllc.com', 'arecllc.com'}
cutoff = today - 21 days

For each prospect where Stage starts with "5.":
  org = prospect's org name
  offering = prospect's offering name

  1. Check meetings.json (via load_meetings(org=org, offering=offering)):
     Filter for meetings where meeting_date > today OR status == 'scheduled'
     → If found: status = 'scheduled'
                 next_meeting_date = earliest future meeting date

  2. Else check meetings.json for held meetings:
     Filter for meetings where meeting_date <= today AND meeting_date >= cutoff
           AND status in ('completed', 'reviewed')
     → If found: status = 'held'
                 status_date = most recent meeting date
                 days_since = today - status_date

  3. Else check email_log.json (via load_email_log()):
     Filter emails where orgMatch matches org (case-insensitive) AND date >= cutoff
     Sort by date descending, take the most recent
     → If from-domain NOT in AREC_DOMAINS: status = 'inbound'
     → Else: status = 'outbound_only'
     In either case: status_date = that email's date, days_since = today - status_date

  4. Else check interactions.md (via load_interactions(org=org)):
     Filter for interactions where date >= cutoff
     → If found: status = 'outbound_only'
                 status_date = most recent interaction date
                 days_since = today - status_date

  5. Else: status = 'no_contact', status_date = None, days_since = None

  Compute staleness:
    if status == 'scheduled': staleness = 'fresh'
    elif days_since <= 7: staleness = 'fresh'
    elif days_since <= 14: staleness = 'aging'
    else: staleness = 'stale'
```

> **Implementation instruction:** `load_prospects()` returns all prospects. Filter for Stage starting with "5." in Python. Prospect dicts have keys: `Org` (the h3 heading under the offering h2), `Offering` (the h2 heading), `Stage`, `Target`, `Assigned To`, `Primary Contact`, `Notes`, `Last Touch`. The `Target` field is a currency string — use `_parse_currency()` to get the float for sorting.

---

## 5. UI / Interface

### 5.1 Page Layout

```
┌─────────────────────────────────────────────────────┐
│  NAV  Tasks | Pipeline | Health | People | Orgs ...  │
├─────────────────────────────────────────────────────┤
│  Stage 5 Engagement Health          [↻ Refresh]     │
│  25 prospects  ·  Last updated: Today 9:14 AM       │
├─────────────────────────────────────────────────────┤
│  LEGEND:  🔴 No Contact  🟠 Outbound Only           │
│           🟡 Inbound Reply  🟢 Meeting Held         │
│           🟢 Meeting Scheduled                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ── No Contact (8) ─────────────────────────────── │  ← Red section header
│  ┌───────────────────────────────────────────────┐  │
│  │ Merseyside Pension Fund  $50M  J. Walton     │  │
│  │ 🔴 No Contact            —                   │  │
│  ├───────────────────────────────────────────────┤  │
│  │ NPS Korea SWF            $300M  Z. Reisner   │  │
│  │ 🔴 No Contact            —                   │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  ── Outbound — No Reply (4) ───────────────────── │  ← Orange
│  ...                                                │
│                                                     │
│  ── Inbound Reply (5) ─────────────────────────── │  ← Yellow
│  ...                                                │
│                                                     │
│  ── Meeting Held (3) ────────────────────────────  │  ← Light Green
│  ...                                                │
│                                                     │
│  ── Meeting Scheduled (3) ───────────────────────  │  ← Green
│  ...                                                │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 5.2 Prospect Row

Each row is a horizontal card containing:

| Field | Content |
|-------|---------|
| **Org Name** | Bold; links to `/crm/prospect/<org>/<offering>` (URL-encoded) |
| **Target** | Formatted as `$50M` |
| **Assigned To** | Short name |
| **Status Chip** | Color-coded pill with status label (see 3.2) |
| **Days Since** | `X days ago` in muted text, or `—` if no date |
| **Next Meeting** | Date string if `scheduled`, else blank |

### 5.3 Color Chip Rendering
- Background = status color hex (Section 3.2)
- Staleness muting via CSS classes: `chip--fresh` (100%), `chip--aging` (75% opacity), `chip--stale` (50% opacity)
- `scheduled` chip always `chip--fresh`; prepend a calendar icon (use Lucide icons — already loaded in `_nav.html`)

### 5.4 Section Headers
- One header per status tier, shown only if that tier has ≥ 1 prospect
- Header text: `── {Status Label} ({count}) ──────`
- Header background: 10% opacity tint of the status color

### 5.5 Refresh
- `[↻ Refresh]` button top-right triggers `window.location.reload()`
- "Last updated" timestamp rendered server-side as current request time

---

## 6. Integration Points

- **Route:** `GET /crm/health` — use `@login_required` decorator (the no-op passthrough defined at top of `crm_blueprint.py`)
- **Data:** calls `get_heatmap_prospects()` in route handler, passes result to template
- **Nav:** Add "Health" link to `_nav.html` — position after "Pipeline", before "People". Use the same `nav-tab` / `nav-tab--active` pattern with `active_tab == 'health'`
- **Interactions:** read-only; no writes from this screen
- **Prospect links:** each org name links to existing `/crm/prospect/<org>/<offering>` (these are URL-encoded strings, not integer IDs)
- **Template:** Create `app/templates/crm_health.html` extending the existing template pattern (include `_nav.html` with `active_tab='health'`)

---

## 7. Constraints

- No new data files, no database, no migrations
- No new JS libraries — vanilla JS and existing `crm.css` custom properties only
- Must match existing dark theme (see other templates for CSS variable usage)
- Page must render in under 2 seconds for up to 50 Stage 5 prospects
- `next_action` cleanup must not break existing tests — run `pytest app/tests/ -v` before and after and confirm all pass
- All data reads go through `crm_reader.py` functions — no direct file parsing in the route handler or template

---

## 8. Acceptance Criteria

- [ ] `/crm/health` loads successfully
- [ ] "Health" nav item present and active when on `/crm/health`
- [ ] All Stage 5 prospects appear grouped by status tier
- [ ] Color chips render correctly for all 5 tiers
- [ ] Staleness muting applies at 8–14d (`chip--aging`) and 15–21d (`chip--stale`)
- [ ] Prospects with no interaction within 21 days show as Red / No Contact
- [ ] Future meeting → Green / Meeting Scheduled with next meeting date shown
- [ ] Within each tier, prospects sorted by Target descending
- [ ] Org name links to correct prospect detail page (`/crm/prospect/<org>/<offering>`)
- [ ] Three remaining `next_action` references removed from `crm_blueprint.py`
- [ ] All existing tests pass after changes (`pytest app/tests/ -v`)
- [ ] Page matches existing dark theme
- [ ] Feedback loop prompt has been run

---

## 9. Files Likely Touched

| File | Change |
|------|--------|
| `app/sources/crm_reader.py` | Add `get_heatmap_prospects()` |
| `app/delivery/crm_blueprint.py` | Add `/crm/health` route; remove 3 `next_action` references |
| `app/templates/crm_health.html` | **New file** |
| `app/templates/_nav.html` | Add Health nav item after Pipeline |
