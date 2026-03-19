SPEC: Prospect & Org Redesign — Implementation Fixes | Project: arec-crm | Date: 2026-03-19 | Status: Ready for implementation

---

## 1. Objective

Fix implementation bugs from the Prospect & Org Detail Page Redesign. The structural layout is correct but several visual and behavioral issues need to be resolved: color sidebar bars are not rendering, brief sections are auto-generating instead of loading from cache, and the meeting log may not be visible on the org page.

---

## 2. Scope

### In Scope

- Fix color sidebar bars not rendering on cards (CSS specificity issue)
- Fix org brief auto-synthesis — must show "Generate" button instead
- Fix prospect detail briefs — neither should auto-generate on page load
- Ensure meeting summaries section is visible on org detail page
- Verify org brief on prospect detail is read-only (loaded from cache, never synthesized)

### Out of Scope

- Layout/ordering changes (already correct)
- New features
- Data model changes

---

## 3. Bug Fixes

### A. Color Sidebar Bars Not Rendering

**Symptom:** Cards on both pages show no colored left/right borders despite having `.card-native` and `.card-crossref` classes applied.

**Root cause:** Each template has an inline `<style>` block that defines `.card` with explicit `border` properties. Inline styles have equal specificity to the external `crm.css`, but the inline block loads after the external stylesheet, overriding the border definitions.

**Fix:** In BOTH `crm_prospect_detail.html` and `crm_org_edit.html`, locate the inline `<style>` block's `.card` rule. It likely has something like:

```css
.card { background: #1e293b; border: 1px solid #334155; border-radius: 8px; ... }
```

The `border: 1px solid #334155` shorthand resets ALL four borders, wiping out the left/right colored borders set by `.card-native` and `.card-crossref` in `crm.css`.

**Solution (choose one, option 1 preferred):**

**Option 1 — Use `!important` in crm.css** (simplest, least risk):
```css
.card-native {
  border-left: 4px solid #22c55e !important;
}
.card-crossref {
  border-right: 4px solid #2563eb !important;
  border-left: none !important;
}
```

**Option 2 — Fix inline styles in both templates:**
Replace the `.card` border shorthand with explicit sides:
```css
.card {
  background: #1e293b;
  border-top: 1px solid #334155;
  border-bottom: 1px solid #334155;
  border-left: 1px solid #334155;
  border-right: 1px solid #334155;
  border-radius: 8px;
  ...
}
```
This allows `.card-native` and `.card-crossref` to override individual sides without fighting the shorthand.

**Verification:** After the fix, visually confirm:
- Prospect Detail: top prospect card has green bar on left. Org info card, org brief, meetings, emails have blue bar on right.
- Org Detail: top org card has green bar on left. Prospect cards have blue bar on right. Org brief, meetings, notes, emails have green bar on left.

---

### B. Org Brief Auto-Synthesizes on Org Detail Page

**Symptom:** When visiting an org that has no cached org brief, the page shows "Loading brief..." and automatically calls `POST /crm/api/synthesize-org-brief` to generate one.

**Current code (crm_org_edit.html, ~line 405-419):**
```javascript
async function loadOrgBrief() {
  // ...
  if (saved && saved.narrative) {
    renderOrgBrief(saved.narrative, saved.generated_at);
  } else {
    showBriefLoading();        // ← shows spinner
    await _synthesizeOrgBrief(); // ← auto-generates!
  }
}
```

**Required behavior:** If no cached brief exists, show a static empty state with a "Generate" button. NEVER auto-synthesize.

**Fix:** Replace the `else` branch:
```javascript
async function loadOrgBrief() {
  try {
    const resp = await fetch(`/crm/api/org/${encodeURIComponent(ORG_NAME)}`);
    const data = await resp.json();
    const saved = data.saved_brief;
    if (saved && saved.narrative) {
      renderOrgBrief(saved.narrative, saved.generated_at);
    } else {
      renderOrgBriefEmpty();  // ← show empty state with Generate button
    }
  } catch (err) {
    renderOrgBriefError();
  }
}

function renderOrgBriefEmpty() {
  const container = document.getElementById('org-brief');
  container.innerHTML = `
    <div class="brief-header">
      <span class="brief-title">ORG BRIEF</span>
      <button class="btn-sm" onclick="refreshOrgBrief()">⟳ Generate</button>
    </div>
    <p style="color:#94a3b8;font-size:14px;">No org brief yet. Click Generate to create one.</p>
  `;
}
```

The `refreshOrgBrief()` function (which calls `_synthesizeOrgBrief()`) remains unchanged — it is only triggered by the user clicking the button.

---

### C. Prospect Detail — Org Brief Must Not Synthesize

**Symptom:** On the prospect detail page, the Org Brief card shows "Loading brief..." and may be triggering synthesis.

**Required behavior:** The Org Brief section on the prospect page is READ-ONLY. It fetches the cached org brief via GET only. If no cached org brief exists, it shows: "No org brief yet. Generate one from the Org page." with a link to the org page. It NEVER calls the synthesis endpoint.

**Fix:** In `crm_prospect_detail.html`, the `loadOrgBrief()` function must:
1. Call `GET /crm/api/org/{name}` to fetch org data (including `saved_brief`)
2. If `saved_brief.narrative` exists → render it read-only
3. If not → show static message with link to org page
4. **NEVER** call `POST /crm/api/synthesize-org-brief` or any synthesis endpoint

Verify that `loadOrgBrief()` in the prospect template does NOT contain any POST/synthesis calls. If it does, remove them entirely. The only POST-capable brief function on this page should be `refreshProspectBrief()` for the Prospect Brief section.

---

### D. Prospect Detail — Prospect Brief Must Not Auto-Generate

**Symptom:** Prospect brief may be showing a loading state or auto-generating on page load.

**Required behavior:** On page load, fetch cached prospect brief via GET. If cached → render. If not cached → show "No prospect brief yet." with a "Generate" button. NEVER auto-generate.

**Verify:** Check `loadProspectBrief()` in `crm_prospect_detail.html`. The code exploration suggests this is already correct (shows Generate button when empty), but confirm there's no code path that triggers a POST on page load. If the GET endpoint itself triggers synthesis server-side, that's also a bug — the GET endpoint must ONLY return cached data from `briefs.json`.

Also check the server-side route handler:
```
GET /crm/api/prospect/<offering>/<org>/prospect-brief
```
This route must ONLY read from `briefs.json` and return whatever is cached (or empty `{}`). It must NOT call any synthesis/AI function.

---

### E. Meeting Summaries Not Visible on Org Detail

**Symptom:** The meeting summaries section may not be showing on the org detail page.

**Current code:** The meetings card starts with `class="hidden"` and is only unhidden if meetings are found by `loadMeetings()`.

**Debug steps:**
1. Check if `loadMeetings()` is called on page load in `crm_org_edit.html`. Search for it in the `DOMContentLoaded` or direct script calls at the bottom.
2. Check if the API endpoint it calls actually returns meetings for this org.
3. If `loadMeetings()` is not being called, add it to the page load sequence.
4. If it IS being called but returning empty, check that it's querying by org name correctly (the org name must match what's in `prospect_meetings.json` or `meetings.json`).

**Fix (if loadMeetings is missing from page load):**
Add to the page load script:
```javascript
loadMeetings();
```

Alongside the other load calls (loadOrgBrief, loadOrgNotes, etc.).

---

## 4. Acceptance Criteria

- [ ] Green left-border bars are visually visible on native cards (both pages)
- [ ] Blue right-border bars are visually visible on cross-reference cards (both pages)
- [ ] Org brief on org detail shows "Generate" button when no cached brief exists — does NOT auto-synthesize
- [ ] Org brief on prospect detail is strictly read-only — loads from cache, shows "Generate from Org page" message if none exists, NEVER triggers synthesis
- [ ] Prospect brief on prospect detail shows "Generate" button when no cached brief exists — does NOT auto-synthesize on page load
- [ ] GET endpoints for briefs return cached data ONLY — no server-side synthesis
- [ ] Meeting summaries section is visible on org detail page when meetings exist for that org
- [ ] No loading spinners appear on page load for any brief section — either show cached content or show empty state with Generate button
- [ ] No regressions in existing tests (`python3 -m pytest app/tests/ -v` passes)
- [ ] Kill and restart the app, then visually verify all fixes on at least one org/prospect pair
- [ ] Feedback loop prompt has been run

---

## 5. Files Likely Touched

| File | Changes |
|------|---------|
| `static/crm.css` | Add `!important` to `.card-native` and `.card-crossref` border rules (or increase specificity) |
| `app/templates/crm_org_edit.html` | Fix `loadOrgBrief()` to show empty state instead of auto-synthesizing. Verify `loadMeetings()` is called on page load. |
| `app/templates/crm_prospect_detail.html` | Verify `loadOrgBrief()` is read-only (no POST calls). Verify `loadProspectBrief()` doesn't auto-generate. |
| `app/delivery/crm_blueprint.py` | Verify GET endpoints for prospect-brief and org brief only return cached data, no synthesis. |
