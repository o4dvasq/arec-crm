# CC-07: AI Email Inbox (drain_inbox.py)

**Target:** `~/Dropbox/Tech/ClaudeProductivity/app/drain_inbox.py`
**Depends on:** CC-04 (Graph auth)
**Blocks:** Nothing (enhances /crm:inbox and /productivity:update)

---

## Purpose

Poll the shared mailbox `ai@avilacapital.com` via Graph API. When Oscar forwards an email there with a personal note at the top, this script extracts the note (intent signal) and the forwarded email body, then writes structured entries to `crm/ai_inbox_queue.md` for Cowork to process via `/crm:inbox`.

**This replaces** the old `p:` subject prefix + Outlook rule + `#Productivity` folder workflow.

## How It Works

1. Oscar forwards any email to `ai@avilacapital.com`
2. He adds a note at the top: "Add this to Merseyside file" or "Follow up next week" or "CRM — new prospect"
3. `drain_inbox.py` reads the mailbox, extracts Oscar's note + original email
4. Writes to `crm/ai_inbox_queue.md` with status `pending`
5. Next `/productivity:update` or `/crm:inbox` run processes the queue

## Graph API Access

The shared mailbox `ai@avilacapital.com` is an M365 shared mailbox. Access via:

```python
# Read shared mailbox messages
GET https://graph.microsoft.com/v1.0/users/{shared_mailbox_id}/messages
  ?$filter=isRead eq false
  &$orderby=receivedDateTime desc
  &$top=50
```

Requires `Mail.Read.Shared` permission in the Azure app registration (same app as CC-04).

After processing each message, mark it as read:
```python
PATCH https://graph.microsoft.com/v1.0/users/{shared_mailbox_id}/messages/{message_id}
Body: {"isRead": true}
```

## Email Parsing

Oscar's note is the text **above** the forwarded message delimiter. Common delimiters:
- `---------- Forwarded message ----------`
- `From:` line followed by `Sent:` or `Date:`
- `-----Original Message-----`

```python
def parse_forwarded_email(body: str) → tuple[str, str]:
    """Returns (oscar_note, original_email_body)"""
```

If no delimiter found, treat the entire body as Oscar's note (it may be a direct email to the inbox, not a forward).

## Output Format

Append to `crm/ai_inbox_queue.md`:

```markdown
## 2026-03-02

### FW: Encore Fund III Materials
- **From:** susannahfriar@wirral.gov.uk
- **Intent:** Add this to Merseyside file — she's confirmed for March 25 DD
- **Org:** Merseyside Pension Fund
- **Status:** pending
- **Action Taken:**
```

**Org matching:** Attempt to match the original sender email against CRM contacts (same logic as CC-04 auto-capture). If no match, set Org to "Unknown".

**Status values:** `pending` | `actioned` | `skipped`

## Script

```python
#!/usr/bin/env python3
"""Drain the ai@avilacapital.com shared mailbox into crm/ai_inbox_queue.md"""

import os
from auth.graph_auth import get_access_token
from sources.crm_reader import ...

SHARED_MAILBOX = "ai@avilacapital.com"  # or use MS_SHARED_MAILBOX_ID env var
QUEUE_PATH = os.path.expanduser("~/Dropbox/Tech/ClaudeProductivity/crm/ai_inbox_queue.md")

def drain_inbox():
    token = get_access_token()
    messages = fetch_unread_messages(token)

    for msg in messages:
        oscar_note, original_body = parse_forwarded_email(msg['body'])
        org = try_match_org(msg['from_email'])

        append_to_queue(
            date=msg['received_date'],
            subject=msg['subject'],
            from_email=msg['from_email'],
            intent=oscar_note,
            org=org
        )

        mark_as_read(token, msg['id'])

    print(f"Processed {len(messages)} messages")

if __name__ == "__main__":
    drain_inbox()
```

## Environment Variable Addition

```
MS_SHARED_MAILBOX_ID=<object ID of ai@avilacapital.com shared mailbox>
```

Or use the email directly with delegated access if the app registration has shared mailbox permissions.

## Manual Trigger

```bash
python3 ~/Dropbox/Tech/ClaudeProductivity/app/drain_inbox.py
```

Can also be called from `main.py` during the 5 AM briefing run (after auto-capture).

## Acceptance Criteria

- Script reads unread messages from shared mailbox
- Parses Oscar's note from forwarded email body
- Writes structured entries to `crm/ai_inbox_queue.md`
- Marks processed messages as read
- Org matching works for known contacts
- Unknown senders get Org: "Unknown"
- Idempotent: re-running doesn't create duplicates (read messages are skipped)
