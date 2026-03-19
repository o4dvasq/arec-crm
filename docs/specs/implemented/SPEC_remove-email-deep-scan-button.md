SPEC: Remove Email Deep Scan Button | Project: arec-crm | Date: 2026-03-19 | Status: Ready for implementation

## 1. Objective

Remove the per-prospect "Deep Scan (90d)" button from the prospect detail page. This functionality is now replaced by the Cowork `/email-scan` skill, which performs a comprehensive 6-pass scan across all mailboxes in a single run rather than per-org on-demand scans. Keeping the button creates confusion about which scan mechanism is authoritative and wastes Claude API credits on per-email Haiku summarization.

## 2. Scope

- Remove the Deep Scan button UI (HTML + CSS + JS)
- Remove the Flask route handler and any supporting functions
- Do NOT remove the email history display itself — that stays
- Do NOT remove email_log.json reading logic — the brief endpoint still needs it

## 3. Business Rules

- Email scanning is now handled exclusively by the `/email-scan` Cowork skill
- The email_log.json file remains the single source of truth for email history
- No per-prospect scanning capability needed going forward

## 4. Data Model / Schema Changes

None. email_log.json schema is unchanged. Existing entries with `matchType: "deep-scan"` remain valid.

## 5. UI / Interface

### Remove from `app/templates/crm_prospect_detail.html`:

**CSS (lines ~385-407):** Remove the `.btn-scan`, `.btn-scan:hover`, `.btn-scan:disabled`, `.scan-status`, `.scan-status.running`, `.scan-status.success`, `.scan-status.error` style rules.

**HTML (lines ~912-917):** Remove the button and status span from the Email History section header. Keep the collapsible toggle. Before:
```html
<div style="display:flex;align-items:center;gap:6px;" onclick="event.stopPropagation()">
    <button class="btn-scan" id="deep-scan-btn" onclick="runDeepEmailScan()">
        ⟳ Deep Scan (90d)
    </button>
    <span class="scan-status hidden" id="scan-status"></span>
    <span class="collapsible-toggle" id="emails-toggle" onclick="toggleSection('emails')" style="cursor:pointer">▼</span>
</div>
```
After:
```html
<span class="collapsible-toggle" id="emails-toggle" onclick="toggleSection('emails')" style="cursor:pointer">▼</span>
```

**JavaScript (lines ~1626-1662):** Remove the entire `runDeepEmailScan()` function.

### Remove from `app/delivery/crm_blueprint.py`:

**Route (lines ~479-608+):** Remove the entire `api_prospect_email_scan()` function and its `@crm_bp.route('/api/prospect/<offering>/<path:org>/email-scan', methods=['POST'])` decorator.

Also remove any imports that become unused after this removal (check `get_contacts_for_org`, `search_emails_deep`, `load_crm_config` if they're only used here).

### Check for removal in `app/sources/ms_graph.py`:

If `search_emails_deep()` exists and is only called from the removed route, remove it as well.

## 6. Integration Points

- No external integrations affected
- The `/email-scan` Cowork skill writes directly to `crm/email_log.json` — no Flask route needed

## 7. Constraints

- Do not break the email history display — it reads from the brief endpoint, not the scan endpoint
- Do not remove `email_log.json` reading logic from `crm_reader.py`
- Preserve existing `matchType: "deep-scan"` entries in the log — they're still valid historical data

## 8. Acceptance Criteria

- [ ] Deep Scan button no longer appears on prospect detail page
- [ ] `/crm/api/prospect/{offering}/{org}/email-scan` route returns 404
- [ ] Email History section still renders correctly with existing email_log.json data
- [ ] No orphaned CSS classes or JS functions remain
- [ ] `python3.12 -m pytest app/tests/ -v --tb=short` passes
- [ ] Feedback loop prompt has been run

## 9. Files Likely Touched

- `app/templates/crm_prospect_detail.html` — Remove button HTML, CSS, and JS function
- `app/delivery/crm_blueprint.py` — Remove route handler
- `app/sources/ms_graph.py` — Remove `search_emails_deep()` if orphaned
