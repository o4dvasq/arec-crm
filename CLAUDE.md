# Working Memory

> **⚠️ Memory Architecture Rule — Read Before Writing**
> CLAUDE.md is **app config only**. Do NOT add people tables, company tables, terms tables, LP tables, or deal tables here.
> All memory additions go to:
> - New people or terms → `memory/glossary.md` + `memory/people/{name}.md`
> - Quick-reference tables (people, companies, terms, deals) → `memory/context/me.md`
> - Company/team context → `memory/context/company.md`
> This file should stay under ~80 lines. If you are tempted to add a table or a named person here, you are in the wrong file.

---

## Identity
**Oscar Vasquez** — oscar@avilacapllc.com
Partner / Co-founder, Avila Real Estate Capital (AREC)
Based: San Francisco / Marin, CA. Splits time with Arboleda, Colombia.
**Timezone:** Pacific Time (PT)
**Key partner:** Tony Avila — 35+ year partner, lead at AREC

→ Full personal context, people quick-reference, companies & LPs: `memory/context/me.md`
→ Full glossary, nicknames, investor universe: `memory/glossary.md`
→ Company context (what AREC does, team, tools): `memory/context/company.md`
→ Active projects: `memory/projects/`
→ Individual profiles: `memory/people/`

---

## Inbox
- `inbox.md` = voice-capture queue from iPhone Shortcuts
- Processed by `/productivity:update` — clears after each run

---

## Preferences

- **Task categories:** Work (IR/Fundraising, IT/Systems, Operations) and Personal (Home, Finance, Arboleda, Fitness, Photography)
- **Task priority:** Hi / Med / Low — assign first-pass priority based on context
- **Notion sync:** Disabled — do NOT push or sync tasks to/from Notion; TASKS.md is the only source of truth for tasks
- **Notion meetings:** ALWAYS read — query Notion meeting notes on every `/productivity:update` run. Use `notion-query-meeting-notes` filtered to today or recent days, then fetch full content for any new meetings found.
- **Briefing filter:** Ignore / exclude anything regarding "Settler" in daily briefings

- **Meeting summary output:** After pulling meeting notes from Notion, save each meeting as a separate markdown file in `meeting-summaries/`. Filename: `YYYY-MM-DD-meeting-title-slug.md`. Format:

```
# Meeting Title

**Date:** YYYY-MM-DD
**Source:** [Notion](https://notion.so/...)
**Attendees:** Name1, Name2, Name3

## Summary
Brief narrative summary.

## Key Decisions
- Decision one

## Action Items
- [ ] **Person Name** — Task description

## Open Questions
- Question one
```

Archive meetings older than 7 days → `meeting-summaries/archive/`

---

## Post-Update Extensions

After the standard `/productivity:update` flow, run these in order:

### Extension 1: Meeting Debrief (Calendar Gap Detection)
- **File:** `skills/meeting-debrief.md`
- **When:** Every run (default and `--comprehensive`)
- **What:** Pulls Outlook calendar, cross-references Notion meeting notes and `meeting-summaries/`, shows gap scorecard, walks Oscar through debrief for meetings without notes
- **Note:** Notion only captures Teams meetings — in-person meetings will almost always be gaps
- **Instructions:** Read `skills/meeting-debrief.md` and follow Steps 1–7

### Extension 2: Email Log Update
- **File:** `skills/email-scan.md`
- **When:** Every run (default and `--comprehensive`)
- **What:** Scans Archive + Sent Items via MS Graph (Oscar is Inbox Zero — received emails live in Archive, not Inbox), matches to CRM orgs, appends to `crm/email_log.json` with summaries + Outlook web links
- **Note:** Domain matching resolves ~90% instantly; first run scans last 30 days to seed the log
- **Instructions:** Read `skills/email-scan.md` and follow Steps 1–7

---

# currentDate
Today's date is 2026-03-07.
