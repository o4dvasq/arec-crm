# CC-05: Morning Briefing Pipeline

**Target:** `~/Dropbox/Tech/ClaudeProductivity/app/main.py` + `briefing/prompt_builder.py` + `briefing/generator.py` + `sources/memory_reader.py`
**Depends on:** CC-04 (Graph auth + ms_graph.py)
**Blocks:** Nothing

---

## Purpose

Automated daily intelligence report. Runs at 5 AM via launchd. Combines Microsoft 365 data (calendar, email) with the Dropbox knowledge base (tasks, memory, CRM), synthesized by Claude API. Output written to `briefing_latest.md` in the Dropbox productivity folder for Cowork to consume during `/productivity:update`.

## Module Map

```
main.py                        ← Orchestrator: auth → fetch → build → generate → write → capture
sources/memory_reader.py       ← Reads all markdown memory + task files
briefing/prompt_builder.py     ← Assembles the Claude prompt
briefing/generator.py          ← Calls Claude API
```

## Module 1: sources/memory_reader.py

Reads all Dropbox markdown files into structured data for prompt injection.

```python
PRODUCTIVITY_ROOT = os.path.expanduser("~/Dropbox/Tech/ClaudeProductivity")

def load_tasks() → dict:
    """Parse TASKS.md → {active: [...], personal: [...], waiting: [...]}"""

def load_memory_summary() → str:
    """Read CLAUDE.md, return as string (cap at 2000 chars)"""

def load_inbox() → list[str]:
    """Parse inbox.md → list of pending items (may be empty)"""
```

## Module 2: briefing/prompt_builder.py

Assembles the system prompt and user prompt for Claude.

### Data Sources Injected

1. **Calendar:** Today's events from `ms_graph.get_today_events()`
2. **Email:** Last 18 hours from `ms_graph.get_recent_emails(hours=18)`
3. **Tasks:** Active + Personal + Waiting On from `memory_reader.load_tasks()`
4. **Memory context:** From `memory_reader.load_memory_summary()`
5. **Investor intelligence** (conditional): see below

### Investor Intelligence Section

**Trigger:** Today's calendar includes a meeting with a High urgency prospect.

**Logic:**
```python
from sources.crm_reader import load_prospects, load_interactions

high_urgency = [p for p in load_prospects() if p['urgency'] == 'High']
today_events = ms_graph.get_today_events(token)

for event in today_events:
    for prospect in high_urgency:
        if matches_event(prospect, event):  # attendee email or org name in subject/title
            # Load: prospect record, last 3 interactions, intel file (cap 800 chars)
            intel = build_intel_context(prospect)
            # Inject as ## INVESTOR INTELLIGENCE section in prompt
```

**Match logic:** Check event attendee emails against contacts for this org. Fallback: check if org name appears in event subject/title (case-insensitive substring).

**Prompt injection format:**
```
## INVESTOR INTELLIGENCE

### Merseyside Pension Fund — 4:00 PM meeting
Stage: 6. Verbal | Target: $50M | Assigned: James Walton
Last 3 interactions:
- 2026-03-01: Email — Sent Credit and Index Comparisons
- 2026-02-25: Email — Follow-up on fund materials
- 2026-02-20: Meeting — Initial Fund II discussion

Intel file excerpt (if exists):
[first 800 chars of memory/people/merseyside-pension-fund.md]

Synthesize a specific pre-meeting paragraph: where things stand, the key
open question, what the goal of today's meeting should be.
```

### System Prompt

```
You are Oscar Vasquez's executive briefing assistant at AREC (Avila Real Estate Capital).
Generate a concise morning briefing. Be specific, not generic.

Rules:
- If there are investor meetings today, open with pre-meeting intelligence paragraphs
- Schedule section: list today's events with relevant context from memory
- Email section: flag action items only (skip FYI/newsletters)
- Tasks section: group by Active/Personal/Waiting, show priorities
- End with a single headline callout — the most important thing today
- Exclude anything related to "Settler"
- Max 1500 tokens
```

### Output Sections

1. **Investor Intelligence** (if applicable) — pre-meeting paragraphs
2. **Schedule** — today's events with context
3. **Email Action Items** — last 18 hours, actionable only
4. **Open Tasks** — from TASKS.md, grouped
5. **Headline** — single key callout

## Module 3: briefing/generator.py

```python
import anthropic

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1500

def generate_briefing(system_prompt: str, user_prompt: str) → str:
    client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY from env
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )
    return response.content[0].text
```

## Module 4: main.py (Orchestrator)

```python
def run_briefing():
    # 1. Authenticate
    token = get_access_token()

    # 2. Fetch data
    events = get_today_events(token)
    emails = get_recent_emails(token, hours=18)
    tasks = load_tasks()
    memory = load_memory_summary()

    # 3. Build prompt (includes investor intel if applicable)
    system_prompt, user_prompt = build_prompt(events, emails, tasks, memory, token)

    # 4. Generate briefing
    briefing_text = generate_briefing(system_prompt, user_prompt)

    # 5. Write briefing to Dropbox for Cowork consumption
    briefing_path = os.path.expanduser("~/Dropbox/Tech/ClaudeProductivity/briefing_latest.md")
    write_briefing(briefing_text, briefing_path)

    # 6. Run auto-capture (CC-04)
    run_auto_capture(token)

    # 7. Log
    log_briefing(briefing_text)

if __name__ == "__main__":
    run_briefing()
```

## Logging

Write to `~/Library/Logs/arec-morning-briefing.log`. Include timestamp, token status, data counts (events, emails, tasks), generation time, delivery status.

## Delivery

**No Slack.** The briefing is written to:
- `~/Dropbox/Tech/ClaudeProductivity/briefing_latest.md` — consumed by Cowork `/productivity:update`
- `~/Library/Logs/arec-morning-briefing.log` — full log with metadata

The `write_briefing()` function overwrites `briefing_latest.md` each run. Include a YAML frontmatter block:

```markdown
---
generated: 2026-03-02T05:00:12
events_count: 6
emails_scanned: 42
investor_meetings: 1
---

[briefing content]
```

## Scheduling (launchd)

### Morning Briefing — `com.arec.morningbriefing.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.arec.morningbriefing</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/oscar/arec-morning-briefing/main.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>5</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/oscar/Library/Logs/arec-morning-briefing.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/oscar/Library/Logs/arec-morning-briefing-error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    <key>WorkingDirectory</key>
    <string>/Users/oscar/arec-morning-briefing</string>
</dict>
</plist>
```

### Dashboard — `com.arec.dashboard.plist`

Same structure but:
- `KeepAlive: true` (always running)
- Program: `python3 delivery/dashboard.py`
- Log: `~/Library/Logs/arec-dashboard.log`

### Installation

```bash
cp com.arec.*.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.arec.morningbriefing.plist
launchctl load ~/Library/LaunchAgents/com.arec.dashboard.plist
```

## Acceptance Criteria

- `python main.py` runs end-to-end: fetches Graph data, builds prompt, calls Claude, writes briefing
- `briefing_latest.md` is written to Dropbox with YAML frontmatter
- Briefing includes investor intel paragraph when today has a High urgency meeting
- Briefing excludes "Settler"-related content
- Output is < 1500 tokens
- Logs written to `~/Library/Logs/arec-morning-briefing.log`
- Both launchd plists are valid XML and load without error
