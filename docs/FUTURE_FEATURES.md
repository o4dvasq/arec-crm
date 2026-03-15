# Future Features Log

**Last updated:** 2026-03-15

Features explicitly deferred from initial release. Each item has been discussed and intentionally postponed — do not implement until prioritized.

---

## Overwatch → CRM Cross-Read

**What:** Overwatch dashboard reads CRM data (via filesystem path) and displays CRM tasks assigned to Oscar in an "AREC Tasks" panel.
**Why deferred:** Get both systems stable independently before wiring them together.
**Depends on:** Overwatch scaffold (Phase 0B) + CRM cleanup (Phase 0A) both complete.
**Notes:** Read-only. Overwatch never writes to CRM files. Display only tasks where `assigned:Oscar` or `assigned:Tony` appears.

## iPhone Shortcuts → CRM Task Capture

**What:** Extend the existing iPhone voice capture shortcut to support a "CRM task" mode. Voice notes tagged as CRM flow into a CRM-specific inbox, get parsed during CRM /update, and become prospect tasks.
**Why deferred:** iPhone → Overwatch inbox flow works today. CRM routing is additive.
**Depends on:** Overwatch scaffold with inbox.md preserved, CRM task system stable.
**Notes:** Could be as simple as a second Shortcut that appends to `arec-crm/crm/task_inbox.md` instead of `overwatch/inbox.md`.

## Overwatch /update Command (Custom)

**What:** A dedicated Overwatch update command (separate from the productivity plugin's `/productivity:update`) that pulls from Gmail, iCloud Reminders, iCloud Calendar, and processes inbox.md.
**Why deferred:** The native productivity plugin's `/productivity:update` handles task sync and memory management. Build a custom one only once we know exactly what gaps remain after using the native plugin with the Overwatch repo.
**Depends on:** Gmail integration, iCloud integration, Overwatch scaffold.
**Notes:** May end up being a skill rather than replacing the plugin. The plugin's --comprehensive mode already scans email and calendar via MCP — if Gmail MCP works, we may not need custom code at all.

## Gmail Integration

**What:** Scan Oscar's personal Gmail for Overwatch-relevant emails. Match to personal contacts in `data/people/`. Store in `data/email_log.json`.
**Why deferred:** The productivity plugin already has Gmail MCP pre-configured (`https://gmail.mcp.claude.com/mcp`). Try the native MCP first before building custom Python code.
**Depends on:** Overwatch scaffold, Gmail MCP connector enabled.

## iCloud Calendar + Reminders Integration

**What:** Pull iCloud Calendar events and Reminders into Overwatch dashboard. Two approaches: CalDAV library or AppleScript/icalBuddy bridge.
**Why deferred:** Spec exists (`SPEC_icloud-calendar-reminders.md`) but lower priority than CRM stability. The productivity plugin has Google Calendar MCP — if Oscar uses Google Calendar instead of iCloud, this may not be needed.
**Depends on:** Overwatch scaffold.

## Teams Chat Scanning

**What:** Scan Microsoft Teams chats for CRM-relevant mentions (prospect names, org names). Store in `crm/chat_log.json`.
**Why deferred:** Graph scope `Chat.Read` is authorized but no implementation exists. Email scanning covers most intelligence needs.
**Depends on:** CRM cleanup complete, Graph auth working.

## Meeting Transcript Ingestion

**What:** Pull meeting transcripts from Microsoft Graph, parse into summaries and action items, feed into relationship briefs.
**Why deferred:** Requires Teams Premium licensing (may not be available). Heavy parsing work.
**Depends on:** CRM cleanup, meeting object promoted to first-class entity.

## Tony Excel Sync

**What:** Poll Tony's master Excel tracker on Egnyte daily, detect changes, fuzzy-match orgs, sync to prospects.md with human review.
**Why deferred:** Spec exists (`SPEC_tony-excel-sync.md`, backend-agnostic). Can be implemented anytime after CRM cleanup.
**Depends on:** CRM cleanup, Egnyte access.

## Meetings as First-Class CRM Object

**What:** Promote meetings from JSON file to proper entity with auto-calendar-scan, AI notes ingestion, meeting detail UI, standalone meetings list.
**Why deferred:** Spec exists (`SPEC_meetings-object.md`) but references Postgres tables. Needs scrubbing for markdown backend.
**Depends on:** CRM cleanup.
