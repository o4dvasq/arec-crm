# SPEC: AREC Advisor — Prompt Rewrite & Retrieval Filtering

**Feature:** Rewrite the AREC Advisor (LoanClaude) system prompt and retrieval pipeline to produce concise, loan-type-aware, conversational responses  
**Priority:** High — this is the user-facing fix for the quality issues  
**Estimated Scope:** Medium (prompt rewrite + retrieval logic changes, no schema changes)  
**Date:** 2026-03-08  
**Prerequisite:** SPEC_KB_SCHEMA_UPGRADE must be implemented first (loan_type and content_type columns must exist on kb_items)

---

## 1. Problem

The AREC Advisor currently produces responses that are:

1. **Contaminated across loan types** — A&D concepts (forward purchase contracts, lot takeout) appear in BBGLOC answers because retrieval doesn't filter by loan type
2. **Leaking internal commentary** — editorial guidance ("credibility-killer with IC") is quoted verbatim to the user instead of being applied silently to shape tone
3. **Over-formatted** — numbered sections, markdown headers, horizontal rules, bold labels — inappropriate for a conversational chat interface
4. **Too long** — research-memo-length responses when the user asked a 1-sentence question

The root causes are: (a) the retrieval pipeline returns everything that matches keywords without loan-type or content-type filtering, (b) the system prompt instructs Claude to be comprehensive rather than conversational, and (c) there is no post-retrieval processing to separate policy from commentary.

---

## 2. What to Build

Three changes, all in the Advisor app and shared retrieval module:

### Change A: Loan-Type Detection in User Query
### Change B: Filtered Retrieval with Content-Type Routing  
### Change C: New System Prompt

---

## 3. Change A — Loan-Type Detection

**File:** `shared/src/arec_shared/core/advisor.py`

Before calling the retrieval function, detect the loan type implied by the user's question. This is a keyword heuristic — not an AI call.

**Add this function** at the module level:

```python
def detect_loan_type(question: str) -> str:
    """
    Detect implied loan type from user question.
    Returns 'bbgloc', 'ad', or 'any'.
    """
    q = question.lower()
    
    bbgloc_signals = [
        "bbgloc", "borrowing base", "builder line", "guidance line",
        "spec home", "spec cap", "spec inventory", "pre-sale",
        "presale", "absorption rate", "vertical construction",
        "builder bulk", "revolving", "unit loan", "collateral acceptance",
        "model home", "gross margin", "builder operations",
        "inventory analysis", "months of supply",
    ]
    
    ad_signals = [
        "a&d", "acquisition and development", "acquisition & development",
        "lot takeout", "forward purchase", "land development",
        "horizontal", "entitlement", "phasing plan", "grading",
        "development budget", "builder takeout", "lot sale",
        "finished lot", "infrastructure", "subdivision",
    ]
    
    bbgloc_hits = sum(1 for s in bbgloc_signals if s in q)
    ad_hits = sum(1 for s in ad_signals if s in q)
    
    if bbgloc_hits > 0 and ad_hits == 0:
        return "bbgloc"
    elif ad_hits > 0 and bbgloc_hits == 0:
        return "ad"
    else:
        return "any"
```

**Call this function** before retrieval in the main ask/answer function. Pass the result to the retrieval call.

---

## 4. Change B — Filtered Retrieval with Content-Type Routing

**File:** `shared/src/arec_shared/core/knowledge_retrieval.py`

This is the module that searches `kb_items` (via FTS5 and/or similarity) and returns results to inject into the Advisor's context.

### 4.1 Add Loan-Type Filter to Search

Find the main search/retrieval function (likely named `search_knowledge`, `retrieve_context`, or similar). It currently builds a SQL query joining `kb_items` to `kb_items_fts`.

**Add parameter:** `loan_type: str = "any"`

**Modify the WHERE clause:** When `loan_type` is not `"any"`, add:

```sql
AND (kb_items.loan_type = ? OR kb_items.loan_type = 'universal')
```

This ensures BBGLOC questions get BBGLOC + universal items, A&D questions get A&D + universal items, and untyped questions get everything.

### 4.2 Reduce Top-K

Find where the result limit is set (likely a `LIMIT` clause or a slice on results). 

**Change:** Reduce from whatever it currently is to **7 items maximum**.

If the current implementation uses a configurable `top_k` parameter, change the default to 7. If it's hardcoded, change the hardcoded value.

### 4.3 Separate Results by Content Type

After retrieval, split the results into two groups before injecting into the prompt:

```python
policy_and_guidance = [
    item for item in results 
    if item.content_type in ("policy_rule", "underwriting_guidance")
]

internal_commentary = [
    item for item in results 
    if item.content_type == "internal_commentary"
]
```

**Return both groups** to the caller (the advisor function) as a tuple or a dataclass:

```python
@dataclass
class RetrievalResult:
    policy_items: list       # policy_rule + underwriting_guidance
    commentary_items: list   # internal_commentary
    loan_type_detected: str  # bbgloc | ad | any
```

### 4.4 Update the Advisor's Context Injection

**File:** `shared/src/arec_shared/core/advisor.py`

Where retrieved items are currently injected into the Claude prompt (likely as a single block of text in the user message or system prompt), replace with two separate blocks:

**Policy block** (injected in the user message as reference material):

```
<reference_material>
The following AREC policy and underwriting guidance is relevant to this question.
Use this information to inform your answer. Cite specific thresholds and standards when relevant.

{formatted policy_items — one per line, numbered}
</reference_material>
```

**Commentary block** (injected in the system prompt as behavioral instruction):

```
<internal_guidance>
Apply the following internal guidance to shape your response tone and avoid common errors.
Do NOT quote, paraphrase, or reference this guidance directly in your answer to the user.
These are internal notes — use them to inform what you say and how you say it, not as content to surface.

{formatted commentary_items — one per line}
</internal_guidance>
```

If there are no commentary items, omit the `<internal_guidance>` block entirely.

---

## 5. Change C — New System Prompt

**File:** `shared/src/arec_shared/core/advisor.py`

Find the current system prompt string (likely a constant or a variable assigned in the ask/answer function). **Replace it entirely** with the following:

```python
ADVISOR_SYSTEM_PROMPT = """You are the AREC Advisor — a knowledgeable credit professional who helps relationship managers and credit staff with questions about AREC's lending programs, credit policy, and underwriting standards.

Your knowledge comes from AREC's institutional policy documents and underwriting guidelines. When reference material is provided with a question, use it to give accurate, specific answers grounded in AREC policy.

RESPONSE STYLE:
- Answer conversationally in 2-4 paragraphs for typical questions. Match response length to question complexity.
- For simple factual questions ("what's our advance rate cap?"), give a direct 1-2 sentence answer.
- For conceptual questions ("how do we handle spec risk?"), explain in 2-4 focused paragraphs.
- Only use structured formats (numbered lists, headers) when the user explicitly asks for a checklist, comparison, or breakdown.
- Never use markdown headers (##), horizontal rules (---), or bold section labels in conversational answers.
- Write in a collegial, professional tone — like a senior colleague answering a question across the desk.

ACCURACY RULES:
- State specific thresholds and standards when they exist in the reference material (e.g., "our standard is ≤85% LTV" not "we have conservative advance rates").
- When the reference material doesn't cover the question, say so plainly: "I don't have specific policy guidance on that — you may want to check with [CLO/CRO/relevant person]."
- Never invent thresholds, standards, or policy positions. If a number isn't in the reference material, don't fabricate one.
- AREC makes two loan products: BBGLOCs (revolving vertical construction lines for homebuilders) and A&D loans (land development financing). Keep these distinct. Do not apply BBGLOC concepts to A&D questions or vice versa.
- Never use DSCR, NOI, or Cap Rate when discussing BBGLOCs or A&D loans. These metrics apply only to income-producing rental properties, which AREC does not finance.

WHAT NOT TO DO:
- Do not produce research memos, white papers, or exhaustive briefings unless explicitly asked.
- Do not add disclaimers, caveats, or hedge language ("it's worth noting," "it should be emphasized").
- Do not repeat the question back before answering.
- Do not sign off with offers to help further ("let me know if you have other questions").
"""
```

**Append the `<internal_guidance>` block** (from Change B) to the end of this system prompt at runtime, only when commentary items exist.

---

## 6. Files to Modify — Summary

| File | Change |
|------|--------|
| `shared/src/arec_shared/core/advisor.py` | Add `detect_loan_type()`, replace system prompt constant, restructure context injection into policy vs. commentary blocks, call retrieval with loan_type parameter |
| `shared/src/arec_shared/core/knowledge_retrieval.py` | Add `loan_type` filter parameter to search, reduce top-k to 7, return `RetrievalResult` with separated content types |

That's it. Two files.

---

## 7. Example Before/After

**User question:** "How do we control spec risk in BBGLOCs?"

**Current behavior (broken):**
- Retrieval returns 12+ items including A&D lot takeout policy, internal framing notes, BBGLOC advance rates, general credit policy
- System prompt tells Claude to be comprehensive
- Output: 800-word formatted memo with A&D concepts mixed in, internal commentary quoted, markdown headers

**New behavior:**
- `detect_loan_type("How do we control spec risk in BBGLOCs?")` → `"bbgloc"`
- Retrieval filters: `loan_type IN ('bbgloc', 'universal')`, returns 5-7 items
- Policy items (spec cap thresholds, advance rates, BRR structure) → injected as `<reference_material>`
- Commentary item ("never use DSCR in BBGLOC context") → injected as `<internal_guidance>` in system prompt
- Claude answers in 3 paragraphs, cites specific thresholds, doesn't mention DSCR at all (silently applies the guidance), doesn't quote internal framing notes

**Expected output (approximately):**

> Spec risk in BBGLOCs is managed through a layered set of structural controls built into the facility terms. The primary driver is the Builder Risk Rating (BRR), which calibrates how much spec exposure a borrower is allowed. Our standard spec cap is ≤40% of the facility at the preferred level, with a hard maximum at 75%. Spec inventory months of supply must stay at or below 6 months, measured against trailing 12-month absorption.
>
> Beyond the caps, the borrowing base mechanics themselves constrain spec builds. Spec units advance at a lower rate than sold/under-contract units — typically 75% LTV / 90% LTC versus 80% LTV / 100% LTC for pre-sold. That spread creates a natural incentive for the builder to convert specs to contracts before drawing further. The rolling draw structure means the borrower can't front-load spec construction ahead of sales velocity.
>
> On the monitoring side, we stress test both price and absorption. Underwriting models a 10-20% price decline and a reduction in closings pace to find breakeven points. Monthly borrowing base reports give us real-time visibility into spec inventory relative to sales pace, and covenant compliance is tested quarterly.

---

## 8. Testing

### 8.1 Loan-Type Detection

Test the keyword function directly:

```python
assert detect_loan_type("How do we handle spec risk in BBGLOCs?") == "bbgloc"
assert detect_loan_type("What's our advance rate for A&D loans?") == "ad"
assert detect_loan_type("What are our guarantor liquidity requirements?") == "any"
assert detect_loan_type("Tell me about lot takeout coverage") == "ad"
assert detect_loan_type("What's our spec cap?") == "bbgloc"
assert detect_loan_type("How does the BRR work for borrowing base facilities?") == "bbgloc"
```

### 8.2 Retrieval Filtering

With classified KB items in the database, run:

```python
# Should return only bbgloc + universal items
results = retrieve_context("spec risk management", loan_type="bbgloc")
for item in results.policy_items:
    assert item.loan_type in ("bbgloc", "universal")

# Should not contain any A&D-only items
for item in results.policy_items:
    assert item.loan_type != "ad"
```

### 8.3 End-to-End

Start the Advisor service and test through the chat UI:

1. Ask: "How do we control spec risk in BBGLOCs?"
   - Response should NOT mention forward purchase contracts, lot takeout, or A&D concepts
   - Response should NOT quote internal framing notes verbatim
   - Response should be 2-4 paragraphs, no markdown headers or horizontal rules
   - Response SHOULD cite specific thresholds (spec cap %, advance rates, MOS limits)

2. Ask: "What's our advance rate?"
   - Response should be 1-3 sentences, direct answer
   - Should NOT produce a formatted memo

3. Ask: "Compare our BBGLOC and A&D underwriting approaches"
   - `detect_loan_type` returns `"any"` (both signals present)
   - Retrieval returns items from both types + universal
   - Response should clearly separate the two products

4. Ask: "What is DSCR?"
   - Internal commentary says to avoid DSCR in construction context
   - Response should explain that DSCR is not applicable to AREC's loan products (homes for sale, not income-producing) — but should NOT say "we internally call this a credibility-killer"

---

## 9. Do NOT Change

- Do not modify the Knowledge Base app, schema, or extraction pipeline (handled by SPEC_KB_SCHEMA_UPGRADE)
- Do not modify ARM Creator or ARM Review
- Do not change the Advisor's SSE streaming mechanism — only the content generation
- Do not add a new API endpoint — the existing `POST /api/ask` endpoint stays the same
- Do not change the Advisor frontend (`advisor.html`) — the UI is fine, the problem is the response content
- Do not add conversation memory or multi-turn context management beyond what already exists

---

## 10. Acceptance Criteria

- [ ] `detect_loan_type()` correctly identifies bbgloc, ad, and any from natural questions
- [ ] Retrieval filters by `loan_type` when detected, always includes `universal`
- [ ] Retrieval returns max 7 items (down from previous limit)
- [ ] Retrieved items are split into policy vs. commentary groups
- [ ] Policy items injected as `<reference_material>` in user message
- [ ] Commentary items injected as `<internal_guidance>` in system prompt with explicit "do not surface" instruction
- [ ] System prompt produces conversational 2-4 paragraph responses for typical questions
- [ ] System prompt produces short 1-2 sentence responses for simple factual questions
- [ ] No markdown headers, horizontal rules, or bold section labels in conversational responses
- [ ] A&D concepts do not appear in BBGLOC-specific answers
- [ ] Internal editorial commentary is never quoted to the user
- [ ] Specific thresholds and standards are cited when available in reference material

---

*SPEC_ADVISOR_REWRITE.md — 2026-03-08*
