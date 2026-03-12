# SPEC: Merge Organizations

**Project:** arec-crm
**Date:** March 11, 2026
**Status:** Ready for implementation

---

## 1. Objective

Allow merging two organizations into one when duplicates are discovered (e.g., "SMBC" and "Sumitomo Mitsui Banking Corporation" were created as separate orgs). The merge combines all data — prospects, contacts, domains, aliases, notes, briefs, email log entries, interactions, and meeting history — into the surviving org, then fully deletes the losing org. This prevents data fragmentation that occurs when the same real-world entity has multiple CRM records.

---

## 2. Scope

**In scope:**
- "Merge into…" button on the org edit page (`crm_org_edit.html`)
- Org picker modal/dropdown to select the target (surviving) org
- Preview screen showing what will be merged (counts of prospects, contacts, emails, etc.)
- Backend `POST /crm/api/org/merge` endpoint that performs the merge
- `merge_organizations(source: str, target: str)` function in `crm_reader.py`
- Data migration for: prospects, contacts_index, organizations.md fields, briefs.json, prospect_notes.json, prospect_meetings.json, email_log.json, interactions.md, and people files (org references)
- The losing org's name is automatically added as an alias on the surviving org
- Full deletion of the losing org after merge

**Out of scope:**
- Merging people/contacts (only org-level merge; contacts are re-linked, not combined)
- Undo/rollback of a merge (destructive operation; user confirms before proceeding)
- Bulk merge (one merge at a time)
- Automatic duplicate detection or merge suggestions
- Merge from the org list page (org detail only, per design decision)

---

## 3. Business Rules

1. **User picks source and target.** The user is on the source (losing) org's page and clicks "Merge into…", then selects the target (surviving) org from a searchable dropdown. The source org is absorbed into the target and then deleted.
2. **Field combination strategy (auto-combine):**
   - **Type:** Keep target's value. If target has no type, use source's.
   - **Domain:** Union of both domains. If both have domains, store comma-separated or pick the target's (domains are single-valued today, so store target's and add source's as a secondary note if different).
   - **Aliases:** Union of both alias lists. Additionally, add the source org's canonical name as a new alias on the target.
   - **Notes:** Concatenate. Target notes first, then a separator line `---`, then source notes (if any). Do not duplicate identical notes.
   - **Stage:** Keep target's value.
3. **Prospect migration:** All prospects under the source org in `prospects.md` are re-parented to the target org. The `### OrgName` heading for each prospect changes from source to target. If a prospect with the same offering already exists under the target, append source's notes and keep the higher-stage prospect's field values.
4. **Contact migration:** All contacts linked to the source org in `contacts_index.md` are moved under the target org. People files (`memory/people/*.md`) that reference the source org name in their Company field are updated to reference the target org name.
5. **Email log migration:** All entries in `email_log.json` where `orgMatch` equals the source org name are updated to reference the target org name.
6. **Interaction migration:** Interactions in `interactions.md` do not have a direct org field — they are keyed by Contact name. After contacts are re-linked to the target org, interactions follow naturally. No direct migration needed for `interactions.md`.
7. **Brief migration:** Saved briefs in `briefs.json` are keyed as `OrgName::FundName`. All entries where the org portion matches the source org name are re-keyed to the target org name (e.g., `"SMBC::AREC Debt Fund II"` becomes `"Sumitomo Mitsui Banking Corporation::AREC Debt Fund II"`).
8. **Prospect notes and meetings:** Entries in `prospect_notes.json` and `prospect_meetings.json` keyed by source org name are re-keyed to the target org name.
9. **After all data is migrated, the source org is fully deleted** from `organizations.md` using the existing `delete_organization()` function.
10. **After merge completes, redirect the user to the target org's edit page.**

---

## 4. Data Model / Schema Changes

No new fields or files. The merge operates on existing data structures:

| Data Store | Key/Identifier | Migration Action |
|------------|----------------|------------------|
| `crm/organizations.md` | `## OrgName` heading | Combine fields into target, delete source section |
| `crm/prospects.md` | `### OrgName` under offering headings | Change heading from source to target |
| `crm/contacts_index.md` | Org name → slug list | Move source's slugs under target's section |
| `memory/people/*.md` | `Company:` field | Replace source org name with target org name |
| `crm/briefs.json` | `OrgName::FundName` composite key | Re-key source org entries to target org name |
| `crm/prospect_notes.json` | Org name in key | Re-key source entries to target |
| `crm/prospect_meetings.json` | Org name in key | Re-key source entries to target |
| `crm/email_log.json` | `orgMatch` field in entries | Update from source to target |
| `crm/interactions.md` | Contact-based (no direct org field) | No direct migration needed; follows contact re-linking |

---

## 5. UI / Interface

### Merge Button on Org Edit Page

Add a "Merge into…" button in the page header area, next to the org name. Style it as a secondary/destructive action (muted color, not primary blue).

```
[← Back to Organizations]

  Sumitomo Mitsui Banking Corporation          [Merge into…]
```

### Merge Flow (3 steps)

**Step 1 — Select Target Org:**
Modal overlay with a searchable dropdown listing all other organizations (exclude the current/source org). The dropdown should use the existing org list from `/crm/api/orgs`. Placeholder text: "Search for the surviving org…"

**Step 2 — Preview:**
After selecting the target, show a confirmation panel with:

```
Merge "SMBC" → "Sumitomo Mitsui Banking Corporation"

This will move:
  • 2 prospects
  • 3 contacts
  • 12 email log entries
  • 1 meeting record

"SMBC" will be added as an alias on the target org.
"SMBC" will be permanently deleted after merge.

[Cancel]  [Confirm Merge]
```

Counts are fetched from a new `GET /crm/api/org/<name>/merge-preview?target=<target>` endpoint.

**Step 3 — Execute & Redirect:**
On confirm, `POST /crm/api/org/merge` fires. On success, redirect to the target org's edit page. Show a transient success flash: "Merged successfully. SMBC → Sumitomo Mitsui Banking Corporation."

### States

- **Loading:** Spinner while merge executes (merges touch multiple files, may take 1-2s)
- **Error:** If merge fails, show error in modal. Do not close the modal. Do not redirect.
- **Success:** Redirect to target org page with flash message.

---

## 6. Integration Points

### Reads from:
- `crm/organizations.md` — source and target org data
- `crm/prospects.md` — prospects for source org
- `crm/contacts_index.md` — contacts for source org
- `memory/people/*.md` — people with Company matching source org
- `crm/email_log.json` — emails attributed to source org
- `crm/interactions.md` — interactions for source org
- `crm/briefs.json` — briefs for source org
- `crm/prospect_notes.json` — notes keyed to source org
- `crm/prospect_meetings.json` — meetings keyed to source org

### Writes to:
- All of the above (re-keyed/updated to target org, source entries removed)

### Calls:
- `write_organization()` — to update target org with merged fields
- `delete_organization()` — to remove source org
- `write_prospect()` — to re-parent prospects (or direct markdown manipulation)
- Existing contact/people helpers to update org references

---

## 7. Constraints

1. **All file operations in `crm_reader.py`.** The merge function must live in `crm_reader.py`, not in the blueprint. The blueprint endpoint calls the reader function.
2. **Merge is atomic-ish.** Since this is file-based, true atomicity isn't possible. But the function should complete all migrations before deleting the source org. If any step fails, stop and return an error — do not delete the source org on partial failure.
3. **No concurrent merge protection.** The system is single-user. No locking needed.
4. **Merge preview is read-only.** The preview endpoint only counts — it does not modify anything.
5. **The source org's name becomes an alias on the target.** This ensures that any future references to the old name (in emails, meeting notes) still resolve correctly via alias matching (requires the Org Aliases feature from SPEC_org-aliases.md).

---

## 8. Acceptance Criteria

1. "Merge into…" button appears on every org edit page.
2. Clicking the button opens a modal with a searchable org picker (excluding the current org).
3. After selecting a target, a preview screen shows counts of data that will be migrated.
4. Confirming the merge migrates all prospects from source to target in `prospects.md`.
5. Confirming the merge moves all contacts from source to target in `contacts_index.md`.
6. People files referencing the source org in their Company field are updated to reference the target.
7. Email log entries (`orgMatch` field) for the source org are re-attributed to the target.
8. The source org's briefs are re-keyed in `briefs.json` (`OrgName::FundName` key format).
9. Prospect notes and meetings keyed to the source org are re-keyed to the target.
10. The source org's canonical name is added as an alias on the target org.
11. Target org's fields are combined per the combination strategy (union aliases, concatenate notes, etc.).
12. The source org is fully deleted from `organizations.md` after successful migration.
13. User is redirected to the target org's edit page after merge.
14. A flash message confirms the merge.
15. If merge fails partway, the source org is NOT deleted and an error is shown.
16. The merge preview endpoint returns accurate counts without modifying any data.
17. Feedback loop prompt has been run.

---

## 9. Files Likely Touched

| File | Reason |
|------|--------|
| `app/sources/crm_reader.py` | Add `merge_organizations(source, target)` function and `get_merge_preview(source, target)` helper. Add helpers to re-key entries in JSON stores and re-parent prospects. |
| `app/delivery/crm_blueprint.py` | Add `POST /crm/api/org/merge` endpoint and `GET /crm/api/org/<name>/merge-preview` endpoint. |
| `app/templates/crm_org_edit.html` | Add "Merge into…" button, merge modal with org picker, preview panel, and confirmation flow. |
| `crm/organizations.md` | Modified at runtime: target org updated with merged fields, source org deleted. |
| `crm/prospects.md` | Modified at runtime: source org's prospects re-parented to target. |
| `crm/contacts_index.md` | Modified at runtime: source org's contacts moved to target. |
| `memory/people/*.md` | Modified at runtime: Company field updated from source to target. |
| `crm/email_log.json` | Modified at runtime: `orgMatch` entries updated. |
| `crm/interactions.md` | No direct migration needed — interactions are contact-based, not org-keyed. |
| `crm/briefs.json` | Modified at runtime: source org's brief deleted. |
| `crm/prospect_notes.json` | Modified at runtime: re-keyed from source to target. |
| `crm/prospect_meetings.json` | Modified at runtime: re-keyed from source to target. |

---

## 10. Dependency

This spec depends on **SPEC: Organization Aliases (AKA)** — specifically the `Aliases` field being editable and the alias-matching infrastructure. The merge operation adds the source org's name as an alias on the target, which requires the aliases feature to be functional. Implement aliases first.
