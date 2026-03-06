# CC-03: Org Detail Page (Phase 4)

**Target:** `~/Dropbox/Tech/ClaudeProductivity/app/templates/crm_org_detail.html` + API routes
**Depends on:** CC-02 (Flask app running)
**Blocks:** Nothing

---

## Purpose

Detail page for a single organization at `/crm/org/<org_name>`. Shows org profile, contacts, and prospect records across all offerings. All fields inline-editable.

## Route

```
GET /crm/org/<path:name>       → Org detail page
```

URL-encode org names with special characters. The page loads data via JS on mount from API endpoints.

## API Routes (add to CRM Blueprint)

```
GET   /crm/api/org/<path:name>          → Org profile + contacts + prospects
PATCH /crm/api/org/<path:name>          → Update org fields (type, notes)
POST  /crm/api/contact                  → Create new contact
PATCH /crm/api/contact/<org>/<name>     → Update contact fields
POST  /crm/api/prospect                 → Add prospect to an offering
```

## Page Layout — Three Sections

### Section 1: Org Profile

Display from `organizations.md`:
- **Name** (read-only heading)
- **Type** (inline dropdown: INSTITUTIONAL, HNWI / FO, BUILDER, INTRODUCER)
- **Notes** (inline textarea)

PATCH body:
```json
{"type": "INSTITUTIONAL", "notes": "UK-based pension fund."}
```

### Section 2: Contacts

Load via `contacts_index.md` → resolve each slug from `memory/people/<slug>.md`.

Display per contact: Name, Title/Role, Email, Phone.
- Title, Email, Phone are inline-editable
- "Add Contact" inline form at bottom (Name required, rest optional)

**Add Contact flow:**
1. `POST /crm/api/contact` with `{name, org, email, role, type}`
2. Backend calls `crm_reader.create_person_file()` → creates `memory/people/<slug>.md`
3. Backend updates `contacts_index.md` to add slug under org heading

**Contact file format** (memory/people/<slug>.md):
```markdown
# Firstname Lastname

## Overview
- **Organization:** Org Name
- **Role:** Title
- **Email:** email@example.com
- **Phone:**
- **Type:** investor | internal | advisor
```

### Section 3: Prospects Across Offerings

Load via `crm_reader.get_prospects_for_org(org_name)`. Shows all prospect records this org has across offerings.

Each prospect card shows all fields with same inline editing as pipeline table (same PATCH endpoint, same editable fields whitelist).

"Add to Offering" form:
- Dropdown of offerings from `offerings.md`
- Only shows offerings where this org doesn't already have a prospect
- On submit: `POST /crm/api/prospect` with `{org, offering, stage: "1. Prospect", target: "$0"}`

No org creation from this page (orgs are created during import or manually in organizations.md).

Delete is disabled (deferred).

## Acceptance Criteria

- `/crm/org/Merseyside%20Pension%20Fund` loads with correct data
- Type dropdown saves to organizations.md
- Contact list shows resolved people from memory/people/
- "Add Contact" creates a new file in memory/people/ and updates contacts_index.md
- Prospect inline editing works same as pipeline table
- "Add to Offering" creates new prospect record
- Back link to `/crm` pipeline
