#!/usr/bin/env python3
"""
Batch script: auto-fill Primary Contact on all prospects that have contacts
but no Primary Contact set.

Usage:
    python3 scripts/batch_primary_contact.py [--dry-run]

Heuristic priority:
  1. Single contact → that person (no ambiguity)
  2. Multiple contacts + interactions → contact mentioned most recently
  3. Multiple contacts, no distinguishing signal → first in contacts index
     (flagged for manual review)

Reports summary at end. Idempotent — skips prospects that already have a value.
"""

import sys
import os

# Make app/ importable when running from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from sources.crm_reader import (
    load_prospects,
    get_contacts_for_org,
    update_prospect_field,
    load_interactions,
)

DRY_RUN = '--dry-run' in sys.argv


def pick_primary_contact(org: str, contacts: list[dict]) -> tuple[str, str]:
    """
    Return (contact_name, heuristic_label) for the best primary contact.
    heuristic_label is one of: 'single', 'interaction', 'first-in-index', 'unknown'
    """
    if len(contacts) == 1:
        return contacts[0]['name'], 'single'

    # Multiple contacts — use most recent interaction mentioning a contact name
    interactions = load_interactions(org=org)
    # interactions are returned newest-first from load_interactions (if sorted),
    # but we'll sort by date descending to be safe
    interactions_sorted = sorted(interactions, key=lambda x: x.get('date', ''), reverse=True)

    contact_names_lower = {c['name'].lower(): c['name'] for c in contacts}
    for ix in interactions_sorted:
        contact_field = ix.get('Contact', '').strip()
        if contact_field.lower() in contact_names_lower:
            return contact_names_lower[contact_field.lower()], 'interaction'

    # No signal — fall back to first in index (contacts list order = index order)
    return contacts[0]['name'], 'first-in-index'


def main():
    prospects = load_prospects()

    total = 0
    skipped_has_primary = 0
    skipped_no_contacts = 0
    updated_single = 0
    updated_interaction = 0
    updated_first = 0
    flagged = 0

    for p in prospects:
        org = p['org']
        offering = p['offering']
        existing_primary = p.get('Primary Contact', '').strip()

        if existing_primary:
            skipped_has_primary += 1
            continue

        contacts = get_contacts_for_org(org)
        if not contacts:
            skipped_no_contacts += 1
            continue

        total += 1
        name, heuristic = pick_primary_contact(org, contacts)

        tag = ''
        if heuristic == 'single':
            updated_single += 1
        elif heuristic == 'interaction':
            updated_interaction += 1
        else:
            updated_first += 1
            flagged += 1
            tag = ' [REVIEW]'

        label = f"  {org} / {offering} → {name}  [{heuristic}]{tag}"
        if DRY_RUN:
            print(f"[DRY RUN] {label}")
        else:
            update_prospect_field(org, offering, 'Primary Contact', name)
            print(label)

    print()
    print("=" * 60)
    print(f"Prospects updated:          {total}")
    print(f"  Single-contact (auto):    {updated_single}")
    print(f"  Interaction heuristic:    {updated_interaction}")
    print(f"  First-in-index (review):  {updated_first}")
    print(f"Already had Primary Contact: {skipped_has_primary}")
    print(f"No contacts found:           {skipped_no_contacts}")
    if flagged:
        print(f"\n{flagged} prospect(s) flagged [REVIEW] — verify manually.")
    if DRY_RUN:
        print("\n(Dry run — no changes written)")


if __name__ == '__main__':
    main()
