# CC-07a: AI Email Inbox — Deltas

**Applies to:** CC-07 (`drain_inbox.py`)
**Source:** AI-EMAIL-INBOX-SPEC.md (prior conversation)
**Depends on:** CC-07 already built, CC-04 (Graph auth)

---

## What CC-07 Already Built

- `drain_inbox.py` polling shared mailbox via Graph API
- `parse_forwarded_email()` separating Oscar's note from original
- Writes structured entries to `crm/ai_inbox_queue.md`
- Marks processed messages as read
- Org matching against CRM contacts

## What's Missing — 3 Deltas

---

### Delta 1: Move Processed Emails to `Processed` Subfolder

CC-07 marks messages as read but does NOT move them out of Inbox.
The prior spec requires moving each processed email to a `Processed`
mail folder in the shared mailbox after reading.

**Add to `sources/ms_graph.py`:**

```python
def move_message(mailbox: str, message_id: str,
                 destination_folder: str = 'Processed') -> None:
    """
    POST /users/{mailbox}/messages/{message_id}/move
    Body: {"destinationId": <folder_id>}

    Creates the destination folder if it doesn't exist:
    POST /users/{mailbox}/mailFolders
    Body: {"displayName": "Processed"}
    """
```

Implementation notes:
- Graph API `move` requires folder ID, not display name
- First call: `GET /users/{mailbox}/mailFolders?$filter=displayName eq 'Processed'`
- If empty result: `POST /users/{mailbox}/mailFolders` to create it
- Cache the folder ID after first lookup (module-level variable, lives for process duration)
- Then: `POST /users/{mailbox}/messages/{message_id}/move` with `{"destinationId": folder_id}`

**Update `drain_inbox.py` — add move after mark-as-read:**

```python
for msg in messages:
    entry = parse_inbox_message(msg)
    # ... existing processing ...
    mark_as_read(token, msg['id'])
    move_message(token, mailbox=inbox_email,
                 message_id=msg['id'],
                 destination_folder='Processed')  # ← NEW
```

---

### Delta 2: Write to `inbox.md` with `[AI Inbox]` Prefix

CC-07 writes ONLY to `crm/ai_inbox_queue.md`. The prior spec requires
drain_inbox.py to write to **`inbox.md`** (not ai_inbox_queue.md) using
the `[AI Inbox]` prefix format. Cowork then reads inbox.md during
`/productivity:update` and triages entries — some become tasks, some
get flagged to `crm/ai_inbox_queue.md`.

**This is a routing change:** drain_inbox.py → inbox.md → Cowork triages → ai_inbox_queue.md

**Replace the current `append_to_queue()` call with `write_to_inbox_md()`:**

Target file: `~/Dropbox/Tech/ClaudeProductivity/inbox.md`

**Entry format for forwarded emails:**

```markdown
## [AI Inbox] 2026-03-02T14:23 — FW: Fund II priorities — Tony

**Intent:** Hey AI, Tony just sent updated priorities. Add tasks to my list
and flag anything relevant to the Merseyside or NPS pipeline.

**Original From:** Tony Avila <tony@avilacapital.com>
**Original Subject:** Fund II priorities

**Original Content:**
Oscar — here are the updated Q1 priorities:
1. Close Merseyside by March 15
2. Get NPS to Verbal by end of March
3. Schedule board prep call week of March 9
```

**Entry format for direct emails (not forwards):**

```markdown
## [AI Inbox] 2026-03-02T16:45 — CRM session notes

**Intent:** Talked to James today. Merseyside wants updated waterfall before
March 15th. Add to Next Action and flag for next CRM session.
```

**Updated `parse_inbox_message()` return dict:**

```python
def parse_inbox_message(message) -> dict:
    """
    Returns:
    {
      'source': 'ai_inbox',
      'received_at': '2026-03-02T14:23:00',
      'subject': 'FW: Fund II priorities — Tony',
      'sender_note': "Hey AI, Tony just sent updated priorities...",
      'original_from': 'Tony Avila <tony@avilacapital.com>',
      'original_subject': 'Fund II priorities',
      'original_body': '...full original email text...',
      'is_forward': True,
      'raw_body': '...complete message body...'
    }
    """
```

**Forward detection patterns** (add Apple Mail if not already present):

- `-------- Forwarded Message --------`
- `-----Original Message-----`
- `From:` at the start of a line after a blank line
- `Begin forwarded message:` (Apple Mail format)

**`write_to_inbox_md()` function:**

```python
INBOX_PATH = os.path.expanduser(
    "~/Dropbox/Tech/ClaudeProductivity/inbox.md")

def write_to_inbox_md(entry: dict) -> None:
    """Append structured [AI Inbox] entry to inbox.md"""
    timestamp = entry['received_at'][:16]  # YYYY-MM-DDTHH:MM
    header = f"## [AI Inbox] {timestamp} — {entry['subject']}"

    lines = [header, ""]
    lines.append(f"**Intent:** {entry['sender_note']}")

    if entry['is_forward']:
        lines.append("")
        lines.append(f"**Original From:** {entry['original_from']}")
        lines.append(f"**Original Subject:** {entry['original_subject']}")
        lines.append("")
        lines.append("**Original Content:**")
        lines.append(entry['original_body'])

    lines.append("")

    with open(INBOX_PATH, 'a') as f:
        f.write('\n'.join(lines) + '\n')
```

**Remove** the direct write to `crm/ai_inbox_queue.md` from drain_inbox.py.
That file is now populated by Cowork during `/productivity:update`, not by
the Python script.

---

### Delta 3: Legacy `--folder` Flag for Migration

Add a `--folder` CLI argument so Oscar can drain any remaining items
from the old `#Productivity` Outlook folder before retiring it.

```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--folder', default=None,
                    help='Legacy: drain from a specific mail folder '
                         'instead of the shared mailbox')
args = parser.parse_args()

if args.folder:
    # Use Oscar's personal mailbox + specified folder
    messages = graph.get_folder_messages(folder=args.folder, ...)
else:
    # Default: shared mailbox
    messages = graph.get_shared_mailbox_messages(mailbox=inbox_email, ...)
```

One-time usage:
```bash
python3 ~/Dropbox/Tech/ClaudeProductivity/app/drain_inbox.py --folder="#Productivity"
```

After migration confirmed working, the `--folder` flag can be ignored
but leave it in place — zero maintenance cost.

---

## Updated .env Variable

```
AI_INBOX_EMAIL=ai@avilacapital.com
```

Remove (if present from legacy):
```
# PRODUCTIVITY_FOLDER=#Productivity  ← delete this line
```

---

## Acceptance Criteria (delta-only)

1. Processed emails are moved to `Processed` subfolder (not just marked read)
2. `Processed` folder auto-created on first run if it doesn't exist
3. `inbox.md` entries use `[AI Inbox]` prefix with structured fields
4. Forward vs. direct email format is correct (Intent-only for direct, full structure for forwards)
5. `crm/ai_inbox_queue.md` is NOT written by drain_inbox.py (Cowork owns that file)
6. `--folder="#Productivity"` flag works for legacy migration drain
7. No regressions on mark-as-read or org matching
