# Claude Productivity — Architecture

> Load this file when discussing structural or architectural changes.
> Do NOT load for routine task/CRM/briefing work.

---

## System Overview

Claude Productivity is a personal productivity and CRM system built around Claude Code and the Claude desktop app (Cowork mode). It consists of three main layers:

1. **Intelligence Layer** — Claude skills, memory, and task management (Cowork / Claude Code)
2. **Web App** — Flask dashboard served locally (`app/`)
3. **Mobile PWA** — Lightweight AREC mobile app (`arec-mobile/`)

---

## Directory Map

```
ClaudeProductivity/
├── CLAUDE.md                  ← Working memory; always loaded
├── TASKS.md                   ← Single source of truth for tasks
├── inbox.md                   ← Voice-capture queue (iPhone Shortcuts)
├── config.yaml                ← App configuration
├── dashboard.html             ← Static dashboard entry point
│
├── docs/                      ← Architecture, decisions, specs (this folder)
│   ├── ARCHITECTURE.md        ← Loaded on demand; structural changes only
│   ├── DECISIONS.md           ← Append-only permanent decisions log
│   ├── PROJECT_STATE.md       ← Overwritten after each Claude Code session
│   └── specs/                 ← One SPEC_ file per feature
│       └── archive/           ← Completed / superseded specs
│
├── app/                       ← Flask backend (Python)
│   ├── main.py                ← App entry point
│   ├── auth/                  ← MS Graph OAuth
│   ├── briefing/              ← Morning briefing pipeline
│   ├── delivery/              ← Delivery/notification layer
│   ├── sources/               ← Data source connectors
│   ├── static/                ← Frontend assets
│   ├── templates/             ← Jinja2 HTML templates
│   └── tests/                 ← Unit tests
│
├── arec-mobile/               ← AREC Mobile PWA
│   ├── arec-mobile.html       ← Single-page app
│   └── manifest.json / sw.js  ← PWA manifests
│
├── crm/                       ← CRM data layer (JSON + markdown)
├── memory/                    ← Claude knowledge base (people, glossary, orgs)
├── meeting-summaries/         ← Auto-generated meeting notes
├── skills/                    ← Claude skills / plugin definitions
└── scripts/                   ← Utility scripts
```

---

## Core Data Flows

### Morning Briefing
`Outlook Calendar + Email` → `app/briefing/` → `dashboard.html`

### Task Management
`inbox.md` (voice capture) → `/productivity:update` → `TASKS.md`

### CRM Intelligence
`Outlook Archive` → `skills/email-scan.md` → `crm/email_log.json` → `crm/` org profiles

### Meeting Notes
`Notion (Teams meetings)` + `Outlook Calendar (in-person gaps)` → `meeting-summaries/YYYY-MM-DD-*.md`

---

## Key Technologies

| Layer | Stack |
|-------|-------|
| Backend | Python / Flask |
| Auth | MS Graph (OAuth, MSAL) |
| Frontend | Jinja2, vanilla JS, Tailwind |
| Mobile | PWA (HTML/JS, no framework) |
| Intelligence | Claude (Cowork / Claude Code) |
| Data | JSON files, Markdown, YAML |
| Integrations | Microsoft Graph, Notion API, Egnyte |

---

## Naming Conventions

- Specs: `SPEC_[FeatureName].md` in `docs/specs/`
- Meeting summaries: `YYYY-MM-DD-meeting-title-slug.md`
- CRM orgs: keyed by domain in `crm/orgs/`
- Memory files: `memory/people/[name].md`, `memory/glossary.md`
