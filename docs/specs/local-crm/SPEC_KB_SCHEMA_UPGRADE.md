# SPEC: Knowledge Base Schema Upgrade — Loan Type & Content Classification

**Feature:** KB item classification for loan-type filtering and content-type routing  
**Priority:** High — prerequisite for Advisor rewrite and classification tool  
**Estimated Scope:** Small (schema migration + shared model updates)  
**Date:** 2026-03-08

---

## 1. Problem

The `kb_items` table stores all institutional knowledge as flat text fragments with no classification by loan product or content purpose. When the AREC Advisor retrieves items via FTS5 search, it returns A&D policy mixed with BBGLOC policy (and vice versa) because shared vocabulary ("spec," "advance rate," "de-risking") matches across loan types. It also returns internal editorial commentary (e.g., "DSCR is a credibility-killer with IC") alongside substantive policy rules, and Claude surfaces both to the user verbatim.

The schema needs two new classification dimensions on `kb_items` so downstream consumers (Advisor RAG, ARM Creator context injection) can filter appropriately.

---

## 2. What to Build

Add two new columns to the `kb_items` table and update all shared models, stores, and API endpoints that touch KB items.

### 2.1 New Column: `loan_type`

**Column definition:**

```sql
loan_type TEXT NOT NULL DEFAULT 'universal'
    CHECK (loan_type IN ('bbgloc', 'ad', 'universal'))
```

Semantics:
- `bbgloc` — applies only to Builder Bulk Guidance Lines of Credit (vertical construction, revolving facilities, borrowing base)
- `ad` — applies only to Acquisition & Development loans (land development, lot takeout, non-revolving)
- `universal` — applies to both loan types (general credit policy, guarantor standards, market analysis methodology, reporting requirements)

### 2.2 New Column: `content_type`

**Column definition:**

```sql
content_type TEXT NOT NULL DEFAULT 'policy_rule'
    CHECK (content_type IN ('policy_rule', 'underwriting_guidance', 'internal_commentary'))
```

Semantics:
- `policy_rule` — hard thresholds, structural requirements, covenant standards (e.g., "Advance rate ≤85% LTV," "Guarantor liquidity ≥10% of loan amount"). These are facts the Advisor should state directly.
- `underwriting_guidance` — analytical methodology, stress testing approaches, risk assessment frameworks (e.g., "Model reductions in absorption rates to identify breakeven points"). These inform how the Advisor explains concepts.
- `internal_commentary` — editorial notes, framing guidance, language dos/don'ts, IC presentation tips (e.g., "Never use DSCR in a BBGLOC context — credibility-killer with IC"). The Advisor should *apply* these to shape its own tone and avoid mistakes, but should **never quote or paraphrase them to the user**.

---

## 3. Files to Modify

### 3.1 Schema Definition

**File:** `shared/src/arec_shared/database/knowledge_schema.sql`

Add both columns to the `kb_items` CREATE TABLE statement. Place them after the existing `rule_type` column.

```sql
loan_type TEXT NOT NULL DEFAULT 'universal'
    CHECK (loan_type IN ('bbgloc', 'ad', 'universal')),
content_type TEXT NOT NULL DEFAULT 'policy_rule'
    CHECK (content_type IN ('policy_rule', 'underwriting_guidance', 'internal_commentary')),
```

Add an index for filtered queries:

```sql
CREATE INDEX IF NOT EXISTS idx_kb_items_loan_type ON kb_items(loan_type);
CREATE INDEX IF NOT EXISTS idx_kb_items_content_type ON kb_items(content_type);
CREATE INDEX IF NOT EXISTS idx_kb_items_classification ON kb_items(loan_type, content_type, status);
```

### 3.2 Migration Script

**New file:** `scripts/migrate_kb_schema_v2.py`

This script runs against the live `data/knowledge_base.db` to add columns to the existing table without data loss.

```python
"""
KB Schema Migration v2: Add loan_type and content_type columns.
Safe to run multiple times — checks for column existence before altering.
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path("data/knowledge_base.db")

def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def migrate():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        sys.exit(1)
    
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    
    changes = []
    
    if not column_exists(cur, "kb_items", "loan_type"):
        cur.execute("""
            ALTER TABLE kb_items 
            ADD COLUMN loan_type TEXT NOT NULL DEFAULT 'universal'
        """)
        changes.append("Added loan_type column")
    
    if not column_exists(cur, "kb_items", "content_type"):
        cur.execute("""
            ALTER TABLE kb_items 
            ADD COLUMN content_type TEXT NOT NULL DEFAULT 'policy_rule'
        """)
        changes.append("Added content_type column")
    
    # Add indexes (IF NOT EXISTS handles idempotency)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_kb_items_loan_type ON kb_items(loan_type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_kb_items_content_type ON kb_items(content_type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_kb_items_classification ON kb_items(loan_type, content_type, status)")
    changes.append("Ensured indexes exist")
    
    conn.commit()
    conn.close()
    
    for c in changes:
        print(f"  ✓ {c}")
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
```

### 3.3 Pydantic Model

**File:** `shared/src/arec_shared/models/knowledge.py`

Find the `KnowledgeItem` model class. Add two fields:

```python
loan_type: str = "universal"       # bbgloc | ad | universal
content_type: str = "policy_rule"  # policy_rule | underwriting_guidance | internal_commentary
```

If there is a `KnowledgeItemCreate` or similar input model, add the same fields there with the same defaults.

### 3.4 Knowledge Store

**File:** `shared/src/arec_shared/stores/knowledge_store.py`

**Insert/create operations:** Every function that INSERTs into `kb_items` must include `loan_type` and `content_type` in the column list and values. Search for all `INSERT INTO kb_items` statements.

**List/search operations:** Every function that SELECTs from `kb_items` must accept optional `loan_type` and `content_type` filter parameters. When provided, add `AND loan_type = ?` and/or `AND content_type = ?` to the WHERE clause. When `loan_type` is provided, also include `universal` items: `AND (loan_type = ? OR loan_type = 'universal')`.

**Specific functions to update (find by name — exact names may vary):**
- `create_item()` or `add_item()` — add columns to INSERT
- `list_items()` or `get_items()` — add optional filter params
- `search_items()` or FTS5 search function — add optional filter params
- `approve_item()` / `reject_item()` — no change needed (status updates only)

### 3.5 Knowledge Extractor

**File:** `shared/src/arec_shared/core/knowledge_extractor_v2.py`

The KnowledgeExtractor sends document text to Claude for structuring into KB items. Update the Claude prompt to request classification of each extracted item.

Add to the extraction prompt (find the system prompt or user prompt that instructs Claude on output format):

```
For each knowledge item you extract, also classify it on two dimensions:

loan_type — which loan product does this item apply to?
  - "bbgloc" — Builder Bulk Guidance Lines of Credit only (vertical construction, revolving facilities, borrowing base, spec homes, pre-sales, absorption rates, builder operations)
  - "ad" — Acquisition & Development loans only (land development, lot takeout, forward purchase contracts, entitlement, horizontal infrastructure, builder takeout commitments)
  - "universal" — applies to both (guarantor standards, general credit policy, market analysis methodology, reporting requirements, compliance)

content_type — what role does this item play?
  - "policy_rule" — hard thresholds, structural requirements, covenant standards, advance rate limits. Quantitative rules with specific numbers.
  - "underwriting_guidance" — analytical methodology, stress testing approaches, risk assessment frameworks, how to evaluate a deal. Procedural knowledge.
  - "internal_commentary" — editorial notes, framing advice, language guidance, presentation tips for IC or investors, what terminology to use or avoid. Meta-guidance about how to communicate, not what the policy is.
```

Update the expected output schema to include `loan_type` and `content_type` fields. Ensure parsed output maps these fields when creating `KnowledgeItem` objects.

### 3.6 API Endpoints

**File:** `apps/knowledge_base/routes/kb_crud.py`

**GET /api/knowledge (list items):** Add optional query parameters `loan_type` and `content_type`. Pass them through to the store's list function.

```python
@router.get("/knowledge")
async def list_knowledge(
    status: Optional[str] = None,
    scope: Optional[str] = None,
    loan_type: Optional[str] = None,        # NEW
    content_type: Optional[str] = None,      # NEW
    entity: Optional[str] = None,
    search: Optional[str] = None,
    ...
):
```

**POST approve/reject:** No changes needed.

**File:** `apps/knowledge_base/routes/upload.py`

No changes needed — the KnowledgeExtractor will handle classification at extraction time.

### 3.7 Knowledge Base Frontend

**File:** `apps/unified_parent/templates/knowledge_base.html`

Add filter dropdowns in the KB list view for `loan_type` (All / BBGLOC / A&D / Universal) and `content_type` (All / Policy Rule / Underwriting Guidance / Internal Commentary). Wire them to the existing API call that fetches KB items.

Display the classification as small badges or tags on each KB item card in the list view.

---

## 4. Testing

Run the migration script, then verify:

```bash
python scripts/migrate_kb_schema_v2.py
```

```bash
sqlite3 data/knowledge_base.db "PRAGMA table_info(kb_items);" | grep -E "loan_type|content_type"
```

Both columns should appear with TEXT type and defaults.

If the KB has existing items (it currently has 0 approved, but may have pending/rejected), verify they all received the defaults:

```bash
sqlite3 data/knowledge_base.db "SELECT id, loan_type, content_type FROM kb_items LIMIT 10;"
```

All existing rows should show `universal` / `policy_rule`.

Start all four backend services and verify:
1. `GET /api/knowledge` returns items with `loan_type` and `content_type` fields in JSON
2. `GET /api/knowledge?loan_type=bbgloc` filters correctly
3. Upload a test document through KB → extracted items should have non-default classifications
4. Knowledge Base UI shows filter dropdowns and classification badges

---

## 5. Do NOT Change

- Do not modify `arm_review.db` schema — it does not use KB items directly
- Do not modify `deal_records` table — it stores structured deal metrics, not knowledge items
- Do not change the FTS5 virtual table definition — FTS5 does not support additional columns; filtering happens in the SQL query that joins `kb_items` to `kb_items_fts`
- Do not remove or rename the existing `rule_type` column — it serves a different purpose (categorizing what the rule is about, not what product it applies to)
- Do not modify ARM Creator or ARM Review at this stage — they will consume the new fields in a later spec

---

## 6. Acceptance Criteria

- [ ] `kb_items` table has `loan_type` and `content_type` columns with CHECK constraints
- [ ] Migration script is idempotent (safe to run multiple times)
- [ ] KnowledgeItem Pydantic model includes both new fields with defaults
- [ ] Knowledge store list/search functions accept and apply both filters
- [ ] Knowledge store insert functions persist both new fields
- [ ] KnowledgeExtractor prompt requests and parses both classifications
- [ ] API endpoints expose filter parameters
- [ ] KB frontend shows filters and badges
- [ ] All existing items default to `universal` / `policy_rule`

---

*SPEC_KB_SCHEMA_UPGRADE.md — 2026-03-08*
