# Task 09 — Show Primary Contact in Pipeline List

## Enhancement
Display the Primary Contact name below the org name in each pipeline row, in smaller/lighter text.

## Files to Modify
- `app/templates/crm_pipeline.html`

## Current Behavior
The `org` column in the pipeline table only shows the organization name. Primary Contact is a separate column that users may or may not have visible.

## Required Changes

### crm_pipeline.html — `buildCellContent()` function (~line 867)

In the `org` column rendering case, append the Primary Contact below the org name:

```javascript
if (col.key === 'org') {
  const link = document.createElement('a');
  link.href = '#';
  link.textContent = p.org;
  link.className = 'org-link';
  link.addEventListener('click', e => { e.preventDefault(); openOrgModal(p); });
  cell.appendChild(link);
  // NEW: Show primary contact in smaller, lighter text below org name
  if (p.primary_contact) {
    const contactLine = document.createElement('div');
    contactLine.textContent = p.primary_contact;
    contactLine.style.cssText = 'font-size:11px; color:#94a3b8; margin-top:2px; font-weight:400;';
    cell.appendChild(contactLine);
  }
  return cell;
}
```

The `p.primary_contact` field is already present in the prospect data returned by the API (mapped from `Primary Contact`).

## Testing
1. Open Pipeline page
2. Verify each prospect row shows the Primary Contact name in small grey text beneath the org name
3. Prospects without a Primary Contact should show org name only (no empty line)
4. Verify the text is noticeably smaller and lighter than the org name
