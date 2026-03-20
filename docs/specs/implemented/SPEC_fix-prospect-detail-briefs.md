# SPEC: Fix Prospect Detail Brief Loading & Generation
**Project:** arec-crm | **Date:** 2026-03-20 | **Status:** Ready for implementation

---

## 1. Objective

Two brief-related bugs on the Prospect Detail page are affecting all (or most) prospects. The Prospect Brief "Generate" button fails immediately, and the Org Brief section shows empty even when a valid org brief exists in `briefs.json`. Both bugs likely share a single root cause: the `loadPageData()` JS function fails before `loadProspectBrief()` and `loadOrgBrief()` can execute.

---

## 2. Symptoms

**Bug A — Prospect Brief generation fails instantly:**
- User clicks "⟳ Generate" on the Prospect Detail page
- Button immediately returns to "No prospect brief yet. Click generate." with no loading state visible
- Observed on: MetLife Insurance Company, Mass Mutual Life Insurance Co., and multiple other prospects
- The POST to `/crm/api/prospect/{offering}/{org}/prospect-brief` appears to return 500 or never fire

**Bug B — Org Brief shows empty on Prospect Detail:**
- Prospect Detail page always shows "No org brief yet. Generate one from the Org page."
- Org brief DOES exist — visible and regeneratable on the Org Detail page
- After regenerating the org brief on the Org page and returning to Prospect Detail, still empty
- The server-side Jinja rendering at lines 860-864 SHOULD show the brief, but the JS `loadOrgBrief()` never fires to refresh it, AND the server-rendered content may be getting overridden

**Working correctly:**
- Org brief generation on the Org Detail/Edit page works fine (POST to `/crm/api/synthesize-org-brief`)
- At A Glance on the pipeline page displays correctly
- The Claude API key and `call_claude_brief()` function work (proven by org brief generation succeeding)

---

## 3. Root Cause Analysis

### Primary Theory: `loadPageData()` cascade failure

In `crm_prospect_detail.html` line 1063, the `loadPageData()` function does:

```javascript
async function loadPageData() {
    try {
        const resp = await fetch(
            `/crm/api/prospect/${enc(OFFERING)}/${enc(ORG)}/brief`
        );
        if (!resp.ok) throw new Error('Brief API failed');  // <-- LINE 1068
        const data = await resp.json();

        renderInteractions(data.interactions);
        renderMeetings(data.meeting_summaries);
        // ...

        loadProspectBrief();   // <-- LINE 1079: NEVER REACHED if above throws
        loadOrgBrief();        // <-- LINE 1082: NEVER REACHED if above throws

    } catch (err) {
        console.error('Page data load failed:', err);  // <-- silent failure
    }
}
```

If the GET to `/crm/api/prospect/{offering}/{org}/brief` returns a 500, `loadProspectBrief()` and `loadOrgBrief()` are NEVER called. This single failure explains both bugs.

The server-rendered Jinja content (lines 834-849, 860-867) should provide a fallback, but this was only recently added (commit `9ebbb88`). If `loadPageData()` overwrites the DOM before failing, or if there's a timing issue with the initial render, the server content may not be visible.

### What's causing the GET `/brief` to fail?

The route at line 434 (`api_prospect_brief`) calls `collect_relationship_data(org, offering)` inside a try/except, then serializes the response with `jsonify(**raw_data, ...)`. Possible failure points:

1. **Serialization failure** — `raw_data` contains non-JSON-serializable types (unlikely — tested OK offline but Flask's jsonify may behave differently than `json.dumps`)
2. **Import or runtime error** in a recently-changed function (e.g., `load_prospect_meetings`, `load_prospect_notes` added in recent commits)
3. **Exception outside the try/except** — lines 443-453 have no exception handling around `compute_content_hash`, `load_saved_brief`, or the `jsonify` call itself

### Secondary issue: `refreshProspectBrief()` failure

Even if `loadPageData()` is fixed, the "Generate" button calls `refreshProspectBrief()` which POSTs to the `/prospect-brief` endpoint. This calls `_run_focused_prospect_brief()` → `call_claude_brief()` with `want_json=True`. The org brief route uses `want_json=False` and works. If the failure is instant (no loading spinner visible), the error is before the Claude API call, likely in `collect_relationship_data` or an unhandled exception in the route.

---

## 4. Debugging Steps (run with CRM server active)

### Step 1: Check the server console
Start the CRM (`python3 app/delivery/dashboard.py`), navigate to any prospect detail page, and look for error output in the terminal. The `[brief]` or `[prospect-brief]` prefix will identify the failing route.

### Step 2: Test the GET brief endpoint directly
```bash
curl -s "http://localhost:8000/crm/api/prospect/AREC%20Debt%20Fund%20II/MetLife%20Insurance%20Company/brief" | python3 -m json.tool | head -20
```
If this returns 500, the response body and server console will show the traceback.

### Step 3: Test the POST prospect-brief endpoint directly
```bash
curl -s -X POST "http://localhost:8000/crm/api/prospect/AREC%20Debt%20Fund%20II/MetLife%20Insurance%20Company/prospect-brief" | python3 -m json.tool
```

### Step 4: Check browser console
Open the prospect detail page with DevTools → Console open. Look for "Page data load failed:" or "Prospect brief refresh error:" messages.

---

## 5. Fixes Required

### Fix 1: Make `loadPageData()` resilient (CRITICAL)
`loadProspectBrief()` and `loadOrgBrief()` must ALWAYS execute regardless of whether the main brief data fetch succeeds. Move them outside the try block or into a `finally` block:

```javascript
async function loadPageData() {
    try {
        const resp = await fetch(
            `/crm/api/prospect/${enc(OFFERING)}/${enc(ORG)}/brief`
        );
        if (!resp.ok) throw new Error('Brief API failed');
        const data = await resp.json();
        loadTasks();
        renderInteractions(data.interactions);
        renderMeetings(data.meeting_summaries);
        renderEmails(data.email_history);
        renderNotesLog(data.notes_log || []);
    } catch (err) {
        console.error('Page data load failed:', err);
    }

    // ALWAYS load briefs — independent of main data fetch
    loadProspectBrief();
    loadOrgBrief();
}
```

### Fix 2: Add exception handling around the full GET brief response (line 434)
Wrap the entire response construction in try/except, not just `collect_relationship_data`:

```python
@crm_bp.route('/api/prospect/<offering>/<path:org>/brief', methods=['GET', 'POST'])
def api_prospect_brief(offering, org):
    if request.method == 'GET':
        try:
            raw_data = collect_relationship_data(org, offering, base_dir=PROJECT_ROOT)
        except Exception as e:
            print(f"[brief] GET collect_relationship_data failed for {org}: {e}")
            raw_data = {}
        try:
            content_hash = compute_content_hash(raw_data)
            brief_key = f"{org}::{offering}"
            saved = load_saved_brief('prospect', brief_key)
            prospect = raw_data.get('prospect', {})
            return jsonify({
                **raw_data,
                'content_hash': content_hash,
                'saved_brief': saved,
                'relationship_brief': prospect.get('Relationship Brief', ''),
                'brief_refreshed': prospect.get('Brief Refreshed', ''),
            })
        except Exception as e:
            print(f"[brief] GET response build failed for {org}: {e}")
            import traceback; traceback.print_exc()
            return jsonify({'error': str(e)}), 500
```

### Fix 3: Identify and fix the actual server-side exception
After steps 1-4 in the debugging section, identify the specific exception causing the 500 and fix it. Common candidates:
- A non-serializable type in `raw_data` (datetime, set, etc.)
- An import-time or runtime error in `load_prospect_meetings` or `load_prospect_notes`
- A file read error in one of the relationship_brief.py helper functions

### Fix 4: Ensure `refreshProspectBrief()` shows errors to the user
Currently the catch block silently reverts to the placeholder. Show a brief error message instead:

```javascript
} catch (err) {
    console.error('Prospect brief refresh error:', err);
    document.getElementById('prospect-brief').innerHTML = `
        <div class="brief-header">
            <div class="section-title">Prospect Brief</div>
            <button class="btn-refresh" onclick="refreshProspectBrief()">⟳ Retry</button>
        </div>
        <div style="color:var(--warning);font-size:13px;padding:0.75rem 0;">
            Brief generation failed. Check server console for details.
        </div>
    `;
}
```

---

## 6. Data Model / Schema Changes

None — this is a bug fix only.

---

## 7. UI / Interface

No new UI elements. Fix 4 adds an error state message to the prospect brief card when generation fails (replacing the ambiguous "No prospect brief yet" placeholder).

---

## 8. Integration Points

- `crm_blueprint.py` — routes at lines 434, 517
- `crm_prospect_detail.html` — JS functions `loadPageData()`, `refreshProspectBrief()`, `loadOrgBrief()`
- `relationship_brief.py` — `collect_relationship_data()` (verify all return types are JSON-serializable)
- `brief_synthesizer.py` — `call_claude_brief()` (verify error handling with `want_json=True`)

---

## 9. Constraints

- Do not change the brief data format or storage (`briefs.json`)
- Do not change the Claude API model or prompt content
- Org brief generation on the Org page must continue working as-is
- Server-side Jinja rendering of briefs (added in `9ebbb88`) should remain as a fallback

---

## 10. Acceptance Criteria

- [ ] Prospect Detail page loads org brief correctly when one exists in `briefs.json`
- [ ] Prospect Detail page loads prospect brief correctly when one exists in `briefs.json`
- [ ] "Generate" button on prospect brief shows loading state, calls Claude API, and renders the result
- [ ] If brief generation fails, user sees an error message (not the ambiguous "no brief yet" placeholder)
- [ ] `loadOrgBrief()` and `loadProspectBrief()` execute even if the main `/brief` GET endpoint fails
- [ ] Tested on at least 3 prospects: MetLife Insurance Company, Mass Mutual Life Insurance Co., and one other
- [ ] Feedback loop prompt has been run

---

## 11. Files Likely Touched

- `app/templates/crm_prospect_detail.html` — Fix 1 (loadPageData resilience), Fix 4 (error state)
- `app/delivery/crm_blueprint.py` — Fix 2 (exception handling), Fix 3 (root cause)
- Possibly `app/sources/relationship_brief.py` — if `collect_relationship_data` returns non-serializable types
