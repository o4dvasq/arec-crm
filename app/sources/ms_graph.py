"""
ms_graph.py — Microsoft Graph API data fetching (CC-04)

Fetches calendar events, emails, and Teams chats using a Bearer token.
Handles pagination and rate-limit retries.
"""

import os
import time
from datetime import datetime, timedelta, timezone

import requests

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _user_id() -> str:
    uid = os.environ.get("MS_USER_ID", "me")
    return uid if uid else "me"


def _get_all_pages(token: str, url: str, params: dict = None) -> list[dict]:
    """GET a Graph endpoint and follow @odata.nextLink pagination."""
    items = []
    headers = _headers(token)

    while url:
        for attempt in range(4):
            resp = requests.get(url, headers=headers, params=params if attempt == 0 else None)
            params = None  # params only on first request; nextLink already has them

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 5))
                time.sleep(retry_after)
                continue
            if resp.status_code in (401, 403):
                # Log and bail — do not retry auth failures
                print(f"[ms_graph] Auth error {resp.status_code} on {url}: {resp.text[:200]}")
                return items
            resp.raise_for_status()
            break
        else:
            print(f"[ms_graph] Rate-limit retries exhausted for {url}")
            return items

        data = resp.json()
        items.extend(data.get("value", []))
        url = data.get("@odata.nextLink")

    return items


def _fmt_attendees(raw: list) -> list[dict]:
    """Normalize attendee list from Graph event."""
    result = []
    for a in raw or []:
        email_info = a.get("emailAddress", {})
        result.append({
            "name": email_info.get("name", ""),
            "email": email_info.get("address", ""),
            "type": a.get("type", ""),
        })
    return result


def get_today_events(token: str) -> list[dict]:
    """Return today's calendar events (local timezone)."""
    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    return get_events_range(
        token,
        start_of_day.strftime("%Y-%m-%dT%H:%M:%SZ"),
        end_of_day.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def get_tomorrow_events(token: str) -> list[dict]:
    """Return tomorrow's calendar events (local timezone)."""
    now = datetime.now(timezone.utc)
    start_of_tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    end_of_tomorrow = start_of_tomorrow + timedelta(days=1)

    return get_events_range(
        token,
        start_of_tomorrow.strftime("%Y-%m-%dT%H:%M:%SZ"),
        end_of_tomorrow.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def get_events_range(token: str, start: str, end: str) -> list[dict]:
    """
    Return calendar events in the given ISO-8601 time range.
    start / end format: '2026-03-02T00:00:00Z'
    """
    uid = _user_id()
    url = f"{GRAPH_BASE}/users/{uid}/calendarView"
    params = {
        "startDateTime": start,
        "endDateTime": end,
        "$select": "subject,start,end,location,attendees,organizer,bodyPreview,isAllDay",
        "$orderby": "start/dateTime",
        "$top": 50,
    }

    raw = _get_all_pages(token, url, params=params)

    events = []
    for e in raw:
        start_raw = e.get("start", {})
        end_raw = e.get("end", {})
        events.append({
            "subject": e.get("subject", ""),
            "start": start_raw.get("dateTime", ""),
            "end": end_raw.get("dateTime", ""),
            "timezone": start_raw.get("timeZone", "UTC"),
            "location": e.get("location", {}).get("displayName", ""),
            "attendees": _fmt_attendees(e.get("attendees", [])),
            "organizer": e.get("organizer", {}).get("emailAddress", {}).get("address", ""),
            "preview": e.get("bodyPreview", "")[:200],
            "is_all_day": e.get("isAllDay", False),
        })

    return events


def get_recent_emails(token: str, hours: int = 18) -> list[dict]:
    """
    Return emails received in the last N hours.
    Returns list of dicts with subject, from_email, from_name, received, preview, importance.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    uid = _user_id()
    url = f"{GRAPH_BASE}/users/{uid}/mailFolders/archive/messages"
    params = {
        "$filter": f"receivedDateTime ge {cutoff_str}",
        "$select": "subject,from,receivedDateTime,bodyPreview,importance,isRead",
        "$orderby": "receivedDateTime desc",
        "$top": 50,
    }

    raw = _get_all_pages(token, url, params=params)

    emails = []
    for m in raw:
        sender = m.get("from", {}).get("emailAddress", {})
        emails.append({
            "subject": m.get("subject", ""),
            "from_name": sender.get("name", ""),
            "from_email": sender.get("address", ""),
            "received": m.get("receivedDateTime", ""),
            "preview": m.get("bodyPreview", "")[:300],
            "importance": m.get("importance", "normal"),
            "is_read": m.get("isRead", False),
        })

    return emails


# ---------------------------------------------------------------------------
# Shared mailbox / folder reads
# ---------------------------------------------------------------------------

def get_shared_mailbox_messages(token: str, mailbox: str) -> list[dict]:
    """
    Return unread messages from a shared mailbox.
    Requires Mail.Read.Shared permission on the Azure app.
    Returns full body (not just preview) for forward parsing.
    """
    url = f"{GRAPH_BASE}/users/{mailbox}/messages"
    params = {
        "$filter": "isRead eq false",
        "$orderby": "receivedDateTime desc",
        "$select": "id,subject,from,receivedDateTime,body,isRead",
        "$top": 50,
    }
    return _get_all_pages(token, url, params=params)


def get_folder_messages(token: str, folder: str, mailbox: str = None) -> list[dict]:
    """
    Return all messages from a named mail folder in Oscar's (or a given) mailbox.
    Used for legacy migration drain (--folder flag).
    """
    uid = mailbox or _user_id()

    # Resolve folder display name → folder ID
    folders_url = f"{GRAPH_BASE}/users/{uid}/mailFolders"
    folders = _get_all_pages(token, folders_url, params={"$top": 100})
    folder_id = None
    for f in folders:
        if f.get("displayName", "").lower() == folder.lstrip("#").lower():
            folder_id = f.get("id")
            break

    if not folder_id:
        print(f"[ms_graph] Folder '{folder}' not found in mailbox {uid}")
        return []

    url = f"{GRAPH_BASE}/users/{uid}/mailFolders/{folder_id}/messages"
    params = {
        "$select": "id,subject,from,receivedDateTime,body,isRead",
        "$top": 50,
    }
    return _get_all_pages(token, url, params=params)


def mark_as_read(token: str, mailbox: str, message_id: str) -> None:
    """Mark a message as read via PATCH."""
    url = f"{GRAPH_BASE}/users/{mailbox}/messages/{message_id}"
    resp = requests.patch(url, headers=_headers(token), json={"isRead": True})
    if resp.status_code not in (200, 204):
        print(f"[ms_graph] mark_as_read failed {resp.status_code}: {resp.text[:200]}")


# Module-level cache: mailbox → folder_id (lives for process duration)
_processed_folder_id: dict[str, str] = {}


def move_message(
    token: str,
    mailbox: str,
    message_id: str,
    destination_folder: str = "Processed",
) -> None:
    """
    Move a message to a destination folder in the shared mailbox.
    Auto-creates the folder if it doesn't exist.
    Caches the folder ID after first lookup.
    """
    cache_key = f"{mailbox}:{destination_folder}"

    if cache_key not in _processed_folder_id:
        # Look up folder by display name
        url = f"{GRAPH_BASE}/users/{mailbox}/mailFolders"
        folders = _get_all_pages(token, url, params={"$top": 100})
        folder_id = None
        for f in folders:
            if f.get("displayName", "").lower() == destination_folder.lower():
                folder_id = f.get("id")
                break

        if not folder_id:
            # Create the folder
            resp = requests.post(
                f"{GRAPH_BASE}/users/{mailbox}/mailFolders",
                headers=_headers(token),
                json={"displayName": destination_folder},
            )
            if resp.status_code in (200, 201):
                folder_id = resp.json().get("id")
            else:
                print(f"[ms_graph] Could not create folder '{destination_folder}': {resp.text[:200]}")
                return

        _processed_folder_id[cache_key] = folder_id

    folder_id = _processed_folder_id[cache_key]
    move_url = f"{GRAPH_BASE}/users/{mailbox}/messages/{message_id}/move"
    resp = requests.post(move_url, headers=_headers(token), json={"destinationId": folder_id})
    if resp.status_code not in (200, 201):
        print(f"[ms_graph] move_message failed {resp.status_code}: {resp.text[:200]}")


def search_emails_deep(
    token: str,
    domain: str,
    contact_emails: list[str],
    days_back: int = 90,
    mailbox: str = None,
) -> list[dict]:
    """
    Deep search for emails related to an org over the past N days.

    Searches:
    - Archive folder (incoming) — by sender domain
    - Sent Items (outgoing) — by recipient domain
    - Archive + Sent by individual contact email addresses (up to 5)

    Args:
        mailbox: Optional delegated mailbox address (e.g., 'tavila@avilacapllc.com').
                 If None, searches the authenticated user's own mailbox.

    Returns list of normalized email dicts (not yet log entries — caller adds
    orgMatch, summary, etc. before writing to email_log.json).
    Each dict includes a 'mailbox' field to identify the source mailbox.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    cutoff_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    uid = mailbox or _user_id()
    seen_ids: set[str] = set()
    results: list[dict] = []

    # Normalize domain — strip leading "@" if present
    domain_clean = domain.lstrip("@")  # e.g. "nepc.com" or "nepc"

    def _search(folder: str, kql: str, is_sent: bool) -> None:
        """Run a single KQL $search against a mail folder and collect results."""
        url = f"{GRAPH_BASE}/users/{uid}/mailFolders/{folder}/messages"
        params = {
            "$search": f'"{kql}"',
            "$select": "id,subject,from,toRecipients,receivedDateTime,bodyPreview,internetMessageId",
            "$top": 100,
        }
        try:
            raw = _get_all_pages(token, url, params=params)
        except Exception as e:
            print(f"[ms_graph] deep_search '{kql}' in {folder} failed: {e}")
            return

        for m in raw:
            graph_id = m.get("id", "")
            if not graph_id or graph_id in seen_ids:
                continue

            received = m.get("receivedDateTime", "")
            # Filter to within the requested window
            if received and received < cutoff_iso:
                continue

            seen_ids.add(graph_id)

            sender = m.get("from", {}).get("emailAddress", {})
            recipients = [
                r.get("emailAddress", {}).get("address", "")
                for r in m.get("toRecipients", [])
            ]

            # Prefer internetMessageId for stable dedup; fall back to Graph ID
            stable_id = m.get("internetMessageId") or graph_id

            results.append({
                "messageId": stable_id,
                "graphId": graph_id,
                "date": received[:10] if received else "",
                "timestamp": received,
                "subject": m.get("subject", ""),
                "from": sender.get("address", ""),
                "fromName": sender.get("name", ""),
                "to": recipients,
                "preview": m.get("bodyPreview", "")[:300],
                "isSent": is_sent,
                "mailbox": mailbox if mailbox else None,
            })

    # --- Archive (incoming) by sender domain ---
    _search("archive", f"from:{domain_clean}", is_sent=False)

    # --- Sent Items (outgoing) by recipient domain ---
    _search("sentitems", f"to:{domain_clean}", is_sent=True)

    # --- Per-contact searches for contacts whose domain doesn't match (e.g. personal email) ---
    for email in contact_emails[:5]:
        if not email or domain_clean.split(".")[0].lower() in email.lower():
            continue  # Already covered by domain search
        _search("archive", f"from:{email}", is_sent=False)
        _search("sentitems", f"to:{email}", is_sent=True)

    # Final dedup pass (different KQL queries can surface the same message)
    final: list[dict] = []
    final_ids: set[str] = set()
    for r in results:
        key = r.get("messageId") or r.get("graphId")
        if key and key not in final_ids:
            final_ids.add(key)
            final.append(r)

    return final


def get_recent_chats(token: str, hours: int = 24) -> list[dict]:
    """
    Return recent Teams chat messages from the last N hours.
    Returns list of dicts with chat_id, sender, content_preview, created.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Get all chats first
    url = f"{GRAPH_BASE}/me/chats"
    params = {"$select": "id,topic,chatType", "$top": 20}

    try:
        chats = _get_all_pages(token, url, params=params)
    except Exception as e:
        print(f"[ms_graph] Could not fetch chats: {e}")
        return []

    messages = []
    for chat in chats:
        chat_id = chat.get("id", "")
        if not chat_id:
            continue

        msg_url = f"{GRAPH_BASE}/me/chats/{chat_id}/messages"
        msg_params = {
            "$filter": f"createdDateTime ge {cutoff.strftime('%Y-%m-%dT%H:%M:%SZ')}",
            "$top": 20,
        }

        try:
            raw_msgs = _get_all_pages(token, msg_url, params=msg_params)
        except Exception:
            continue

        for msg in raw_msgs:
            sender_info = msg.get("from", {}).get("user", {})
            body = msg.get("body", {}).get("content", "")
            # Strip HTML tags if present
            import re
            body_text = re.sub(r"<[^>]+>", "", body).strip()[:300]

            messages.append({
                "chat_id": chat_id,
                "chat_topic": chat.get("topic", ""),
                "sender": sender_info.get("displayName", ""),
                "sender_email": sender_info.get("userPrincipalName", ""),
                "content_preview": body_text,
                "created": msg.get("createdDateTime", ""),
            })

    return messages
