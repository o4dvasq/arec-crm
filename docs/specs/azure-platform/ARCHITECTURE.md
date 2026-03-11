# AREC Intelligence Platform — Architecture

**Author:** Oscar Vasquez, COO — Avila Real Estate Capital  
**Date:** March 8, 2026  
**Status:** Architecture Overview — Ready for Phased Spec Development  
**Supersedes:** MULTI-USER-CRM-ARCHITECTURE.md (the "CRM with logins" version)

---

## 1. What This Is

A shared intelligence platform for AREC's capital-raising team. The system passively scans the team's emails and calendars, accepts forwarded emails and quick notes, and uses AI to build a cumulative knowledge graph about every investor relationship. Each morning, every team member receives a personalized email briefing — their meetings for the day, enriched with everything the team collectively knows about each investor they're meeting.

The pipeline table (stages, targets, assignments) still exists as the operational CRM. But the core product is the intelligence layer, not the spreadsheet.

### The Value Proposition

Without this system, Zach walks into a meeting with Merseyside knowing only what he personally remembers. With this system, Zach's morning email tells him:

> **Merseyside Pension Fund — 10:30 AM call with Susannah Friar**
>
> *What we know:* Verbal at $50M for Fund II, targeting Final close. Oscar met with the team on March 2 and reported Susannah seemed hesitant on fund structure but responded well to track record discussion. James forwarded an email thread on March 5 showing their board meets in April and needs a GP recommendation by then. Patrick had a separate call with their external consultant who confirmed they're comparing us to two other managers.
>
> *Key signals:* April board deadline creates urgency. Structure concerns need addressing — consider preparing the Cayman structure memo. Competitive situation means we need to differentiate on track record.
>
> *Last touch:* March 5 (James, email). 3 days ago.

That briefing paragraph is the product. Everything else is infrastructure to make it possible.

### What Replaces What

| Current System | New System |
|---------------|------------|
| Markdown files in Dropbox | PostgreSQL on Azure |
| Claude Cowork writes local files | AI pipeline writes directly to cloud database |
| Oscar-only morning briefing (localhost) | Per-user email briefings for the whole team |
| Single-user Flask dashboard | Multi-user web app with Entra ID SSO |
| `crm_reader.py` parses markdown | `crm_db.py` queries Postgres |
| crm@avilacapllc.com shared mailbox (Oscar) | Same mailbox, now processes for all team members |
| Notion meeting transcripts (Oscar only) | Teams Meeting Notes for the whole team |
| `/productivity:update` via Cowork | Cloud-native intelligence pipeline replaces it |

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AZURE CLOUD                              │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              INTELLIGENCE PIPELINE                      │    │
│  │                                                         │    │
│  │  ┌──────────┐  ┌──────────┐  ┌────────────────────┐    │    │
│  │  │  Graph    │  │  Email   │  │  Meeting           │    │    │
│  │  │  Scanner  │  │  Inbox   │  │  Transcript        │    │    │
│  │  │          │  │  Processor│  │  Processor         │    │    │
│  │  │ (8 users │  │          │  │                    │    │    │
│  │  │  mail +  │  │ crm@     │  │  Teams Meeting     │    │    │
│  │  │  calendar)│  │ avila    │  │  Notes             │    │    │
│  │  └────┬─────┘  └────┬─────┘  └────────┬───────────┘    │    │
│  │       │              │                 │                │    │
│  │       ▼              ▼                 ▼                │    │
│  │  ┌──────────────────────────────────────────────────┐   │    │
│  │  │           AI ATTRIBUTION ENGINE                  │   │    │
│  │  │                                                  │   │    │
│  │  │  • Match email/meeting to prospect + org         │   │    │
│  │  │  • Identify which team member(s) were involved   │   │    │
│  │  │  • Extract key signals and relationship context  │   │    │
│  │  │  • Detect intent signals (interest, hesitation,  │   │    │
│  │  │    competitive mentions, timeline pressure)      │   │    │
│  │  │  • Write structured intelligence to database     │   │    │
│  │  └──────────────────────┬───────────────────────────┘   │    │
│  │                         │                               │    │
│  └─────────────────────────┼───────────────────────────────┘    │
│                            ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    POSTGRESQL                             │   │
│  │                                                           │   │
│  │  offerings, organizations, contacts, prospects            │   │
│  │  interactions, intelligence_notes, signals                │   │
│  │  users, email_scan_log, briefing_history                  │   │
│  └──────────────────────────────────┬────────────────────────┘   │
│                                     │                            │
│        ┌────────────────────────────┼──────────────────┐         │
│        ▼                            ▼                  ▼         │
│  ┌───────────┐            ┌──────────────┐    ┌──────────────┐   │
│  │  Flask    │            │  Briefing    │    │  Entra ID    │   │
│  │  Web App  │            │  Engine      │    │  (SSO)       │   │
│  │           │            │              │    │              │   │
│  │  Pipeline │            │  6 AM daily: │    │  8 AREC      │   │
│  │  table,   │            │  per-user    │    │  team        │   │
│  │  org      │            │  email       │    │  members     │   │
│  │  detail,  │            │  briefing    │    │              │   │
│  │  inline   │            │              │    └──────────────┘   │
│  │  editing  │            └──────┬───────┘                       │
│  └───────────┘                   │                               │
│                                  ▼                               │
│                          ┌──────────────┐                        │
│                          │  SendGrid /  │                        │
│                          │  Azure Comm  │                        │
│                          │  Services    │                        │
│                          └──────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
         │                          │
    HTTPS │                         │ Email
         ▼                          ▼
    ┌───────────┐            ┌────────────────┐
    │  Team     │            │  Team inboxes  │
    │  browsers │            │  (Outlook)     │
    └───────────┘            └────────────────┘
```

---

## 3. The Intelligence Model

This is the core of the system. Instead of a flat "Notes" text field on a prospect record, intelligence is stored as a structured, attributed, timestamped stream of knowledge.

### 3.1 Three Layers of Intelligence

**Layer 1 — Interactions (facts)**
What happened. Automatically captured from Graph or manually logged.

> *March 2, 2026 — Meeting — Oscar Vasquez, Susannah Friar, Dragos Serbanica*
> *Subject: Fund II deep dive*
> *Source: auto-graph (calendar)*

**Layer 2 — Intelligence Notes (interpretation)**
What it means. AI-extracted from email content, meeting transcripts, or manually contributed by a team member. Attributed to the person who contributed it.

> *March 2, 2026 — Oscar Vasquez:*
> *"Susannah seemed hesitant on the Cayman fund structure but warmed up significantly when we walked through Fund I track record. Dragos was quiet — may need to engage him separately. They mentioned comparing us to two other GPs but wouldn't name them."*

> *March 5, 2026 — AI-extracted from James Walton forwarded email:*
> *"Merseyside board meets in April. Investment committee needs to present GP recommendation before then. Timeline creates natural urgency for a close."*

**Layer 3 — Signals (AI-detected patterns)**
Structured tags the AI assigns to intelligence notes for filtering and briefing prioritization.

| Signal Type | Example |
|------------|---------|
| `timeline_pressure` | Board meeting in April |
| `competitive_mention` | Comparing to other GPs |
| `hesitation` | Concerns about fund structure |
| `positive_momentum` | Responded well to track record |
| `key_contact_shift` | New decision-maker identified |
| `document_request` | Asked for specific materials |
| `commitment_signal` | Verbal indication of amount |

Signals power the briefing engine. A prospect with `timeline_pressure` + `hesitation` gets flagged differently than one with `positive_momentum` + `commitment_signal`.

### 3.2 Attribution Model

Every piece of intelligence is attributed:

- **Who contributed it** — the team member (or "system" for auto-capture)
- **How it was captured** — Graph scan, forwarded email, manual note, meeting transcript
- **When** — timestamp
- **Confidence** — auto-extracted vs. human-confirmed

This means the briefing can say: *"Oscar reported on March 2 that..."* and *"Based on an email James forwarded on March 5..."* — the AI synthesizes, but the attribution is preserved.

### 3.3 Knowledge Is Shared, Briefings Are Personal

All intelligence is visible to all team members. There are no private notes. The personalization happens at the briefing layer:

- **Oscar's briefing** emphasizes his meetings, his assigned prospects, and flags things that changed since his last touch
- **Zach's briefing** emphasizes his meetings and prospects, but includes intelligence from Oscar and James about shared prospects
- **Tony's briefing** is a high-level summary — pipeline movement, key signals across all prospects, anything requiring his attention

The same database, different lenses.

---

## 4. Intelligence Capture Pipeline

### 4.1 Graph Scanner (Automatic)

Runs daily at ~5 AM (before briefings). Scans all 8 team members' mailboxes and calendars via Microsoft Graph with application-level permissions (admin consent).

**Email scanning:**
- For each team member, pull emails from the last 24 hours
- Match sender/recipient against known contacts in the CRM
- For matched emails: create an interaction record + AI-extract intelligence
- AI processes the email body to extract signals and key context
- Skip internal-only emails (all participants are AREC team)
- Skip noise (newsletters, automated notifications) via heuristics

**Calendar scanning:**
- For each team member, pull today's and tomorrow's calendar events
- Match attendees against known contacts
- Create interaction records for meetings with investor contacts
- Flag today's meetings for briefing emphasis

**Graph permissions required:**
- `Mail.Read` (application-level, all users)
- `Calendars.Read` (application-level, all users)
- Single app registration with admin consent
- Restricted to AREC tenant

### 4.2 Shared Mailbox Processor (Semi-Automatic)

The existing crm@avilacapllc.com shared mailbox pattern extends to the whole team.

**How it works:**
1. Team member forwards an email to crm@avilacapllc.com
2. Optionally adds a note above the forwarded content (e.g., "She's leaning yes but worried about structure")
3. The processor picks it up, identifies the forwarder, matches the email thread to a prospect/org
4. Creates an interaction + intelligence note, attributed to the forwarder
5. The forwarder's personal note becomes a high-confidence intelligence note (human-contributed, not AI-inferred)

**Advantages over Graph scanning alone:**
- The team member is choosing to flag this email as important
- The personal note adds interpretation the AI can't infer from the email alone
- It's the same workflow pattern already proven with Oscar

### 4.3 Meeting Transcript Processor (Phase I5)

**Teams Meeting Notes (default for all team members):**
- Teams Meeting Notes is the standard transcript capture for the whole team
- Transcripts are available via Microsoft Graph for meetings with CRM contacts
- AI summarizes and extracts intelligence, attributed to attending team members

**Notion (Oscar only — not a platform integration):**
- Oscar uses Notion for personal meeting notes/transcripts
- This is a local workflow managed through Cowork, not a first-class integration in the platform
- If Oscar's Notion notes need to feed the intelligence pipeline, he can forward key excerpts to crm@avilacapllc.com or add them as manual notes in the web UI

### 4.4 Manual Notes via Web UI

For anything that doesn't come through email or meetings:

- On the prospect detail page, a simple text input: "Add intelligence note"
- Team member types a quick note, attributed to them
- AI processes for signals
- Lowest friction digital capture for in-the-moment context

---

## 5. Briefing Engine

### 5.1 How It Works

Runs daily at 6 AM via Azure Function. For each active team member:

1. **Pull their calendar** — who are they meeting today?
2. **For each meeting with a CRM contact:**
   - Gather all intelligence notes for that prospect (from all team members)
   - Gather recent interactions (last 30 days)
   - Identify active signals
   - Synthesize into a briefing paragraph via Claude API
3. **Prospect alerts:**
   - Prospects assigned to this user not touched in 14+ days
   - Stage changes since last briefing on prospects they're involved with
   - New intelligence from other team members on their prospects
4. **Executive summary (Tony, Oscar only):**
   - Pipeline movement summary
   - Commitment progress
   - High-urgency signals across all prospects
5. **Compose and send** — HTML email via SendGrid or Azure Communication Services

### 5.2 Briefing Email Format

```
Subject: AREC Briefing — Tuesday, March 10

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR MEETINGS TODAY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MERSEYSIDE PENSION FUND — 10:30 AM
Susannah Friar, Dragos Serbanica
Fund II · 6. Verbal · $50M · Final close
Assigned: James Walton

  What we know: [AI-synthesized paragraph drawing from all team
  members' interactions and intelligence notes. Attributed:
  "Oscar noted on March 2 that..." "An email James forwarded
  on March 5 indicates..."]

  Key signals: ⏰ April board deadline · ⚔️ Competitive
  situation · ⚠️ Structure concerns unresolved

  Suggested prep: [AI-generated based on signals — e.g.,
  "Consider bringing the Cayman structure memo. Track record
  comparison may differentiate vs. competing GPs."]

NPS (KOREA SWF) — 2:00 PM
[...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR PROSPECTS — WHAT'S NEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Merseyside: James forwarded new email thread (March 5).
  Board deadline confirmed for April.

• CalPERS: No activity in 16 days. Last touch: Feb 22 (Oscar).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PIPELINE SNAPSHOT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Fund II: $156M / $1B (16%)
67 prospects · 4 at Verbal · 12 at Interested

[View full pipeline → https://crm.avilacapllc.com/crm]
```

### 5.3 Briefing Personalization Rules

| Team Member | Briefing Scope |
|-------------|---------------|
| **Tony Avila** (CEO) | Executive: pipeline summary, commitment progress, high-urgency signals, his meetings only |
| **Oscar Vasquez** (COO) | Full: all meetings, all pipeline intelligence, staleness alerts, team activity summary |
| **Truman Flynn** (VP IR) | Standard: his meetings, his assigned prospects, new intelligence from teammates on shared prospects |
| **Zach Reisner** (IR) | Standard: his meetings, his assigned prospects, competitive intelligence signals |
| **James Walton** | Standard: his meetings, his assigned prospects |
| **Others** | Standard: their meetings, their assigned prospects |

Configurable per user via `briefing_scope` field (`executive`, `full`, `standard`, `minimal`).

---

## 6. Database Schema

### 6.1 Enums

```sql
CREATE TYPE org_type AS ENUM ('INSTITUTIONAL', 'HNWI / FO', 'BUILDER', 'INTRODUCER');
CREATE TYPE urgency_level AS ENUM ('High', 'Med', 'Low');
CREATE TYPE closing_option AS ENUM ('1st', '2nd', 'Final');
CREATE TYPE interaction_type AS ENUM (
    'Email', 'Meeting', 'Call', 'Note', 'Document Sent', 'Document Received'
);
CREATE TYPE interaction_source AS ENUM (
    'manual', 'auto-graph', 'auto-teams', 'forwarded-email'
);
CREATE TYPE capture_method AS ENUM (
    'graph_scan', 'forwarded_email', 'meeting_transcript', 'manual', 'ai_extracted'
);
CREATE TYPE confidence_level AS ENUM ('human_confirmed', 'ai_inferred');
CREATE TYPE signal_strength AS ENUM ('strong', 'moderate', 'weak');
CREATE TYPE briefing_scope AS ENUM ('executive', 'full', 'standard', 'minimal');
```

### 6.2 Core CRM Tables

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    entra_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    briefing_enabled BOOLEAN DEFAULT true,
    briefing_scope briefing_scope DEFAULT 'standard',
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

CREATE TABLE offerings (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    target BIGINT,
    hard_cap BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by INTEGER REFERENCES users(id)
);

CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    type org_type NOT NULL,
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by INTEGER REFERENCES users(id)
);

CREATE TABLE contacts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    title VARCHAR(255) DEFAULT '',
    email VARCHAR(255) DEFAULT '',
    phone VARCHAR(255) DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by INTEGER REFERENCES users(id),
    UNIQUE(name, organization_id)
);

CREATE TABLE prospects (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    offering_id INTEGER NOT NULL REFERENCES offerings(id) ON DELETE CASCADE,
    stage VARCHAR(50) NOT NULL DEFAULT '1. New Lead',
    target BIGINT DEFAULT 0,
    committed BIGINT DEFAULT 0,
    primary_contact_id INTEGER REFERENCES contacts(id),
    closing closing_option,
    urgency urgency_level,
    assigned_to INTEGER REFERENCES users(id),
    next_action TEXT DEFAULT '',
    last_touch DATE,
    disambiguator VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by INTEGER REFERENCES users(id),
    UNIQUE(organization_id, offering_id, disambiguator)
);

CREATE TABLE pipeline_stages (
    id SERIAL PRIMARY KEY,
    number INTEGER UNIQUE,
    name VARCHAR(100) UNIQUE NOT NULL,
    is_terminal BOOLEAN DEFAULT false,
    sort_order INTEGER NOT NULL
);
```

### 6.3 Intelligence Tables

```sql
CREATE TABLE interactions (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    offering_id INTEGER REFERENCES offerings(id),
    contact_id INTEGER REFERENCES contacts(id),
    interaction_date DATE NOT NULL,
    type interaction_type NOT NULL,
    subject VARCHAR(500) DEFAULT '',
    summary TEXT DEFAULT '',
    source interaction_source DEFAULT 'manual',
    source_ref VARCHAR(500) DEFAULT '',
    team_members INTEGER[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id)
);

CREATE TABLE intelligence_notes (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    prospect_id INTEGER REFERENCES prospects(id),
    interaction_id INTEGER REFERENCES interactions(id),
    contributed_by INTEGER REFERENCES users(id),
    content TEXT NOT NULL,
    capture_method capture_method NOT NULL,
    confidence confidence_level DEFAULT 'ai_inferred',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE signals (
    id SERIAL PRIMARY KEY,
    intelligence_note_id INTEGER NOT NULL REFERENCES intelligence_notes(id) ON DELETE CASCADE,
    signal_type VARCHAR(100) NOT NULL,
    detail TEXT DEFAULT '',
    strength signal_strength DEFAULT 'moderate',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE email_scan_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    graph_message_id VARCHAR(500) UNIQUE NOT NULL,
    scanned_at TIMESTAMP DEFAULT NOW(),
    matched_org_id INTEGER REFERENCES organizations(id),
    result VARCHAR(50) NOT NULL
);

CREATE TABLE briefing_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    briefing_date DATE NOT NULL,
    content_html TEXT NOT NULL,
    prospect_ids INTEGER[] DEFAULT '{}',
    sent_at TIMESTAMP,
    UNIQUE(user_id, briefing_date)
);
```

### 6.4 Indexes

```sql
CREATE INDEX idx_intel_notes_org ON intelligence_notes(organization_id);
CREATE INDEX idx_intel_notes_prospect ON intelligence_notes(prospect_id);
CREATE INDEX idx_intel_notes_date ON intelligence_notes(created_at);
CREATE INDEX idx_signals_type ON signals(signal_type);
CREATE INDEX idx_interactions_org ON interactions(organization_id);
CREATE INDEX idx_interactions_date ON interactions(interaction_date);
CREATE INDEX idx_email_scan_msg ON email_scan_log(graph_message_id);
CREATE INDEX idx_prospects_offering ON prospects(offering_id);
CREATE INDEX idx_prospects_org ON prospects(organization_id);
CREATE INDEX idx_contacts_org ON contacts(organization_id);
```

### 6.5 Key Schema Decisions

**`intelligence_notes` is separate from `interactions`.** An interaction is a fact (a meeting happened). An intelligence note is an interpretation (here's what we learned). One interaction can produce multiple intelligence notes. An intelligence note can also exist without an interaction (someone just knows something).

**`signals` are linked to intelligence notes, not to prospects directly.** This preserves provenance. You can trace: this prospect has `timeline_pressure` because of this intelligence note, contributed by James, extracted from this forwarded email, on this date.

**`team_members` on interactions is an array.** A meeting can involve multiple AREC team members. This lets the briefing say "Oscar and James met with Merseyside on March 2."

**`briefing_history` stores rendered HTML.** Audit trail and lets team members revisit past briefings. Also useful for debugging the briefing engine.

**Prospect `notes` field is gone.** Replaced entirely by the `intelligence_notes` stream. The flat Notes field was doing double duty as interaction history and context — those are now separate first-class entities.

**Currency stored as BIGINT (cents).** `$50,000,000` stored as `5000000000`. Standard practice for financial applications.

**Single `assigned_to` FK.** Consistent with the recent single-owner simplification. If multi-assign is needed later, a junction table can be added.

---

## 7. Web UI Changes

### 7.1 What Stays From Local CRM

- Pipeline table at `/crm` — sortable, filterable, inline-editable
- Offering tabs with commitment progress
- Organization detail pages with contacts and prospects across offerings
- Filter bar (Stage, Type, Urgency, Closing, Assigned To)
- Inline editing (dropdowns, inputs, save on blur)

### 7.2 What Changes

**Prospect / Org detail page — Intelligence Timeline:**
- Below the editable fields, a chronological stream replaces the flat Notes field
- Each entry: date, contributor (avatar/initials), capture method icon, content
- Signal badges inline
- "Add note" input at top of timeline
- Expandable interaction details (click to see full email summary)

**Pipeline table:**
- `Notes` column removed (intelligence lives on detail page)
- `Last Modified By` column added
- Everything else stays

**New page: Team Activity Feed** (`/crm/activity`)
- Chronological feed of all CRM activity across the team
- Filterable by team member, prospect, signal type
- For Oscar/Tony: see what the team is doing at a glance

### 7.3 No Analytics Page in V1

Briefing email covers the pipeline snapshot. Dedicated analytics can come later.

---

## 8. Technology Stack

| Layer | Technology |
|-------|-----------|
| Web framework | Flask |
| Database | PostgreSQL on Azure Flexible Server |
| ORM | SQLAlchemy |
| Auth | MSAL (Microsoft Authentication Library) for Python |
| AI / LLM | Claude API (Anthropic) for intelligence extraction + briefing synthesis |
| Email sending | Azure Communication Services or SendGrid |
| Email scanning | Microsoft Graph API (application permissions) |
| Meeting transcripts | Teams Meeting Notes via Microsoft Graph |
| Hosting | Azure App Service |
| Secrets | Azure Key Vault |
| Scheduling | Azure Functions (timer triggers) |
| Frontend | Vanilla HTML/CSS/JS |

---

## 9. Implementation Phases

### Prerequisite: Complete Local CRM Phases 1–4
Finish the existing local CRM build first. This gives us working pipeline table, org detail pages, inline editing, and the full data model proven. The UI ports directly.

### Parallel Pilot Strategy
Oscar will pilot the Azure platform while maintaining the existing local/Cowork CRM in parallel. Both systems run simultaneously during testing and QA. Cutover to Azure-only happens once Oscar is confident the new system is stable and the team is onboarded. No Cowork bridge is needed — the local system simply stays running until it's no longer needed.

---

### Phase I1: Database + Auth + Core Web App
**Goal:** Multi-user CRM on Azure with Postgres and Entra ID.  
**Deliverable:** Team can log in and use the pipeline table.

- Postgres schema (Section 6)
- `crm_db.py` replacing `crm_reader.py` (same function signatures)
- Migration script: markdown files → Postgres
- Entra ID integration
- Deploy to Azure App Service
- Pipeline table, org detail, inline editing — same UI, new backend

---

### Phase I2: Graph Scanner + Email Processor
**Goal:** Automatic intelligence capture from team email and calendars.  
**Deliverable:** System passively records interactions and extracts intelligence.

- Graph app registration with application-level permissions
- Email scanner: 8 mailboxes, last 24 hours, match against CRM contacts
- Calendar scanner: today's events, match attendees
- AI attribution engine: Claude API extracts intelligence notes + signals
- Shared mailbox processor: crm@avilacapllc.com for all team members
- Email scan deduplication log
- Scheduled Azure Function (5 AM daily)

---

### Phase I3: Intelligence UI
**Goal:** Intelligence timeline on prospect detail, team activity feed.  
**Deliverable:** Full intelligence picture visible in the web UI.

- Intelligence timeline component on org/prospect detail pages
- "Add note" manual input with signal detection
- Signal badges
- Team activity feed (`/crm/activity`)
- `Last Modified By` on pipeline table

---

### Phase I4: Briefing Engine
**Goal:** Personalized morning email briefings for every team member.  
**Deliverable:** Daily emails at 6 AM.

- Per-user calendar pull → prospect matching → intelligence gathering → Claude API synthesis
- HTML email template (Section 5.2)
- Briefing personalization per user role
- Email delivery via Azure Communication Services or SendGrid
- Briefing history storage
- Scheduled Azure Function (6 AM daily)

---

### Phase I5: Meeting Transcript Integration
**Goal:** Teams Meeting Notes transcripts feed the intelligence pipeline.  
**Deliverable:** Teams transcripts processed and attributed.

- Teams Meeting Notes pull via Microsoft Graph
- AI processing: summarize, extract intelligence, detect signals
- Attribution to attending team members
- Note: Notion is Oscar's personal workflow only — not integrated into the platform

---

## 10. AI Usage and Costs

| Operation | Frequency | Estimated Calls/Day |
|-----------|-----------|-------------------|
| Email intelligence extraction | Per matched email, daily | ~20-50 |
| Meeting transcript summarization | Per meeting with CRM contacts | ~5-10 |
| Signal detection | Per intelligence note | ~20-50 |
| Briefing synthesis | Per user per meeting-day prospect | ~15-30 |
| Forwarded email processing | As received | ~5-10 |

Estimated daily Claude API usage: 75–150 calls. At Sonnet pricing, likely under $5/day.

---

## 11. Azure Cost Estimate

| Service | Tier | Monthly Cost |
|---------|------|-------------|
| App Service | B1 (Basic) | ~$13 |
| PostgreSQL Flexible Server | Burstable B1ms | ~$13 |
| Azure Functions | Consumption | ~$0 (free tier covers this volume) |
| Key Vault | Standard | ~$0.03/10K operations |
| Communication Services (email) | Pay-as-you-go | ~$1-2 |
| **Total** | | **~$30/month** |

Claude API costs estimated at ~$100-150/month separately.

---

## 12. Migration Path

```
LOCAL (current)                      AZURE (target)
───────────────                      ───────────────
prospects.md        ──migrate──▶     prospects table
organizations.md    ──migrate──▶     organizations table
contacts.md         ──migrate──▶     contacts table
offerings.md        ──migrate──▶     offerings table
interactions.md     ──migrate──▶     interactions table
config.md           ──migrate──▶     pipeline_stages + enums

TASKS.md            ──stays──▶       Dropbox (unchanged)
memory/people/*.md  ──stays──▶       Local KB (Cowork, unchanged)
crm_reader.py       ──replaced──▶    crm_db.py
dashboard.py (CRM)  ──deployed──▶    Azure App Service
main.py (briefing)  ──stays local──▶ Reads from Azure API

NOTE: Local/Cowork CRM runs in parallel during pilot.
Both systems operational until Azure cutover confirmed.
```

---

## 13. What Oscar's Day Looks Like After

**6:00 AM** — Oscar's phone buzzes. Email from AREC Intelligence Platform.

The briefing shows three meetings today. For each one, a paragraph synthesizes everything the team knows — Truman's call notes from last week, an email Zach forwarded, the timeline pressure the AI detected.

**9:30 AM** — After a meeting with CalPERS, Oscar opens crm.avilacapllc.com, navigates to CalPERS, types: "Jane pushing for 2nd close commitment. Wants updated track record by Friday." The AI tags it `commitment_signal` + `document_request`.

**10:00 AM** — Truman has a call with CalPERS. His briefing tomorrow morning will include: *"Oscar met with Jane at 9:30 and reported she's pushing for a 2nd close commitment and wants an updated track record by Friday."*

The intelligence compounds. Every team member's briefing gets smarter.

---

## 14. Acceptance Criteria

### Phase I1 (Database + Auth + Web App)
1. ✅ All prospect data migrated to Postgres with zero loss
2. ✅ 8 team members log in via Microsoft SSO
3. ✅ Pipeline table, org detail, inline editing functional
4. ✅ `updated_by` tracked and displayed

### Phase I2 (Graph Scanner + Email Processor)
5. ✅ Graph scans 8 mailboxes daily without errors
6. ✅ Matched emails create interactions + intelligence notes
7. ✅ Calendar events matched and recorded
8. ✅ Forwarded emails to crm@avilacapllc.com processed and attributed
9. ✅ No duplicate processing

### Phase I3 (Intelligence UI)
10. ✅ Intelligence timeline on every prospect detail page
11. ✅ Manual notes attributed to logged-in user
12. ✅ Signal badges display on intelligence entries
13. ✅ Team activity feed works

### Phase I4 (Briefing Engine)
14. ✅ Personalized briefing email delivered to each team member by 6:30 AM
15. ✅ Briefings include today's meetings with synthesized intelligence
16. ✅ Staleness alerts and pipeline updates included
17. ✅ Briefing history stored

### Phase I5 (Meeting Transcripts)
18. ✅ Teams Meeting Notes transcripts automatically processed and attributed
19. ✅ Extracted intelligence appears on prospect timelines
