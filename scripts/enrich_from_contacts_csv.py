"""
Enrich CRM contacts from an Outlook contacts CSV export.

Logic:
1. Load all CRM orgs and their domains from PostgreSQL
2. Parse the CSV — extract email domain for each contact
3. Match email domains against CRM org domains
4. For matches: update existing contacts (email, phone, title) or create new ones
5. Skip everything that doesn't match a CRM org domain

Usage:
    DATABASE_URL="postgresql://..." python3 scripts/enrich_from_contacts_csv.py <csv_file> [--dry-run]

The CSV must be an Outlook-format export with columns:
    First Name, Last Name, E-mail Address, Company, Job Title,
    Mobile Phone, Business Phone
"""

import csv
import os
import sys
from collections import defaultdict
from datetime import datetime

APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
sys.path.insert(0, APP_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(APP_DIR, '.env'))
load_dotenv(os.path.join(APP_DIR, '.env.azure'))

from models import Organization, Contact
from db import init_db, session_scope


# Domains to skip (internal, generic email providers)
SKIP_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'me.com', 'live.com', 'msn.com', 'comcast.net',
    'verizon.net', 'att.net', 'sbcglobal.net', 'cox.net', 'charter.net',
    'earthlink.net', 'mac.com', 'protonmail.com', 'zoho.com',
    'avilacapllc.com', 'avilacapital.com', 'builderadvisorgroup.com',
}


def extract_domain(email):
    """Extract domain from email address."""
    if not email or '@' not in email:
        return None
    return email.strip().lower().split('@')[1]


def parse_csv(filepath):
    """Parse Outlook contacts CSV → list of contact dicts."""
    contacts = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            first = (row.get('First Name') or '').strip()
            last = (row.get('Last Name') or '').strip()
            email = (row.get('E-mail Address') or '').strip().lower()
            email2 = (row.get('E-mail 2 Address') or '').strip().lower()
            company = (row.get('Company') or '').strip()
            title = (row.get('Job Title') or '').strip()
            mobile = (row.get('Mobile Phone') or '').strip()
            business = (row.get('Business Phone') or '').strip()
            phone = mobile or business

            if not first and not last:
                continue

            name = f"{first} {last}".strip()
            domain = extract_domain(email) or extract_domain(email2)

            if not domain or domain in SKIP_DOMAINS:
                continue

            contacts.append({
                'name': name,
                'email': email or email2,
                'domain': domain,
                'company': company,
                'title': title,
                'phone': phone,
            })

    return contacts


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/enrich_from_contacts_csv.py <csv_file> [--dry-run]")
        sys.exit(1)

    csv_path = sys.argv[1]
    dry_run = '--dry-run' in sys.argv

    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        sys.exit(1)

    if dry_run:
        print("=== DRY RUN MODE ===\n")

    init_db()

    # Parse CSV
    csv_contacts = parse_csv(csv_path)
    print(f"Parsed {len(csv_contacts)} contacts with valid email domains from CSV\n")

    # Index CSV contacts by domain
    by_domain = defaultdict(list)
    for c in csv_contacts:
        by_domain[c['domain']].append(c)

    print(f"Unique domains in CSV: {len(by_domain)}\n")

    with session_scope() as session:
        # Load all CRM orgs and their domains
        orgs = session.query(Organization).all()
        print(f"CRM organizations: {len(orgs)}")

        # Build domain → org mapping
        # Check org_domains table first, then fall back to org.domain field
        domain_to_org = {}

        # From org.domain field
        for org in orgs:
            if org.domain:
                d = org.domain.strip().lower()
                if d and d not in domain_to_org:
                    domain_to_org[d] = org.id

        print(f"CRM org domains indexed: {len(domain_to_org)}")

        # Build org_id → org name lookup
        org_names = {org.id: org.name for org in orgs}

        # Match CSV domains against CRM domains
        matched_domains = set(by_domain.keys()) & set(domain_to_org.keys())
        print(f"Matching domains: {len(matched_domains)}\n")

        if matched_domains:
            print("Matched domains:")
            for d in sorted(matched_domains):
                org_id = domain_to_org[d]
                count = len(by_domain[d])
                print(f"  {d} → {org_names.get(org_id, '?')} ({count} contacts)")
            print()

        # Process matches
        created = 0
        updated = 0
        skipped_existing = 0

        for domain in sorted(matched_domains):
            org_id = domain_to_org[domain]
            org_name = org_names.get(org_id, '?')

            for csv_contact in by_domain[domain]:
                name = csv_contact['name']
                email = csv_contact['email']
                phone = csv_contact['phone']
                title = csv_contact['title']

                # Check if contact already exists (by name or email)
                existing = None

                # Try email match first
                if email:
                    existing = session.query(Contact).filter_by(
                        organization_id=org_id
                    ).filter(Contact.email.ilike(email)).first()

                # Try name match
                if not existing:
                    existing = session.query(Contact).filter_by(
                        organization_id=org_id
                    ).filter(Contact.name.ilike(name)).first()

                if existing:
                    # Update missing fields only
                    changed = False
                    if email and not existing.email:
                        existing.email = email
                        changed = True
                    if phone and not existing.phone:
                        existing.phone = phone
                        changed = True
                    if title and not existing.title:
                        existing.title = title
                        changed = True

                    if changed:
                        existing.updated_at = datetime.now()
                        updated += 1
                        print(f"  UPDATED: {name} ({org_name}) — filled in {'+'.join(f for f, v in [('email', email), ('phone', phone), ('title', title)] if v and f)}")
                    else:
                        skipped_existing += 1
                else:
                    # Create new contact for this CRM org
                    if not dry_run:
                        contact = Contact(
                            name=name,
                            organization_id=org_id,
                            email=email,
                            phone=phone,
                            title=title,
                        )
                        session.add(contact)

                    created += 1
                    print(f"  CREATED: {name} → {org_name} ({email})")

        # Summary
        print(f"\n{'='*60}")
        print(f"RESULTS {'(DRY RUN)' if dry_run else ''}:")
        print(f"  Contacts created:       {created}")
        print(f"  Contacts updated:       {updated}")
        print(f"  Already complete:       {skipped_existing}")
        print(f"  Domains matched:        {len(matched_domains)}")
        print(f"  Domains not in CRM:     {len(by_domain) - len(matched_domains)}")

        if dry_run:
            print(f"\n  Re-run without --dry-run to apply changes.")
            session.rollback()


if __name__ == '__main__':
    main()
