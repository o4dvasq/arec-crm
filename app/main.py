"""
main.py — Morning briefing orchestrator (CC-05)

Run: python main.py
Scheduled via launchd at 5 AM daily.

Flow:
1. Authenticate with Microsoft Graph
2. Fetch today's calendar events + last 18h of email
2a. Write dashboard_calendar.json so the web dashboard is current at startup
3. Load tasks, memory context, inbox
4. Build Claude prompt (includes investor intel if applicable)
5. Generate briefing via Claude API
6. Write briefing_latest.md to Dropbox
7. Run auto-capture (email + calendar → CRM)
8. Log to ~/Library/Logs/arec-morning-briefing.log
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

# Allow running from the app/ directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# Load .env from the app directory
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from auth.graph_auth import get_access_token
from briefing.generator import generate_briefing
from briefing.prompt_builder import build_prompt
from sources.crm_graph_sync import run_auto_capture
from sources.memory_reader import load_inbox, load_memory_summary, load_tasks
from sources.ms_graph import get_recent_emails, get_today_events, get_tomorrow_events

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_DIR = os.path.expanduser("~/Library/Logs")
LOG_PATH = os.path.join(LOG_DIR, "arec-morning-briefing.log")

os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

BRIEFING_PATH = os.path.expanduser(
    "~/Dropbox/Tech/ClaudeProductivity/briefing_latest.md"
)

# dashboard_calendar.json lives at the project root (one level above app/)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALENDAR_JSON_PATH = os.path.join(_PROJECT_ROOT, "dashboard_calendar.json")


# ---------------------------------------------------------------------------
# Write output
# ---------------------------------------------------------------------------

def write_briefing(briefing_text: str, path: str, meta: dict) -> None:
    """Write briefing with YAML frontmatter to the given path."""
    generated = meta.get("generated", datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    events_count = meta.get("events_count", 0)
    emails_scanned = meta.get("emails_scanned", 0)
    investor_meetings = meta.get("investor_meetings", 0)

    frontmatter = f"""---
generated: {generated}
events_count: {events_count}
emails_scanned: {emails_scanned}
investor_meetings: {investor_meetings}
---

"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(frontmatter + briefing_text)

    log.info(f"Briefing written to {path}")


# ---------------------------------------------------------------------------
# Write dashboard calendar JSON
# ---------------------------------------------------------------------------

def write_dashboard_calendar(events: list[dict]) -> None:
    """Format Graph events and write dashboard_calendar.json for the web app.

    Uses the same format as /api/calendar/refresh so the dashboard reads it
    correctly whether it was written by the morning script or the in-app button.
    """
    try:
        from zoneinfo import ZoneInfo
        pacific = ZoneInfo("America/Los_Angeles")
    except Exception:
        pacific = None

    def _parse_dt(s: str, tz_fallback: str):
        if not s:
            return None
        s = s.rstrip("Z")
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return None
        if dt.tzinfo is None:
            try:
                from zoneinfo import ZoneInfo
                dt = dt.replace(tzinfo=ZoneInfo(tz_fallback))
            except Exception:
                dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def _fmt_time(dt) -> str:
        if not dt:
            return ""
        h = dt.hour % 12 or 12
        ampm = "AM" if dt.hour < 12 else "PM"
        return f"{h}:{dt.minute:02d} {ampm}"

    formatted = []
    for evt in events:
        if evt.get("is_all_day"):
            continue

        start_dt = _parse_dt(evt.get("start", ""), evt.get("timezone", "UTC"))
        end_dt   = _parse_dt(evt.get("end", ""),   evt.get("timezone", "UTC"))

        if start_dt and pacific:
            start_dt = start_dt.astimezone(pacific)
        if end_dt and pacific:
            end_dt = end_dt.astimezone(pacific)

        time_str = (
            f"{_fmt_time(start_dt)} \u2013 {_fmt_time(end_dt)}"
            if start_dt and end_dt else ""
        )
        attendees = ", ".join(
            a["name"] or a["email"]
            for a in evt.get("attendees", [])
            if a.get("name") or a.get("email")
        )
        formatted.append({
            "time":      time_str,
            "title":     evt.get("subject", ""),
            "attendees": attendees,
            "location":  evt.get("location", ""),
        })

    try:
        with open(CALENDAR_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(formatted, f, ensure_ascii=False)
        log.info(f"dashboard_calendar.json written ({len(formatted)} events)")
    except IOError as e:
        log.warning(f"Could not write dashboard_calendar.json: {e}")


# ---------------------------------------------------------------------------
# Investor meeting count (for frontmatter metadata)
# ---------------------------------------------------------------------------

def _count_investor_meetings(events: list[dict]) -> int:
    """Count today's events that match High urgency prospects."""
    from briefing.prompt_builder import _matches_event
    from sources.crm_reader import load_prospects

    high_urgency = [
        p for p in load_prospects()
        if p.get("urgency", p.get("Urgency", "")).lower() == "high"
    ]
    count = 0
    for event in events:
        for prospect in high_urgency:
            if _matches_event(prospect, event):
                count += 1
                break
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_briefing() -> None:
    start_time = time.time()
    log.info("=== Morning briefing starting ===")

    # 1. Authenticate
    log.info("Authenticating with Microsoft Graph...")
    try:
        token = get_access_token()
        log.info("Token acquired successfully")
    except Exception as e:
        log.error(f"Authentication failed: {e}")
        sys.exit(1)

    # 2. Fetch data
    log.info("Fetching calendar events...")
    try:
        events = get_today_events(token)
        log.info(f"Fetched {len(events)} events")
        write_dashboard_calendar(events)  # seed dashboard before generating briefing
    except Exception as e:
        log.warning(f"Calendar fetch failed: {e}")
        events = []

    tomorrow_events = []
    if len(events) < 2:
        log.info("Fewer than 2 events today, fetching tomorrow's schedule...")
        try:
            tomorrow_events = get_tomorrow_events(token)
            log.info(f"Fetched {len(tomorrow_events)} tomorrow events")
        except Exception as e:
            log.warning(f"Tomorrow calendar fetch failed: {e}")
            tomorrow_events = []

    log.info("Fetching recent emails...")
    try:
        emails = get_recent_emails(token, hours=18)
        log.info(f"Fetched {len(emails)} emails")
    except Exception as e:
        log.warning(f"Email fetch failed: {e}")
        emails = []

    # 3. Load local data
    tasks = load_tasks()
    memory = load_memory_summary()
    inbox = load_inbox()
    log.info(
        f"Loaded tasks: {sum(len(v) for v in tasks.values())} items, "
        f"inbox: {len(inbox)} items"
    )

    # 4. Build prompt
    log.info("Building Claude prompt...")
    system_prompt, user_prompt = build_prompt(events, emails, tasks, memory, token, tomorrow_events=tomorrow_events)

    # 5. Generate briefing
    log.info("Calling Claude API...")
    gen_start = time.time()
    try:
        briefing_text = generate_briefing(system_prompt, user_prompt)
        gen_elapsed = time.time() - gen_start
        log.info(f"Briefing generated in {gen_elapsed:.1f}s")
    except Exception as e:
        log.error(f"Claude API call failed: {e}")
        sys.exit(1)

    # 6. Write briefing
    investor_count = _count_investor_meetings(events)
    meta = {
        "generated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "events_count": len(events),
        "emails_scanned": len(emails),
        "investor_meetings": investor_count,
    }
    write_briefing(briefing_text, BRIEFING_PATH, meta)

    # 7. Run auto-capture
    log.info("Running auto-capture...")
    try:
        capture_stats = run_auto_capture(token)
        log.info(f"Auto-capture: {capture_stats}")
    except Exception as e:
        log.warning(f"Auto-capture failed (non-fatal): {e}")

    elapsed = time.time() - start_time
    log.info(f"=== Morning briefing complete in {elapsed:.1f}s ===")


if __name__ == "__main__":
    run_briefing()
