# Claude Code Build Order & Parallelism Guide

**Date:** March 2, 2026
**Total specs:** 6 (CC-01 through CC-05, CC-07)
**Eliminated:** CC-06 (Slack Delivery) — briefing consumed natively in Cowork

---

## Project Root

Everything lives in one Dropbox-synced folder:

```
~/Dropbox/Tech/ClaudeProductivity/
├── CLAUDE.md, TASKS.md, inbox.md     ← Cowork data (existing)
├── memory/                            ← Knowledge base (existing)
├── crm/                               ← CRM data (existing)
├── specs/                             ← These spec files
├── app/                               ← Python application (NEW — all code goes here)
│   ├── main.py
│   ├── requirements.txt
│   ├── .env
│   ├── auth/
│   ├── sources/
│   ├── briefing/
│   ├── delivery/
│   ├── templates/
│   ├── static/
│   └── tests/
└── briefing_latest.md                 ← Morning briefing output (written by app)
```

**Why one folder:** All data and code in the same Dropbox tree. No cross-directory path resolution. Syncs to all three Macs. Secrets (.env) are fine — Oscar controls all devices.

## Dependency Graph

```
CC-01  crm_reader.py ──────┬──→ CC-02  Flask + Pipeline (Phases 2-3)
       (no deps)           │         └──→ CC-03  Org Detail (Phase 4)
                           │
                           └──→ CC-04  Graph Auth + Auto-Capture
                                      ├──→ CC-05  Morning Briefing
                                      └──→ CC-07  AI Email Inbox
```

## Parallelism Options

### Wave 1 (start immediately)

| Agent | Spec | Est. Effort |
|-------|------|-------------|
| Agent A | **CC-01** crm_reader.py | Medium — core parser, ~25 functions, tests |

CC-01 has no dependencies. Everything else depends on it. Start here.

### Wave 2 (after CC-01 passes tests)

These three can run in **parallel** — they import crm_reader but don't depend on each other:

| Agent | Spec | Est. Effort |
|-------|------|-------------|
| Agent B | **CC-02** Flask + Pipeline table | Medium — Flask app, CRM Blueprint, inline edit |
| Agent C | **CC-04** Graph Auth + Auto-Capture | Medium — 3 modules, Graph API, matching engine |
| Agent D | **CC-07** AI Email Inbox | Small — single script, shared mailbox polling |

### Wave 3 (after CC-02 and CC-04)

| Agent | Spec | Est. Effort |
|-------|------|-------------|
| Agent E | **CC-03** Org Detail page | Small — one page, reuses CC-02 patterns |
| Agent F | **CC-05** Morning Briefing | Medium — prompt builder, Claude API, investor intel |

## Delivery Model

The morning briefing is **not** delivered via Slack. Instead:
- `main.py` writes the briefing to `~/Dropbox/Tech/ClaudeProductivity/briefing_latest.md`
- Cowork's `/productivity:update` reads this file and presents it during the morning session
- The 5 AM launchd job still runs Graph fetch + auto-capture + briefing generation
- Output is also logged to `~/Library/Logs/arec-morning-briefing.log`

## What's Already Done (Cowork-side, not Claude Code)

- ✅ Created `crm/ai_inbox_queue.md` (was missing)
- ✅ Created `crm/pending_interviews.json` (was missing)
- ✅ Deleted `crm/contacts.md` (deprecated per spec)
- ✅ Cowork plugin skills already working: /crm:interview, /crm:review, /crm:inbox, /productivity:update

## Shared Setup (run once before any agent)

```bash
cd ~/Dropbox/Tech/ClaudeProductivity
mkdir -p app/{auth,sources,briefing,delivery,templates,static,scripts,tests/fixtures}
touch app/__init__.py
touch app/sources/__init__.py
touch app/auth/__init__.py
touch app/briefing/__init__.py
touch app/delivery/__init__.py

cat > app/requirements.txt << 'EOF'
anthropic>=0.25.0
msal>=1.28.0
requests>=2.31.0
pyyaml>=6.0
python-dotenv>=1.0.0
flask>=3.0.0
EOF

cat > app/.env.example << 'EOF'
ANTHROPIC_API_KEY=
AZURE_CLIENT_ID=
AZURE_TENANT_ID=
MS_USER_ID=
MS_SHARED_MAILBOX_ID=
EOF
```

## Notes for Claude Code Agents

- **Project root:** `~/Dropbox/Tech/ClaudeProductivity/`
- **App code root:** `~/Dropbox/Tech/ClaudeProductivity/app/`
- **CRM data:** `../crm/` relative to app, or use `PROJECT_ROOT` constant in crm_reader.py
- **Do not modify CRM markdown files** unless your spec explicitly calls for it
- **All CRM data access goes through crm_reader.py** — never parse markdown directly in Flask routes or other modules
- **prospects.md is 344 KB / 15,700 lines** — parse functions must handle this efficiently
- **No npm, no React, no build step** — vanilla HTML/CSS/JS only for frontend
- **No Slack dependency** — briefing output goes to markdown file, not Slack
