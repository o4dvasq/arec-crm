# SPEC: Org Detail Page Enhancements | Project: arec-crm | Date: 2026-03-17 | Status: Ready for implementation

---

## 1. Objective

Enhance the Organization detail page with three changes:
1. Remove the "Notes" subsection from the org top card.
2. Add an **Org Brief** — a new AI-synthesized relationship brief at the org level, rendered in its own section between Contacts and Prospects. The Org Brief reads all prospect briefs for that org, org notes, and opens with which offerings the org is considering.
3. Add an **Org Notes** append-only timestamped log (mirroring `prospect_notes`) at the bottom of the page, with the ability to add new entries.
4. Rename the existing brief on the Prospect detail page from "Relationship Brief" to "Prospect Briefing".

---

## 2. Scope

**In scope:**
- New `org_briefs` table (separate from `briefs`)
- New `org_notes` table (mirroring `prospect_notes`)
- Org Brief section on org detail page with Refresh button
- Org Notes section on org detail page with Add Note form
- Remove Notes rendering from org top card
- Org Brief synthesis via Claude API with org-specific system prompt
- Rename "Relationship Brief" → "Prospect Briefing" on prospect detail page
- New `crm_db.py` functions for org briefs and org notes

**Out of scope:**
- Changes to prospect brief logic or storage
- Org brief in pipeline list view
- Bulk brief refresh for orgs
- Any changes to email auto-capture or interaction logging

---

## 3. Business Rules

### Org Brief
- The Org Brief is a standalone AI synthesis at the **organization** level, stored in its own table (`org_briefs`).
- Context sources for synthesis (in order):
  1. Organization record (name, type)
  2. All contacts linked to the org
  3. All prospect records for this org (stage, target, committed, assigned to, next action)
  4. All **prospect briefs** for this org's prospects (read from existing `briefs` table)
  5. All org notes (from new `org_notes` table)
  6. Interaction history for the org
  7. Email history for the org
- The narrative **must open** with a sentence identifying which offerings the org is considering, e.g.: *"Future Fund is considering both a Fund II investment and a Mountain House co-investment."*
- Same JSON contract as prospect briefs: `{narrative, at_a_glance}`
- Cached in `org_briefs` table; refreshed on demand via button click
- If no prospect briefs exist yet, the org brief still generates using available context (org record, contacts, notes, interactions)

### Org Notes
- Append-only timestamped log, identical behavior to `prospect_notes`
- Each entry: timestamp + user (from session) + free-text note
- Displayed in reverse chronological order (newest first)
- Notes feed into the Org Brief synthesis context

### Top Card Notes Removal
- Remove the "Notes" subsection from the org top card rendering
- The `organizations.notes` column remains in the DB (no migration to drop it) — it just stops being displayed
- Existing data in `organizations.notes` is not migrated to `org_notes` — clean start

---

## 4. Data Model / Schema Changes

### New table: `org_briefs`

```sql
CREATE TABLE org_briefs (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    narrative TEXT NOT NULL DEFAULT '',
    at_a_glance TEXT NOT NULL DEFAULT '',
    generated_at TIMESTAMP DEFAULT NOW(),
    generated_by INTEGER REFERENCES users(id),
    UNIQUE(organization_id)
);
```

One brief per org (upsert on refresh). `at_a_glance` stores the bullet list as text (same format as prospect briefs).

### New table: `org_notes`

```sql
CREATE TABLE org_notes (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    note TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id)
);
CREATE INDEX idx_org_notes_org_id ON org_notes(organization_id);
```

Mirrors `prospect_notes` structure.

### Models (models.py)

Add two new SQLAlchemy model classes: `OrgBrief` and `OrgNote`, following existing patterns for `Brief` and `ProspectNote`.

---

## 5. UI / Interface

### 5a. Org Detail Page — Section Order (top to bottom)

1. **Top Card** — org name, type, domains, email history (NO notes subsection)
2. **Contacts** — existing contacts table (unchanged)
3. **Org Brief** — NEW section (see below)
4. **Prospects** — existing prospect cards for this org (unchanged)
5. **Interactions** — existing interaction log (unchanged)
6. **Org Notes** — NEW section (see below)

### 5b. Org Brief Section

```
┌─────────────────────────────────────────────────┐
│  Org Brief                        [↻ Refresh]   │
├─────────────────────────────────────────────────┤
│                                                  │
│  AT A GLANCE                                     │
│  • Considering Fund II ($50M) and Mountain       │
│    House co-invest ($10M)                        │
│  • Primary contact: John Kim, CIO                │
│  • Last interaction: March 12 (email)            │
│                                                  │
│  Future Fund is considering both a Fund II       │
│  investment and a Mountain House co-investment.  │
│  John Kim, CIO, has been the primary point of    │
│  contact...                                      │
│                                                  │
│  Last refreshed: Mar 17, 2026 by Oscar Vasquez   │
└─────────────────────────────────────────────────┘
```

- Same visual styling as the existing Prospect Briefing card (dark card, prose paragraphs)
- `at_a_glance` rendered as bullet list above narrative
- "Refresh" button triggers Claude API synthesis, replaces cached brief
- If no brief exists yet: show "No org brief yet. Click Refresh to generate." with the Refresh button
- "Last refreshed" line at bottom with timestamp and user who triggered it
- Empty state (no brief, no data): still allow refresh — the brief will synthesize whatever is available

### 5c. Org Notes Section

```
┌─────────────────────────────────────────────────┐
│  Notes                              [+ Add Note] │
├─────────────────────────────────────────────────┤
│  Mar 17, 2026 · Oscar Vasquez                    │
│  Spoke with John Kim — they want to see the      │
│  updated track record before next IC meeting.    │
│                                                  │
│  Mar 12, 2026 · Zach Reisner                     │
│  Sent credit comparison and index benchmarks.    │
└─────────────────────────────────────────────────┘
```

- Reverse chronological (newest first)
- "Add Note" button opens inline form (textarea + Save/Cancel), same UX as prospect notes
- User auto-populated from session (not editable)
- Timestamp auto-set on save

### 5d. Prospect Detail Page — Rename

- Change heading "Relationship Brief" → "Prospect Briefing" on `crm_prospect_detail.html`
- No other changes to prospect brief behavior

---

## 6. Integration Points

### Claude API — Org Brief Synthesis

New function in `brief_synthesizer.py` (or a new `org_brief_synthesizer.py` if cleaner):

**System prompt** (tuned for org-level voice):
```
You are a fundraising intelligence analyst for a real estate private equity firm
raising institutional capital. Generate a relationship brief for an organization
that may be considering multiple investment offerings.

Your brief MUST open with a sentence identifying which offerings the organization
is currently considering and at what stage/size.

Write in direct, specific prose. Use names, dates, and dollar amounts. No bullets
in the narrative — save structured info for at_a_glance. 2-4 paragraphs.

Respond with JSON only: {"narrative": "...", "at_a_glance": "..."}
at_a_glance should be 3-5 bullet points, newline-separated.
```

**Context block construction** — new function `collect_org_brief_context(org_id)`:
1. Org record (name, type)
2. All contacts (name, title, email)
3. All prospects for this org: for each, include offering name, stage, target, committed, urgency, assigned_to, next_action
4. All prospect briefs for this org's prospects (narrative text from `briefs` table)
5. All org notes (from `org_notes`, reverse chronological)
6. Recent interactions for the org (last 20)
7. Email history summary

### Existing Prospect Brief

No changes. Prospect briefs continue to work exactly as they do today, just renamed in the UI.

---

## 7. Constraints

- **Surgical changes only.** No refactoring of existing brief infrastructure.
- **No new libraries.** Uses existing `anthropic` SDK, same Claude model (`claude-sonnet-4-20250514`).
- **Same JSON contract** — `{narrative, at_a_glance}` with identical parse/fallback logic from `brief_synthesizer.py`.
- **Same caching pattern** — one cached brief per org, overwritten on refresh. No history of old briefs.
- **Auth:** Org brief refresh and note creation use `@login_required` (browser session), same as all other CRM routes.
- **Empty fields not rendered** — if org has no contacts, no prospects, etc., those context sections are omitted from the Claude prompt (not sent as empty).
- **Migration script required** — `scripts/migrate_add_org_briefs_notes.py` to create the two new tables. Must be idempotent (IF NOT EXISTS).
- **Claude model for org briefs:** `claude-sonnet-4-20250514`, max_tokens 1600 (same as prospect briefs).

---

## 8. Acceptance Criteria

1. Org detail page top card no longer renders a "Notes" subsection
2. New "Org Brief" section appears between Contacts and Prospects on org detail page
3. Org Brief "Refresh" button calls Claude API, synthesizes brief from all org context sources, and caches result in `org_briefs` table
4. Org Brief narrative opens with a sentence about which offerings the org is considering
5. Org Brief displays `at_a_glance` bullets + narrative prose + "last refreshed" attribution
6. New "Org Notes" section appears at bottom of org detail page
7. "Add Note" creates a timestamped entry with session user attribution in `org_notes` table
8. Notes display in reverse chronological order
9. Prospect detail page heading reads "Prospect Briefing" (not "Relationship Brief")
10. Migration script `migrate_add_org_briefs_notes.py` creates both tables idempotently
11. All new routes use `@login_required`
12. Existing prospect brief functionality is unchanged
13. Feedback loop prompt has been run

---

## 9. Files Likely Touched

### New files:
- `scripts/migrate_add_org_briefs_notes.py` — migration for `org_briefs` + `org_notes` tables

### Modified files:
- `app/models.py` — add `OrgBrief` and `OrgNote` model classes
- `app/sources/crm_db.py` — add functions: `get_org_brief()`, `upsert_org_brief()`, `get_org_notes()`, `add_org_note()`, `collect_org_brief_context()`
- `app/briefing/brief_synthesizer.py` — add `synthesize_org_brief()` with org-specific system prompt (or create `org_brief_synthesizer.py`)
- `app/delivery/crm_blueprint.py` — add routes: `GET /crm/org/<id>/brief/refresh` (POST), `POST /crm/org/<id>/notes`; modify org detail route to pass org brief + org notes to template
- `app/templates/crm_org_edit.html` — remove Notes from top card; add Org Brief section; add Org Notes section
- `app/templates/crm_prospect_detail.html` — rename "Relationship Brief" → "Prospect Briefing"
- `app/static/crm.css` — styling for org brief card and org notes (reuse prospect brief/notes patterns)
- `app/static/crm.js` — JS for org brief refresh button, add note form toggle
