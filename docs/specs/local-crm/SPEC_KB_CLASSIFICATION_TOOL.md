# SPEC: KB Classification Tool — Export, Review, Re-Import

**Feature:** Standalone Python script to export KB items to Excel with AI-suggested classifications, allow manual correction, and re-import corrected classifications  
**Priority:** High — must run after SPEC_KB_SCHEMA_UPGRADE is complete  
**Estimated Scope:** Medium (standalone script, not integrated into the app)  
**Date:** 2026-03-08  
**Prerequisite:** SPEC_KB_SCHEMA_UPGRADE must be implemented first (loan_type and content_type columns must exist)

---

## 1. Problem

After the schema upgrade, all existing KB items default to `universal` / `policy_rule`. New items ingested by the KnowledgeExtractor will get AI-classified at extraction time, but existing items need retroactive classification. Additionally, the AI classifier won't be perfect — Oscar needs to review and correct classifications before they're used for retrieval filtering.

This tool creates a human-in-the-loop workflow: export → AI pre-classify → human review in Excel → re-import.

---

## 2. What to Build

A single Python script with three subcommands:

```
python scripts/kb_classify.py export    → creates Excel file
python scripts/kb_classify.py classify  → calls Claude to fill in suggestions
python scripts/kb_classify.py import    → reads corrected Excel, updates DB
```

### Why three steps (not one):
1. **Export** can run without an API key — useful for inspection
2. **Classify** costs money (Claude API calls) — run it once, not accidentally
3. **Import** is destructive — should only run after manual review

---

## 3. Detailed Behavior

### 3.1 `export` Subcommand

**Input:** `data/knowledge_base.db`  
**Output:** `data/kb_classification_export.xlsx`

Reads all rows from `kb_items` (regardless of status) and writes one row per item to an Excel workbook.

**Columns (in order):**

| Column | Source | Editable? | Notes |
|--------|--------|-----------|-------|
| A: `id` | kb_items.id | No (protected) | Integer primary key |
| B: `status` | kb_items.status | No | pending / approved / rejected — for context only |
| C: `scope` | kb_items.scope | No | deal / institutional — for context only |
| D: `rule_type` | kb_items.rule_type | No | Existing classification — for context |
| E: `content_preview` | kb_items.content | No | First 300 characters of content, truncated with "..." |
| F: `full_content` | kb_items.content | No | Complete content text (column width set to 80) |
| G: `loan_type_current` | kb_items.loan_type | No | Current value (will be "universal" for legacy items) |
| H: `loan_type_suggested` | Empty on export | **Yes** | Claude fills this in the `classify` step |
| I: `loan_type_final` | Empty on export | **Yes** | Oscar's corrected value — this is what gets imported |
| J: `content_type_current` | kb_items.content_type | No | Current value (will be "policy_rule" for legacy items) |
| K: `content_type_suggested` | Empty on export | **Yes** | Claude fills this in the `classify` step |
| L: `content_type_final` | Empty on export | **Yes** | Oscar's corrected value — this is what gets imported |
| M: `notes` | Empty | **Yes** | Free-text column for Oscar's notes during review |

**Excel formatting:**

- Header row: Bold, Navy (#1B3A5C) text, Light Gray (#F2F4F6) fill, freeze panes below header
- Protected columns (A–G, no fill): column header text ends with ` (read-only)`
- Editable columns (H–M): Light yellow (#FFFFF0) fill on data cells
- Column I and L: Add Excel data validation dropdowns
  - Column I (`loan_type_final`): dropdown list = `bbgloc, ad, universal`
  - Column L (`content_type_final`): dropdown list = `policy_rule, underwriting_guidance, internal_commentary`
- Auto-filter enabled on header row
- Column E width: 50. Column F width: 80. All other columns: auto-fit or 20.
- Sheet name: `KB Classifications`

### 3.2 `classify` Subcommand

**Input:** `data/kb_classification_export.xlsx` (from export step)  
**Output:** Overwrites same file with `loan_type_suggested` and `content_type_suggested` columns populated

**Process:**

1. Read all rows from the Excel file
2. Batch items into groups of 20 (to fit in context without excessive API calls)
3. For each batch, call Claude Haiku (`claude-haiku-4-5-20251001`) with this prompt:

```
You are classifying knowledge base items for a specialty real estate lender (AREC) that makes two types of loans:

1. BBGLOC (Builder Bulk Guidance Lines of Credit) — revolving vertical construction facilities for homebuilders. Key concepts: spec homes, pre-sales, absorption rates, borrowing base, builder operations, gross margins, inventory management, model homes, unit-level draws, collateral acceptance periods.

2. A&D (Acquisition & Development) — land development loans for subdivisions. Key concepts: lot takeout, forward purchase contracts, horizontal infrastructure, entitlement, phasing, builder takeout commitments, development budget, grading, utilities, LTC on land basis.

For each item below, provide two classifications:

loan_type:
- "bbgloc" if the item specifically addresses vertical construction / homebuilder operations concepts
- "ad" if the item specifically addresses land development / lot sale concepts  
- "universal" if the item applies to both (guarantor standards, general credit policy, market analysis, reporting, compliance)

content_type:
- "policy_rule" if the item states a hard threshold, limit, structural requirement, or covenant standard with a specific number or condition
- "underwriting_guidance" if the item describes analytical methodology, how to evaluate something, stress testing procedures, or risk assessment frameworks
- "internal_commentary" if the item is editorial guidance about how to present, frame, or communicate findings — language tips, IC presentation advice, terminology preferences, what to say or avoid saying

Respond with JSON only. Array of objects with keys: id, loan_type, content_type.
Do not include any text outside the JSON array.

Items to classify:
```

4. Append each batch's items as numbered entries: `[id: {id}] {full_content}`
5. Parse Claude's JSON response
6. Write `loan_type` to column H (`loan_type_suggested`) and `content_type` to column K (`content_type_suggested`)
7. Also copy suggested values into columns I and L (`_final` columns) as defaults — Oscar can overwrite these
8. Save the file

**Error handling:**
- If Claude returns malformed JSON for a batch, log the error and skip that batch (don't crash)
- Print progress: `Classifying batch 1/N... done (20 items)`
- Print summary: `Classified X items. Y items failed. Review data/kb_classification_export.xlsx`

**API config:** Read `ANTHROPIC_API_KEY` from environment or from `.env` file in project root.

### 3.3 `import` Subcommand

**Input:** `data/kb_classification_export.xlsx` (after Oscar's review)  
**Output:** Updates `kb_items` rows in `data/knowledge_base.db`

**Process:**

1. Read all rows from the Excel file
2. For each row where `loan_type_final` (column I) is not empty:
   - Validate value is one of: `bbgloc`, `ad`, `universal`
   - Update `kb_items SET loan_type = ? WHERE id = ?`
3. For each row where `content_type_final` (column L) is not empty:
   - Validate value is one of: `policy_rule`, `underwriting_guidance`, `internal_commentary`
   - Update `kb_items SET content_type = ? WHERE id = ?`
4. Skip rows where final columns are empty (don't overwrite with blanks)
5. Print summary: `Updated X items. Skipped Y items (no final value). Z validation errors.`

**Safety:**
- Before writing, back up the database: copy `data/knowledge_base.db` to `data/knowledge_base.db.bak.{timestamp}`
- If any validation error occurs, print the error but continue processing other rows (don't abort)
- Print each validation error: `Row {N} (id={id}): invalid loan_type "{value}" — skipped`

---

## 4. File Location

**Create:** `scripts/kb_classify.py`

Single file, no external dependencies beyond:
- `openpyxl` (already available — used by other scripts)
- `anthropic` Python SDK (already installed — used by the platform)
- `sqlite3` (stdlib)
- `python-dotenv` (already installed)

---

## 5. Usage

```bash
cd /path/to/arec-lending-intelligence

python scripts/kb_classify.py export
python scripts/kb_classify.py classify
python scripts/kb_classify.py import
```

The typical workflow:

1. Run `export` — produces Excel file
2. Run `classify` — Claude fills in suggested classifications
3. Open `data/kb_classification_export.xlsx` in Excel
4. Review column H vs column I (loan_type). Accept Claude's suggestion or change column I.
5. Review column K vs column L (content_type). Accept Claude's suggestion or change column L.
6. Save Excel file
7. Run `import` — writes final values back to database
8. Verify in the Knowledge Base UI that items show correct classifications

---

## 6. Edge Cases

- **KB is empty (0 items):** Export should produce a file with just the header row and print `No items to export.`
- **Classify with 0 unclassified items:** If all `_suggested` columns are already populated, print `All items already classified. Re-run export first to reset.`
- **Large KB (500+ items):** Batching at 20 items per call = 25 API calls max. Print progress per batch. Total cost: ~$0.50 with Haiku.
- **Items with very long content:** Truncate content sent to Claude at 2,000 characters per item to stay within context limits. The full content stays in the Excel file for Oscar's reference.
- **Re-running export after partial import:** Export always reads current DB state, so it will show updated `loan_type_current` / `content_type_current` values.

---

## 7. Testing

After running the full workflow:

```bash
sqlite3 data/knowledge_base.db "SELECT loan_type, content_type, COUNT(*) FROM kb_items GROUP BY loan_type, content_type;"
```

Should show a distribution across categories, not all `universal` / `policy_rule`.

```bash
sqlite3 data/knowledge_base.db "SELECT id, loan_type, content_type, substr(content, 1, 80) FROM kb_items WHERE loan_type != 'universal' LIMIT 5;"
```

Spot-check that loan-type-specific items are classified correctly.

---

## 8. Do NOT Change

- Do not modify the KB web UI in this spec — the schema spec handles UI filter additions
- Do not modify the KnowledgeExtractor — the schema spec handles future extraction classification
- Do not auto-run classify during export — they are separate steps intentionally
- Do not add this to the web application — it is a CLI-only maintenance tool

---

## 9. Acceptance Criteria

- [ ] `export` produces a well-formatted Excel file with all KB items and correct column structure
- [ ] Excel has data validation dropdowns on final columns
- [ ] `classify` calls Claude Haiku in batches and populates suggested columns
- [ ] `classify` copies suggestions into final columns as defaults
- [ ] `import` reads final columns and updates DB with validation
- [ ] `import` creates a database backup before writing
- [ ] All three subcommands print clear progress and summary messages
- [ ] Script handles empty KB gracefully
- [ ] Script handles Claude API errors per-batch without crashing

---

*SPEC_KB_CLASSIFICATION_TOOL.md — 2026-03-08*
