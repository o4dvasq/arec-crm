#!/usr/bin/env python3
"""
scripts/backfill_emails.py — One-time 90-day email backfill.

Scans Oscar's and Tony's mailboxes (sent + received) for the past 90 days,
matches emails to CRM orgs, and writes to crm/email_log.json.
Wipes all existing email_log.json entries before backfilling.
Updates Last Touch on affected prospects after completion.

Usage:
    python3 scripts/backfill_emails.py

Requires AZURE_CLIENT_ID and AZURE_TENANT_ID in app/.env (or environment).
"""

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

# Add app/ to path for imports
APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app')
sys.path.insert(0, APP_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(APP_DIR, '.env'))

import requests
from auth.graph_auth import get_access_token
from sources.crm_reader import (
    load_email_log, save_email_log, get_org_domains,
    add_emails_to_log, load_prospects, write_prospect,
    find_person_by_email,
)
from sources.email_matching import _is_internal


GRAPH_BASE = "https://graph.microsoft.com/v1.0"
DAYS_BACK = 90

MAILBOXES = [
    {"upn": "ovasquez@avilacapllc.com", "name": "Oscar"},
    {"upn": "tavila@avilacapllc.com", "name": "Tony"},
]

GRAPH_SELECT = (
    "id,conversationId,subject,bodyPreview,receivedDateTime,"
    "from,toRecipients,ccRecipients,isDraft"
)

SKIP_SUBJECT_PREFIXES = (
    "accepted:", "declined:", "automatic reply:", "out of office:",
    "delivery failure", "undeliverable:", "read:", "fw: calendar",
)


# ---------------------------------------------------------------------------
# Graph API helpers
# ---------------------------------------------------------------------------

def graph_get(token: str, url: str, params: dict = None) -> dict:
    """GET with exponential backoff on 429."""
    headers = {"Authorization": f"Bearer {token}"}
    delays = [0, 1, 2, 4, 8, 16]
    for attempt, delay in enumerate(delays):
        if delay:
            print(f"  Rate limited — retrying in {delay}s...")
            time.sleep(delay)
        resp = requests.get(url, headers=headers, params=params or {})
        if resp.status_code == 429:
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"Graph API failed after retries: {url}")


def get_all_messages(token: str, upn: str, folder: str, since_iso: str) -> list[dict]:
    """Fetch all messages from a folder since the given date, following pagination."""
    if folder == "sentitems":
        url = f"{GRAPH_BASE}/users/{quote(upn)}/mailFolders/sentitems/messages"
    else:
        url = f"{GRAPH_BASE}/users/{quote(upn)}/messages"

    params = {
        "$filter": f"receivedDateTime ge {since_iso}",
        "$select": GRAPH_SELECT,
        "$orderby": "receivedDateTime desc",
        "$top": "1000",
    }

    all_messages = []
    page_count = 0
    current_url = url
    current_params = params

    while current_url:
        data = graph_get(token, current_url, current_params)
        all_messages.extend(data.get("value", []))
        current_url = data.get("@odata.nextLink")
        current_params = None  # nextLink already includes params
        page_count += 1
        if page_count % 5 == 0:
            print(f"    ...{len(all_messages)} fetched so far")

    return all_messages


# ---------------------------------------------------------------------------
# Email matching
# ---------------------------------------------------------------------------

def _extract_domain(email_addr: str) -> str:
    if not email_addr or "@" not in email_addr:
        return ""
    return email_addr.split("@")[-1].lower()


def _is_internal_only(from_addr: str, to_addrs: list[str], cc_addrs: list[str]) -> bool:
    """True if all participants are internal AREC domains."""
    all_addrs = [from_addr] + to_addrs + cc_addrs
    return all(_is_internal(a) for a in all_addrs if a)


def _should_skip_subject(subject: str) -> bool:
    s = (subject or "").lower().strip()
    return any(s.startswith(pfx) for pfx in SKIP_SUBJECT_PREFIXES)


def _get_addr(addr_obj: dict) -> str:
    return (addr_obj.get("emailAddress") or {}).get("address", "").lower()


def _get_name(addr_obj: dict) -> str:
    return (addr_obj.get("emailAddress") or {}).get("name", "")


def match_to_org(msg: dict, upn: str, domain_to_org: dict) -> dict | None:
    """
    Try to match an email message to a CRM org using two-tier logic.
    Returns a log entry dict or None if no match / should be skipped.
    """
    from_obj = msg.get("from") or {}
    from_addr = _get_addr(from_obj)
    from_name = _get_name(from_obj)

    to_addrs = [_get_addr(r) for r in (msg.get("toRecipients") or []) if r]
    cc_addrs = [_get_addr(r) for r in (msg.get("ccRecipients") or []) if r]

    subject = msg.get("subject") or ""

    if _should_skip_subject(subject):
        return None
    if msg.get("isDraft"):
        return None

    # Skip internal-only emails
    if _is_internal_only(from_addr, to_addrs, cc_addrs):
        return None

    # Determine direction by comparing from address to scanned mailbox UPN
    direction = "sent" if from_addr == upn.lower() else "received"

    # For received: match on sender. For sent: match on recipients.
    if direction == "received":
        candidate_emails = [from_addr]
    else:
        candidate_emails = [a for a in to_addrs + cc_addrs if not _is_internal(a)]

    org_match = None
    match_type = None
    confidence = 0.0

    # Tier 1: Domain match
    for addr in candidate_emails:
        domain = _extract_domain(addr)
        if domain and domain in domain_to_org:
            org_match = domain_to_org[domain]
            match_type = "domain"
            confidence = 0.95
            break

    # Tier 2: Person email match
    if not org_match:
        for addr in candidate_emails:
            person = find_person_by_email(addr)
            if person:
                org = person.get("organization") or person.get("org", "")
                if org:
                    org_match = org
                    match_type = "person"
                    confidence = 0.90
                    break

    if not org_match:
        return None

    received_dt = msg.get("receivedDateTime", "")
    date_str = received_dt[:10] if received_dt else ""

    return {
        "messageId": msg.get("id", ""),
        "conversationId": msg.get("conversationId"),
        "direction": direction,
        "mailboxSource": upn,
        "date": date_str,
        "timestamp": received_dt,
        "subject": subject,
        "from": from_addr,
        "fromName": from_name,
        "to": to_addrs,
        "cc": cc_addrs,
        "orgMatch": org_match,
        "matchType": match_type,
        "confidence": confidence,
        "summary": (msg.get("bodyPreview") or "")[:200],
        "outlookUrl": f"https://outlook.office365.com/mail/id/{quote(msg.get('id', ''), safe='')}",
    }


# ---------------------------------------------------------------------------
# Last Touch update
# ---------------------------------------------------------------------------

def update_last_touch(affected_orgs: dict) -> int:
    """
    Update Last Touch on prospects for orgs with new emails.
    Uses write_prospect directly to set the actual backfill date
    (not today's date, as update_prospect_field always sets to today).

    affected_orgs: {org_name: max_email_date_str}
    Returns count of prospects updated.
    """
    all_prospects = load_prospects()
    updated = 0

    for org_name, max_date in affected_orgs.items():
        matching = [p for p in all_prospects if p["org"].lower() == org_name.lower()]
        for prospect in matching:
            existing_lt = prospect.get("Last Touch", "")
            if not existing_lt or max_date > existing_lt:
                prospect["Last Touch"] = max_date
                write_prospect(prospect["org"], prospect["offering"], prospect)
                print(f"  {prospect['org']} ({prospect['offering']}): {max_date}")
                updated += 1

    return updated


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"=== Email Backfill — {DAYS_BACK} days back from {datetime.now().date()} ===\n")

    # Authenticate
    print("Authenticating with Microsoft Graph...")
    token = get_access_token()
    print("Authenticated.\n")

    since_dt = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
    since_iso = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"Scan window: {since_iso} to now\n")

    # Build reverse domain map: domain -> org_name
    org_domain_map = get_org_domains(prospect_only=True)
    domain_to_org = {v.lstrip("@"): k for k, v in org_domain_map.items()}
    print(f"Loaded {len(org_domain_map)} org domains for matching.\n")

    # Wipe existing email_log entries
    print("Clearing existing email_log.json entries...")
    log = load_email_log()
    original_count = len(log.get("emails", []))
    log["emails"] = []
    save_email_log(log)
    print(f"  Cleared {original_count} entries.\n")

    # Scan mailboxes
    all_new_emails: list[dict] = []
    seen_message_ids: set[str] = set()

    for mailbox in MAILBOXES:
        upn = mailbox["upn"]
        name = mailbox["name"]

        for direction_label, folder in [("received", "messages"), ("sent", "sentitems")]:
            print(f"Scanning {name} {direction_label}...")

            try:
                messages = get_all_messages(token, upn, folder, since_iso)
            except Exception as exc:
                print(f"  WARNING: Could not scan {name} {direction_label}: {exc}")
                continue

            print(f"  {len(messages)} messages retrieved.")

            matched = skipped_dedup = skipped_internal = skipped_no_match = 0

            for msg in messages:
                msg_id = msg.get("id", "")

                if msg_id in seen_message_ids:
                    skipped_dedup += 1
                    continue

                entry = match_to_org(msg, upn, domain_to_org)
                if entry is None:
                    from_addr = _get_addr(msg.get("from") or {})
                    to_addrs = [_get_addr(r) for r in (msg.get("toRecipients") or []) if r]
                    cc_addrs = [_get_addr(r) for r in (msg.get("ccRecipients") or []) if r]
                    if _is_internal_only(from_addr, to_addrs, cc_addrs):
                        skipped_internal += 1
                    else:
                        skipped_no_match += 1
                    continue

                seen_message_ids.add(msg_id)
                all_new_emails.append(entry)
                matched += 1

            print(
                f"  matched: {matched} | "
                f"dedup: {skipped_dedup} | "
                f"internal: {skipped_internal} | "
                f"no match: {skipped_no_match}"
            )

    # Write to log
    print(f"\nWriting {len(all_new_emails)} emails to email_log.json...")
    count_added = add_emails_to_log(all_new_emails)
    print(f"  Added: {count_added} (after messageId dedup)")

    # Update Last Touch
    print("\nUpdating Last Touch on affected prospects...")
    affected_orgs: dict[str, str] = {}
    for entry in all_new_emails:
        org = entry["orgMatch"]
        date_str = entry["date"]
        if org and date_str:
            if org not in affected_orgs or date_str > affected_orgs[org]:
                affected_orgs[org] = date_str

    updated = update_last_touch(affected_orgs)
    print(f"  Updated {updated} prospect records across {len(affected_orgs)} orgs.")

    print(f"\n=== Backfill complete: {count_added} emails, {len(affected_orgs)} orgs ===")


if __name__ == "__main__":
    main()
