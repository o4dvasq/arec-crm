# Task 12 — Delete Merseyside Pension Fund Contact/Person (Keep as Org)

## Enhancement
Remove the Primary Contact / Person record for Merseyside Pension Fund, but keep the organization entry in prospects.md.

## This is a data-only change, no code modifications.

## Steps

### 1. Find the prospect in `crm/prospects.md`
Look for `### Merseyside Pension Fund` (or similar). Clear the `Primary Contact` field:

Before:
```markdown
### Merseyside Pension Fund
- **Stage:** ...
- **Primary Contact:** [some name]
```

After:
```markdown
### Merseyside Pension Fund
- **Stage:** ...
- **Primary Contact:**
```

### 2. Check `crm/contacts_index.md`
If there's a line mapping Merseyside Pension Fund to a person slug, remove it:

```markdown
Merseyside Pension Fund: person-slug
```
→ Remove this line entirely.

### 3. Check `memory/people/` directory
If there's a person file tied only to Merseyside Pension Fund (e.g., `memory/people/some-contact.md`), delete it. If the person is referenced by other orgs, leave the file but remove the Merseyside reference.

### 4. Keep the org record
`crm/organizations.md` — do NOT delete the Merseyside Pension Fund entry. It stays as an org.

## Testing
1. Open Pipeline — Merseyside Pension Fund should still appear as a prospect
2. Primary Contact column should be empty for this org
3. Open Org Detail page — Contacts section should be empty or not list the removed person
