#!/usr/bin/env python3
"""
One-time migration: convert Urgency (High/Med/Low) → Urgent (Yes/blank).

  High     → Urgent: Yes
  Med/Low/blank → Urgent: (blank)

Run from the repo root:
  python app/scripts/migrate_urgency.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.sources.crm_reader import load_prospects, write_prospect


def migrate():
    prospects = load_prospects()  # load all offerings
    marked = 0
    cleared = 0

    for p in prospects:
        old_urgency = p.get('Urgency', '').strip()

        if old_urgency.lower() == 'high':
            p['Urgent'] = 'Yes'
            marked += 1
        else:
            p['Urgent'] = ''
            cleared += 1

        # Remove legacy field
        p.pop('Urgency', None)

        write_prospect(p['org'], p['offering'], p)

    print(f"Done. Marked urgent: {marked}  Cleared: {cleared}")


if __name__ == '__main__':
    migrate()
