#!/usr/bin/env python3
"""
tony_calendar_scan.py — Scan Tony's Outlook calendar for investor meetings
and write them to the shared CRM meetings.json with dedup.

Runs on Tony's machine (or any machine with Tony's Graph token).
Authenticates as Tony via MSAL device code flow on first run,
then uses cached token silently on subsequent runs.

Usage:
    python3 tony_calendar_scan.py                # default: -7 to +14 days
    python3 tony_calendar_scan.py --days-back 3 --days-forward 21
    python3 tony_calendar_scan.py --dry-run      # preview without writing
"""

import argparse
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import msal
except ImportError:
    print("ERROR: msal not installed. Run: pip install msal")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Resolve paths relative to this script's location in tools/
# Works on both macOS (~/Dropbox/projects/arec-crm/) and Windows (C:\Users\Tony\Dropbox\projects\arec-crm\)
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
CRM_DIR = REPO_ROOT / "crm"
MEETINGS_JSON = CRM_DIR / "meetings.json"

# Azure app registration — same app as Oscar's setup
# Set these as environment variables or in a .env file
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")

SCOPES = [
    "https://graph.microsoft.com/Calendars.Read",
    "https://graph.microsoft.com/User.Read",
]

# Token cache — works on both macOS (~/) and Windows (C:\Users\Tony\)
TOKEN_CACHE_PATH = os.path.join(os.path.expanduser("~"), ".arec_tony_calendar_token.json")

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# Internal AREC domains — never match as external prospects
INTERNAL_DOMAINS = {
    "avilacapllc.com",
    "avilacapital.com",
    "encorefunds.com",
    "builderadvisorgroup.com",
    "south40capital.com",
    "falconegroup.info",
}

# Skip patterns — internal/recurring meetings that aren't investor meetings
SKIP_SUBJECTS = [
    r"^Deal Screen Meeting",
    r"^Pipeline Review",
    r"^HBF 201",
    r"^Coffee Talk",
    r"^AREC Exec Meeting",
    r"^Executive Finance Review",
    r"^AREC Fundraising Weekly",
    r"^Max Fundraising Status",
    r"^Weekly Catch-up",
    r"^Please dial in",
    r"^Canceled:",
    r"^Cancelled:",
]

SKIP_PATTERNS = [re.compile(p, re.IGNORECASE) for p in SKIP_SUBJECTS]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _load_cache():
    cache = msal.SerializableTokenCache()
    if os.path.exists(TOKEN_CACHE_PATH):
        with open(TOKEN_CACHE_PATH, "r") as f:
            cache.deserialize(f.read())
    return cache


def _save_cache(cache):
    if cache.has_state_changed:
        with open(TOKEN_CACHE_PATH, "w") as f:
            f.write(cache.serialize())


def get_access_token() -> str:
    """Acquire a Graph token for Tony's account via device code flow."""
    if not AZURE_CLIENT_ID or not AZURE_TENANT_ID:
        print("ERROR: AZURE_CLIENT_ID and AZURE_TENANT_ID must be set.")
        print("Export them or add to your shell profile.")
        sys.exit(1)

    cache = _load_cache()
    authority = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}"
    app = msal.PublicClientApplication(
        AZURE_CLIENT_ID, authority=authority, token_cache=cache
    )

    accounts = app.get_accounts()
    result = None
    if accounts:
        result = app.acquire_token_silent_with_error(SCOPES, account=accounts[0])

    if result and "error" in result and "access_token" not in result:
        if result.get("error") in ("invalid_grant", "interaction_required"):
            if os.path.exists(TOKEN_CACHE_PATH):
                os.remove(TOKEN_CACHE_PATH)
            result = None

    if not result or "access_token" not in result:
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            print(f"Device flow failed: {flow}")
            sys.exit(1)
        print(f"\n{flow['message']}")
        print("Waiting for authentication...\n")
        result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        error = result.get("error_description", result.get("error", "Unknown"))
        print(f"Auth failed: {error}")
        sys.exit(1)

    _save_cache(cache)
    return result["access_token"]


# ---------------------------------------------------------------------------
# Graph API
# ---------------------------------------------------------------------------

def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _get_all_pages(token: str, url: str, params: dict = None) -> list:
    items = []
    headers = _headers(token)
    while url:
        for attempt in range(4):
            resp = requests.get(
                url, headers=headers, params=params if attempt == 0 else None
            )
            params = None
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 5))
                print(f"  Rate limited — waiting {retry_after}s...")
                time.sleep(retry_after)
                continue
            if resp.status_code in (401, 403):
                print(f"  Auth error {resp.status_code}: {resp.text[:200]}")
                return items
            resp.raise_for_status()
            break
        else:
            print("  Rate-limit retries exhausted")
            return items
        data = resp.json()
        items.extend(data.get("value", []))
        url = data.get("@odata.nextLink")
    return items


def fetch_calendar_events(token: str, start: str, end: str) -> list:
    """Fetch Tony's calendar events in the given ISO range."""
    url = f"{GRAPH_BASE}/me/calendarView"
    params = {
        "startDateTime": start,
        "endDateTime": end,
        "$select": "id,subject,start,end,location,attendees,organizer,bodyPreview,isAllDay,isCancelled",
        "$orderby": "start/dateTime",
        "$top": 50,
    }
    return _get_all_pages(token, url, params=params)


# ---------------------------------------------------------------------------
# Domain matching
# ---------------------------------------------------------------------------

def load_org_domain_map() -> dict:
    """
    Build domain → org_name map from CRM data.
    Reads organizations.md for Domain fields.
    Format: - **Domain:** @domain.com
    """
    domain_to_org = {}

    filepath = CRM_DIR / "organizations.md"
    if not filepath.exists():
        print(f"WARNING: {filepath} not found")
        return domain_to_org

    content = filepath.read_text()
    current_org = None
    for line in content.split("\n"):
        if line.startswith("## ") and not line.startswith("### "):
            current_org = line[3:].strip()
        m = re.match(r"[-\s]*\*\*Domain:\*\*\s*@?([\w\.\-]+)", line)
        if m and current_org:
            domain_to_org[m.group(1).lower()] = current_org
    return domain_to_org


def extract_external_domains(attendees: list, organizer_email: str) -> set:
    """Extract non-AREC attendee domains."""
    domains = set()
    all_emails = [organizer_email] if organizer_email else []
    for a in attendees or []:
        email = a.get("emailAddress", {}).get("address", "")
        if email:
            all_emails.append(email)

    for email in all_emails:
        parts = email.lower().split("@")
        if len(parts) == 2:
            domain = parts[1]
            if domain not in INTERNAL_DOMAINS:
                domains.add(domain)
    return domains


def should_skip(subject: str, is_cancelled: bool) -> bool:
    """Check if event should be skipped (internal recurring, cancelled, etc.)."""
    if is_cancelled:
        return True
    for pattern in SKIP_PATTERNS:
        if pattern.search(subject):
            return True
    return False


# ---------------------------------------------------------------------------
# Meetings.json I/O
# ---------------------------------------------------------------------------

def load_meetings() -> list:
    if not MEETINGS_JSON.exists():
        return []
    with open(MEETINGS_JSON) as f:
        return json.load(f)


def save_meetings(meetings: list):
    with open(MEETINGS_JSON, "w") as f:
        json.dump(meetings, f, indent=2)


def get_existing_graph_ids(meetings: list) -> set:
    return {m["graph_event_id"] for m in meetings if m.get("graph_event_id")}


def format_attendees_str(attendees: list, domain_to_org: dict) -> str:
    """Format attendee list as human-readable string, highlighting external."""
    parts = []
    for a in attendees or []:
        name = a.get("emailAddress", {}).get("name", "")
        email = a.get("emailAddress", {}).get("address", "")
        domain = email.split("@")[1].lower() if "@" in email else ""

        if domain in INTERNAL_DOMAINS:
            first = name.split()[0] if name else email.split("@")[0]
            parts.append(first)
        else:
            org = domain_to_org.get(domain, "")
            label = f"{name} ({org})" if org else name or email
            parts.append(label)
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Scan Tony's calendar → meetings.json")
    parser.add_argument("--days-back", type=int, default=7, help="Days in the past to scan")
    parser.add_argument("--days-forward", type=int, default=14, help="Days in the future to scan")
    parser.add_argument("--dry-run", action="store_true", help="Preview matches without writing")
    args = parser.parse_args()

    print("=" * 60)
    print("Tony Calendar Scan → meetings.json")
    print("=" * 60)

    # Verify meetings.json path
    if not CRM_DIR.exists():
        print(f"ERROR: CRM directory not found at {CRM_DIR}")
        print("Make sure Dropbox is syncing and the arec-crm repo is accessible.")
        sys.exit(1)

    # Load org domain map
    domain_to_org = load_org_domain_map()
    print(f"Loaded {len(domain_to_org)} org domains from CRM")

    # Auth
    print("Authenticating...")
    token = get_access_token()
    print("Authenticated as Tony ✓")

    # Date range
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=args.days_back)).strftime("%Y-%m-%dT00:00:00Z")
    end = (now + timedelta(days=args.days_forward)).strftime("%Y-%m-%dT23:59:59Z")
    print(f"Scanning: {start[:10]} → {end[:10]}")

    # Fetch events
    raw_events = fetch_calendar_events(token, start, end)
    print(f"Fetched {len(raw_events)} calendar events")

    # Load existing meetings for dedup
    meetings = load_meetings()
    existing_gids = get_existing_graph_ids(meetings)
    print(f"Existing meetings: {len(meetings)} ({len(existing_gids)} with graph IDs)")

    # Process events
    new_meetings = []
    skipped = 0
    deduped = 0
    no_match = 0

    for event in raw_events:
        subject = event.get("subject", "")
        event_id = event.get("id", "")
        is_cancelled = event.get("isCancelled", False)
        attendees = event.get("attendees", [])
        organizer = event.get("organizer", {}).get("emailAddress", {}).get("address", "")
        start_dt = event.get("start", {}).get("dateTime", "")
        end_dt = event.get("end", {}).get("dateTime", "")
        location = event.get("location", {}).get("displayName", "")
        preview = event.get("bodyPreview", "")[:200]

        # Skip internal/recurring
        if should_skip(subject, is_cancelled):
            skipped += 1
            continue

        # Dedup by graph_event_id
        if event_id in existing_gids:
            deduped += 1
            continue

        # Dedup fallback: org+date match (catches cross-source duplicates)
        date_str_check = start_dt[:10] if start_dt else ""
        ext_domains_check = extract_external_domains(attendees, organizer)
        matched_orgs_check = [domain_to_org[d] for d in ext_domains_check if d in domain_to_org]
        if date_str_check and matched_orgs_check:
            org_check = matched_orgs_check[0].lower().strip()
            already_exists = False
            for existing in meetings:
                if existing.get('org', '').lower().strip() == org_check:
                    existing_date = existing.get('meeting_date', '')
                    if existing_date == date_str_check:
                        # Backfill graph_event_id on the existing meeting
                        if event_id and not existing.get('graph_event_id'):
                            existing['graph_event_id'] = event_id
                        already_exists = True
                        break
            if already_exists:
                deduped += 1
                continue

        # Match external attendee domains to CRM orgs
        ext_domains = extract_external_domains(attendees, organizer)
        matched_orgs = []
        for d in ext_domains:
            org = domain_to_org.get(d)
            if org:
                matched_orgs.append(org)

        if not matched_orgs and not ext_domains:
            skipped += 1  # all-internal meeting
            continue

        if not matched_orgs:
            no_match += 1
            continue

        # Build meeting record
        date_str = start_dt[:10] if start_dt else ""
        time_str = ""
        if start_dt and "T" in start_dt:
            try:
                dt = datetime.fromisoformat(start_dt.replace("Z", "+00:00"))
                pt = dt - timedelta(hours=7)  # rough UTC→PT
                time_str = pt.strftime("%I:%M%p PT").lstrip("0")
            except Exception:
                pass

        # Determine status
        if date_str and date_str < now.strftime("%Y-%m-%d"):
            status = "completed"
        else:
            status = "scheduled"

        meeting = {
            "id": str(uuid.uuid4()),
            "org": matched_orgs[0],  # primary org
            "offering": "",
            "meeting_date": date_str,
            "meeting_time": time_str,
            "title": subject,
            "attendees": format_attendees_str(attendees, domain_to_org),
            "graph_event_id": event_id,
            "source": "tony_calendar_scan",
            "status": status,
            "location": location or "",
            "notes": f"Via Tony's calendar. Preview: {preview[:100]}" if preview else "Via Tony's calendar.",
        }
        new_meetings.append(meeting)

    # Report
    print(f"\n{'=' * 60}")
    print(f"Results:")
    print(f"  Skipped (internal/recurring): {skipped}")
    print(f"  Deduped (already in CRM):     {deduped}")
    print(f"  No org match:                 {no_match}")
    print(f"  NEW investor meetings:        {len(new_meetings)}")
    print(f"{'=' * 60}\n")

    if new_meetings:
        for m in new_meetings:
            flag = "📅" if m["status"] == "scheduled" else "✅"
            print(f"  {flag} {m['meeting_date']} | {m['org'][:35]:35s} | {m['title'][:50]}")

    if args.dry_run:
        print("\n[DRY RUN] No changes written.")
        return

    if new_meetings:
        meetings.extend(new_meetings)
        save_meetings(meetings)
        print(f"\n✓ Wrote {len(new_meetings)} new meetings to {MEETINGS_JSON}")
        print(f"  Total meetings now: {len(meetings)}")
    else:
        print("\nNo new meetings to write.")


if __name__ == "__main__":
    main()
