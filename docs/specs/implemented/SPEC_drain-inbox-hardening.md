SPEC: Drain Inbox Hardening | Project: arec-crm | Date: 2026-03-19 | Status: Ready for implementation

---

## 1. Objective

Harden `drain_inbox.py` so it runs reliably as an unattended background process (via launchd), produces machine-readable output for CoWork to consume, and doesn't accumulate duplicate entries when the mark-as-read step fails.

---

## 2. Scope

Two changes to `app/drain_inbox.py`:

1. **Write `crm/drain_last_run.json`** at the end of every run (success or failure), so CoWork can check drain freshness without parsing log files.
2. **Fix the 403 on mark-as-read / move-to-Processed** by using the correct Graph API endpoint for shared mailbox write operations.

One new file already created by CoWork:
- `scripts/run_drain_inbox.sh` — wrapper with logging and metadata write (belt-and-suspenders; also writes metadata via shell, but Python-level write in drain_inbox.py is cleaner)
- `scripts/com.arec.drain-inbox.plist` — launchd agent (installed manually)

---

## 3. Business Rules

- `drain_last_run.json` must be written even when `processed == 0` (quiet inbox).
- `drain_last_run.json` must be written even when drain fails (exit_code captures the failure).
- Duplicate entries in `inbox.md` must be prevented when mark-as-read fails. Use a local dedup log (`crm/drain_seen_ids.json`) keyed by `message.id` to track already-processed messages across runs.
- If a message is in `drain_seen_ids.json`, skip it even if it's still unread in the mailbox (mark-as-read may have silently failed).
- `drain_seen_ids.json` entries older than 30 days can be pruned automatically.

---

## 4. Data Model / Schema Changes

**New file: `crm/drain_last_run.json`**
```json
{
  "last_run": "2026-03-19T14:30:00Z",
  "messages_processed": 3,
  "messages_skipped_dedup": 1,
  "exit_code": 0,
  "error": null
}
```

**New file: `crm/drain_seen_ids.json`**
```json
{
  "seen": {
    "AAMkAGVi...messageId1": "2026-03-19T14:30:00Z",
    "AAMkAGVi...messageId2": "2026-03-18T07:00:00Z"
  }
}
```
Both files are gitignored (add to `.gitignore`).

---

## 5. UI / Interface

None. This is a backend-only change. CoWork reads `drain_last_run.json` in Step 1 of the crm-update skill (already updated in skill docs).

---

## 6. Integration Points

**Graph API — mark-as-read on shared mailbox:**

The current call uses the standard `/me/messages/{id}` endpoint which does not work for shared mailboxes. The correct endpoint for shared mailbox write operations is:

```
PATCH https://graph.microsoft.com/v1.0/users/crm@avilacapllc.com/messages/{id}
Body: {"isRead": true}
```

The move-to-folder call similarly needs:
```
POST https://graph.microsoft.com/v1.0/users/crm@avilacapllc.com/messages/{id}/move
Body: {"destinationId": "Processed"}
```

Check `app/sources/ms_graph.py` — the `mark_as_read()` and `move_message()` functions likely construct URLs using `/me/` or the delegated token's mailbox rather than the shared mailbox address. Fix them to accept a `mailbox` parameter (they already do based on the drain_inbox.py call signature), and verify the URL construction uses `users/{mailbox}` not `me`.

If the 403 persists after the URL fix, it is a Graph API permission scope issue. The app registration needs `Mail.ReadWrite.Shared` delegated permission in addition to `Mail.Read.Shared`. Check `app/auth/graph_auth.py` for the current scope list and add `https://graph.microsoft.com/Mail.ReadWrite.Shared` if missing.

---

## 7. Constraints

- Do not change the `inbox.md` write format — CoWork and the skill parse this format.
- `drain_seen_ids.json` must be gitignored. It is machine-local state.
- The wrapper script `scripts/run_drain_inbox.sh` also writes `drain_last_run.json` via Python subprocess. The Python-level write in `drain_inbox.py` should take precedence (it runs first); the shell-level write in the wrapper is a fallback if the Python process crashes before completing.
- Keep both `requirements.txt` files in sync if any new dependencies are added (none expected for this spec).

---

## 8. Acceptance Criteria

- [ ] `crm/drain_last_run.json` exists and is updated after every `drain_inbox.py` run.
- [ ] Running drain twice in a row does not create duplicate entries in `inbox.md`.
- [ ] `drain_seen_ids.json` correctly skips messages already written to `inbox.md`.
- [ ] Mark-as-read no longer returns 403 on `crm@avilacapllc.com` messages (or error is clearly surfaced with scope diagnosis).
- [ ] `scripts/run_drain_inbox.sh` runs cleanly from terminal: `cd ~/Dropbox/projects/arec-crm && ./scripts/run_drain_inbox.sh`
- [ ] Feedback loop prompt has been run.

---

## 9. Files Likely Touched

| File | Change |
|------|--------|
| `app/drain_inbox.py` | Add `drain_last_run.json` write + `drain_seen_ids.json` dedup |
| `app/sources/ms_graph.py` | Fix `mark_as_read()` and `move_message()` URL construction for shared mailbox |
| `app/auth/graph_auth.py` | Add `Mail.ReadWrite.Shared` scope if missing |
| `.gitignore` | Add `crm/drain_last_run.json` and `crm/drain_seen_ids.json` |
| `scripts/run_drain_inbox.sh` | Already created by CoWork — no changes needed |
| `scripts/com.arec.drain-inbox.plist` | Already created by CoWork — install manually |
