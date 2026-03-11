# AREC Mobile PWA — Architecture Spec

**Author:** Oscar Vasquez, COO — Avila Real Estate Capital  
**Date:** February 28, 2026  
**Status:** Architecture Complete  
**Companion to:** CRM Architecture v4 (FINAL)

---

## 1. Purpose

A single-file Progressive Web App (PWA) that provides a mobile-optimized UI for managing tasks and investor prospects directly from an iPhone. The app reads and writes markdown files in Dropbox — the same `TASKS.md` and `crm/*.md` files used by the desktop dashboard and Claude Cowork. No server required. Bookmark it to the home screen and it looks and behaves like a native app.

---

## 2. Design Principles

1. **Single HTML file.** One self-contained file with embedded CSS and JS. No build step, no dependencies, no server. Host it anywhere (Dropbox itself, GitHub Pages, or just open it locally).
2. **Dropbox is the backend.** Read/write files via Dropbox HTTP API. Dropbox sync propagates changes to all devices.
3. **Offline-capable.** Cache file contents in localStorage. Edit offline, sync when connection returns.
4. **Phone-first.** Designed for iPhone Safari. Touch targets ≥ 44px. Swipe gestures. Bottom tab bar. No hover states.
5. **Same markdown format.** Reads and writes the exact same file format as `crm_reader.py` and the desktop dashboard. No format conversion, no parallel data store.

---

## 3. Dropbox API Integration

### 3.1 Authentication

**Dropbox App Setup (one-time):**
1. Create a Dropbox App at https://www.dropbox.com/developers/apps
2. App type: Scoped access
3. Scope: `files.content.read`, `files.content.write`
4. Access type: App folder OR Full Dropbox (Full needed since files are in `~/Dropbox/Tech/ClaudeProductivity/`)
5. Generate a long-lived access token (or use refresh token flow)

**In the PWA:**
- Store the access token in localStorage (single-user app, acceptable security for personal use)
- First launch: prompt for token paste (one-time setup screen)
- All API calls include `Authorization: Bearer {token}` header

### 3.2 API Calls Used

Only three Dropbox endpoints needed:

**Read a file:**
```
POST https://content.dropboxapi.com/2/files/download
Headers:
  Authorization: Bearer {token}
  Dropbox-API-Arg: {"path": "/Tech/ClaudeProductivity/TASKS.md"}
Response: raw file content
```

**Write a file:**
```
POST https://content.dropboxapi.com/2/files/upload
Headers:
  Authorization: Bearer {token}
  Dropbox-API-Arg: {"path": "/Tech/ClaudeProductivity/TASKS.md", "mode": "overwrite"}
  Content-Type: application/octet-stream
Body: raw file content
```

**Get file metadata (for change detection):**
```
POST https://api.dropboxapi.com/2/files/get_metadata
Headers:
  Authorization: Bearer {token}
Body: {"path": "/Tech/ClaudeProductivity/TASKS.md"}
Response: includes content_hash for change detection
```

### 3.3 File Paths

| File | Dropbox Path | Purpose |
|------|-------------|---------|
| TASKS.md | /Tech/ClaudeProductivity/TASKS.md | Task list |
| prospects.md | /Tech/ClaudeProductivity/crm/prospects.md | Prospect records |
| organizations.md | /Tech/ClaudeProductivity/crm/organizations.md | Org type for display |
| config.md | /Tech/ClaudeProductivity/crm/config.md | Pipeline stages, types, urgency, team |
| offerings.md | /Tech/ClaudeProductivity/crm/offerings.md | Offering names and targets |

### 3.4 Sync Strategy

**On app open:**
1. Load cached files from localStorage (instant render)
2. Fetch fresh files from Dropbox in background
3. If content_hash changed → update localStorage + re-render
4. If no network → use cached version, show "Offline" indicator

**On edit:**
1. Update localStorage immediately (instant UI response)
2. Write to Dropbox API in background
3. If write fails (offline) → queue in localStorage as pending write
4. On next app open or network return → flush pending writes
5. Show subtle sync indicator: ✓ synced / ↻ syncing / ⚠ pending

**Conflict handling:**
- Last write wins (same as desktop — no conflict resolution per architecture decision)
- Pending offline edits are applied on next sync, may overwrite remote changes
- This is acceptable for single-user system

---

## 4. App Structure

### 4.1 Shell

```
┌─────────────────────────────┐
│  AREC                    ↻  │  ← Header: title + sync status
├─────────────────────────────┤
│                             │
│                             │
│       (content area)        │  ← Scrollable content
│                             │
│                             │
├─────────────────────────────┤
│  ☑ Tasks    │  📊 Pipeline  │  ← Bottom tab bar (fixed)
└─────────────────────────────┘
```

- **Header:** "AREC" left, sync indicator right (✓ / ↻ / ⚠)
- **Content area:** full-height scrollable, swipe between tabs
- **Bottom tab bar:** two tabs, fixed at bottom, 50px tall
- **Add to Home Screen:** includes PWA manifest for icon, splash screen, standalone mode (hides Safari chrome)

### 4.2 Color Palette (matches desktop dashboard)

- Background: `#f8f9fa`
- Header/tab bar: `#1a1a2e`
- Primary accent: `#3b82f6`
- Urgency High: `#ef4444`
- Urgency Med: `#f59e0b`
- Urgency Low / default: `#9ca3af`
- Success/complete: `#22c55e`
- Text: `#1f2937`

---

## 5. Tasks Tab

### 5.1 Layout

```
┌─────────────────────────────┐
│  AREC                    ✓  │
├─────────────────────────────┤
│  + Add Task                 │  ← Sticky input bar
├─────────────────────────────┤
│                             │
│  IR / FUNDRAISING        ▼  │  ← Section header (collapsible)
│  ┌─────────────────────────┐│
│  │ 🔴 Call Drew re: Fund II ││  ← Task card (swipe to complete)
│  │ 🟡 Send IRR deck        ││
│  │ ⚪ Update CRM notes     ││
│  └─────────────────────────┘│
│                             │
│  OPERATIONS              ▼  │
│  ┌─────────────────────────┐│
│  │ 🔴 Q4 board deck draft  ││
│  │ 🟡 Review lease abstract ││
│  └─────────────────────────┘│
│                             │
│  PERSONAL                ▼  │
│  ┌─────────────────────────┐│
│  │ ⚪ Renew passport       ││
│  └─────────────────────────┘│
│                             │
│  WAITING ON              ▼  │
│  ┌─────────────────────────┐│
│  │ ⚪ Tony: LP agreement   ││
│  └─────────────────────────┘│
│                             │
├─────────────────────────────┤
│  ☑ Tasks    │  📊 Pipeline  │
└─────────────────────────────┘
```

### 5.2 Task Card

Each task is a horizontal card:

```
┌──────────────────────────────────┐
│ 🔴  Call Drew re: Fund II        │
│     due 3/5 · for Tony           │
└──────────────────────────────────┘
```

- Left: priority dot (🔴 Hi, 🟡 Med, ⚪ Lo)
- Main: task text (parsed from TASKS.md, markdown bold stripped)
- Subtitle: due date and context (extracted from task text if present)
- **Swipe right → complete** (green slide reveal, checkmark icon)
  - Changes `- [ ]` to `- [x]` in TASKS.md
  - Moves task to Done section with completion date
  - Card slides out with animation
- **Tap → expand** for full text if truncated
- **Long press → action sheet:** Change Priority, Move Section, Delete

### 5.3 Add Task

Sticky input bar at top of content area:

```
┌──────────────────────────────────┐
│ + What needs to happen?      [▶] │
└──────────────────────────────────┘
```

- Tap to focus → keyboard opens
- Type task text
- [▶] button or Return to submit
- On submit → picker appears: Section (dropdown) + Priority (Hi/Med/Lo toggle)
- Defaults: section = first work section, priority = Med
- Writes `- [ ] **[Med]** {task text}` to appropriate section in TASKS.md

### 5.4 Reorder & Priority

- **Drag handle** (≡) on right edge of each card, visible when editing
- Drag to reorder within a section → rewrites task order in TASKS.md
- **Priority change:** long press → action sheet → select new priority
  - Updates `[Hi]`/`[Med]`/`[Lo]` tag in TASKS.md

### 5.5 Section Behavior

- Sections parsed from `##` headings in TASKS.md
- Collapsible (tap header to toggle)
- Collapsed state saved in localStorage
- Done section hidden by default (expandable at bottom)
- Task count badge next to each section header

### 5.6 TASKS.md Parser (JavaScript)

Must handle the exact same format as the Python parser:

```javascript
// Parse sections from ## headings
// Parse tasks: - [ ] **[Priority]** Task text — context
// Extract: checkbox state, priority, text, context after "—"
// Stop at ## Done
// Write back: preserve section order, heading format, completed items
```

---

## 6. Prospects Tab (Pipeline)

### 6.1 Layout

```
┌─────────────────────────────┐
│  AREC                    ✓  │
├─────────────────────────────┤
│ [Fund II ▼]   $156M / $1B  │  ← Offering picker + progress
├─────────────────────────────┤
│  🔍 Search prospects...     │  ← Search bar
│  Stage ▼  Urgency ▼  More ▼│  ← Compact filter chips
├─────────────────────────────┤
│                             │
│ ┌───────────────────────────┐│
│ │ Merseyside Pension Fund   ││  ← Prospect card
│ │ INSTITUTIONAL             ││
│ │ 6. Verbal · $50M · Final  ││
│ │ 🔴 High  · James Walton  ││
│ │ → Meeting March 2         ││
│ │ Last touch: Feb 25 🟢     ││
│ └───────────────────────────┘│
│                             │
│ ┌───────────────────────────┐│
│ │ NPS (Korea SWF)           ││
│ │ INSTITUTIONAL             ││
│ │ 5. Interested · $300M     ││
│ │ 🔴 High  · Zach Reisner  ││
│ │ → Meeting w/ John Kim     ││
│ │ Last touch: Feb 25 🟢     ││
│ └───────────────────────────┘│
│                             │
│ ┌───────────────────────────┐│
│ │ Berkshire Hathaway        ││
│ │ ...                       ││
│ └───────────────────────────┘│
│                             │
├─────────────────────────────┤
│  ☑ Tasks    │  📊 Pipeline  │
└─────────────────────────────┘
```

### 6.2 Prospect Card

Each prospect is a card showing key fields at a glance:

```
┌──────────────────────────────────┐
│ Merseyside Pension Fund          │  ← Org name (bold)
│ INSTITUTIONAL                    │  ← Type badge
│ 6. Verbal · $50M · Final        │  ← Stage · Target · Closing
│ 🔴 High  · James Walton         │  ← Urgency badge · Assigned
│ → Meeting March 2               │  ← Next Action (→ prefix)
│ Last touch: Feb 25 🟢           │  ← Date + staleness dot
└──────────────────────────────────┘
```

- **Tap card → edit sheet** (slide-up panel, not a new page)
- Default sort: Stage descending, then Urgency (High first), then Target descending
- Staleness dots: 🟢 < 7d, 🟡 8–14d, 🔴 15+d

### 6.3 Offering Picker

Dropdown at top of Pipeline tab:
- Lists all offerings from offerings.md
- Shows commitment progress for selected offering: `$156M / $1B (16%)`
- Compact progress bar below text
- Switching offering re-filters the card list

### 6.4 Search & Filter

**Search bar:** filters prospect cards by org name (client-side, instant)

**Filter chips:** compact row of dropdown pills
- Stage: `All Stages ▼` → dropdown of stages from config.md
- Urgency: `All ▼` → High / Med / Low
- "More ▼" → Type, Closing, Assigned To
- Active filters show as filled chips with × to clear
- "Clear all" link when any filter active

### 6.5 Edit Sheet

Tap a prospect card → slide-up panel covers bottom 75% of screen:

```
┌─────────────────────────────┐
│ ─── (drag handle)           │  ← Swipe down to dismiss
├─────────────────────────────┤
│ Merseyside Pension Fund     │
│ INSTITUTIONAL               │
├─────────────────────────────┤
│ Stage      [6. Verbal    ▼] │  ← Dropdown
│ Target     [$50,000,000   ] │  ← Input
│ Committed  [$0            ] │  ← Input
│ Closing    [Final        ▼] │  ← Dropdown
│ Urgency    [High ▼]        │  ← Dropdown
│ Assigned   [James Walton ▼] │  ← Dropdown
│ Contact    [Susannah F.  ▼] │  ← Dropdown
├─────────────────────────────┤
│ Next Action                 │
│ ┌───────────────────────────┐│
│ │ Meeting March 2           ││  ← Textarea
│ └───────────────────────────┘│
│ Notes                       │
│ ┌───────────────────────────┐│
│ │ Sent Credit and Index     ││  ← Textarea (expandable)
│ │ Comparisons on 2/25       ││
│ └───────────────────────────┘│
├─────────────────────────────┤
│         [ Save ]            │  ← Primary button
└─────────────────────────────┘
```

- All enum fields are native `<select>` elements (use iOS picker wheel)
- Text fields are `<input>` or `<textarea>`
- **Save** button writes changes to prospects.md via Dropbox API
- Dismiss by swiping down or tapping outside
- Card in list updates immediately after save

### 6.6 prospects.md Parser (JavaScript)

Must handle the two-level heading structure:

```javascript
// Parse ## OfferingName sections
// Within each: parse ### OrgName subsections
// Within each: parse - **Field:** Value lines
// For duplicate orgs (UTIMCO): heading includes contact disambiguator
// Write back: preserve structure, only modify changed prospect section
```

**Critical:** The JS parser must produce identical output format to `crm_reader.py`. Both parsers read/write the same files.

---

## 7. Offline Support

### 7.1 Service Worker

Register a service worker that caches:
- The PWA HTML file itself
- Any loaded file contents (via Cache API)

This allows the app to open even with no network.

### 7.2 Offline Write Queue

```javascript
// On edit when offline:
pendingWrites.push({
  path: "/Tech/ClaudeProductivity/crm/prospects.md",
  content: updatedFileContent,
  timestamp: Date.now()
});
localStorage.setItem('pendingWrites', JSON.stringify(pendingWrites));

// On network return:
for (const write of pendingWrites) {
  await dropboxUpload(write.path, write.content);
}
localStorage.removeItem('pendingWrites');
```

### 7.3 Sync Indicator

- ✓ (green) — all synced
- ↻ (blue, animated) — syncing in progress
- ⚠ (amber) — pending offline writes (tap to see count)
- ✗ (red) — sync error (tap for details)

---

## 8. PWA Manifest

Enables "Add to Home Screen" with app-like experience:

```json
{
  "name": "AREC",
  "short_name": "AREC",
  "start_url": "./arec-mobile.html",
  "display": "standalone",
  "background_color": "#1a1a2e",
  "theme_color": "#1a1a2e",
  "icons": [
    { "src": "icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

When added to home screen:
- No Safari address bar
- Status bar matches app theme
- Splash screen on launch
- App icon on home screen

---

## 9. File Structure

The PWA is a single deliverable — one HTML file plus a manifest and icons:

```
arec-mobile/
├── arec-mobile.html    ← The entire app (HTML + CSS + JS, self-contained)
├── manifest.json       ← PWA manifest
├── sw.js               ← Service worker for offline support
├── icon-192.png        ← Home screen icon
└── icon-512.png        ← Splash screen icon
```

**Hosting options (pick one):**
- Drop in Dropbox and open via Dropbox link (simplest)
- GitHub Pages (free, HTTPS, custom domain optional)
- Any static file host

---

## 10. Implementation Plan

This is a **single phase** that can be built independently from the CRM phases. It only depends on the markdown file format being stable (which it is after CRM Phase 1).

### Phase: Mobile PWA
**Goal:** Build the complete PWA with Tasks and Prospects tabs.  
**Depends on:** CRM Phase 1 (data files and format must exist)  
**Deliverable:** Working PWA bookmarkable to iPhone home screen  

**Agent instructions:**
```
Build a mobile PWA for AREC that reads/writes markdown files via Dropbox API.

CONTEXT:
- Single HTML file with embedded CSS and JS. No build step, no frameworks.
- Reads/writes files in Dropbox at /Tech/ClaudeProductivity/
- Two tabs: Tasks (TASKS.md) and Pipeline (crm/prospects.md + supporting files)
- Phone-first design: iPhone Safari, touch targets ≥ 44px, bottom tab bar
- Must parse and write the EXACT same markdown format as the Python parsers

DROPBOX API:
- Auth: long-lived access token stored in localStorage
- Read: POST https://content.dropboxapi.com/2/files/download
- Write: POST https://content.dropboxapi.com/2/files/upload (mode: overwrite)
- Metadata: POST https://api.dropboxapi.com/2/files/get_metadata (content_hash)
- First launch: show setup screen asking user to paste Dropbox access token

FILES TO READ/WRITE:
- /Tech/ClaudeProductivity/TASKS.md (read + write)
- /Tech/ClaudeProductivity/crm/prospects.md (read + write)
- /Tech/ClaudeProductivity/crm/organizations.md (read only — for org type)
- /Tech/ClaudeProductivity/crm/config.md (read only — stages, types, urgency, team)
- /Tech/ClaudeProductivity/crm/offerings.md (read only — offering names and targets)

TASKS TAB:
- Parse TASKS.md: ## section headings → task groups
  Task format: - [ ] **[Priority]** Task text — context
  Priorities: [Hi], [Med], [Lo]
  Sections: everything up to ## Done
- Display: section headers (collapsible) → task cards with priority dot
- Swipe right on task → complete (change - [ ] to - [x], move to Done with date)
- Add task: sticky input bar at top, section picker + priority toggle on submit
  Writes - [ ] **[Priority]** {text} to selected section
- Long press → action sheet: Change Priority, Move Section, Delete
- Drag to reorder within section
- Done section collapsed at bottom, expandable

PIPELINE TAB:
- Parse offerings.md for offering names and targets
- Parse config.md for stages, types, urgency levels, team members, closings
- Parse organizations.md for org type lookup
- Parse prospects.md: ## OfferingName → ### OrgName → - **Field:** Value
  Fields: Stage, Target, Committed, Primary Contact, Closing, Urgency,
  Assigned To, Notes, Next Action, Last Touch
- Display: offering picker at top with progress bar, then prospect card list
- Each card: org name, type badge, stage · target · closing, urgency badge ·
  assigned to, next action (→ prefix), last touch + staleness dot
- Search bar: filter by org name (instant, client-side)
- Filter chips: Stage, Urgency, plus "More" for Type/Closing/Assigned To
- Tap card → slide-up edit sheet with all editable fields
  Enum fields use <select> (native iOS picker)
  Save writes changes back to prospects.md via Dropbox API
- Default sort: Stage desc, Urgency (High first), Target desc
- Staleness: green < 7d, yellow 8-14d, red 15+d

SYNC:
- On open: load from localStorage (instant), fetch from Dropbox (background update)
- Use content_hash to detect changes
- On edit: update localStorage immediately, write to Dropbox in background
- Offline: queue writes in localStorage, flush on network return
- Sync indicator in header: ✓ synced / ↻ syncing / ⚠ pending / ✗ error

PWA:
- Include manifest.json for Add to Home Screen
- Include service worker (sw.js) for offline caching
- Standalone display mode (no Safari chrome)
- Theme color: #1a1a2e

STYLE:
- Background: #f8f9fa, header/tabs: #1a1a2e, accent: #3b82f6
- Urgency: High=#ef4444, Med=#f59e0b, Low=#9ca3af
- Font: -apple-system (San Francisco on iOS)
- Touch targets: minimum 44px
- No hover states. Tap and swipe only.
- Smooth transitions on card actions (complete, edit sheet slide)

CRITICAL PARSING RULES:
- Task parser must be identical in behavior to the Python memory_reader.py
- Prospect parser must be identical in behavior to crm_reader.py
- Both parsers read AND write — output must be valid markdown that the Python
  parsers can read without error
- Currency: stored as "$50,000,000" in files, display as "$50M" in UI
- Two-level prospect parsing: ## Offering → ### Org (some orgs have contact
  disambiguator in parens in heading)

OUTPUT:
- arec-mobile.html (the complete app)
- manifest.json
- sw.js
- Create placeholder icon PNGs (simple "A" on dark background)

DO NOT create any server-side code. This is a pure client-side app.
```

---

## 11. Dropbox App Setup Instructions

One-time setup (include in a README or in the app's first-launch screen):

```
1. Go to https://www.dropbox.com/developers/apps
2. Click "Create app"
3. Choose: Scoped access → Full Dropbox → Name it "AREC Mobile"
4. In the app settings, under Permissions tab, enable:
   - files.content.read
   - files.content.write
5. Under Settings tab, click "Generate access token"
   (For long-lived access: use refresh token flow instead)
6. Copy the token
7. Open the AREC PWA on your iPhone
8. Paste the token in the setup screen
9. Add to Home Screen via Safari share menu
```

---

## 12. Integration with CRM Phases

| CRM Phase | PWA Impact |
|-----------|-----------|
| Phase 1 (Data Layer) | **Must complete first.** PWA depends on stable file format. |
| Phase 2–4 (Desktop UI) | No impact. PWA and desktop read/write the same files independently. |
| Phase 5 (Auto-Capture) | Auto-captured interactions update Last Touch — PWA sees fresh dates on next sync. |
| Phase 6 (Analytics) | No mobile analytics view (use desktop for charts). |
| Phase 7 (Dashboard cleanup) | No impact. |

The PWA can be built in parallel with CRM Phases 2–7, as long as Phase 1 is done first.

---

## 13. Acceptance Criteria

1. ✅ PWA loads on iPhone Safari and can be added to home screen
2. ✅ Setup screen accepts Dropbox token, persists in localStorage
3. ✅ Tasks tab: displays all sections from TASKS.md with priority dots
4. ✅ Tasks: swipe to complete, add new task, change priority, reorder
5. ✅ Tasks: edits write back to TASKS.md via Dropbox API
6. ✅ Pipeline tab: displays prospects filtered by offering
7. ✅ Pipeline: search by org name, filter by stage/urgency
8. ✅ Pipeline: tap card → edit sheet with dropdowns for all fields
9. ✅ Pipeline: edits write back to prospects.md via Dropbox API
10. ✅ Offline: app opens from cache, queues writes, syncs on reconnect
11. ✅ Sync indicator shows current state (synced/syncing/pending/error)
12. ✅ Files written by PWA are valid markdown readable by Python parsers
13. ✅ Files written by Python parsers render correctly in PWA
