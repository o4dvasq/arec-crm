"""
graph_poller.py — Centralized team email polling via Microsoft Graph (app-only auth).

Scans all 6 IR team mailboxes for the last 48 hours (received + sent),
matches emails to CRM organizations/contacts, and writes results to
crm/email_staging_queue.json for Oscar to review via /crm-update.

Sends a summary email to oscar@avilacapllc.com after every run.

Usage:
    PYTHONPATH=app python3 app/graph_poller.py
"""

import os

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

# Ensure app/ is on the path when run directly
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from auth.graph_auth import get_app_token
from sources.crm_reader import (
    get_org_by_domain,
    find_person_by_email,
    load_prospects,
    get_staging_dedup_ids,
    append_staged_items,
    load_email_log,
    is_ally_org,
    is_ally_email,
    get_individual_ally_name,
)
from sources.email_matching import INTERNAL_DOMAINS, _is_internal

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

SCAN_MAILBOXES = [
    "oscar@avilacapllc.com",
    "tony@avilacapllc.com",
    "truman@avilacapllc.com",
    "zachary.reisner@avilacapllc.com",
    "anthony@avilacapllc.com",
    "robert@avilacapllc.com",
]

AREC_OUTBOUND_DOMAINS = {"avilacapllc.com", "arecllc.com"}
SUMMARY_RECIPIENT = "oscar@avilacapllc.com"
LOOKBACK_HOURS = 48


# ---------------------------------------------------------------------------
# Graph HTTP helpers
# ---------------------------------------------------------------------------

def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _get_all_pages(token: str, url: str, params: dict = None) -> list:
    """GET a Graph endpoint and follow @odata.nextLink pagination with rate-limit retry."""
    items = []
    headers = _headers(token)

    while url:
        for attempt in range(4):
            resp = requests.get(url, headers=headers, params=params if attempt == 0 else None)
            params = None  # params only on first request; nextLink already includes them

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 5))
                time.sleep(retry_after)
                continue
            if resp.status_code in (401, 403):
                raise PermissionError(f"Auth error {resp.status_code}: {resp.text[:200]}")
            resp.raise_for_status()
            break
        else:
            print(f"[graph_poller] Rate-limit retries exhausted for {url}")
            return items

        data = resp.json()
        items.extend(data.get("value", []))
        url = data.get("@odata.nextLink")

    return items


# ---------------------------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------------------------

def _sender_domain(email_addr: str) -> str:
    if not email_addr or "@" not in email_addr:
        return ""
    return email_addr.lower().split("@")[-1]


def _infer_direction(sender_email: str) -> str:
    domain = _sender_domain(sender_email)
    return "outbound" if domain in AREC_OUTBOUND_DOMAINS else "inbound"


def _extract_recipients(msg: dict) -> list:
    """Extract all recipient email addresses from to + cc."""
    addrs = []
    for field in ("toRecipients", "ccRecipients"):
        for r in msg.get(field, []):
            addr = r.get("emailAddress", {}).get("address", "")
            if addr:
                addrs.append(addr.lower())
    return addrs


def _is_ally_participant(email: str) -> bool:
    """Return True if this email participant is a fundraising ally (domain-based or individual)."""
    if is_ally_email(email):
        return True
    domain = _sender_domain(email)
    org = get_org_by_domain(domain)
    return bool(org and is_ally_org(org))


def _scan_for_real_org(emails: list, via_ally: str) -> dict | None:
    """Scan a list of emails for the first non-ally CRM org match.
    Returns a match dict with via_ally set, or None."""
    for email in emails:
        if _is_internal(email) or _is_ally_participant(email):
            continue
        domain = _sender_domain(email)
        org = get_org_by_domain(domain)
        if org:
            return {"org": org, "contact": None, "match_tier": "domain",
                    "external_email": email, "via_ally": via_ally}
        person = find_person_by_email(email)
        if person:
            org = person.get("organization") or person.get("org", "")
            if org:
                return {"org": org, "contact": person.get("name", ""),
                        "match_tier": "person_email", "external_email": email,
                        "via_ally": via_ally}
    return None


def match_email_to_org(msg: dict) -> dict | None:
    """
    Try to match a Graph message to a CRM org using two-tier matching with ally pass-through.
    Returns a match dict or None.

    Tier 1: sender/recipient domain → crm_reader.get_org_by_domain()
    Tier 2: sender/recipient email → crm_reader.find_person_by_email()

    Ally pass-through: if the first match resolves to a fundraising ally (placement agent or
    individual connector), continue scanning remaining participants for a real prospect org.
    Ally-only emails (no real prospect found) return None and are silently skipped.
    """
    sender_email = msg.get("from", {}).get("emailAddress", {}).get("address", "")
    sender_name = msg.get("from", {}).get("emailAddress", {}).get("name", "")

    if _is_internal(sender_email):
        # Outbound — scan recipients for external org match, skipping ally recipients
        recipients = _extract_recipients(msg)
        via_ally = None
        for recip_email in recipients:
            if _is_internal(recip_email):
                continue
            domain = _sender_domain(recip_email)
            org = get_org_by_domain(domain)
            if org:
                if is_ally_org(org):
                    if via_ally is None:
                        via_ally = org
                    continue
                result = {"org": org, "contact": None, "match_tier": "domain",
                          "external_email": recip_email}
                if via_ally:
                    result["via_ally"] = via_ally
                return result
            person = find_person_by_email(recip_email)
            if person:
                org = person.get("organization") or person.get("org", "")
                if org:
                    if is_ally_org(org) or is_ally_email(recip_email):
                        if via_ally is None:
                            via_ally = org
                        continue
                    result = {"org": org, "contact": person.get("name", ""),
                              "match_tier": "person_email", "external_email": recip_email}
                    if via_ally:
                        result["via_ally"] = via_ally
                    return result
        return None

    # Inbound — individual ally email check runs first (handles Ira Lubert case where
    # his domain resolves to a real prospect org but he is an individual ally)
    if is_ally_email(sender_email):
        via_ally = get_individual_ally_name(sender_email) or sender_name
        recipients = _extract_recipients(msg)
        return _scan_for_real_org(recipients, via_ally)

    # Inbound — match sender by domain
    domain = _sender_domain(sender_email)
    org = get_org_by_domain(domain)
    if org:
        if is_ally_org(org):
            via_ally = org
            recipients = _extract_recipients(msg)
            return _scan_for_real_org(recipients, via_ally)
        return {"org": org, "contact": sender_name, "match_tier": "domain",
                "external_email": sender_email}

    # Inbound — match sender by person file
    person = find_person_by_email(sender_email)
    if person:
        org = person.get("organization") or person.get("org", "")
        if org:
            if is_ally_org(org):
                via_ally = org
                recipients = _extract_recipients(msg)
                return _scan_for_real_org(recipients, via_ally)
            return {"org": org, "contact": person.get("name", sender_name),
                    "match_tier": "person_email", "external_email": sender_email}

    return None


def _build_suggested_action(direction: str, org: str, sender_name: str,
                              contact_name: str | None, match_tier: str) -> str:
    """Generate a plain-text suggested action string (no Claude API call)."""
    prospects = load_prospects()
    prospect_orgs = {p.get("Org", "").strip().lower() for p in prospects}
    has_prospect = org.lower() in prospect_orgs

    display = contact_name or sender_name

    if match_tier == "person_email" and display:
        prefix = f"From {display} ({org})"
    else:
        prefix = None

    if direction == "inbound":
        if has_prospect:
            action = f"Log inbound from {sender_name} re: {org} — update Last Touch"
        else:
            action = f"Log inbound from {sender_name} — review if new prospect"
    else:
        if has_prospect:
            action = f"Log outbound to {org} — update Last Touch"
        else:
            action = f"Log outbound to {org} — review if new prospect"

    if prefix and match_tier == "person_email":
        action = f"{prefix}: {action}"

    return action


# ---------------------------------------------------------------------------
# Build dedup set from both staging queue and email_log
# ---------------------------------------------------------------------------

def build_dedup_set() -> set:
    """Return set of all known graph_message_ids (staging queue + email_log)."""
    dedup = get_staging_dedup_ids()
    log = load_email_log()
    for email in log.get("emails", []):
        mid = email.get("messageId")
        if mid:
            dedup.add(mid)
    return dedup


# ---------------------------------------------------------------------------
# Stage a single matched item
# ---------------------------------------------------------------------------

def build_staged_item(msg: dict, match: dict, mailbox: str, now_iso: str) -> dict:
    sender_email = msg.get("from", {}).get("emailAddress", {}).get("address", "")
    sender_name = msg.get("from", {}).get("emailAddress", {}).get("name", "")
    direction = _infer_direction(sender_email)
    recipients = _extract_recipients(msg)
    date_field = msg.get("receivedDateTime") or msg.get("sentDateTime", "")
    suggested = _build_suggested_action(
        direction, match["org"], sender_name, match.get("contact"), match["match_tier"]
    )
    return {
        "graph_message_id": msg["id"],
        "scanned_from_mailbox": mailbox,
        "matched_org": match["org"],
        "matched_contact": match.get("contact"),
        "match_tier": match["match_tier"],
        "via_ally": match.get("via_ally"),
        "sender_email": sender_email,
        "sender_name": sender_name,
        "recipient_emails": recipients,
        "subject": msg.get("subject", ""),
        "email_date": date_field,
        "direction": direction,
        "suggested_action": suggested,
        "status": "pending",
        "created_at": now_iso,
        "reviewed_at": None,
    }


# ---------------------------------------------------------------------------
# Per-mailbox scan
# ---------------------------------------------------------------------------

def scan_mailbox(token: str, mailbox: str, dedup_ids: set, cutoff_iso: str) -> dict:
    """
    Scan a single mailbox (received + sent) for the lookback window.
    Returns dict: {scanned, matched, unmatched, errors, staged_items}.
    """
    stats = {"scanned": 0, "matched": 0, "unmatched": 0, "errors": [], "staged_items": []}
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    message_batches = []

    # Received messages
    try:
        received = _get_all_pages(token,
            f"{GRAPH_BASE}/users/{mailbox}/messages",
            params={
                "$filter": f"receivedDateTime ge {cutoff_iso}",
                "$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,bodyPreview",
                "$orderby": "receivedDateTime desc",
                "$top": "50",
            }
        )
        message_batches.append(received)
    except Exception as e:
        stats["errors"].append(f"received scan failed: {e}")

    # Sent messages
    try:
        sent = _get_all_pages(token,
            f"{GRAPH_BASE}/users/{mailbox}/mailFolders/sentItems/messages",
            params={
                "$filter": f"sentDateTime ge {cutoff_iso}",
                "$select": "id,subject,from,toRecipients,ccRecipients,sentDateTime,bodyPreview",
                "$orderby": "sentDateTime desc",
                "$top": "50",
            }
        )
        message_batches.append(sent)
    except Exception as e:
        stats["errors"].append(f"sent scan failed: {e}")

    for batch in message_batches:
        for msg in batch:
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

    return stats


# ---------------------------------------------------------------------------
# Summary email
# ---------------------------------------------------------------------------

def send_summary_email(token: str, run_date: str, run_time: str,
                        mailbox_stats: dict, all_staged: list, errors: dict) -> None:
    """Send HTML summary email to oscar@avilacapllc.com."""
    total_staged = len(all_staged)

    # Build staged items section
    items_html = ""
    for item in all_staged:
        items_html += f"""
  <p>
    <strong>Org:</strong> {item['matched_org']}<br>
    <strong>From/To:</strong> {item['sender_name']} &lt;{item['sender_email']}&gt;<br>
    <strong>Mailbox:</strong> {item['scanned_from_mailbox']}<br>
    <strong>Date:</strong> {item['email_date']}<br>
    <strong>Subject:</strong> {item['subject']}<br>
    <strong>Suggested Action:</strong> {item['suggested_action']}<br>
    <strong>Match:</strong> {item['match_tier']} match
  </p>
  <hr>"""

    # Build mailbox results section
    mailbox_rows = ""
    for mb in SCAN_MAILBOXES:
        s = mailbox_stats.get(mb, {})
        mb_errors = errors.get(mb, [])
        status = "✓" if not mb_errors else "✗"
        mailbox_rows += (
            f"  {status}  {mb:<40}  "
            f"{s.get('scanned', 0)} scanned, {s.get('matched', 0)} matched<br>\n"
        )

    # Build errors section
    errors_html = ""
    for mb, errs in errors.items():
        for err in errs:
            errors_html += f"  <strong>{mb}:</strong> {err}<br>\n"

    body_html = f"""<pre>
AREC CRM Email Scan — {run_date}
Run completed at {run_time} PT

STAGED FOR REVIEW: {total_staged} items
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
</pre>
{items_html}
<pre>
MAILBOX SCAN RESULTS:
{mailbox_rows}
{"ERRORS:" + chr(10) + errors_html if errors_html else ""}
To review: run /crm-update in Claude Desktop
</pre>"""

    subject = f"AREC CRM — Email Scan Summary {run_date} — {total_staged} items staged"
    url = f"{GRAPH_BASE}/users/oscar@avilacapllc.com/sendMail"
    headers = _headers(token)
    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": body_html},
            "toRecipients": [{"emailAddress": {"address": SUMMARY_RECIPIENT}}],
        }
    }
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code not in (200, 202):
        print(f"[graph_poller] send_summary_email failed {resp.status_code}: {resp.text[:200]}")
    else:
        print(f"[graph_poller] Summary email sent to {SUMMARY_RECIPIENT}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=LOOKBACK_HOURS)
    cutoff_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    run_date = now.strftime("%Y-%m-%d")
    run_time = now.strftime("%H:%M")

    print(f"[graph_poller] Starting run at {now.isoformat()} — cutoff {cutoff_iso}")

    token = get_app_token()
    print("[graph_poller] App token acquired")

    dedup_ids = build_dedup_set()
    print(f"[graph_poller] Dedup set: {len(dedup_ids)} known IDs")

    all_staged = []
    mailbox_stats = {}
    errors = {}

    for mailbox in SCAN_MAILBOXES:
        print(f"[graph_poller] Scanning {mailbox}...")
        try:
            stats = scan_mailbox(token, mailbox, dedup_ids, cutoff_iso)
            mailbox_stats[mailbox] = stats
            all_staged.extend(stats["staged_items"])
            if stats["errors"]:
                errors[mailbox] = stats["errors"]
                print(f"[graph_poller]   {mailbox}: {stats['scanned']} scanned, "
                      f"{stats['matched']} matched — ERRORS: {stats['errors']}")
            else:
                print(f"[graph_poller]   {mailbox}: {stats['scanned']} scanned, "
                      f"{stats['matched']} matched")
        except Exception as e:
            errors[mailbox] = [str(e)]
            mailbox_stats[mailbox] = {"scanned": 0, "matched": 0, "unmatched": 0,
                                       "errors": [str(e)], "staged_items": []}
            print(f"[graph_poller]   {mailbox}: FAILED — {e}")

    # Write staged items to queue
    if all_staged:
        added = append_staged_items(all_staged)
        print(f"[graph_poller] Staged {added} new items (of {len(all_staged)} matched)")
    else:
        print("[graph_poller] No new matches to stage")

    # Send summary email
    try:
        send_summary_email(token, run_date, run_time, mailbox_stats, all_staged, errors)
    except Exception as e:
        print(f"[graph_poller] Failed to send summary email: {e}")

    total_scanned = sum(s.get("scanned", 0) for s in mailbox_stats.values())
    total_matched = sum(s.get("matched", 0) for s in mailbox_stats.values())
    print(f"[graph_poller] Done — {total_scanned} scanned, {total_matched} matched, "
          f"{len(all_staged)} staged, {len(errors)} mailbox error(s)")


if __name__ == "__main__":
    main()
