# Capture Task — iPhone Shortcut Setup

## What it does
Speak a task → it appends to ClaudeProductivity/inbox.md in iCloud Drive.
Next time you run /productivity:update on desktop, Claude reads the inbox,
infers the area, and moves tasks into your main list + Notion.

## Build it in Shortcuts (iPhone)

1. Open **Shortcuts** app → tap **+** (new shortcut)

2. Add action: **Dictate Text**
   - Language: English (US)
   - (leave all other defaults)

3. Add action: **Text**
   - Content:
     ```
     - [ ] [Dictated Text] ([Shortcut Input: Current Date])
     ```
   - Tap "Dictated Text" → select the variable from step 2
   - Tap the date part → Format: Short Date (2/21/2026)

4. Add action: **Append to File**
   - File path: ClaudeProductivity/inbox.md
   - Service: iCloud Drive
   - ✅ Create file if it doesn't exist: ON
   - ✅ Add new line: ON

5. Add action: **Show Notification**
   - Title: Task captured ✓
   - Body: [Dictated Text]

## Name & launch options

- Name the shortcut: **Capture Task**
- Tap the share icon → **Add to Home Screen** (gives you a one-tap icon)
- Or set a Siri phrase: say "Hey Siri, Capture Task" — it runs hands-free

## Tips

- Speak naturally: "Remind Tony to send the data room link to Kevin"
- Or short: "Call Art about Boca"
- Area will be inferred by Claude on desktop — no need to say it
- Works offline — syncs to iCloud when you next have signal
