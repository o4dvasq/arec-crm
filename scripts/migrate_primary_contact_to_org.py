#!/usr/bin/env python3
"""
migrate_primary_contact_to_org.py

Promote prospect-level "Primary Contact" data to org-level contact files.

Steps:
  1. Scan all prospect records for "Primary Contact" field.
  2. For each org, resolve any conflicts (highest pipeline stage wins).
  3. Write "Primary: true" to the winning contact file.
  4. Strip "Primary Contact:" lines from crm/prospects.md.

Safe to run multiple times (idempotent).
"""

import os
import sys
import re

# Ensure project root is on path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
APP_DIR = os.path.join(PROJECT_ROOT, 'app')
sys.path.insert(0, APP_DIR)

from sources.crm_reader import (
    load_prospects, get_contacts_for_org,
    set_primary_contact,
)

CRM_ROOT = os.path.join(PROJECT_ROOT, 'crm')
PROSPECTS_PATH = os.path.join(CRM_ROOT, 'prospects.md')


def stage_number(stage_str: str) -> int:
    """Extract the numeric prefix from a stage string like '5. Active Prospect'."""
    m = re.match(r'^(\d+)', str(stage_str).strip())
    return int(m.group(1)) if m else 0


def main():
    prospects = load_prospects()

    # Group by org: collect (stage_num, primary_contact_name) pairs
    org_data: dict[str, list[tuple[int, str]]] = {}
    for p in prospects:
        org = p.get('org', '').strip()
        pc = p.get('Primary Contact', '').strip()
        if not org or not pc:
            continue
        # Take first name if semicolon-separated
        primary_name = pc.split(';')[0].strip()
        if not primary_name:
            continue
        stage = stage_number(p.get('Stage', '0'))
        org_data.setdefault(org, []).append((stage, primary_name))

    orgs_updated = 0
    conflicts_resolved = 0
    contacts_not_found = []
    orgs_no_primary = []

    for org, entries in sorted(org_data.items()):
        # Check if all entries agree on the same name
        names = [e[1] for e in entries]
        unique_names = list(dict.fromkeys(names))  # preserves order, deduplicates

        if len(unique_names) == 1:
            chosen_name = unique_names[0]
        else:
            # Conflict: pick by highest stage number
            conflicts_resolved += 1
            best_stage, best_name = max(entries, key=lambda x: x[0])
            # Find any other names for logging
            others = [(s, n) for s, n in entries if n != best_name]
            other_desc = ', '.join(f"{n} (Stage {s})" for s, n in others)
            print(f"  CONFLICT [{org}]: {best_name} (Stage {best_stage}) vs {other_desc} → chose {best_name}")
            chosen_name = best_name

        # Verify the contact exists in this org's contact list
        contacts = get_contacts_for_org(org)
        contact_names = [c.get('name', '').lower() for c in contacts]
        if chosen_name.lower() not in contact_names:
            print(f"  WARN [{org}]: contact '{chosen_name}' not found in org contacts — skipping")
            contacts_not_found.append((org, chosen_name))
            continue

        ok = set_primary_contact(org, chosen_name)
        if ok:
            print(f"  [{org}] → set primary: {chosen_name}")
            orgs_updated += 1
        else:
            print(f"  WARN [{org}]: set_primary_contact returned False for '{chosen_name}'")
            contacts_not_found.append((org, chosen_name))

    # Orgs with no primary contact data in prospects
    all_orgs_with_contacts = set()
    for p in prospects:
        if p.get('org') and get_contacts_for_org(p['org']):
            all_orgs_with_contacts.add(p['org'])
    orgs_no_primary = sorted(all_orgs_with_contacts - set(org_data.keys()))

    # Strip "Primary Contact:" lines from prospects.md
    with open(PROSPECTS_PATH, 'r', encoding='utf-8') as f:
        text = f.read()

    cleaned = re.sub(r'^- \*\*Primary Contact:\*\*.*\n?', '', text, flags=re.MULTILINE)

    if cleaned != text:
        with open(PROSPECTS_PATH, 'w', encoding='utf-8') as f:
            f.write(cleaned)
        removed_count = text.count('- **Primary Contact:**')
        print(f"\n  Removed {removed_count} 'Primary Contact:' line(s) from prospects.md")
    else:
        print("\n  No 'Primary Contact:' lines found in prospects.md (already clean)")

    print("\n=== Migration Summary ===")
    print(f"  Orgs updated:          {orgs_updated}")
    print(f"  Conflicts resolved:    {conflicts_resolved}")
    print(f"  Contacts not found:    {len(contacts_not_found)}")
    for org, name in contacts_not_found:
        print(f"    - [{org}] '{name}'")
    print(f"  Orgs with no primary:  {len(orgs_no_primary)}")
    for org in orgs_no_primary:
        print(f"    - {org}")


if __name__ == '__main__':
    print("Starting primary contact migration...\n")
    main()
    print("\nDone.")
