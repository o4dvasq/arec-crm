# CRM Phase 7 — Dashboard Cleanup Spec
**For Claude Code**
**Author:** Oscar Vasquez, COO — Avila Real Estate Capital
**Date:** March 2026
**Status:** Ready for Execution
**Depends on:** Phases 1–5 complete (Phase 6 analytics skipped)

---

## Overview

Final cleanup phase. Remove the Investors column (Column 4) from the existing
morning briefing dashboard, update the CSS grid from 4 to 3 columns, and strip
all investor/glossary loading code from `dashboard.py`. Verify no regressions
across the full system.

---

## Environment

- App root: `~/arec-morning-briefing/`
- Flask app: `delivery/dashboard.py`, port 3001
- Dashboard template: `templates/dashboard.html`
- Do not touch any CRM files (`templates/crm/`, `static/crm/`, `sources/crm_reader.py`, etc.)

---

## Step 1 — Remove Column 4 from `templates/dashboard.html`

**File to modify:** `templates/dashboard.html`

Find and remove the entire Column 4 (Investors) block — all HTML from its
opening wrapper element to its closing tag. This column reads from
`memory/glossary.md` and displays an investor universe table with status
badges and recent activity.

After removal the content area must render exactly 3 columns:
- Column 1: Tasks
- Column 2: Today (calendar)
- Column 3: Email

Update the CSS grid definition from 4 columns to 3. Look for a rule like:

```css
grid-template-columns: repeat(4, 1fr);
/* or */
grid-template-columns: 1fr 1fr 1fr 1fr;
```

Change to:

```css
grid-template-columns: repeat(3, 1fr);
```

If the columns use named grid areas, update accordingly.

Remove any Column 4 specific CSS (investor badges, activity tags, etc.) that
is no longer needed. Do not remove CSS shared with other columns.

---

## Step 2 — Remove Investor Loading Code from `dashboard.py`

**File to modify:** `delivery/dashboard.py`

Find and remove all code that:
- Reads `memory/glossary.md` to parse the Investor Universe table
- Passes investor data to the dashboard template context
- Defines any helper functions used exclusively for investor column rendering

Do not remove:
- The `crm_bp` Blueprint or any CRM routes (added in Phases 2–5)
- Any other existing dashboard routes or data loading functions
- The `memory_reader.py` import if it is still used by other parts of the dashboard

After removal, restart the app and confirm the dashboard route returns 200
with no template rendering errors.

---

## Step 3 — Verify Full System

```bash
cd ~/arec-morning-briefing
python3 delivery/dashboard.py
```

### Dashboard checks
- [ ] `http://localhost:3001` loads with no errors
- [ ] Dashboard shows exactly 3 columns: Tasks, Today, Email
- [ ] Column widths are even (no collapsed or oversized columns)
- [ ] No investor/glossary content visible anywhere on the dashboard
- [ ] "CRM →" link in dashboard header still present and navigates to `/crm`
- [ ] No Python errors in terminal on page load

### CRM checks (regression)
- [ ] `http://localhost:3001/crm` — pipeline table loads, offering tabs work
- [ ] Inline editing still works (Stage, Urgency, Expected, Next Action)
- [ ] `http://localhost:3001/crm/org/<n>` — org detail page loads
- [ ] Org profile, contacts, and prospects sections render and edit correctly
- [ ] Auto-capture button on pipeline page still functional
- [ ] Unmatched review panel renders

### Morning briefing check
```bash
# Dry run — verify briefing generation still works
python3 main.py --dry-run
# (or however the app supports a test run without sending to Slack)
```
- [ ] No import errors related to removed investor code
- [ ] Briefing generates successfully

---

## What This Phase Does NOT Touch

- CRM routes, templates, JS, CSS — untouched
- `memory/glossary.md` file itself — leave on disk, just stop reading it
- Morning briefing prompt builder — if it references glossary investor data,
  leave that intact (the briefing's investor context is separate from the
  dashboard column)
- Any Phase 5 auto-capture or unmatched review functionality

---

## Files Modified

```
templates/dashboard.html    ← MODIFIED: remove Column 4 HTML + update grid CSS
delivery/dashboard.py       ← MODIFIED: remove investor/glossary loading code
```

---

## Done

With Phase 7 complete, the full CRM build is finished:

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Data layer — parser, CSV import, unit tests | ✅ |
| 2 | Prospects table — read-only, filtering, sorting | ✅ |
| 3 | Inline editing — field PATCH API, 5 editable fields | ✅ |
| 4 | Org detail page — profile, contacts, prospects, Add Prospect | ✅ |
| 5 | Graph auto-capture — email + calendar matching, review panel | ✅ |
| 6 | Analytics | Skipped |
| 7 | Dashboard cleanup — remove Column 4, 3-column grid | ✅ |
