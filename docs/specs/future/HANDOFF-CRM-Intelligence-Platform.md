# Conversation Handoff: CRM → Intelligence Platform Architecture

**Date:** March 8, 2026  
**Conversation:** Multi-user CRM requirements interview → Architecture doc  
**Response count at end:** 10

---

## What Happened

Oscar asked what it would take to make the AREC CRM multi-user. Through a structured interview (8 rounds of questions), the scope evolved significantly:

1. **Started as:** "Put the CRM on Azure with logins for 8 people"
2. **Evolved to:** "Build a shared intelligence platform where AI synthesizes the team's collective knowledge about every investor relationship and delivers personalized morning briefings"

The key pivot came when Oscar challenged the core assumption: the value isn't in the database or web UI — it's in the AI intelligence layer (meeting context, email signals, relationship knowledge). This led to questioning whether markdown was the right foundation (answer: no, it was an artifact of the single-user Cowork workflow) and surfacing a new kind of conflict problem — not "who touched the database row last" but "Oscar's knowledge about Merseyside is different from Zach's, and neither has the full picture."

---

## Decisions Made

| Decision | Choice |
|----------|--------|
| Users | Full AREC team from config.md (~8 people) |
| Editing model | Everyone reads and writes the same pipeline |
| Change tracking | Nice to have — show last modifier, no full audit trail |
| Hosting | Azure (App Service + PostgreSQL Flexible Server) |
| Auth | Microsoft Entra ID SSO (existing M365 accounts) |
| Data store | PostgreSQL (replacing markdown entirely for CRM data) |
| Markdown going forward | Letting go of it — cloud-native from the start |
| Morning briefing scope | Every team member gets personalized email briefing |
| Briefing cadence | Morning only — one email at 6-7 AM |
| Graph permissions | Admin consent for all 8 team mailboxes |
| Knowledge visibility | All shared — everyone sees full picture on every prospect |
| Team adoption model | Light active input — forward emails, quick notes after meetings |
| Capture surface | Email-first (forward to ai@avilacapital.com + Graph auto-scan) |
| Briefing delivery | Email (daily digest) |
| Mobile PWA | Desktop only for V1 |
| Local morning briefing | Stays on Oscar's machine, reads from Azure API |
| Cowork | Phased: starts as Oscar's private read-only layer, later gets API write access |
| Sequencing | Finish local CRM Phases 1-4 first, THEN migrate to Azure intelligence platform |

---

## Documents Produced

### AREC-INTELLIGENCE-PLATFORM-ARCHITECTURE.md (add to project files)
The primary architecture document. Covers:

- **Three-layer intelligence model:** Interactions (facts) → Intelligence Notes (interpretation) → Signals (AI-detected patterns). These are separate database tables, not a Notes text field.
- **Attribution model:** Every piece of intelligence tracks who contributed it, how it was captured, when, and confidence level.
- **Intelligence capture pipeline:** Graph scanner (automatic, 8 mailboxes), shared mailbox processor (ai@avilacapital.com), meeting transcripts, manual web UI notes.
- **Briefing engine:** 6 AM daily, per-user personalization based on their calendar + assigned prospects + team intelligence. Claude API synthesizes briefing paragraphs.
- **Full Postgres schema:** Core CRM tables (offerings, orgs, contacts, prospects) + intelligence tables (interactions, intelligence_notes, signals, email_scan_log, briefing_history).
- **Six implementation phases:** I1 (DB + Auth + Web App) → I2 (Graph Scanner) → I3 (Intelligence UI) → I4 (Briefing Engine) → I5 (Meeting Transcripts) → I6 (Cowork Bridge)
- **Azure cost estimate:** ~$30/month infrastructure + ~$100-150/month Claude API

### MULTI-USER-CRM-ARCHITECTURE.md (superseded — discard)
The earlier "CRM with logins" version. Produced before the pivot to intelligence platform. No longer relevant.

---

## What's Next

1. **Finish local CRM Phases 1-4** (prerequisite — already in progress per existing CRM-ARCHITECTURE-FINAL.md)
2. **Phase I1 spec** — First Claude Code handoff for the intelligence platform: Postgres schema, migration script from markdown, `crm_db.py` data access layer, Entra ID auth, Azure deployment. Oscar should ask for this spec when ready.
3. **Subsequent phase specs** — Each phase (I2-I6) gets its own spec as a Claude Code handoff when the previous phase is complete.

---

## Project Files State

After this conversation, project files should be:
- `CRM-ARCHITECTURE-FINAL.md` — keep (governs local Phases 1-4)
- `MOBILE-PWA-ARCHITECTURE.md` — keep (deferred to post-V1, may need revision later)
- `AREC-INTELLIGENCE-PLATFORM-ARCHITECTURE.md` — **ADD** (governs multi-user migration Phases I1-I6)
