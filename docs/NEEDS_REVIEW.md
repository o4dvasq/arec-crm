# Needs Review

Items skipped during Phase 2 safe cleanup. Each requires manual analysis before acting.

---

## 1. crm/ai_inbox_queue.md — Not Deleted (Live Data)

**Why skipped:** Audit labeled this file dead (superseded by drain_inbox.py flow), but the file contains ~15 pending CRM items with real investor intelligence: SMTB Mar 16 calls, Blackstone NYC meeting, Future Fund agenda, Nomura facility negotiation, Starwood status, Jim Steinbugl (PSU) outreach, Phillips & Co referral thread.

**Recommended action:** Process the pending items through `/crm:inbox` or migrate them to `crm/interactions.md` and `TASKS.md`, then delete the file once empty.

---

## 2. Brief Synthesis — Near-Duplicate Logic (3 implementations)

**Location:** `app/delivery/dashboard.py`

| Function | Lines | Scope |
|----------|-------|-------|
| `_synthesize_and_persist_brief()` | ~72 | Prospect-level brief; persists to prospects.md |
| `api_synthesize_brief()` | ~100 | Called by prospect detail route; overlaps with above |
| `api_synthesize_org_brief()` | ~91 | Org-level brief |

**Why skipped:** All three call Claude, parse JSON, and persist to markdown — but prompts, field mappings, and persistence targets differ. Not byte-for-byte identical.

**Recommended action:** Extract shared Claude call + JSON parsing into `briefing/brief_synthesizer.py`. Each function keeps its own prompt and persistence logic. Phase 3 refactor.

---

## 3. Task Line Parsing — Near-Duplicate Logic (3 implementations)

**Location:** `app/delivery/dashboard.py` and `app/sources/memory_reader.py`

| Location | Function | Purpose |
|----------|----------|---------|
| `dashboard.py:_load_tasks_grouped()` | ~70 lines | Section-based TASKS.md parsing for kanban |
| `dashboard.py:_parse_task_line()` | ~81 lines | Detailed field extraction (status, priority, assignee) |
| `memory_reader.py:load_tasks()` | ~30 lines | Lightweight parsing for morning briefing |

**Why skipped:** Subtle differences in regex patterns and field extraction. Risk of behavior change if consolidated carelessly.

**Recommended action:** Consolidate into a single `parse_task_line()` in `sources/memory_reader.py` and have dashboard import it. Add unit tests first. Phase 3 refactor.

---

## 4. app/scripts/ — One-Time Migration Scripts

**Files:**
- `app/scripts/migrate_tasks_status.py`
- `app/scripts/migrate_tasks_data_model.py`
- `app/scripts/migrate_tasks_sections.py`
- `app/scripts/migrate_assignee_tasks.py`
- `app/scripts/migrate_urgency.py`
- `app/scripts/cleanup_org_duplicates.py`
- `app/scripts/bootstrap_contacts_index.py`

**Why skipped:** Audit notes these as "safe to retain but will not be run again." Not imported by any app code. Could be deleted but contain institutional knowledge about the data model evolution.

**Recommended action:** Move to `docs/archive/migration-scripts/` or delete after confirming TASKS.md and CRM data are in final format.

---

## 5. ms_graph.py — Email Inbox vs. Archive Bug

✅ **Resolved** — `ms_graph.py:141` already reads from `archive` folder. Audit was based on stale snapshot.

---

## 6. Test Coverage

✅ **Resolved** — 52 tests passing across 3 files:
- `test_task_parsing.py` — 22 cases for `_parse_task_line`
- `test_email_matching.py` — 20 cases for fuzzy org matching, internal detection, participant resolution
- `test_brief_synthesizer.py` — 10 cases for `call_claude_brief` (JSON parsing, fallbacks, prompt injection)

---

## 7. File Naming — Already Consistent

All Python source files use snake_case. No renames needed. Noted for completeness.
