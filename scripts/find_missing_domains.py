"""
Find CRM orgs without domains, then fuzzy-match against a contacts CSV
to discover their domains.

Logic:
1. Query all CRM orgs where domain is NULL or empty
2. Parse CSV contacts — build company_name → [email_domain] mapping
3. Fuzzy-match CRM org names against CSV company names
4. Suggest domain assignments

Usage:
    DATABASE_URL="postgresql://..." python3 scripts/find_missing_domains.py <csv_file> [--apply]

Without --apply, just prints suggestions. With --apply, updates org.domain in the DB.
"""

import csv
import os
import sys
from collections import defaultdict
from difflib import SequenceMatcher

APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
sys.path.insert(0, APP_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(APP_DIR, '.env'))
load_dotenv(os.path.join(APP_DIR, '.env.azure'))

from models import Organization
from db import init_db, session_scope


SKIP_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'icloud.com', 'me.com', 'live.com', 'msn.com', 'comcast.net',
    'verizon.net', 'att.net', 'sbcglobal.net', 'cox.net', 'charter.net',
    'earthlink.net', 'mac.com', 'protonmail.com', 'zoho.com',
    'avilacapllc.com', 'avilacapital.com', 'builderadvisorgroup.com',
}


def extract_domain(email):
    if not email or '@' not in email:
        return None
    return email.strip().lower().split('@')[1]


def parse_csv_companies(filepath):
    """Parse CSV → {company_name_lower: {domain: count}}"""
    companies = defaultdict(lambda: defaultdict(int))
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            company = (row.get('Company') or '').strip()
            email = (row.get('E-mail Address') or '').strip().lower()
            domain = extract_domain(email)

            if not company or not domain or domain in SKIP_DOMAINS:
                continue

            companies[company.lower()][domain] += 1

    # For each company, pick the most common domain
    result = {}
    for company_lower, domains in companies.items():
        best_domain = max(domains, key=domains.get)
        result[company_lower] = {
            'domain': best_domain,
            'count': domains[best_domain],
            'original_name': company,  # preserve original casing
        }

    return result


def fuzzy_match(org_name, csv_companies, threshold=0.75):
    """Find best matching company from CSV using fuzzy matching."""
    org_lower = org_name.lower().strip()

    # Exact match first
    if org_lower in csv_companies:
        return csv_companies[org_lower], 1.0

    # Containment check
    best = None
    best_score = 0

    for csv_name, data in csv_companies.items():
        # Check if one contains the other
        if org_lower in csv_name or csv_name in org_lower:
            score = 0.9
            if score > best_score:
                best = data
                best_score = score
                continue

        # Fuzzy ratio
        score = SequenceMatcher(None, org_lower, csv_name).ratio()
        if score > best_score and score >= threshold:
            best = data
            best_score = score

    if best:
        return best, best_score
    return None, 0


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/find_missing_domains.py <csv_file> [--apply]")
        sys.exit(1)

    csv_path = sys.argv[1]
    apply = '--apply' in sys.argv

    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        sys.exit(1)

    init_db()

    # Parse CSV companies
    csv_companies = parse_csv_companies(csv_path)
    print(f"CSV companies with email domains: {len(csv_companies)}\n")

    with session_scope() as session:
        # Find orgs without domains
        orgs_no_domain = session.query(Organization).filter(
            (Organization.domain.is_(None)) | (Organization.domain == '')
        ).order_by(Organization.name).all()

        all_orgs = session.query(Organization).count()
        orgs_with_domain = all_orgs - len(orgs_no_domain)

        print(f"Total CRM orgs: {all_orgs}")
        print(f"  With domain:    {orgs_with_domain}")
        print(f"  Missing domain: {len(orgs_no_domain)}\n")

        if not orgs_no_domain:
            print("All orgs have domains. Nothing to do.")
            return

        # Match against CSV
        matched = []
        unmatched = []

        for org in orgs_no_domain:
            result, score = fuzzy_match(org.name, csv_companies)
            if result:
                matched.append((org, result['domain'], score, result.get('original_name', '')))
            else:
                unmatched.append(org.name)

        # Print matches
        if matched:
            print(f"MATCHES FOUND ({len(matched)}):")
            print(f"{'CRM Org':<45} {'Domain':<35} {'CSV Company':<35} {'Score'}")
            print(f"{'-'*45} {'-'*35} {'-'*35} {'-'*5}")
            for org, domain, score, csv_name in matched:
                label = "exact" if score == 1.0 else f"{score:.0%}"
                print(f"{org.name:<45} {domain:<35} {csv_name:<35} {label}")

                if apply:
                    org.domain = domain

            print()

        if unmatched:
            print(f"\nNO MATCH ({len(unmatched)}):")
            for name in unmatched:
                print(f"  - {name}")

        # Summary
        print(f"\n{'='*60}")
        print(f"RESULTS:")
        print(f"  Domains discovered: {len(matched)}")
        print(f"  No match found:    {len(unmatched)}")

        if matched and not apply:
            print(f"\n  Re-run with --apply to update these domains in the database.")
        elif matched and apply:
            print(f"\n  Updated {len(matched)} org domains in database.")

        if not apply and matched:
            session.rollback()


if __name__ == '__main__':
    main()
