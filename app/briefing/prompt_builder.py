"""
prompt_builder.py — Assembles the Claude prompt for the morning briefing (CC-05)
"""

import os
import re
from datetime import date, timedelta

from sources.crm_reader import load_interactions, load_prospects

_APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../app
PRODUCTIVITY_ROOT = os.path.dirname(_APP_ROOT)  # project root (works in any location)

SYSTEM_PROMPT = """You are Oscar Vasquez's executive briefing assistant at AREC (Avila Real Estate Capital).
Generate a concise morning briefing. Be specific, not generic.

Rules:
- If there are investor meetings today, open with pre-meeting intelligence paragraphs
- Schedule section: list today's events with relevant context from memory
- Email section: flag action items only (skip FYI/newsletters)
- Tasks section: group by Active/Personal/Waiting, show priorities
- End with a single headline callout — the most important thing today
- Exclude anything related to "Settler"
- Max 1500 tokens"""


def _fmt_time(dt_str: str) -> str:
    """'2026-03-02T09:00:00' → '9:00 AM'"""
    if not dt_str:
        return ""
    try:
        parts = dt_str.split("T")
        if len(parts) < 2:
            return dt_str
        time_part = parts[1][:5]
        h, m = int(time_part[:2]), int(time_part[3:5])
        suffix = "AM" if h < 12 else "PM"
        h12 = h if 1 <= h <= 12 else (12 if h == 0 else h - 12)
        return f"{h12}:{m:02d} {suffix}"
    except Exception:
        return dt_str


def _matches_event(prospect: dict, event: dict) -> bool:
    """
    Return True if this event appears to be with this prospect's org.
    Checks attendee emails against person files, and org name in subject/title.
    """
    org_name = prospect.get("org", "").lower()
    if not org_name:
        return False

    # Check org name in event subject
    subject = event.get("subject", "").lower()
    if len(org_name) >= 6 and org_name in subject:
        return True

    # Check attendee emails/names
    try:
        from sources.crm_reader import find_person_by_email, get_contacts_for_org
        contacts = get_contacts_for_org(prospect.get("org", ""))
        contact_emails = {c.get("email", "").lower() for c in contacts if c.get("email")}

        for attendee in event.get("attendees", []):
            att_email = attendee.get("email", "").lower()
            att_name = attendee.get("name", "").lower()

            if att_email and att_email in contact_emails:
                return True

            # Also check person email lookup
            if att_email:
                person = find_person_by_email(att_email)
                if person:
                    p_org = (person.get("organization") or person.get("org", "")).lower()
                    if p_org == org_name:
                        return True

            # Fallback: org name in attendee display name
            if len(org_name) >= 6 and org_name in att_name:
                return True
    except Exception:
        pass

    return False


def _load_intel_file(org: str) -> str:
    """Load the intel file for an org from memory/people/ (capped at 800 chars)."""
    slug = re.sub(r"[^a-z0-9]+", "-", org.lower()).strip("-")
    path = os.path.join(PRODUCTIVITY_ROOT, "memory", "people", f"{slug}.md")
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return content[:800]


def _build_investor_intel(prospect: dict, event: dict) -> str:
    """Build the investor intelligence block for one matched prospect + event."""
    org = prospect.get("org", "")
    event_time = _fmt_time(event.get("start", ""))
    meeting_title = event.get("subject", "Meeting")

    stage = prospect.get("Stage", prospect.get("stage", ""))
    target = prospect.get("Target", prospect.get("target", ""))
    assigned = prospect.get("Assigned To", prospect.get("assigned_to", ""))
    offering = prospect.get("offering", "")

    # Last 3 interactions
    interactions = load_interactions(org=org, limit=3)
    interaction_lines = []
    for i in interactions:
        i_date = i.get("date", "")
        i_type = i.get("type", "")
        i_subject = i.get("Subject", i.get("subject", ""))
        interaction_lines.append(f"- {i_date}: {i_type} — {i_subject}")

    interactions_text = "\n".join(interaction_lines) if interaction_lines else "- No recent interactions logged"

    # Intel file excerpt
    intel_content = _load_intel_file(org)
    intel_section = ""
    if intel_content:
        intel_section = f"\nIntel file excerpt:\n{intel_content}"

    return f"""### {org} — {event_time} {meeting_title}
Stage: {stage} | Target: {target} | Assigned: {assigned} | Offering: {offering}
Last 3 interactions:
{interactions_text}{intel_section}

Synthesize a specific pre-meeting paragraph: where things stand, the key
open question, what the goal of today's meeting should be."""


def build_prompt(
    events: list[dict],
    emails: list[dict],
    tasks: dict,
    memory: str,
    token: str = None,
    tomorrow_events: list[dict] = None,
) -> tuple[str, str]:
    """
    Assemble the system and user prompts for Claude.
    Returns (system_prompt, user_prompt).
    """
    today = date.today().strftime("%A, %B %d, %Y")
    sections = []

    # --- Investor Intelligence ---
    high_urgency = [p for p in load_prospects() if p.get("urgency", p.get("Urgency", "")).lower() == "high"]
    intel_blocks = []
    for event in events:
        for prospect in high_urgency:
            if _matches_event(prospect, event):
                intel_blocks.append(_build_investor_intel(prospect, event))
                break  # one intel block per event

    if intel_blocks:
        sections.append("## INVESTOR INTELLIGENCE\n\n" + "\n\n".join(intel_blocks))

    # --- Schedule ---
    schedule_lines = [f"## SCHEDULE — {today}"]
    if events:
        for event in events:
            time_str = _fmt_time(event.get("start", ""))
            subject = event.get("subject", "(no subject)")
            location = event.get("location", "")
            loc_note = f" @ {location}" if location else ""
            attendees = event.get("attendees", [])
            att_count = len(attendees)
            att_note = f" ({att_count} attendees)" if att_count > 0 else ""
            schedule_lines.append(f"- {time_str}: {subject}{loc_note}{att_note}")
    else:
        schedule_lines.append("- No events today")

    # Show tomorrow's schedule when today has fewer than 2 events
    if tomorrow_events and len(events) < 2:
        tomorrow_date = (date.today() + timedelta(days=1)).strftime("%A, %B %d")
        schedule_lines.append("")
        schedule_lines.append(f"### Tomorrow — {tomorrow_date}")
        for event in tomorrow_events:
            time_str = _fmt_time(event.get("start", ""))
            subject = event.get("subject", "(no subject)")
            location = event.get("location", "")
            loc_note = f" @ {location}" if location else ""
            attendees = event.get("attendees", [])
            att_count = len(attendees)
            att_note = f" ({att_count} attendees)" if att_count > 0 else ""
            schedule_lines.append(f"- {time_str}: {subject}{loc_note}{att_note}")
        if not tomorrow_events:
            schedule_lines.append("- No events tomorrow")

    sections.append("\n".join(schedule_lines))

    # --- Email Action Items ---
    email_lines = ["## EMAIL ACTION ITEMS (last 18h)"]
    actionable = [
        e for e in emails
        if e.get("importance", "normal").lower() != "low"
        and not e.get("is_read", False)
    ]
    if actionable:
        for e in actionable[:10]:
            from_info = f"{e.get('from_name', '')} <{e.get('from_email', '')}>"
            subject = e.get("subject", "(no subject)")
            preview = e.get("preview", "")[:100]
            importance = e.get("importance", "normal")
            flag = "[HIGH] " if importance.lower() == "high" else ""
            email_lines.append(f"- {flag}From: {from_info}")
            email_lines.append(f"  Subject: {subject}")
            if preview:
                email_lines.append(f"  Preview: {preview}")
    else:
        email_lines.append("- No unread actionable emails in last 18h")
    sections.append("\n".join(email_lines))

    # --- Tasks ---
    task_lines = ["## OPEN TASKS"]
    active = tasks.get("active", [])
    personal = tasks.get("personal", [])

    if active:
        task_lines.append("\n### Active")
        for t in active:
            task_lines.append(f"- {t}")
    if personal:
        task_lines.append("\n### Personal")
        for t in personal:
            task_lines.append(f"- {t}")
    if not (active or personal):
        task_lines.append("- No open tasks")
    sections.append("\n".join(task_lines))

    # --- Inbox ---
    # (memory_reader.load_inbox is called by main.py; inbox not passed here
    #  but tasks dict may include it if needed)

    # --- Memory context ---
    memory_section = f"## CONTEXT\n{memory[:1500]}" if memory else ""
    if memory_section:
        sections.append(memory_section)

    user_prompt = "\n\n".join(sections)

    return SYSTEM_PROMPT, user_prompt
