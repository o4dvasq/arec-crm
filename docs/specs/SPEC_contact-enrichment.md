# SPEC: Contact Enrichment

**Project:** arec-crm
**Date:** 2026-03-12
**Status:** Ready for implementation
**Priority:** Low (UI polish batch)
**Parallel group:** Can run simultaneously with Nav Redesign, Pipeline Polish, Prospect Detail, Tasks Page specs

---

## 1. Objective

Add an "Enrich Contact" button to the person detail page that performs automated intelligence gathering: web search, LinkedIn lookup, 30-day email scan for contact info in email footers, and Outlook contact lookup for missing details (phone number, email address).

## 2. Scope

**In scope:**
- "Enrich Contact" button on `crm_person_detail.html`
- New API route: `POST /crm/api/people/<slug>/enrich`
- Web search for the person's name + organization (use available search tools or APIs)
- LinkedIn profile discovery (search-based, not API — find the LinkedIn URL)
- 30-day email scan: search emails to/from this contact, parse email footers/signatures for phone numbers, titles, addresses
- Outlook contact lookup: check if the user's Outlook contacts have additional details for this person
- Auto-update the person record with any discovered information (phone, email, title, LinkedIn URL)
- Show enrichment results to the user before saving (preview + confirm pattern)

**Out of scope:**
- Paid enrichment APIs (Clearbit, ZoomInfo, etc.)
- Bulk enrichment of all contacts
- Changes to the nav bar or pipeline view

## 3. Business Rules

- **Do not overwrite existing data.** If the person already has a phone number and the enrichment finds a different one, present both to the user and let them choose.
- **Email footer parsing:** Look for patterns like phone numbers (xxx-xxx-xxxx, +1..., etc.), titles (VP, Director, Managing, Partner, etc.), and addresses in the last 10 lines of email bodies.
- **LinkedIn:** Search for `"{person name}" "{org name}" site:linkedin.com`. Extract the LinkedIn profile URL if found. Do NOT scrape LinkedIn pages.
- **Outlook contacts:** Use Graph API `GET /me/contacts` filtered by name or email. Pull phone numbers, job title, company name, addresses.
- **Enrichment should be idempotent** — running it twice should not create duplicate data.
- **Rate limiting:** Add a cooldown indicator. If enrichment was run in the last 24 hours, show "Last enriched: X hours ago" and still allow re-run.

## 4. Data Model / Schema Changes

Consider adding to the `contacts` table (or the underlying person storage):
- `linkedin_url` (TEXT, nullable) — LinkedIn profile URL
- `enriched_at` (TIMESTAMP, nullable) — when enrichment was last run
- `enrichment_source` (TEXT, nullable) — JSON blob of what was found and where

If these columns don't exist, create a migration script (`scripts/migrate_add_enrichment_columns.py`).

Alternatively, if the contacts table already has flexible fields or a JSON column, use that.

## 5. UI / Interface

### Enrich Contact Button
Location: Person detail page header, next to any existing action buttons.
- Button label: "Enrich Contact"
- Icon: Lucide `sparkles` or `search`
- Style: `.btn-secondary` (matches existing button style)

### Enrichment Flow
1. User clicks "Enrich Contact"
2. Button shows loading spinner: "Enriching..."
3. Backend runs enrichment pipeline (web search → email scan → Outlook lookup)
4. Returns results as a preview card:
   ```
   ENRICHMENT RESULTS
   ─────────────────────
   LinkedIn: linkedin.com/in/john-smith (NEW)
   Phone: (415) 555-1234 (from email footer)
   Title: Managing Director (from Outlook)
   Email: john@acmecorp.com (confirmed)
   ─────────────────────
   [Save Changes] [Dismiss]
   ```
5. User clicks "Save Changes" to apply, or "Dismiss" to skip.

### Enrichment History
Below the button, show: "Last enriched: Mar 10, 2026" (if applicable).

## 6. Integration Points

- **Web search:** Use a server-side web search (e.g., `requests` to a search API, or use the existing Anthropic tooling if available in the app). If no search API is configured, skip this step gracefully.
- **Email scan:** Use `ms_graph.py` to search emails. Filter by sender/recipient matching the contact's email(s). Parse the last 10 lines of each email body for signature data.
- **Outlook contacts:** Use Graph API `GET /me/contacts?$filter=displayName eq '{name}'` via `ms_graph.py`.
- **Person record update:** Use `update_contact_fields()` from `crm_db.py`.
- **Graph API token:** Requires the current user to have `graph_consent_granted=True`. If not, show message: "Email enrichment requires Graph API consent."

## 7. Constraints

- Must use `@login_required` on the new route.
- All Graph API calls must use the current user's token (multi-user aware).
- Web search should have a timeout (10 seconds max) to avoid hanging the UI.
- Email footer parsing is best-effort — false positives are acceptable since the user reviews before saving.
- Do NOT store raw email content — only extract and store structured fields (phone, title, etc.).
- The enrichment endpoint should return results as JSON, and the frontend renders the preview. Do not auto-save.

## 8. Acceptance Criteria

- [ ] "Enrich Contact" button visible on person detail page
- [ ] Clicking the button triggers the enrichment pipeline
- [ ] Loading state shown while enrichment runs
- [ ] Results displayed as a preview card (not auto-saved)
- [ ] User can accept (save) or dismiss enrichment results
- [ ] Email footer parsing extracts phone numbers and titles from recent emails
- [ ] Outlook contact lookup finds additional details if available
- [ ] LinkedIn URL discovered via web search (if available)
- [ ] Existing data is not overwritten without user confirmation
- [ ] Enrichment timestamp recorded (`enriched_at`)
- [ ] Graceful degradation if Graph API consent not granted
- [ ] All 99+ tests pass (add tests for enrichment route)
- [ ] Feedback loop prompt has been run

## 9. Files Likely Touched

| File | Reason |
|------|--------|
| `app/templates/crm_person_detail.html` | Add Enrich Contact button + results preview UI |
| `app/delivery/crm_blueprint.py` | New route: `POST /crm/api/people/<slug>/enrich` |
| `app/sources/crm_db.py` | Add `enriched_at`/`linkedin_url` field support if needed. Update `update_contact_fields()` if needed. |
| `app/sources/ms_graph.py` | Add Outlook contact lookup function. Add email search for footer parsing. |
| `app/models.py` | Add `linkedin_url`, `enriched_at`, `enrichment_source` columns to contacts model if needed |
| `scripts/migrate_add_enrichment_columns.py` | **New file** — migration for new columns |
| `app/tests/test_crm_db.py` | Add tests for enrichment route and data handling |
