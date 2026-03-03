# Meeting Transcript Sync — Architecture & Data Model

*Last updated: 2026-02-25*
*For use in: Productivity workflow documentation*

---

## What We Built

An automated pipeline that pulls meeting transcripts from Notion, summarizes them into structured markdown files, extracts action items, and cross-references those items against the existing task list (TASKS.md). This runs as part of the `/productivity:update` command — the same command that already handles inbox processing, external task sync, stale-item triage, and memory gap detection.

---

## Where It Lives in the System

The meeting sync is **Step 3** in the 8-step `/productivity:update` workflow. Here's the full command flow with the new step highlighted:

```
Step 1: Load State          → Read TASKS.md, CLAUDE.md, memory/
Step 2: Sync External Tasks → Pull from Asana, Linear, Jira, GitHub (if connected)
Step 3: Sync Notion Meeting Transcripts  ← NEW
Step 4: Triage Stale Items  → Flag overdue, 30+ day items, missing context
Step 5: Decode Tasks        → Resolve shorthand, acronyms, unknown names
Step 6: Fill Gaps           → Ask user about anything unrecognized
Step 7: Capture Enrichment  → Links, status changes, deadlines from conversation
Step 8: Report              → Summary of everything found, changed, proposed
```

---

## Data Flow

```
┌──────────────────────┐
│  Notion Meeting Notes │  (source of truth for transcripts)
│  via MCP connector    │
└──────────┬───────────┘
           │
           │  notion-query-meeting-notes (last 3 days)
           ▼
┌──────────────────────┐
│  List of meetings     │  title, URL, created_time
│  (metadata only)      │
└──────────┬───────────┘
           │
           │  Check meeting-summaries/ for existing files
           │  (dedup by date + fuzzy title match on filename)
           ▼
┌──────────────────────┐
│  New meetings only    │  Skip already-processed
└──────────┬───────────┘
           │
           │  notion-fetch (include_transcript: true)
           ▼
┌──────────────────────┐
│  Full transcript text │  Raw conversation + Notion AI notes
│  + AI-generated notes │  (action items, summaries, decisions)
└──────────┬───────────┘
           │
           │  Summarize with CLAUDE.md context
           │  (resolve names, deals, acronyms)
           ▼
┌──────────────────────────────────┐
│  meeting-summaries/              │
│  YYYY-MM-DD-meeting-slug.md      │  ← written to disk
└──────────┬───────────────────────┘
           │
           │  Extract action items
           │  Cross-reference TASKS.md
           ▼
┌──────────────────────┐
│  Proposed new tasks   │  Presented to user for approval
│  (not auto-added)     │  before touching TASKS.md
└───────────────────────┘
```

---

## File Structure

```
ClaudeProductivity/
├── CLAUDE.md                      ← Working memory (people, terms, deals)
├── TASKS.md                       ← Single source of truth for tasks
├── inbox.md                       ← iPhone voice capture queue
├── update.md                      ← Updated command file (needs install)
├── meeting-summaries-architecture.md  ← This document
├── meeting-summaries/             ← NEW DIRECTORY
│   ├── 2026-02-23-fund-structure-legal-review.md
│   ├── 2026-02-23-tax-structuring-israeli-investors.md
│   ├── 2026-02-23-utimco-investor-presentation-prep.md
│   ├── 2026-02-24-family-office-partnership-discussion.md
│   ├── 2026-02-24-investor-documentation-review.md
│   ├── 2026-02-25-rxr-arec-venture-term-sheet-review.md
│   └── 2026-02-25-sharepoint-migration-discussion.md
├── memory/
│   ├── glossary.md
│   ├── context/company.md
│   ├── people/
│   │   ├── tony-avila.md
│   │   ├── adrian-vasquez.md
│   │   ├── paige.md
│   │   └── anthony-albuquerque.md
│   └── projects/
│       └── arec-fund-ii.md
├── dashboard.html
└── SHORTCUT-SETUP.md
```

---

## Meeting Summary Data Model

### File Naming Convention

```
meeting-summaries/YYYY-MM-DD-meeting-title-slug.md
```

Rules:
- Date prefix from the meeting's `created_time` in Notion
- Title slug is the meeting title, lowercased, spaces replaced with hyphens, special characters stripped
- If two meetings on the same day have the same slug, append `-2`, `-3`, etc.

### Schema (Markdown Template)

Every summary file follows this exact structure:

```markdown
# [Meeting Title]

**Date:** YYYY-MM-DD
**Source:** [Notion](https://www.notion.so/{page-id})
**Attendees:** [Comma-separated list, using known names from CLAUDE.md]

## Summary
[2-5 paragraphs of narrative prose. Not a transcript — a distilled account of
what was discussed, what mattered, and why. Written with full context from
CLAUDE.md so that deal names, people, and acronyms are resolved inline.
Includes dollar amounts, percentages, and specific terms where mentioned.]

## Key Decisions
- [Bullet list of concrete decisions made during the meeting]
- [Each item is a single sentence stating what was decided]

## Action Items
- [ ] **[Person Name]** — Action item description
- [ ] **[Person Name]** — Another action item
[Checkboxes for tracking. Person name bolded. Only items with a clear
owner are included. Items without an owner get "Team" as the assignee.]

## Open Questions
- [Unresolved questions or items that need follow-up]
- [Things that were raised but not answered]
```

### Field Definitions

| Field | Source | Format | Notes |
|-------|--------|--------|-------|
| **Title** | Notion page title (cleaned) | H1 heading | Notion titles often include `@Today` date mentions — these are stripped and replaced with a descriptive title |
| **Date** | Notion `created_time` | `YYYY-MM-DD` | UTC date from the meeting note creation |
| **Source** | Notion page URL | Markdown link | Direct link back to the Notion page for reference |
| **Attendees** | Extracted from transcript | Comma-separated names | Cross-referenced against CLAUDE.md people table. External participants include company/role |
| **Summary** | Generated from transcript | Narrative prose | 2-5 paragraphs. Context-enriched using CLAUDE.md (resolves "Tony" → "Tony Avila", "A&D" → "Acquisition & Development", etc.) |
| **Key Decisions** | Extracted from transcript | Bullet list | Only includes items where a clear decision was reached, not just discussed |
| **Action Items** | Extracted from transcript + Notion AI | Checkbox list | Format: `- [ ] **[Person]** — Description`. These are candidates for TASKS.md but are NOT auto-added |
| **Open Questions** | Inferred from transcript | Bullet list | Items raised but not resolved, or next steps that need clarification |

---

## How Deduplication Works

Before generating a new summary, the system checks the `meeting-summaries/` directory:

1. **List existing files** in `meeting-summaries/`
2. **Extract dates** from filenames (the `YYYY-MM-DD` prefix)
3. **Fuzzy match** the meeting title slug against existing filenames for the same date
4. **Skip** any meeting that already has a corresponding file

This means re-running `/productivity:update` is safe — it won't regenerate summaries that already exist. To force a regeneration, delete the specific file from `meeting-summaries/`.

---

## How Action Items Flow to TASKS.md

Action items extracted from meetings are **proposed, not auto-added**. The flow:

```
Meeting transcript
  → Extract action items (person + description)
  → Cross-reference against TASKS.md (check for duplicates by fuzzy matching)
  → Filter to Oscar-owned items only (other people's items stay in the summary)
  → Present new items to user in the update report
  → User approves → items added to TASKS.md Active section
```

TASKS.md format for new items from meetings:

```markdown
- [ ] **[Med]** Description — from [meeting name] [date]
```

Priority is assigned based on context (urgency language, deadlines mentioned, who requested it).

---

## API Details

### Notion MCP Tools Used

**1. `notion-query-meeting-notes`** — Finds meetings within a date range

```json
{
  "filter": {
    "operator": "and",
    "filters": [{
      "property": "created_time",
      "filter": {
        "operator": "date_is_within",
        "value": {
          "type": "relative",
          "value": "custom",
          "direction": "past",
          "unit": "day",
          "count": 3
        }
      }
    }]
  }
}
```

Returns: List of meeting pages with titles, URLs, and timestamps. Does NOT include transcript content.

**2. `notion-fetch`** — Retrieves full meeting content

```
notion-fetch(id: "<page-url>", include_transcript: true)
```

Returns: Full page content including:
- `title` — Meeting title (often includes `@Today` date reference)
- `url` — Canonical Notion page URL
- `text` — Complete page content, which includes:
  - Notion AI-generated structured notes (action items, key points, summaries)
  - Raw transcript text (full conversation with speaker turns)

The raw transcript is the primary source material. The Notion AI notes are useful as a cross-check but are not relied upon exclusively — Claude re-summarizes from the transcript with AREC-specific context.

---

## Relationship to Other System Components

### CLAUDE.md (Working Memory)

Meeting summaries are enriched using CLAUDE.md context:
- **People table** → Resolves first names to full names and roles ("Zach" → "Zach Reisner")
- **Terms table** → Expands acronyms inline ("A&D" → "Acquisition & Development")
- **Key Deals** → Adds context when deals are mentioned ("Mountain House" → "$477M A&D loan, 27-28% IRR")
- **Companies & LPs** → Links investor mentions to known relationships

### TASKS.md (Task Tracking)

Meeting summaries feed action items into TASKS.md, but the relationship is one-way and gated:
- Summaries are generated independently of TASKS.md
- Action items are extracted and cross-referenced (not duplicated)
- New items require user approval before being added
- Once added to TASKS.md, the task lives there — the summary is historical record only

### memory/ (Deep Storage)

Meeting summaries may trigger memory updates:
- New people mentioned → candidate for `memory/people/` profile
- New terms or acronyms → candidate for `memory/glossary.md`
- Project updates → candidate for `memory/projects/` updates

These are flagged during the update, not auto-written.

---

## Installation Note

The updated `update.md` command file is currently saved at:
```
ClaudeProductivity/update.md
```

To activate it, it needs to be copied to the plugin's command directory:
```
~/.local-plugins/cache/knowledge-work-plugins/productivity/1.0.0/commands/update.md
```

The plugin cache is read-only within the Cowork VM, so this copy must be done on the host machine.

---

## What a Typical Run Looks Like

When Oscar runs `/productivity:update`, the meeting sync step produces output like:

```
Meeting Transcripts (last 3 days):
  ✓ 7 meetings found in Notion
  ✓ 4 already summarized (skipped)
  ✓ 3 new summaries written to meeting-summaries/

  New action items extracted:
  1. [Med] Follow up with Anthony on $110K partnership fee — from Family Office Discussion 2/24
  2. [Hi] Finalize FAQ edits for Japanese bank — from Investor Doc Review 2/24

  → Add these to TASKS.md? (y/n)
```

The user confirms, items are added, and the update continues to the next step.
