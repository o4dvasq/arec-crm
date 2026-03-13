"""
Repair script: Rebuild contact-org links lost during PostgreSQL migration.

The original migrate_to_postgres.py used exact org name matching (ilike) against
contacts_index.md entries. When org names didn't match exactly (e.g., "Future Fund"
vs "Future Fund (Australia)"), contacts were silently skipped.

This script:
1. Parses crm/contacts_index.md for org → [contact-slug] mappings
2. Loads each contact's markdown file from memory/people/*.md
3. Fuzzy-matches org names against the PostgreSQL organizations table
4. Inserts missing contacts and links them to orgs
5. Repairs primary_contact_id on prospects where it's NULL but should be set

Run: python3 scripts/repair_contacts.py [--dry-run]
Requires: DATABASE_URL in app/.env or environment
"""

import os
import re
import sys
from datetime import datetime
from difflib import SequenceMatcher

# Add app/ to path
APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
sys.path.insert(0, APP_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(APP_DIR, '.env'))
load_dotenv(os.path.join(APP_DIR, '.env.azure'))

from models import Organization, Contact, Prospect
from db import init_db, session_scope

PROJECT_ROOT = os.path.dirname(APP_DIR)
CONTACTS_INDEX = os.path.join(PROJECT_ROOT, 'crm', 'contacts_index.md')
PEOPLE_DIR = os.path.join(PROJECT_ROOT, 'memory', 'people')


def parse_contacts_index():
    """Parse crm/contacts_index.md → {org_name: [slug, ...]}"""
    mapping = {}
    with open(CONTACTS_INDEX, 'r') as f:
        for line in f:
            line = line.strip()
            if not line.startswith('- ') or ':' not in line:
                continue
            org_part, slugs_part = line[2:].split(':', 1)
            org_name = org_part.strip()
            slugs = [s.strip() for s in slugs_part.split(',') if s.strip() and s.strip() != 'tbd']
            if slugs:
                # Merge duplicates (some orgs appear twice)
                if org_name in mapping:
                    existing = set(mapping[org_name])
                    for s in slugs:
                        if s not in existing:
                            mapping[org_name].append(s)
                else:
                    mapping[org_name] = slugs
    return mapping


def parse_person_md(slug):
    """Parse memory/people/<slug>.md → dict with name, org, role, email, phone."""
    path = os.path.join(PEOPLE_DIR, f'{slug}.md')
    if not os.path.exists(path):
        return None

    with open(path, 'r') as f:
        content = f.read()

    data = {'slug': slug}

    # Name from H1
    m = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if m:
        data['name'] = m.group(1).strip()

    # Fields (handle both "**Key:** value" and "- **Key:** value" formats)
    for key, field in [
        ('Organization', 'organization'),
        ('Role', 'role'),
        ('Email', 'email'),
        ('Phone', 'phone'),
        ('Title', 'title'),
    ]:
        m = re.search(rf'\*\*{key}:\*\*\s*(.+?)$', content, re.MULTILINE)
        if m:
            val = m.group(1).strip()
            # Strip markdown artifacts and parenthetical domain
            val = re.sub(r'\(.*?\)', '', val).strip()
            if val and val != '(TBD)' and val != 'TBD':
                data[field] = val

    # Use title as role fallback
    if 'title' in data and 'role' not in data:
        data['role'] = data['title']

    return data


def fuzzy_match_org(org_name, db_orgs, threshold=0.7):
    """Find best matching org from DB using fuzzy matching.

    Returns (org_id, org_db_name, score) or None.
    """
    # Strip disambiguators: "UTIMCO - Real Estate" stays, but "Future Fund (March 17)" → "Future Fund"
    clean_name = re.sub(r'\s*\([^)]*\)\s*$', '', org_name).strip()

    best = None
    best_score = 0

    for db_org in db_orgs:
        db_name = db_org.name

        # Exact match (case-insensitive)
        if clean_name.lower() == db_name.lower():
            return (db_org.id, db_name, 1.0)

        # Check if one contains the other
        if clean_name.lower() in db_name.lower() or db_name.lower() in clean_name.lower():
            score = 0.9
            if score > best_score:
                best = (db_org.id, db_name, score)
                best_score = score
                continue

        # Fuzzy ratio
        score = SequenceMatcher(None, clean_name.lower(), db_name.lower()).ratio()
        if score > best_score and score >= threshold:
            best = (db_org.id, db_name, score)
            best_score = score

    return best


def main():
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        print("=== DRY RUN MODE (no changes will be made) ===\n")

    init_db()

    # Load contacts index
    index = parse_contacts_index()
    print(f"Loaded {len(index)} org entries from contacts_index.md")
    print(f"Found {len(os.listdir(PEOPLE_DIR))} person files in memory/people/\n")

    with session_scope() as session:
        # Load all DB orgs for matching
        db_orgs = session.query(Organization).all()
        print(f"Found {len(db_orgs)} organizations in database\n")

        # Track stats
        inserted = 0
        updated = 0
        skipped_no_match = []
        skipped_no_file = []
        already_exists = 0

        for md_org_name, slugs in index.items():
            match = fuzzy_match_org(md_org_name, db_orgs)

            if not match:
                skipped_no_match.append(md_org_name)
                continue

            org_id, db_org_name, score = match
            match_label = f"(exact)" if score == 1.0 else f"(fuzzy {score:.0%} → '{db_org_name}')"

            for slug in slugs:
                person = parse_person_md(slug)
                if not person or 'name' not in person:
                    skipped_no_file.append(slug)
                    continue

                name = person['name']
                role = person.get('role', '')
                email = person.get('email', '')
                phone = person.get('phone', '')

                # Check if contact already exists for this org
                existing = session.query(Contact).filter_by(
                    organization_id=org_id
                ).filter(Contact.name.ilike(name)).first()

                if existing:
                    # Update if we have new data
                    changed = False
                    if email and not existing.email:
                        existing.email = email
                        changed = True
                    if role and not existing.title:
                        existing.title = role
                        changed = True
                    if phone and not existing.phone:
                        existing.phone = phone
                        changed = True
                    if changed:
                        existing.updated_at = datetime.now()
                        updated += 1
                        print(f"  UPDATED: {name} → {db_org_name} {match_label}")
                    else:
                        already_exists += 1
                    continue

                # Insert new contact
                if not dry_run:
                    contact = Contact(
                        name=name,
                        organization_id=org_id,
                        title=role,
                        email=email,
                        phone=phone,
                    )
                    session.add(contact)
                    session.flush()  # Get the ID immediately

                inserted += 1
                print(f"  INSERTED: {name} → {db_org_name} {match_label}")

        # --- Phase 2: Repair primary_contact_id on prospects ---
        print(f"\n--- Repairing primary_contact_id on prospects ---")
        prospects_fixed = 0

        # Load prospect markdown for primary contact hints
        prospects_md_path = os.path.join(PROJECT_ROOT, 'crm', 'prospects.md')
        if os.path.exists(prospects_md_path):
            with open(prospects_md_path, 'r') as f:
                prospects_content = f.read()

            # Find prospects with NULL primary_contact_id
            null_prospects = session.query(Prospect).filter(
                Prospect.primary_contact_id.is_(None)
            ).all()

            for prospect in null_prospects:
                org = session.query(Organization).get(prospect.organization_id)
                if not org:
                    continue

                # Look up contacts for this org
                contacts = session.query(Contact).filter_by(
                    organization_id=org.id
                ).all()

                if not contacts:
                    continue

                # If only one contact, use them
                if len(contacts) == 1:
                    if not dry_run:
                        prospect.primary_contact_id = contacts[0].id
                    prospects_fixed += 1
                    print(f"  LINKED (sole contact): {org.name} → {contacts[0].name}")
                    continue

                # Try to find primary contact from markdown
                # Look for "Primary Contact: <name>" near the org name
                pattern = rf'{re.escape(org.name)}.*?Primary Contact:\s*(.+?)(?:\n|$)'
                m = re.search(pattern, prospects_content, re.DOTALL | re.IGNORECASE)
                if m:
                    primary_name = m.group(1).strip().split(',')[0].strip()
                    # Match against available contacts
                    for c in contacts:
                        if primary_name.lower() in c.name.lower() or c.name.lower() in primary_name.lower():
                            if not dry_run:
                                prospect.primary_contact_id = c.id
                            prospects_fixed += 1
                            print(f"  LINKED (from markdown): {org.name} → {c.name}")
                            break

        # --- Summary ---
        print(f"\n{'='*60}")
        print(f"RESULTS {'(DRY RUN)' if dry_run else ''}:")
        print(f"  Contacts inserted:  {inserted}")
        print(f"  Contacts updated:   {updated}")
        print(f"  Already existed:    {already_exists}")
        print(f"  Prospects linked:   {prospects_fixed}")

        if skipped_no_match:
            print(f"\n  ⚠ Orgs not matched ({len(skipped_no_match)}):")
            for org in skipped_no_match:
                print(f"    - {org}")

        if skipped_no_file:
            print(f"\n  ⚠ Person files not found ({len(skipped_no_file)}):")
            for slug in skipped_no_file:
                print(f"    - {slug}")

        if dry_run:
            print(f"\n  Re-run without --dry-run to apply changes.")
            session.rollback()


if __name__ == '__main__':
    main()
