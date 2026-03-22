"""
deep_scan_team.py — One-time deep scan for Truman, Zach, Anthony, and Robert.

Covers per mailbox:
  - Email received: 90-day lookback
  - Email sent:     90-day lookback
  - Calendar:       90 days back + 30 days forward (past + upcoming meetings)

All results go to crm/email_staging_queue.json for Oscar to review via /crm-update.
Oscar and Tony are excluded — their history is already in the CRM.

Idempotent: safe to re-run. Duplicate graph_message_ids are skipped.

Usage:
    cd ~/Dropbox/projects/arec-crm
    PYTHONPATH=app python3 scripts/deep_scan_team.py
"""

import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

# Ensure app/ is on the path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(SCRIPT_DIR, "..", "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from auth.graph_auth import get_app_token
from sources.crm_reader import append_staged_items, load_email_log, get_staging_dedup_ids
from sources.email_matching import _is_internal

# Import shared matching/staging helpers from graph_poller
from graph_poller import (
    GRAPH_BASE,
    _headers,
    _get_all_pages,
    _infer_direction,
    _extract_recipients,
    match_email_to_org,
    build_staged_item,
    build_dedup_set,
    send_summary_email,
)

DEEP_SCAN_MAILBOXES = [
    "truman@avilacapllc.com",
    "zachary.reisner@avilacapllc.com",
    "anthony@avilacapllc.com",
    "robert@avilacapllc.com",
]

LOOKBACK_DAYS_EMAIL = 90
LOOKBACK_DAYS_CALENDAR = 90
FORWARD_DAYS_CALENDAR = 30


# ---------------------------------------------------------------------------
# Calendar helpers
# ---------------------------------------------------------------------------

def _get_external_attendees(event: dict) -> list:
    """Return list of external attendee email addresses from a calendar event."""
    external = []
    for attendee in event.get("attendees", []):
        email = attendee.get("emailAddress", {}).get("address", "")
        if email and not _is_internal(email):
            external.append(email.lower())
    return external


def match_calendar_event_to_org(event: dict) -> dict | None:
    """Try to match a calendar event to a CRM org via attendee domains/emails.
    Applies ally pass-through: if the first matching attendee is a fundraising ally,
    continue scanning remaining attendees for a real prospect org."""
    from sources.crm_reader import (
        get_org_by_domain, find_person_by_email, is_ally_org, is_ally_email,
        get_individual_ally_name,
    )

    def _attendee_name(email: str) -> str:
        for attendee in event.get("attendees", []):
            if attendee.get("emailAddress", {}).get("address", "").lower() == email:
                return attendee.get("emailAddress", {}).get("name", "")
        return ""

    def _is_ally_participant(email: str, org: str | None) -> bool:
        return is_ally_email(email) or (bool(org) and is_ally_org(org))

    externals = _get_external_attendees(event)
    via_ally = None

    for email in externals:
        # Individual ally email check first (handles Ira Lubert case)
        if is_ally_email(email):
            if via_ally is None:
                via_ally = get_individual_ally_name(email) or email
            continue

        domain = email.split("@")[-1] if "@" in email else ""
        org = get_org_by_domain(domain) if domain else None
        if org:
            if is_ally_org(org):
                if via_ally is None:
                    via_ally = org
                continue
            result = {"org": org, "contact": _attendee_name(email),
                      "match_tier": "domain", "external_email": email}
            if via_ally:
                result["via_ally"] = via_ally
            return result

        person = find_person_by_email(email)
        if person:
            org = person.get("organization") or person.get("org", "")
            if org:
                if is_ally_org(org):
                    if via_ally is None:
                        via_ally = org
                    continue
                result = {"org": org, "contact": person.get("name", ""),
                          "match_tier": "person_email", "external_email": email}
                if via_ally:
                    result["via_ally"] = via_ally
                return result

    return None


def build_calendar_staged_item(event: dict, match: dict, mailbox: str, now_iso: str) -> dict:
    """Build a staged item from a calendar event (direction='meeting')."""
    start = event.get("start", {}).get("dateTime", "")
    subject = event.get("subject", "")
    org = match["org"]
    return {
        "graph_message_id": event["id"],
        "scanned_from_mailbox": mailbox,
        "matched_org": org,
        "matched_contact": match.get("contact"),
        "match_tier": match["match_tier"],
        "via_ally": match.get("via_ally"),
        "sender_email": match.get("external_email", ""),
        "sender_name": match.get("contact", ""),
        "recipient_emails": _get_external_attendees(event),
        "subject": subject,
        "email_date": start,
        "direction": "meeting",
        "suggested_action": f"Review calendar meeting with {org}: {subject}",
        "status": "pending",
        "created_at": now_iso,
        "reviewed_at": None,
    }


# ---------------------------------------------------------------------------
# Per-mailbox deep scan
# ---------------------------------------------------------------------------

def deep_scan_mailbox(token: str, mailbox: str, dedup_ids: set,
                       email_cutoff_iso: str, cal_start_iso: str,
                       cal_end_iso: str) -> dict:
    """
    Scan a single mailbox: received email, sent email, and calendar events.
    Returns stats dict.
    """
    stats = {"scanned": 0, "matched": 0, "unmatched": 0, "errors": [], "staged_items": []}
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # --- Received email ---
    try:
        received = _get_all_pages(token,
            f"{GRAPH_BASE}/users/{mailbox}/messages",
            params={
                "$filter": f"receivedDateTime ge {email_cutoff_iso}",
                "$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,bodyPreview",
                "$orderby": "receivedDateTime desc",
                "$top": "50",
            }
        )
        print(f"  [deep_scan] {mailbox}: {len(received)} received messages fetched")
        for msg in received:
            stats["scanned"] += 1
            msg_id = msg.get("id", "")
            if msg_id in dedup_ids:
                continue
            match = match_email_to_org(msg)
            if match:
                item = build_staged_item(msg, match, mailbox, now_iso)
                stats["staged_items"].append(item)
                dedup_ids.add(msg_id)
                stats["matched"] += 1
            else:
                stats["unmatched"] += 1
    except Exception as e:
        stats["errors"].append(f"received scan failed: {e}")
        print(f"  [deep_scan] {mailbox}: received scan ERROR — {e}")

    # --- Sent email ---
    try:
        sent = _get_all_pages(token,
            f"{GRAPH_BASE}/users/{mailbox}/mailFolders/sentItems/messages",
            params={
                "$filter": f"sentDateTime ge {email_cutoff_iso}",
                "$select": "id,subject,from,toRecipients,ccRecipients,sentDateTime,bodyPreview",
                "$orderby": "sentDateTime desc",
                "$top": "50",
            }
        )
        print(f"  [deep_scan] {mailbox}: {len(sent)} sent messages fetched")
        for msg in sent:
            stats["scanned"] += 1
            msg_id = msg.get("id", "")
            if msg_id in dedup_ids:
                continue
            match = match_email_to_org(msg)
            if match:
                item = build_staged_item(msg, match, mailbox, now_iso)
                stats["staged_items"].append(item)
                dedup_ids.add(msg_id)
                stats["matched"] += 1
            else:
                stats["unmatched"] += 1
    except Exception as e:
        stats["errors"].append(f"sent scan failed: {e}")
        print(f"  [deep_scan] {mailbox}: sent scan ERROR — {e}")

    # --- Calendar events ---
    try:
        events = _get_all_pages(token,
            f"{GRAPH_BASE}/users/{mailbox}/calendarView",
            params={
                "startDateTime": cal_start_iso,
                "endDateTime": cal_end_iso,
                "$select": "id,subject,start,end,attendees",
                "$top": "50",
            }
        )
        print(f"  [deep_scan] {mailbox}: {len(events)} calendar events fetched")
        for event in events:
            stats["scanned"] += 1
            event_id = event.get("id", "")
            if event_id in dedup_ids:
                continue
            match = match_calendar_event_to_org(event)
            if match:
                item = build_calendar_staged_item(event, match, mailbox, now_iso)
                stats["staged_items"].append(item)
                dedup_ids.add(event_id)
                stats["matched"] += 1
            else:
                stats["unmatched"] += 1
    except Exception as e:
        stats["errors"].append(f"calendar scan failed: {e}")
        print(f"  [deep_scan] {mailbox}: calendar scan ERROR — {e}")

    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    now = datetime.now(timezone.utc)
    email_cutoff = now - timedelta(days=LOOKBACK_DAYS_EMAIL)
    cal_start = now - timedelta(days=LOOKBACK_DAYS_CALENDAR)
    cal_end = now + timedelta(days=FORWARD_DAYS_CALENDAR)

    email_cutoff_iso = email_cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    cal_start_iso = cal_start.strftime("%Y-%m-%dT%H:%M:%SZ")
    cal_end_iso = cal_end.strftime("%Y-%m-%dT%H:%M:%SZ")
    run_date = now.strftime("%Y-%m-%d")
    run_time = now.strftime("%H:%M")

    print(f"[deep_scan] Starting at {now.isoformat()}")
    print(f"[deep_scan] Email lookback: {email_cutoff_iso}")
    print(f"[deep_scan] Calendar range: {cal_start_iso} → {cal_end_iso}")
    print(f"[deep_scan] Mailboxes: {DEEP_SCAN_MAILBOXES}")

    token = get_app_token()
    print("[deep_scan] App token acquired")

    dedup_ids = build_dedup_set()
    print(f"[deep_scan] Dedup set: {len(dedup_ids)} known IDs")

    all_staged = []
    mailbox_stats = {}
    errors = {}

    for mailbox in DEEP_SCAN_MAILBOXES:
        print(f"\n[deep_scan] Scanning {mailbox}...")
        try:
            stats = deep_scan_mailbox(
                token, mailbox, dedup_ids,
                email_cutoff_iso, cal_start_iso, cal_end_iso
            )
            mailbox_stats[mailbox] = stats
            all_staged.extend(stats["staged_items"])
            if stats["errors"]:
                errors[mailbox] = stats["errors"]
            print(f"[deep_scan] {mailbox}: {stats['scanned']} scanned, "
                  f"{stats['matched']} matched, {len(stats['errors'])} errors")
        except Exception as e:
            errors[mailbox] = [str(e)]
            mailbox_stats[mailbox] = {"scanned": 0, "matched": 0, "unmatched": 0,
                                       "errors": [str(e)], "staged_items": []}
            print(f"[deep_scan] {mailbox}: FAILED — {e}")

    # Write to staging queue
    print(f"\n[deep_scan] Writing {len(all_staged)} items to staging queue...")
    added = append_staged_items(all_staged) if all_staged else 0
    print(f"[deep_scan] Staged {added} new items (of {len(all_staged)} matched, "
          f"remainder were duplicates)")

    # Send summary email
    try:
        send_summary_email(token, f"{run_date} (deep scan)", run_time,
                           mailbox_stats, all_staged, errors)
    except Exception as e:
        print(f"[deep_scan] Failed to send summary email: {e}")

    total_scanned = sum(s.get("scanned", 0) for s in mailbox_stats.values())
    total_matched = sum(s.get("matched", 0) for s in mailbox_stats.values())
    print(f"\n[deep_scan] Complete — {total_scanned} scanned, {total_matched} matched, "
          f"{added} staged, {len(errors)} mailbox error(s)")


if __name__ == "__main__":
    main()
