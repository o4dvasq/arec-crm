#!/usr/bin/env python3
"""
drain_inbox.py — AI Email Inbox drain script

Reads unread messages from the crm@avilacapllc.com shared mailbox,
parses Oscar's intent note from forwarded emails, and appends structured
[AI Inbox] entries to inbox.md.

Usage:
    python3 drain_inbox.py
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from auth.graph_auth import get_access_token
from sources.ms_graph import (
    get_shared_mailbox_messages,
    mark_as_read,
    move_message,
)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX_PATH = os.path.join(_PROJECT_ROOT, "inbox.md")
LAST_RUN_PATH = os.path.join(_PROJECT_ROOT, "crm", "drain_last_run.json")
SEEN_IDS_PATH = os.path.join(_PROJECT_ROOT, "crm", "drain_seen_ids.json")

# Forward delimiter patterns, checked in order
FORWARD_PATTERNS = [
    r"-{4,}\s*Forwarded Message\s*-{4,}",
    r"-{4,}\s*Original Message\s*-{4,}",
    r"Begin forwarded message:",
    # Loose "From: ... \nDate:" or "From: ... \nSent:" pattern
    r"(?m)^From:\s+.+\n(?:Date|Sent):",
]

# Header field prefixes to consume when extracting the original email header
HEADER_PREFIXES = ("from:", "to:", "cc:", "bcc:", "date:", "sent:", "subject:", "reply-to:")


# ---------------------------------------------------------------------------
# Dedup helpers
# ---------------------------------------------------------------------------

def _load_seen_ids() -> dict:
    """Load crm/drain_seen_ids.json, return empty structure if missing."""
    if os.path.exists(SEEN_IDS_PATH):
        try:
            with open(SEEN_IDS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"seen": {}}


def _save_seen_ids(data: dict) -> None:
    with open(SEEN_IDS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _prune_seen_ids(data: dict, days: int = 30) -> dict:
    """Remove entries older than `days` days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    data["seen"] = {
        msg_id: ts
        for msg_id, ts in data["seen"].items()
        if ts >= cutoff
    }
    return data


def _write_last_run(processed: int, skipped: int, exit_code: int, error: str = None) -> None:
    """Write crm/drain_last_run.json with run metadata."""
    meta = {
        "last_run": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "messages_processed": processed,
        "messages_skipped_dedup": skipped,
        "exit_code": exit_code,
        "error": error,
    }
    try:
        with open(LAST_RUN_PATH, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
    except OSError as e:
        print(f"[drain_inbox] WARNING: could not write drain_last_run.json: {e}")


# ---------------------------------------------------------------------------
# Email parsing
# ---------------------------------------------------------------------------

def _strip_html(text: str) -> str:
    """Remove HTML tags and decode common entities."""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _parse_header_block(lines: list[str]) -> tuple[str, str]:
    """
    Extract From and Subject values from a list of header lines.
    Returns (original_from, original_subject).
    """
    original_from = ""
    original_subject = ""
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("from:") and not original_from:
            original_from = stripped[5:].strip()
        elif stripped.lower().startswith("subject:") and not original_subject:
            original_subject = stripped[8:].strip()
    return original_from, original_subject


def parse_forwarded_email(body: str) -> tuple[str, bool, str, str, str]:
    """
    Split an email body into Oscar's note and the forwarded original.

    Returns:
        (sender_note, is_forward, original_from, original_subject, original_body)

    If no forward delimiter is found, sender_note = entire body, is_forward = False.
    """
    for pattern in FORWARD_PATTERNS:
        m = re.search(pattern, body, re.IGNORECASE)
        if m:
            sender_note = body[: m.start()].strip()
            remainder = body[m.end() :].strip()

            # Walk through remainder lines to extract header fields
            lines = remainder.splitlines()
            header_lines = []
            body_start = 0

            for i, line in enumerate(lines):
                stripped = line.strip()
                if not stripped:
                    # Blank line — if we've seen at least one header field, body starts next
                    if header_lines:
                        body_start = i + 1
                        break
                    continue
                if any(stripped.lower().startswith(p) for p in HEADER_PREFIXES):
                    header_lines.append(stripped)
                    body_start = i + 1
                else:
                    # First non-header, non-blank line — body starts here
                    body_start = i
                    break

            original_from, original_subject = _parse_header_block(header_lines)
            original_body = "\n".join(lines[body_start:]).strip()

            return sender_note, True, original_from, original_subject, original_body

    # No forward delimiter found — treat entire body as intent note
    return body.strip(), False, "", "", ""


def parse_inbox_message(message: dict) -> dict:
    """
    Parse a raw Graph API message dict into a structured inbox entry.

    Returns:
    {
      'source': 'ai_inbox',
      'message_id': str,
      'received_at': str,          # ISO-8601
      'subject': str,
      'sender_name': str,
      'sender_email': str,
      'sender_note': str,          # Oscar's intent text
      'original_from': str,        # empty if not a forward
      'original_subject': str,     # empty if not a forward
      'original_body': str,        # empty if not a forward
      'is_forward': bool,
      'raw_body': str,
    }
    """
    body_info = message.get("body", {})
    raw_body = body_info.get("content", "")
    content_type = body_info.get("contentType", "text")

    if content_type.lower() == "html":
        raw_body = _strip_html(raw_body)

    sender_note, is_forward, original_from, original_subject, original_body = (
        parse_forwarded_email(raw_body)
    )

    sender_info = message.get("from", {}).get("emailAddress", {})

    return {
        "source": "ai_inbox",
        "message_id": message.get("id", ""),
        "received_at": message.get("receivedDateTime", ""),
        "subject": message.get("subject", ""),
        "sender_name": sender_info.get("name", ""),
        "sender_email": sender_info.get("address", ""),
        "sender_note": sender_note,
        "original_from": original_from,
        "original_subject": original_subject,
        "original_body": original_body,
        "is_forward": is_forward,
        "raw_body": raw_body,
    }


def write_to_inbox_md(entry: dict) -> None:
    """
    Append a structured [AI Inbox] entry to inbox.md.

    Format for forwards:
        ## [AI Inbox] 2026-03-02T14:23 — FW: Fund II priorities — Tony
        **Intent:** Hey AI, Tony just sent updated priorities...
        **Original From:** Tony Avila <tony@...>
        **Original Subject:** Fund II priorities
        **Original Content:**
        Oscar — here are the updated Q1 priorities: ...

    Format for direct emails:
        ## [AI Inbox] 2026-03-02T16:45 — CRM session notes
        **Intent:** Talked to James today. Merseyside wants...
    """
    timestamp = entry["received_at"][:16]  # YYYY-MM-DDTHH:MM
    header = f"## [AI Inbox] {timestamp} — {entry['subject']}"

    lines = [header, ""]

    sender_note = entry["sender_note"] or "(no note)"
    lines.append(f"**Intent:** {sender_note}")

    if entry["is_forward"]:
        lines.append("")
        lines.append(f"**Original From:** {entry['original_from']}")
        lines.append(f"**Original Subject:** {entry['original_subject']}")
        lines.append("")
        lines.append("**Original Content:**")
        lines.append(entry["original_body"])

    lines.append("")

    with open(INBOX_PATH, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def drain_inbox() -> int:
    """
    Main entry point. Returns count of processed messages.
    Writes crm/drain_last_run.json on every exit (success or failure).
    Skips messages already recorded in crm/drain_seen_ids.json to prevent
    duplicate inbox.md entries when mark-as-read fails.
    """
    seen_data = _load_seen_ids()
    seen_data = _prune_seen_ids(seen_data)

    try:
        token = get_access_token()
    except Exception as e:
        print(f"[drain_inbox] Auth failed: {e}")
        _write_last_run(processed=0, skipped=0, exit_code=1, error=str(e))
        return 0

    ai_inbox_email = os.environ.get("AI_INBOX_EMAIL", "crm@avilacapllc.com")

    print(f"[drain_inbox] Draining shared mailbox {ai_inbox_email}")

    try:
        messages = get_shared_mailbox_messages(token, mailbox=ai_inbox_email)
    except Exception as e:
        print(f"[drain_inbox] Failed to fetch messages: {e}")
        _write_last_run(processed=0, skipped=0, exit_code=1, error=str(e))
        return 0

    if not messages:
        print("[drain_inbox] No unread messages found")
        _write_last_run(processed=0, skipped=0, exit_code=0)
        _save_seen_ids(seen_data)
        return 0

    processed = 0
    skipped = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    for msg in messages:
        msg_id = msg.get("id", "")

        # Dedup: skip if already written to inbox.md in a prior run
        if msg_id and msg_id in seen_data["seen"]:
            skipped += 1
            print(f"  ⟳ skipping (already processed): {msg.get('subject', '(no subject)')}")
            continue

        entry = parse_inbox_message(msg)
        write_to_inbox_md(entry)

        # Record in seen IDs before attempting mark-as-read
        # (so even if mark-as-read fails, we won't duplicate on next run)
        if msg_id:
            seen_data["seen"][msg_id] = now_iso

        mark_as_read(token, mailbox=ai_inbox_email, message_id=msg_id)
        move_message(
            token,
            mailbox=ai_inbox_email,
            message_id=msg_id,
            destination_folder="Processed",
        )

        processed += 1
        subject = entry.get("subject", "(no subject)")
        fwd = " [forward]" if entry["is_forward"] else ""
        print(f"  ✓ {subject}{fwd}")

    _save_seen_ids(seen_data)
    _write_last_run(processed=processed, skipped=skipped, exit_code=0)

    print(f"[drain_inbox] Processed {processed} message(s), skipped {skipped} duplicate(s) → inbox.md")
    return processed


if __name__ == "__main__":
    drain_inbox()
