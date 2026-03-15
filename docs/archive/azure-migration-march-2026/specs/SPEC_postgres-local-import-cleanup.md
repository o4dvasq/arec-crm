# SPEC: Postgres-Local Import Cleanup (Follow-up to Branch 1)

**Project:** arec-crm
**Date:** 2026-03-14
**Status:** Ready for implementation
**Prerequisite:** SPEC_postgres-local.md must be implemented first (it is)

---

## Objective

The initial postgres-local implementation correctly swapped imports in the three delivery files (`dashboard.py`, `crm_blueprint.py` top-level, `tasks_blueprint.py`). But several other production files still contain inline `from sources.crm_reader import ...` statements that will crash at runtime when those code paths are hit. This spec fixes all remaining crm_reader imports in production code.

---

## Scope

Five files need changes. Two are critical (brief synthesis will crash without them), one is a Graph API route that should be disabled, and two are supporting modules.

### Explicitly Out of Scope

- `app/main.py` — old Flask entry point from before the crm_blueprint extraction. Not used on this branch (dashboard.py is the entry point). Leave as-is.
- `app/scripts/migrate_assignee_tasks.py`, `app/scripts/migrate_urgency.py`, `app/scripts/bootstrap_contacts_index.py` — one-time migration scripts, not production code. Leave as-is.
- `app/sources/crm_graph_sync.py` — Graph API sync module. No Graph API on this branch. See File 5 below for how to handle it.

---

## File 1: `app/sources/relationship_brief.py` (CRITICAL)

This file has 5 inline imports from crm_reader across 3 functions. All must switch to crm_db.

### Change 1a — `collect_relationship_data()` (line 195)

```python
# BEFORE (line 195-198):
    from sources.crm_reader import (
        get_prospect, get_organization, get_contacts_for_org,
        load_interactions, get_emails_for_org,
    )

# AFTER:
    from sources.crm_db import (
        get_prospect, get_organization, get_contacts_for_org,
        load_interactions, get_emails_for_org,
    )
```

### Change 1b — `collect_relationship_data()` (line 232)

```python
# BEFORE (line 232):
    from sources.crm_reader import load_prospect_notes, load_prospect_meetings

# AFTER:
    from sources.crm_db import load_prospect_notes, load_prospect_meetings
```

**Verify:** `crm_db.py` must export both `load_prospect_notes` and `load_prospect_meetings`. Check that these functions exist. If `load_prospect_meetings` does not exist in `crm_db.py`, you need to add it — it should query the `prospect_meetings` JSON file (still file-backed per CLAUDE.md: "prospect_meetings: Still JSON file-backed") or return an empty list if the JSON file doesn't exist. The function signature in crm_reader is: `load_prospect_meetings(org: str, offering: str) -> list`.

### Change 1c — `get_email_history_for_person()` (line 608)

```python
# BEFORE (line 608):
    from sources.crm_reader import get_emails_for_org

# AFTER:
    from sources.crm_db import get_emails_for_org
```

### Change 1d — `collect_person_data()` (line 663)

```python
# BEFORE (line 663-665):
    from sources.crm_reader import (
        get_organization, get_prospects_for_org, load_interactions,
    )

# AFTER:
    from sources.crm_db import (
        get_organization, get_prospects_for_org, load_interactions,
    )
```

### Change 1e — `execute_person_updates()` (line 852)

```python
# BEFORE (line 852-855):
    from sources.crm_reader import (
        update_contact_fields, get_prospects_for_org,
        update_prospect_field, append_interaction,
    )

# AFTER:
    from sources.crm_db import (
        update_contact_fields, get_prospects_for_org,
        update_prospect_field, append_interaction,
    )
```

---

## File 2: `app/briefing/prompt_builder.py` (CRITICAL)

This file has 2 imports from crm_reader. The morning briefing will crash without this fix.

### Change 2a — top-level import (line 9)

```python
# BEFORE (line 9):
from sources.crm_reader import load_interactions, load_prospects

# AFTER:
from sources.crm_db import load_interactions, load_prospects
```

### Change 2b — inline import in `_matches_event()` (line 60)

```python
# BEFORE (line 60):
        from sources.crm_reader import find_person_by_email, get_contacts_for_org

# AFTER:
        from sources.crm_db import find_person_by_email, get_contacts_for_org
```

**Verify:** `crm_db.py` must export `find_person_by_email`. Check that this function exists and returns the same shape as crm_reader's version (a dict with keys like `name`, `organization`, `email`, `role`, etc., or None).

---

## File 3: `app/delivery/crm_blueprint.py` line 443 (Graph API route)

This is the `api_prospect_email_scan` route which calls MS Graph. Graph API is out of scope for this branch. Two options — pick the simpler one:

**Option A (preferred): Swap the import and let it fail gracefully at the Graph auth step.**

```python
# BEFORE (line 443):
    from sources.crm_reader import get_org_domains, add_emails_to_log

# AFTER:
    from sources.crm_db import get_org_domains, add_emails_to_log
```

**Verify:** `crm_db.py` must export `get_org_domains` and `add_emails_to_log`. If either is missing, add a stub that returns an empty dict / 0 respectively.

**Option B: Short-circuit the route entirely.**

```python
@crm_bp.route('/api/prospect/<offering>/<path:org>/email-scan', methods=['POST'])
def api_prospect_email_scan(offering, org):
    """Disabled on postgres-local branch (no Graph API)."""
    return jsonify({'error': 'Email scanning requires Graph API (not available on this branch)', 'added': 0}), 501
```

---

## File 4: `app/sources/crm_graph_sync.py`

This entire module depends on Graph API (`ms_graph.py`, `auth/graph_auth.py`) which doesn't exist on this branch. Do NOT fix the imports — instead, ensure nothing imports it. Currently only one place does:

```
app/delivery/crm_blueprint.py:1287:  from sources.crm_graph_sync import run_auto_capture
```

This is inside the `/api/auto-capture` POST route. Short-circuit that route the same way:

```python
# Find the route handler for /api/auto-capture and replace its body:
@crm_bp.route('/api/auto-capture', methods=['POST'])
def api_auto_capture():
    """Disabled on postgres-local branch (no Graph API)."""
    return jsonify({'error': 'Auto-capture requires Graph API (not available on this branch)', 'added': 0}), 501
```

---

## File 5: Functions to verify exist in `crm_db.py`

Before making the import swaps, confirm these functions are exported from `crm_db.py`. If any are missing, add them.

| Function | Used by | Expected signature | Expected return |
|----------|---------|-------------------|-----------------|
| `load_prospect_meetings` | relationship_brief.py | `(org: str, offering: str) -> list` | List of meeting dicts, or `[]` |
| `save_prospect_meeting` | crm_blueprint.py (line 39) | `(org: str, offering: str, meeting: dict) -> dict` | The saved meeting dict |
| `find_person_by_email` | prompt_builder.py | `(email: str) -> dict or None` | Person dict or None |
| `get_org_domains` | crm_blueprint.py | `(prospect_only: bool = False) -> dict` | `{org_name: domain_string}` |
| `add_emails_to_log` | crm_blueprint.py | `(emails: list[dict]) -> int` | Count of emails added |

If `load_prospect_meetings` or `save_prospect_meeting` don't exist, implement them as JSON file-backed (reading/writing `crm/prospect_meetings.json`) since CLAUDE.md states meetings are still file-backed.

---

## Acceptance Criteria

1. `grep -r "from sources.crm_reader" app/delivery/ app/sources/relationship_brief.py app/briefing/` returns zero results
2. `grep -r "from sources.crm_reader" app/sources/crm_graph_sync.py` — this file is untouched but nothing imports it
3. Brief synthesis works end-to-end: clicking "Generate Brief" on a prospect detail page calls Claude and saves the result
4. Person brief synthesis works: the collect_person_data → build_person_context_block path completes without import errors
5. The morning briefing (`prompt_builder.py`) builds prompts without import errors
6. `/api/prospect/.../email-scan` and `/api/auto-capture` return 501 with clear messages instead of crashing
7. All 52 existing tests still pass
8. Feedback loop: after fixing, do `python -c "from sources.relationship_brief import collect_relationship_data, collect_person_data; print('OK')"` and `python -c "from briefing.prompt_builder import build_prompt; print('OK')"` from the `app/` directory to confirm imports resolve

---

## Files Touched

| File | Action | Changes |
|------|--------|---------|
| `app/sources/relationship_brief.py` | Edit | 5 inline imports: `crm_reader` → `crm_db` |
| `app/briefing/prompt_builder.py` | Edit | 2 imports: `crm_reader` → `crm_db` (1 top-level, 1 inline) |
| `app/delivery/crm_blueprint.py` | Edit | Line 443: swap import or short-circuit route; line ~1287: short-circuit auto-capture route |
| `app/sources/crm_db.py` | Edit (if needed) | Add missing functions: `load_prospect_meetings`, `save_prospect_meeting`, `get_org_domains`, `add_emails_to_log`, `find_person_by_email` if any are absent |
