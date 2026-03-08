# Decisions Log

> **Append-only. Never overwrite or delete entries.**
> Add new decisions at the bottom. Format: date, decision, rationale.

---

## Format

```
## YYYY-MM-DD — [Short Decision Title]
**Decision:** What was decided.
**Rationale:** Why this choice was made over alternatives.
**Impact:** Files / systems affected.
```

---

## Log

## 2026-03-07 — Adopted docs/ Project Structure
**Decision:** Reorganized all projects to follow the `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `docs/PROJECT_STATE.md`, `docs/specs/SPEC_*.md` convention.
**Rationale:** Standardizes the design → spec → code → resume workflow across all Claude Code sessions. CLAUDE.md stays lean (working memory); docs/ carries structured reference material loaded on demand.
**Impact:** `specs/` folder replaced by `docs/specs/`. Active specs renamed to `SPEC_` prefix. Archive preserved at `docs/specs/archive/`.

---

<!-- Add new entries below this line -->
