# CC-02: Flask App + Pipeline Table (Phases 2-3)

**Target:** `~/Dropbox/Tech/ClaudeProductivity/app/delivery/dashboard.py` + templates
**Depends on:** CC-01 (crm_reader.py)
**Blocks:** CC-03, CC-04

---

## Purpose

Flask web application serving the 3-column productivity dashboard on port 3001, plus a CRM pipeline table at `/crm` with inline editing. This is the primary browser UI.

## Tech Constraints

- Python 3.9+, Flask 3.0
- Vanilla HTML/CSS/JS — no npm, no React, no frameworks
- All CRM data access via `from sources.crm_reader import ...`
- No caching — read fresh from disk on every request

## Project Structure

```
~/Dropbox/Tech/ClaudeProductivity/app/
├── delivery/
│   └── dashboard.py          ← Flask app (port 3001)
├── sources/
│   └── crm_reader.py         ← from CC-01
├── templates/
│   ├── dashboard.html         ← 3-column main dashboard
│   ├── crm_pipeline.html      ← Pipeline table
│   └── crm_org_detail.html    ← (CC-03, placeholder for now)
├── static/
│   └── style.css              ← Shared styles
├── .env                       ← Environment variables
└── requirements.txt
```

## Dashboard Routes (existing concept)

```
GET /                          → 3-column dashboard
POST /api/task/complete        → Mark task done in TASKS.md
POST /api/email/dismiss        → Dismiss email item
```

The 3-column dashboard layout:

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Tasks (from TASKS.md) | Calendar (from Graph) | Email (from Graph) |

Header includes a "CRM →" link to `/crm`.

For this spec, the dashboard can be a stub that reads TASKS.md and displays tasks. Calendar and Email columns require Graph auth (CC-04) — show placeholder text until that's built.

## CRM Blueprint

Register as Blueprint with `url_prefix='/crm'`.

### Page Routes

```
GET /crm                       → Pipeline table (main CRM view)
GET /crm/org/<path:name>       → Org detail (CC-03 — return stub for now)
```

### API Routes

```
GET  /crm/api/offerings
GET  /crm/api/prospects?offering=X&include_closed=false
GET  /crm/api/fund-summary?offering=X
PATCH /crm/api/prospect/field  ← inline edit (Phase 3)
```

### Pipeline Table (`/crm`)

**Default columns:** Organization | Urgency | Stage | Expected | Next Action

**Default view:** Active pipeline only — exclude stages: Closed, Not Pursuing, Declined

**Default sort:** Urgency (High → Med → Low → blank), then Stage descending by stage number

**Offering tabs:** "AREC Debt Fund II" | "Mountain House Refi"
- Last selection persisted in localStorage
- Tab shows fund summary: total target, total committed, prospect count

**Client-side filters (JS, no server round-trip):**
- Stage (dropdown, multi-select)
- Urgency (dropdown)
- Assigned To (dropdown)
- Type (dropdown)
- "Include Closed" toggle (default: off)
- Text search on org name (instant, client-side)

**Mobile (<768px):** Collapse to 3 columns: Org | Stage | Urgency

**Row click:** Navigate to `/crm/org/<org_name>`

### Inline Editing (Phase 3)

Click any editable cell → it becomes an input/dropdown. On blur or Enter → `PATCH /crm/api/prospect/field`.

**Editable fields whitelist:**
```python
EDITABLE_FIELDS = {
    'stage', 'urgency', 'target', 'assigned_to',
    'next_action', 'notes', 'closing'
}
```

**PATCH body:**
```json
{
    "org": "Merseyside Pension Fund",
    "offering": "AREC Debt Fund II",
    "field": "urgency",
    "value": "High"
}
```

**Response:** `200 OK` with updated prospect dict, or `400` with error message.

The PATCH handler calls `crm_reader.update_prospect_field()`, which auto-updates `last_touch`.

**Stage field:** Render as dropdown with values from `config.md` stages.
**Urgency field:** Render as dropdown: High, Med, Low, (blank).
**Assigned To field:** Render as dropdown with values from `config.md` team roster.
**Target field:** Accept abbreviated input ("50M", "$5,000,000") — parse via `_parse_currency()`, store full format.
**Next Action / Notes:** Render as text input.

### Unmatched Review Panel

Collapsible panel above the pipeline table. Reads `unmatched_review.json`.

Each row shows: sender name, email, subject, date.

Actions per row:
- "Link to Org" → dropdown of existing org names → calls `POST /crm/api/unmatched/resolve` with `{email, org_name}`
- "Dismiss" → calls `DELETE /crm/api/unmatched/<email>`

```
POST /crm/api/unmatched/resolve   body: {email, org_name}
DELETE /crm/api/unmatched/<email>
GET  /crm/api/unmatched
```

## Styling

- Dark navy theme (`#1a1a2e` background) to match PWA
- Clean table with alternating row colors
- Urgency badges: High = red, Med = yellow, Low = gray
- Stage badges with color coding (higher stages = greener)
- Responsive: works on desktop and tablet

## Acceptance Criteria

- `python delivery/dashboard.py` starts Flask on port 3001
- `GET /` shows dashboard with tasks from TASKS.md
- `GET /crm` shows pipeline table with ~1,313 prospects loaded
- Offering tabs switch between Fund II and Mountain House
- Filters work client-side (no page reload)
- Inline edit on urgency field → persists to prospects.md
- Unmatched panel shows items from unmatched_review.json
- Page loads in < 2 seconds despite 15K-line prospects.md
