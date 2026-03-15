#!/usr/bin/env python3
"""
One-time: bootstrap contacts_index.md from High/Med urgency prospects
that have matching person files in contacts/.

Run from the app/ directory:
    python3 scripts/bootstrap_contacts_index.py
"""
import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sources.crm_reader import load_prospects, add_contact_to_index

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PEOPLE_DIR = os.path.join(_PROJECT_ROOT, 'contacts')


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[''`]", '', slug)
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


def main():
    prospects = load_prospects()
    found = 0
    missing = 0

    for p in prospects:
        if p.get('Urgency') not in ('High', 'Med'):
            continue
        contact = p.get('Primary Contact', '').strip()
        if not contact:
            continue
        slug = slugify(contact)
        path = os.path.join(PEOPLE_DIR, slug + '.md')
        if os.path.exists(path):
            add_contact_to_index(p['org'], slug)
            found += 1
            print(f"  FOUND: {contact} → {slug}.md → {p['org']}")
        else:
            missing += 1
            print(f"  MISSING: {contact} → {slug}.md (org: {p['org']})")

    print(f"\nDone. Found: {found}, Missing: {missing}")


if __name__ == '__main__':
    main()
