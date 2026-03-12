"""
crm_graph_sync.py — Auto-capture engine (CC-04)

Scans last 24h of Microsoft Graph email + calendar data.
Matches participants to CRM orgs and logs interactions.
"""

import os
import yaml
from datetime import date, datetime

from sources.crm_db import (
    add_pending_interview,
    add_unmatched,
    append_interaction,
    append_org_email_history,
    append_person_email_history,
    discover_and_enrich_contact_emails,
    enrich_org_domain,
    enrich_person_email,
    find_person_by_email,
    load_organizations,
    load_prospects,
    purge_old_unmatched,
)
from sources.ms_graph import get_events_range, get_recent_emails

# Internal AREC domains to skip
INTERNAL_DOMAINS = {
    "avilacapllc.com",
    "avilacapital.com",
    "builderadvisorgroup.com",
}


def _get_user_email() -> str:
    """Get user email from config or env."""
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.yaml')
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = yaml.safe_load(f)
            if config and 'graph' in config:
                return config['graph'].get('user_email', '')
    return os.getenv('MS_USER_ID', 'oscar@avilacapllc.com')


def _is_internal(email: str) -> bool:
    if not email:
        return True
    email_lower = email.lower()
    # Check against internal domains
    domain = email_lower.split("@")[-1]
    if domain in INTERNAL_DOMAINS:
        return True
    # Check against configured user email
    user_email = _get_user_email().lower()
    if user_email and email_lower == user_email:
        return True
    return False


def _fuzzy_match_org(display_name: str, org_names: list[str]) -> str | None:
    """
    Substring fuzzy match: find a single org whose name appears in or contains
    the display name (≥6 character overlap). Returns org name or None.
    If multiple orgs match, return None (ambiguous).
    """
    display_lower = display_name.lower()
    matches = []

    for org_name in org_names:
        org_lower = org_name.lower()
        # Check if org name appears in display_name or vice versa
        overlap = min(len(org_lower), len(display_lower))
        if overlap < 6:
            continue
        if org_lower in display_lower or display_lower in org_lower:
            matches.append(org_name)

    if len(matches) == 1:
        return matches[0]
    return None


def _resolve_participant(email: str, display_name: str, all_org_names: list[str]) -> dict | None:
    """
    Try to resolve a participant (email + display name) to a CRM org.
    Returns {'org': name, 'contact': display_name} or None.
    """
    if _is_internal(email):
        return None

    # 1. Email exact match via person files
    person = find_person_by_email(email)
    if person:
        org = person.get("organization") or person.get("org", "")
        if org:
            return {"org": org, "contact": person.get("name", display_name)}

    # 2. Org name fuzzy match on display name
    org_match = _fuzzy_match_org(display_name, all_org_names)
    if org_match:
        return {"org": org_match, "contact": display_name}

    return None


def _get_offering_for_org(org: str) -> str:
    """Return the primary offering for a prospect org, or empty string."""
    prospects = load_prospects()
    for p in prospects:
        if p["org"].lower() == org.lower():
            return p.get("offering", "")
    return ""


def _is_high_urgency(org: str) -> bool:
    """Return True if this org has any High urgency prospect."""
    prospects = load_prospects()
    for p in prospects:
        if p["org"].lower() == org.lower():
            urgency = p.get("Urgency", p.get("urgency", "")).lower()
            if urgency == "high":
                return True
    return False


def run_auto_capture(token: str, user_id: int = None) -> dict:
    """
    Scan last 24h of email + calendar. Match participants to CRM orgs.
    Log matched interactions; queue unmatched for review.

    Args:
        token: MS Graph access token
        user_id: User ID for multi-user attribution (optional, for background polling)

    Returns: {'matched': N, 'unmatched': N, 'skipped_dedup': N, 'pending_interviews_added': N}
    """
    purge_old_unmatched(days=14)

    all_org_names = [o["name"] for o in load_organizations()]
    today = date.today().isoformat()

    stats = {
        "matched": 0, "unmatched": 0, "skipped_dedup": 0,
        "pending_interviews_added": 0,
        "domains_added": 0, "emails_enriched": 0, "history_entries": 0,
    }

    # --- Emails ---
    emails = get_recent_emails(token, hours=24)
    for email in emails:
        from_email = email.get("from_email", "")
        from_name = email.get("from_name", "")
        subject = email.get("subject", "")
        received_date = email.get("received", "")[:10] or today

        if _is_internal(from_email):
            continue

        match = _resolve_participant(from_email, from_name, all_org_names)

        if match:
            # Enrich person email if we have a match but no stored email
            matched_person = find_person_by_email(from_email)
            if matched_person and not matched_person.get("email") and from_email:
                enrich_person_email(matched_person["slug"], from_email)

            # --- Email enrichment (a)(b)(c) ---
            org_name = match["org"]
            from_domain = from_email.split("@")[-1].lower() if from_email else ""

            # (a) Add domain to org if missing
            if from_domain and enrich_org_domain(org_name, from_domain):
                stats["domains_added"] += 1

            # (b) Append email history to person profile and org
            if matched_person and matched_person.get("slug"):
                append_person_email_history(
                    matched_person["slug"], received_date, subject, "incoming"
                )
                stats["history_entries"] += 1
            append_org_email_history(
                org_name, received_date, subject, match["contact"], "incoming"
            )

            # (c) Discover and enrich contact emails from this org
            enrichment = discover_and_enrich_contact_emails(
                org_name, [(from_email, from_name)]
            )
            stats["emails_enriched"] += enrichment["emails_enriched"]

            offering = _get_offering_for_org(match["org"])
            entry = {
                "org": match["org"],
                "type": "Email",
                "offering": offering,
                "date": received_date,
                "contact": match["contact"],
                "subject": subject,
                "summary": f"Auto-captured: {from_name} → {subject}",
                "source": "auto-graph",
            }
            # Check dedup before appending
            from sources.crm_db import load_interactions
            existing = load_interactions(org=match["org"])
            is_dup = any(
                i.get("date") == received_date and i.get("type", "").lower() == "email"
                and i.get("subject", "") == subject
                for i in existing
            )
            if is_dup:
                stats["skipped_dedup"] += 1
            else:
                append_interaction(entry)
                stats["matched"] += 1
        else:
            if from_email:
                add_unmatched({
                    "source": "email",
                    "date": received_date,
                    "participant_email": from_email,
                    "participant_name": from_name,
                    "subject": subject,
                    "reason": "No email match; org name not found in display name",
                })
                stats["unmatched"] += 1

    # --- Calendar events ---
    from datetime import timezone
    now = datetime.now(timezone.utc)
    start = (now.replace(hour=0, minute=0, second=0, microsecond=0)).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_dt = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    events = get_events_range(token, start, end_dt)

    for event in events:
        subject = event.get("subject", "")
        event_date = event.get("start", "")[:10] or today
        attendees = event.get("attendees", [])

        for attendee in attendees:
            att_email = attendee.get("email", "")
            att_name = attendee.get("name", "")

            if _is_internal(att_email):
                continue

            match = _resolve_participant(att_email, att_name, all_org_names)

            if match:
                offering = _get_offering_for_org(match["org"])
                entry = {
                    "org": match["org"],
                    "type": "Meeting",
                    "offering": offering,
                    "date": event_date,
                    "contact": match["contact"],
                    "subject": subject,
                    "summary": f"Auto-captured: {att_name} meeting — {subject}",
                    "source": "auto-graph",
                }
                from sources.crm_db import load_interactions
                existing = load_interactions(org=match["org"])
                is_dup = any(
                    i.get("date") == event_date and i.get("type", "").lower() == "meeting"
                    and i.get("subject", "") == subject
                    for i in existing
                )
                if is_dup:
                    stats["skipped_dedup"] += 1
                else:
                    append_interaction(entry)
                    stats["matched"] += 1

                    # Add to pending interviews if High urgency
                    if _is_high_urgency(match["org"]):
                        add_pending_interview({
                            "org": match["org"],
                            "offering": offering,
                            "meeting_date": event_date,
                            "meeting_title": subject,
                            "detected_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                        })
                        stats["pending_interviews_added"] += 1
            else:
                if att_email:
                    add_unmatched({
                        "source": "calendar",
                        "date": event_date,
                        "participant_email": att_email,
                        "participant_name": att_name,
                        "subject": subject,
                        "reason": "No email match; org name not found in display name",
                    })
                    stats["unmatched"] += 1

    return stats
