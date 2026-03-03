# AREC System Build Audit — March 2, 2026

**Spec reviewed:** `AREC-Master-System-Spec-updated_2.md` (v1.0)
**Audited by:** Claude (Cowork session)
**Purpose:** Determine what has/hasn't been built per spec. Guide Claude Code priorities.

---

## Executive Summary

The **Cowork productivity plugin** and **CRM data layer** are substantially built and in daily use. The **Flask application** (dashboard, CRM UI, API routes, Graph auto-capture engine) **has not been built at all** — `~/arec-morning-briefing/` is empty. The **Mobile PWA** shell exists but has no backend to connect to. Three Cowork plugin skills (`/crm:interview`, `/crm:review`, `/crm:inbox`) are defined and functional. Two critical CRM files are missing.

---

## Component-by-Component Status

### Component 1 — Cowork Productivity Plugin

| Item | Spec Section | Status | Notes |
|------|-------------|--------|-------|
| CLAUDE.md (hot cache) | 3.4 | ✅ Built | ~30 contacts, terms, deals, preferences |
| TASKS.md | 3.3 | ✅ Built | Active/Personal/Waiting On/Done sections |
| inbox.md (voice capture) | 3.2 | ✅ Built | iPhone Shortcut integration working |
| Memory system (2-tier) | 3.4 | ✅ Built | glossary.md + people/ + projects/ + context/ |
| `/productivity:update` | 3.5 | ✅ Built | update.md skill file (11.6 KB), runs daily |
| `/productivity:start` | 3.5 | ✅ Built | Initialization command |
| `/productivity:task-management` | 3.5 | ✅ Built | Direct task interaction |
| `/productivity:memory-management` | 3.5 | ✅ Built | Add/update memory entries |
| CRM Pulse in `/productivity:update` | 3.7 | ✅ Built | Reads High urgency prospects, surfaces ≤2 observations |
| Pre-Meeting Intelligence in update | CLAUDE.md | ✅ Built | Calendar cross-ref with High urgency prospects |
| `/crm:interview` | 3.5 | ✅ Built | crm-interview.md skill (5.8 KB), first/delta modes |
| `/crm:review` | 3.5 | ✅ Built | crm-review.md skill (3.5 KB) |
| `/crm:inbox` | 3.5 | ✅ Built | crm-inbox.md skill (2.7 KB) |
| AI Email Inbox (`ai@avilacapital.com`) | 3.6 | ❌ Not built | No drain_inbox.py, no ai_inbox_queue.md file |
| SHORTCUT-SETUP.md | 3.2 | ✅ Built | iPhone Shortcuts documentation |

**Plugin verdict:** Core productivity system is production-ready. CRM intelligence skills are defined and functional within Cowork. The AI Email Inbox pipeline (Section 3.6) is not wired up.

---

### Component 2 — Morning Briefing Platform

| Item | Spec Section | Status | Notes |
|------|-------------|--------|-------|
| `main.py` orchestrator | 4.2 | ❌ Not built | `~/arec-morning-briefing/` is empty |
| `auth/graph_auth.py` | 4.2 | ❌ Not built | |
| `sources/ms_graph.py` | 4.2 | ❌ Not built | |
| `sources/memory_reader.py` | 4.2 | ❌ Not built | |
| `briefing/prompt_builder.py` | 4.2 | ❌ Not built | |
| `briefing/generator.py` | 4.2 | ❌ Not built | |
| `delivery/slack_sender.py` | 4.2 | ❌ Not built | |
| `delivery/slack_listener.py` | 4.2 | ❌ Not built | |
| `delivery/dashboard.py` | 4.2 | ❌ Not built | |
| Investor Intelligence in briefing | 4.4 | ❌ Not built | prompt_builder.py doesn't exist |
| Slack two-way interaction | 4.5 | ❌ Not built | |
| Web dashboard (3-column) | 4.6 | ❌ Not built | |
| launchd jobs (5 AM cron) | 2.6 | ❌ Not built | No plist files in LaunchAgents |

**Briefing verdict:** The entire Python application is unbuilt. No Flask server, no Graph auth, no Slack integration, no scheduled jobs. The spec Section 10.1 marks these as "✅ Production" — that appears to be aspirational or refers to an earlier version that was lost/reset.

---

### Component 3 — Investor CRM

#### Data Layer (Phase 1)

| Item | Spec Section | Status | Notes |
|------|-------------|--------|-------|
| `crm/config.md` | 5.3 | ✅ Built | Pipeline stages, org types, urgency, team |
| `crm/offerings.md` | 5.3 | ✅ Built | Fund II ($1B) + Mountain House Refi ($35M) |
| `crm/organizations.md` | 5.3 | ✅ Built | ~1,292 orgs imported |
| `crm/prospects.md` | 5.3 | ✅ Built | ~1,313 prospects, 344 KB, 15K+ lines |
| `crm/interactions.md` | 5.3 | ⚠️ Sparse | 1 entry only. Needs auto-capture to populate |
| `crm/contacts_index.md` | 5.3 | ⚠️ Sparse | 3 entries only (Tony, Jared, Matt) |
| `crm/unmatched_review.json` | 5.8 | ✅ Built | 2 unmatched items from auto-capture |
| `crm/contacts.md` | 5.3 | ⚠️ Should be deleted | Spec says ELIMINATED — 200 KB legacy file still present |
| `crm/ai_inbox_queue.md` | 3.6 | ❌ Missing | Referenced by /crm:inbox but file doesn't exist |
| `crm/pending_interviews.json` | 6.7 | ❌ Missing | Referenced by /productivity:update and /crm:interview |
| `sources/crm_reader.py` | 5.4 | ❌ Not built | Core parser module — all Flask routes depend on this |
| `scripts/import_prospects.py` | 5.9 | ❌ Not built | CSV import was done some other way (data exists) |

**Data layer verdict:** The markdown data files are populated and well-structured — the CSV import clearly happened. But the Python parser (`crm_reader.py`) that all downstream code depends on does not exist. The data is there; the code to read/write it programmatically is not.

#### UI & API (Phases 2–7)

| Item | Spec Section | Status |
|------|-------------|--------|
| Pipeline table (`/crm`) | 5.6 | ❌ Not built |
| Inline editing (PATCH API) | 5.5 | ❌ Not built |
| Org detail page (`/crm/org/<n>`) | 5.7 | ❌ Not built |
| Graph auto-capture (`crm_graph_sync.py`) | 5.8 | ❌ Not built |
| Dashboard cleanup (3-column) | 5.6 | ❌ Not built |
| All Flask API routes | 5.5 | ❌ Not built |

**CRM UI verdict:** Nothing built. Phases 2–7 are all unstarted.

---

### Component 4 — Intelligence Layer

| Item | Spec Section | Status | Notes |
|------|-------------|--------|-------|
| Intel file format | 6.2 | ✅ Defined | Standard sections: Relationship, Decision Dynamics, etc. |
| Intel files created | 6.2 | ⚠️ Partial | 7 files exist (5 internal people + 2 investor orgs) |
| `/crm:interview` skill | 6.6 | ✅ Built | First session + delta session modes |
| `/crm:review` skill | 6.5 | ✅ Built | Pipeline intelligence review |
| CRM Pulse in update | 6.4 | ✅ Built | ≤2 observations from High urgency prospects |
| Pre-meeting intel in update | 6.3 | ✅ Built | Calendar cross-ref in CLAUDE.md instructions |
| `pending_interviews.json` write | 6.7 | ❌ Not built | Requires crm_graph_sync.py (Phase 5) |
| Morning briefing enrichment | 6.3 | ❌ Not built | Requires prompt_builder.py |
| `crm_graph_sync.py` integration | 6.1 | ❌ Not built | Auto-capture engine doesn't exist |

**Intelligence verdict:** The Cowork-side intelligence (interview, review, pulse) works because it reads markdown files directly. The automated pipeline (auto-capture → pending interviews → briefing enrichment) is blocked by the missing Python application.

---

### Component 5 — Mobile PWA

| Item | Spec Section | Status | Notes |
|------|-------------|--------|-------|
| `arec-mobile.html` | 7.5 | ✅ Built | 83.8 KB single-file PWA |
| `manifest.json` | 7.5 | ✅ Built | PWA manifest configured |
| `sw.js` | 7.5 | ✅ Built | Service worker for offline |
| Icons (192 + 512) | 7.5 | ✅ Built | Both present |
| Tasks tab | 7.3 | ✅ Built | Reads/writes TASKS.md via Dropbox API |
| Pipeline tab | 7.3 | ✅ Built | Reads/writes prospects.md via Dropbox API |
| Dropbox API integration | 7.4 | ✅ Built | Download/upload/metadata endpoints |

**PWA verdict:** Built and deployable. Operates independently via Dropbox API (no Flask dependency). Spec says "Architecture designed, not yet built" in 7.1 — that's outdated; it is built.

---

## Critical Gaps (Action Items for Claude Code)

### Immediate Fixes (no code required)

| # | Action | Priority |
|---|--------|----------|
| 1 | Create empty `crm/ai_inbox_queue.md` | High — /crm:inbox references it |
| 2 | Create empty `crm/pending_interviews.json` with `{"pending": []}` | High — /productivity:update references it |
| 3 | Delete `crm/contacts.md` | Med — deprecated per spec, 200 KB dead weight |

### Python Application Build (the big gap)

The entire `~/arec-morning-briefing/` application is unbuilt. Build sequence per spec Section 10:

| Phase | What | Depends On | Effort Est. |
|-------|------|-----------|-------------|
| **1** | `crm_reader.py` + `import_prospects.py` + unit tests | Nothing | Medium |
| **2** | Flask app + pipeline table (read-only) | Phase 1 | Medium |
| **3** | Inline editing + PATCH API | Phase 2 | Small |
| **4** | Org detail page | Phase 3 | Small |
| **5** | `crm_graph_sync.py` + auto-capture + pending_interviews | Phase 4 | Large |
| **7** | Dashboard cleanup | Phase 5 | Small |

Separately (can parallel after Phase 1):

| Component | What | Effort Est. |
|-----------|------|-------------|
| **Auth** | `graph_auth.py` (MSAL device code flow) | Small |
| **Briefing** | `main.py` + `prompt_builder.py` + `generator.py` | Medium |
| **Delivery** | `slack_sender.py` + `slack_listener.py` | Medium |
| **Scheduling** | launchd plist files | Small |
| **Intelligence** | `prompt_builder.py` investor intel section | Small (after briefing works) |

### Spec Accuracy Issues

| Spec Claim | Reality |
|------------|---------|
| Section 10.1 lists Morning Briefing, Dashboard, Slack Listener, iPhone Capture as "✅ Production" | Only iPhone Capture is production. Others are unbuilt. |
| Section 7.1 says PWA is "not yet built" | PWA is built and functional |
| Section 5.3 says contacts.md is "ELIMINATED" | File still exists (200 KB) |

---

## Recommended Build Priority for Claude Code

**If you want the most immediate value:**

1. Create the two missing CRM files (ai_inbox_queue.md, pending_interviews.json) — 5 min
2. Delete contacts.md — 1 min
3. Build `crm_reader.py` (Phase 1) — this unlocks everything downstream
4. Build Flask app skeleton + pipeline table (Phases 2-3) — gives you a browser UI for the CRM data that already exists
5. Build `graph_auth.py` + `crm_graph_sync.py` (Phase 5) — auto-populates interactions.md and pending_interviews.json, which makes the intelligence layer actually work end-to-end

**What's already working well without any code:**
- The Cowork plugin skills (/crm:interview, /crm:review, /crm:inbox) work by reading/writing markdown directly
- The PWA works via Dropbox API
- The productivity system (tasks, memory, inbox) is fully operational
