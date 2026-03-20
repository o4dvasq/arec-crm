# SPEC: Audit JS Templates for Undefined Function Calls
**Project:** arec-crm | **Date:** 2026-03-20 | **Status:** Ready for implementation

---

## 1. Objective

A production bug was caused by `narrativeToHtml()` calling `markdownToHtml()` — a function that was never defined anywhere in the codebase. The JS silently threw a `ReferenceError` into a catch block, making brief rendering fail with no useful error. This was invisible in server logs (the server returned 200) and required manual debugging to find.

Audit all HTML templates and JS files in the app for similar issues: functions that are called but never defined, missing imports, and references to removed or renamed functions.

---

## 2. Scope

**In scope:**
- All `.html` templates in `app/templates/` — inline `<script>` blocks
- All `.js` files in `app/static/`
- Cross-file dependencies (e.g., a template calling a function defined in `crm.js` or `icons.js`)
- Python backend: check for calls to functions that don't exist in imported modules

**Out of scope:**
- Third-party libraries (jQuery, etc. — if any)
- CSS issues
- Logic bugs within existing functions

---

## 3. Audit Process

### Step 1: Extract all JS function calls from templates and static JS

For each `.html` file in `app/templates/` and each `.js` file in `app/static/`:
1. Extract all function CALLS — any identifier followed by `(` that isn't a keyword (`if`, `for`, `while`, `switch`, `catch`, `return`, `typeof`, `new`, `throw`)
2. Extract all function DEFINITIONS — `function name(`, `const name = (`, `const name = function`, `const name = async (`, arrow functions assigned to variables
3. Also extract method calls on known objects (e.g., `document.getElementById` is fine — it's a browser API)

### Step 2: Build a cross-file function registry

Combine all function definitions from:
- Each template's inline `<script>` blocks
- Each `.js` file in `app/static/`
- Browser built-ins (document, window, fetch, console, JSON, Math, Array, Object, String, Date, encodeURIComponent, parseInt, parseFloat, setTimeout, setInterval, alert, confirm, Promise, etc.)
- Jinja template functions/filters (these appear in `{{ }}` and `{% %}` blocks — skip these)

### Step 3: Flag undefined function calls

For each function call found in Step 1, check if it exists in the registry from Step 2. Flag any call where:
- The function is not defined in the same file
- The function is not defined in any loaded `.js` file (check `<script src="...">` tags to know which JS files each template loads)
- The function is not a browser built-in or Web API

### Step 4: Check Python backend too

Run a similar check on Python files in `app/`:
1. For each `.py` file, check that every function/method call references something that is either: defined in the same file, imported at the top, or a Python built-in
2. Pay special attention to cross-module calls (e.g., `crm_blueprint.py` importing from `crm_reader.py` — verify every imported name exists in the source module)

### Step 5: Check for stale references

Look for:
- `.backup` files in `app/templates/` that may indicate recent refactoring where functions were moved or renamed
- Git blame on any flagged lines to see if they were introduced in a recent commit
- Comments referencing function names that no longer exist

---

## 4. Known Issue (already fixed)

**`markdownToHtml`** — called in `crm_prospect_detail.html` line 1215 inside `narrativeToHtml()`, never defined. Fixed by Cowork on 2026-03-20 by adding the function definition. This was introduced during the brief redesign refactoring (commits around `9ebbb88` and `98e7967`).

---

## 5. Expected Output

Produce a report listing:

```
FILE: app/templates/crm_prospect_detail.html
  - [OK/FIXED] markdownToHtml() — was missing, fixed 2026-03-20
  - [FLAG] someOtherFunction() — called on line X, not defined anywhere

FILE: app/templates/crm_org_detail.html
  - [FLAG] ...

FILE: app/static/crm.js
  - (all clear)
```

For each flagged item, either:
1. Add the missing function definition
2. Remove the dead call
3. Replace with the correct function name if it was renamed

---

## 6. Acceptance Criteria

- [ ] Every function call in every `.html` template and `.js` file resolves to a definition
- [ ] Every Python import resolves to an actual function/class in the source module
- [ ] No `ReferenceError` thrown when loading any CRM page (test: Dashboard, Pipeline, Prospect Detail, Org Detail, People, Tasks)
- [ ] Report of all findings committed to `docs/` or output to console
- [ ] Any fixes are tested by loading the affected pages in a browser
