# Overwatch — Project Context for New Conversation

**Author:** Oscar Vasquez, COO — Avila Real Estate Capital
**Date:** 2026-03-13
**Purpose:** Onboarding context for a new Claude Desktop session on the Overwatch project.
**Reader:** You are a software engineer + AI workflow designer helping Oscar build and maintain Overwatch.

---

## 1. What Overwatch Is

Overwatch is Oscar's **personal productivity platform** — tasks, meeting summaries, personal memory, and calendar integration. It is local-only (single-user, no authentication, no Azure deployment) and runs as a Flask app on port 3001.

It was carved off from the AREC CRM project on 2026-03-12 as part of a broader architectural split. The CRM became a multi-user, PostgreSQL-backed, Azure-deployed platform for the fundraising team. Overwatch inherited the personal productivity layer that didn't belong on a shared platform.

**Location:** `~/Dropbox/projects/overwatch/`
**Port:** 3001
**No Azure, no auth, no team access.**

---

## 2. The Pre-Split Architecture (What We Had Before)

Before the split, everything lived in a single project at:

```
~/Dropbox/Tech/ClaudeProductivity/
```

This was a Flask app with two intertwined responsibilities:

| Layer | What It Did |
|-------|------------|
| **CRM** | Fundraising pipeline, prospects, organizations, relationship briefs, email auto-capture |
| **Productivity** | Tasks, morning briefings, meeting notes, personal memory, calendar intel |

**All data was markdown flat files:**

```
~/Dropbox/Tech/ClaudeProductivity/
├── TASKS.md                    ← Task list (Oscar's only)
├── crm/
│   ├── prospects.md            ← Fundraising pipeline
│   ├── organizations.md        ← Org records
│   ├── config.md               ← Pipeline stages, team roster, urgency levels
│   ├── offerings.md            ← Fund names and targets
│   └── interactions.md         ← Interaction log
├── memory/
│   └── people/{name}.md        ← Individual contact intelligence files
└── glossary.md                 ← Terminology
```

**The AI layer** was Claude Desktop (Cowork plugin). All knowledge base writes flowed through Cowork. Claude Desktop served as the brain — synthesizing context, generating morning briefings, processing email, triaging tasks.

---

## 3. The Cowork Skill System (Pre-Split)

Claude Desktop used a **skills** system: markdown-defined workflows that Claude executed on command. The key skill was:

### `/productivity:update` (the flagship skill)
This was a comprehensive daily update workflow that ran roughly in this order:

1. **Email scan** — Scanned Oscar's Outlook `#productivity` folder via Microsoft Graph API for CRM-relevant emails. Matched against prospect orgs, queued to `crm/ai_inbox_queue.md`.
2. **Calendar check** — Pulled upcoming calendar events and Teams meetings from Graph API. Surfaced prep context for upcoming investor meetings.
3. **Notion sync** — Oscar's personal Notion workspace was checked for task or note updates (Notion was Oscar's personal workflow only, not a platform integration).
4. **Task triage** — Reviewed `TASKS.md`, flagged overdue or stale items, extracted newly-mentioned tasks from email context.
5. **Morning briefing** — Synthesized all of the above into a narrative briefing: what's happening today, who to call, what's overdue.

Supporting skills:
- `/email` — Deep scan of the `#productivity` Outlook folder, interactive quiz on unknowns, archive processed items
- `/email-scan` — Faster, non-interactive version: scan 5 email passes (Oscar received, Oscar sent, Tony received, Tony sent, CRM shared mailbox), match to orgs, log to `crm/email_log.json`

---

## 4. What Changed in the Split (2026-03-12)

### What went to AREC CRM (PostgreSQL / Azure)
- Fundraising pipeline (prospects, orgs, contacts)
- Relationship briefs
- Email auto-capture and interaction history
- Team tasks (`prospect_tasks` DB table)
- All multi-user data

### What stayed in Overwatch (local / markdown)
- `TASKS.md` — Oscar's personal task list (source of truth, still markdown)
- Meeting summaries (`meeting-summaries/` directory)
- Personal memory (`memory/` directory — project notes, glossary)
- Calendar integration (personal calendar context)
- Morning briefing concept (officially "deprecated" but the intent lives in Overwatch)

### Key structural facts post-split
- Overwatch has **zero imports from arec-crm**. Shared modules (graph_auth, ms_graph) were **copied** into Overwatch — not shared.
- The old project path `~/Dropbox/Tech/ClaudeProductivity/` is **legacy**. Overwatch lives at `~/Dropbox/projects/overwatch/`.
- The `/crm/` markdown files still exist locally as historical backup but are **not used by any live app**.

---

## 5. The Skills Question: Does `/update` Still Work?

**Short answer: uncertain — this needs investigation.**

The Cowork skills (including `/productivity:update`, `/email`, `/email-scan`) are defined as markdown files in:
```
/mnt/skills/user/
```

These skills contain file paths and logic that were written for the **pre-split** project structure at `~/Dropbox/Tech/ClaudeProductivity/`. After the split:

| Concern | Status |
|---------|--------|
| File paths in skills may still point to old `ClaudeProductivity/` location | Likely stale |
| `crm/ai_inbox_queue.md` referenced in email skill — does it exist in Overwatch? | Unknown |
| `email_log.json` target path — correct location? | Unknown |
| Task triage in `/update` reads `TASKS.md` — does it know the new path? | Unknown |
| CRM-related steps in `/update` (prospect matching) — still relevant or broken? | Broken by design — CRM is now PostgreSQL |

**The CRM-facing steps of `/update` are structurally broken** — they were written to read/write markdown prospect files that no longer serve as the source of truth. The personal productivity steps (tasks, calendar, briefing) may still work if the file paths are updated.

---

## 6. Overwatch Current State (as of 2026-03-13)

What is confirmed built and working:

- Flask app on port 3001, local-only
- Task management reading/writing `TASKS.md`
- Meeting summaries in `meeting-summaries/`
- Personal memory in `memory/`
- Calendar integration (Graph API, personal calendar)
- Separate from arec-crm, zero shared code (modules copied)

What is unclear / not yet confirmed:

- Whether the Cowork skill paths have been updated to `~/Dropbox/projects/overwatch/`
- Whether `/productivity:update` runs end-to-end against the new structure
- What the morning briefing currently produces (it was "deprecated" from CRM but the intent lives here)
- Whether `drain_inbox.py` (shared mailbox drain) was copied to Overwatch or lives only in arec-crm

---

## 7. The Vision (What Overwatch Should Become)

The original intent for this layer (now Overwatch) was:

> An AI-native shared intelligence platform where every team member receives a personalized morning briefing synthesized from collective relationship knowledge. The system preserves institutional knowledge and surfaces it at the right moment — not just a database with a web UI.

For Oscar personally (single-user Overwatch):
- A **morning briefing** that synthesizes: calendar for the day, overdue tasks, prep context for investor meetings, recent email signals, and people intel
- **Tasks** managed via TASKS.md with mobile access (see PWA)
- **Meeting notes** captured from Teams and surfaced as context before related meetings
- **People intelligence** — `memory/people/{name}.md` files as durable contact profiles

The key metric: **does the morning briefing actually change how Oscar prepares for a meeting?**

---

## 8. Key Files and Paths

| Item | Path |
|------|------|
| Project root | `~/Dropbox/projects/overwatch/` |
| Tasks | `TASKS.md` (in project root or overwatch data dir — verify) |
| Meeting summaries | `meeting-summaries/` |
| People intel | `memory/people/{name}.md` |
| Flask app | `app/delivery/dashboard.py` (port 3001) |
| Tasks blueprint | `app/delivery/tasks_blueprint.py` |
| Cowork skills | `/mnt/skills/user/` |
| Graph auth (copied) | `app/auth/graph_auth.py` |
| Graph API wrapper (copied) | `app/sources/ms_graph.py` |

---

## 9. Immediate Open Questions for This Conversation

1. What is the actual directory structure of `~/Dropbox/projects/overwatch/` right now?
2. Do the Cowork skills (`/email`, `/email-scan`, `/update`) have updated file paths, or are they still pointing at `~/Dropbox/Tech/ClaudeProductivity/`?
3. Does `crm/ai_inbox_queue.md` exist in the Overwatch project?
4. Was `drain_inbox.py` (shared mailbox drain) copied to Overwatch?
5. What does the morning briefing currently produce — is there a working briefing route in the Flask app?
6. Is there a `CLAUDE.md` in the Overwatch project root?

---

## 10. Relevant Connected Systems

| System | Relation to Overwatch |
|--------|----------------------|
| **AREC CRM** (`arec-crm-app.azurewebsites.net`) | Separate app. Zero code sharing. Handles team CRM data. |
| **Microsoft Graph API** | Outlook + Teams + Calendar. Overwatch has a copied `ms_graph.py`. |
| **Dropbox** | Syncs `TASKS.md` and markdown files across Oscar's iMac and MacBook Air. |
| **AREC Mobile PWA** (`arec-mobile/`) | Reads/writes same `TASKS.md` and prospect markdown. Functional, not actively iterated. |
| **Notion** | Oscar's personal workflow only. Was part of `/update` skill. Not a platform integration. |
| **Anthropic API** | Used for brief synthesis. Model: `claude-sonnet-4-6`. API key in `app/.env`. |

---

*End of context document. Hand this to the new Overwatch conversation as the starting brief.*
