SPEC: Shared Inbox Priority Elevation & Multi-User Support
Project: arec-crm
Date: 2026-03-16
Status: Ready for implementation

---

## 1. Objective

Upgrade the CRM shared mailbox intake (`crm@avilacapllc.com`) to support priority elevation, multi-user attribution, and unified queue routing. Emails forwarded to the shared inbox should be treated as high-priority items in the CRM update workflow, carry metadata about who forwarded them and why, and flow through the same queue (`crm/ai_inbox_queue.md`) that the CRM update workflow already processes — eliminating `inbox.md` as a separate intake point for shared mailbox items.

This also lays the groundwork for teammate onboarding: any AREC team member can forward an email to `crm@avilacapllc.com` with a note, and it enters the CRM pipeline with proper attribution.

## 2. Scope

### In scope

- Modify `drain_inbox.py` to write entries to `crm/ai_inbox_queue.md` instead of `inbox.md`
- Add `Priority: high` tag to all shared mailbox entries (forwarding to `crm@` is an intentional act — it's always elevated)
- Extract and record the forwarder's identity (`ForwardedBy`) from the Graph API envelope sender
- Map forwarder email to AREC team member name using `crm/config.md` → `## AREC Team`
- Preserve Oscar's intent note parsing (the text added above the forward delimiter)
- Preserve the existing drain mechanics: mark as read → move to `Processed` folder
- Update the `/crm-update` skill to process `Priority: high` items first within queue consumption (Step 2)
- Update the `/email-scan` skill's Pass 5 documentation to reference the new queue routing
- Remove shared-mailbox entries from `inbox.md` (it returns to voice-capture-only duty)

### Out of scope

- Web UI for the shared inbox (this remains a backend pipeline)
- Notification system for new shared inbox items (future feature)
- Per-user permissions or access control on the shared mailbox
- Exchange retention policies (admin-level config, not code)
- Processing non-forwarded emails sent directly to `crm@` by external parties (skip these — the mailbox is internal-forward-only)

## 3. Business Rules

### Priority elevation

All entries originating from `crm@avilacapllc.com` receive `Priority: high`. The rationale: forwarding to the CRM inbox is a deliberate action — the user decided this email matters enough to explicitly route it. This is a stronger signal than passive email scanning (Passes 1–4), which catches everything and relies on matching heuristics.

The CRM update workflow processes queue items in this order within Step 2:
1. `Priority: high` + `Status: pending` (shared inbox forwards)
2. `Priority: normal` + `Status: pending` (Overwatch ingress items)

### Multi-user attribution

The forwarder is identified from the Graph API `from.emailAddress` field on the message in the shared mailbox. This is the envelope sender — the person who hit "Forward" — not the original email's From header.

Mapping logic:
1. Extract forwarder email from `message.from.emailAddress.address`
2. Look up against AREC team emails in `crm/config.md` → `## AREC Team`
3. If match found: `ForwardedBy: {FirstName}` (e.g., "Oscar", "Tony")
4. If no match: `ForwardedBy: {email address}` (unknown team member — still process, just can't resolve name)

Internal AREC domains for team member detection (same as existing skip rules):
- avilacapllc.com
- avilacapital.com
- encorefunds.com
- builderadvisorgroup.com
- south40capital.com

### Queue routing (architectural decision)

**Decision: Unify on `crm/ai_inbox_queue.md` as the single intake queue.**

Currently `drain_inbox.py` writes to `inbox.md`, which is a separate file from the CRM update workflow's queue. This creates two intake points that the workflow must check independently. The cleaner architecture routes shared mailbox items into `crm/ai_inbox_queue.md` with `Source: crm-shared-mailbox`, where they join Overwatch-originated items and get processed by the same Step 2 loop in `/crm-update`.

What this changes:
- `drain_inbox.py` → writes to `crm/ai_inbox_queue.md` (was: `inbox.md`)
- `inbox.md` → returns to its original purpose: voice-captured tasks only (Siri Shortcuts)
- `/crm-update` Step 2 → no change needed to the consumption loop; it already reads all `pending` entries from the queue. The new `Priority` field enables ordering.

What this preserves:
- The `Processed` folder drain in the shared mailbox (mark read + move) stays exactly as-is
- The forward delimiter parsing stays exactly as-is
- The `make inbox` CLI entry point stays (just writes to a different target file)

### Handling non-forwarded emails

If someone sends an email directly TO `crm@avilacapllc.com` (not a forward), `parse_forwarded_email()` already handles this — `is_forward` returns `False` and the entire body becomes the `sender_note`. These should still be queued, but with a note that no original email was extracted. The intent note is the full message body.

### Org matching for shared inbox items

Shared inbox items get matched to CRM orgs using the same two-tier matching from `/crm-update` and `/email-scan`:

For forwards:
- Tier 1: Match `original_from` domain against `get_org_domains()`
- Tier 2: Match `original_from` email against `find_person_by_email()`
- If no match: `Org: unknown` — the CRM update workflow's interactive triage handles this

For direct emails (non-forwards):
- Match the sender's domain/email (same tiers)
- These are likely from teammates, so org match may fail — that's fine, the intent note carries the context

## 4. Data Model / Schema Changes

### Queue entry additions

Two new fields added to the `crm/ai_inbox_queue.md` entry schema:

```markdown
### [Subject Line]
- **Source:** crm-shared-mailbox              ← new source value
- **Priority:** high                           ← NEW FIELD (values: high, normal)
- **ForwardedBy:** Oscar                       ← NEW FIELD (team member name or email)
- **From:** [Original sender] <[email]>        ← original email's From (for forwards)
- **To:** [original recipients]
- **Date:** [original email date]
- **Org:** [matched org or "unknown"]
- **Contact:** [matched contact or "(unknown)"]
- **Match:** [domain | person | manual] (confidence: [0.0-1.0])
- **Summary:** [Oscar's intent note — the text added when forwarding]
- **OriginalSubject:** [original email subject] ← NEW FIELD (for forwards only)
- **Status:** pending
- **Queued:** [ISO 8601 timestamp]
- **Processed:**
- **CRM Action:**
```

Key differences from Overwatch-originated entries:
- `Source: crm-shared-mailbox` (vs. `outlook-email`, `outlook-calendar`, etc.)
- `Priority: high` (Overwatch items default to `normal`)
- `ForwardedBy` field populated (Overwatch items don't have this)
- `Summary` contains the forwarder's intent note (not an AI-generated summary)
- `OriginalSubject` preserves the original email's subject line separately from the queue entry header

### Changes to drain_inbox.py output

Current `parse_inbox_message()` return dict gets two new keys:

```python
{
    # ... existing fields ...
    'forwarded_by_name': str,    # AREC team member name (resolved from sender)
    'forwarded_by_email': str,   # forwarder's email address
}
```

### No schema changes to

- `crm/email_log.json` — shared inbox items are NOT logged here (they're queue items, not scan results)
- `crm/organizations.md` — no structural change
- `contacts/*.md` — no structural change
- `crm/interactions.md` — activities created from queue items use existing schema with `Source: queue`

## 5. UI / Interface

No web UI changes. This is a backend pipeline change affecting:

1. **`make inbox` CLI** — same command, different output target
2. **`/crm-update` Step 2** — processes shared inbox items first (high priority), then Overwatch items
3. **`/email-scan` Pass 5** — documentation update only; the pass now routes through the queue instead of inbox.md

### Updated `/crm-update` Step 2 flow

```
Step 2: Process queue (crm/ai_inbox_queue.md)
  │
  ├── Sort pending items: Priority: high first, then by Queued timestamp
  │
  ├── For each high-priority item (Source: crm-shared-mailbox):
  │   ├── Display: "🔴 [ForwardedBy] forwarded: [Subject]"
  │   ├── Show intent note prominently
  │   ├── Match org (or ask Oscar to classify if unknown)
  │   ├── Create activity via append_interaction()
  │   └── Mark done with CRM Action
  │
  ├── For each normal-priority item (Source: outlook-email, etc.):
  │   ├── Display: "○ [Subject]"
  │   ├── (existing processing — unchanged)
  │   └── Mark done/skipped
  │
  └── Report: "Processed N queue items (K high-priority, M normal)"
```

## 6. Integration Points

- **Reads from:** Graph API (`get_shared_mailbox_messages`), `crm/config.md` (team member lookup), `crm/organizations.md` (org matching via `get_org_domains()`), `contacts/*.md` (person matching via `find_person_by_email()`)
- **Writes to:** `crm/ai_inbox_queue.md` (new entries with `Status: pending`)
- **Consumed by:** `/crm-update` skill (Step 2 queue processing)
- **Depends on:** Microsoft Graph token via `get_access_token()`, Mail.Read.Shared permission on Azure app
- **No longer writes to:** `inbox.md` (shared mailbox entries only — voice capture continues writing there via Siri Shortcuts)

### Interaction with existing email-scan

The `/email-scan` skill's 5-pass model references a "CRM shared mailbox pass" as Pass 5. After this spec, Pass 5 is replaced by invoking `drain_inbox.py` (or `make inbox`), which routes items to the unified queue. The email-scan skill documentation should be updated to reflect this:

```
Pass 5 (CRM Shared Mailbox):
  → Calls drain_inbox() which writes to crm/ai_inbox_queue.md
  → Items processed by /crm-update Step 2 (not inline by email-scan)
```

### Interaction with `/crm-update`

The CRM update workflow spec (SPEC_crm-update-workflow.md, now in `implemented/`) already defines Step 2 as "Process Overwatch queue" reading `crm/ai_inbox_queue.md`. Shared inbox items flow through the same step with no structural change — only the addition of priority-based ordering and the display treatment for high-priority items.

## 7. Constraints

- `drain_inbox.py` must remain callable standalone (`make inbox` / `python3 app/drain_inbox.py`) — it should not require the full CRM update workflow to run
- The `Processed` folder in the shared mailbox is the archive mechanism — do not delete processed emails
- Queue entries are append-only from `drain_inbox.py`; status transitions (`done`/`skipped`) happen only in `/crm-update`
- The `Priority` field must default to `normal` for all non-shared-mailbox sources to avoid breaking existing Overwatch queue entries that lack the field
- Team member resolution is best-effort — if the forwarder can't be mapped to a name, the email address is recorded and processing continues
- `inbox.md` must not be broken — existing voice-capture entries stay; only shared mailbox writes are redirected
- The `crm/ai_inbox_queue.md` format is shared with Overwatch — any schema additions (Priority, ForwardedBy, OriginalSubject) must be backward-compatible (fields are simply absent on older entries)

## 8. Acceptance Criteria

- [ ] `drain_inbox.py` writes new entries to `crm/ai_inbox_queue.md` (not `inbox.md`)
- [ ] Each entry includes `Source: crm-shared-mailbox`, `Priority: high`, and `ForwardedBy: {name or email}`
- [ ] Forward delimiter parsing still works for all 4 patterns (Forwarded Message, Original Message, Begin forwarded message, loose From/Date)
- [ ] Non-forwarded emails (sent directly to crm@) are handled gracefully — full body becomes the intent note
- [ ] Forwarder identity is resolved to AREC team member name when possible, falls back to email
- [ ] Org matching uses standard two-tier matching (domain → person) against the original sender
- [ ] Emails are still marked as read and moved to `Processed` folder after queue write
- [ ] `make inbox` still works as a standalone CLI command
- [ ] `/crm-update` Step 2 processes high-priority items before normal-priority items
- [ ] Existing Overwatch queue entries (without Priority field) default to `normal` and process correctly
- [ ] `inbox.md` is no longer written to by `drain_inbox.py`
- [ ] Email-scan skill documentation (Pass 5) is updated to reference queue routing
- [ ] Unit tests for `parse_forwarded_email()` still pass (no behavioral change to parsing)
- [ ] New unit test: `write_to_queue()` produces valid queue entry with all required fields
- [ ] New unit test: forwarder resolution maps known AREC team emails to first names
- [ ] Feedback loop prompt has been run

## 9. Files Likely Touched

| File | Change |
|------|--------|
| `app/drain_inbox.py` | **Modified** — Replace `write_to_inbox_md()` with `write_to_queue_md()`. Add `resolve_forwarder()`. Add org matching via `get_org_domains()` / `find_person_by_email()`. Update `drain_inbox()` main loop. |
| `app/sources/crm_reader.py` | **Read only** — uses existing `get_org_domains()`, `find_person_by_email()`. No changes needed. |
| `crm/ai_inbox_queue.md` | **Written to** — new entries appended by `drain_inbox.py` |
| `crm/config.md` | **Read only** — team member lookup for forwarder resolution. May need `## AREC Team` to include email addresses if not already present. |
| `skills/email-scan.md` | **Modified** — Update Pass 5 documentation to reference queue routing |
| `skills/crm-update/SKILL.md` | **Modified** — Add priority ordering to Step 2, add display treatment for high-priority items |
| `app/tests/test_drain_inbox.py` | **Modified/New** — Update existing tests for queue output format, add forwarder resolution tests |
| `Makefile` | **No change** — `make inbox` target stays the same |
| `inbox.md` | **No change** — existing content stays; `drain_inbox.py` just stops writing here |
| `docs/specs/implemented/SPEC_crm-update-workflow.md` | **Reference only** — the CRM update workflow spec documents the queue consumption loop this spec feeds into |
