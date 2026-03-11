"""
Post-migration verification script.

Compares record counts between markdown files and PostgreSQL,
performs spot checks on sample records to ensure data integrity.
"""

import os
import sys

# Add app/ to path
APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
sys.path.insert(0, APP_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(APP_DIR, '.env.azure'))

from models import (
    Organization, Offering, Contact, Prospect, Interaction, EmailScanLog,
    Brief, ProspectNote, UnmatchedEmail, PendingInterview, User, PipelineStage
)
from db import init_db, get_session
from sources.crm_reader import (
    load_organizations, load_offerings, load_prospects, load_contacts_index,
    load_person, load_interactions, load_email_log, load_all_briefs,
    load_unmatched, load_pending_interviews
)


def count_markdown_contacts():
    """Count total contacts across all orgs in contacts_index.md."""
    index = load_contacts_index()
    total = sum(len(slugs) for slugs in index.values())
    return total


def count_markdown_briefs():
    """Count all briefs across all types."""
    briefs = load_all_briefs()
    total = sum(len(entries) for entries in briefs.values())
    return total


def count_markdown_prospect_notes():
    """Count all prospect notes."""
    import json
    from os.path import join, exists
    PROJECT_ROOT = os.path.dirname(APP_DIR)
    notes_path = join(PROJECT_ROOT, 'crm', 'prospect_notes.json')
    if not exists(notes_path):
        return 0
    with open(notes_path, 'r') as f:
        data = json.load(f)
    total = sum(len(notes) for notes in data.values())
    return total


def verify_counts(session):
    """Compare record counts: markdown vs PostgreSQL."""
    print("\nVerifying record counts...")
    print("-" * 70)
    print(f"{'Table':<25} {'Markdown':<15} {'PostgreSQL':<15} {'Status':<10}")
    print("-" * 70)

    checks = []

    # Organizations
    md_orgs = len(load_organizations())
    pg_orgs = session.query(Organization).count()
    checks.append(('Organizations', md_orgs, pg_orgs))

    # Offerings
    md_offerings = len(load_offerings())
    pg_offerings = session.query(Offering).count()
    checks.append(('Offerings', md_offerings, pg_offerings))

    # Contacts
    md_contacts = count_markdown_contacts()
    pg_contacts = session.query(Contact).count()
    checks.append(('Contacts', md_contacts, pg_contacts))

    # Prospects
    md_prospects = len(load_prospects())
    pg_prospects = session.query(Prospect).count()
    checks.append(('Prospects', md_prospects, pg_prospects))

    # Interactions
    md_interactions = len(load_interactions())
    pg_interactions = session.query(Interaction).count()
    checks.append(('Interactions', md_interactions, pg_interactions))

    # Email log
    md_emails = len(load_email_log().get('emails', []))
    pg_emails = session.query(EmailScanLog).count()
    checks.append(('Email Log', md_emails, pg_emails))

    # Briefs
    md_briefs = count_markdown_briefs()
    pg_briefs = session.query(Brief).count()
    checks.append(('Briefs', md_briefs, pg_briefs))

    # Prospect notes
    md_notes = count_markdown_prospect_notes()
    pg_notes = session.query(ProspectNote).count()
    checks.append(('Prospect Notes', md_notes, pg_notes))

    # Unmatched emails
    md_unmatched = len(load_unmatched())
    pg_unmatched = session.query(UnmatchedEmail).count()
    checks.append(('Unmatched Emails', md_unmatched, pg_unmatched))

    # Pending interviews
    md_pending = len(load_pending_interviews())
    pg_pending = session.query(PendingInterview).count()
    checks.append(('Pending Interviews', md_pending, pg_pending))

    all_pass = True
    for table, md_count, pg_count in checks:
        status = "✓ PASS" if md_count == pg_count else "✗ FAIL"
        if md_count != pg_count:
            all_pass = False
        print(f"{table:<25} {md_count:<15} {pg_count:<15} {status:<10}")

    print("-" * 70)
    return all_pass


def spot_check_data(session):
    """Perform spot checks on sample records."""
    print("\nSpot-checking sample records...")

    issues = []

    # Check: All orgs have types
    orgs_no_type = session.query(Organization).filter(
        (Organization.type == '') | (Organization.type == None)
    ).count()
    if orgs_no_type > 0:
        issues.append(f"  ✗ {orgs_no_type} organizations missing type")
    else:
        print("  ✓ All organizations have types")

    # Check: HNWI/FO normalized to HNWI / FO
    hnwi_old = session.query(Organization).filter_by(type='HNWI/FO').count()
    if hnwi_old > 0:
        issues.append(f"  ✗ {hnwi_old} orgs still have 'HNWI/FO' (should be 'HNWI / FO')")
    else:
        print("  ✓ Org type normalization correct (HNWI / FO)")

    # Check: Pipeline stage remapping
    qualified = session.query(Prospect).filter_by(stage='2. Qualified').count()
    presentation = session.query(Prospect).filter_by(stage='3. Presentation').count()
    if qualified > 0 or presentation > 0:
        issues.append(f"  ✗ Stage remapping incomplete ({qualified} Qualified, {presentation} Presentation)")
    else:
        print("  ✓ Pipeline stages remapped correctly")

    # Check: All prospects have org and offering
    orphan_prospects = session.query(Prospect).filter(
        (Prospect.organization_id == None) | (Prospect.offering_id == None)
    ).count()
    if orphan_prospects > 0:
        issues.append(f"  ✗ {orphan_prospects} prospects missing org or offering")
    else:
        print("  ✓ All prospects have organization and offering")

    # Check: Currency stored as BIGINT (cents)
    # Sample a prospect with $50M target → should be 5000000000 cents
    sample_prospect = session.query(Prospect).filter(Prospect.target > 0).first()
    if sample_prospect:
        # Verify target is in cents (large integer)
        if sample_prospect.target >= 100:
            print(f"  ✓ Currency stored as cents (sample: {sample_prospect.target})")
        else:
            issues.append(f"  ✗ Currency might not be in cents (sample: {sample_prospect.target})")

    # Check: All users seeded
    user_count = session.query(User).count()
    if user_count == 8:
        print("  ✓ All 8 team members seeded")
    else:
        issues.append(f"  ✗ Expected 8 users, found {user_count}")

    # Check: Pipeline stages seeded
    stage_count = session.query(PipelineStage).count()
    if stage_count == 9:
        print("  ✓ All 9 pipeline stages seeded")
    else:
        issues.append(f"  ✗ Expected 9 pipeline stages, found {stage_count}")

    if issues:
        print("\nIssues found:")
        for issue in issues:
            print(issue)
        return False

    return True


def main():
    """Run verification checks."""
    print("AREC CRM Migration Verification")
    print("=" * 70)

    try:
        init_db()
        session = get_session()

        counts_pass = verify_counts(session)
        spot_check_pass = spot_check_data(session)

        print("\n" + "=" * 70)
        if counts_pass and spot_check_pass:
            print("✓ VERIFICATION PASSED")
            print("\nAll record counts match and spot checks passed.")
            print("Migration successful!")
        else:
            print("✗ VERIFICATION FAILED")
            print("\nSome checks did not pass. Review the output above.")
            sys.exit(1)

        session.close()

    except Exception as e:
        print(f"\n✗ Verification error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
