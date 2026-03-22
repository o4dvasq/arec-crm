# SPEC: Fundraising Allies — Placement Agents & Connectors
**Project:** arec-crm
**Date:** 2026-03-22
**Status:** Ready for implementation

SPEC: Fundraising Allies | Project: arec-crm | Date: 2026-03-22 | Status: Ready for implementation

---

## 1. Objective

Introduce a "Fundraising Ally" concept to the email matching pipeline so that placement agents (South40 Capital, Angeloni & Co, JTP Capital) and individual connectors/introducers (Greg Kostka, Scott Richland, Ira Lubert) are treated as pass-through entities rather than match endpoints. When the poller or deep scan matches an email to a Fundraising Ally, it should look through the remaining participants for a **real prospect org** and attribute the staged item to that prospect instead. Ally-only emails (no other prospect org found) are silently skipped.

This mirrors how AREC treats these partners operationally: they function like extended fundraising team members whose communications matter only insofar as they touch actual prospects.

---

## 2. Scope

**In scope:**
- New org type `Placement Agent` in `config.md` Organization Types
- New `ally` boolean field on organizations in `organizations.md` (applies to Placement Agent and INTRODUCER types)
- A `crm/fundraising_allies.json` config file listing ally orgs and ally individuals with their domains/emails
- Modify `graph_poller.py::match_email_to_org()` to implement pass-through matching when the first match hits an ally
- Same pass-through logic in `deep_scan_team.py::match_calendar_event_to_org()`
- Reclassify three existing orgs: South40 Capital, Angeloni & Co, JRT Partners → type `Placement Agent`
- Fix org name: `JRT Partners` → `JTP Capital` (domain is `@jtpllc.com`)
- Register three individual connectors as allies: Greg Kostka, Scott Richland, Ira Lubert
- Add ally domains to `INTERNAL_DOMAINS` in `email_matching.py` (so ally-to-AREC-only emails are skipped like internal mail)

**Out of scope:**
- Scanning ally mailboxes via Graph (they are external; we have no Graph access to them)
- UI changes to the CRM dashboard (ally orgs can still appear in the org list, just tagged differently)
- Retroactive reprocessing of already-accepted staging queue items
- Changes to brief synthesis or interactions

---

## 3. Business Rules

1. **Ally org definition:** An org is an ally if its type is `Placement Agent` or `INTRODUCER`, or if it appears in `crm/fundraising_allies.json`.
2. **Ally individual definition:** A person is an ally if they appear in the `individuals` section of `fundraising_allies.json` (keyed by email address).
3. **Pass-through matching:** When `match_email_to_org()` resolves to an ally org (via domain or person_email), instead of returning that match, the function continues scanning remaining participants (recipients for outbound, sender + other recipients for inbound) looking for a non-ally CRM org match. If found, it returns that org as the match with an additional field `via_ally: "<ally org name>"`. If no non-ally org is found, it returns `None` (email is skipped).
4. **Match priority after ally detection:** Domain match on a non-ally org takes priority over person_email match on a non-ally org, same as today's tier logic.
5. **Ally domains treated as semi-internal:** Add ally org domains to `email_matching.py`'s `INTERNAL_DOMAINS` set (or a parallel `ALLY_DOMAINS` set) so that when scanning participants, ally emails are skipped the same way AREC team emails are skipped. This prevents ally-to-ally cross-matching.
6. **Staged item attribution:** The `matched_org` field on staged items always contains the real prospect org, never the ally. The new `via_ally` field preserves the attribution chain for audit.
7. **Calendar events:** Same pass-through logic applies in `match_calendar_event_to_org()` — if the first attendee domain match hits an ally, keep scanning other attendees for a real prospect.
8. **No Graph scanning of allies:** Allies are external to AREC. Their mailboxes are never added to `calendar_users.json` or the poller mailbox list.
9. **Ally-only emails are noise:** If ALL external participants on an email are allies (no real prospect found), the email is silently skipped. This is the desired behavior — these are coordination emails between AREC and their agents.

---

## 4. Data Model / Schema Changes

### New file: `crm/fundraising_allies.json`

```json
{
  "version": 1,
  "orgs": [
    {
      "name": "South40 Capital",
      "domain": "south40capital.com",
      "type": "Placement Agent"
    },
    {
      "name": "Angeloni & Co",
      "domain": "angeloniandco.com",
      "type": "Placement Agent"
    },
    {
      "name": "JTP Capital",
      "domain": "jtpllc.com",
      "type": "Placement Agent"
    }
  ],
  "individuals": [
    {
      "name": "Greg Kostka",
      "email": "greg@example.com",
      "org": "Greg Kostka",
      "type": "INTRODUCER",
      "notes": "Hillwood connection"
    },
    {
      "name": "Scott Richland",
      "email": "scott@example.com",
      "org": "Scott Richland",
      "type": "INTRODUCER",
      "notes": ""
    },
    {
      "name": "Ira Lubert",
      "email": "ilubert@belgravialp.com",
      "org": "Belgravia Management",
      "type": "INTRODUCER",
      "notes": "PSERS/SERS connector. Domain belgravialp.com is Belgravia LP — do NOT add to INTERNAL_DOMAINS (Belgravia is a real Stage 7 prospect)"
    }
  ]
}
```

**Important:** Ira Lubert's domain (`belgravialp.com`) overlaps with Belgravia Management, which is a real Stage 7 prospect. His pass-through status must be keyed by **email address** (`ilubert@belgravialp.com`), not by domain. Other Belgravia emails should still match to Belgravia Management normally.

### Changes to `crm/config.md`

Add `Placement Agent` to Organization Types (after `INTRODUCER`):

```
- INTRODUCER
- Placement Agent
```

### Changes to `crm/organizations.md`

Reclassify three orgs:
- `South40 Capital`: Type → `Placement Agent`
- `Angeloni & Co`: Type → `Placement Agent`
- `JRT Partners` → rename to `JTP Capital`, Type → `Placement Agent`

### Changes to staged item schema

Add optional field to staging queue items:
- `via_ally` (string, nullable): Name of the ally org/person through which this email was routed. `null` for direct matches.

---

## 5. UI / Interface

No UI changes required. Ally orgs remain visible in the CRM org list. The `via_ally` field will appear in staging queue items when reviewed via `/crm-update` — the skill can optionally display "via South40 Capital" in the suggested action text, but this is cosmetic and non-blocking.

---

## 6. Integration Points

- **`app/graph_poller.py`** — `match_email_to_org()`: Core change. Must detect ally match, then continue scanning participants.
- **`scripts/deep_scan_team.py`** — `match_calendar_event_to_org()`: Same pass-through logic for calendar attendees.
- **`app/sources/email_matching.py`** — `INTERNAL_DOMAINS` or new `ALLY_DOMAINS`: Add placement agent domains so ally emails are skipped during participant scanning.
- **`app/sources/crm_reader.py`** — New functions: `load_fundraising_allies()`, `is_ally_org(org_name)`, `is_ally_email(email)`. These read from `crm/fundraising_allies.json` and are called by the poller.
- **`app/graph_poller.py`** — `build_staged_item()`: Include `via_ally` field in output dict.
- **`scripts/deep_scan_team.py`** — `build_calendar_staged_item()`: Include `via_ally` field.

---

## 7. Constraints

- **Ira Lubert is email-keyed, not domain-keyed.** His domain `belgravialp.com` belongs to Belgravia Management (Stage 7 — Legal/DD). Only `ilubert@belgravialp.com` triggers ally pass-through. All other `@belgravialp.com` emails match to Belgravia Management normally.
- **Ian Morgan (ian@south40capital.com) is already in AREC Team** in `config.md`. His emails are already filtered as internal. Adding `south40capital.com` to ally domains must not conflict with this — but since internal check runs first, there's no conflict.
- **Ally config must be a flat file** (`crm/fundraising_allies.json`), consistent with the no-database architecture.
- **Individual ally emails need to be populated.** The spec includes placeholder emails for Greg Kostka and Scott Richland (`greg@example.com`, `scott@example.com`). Claude Code should check `crm/people/` files for their actual email addresses before creating the config file. If no email is on file, leave the field blank and add a TODO comment.
- **Backward compatibility:** Existing staging queue items already processed are not affected. The `via_ally` field is nullable and optional.

---

## 8. Acceptance Criteria

- [ ] `crm/fundraising_allies.json` exists with the three placement agent orgs and three individual connectors
- [ ] `config.md` includes `Placement Agent` in Organization Types
- [ ] South40 Capital, Angeloni & Co, JTP Capital (renamed from JRT Partners) are type `Placement Agent` in `organizations.md`
- [ ] `crm_reader.py` exposes `load_fundraising_allies()`, `is_ally_org()`, `is_ally_email()` functions
- [ ] `graph_poller.py::match_email_to_org()` detects ally matches and continues scanning for real prospect orgs
- [ ] `deep_scan_team.py::match_calendar_event_to_org()` has the same pass-through logic
- [ ] Staged items include `via_ally` field when matched through an ally
- [ ] Ally-only emails (no real prospect found after pass-through) return `None` and are skipped
- [ ] Ira Lubert pass-through is email-keyed only — other `@belgravialp.com` addresses still match to Belgravia Management
- [ ] Placement agent domains added to `ALLY_DOMAINS` (or equivalent) in `email_matching.py`
- [ ] All existing tests pass (`python3 -m pytest app/tests/ -v`)
- [ ] New tests: ally pass-through match, ally-only skip, Lubert email-vs-domain distinction
- [ ] Feedback loop prompt has been run

---

## 9. Files Likely Touched

| File | Change |
|------|--------|
| `crm/fundraising_allies.json` | **New file** — ally org and individual config |
| `crm/config.md` | Add `Placement Agent` to Organization Types |
| `crm/organizations.md` | Reclassify South40, Angeloni, JTP; rename JRT → JTP Capital |
| `app/sources/crm_reader.py` | New functions: `load_fundraising_allies()`, `is_ally_org()`, `is_ally_email()` |
| `app/sources/email_matching.py` | Add `ALLY_DOMAINS` set; update `_is_internal()` or add `_is_ally()` helper |
| `app/graph_poller.py` | Modify `match_email_to_org()` for pass-through; add `via_ally` to `build_staged_item()` |
| `scripts/deep_scan_team.py` | Modify `match_calendar_event_to_org()` for pass-through; add `via_ally` to `build_calendar_staged_item()` |
| `app/tests/test_email_matching.py` | New test cases for ally pass-through, ally-only skip, Lubert edge case |
