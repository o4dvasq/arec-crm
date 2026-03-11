#!/usr/bin/env python3
"""
drain_inbox.py — AI Email Inbox drain script

Reads unread messages from the crm@avilacapllc.com shared mailbox,
parses Oscar's intent note from forwarded emails, and appends structured
[AI Inbox] entries to inbox.md.

Usage:
    python3 drain_inbox.py
"""

import os
import re
import sys

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


def drain_inbox() -> int:
    """
    Main entry point. Returns count of processed messages.
    """
    token = get_access_token()
    ai_inbox_email = os.environ.get("AI_INBOX_EMAIL", "crm@avilacapllc.com")

    print(f"[drain_inbox] Draining shared mailbox {ai_inbox_email}")
    messages = get_shared_mailbox_messages(token, mailbox=ai_inbox_email)

    if not messages:
        print("[drain_inbox] No unread messages found")
        return 0

    processed = 0
    for msg in messages:
        entry = parse_inbox_message(msg)
        write_to_inbox_md(entry)

        mark_as_read(token, mailbox=ai_inbox_email, message_id=msg["id"])
        move_message(
            token,
            mailbox=ai_inbox_email,
            message_id=msg["id"],
            destination_folder="Processed",
        )

        processed += 1
        subject = entry.get("subject", "(no subject)")
        fwd = " [forward]" if entry["is_forward"] else ""
        print(f"  ✓ {subject}{fwd}")

    print(f"[drain_inbox] Processed {processed} message(s) → inbox.md")
    return processed


if __name__ == "__main__":
    drain_inbox()
