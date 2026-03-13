"""
test_crm_db.py — Tests for crm_db.py Postgres backend.

Tests all ~45 functions exported by crm_db.py against an ephemeral test database.
Uses fixtures from conftest_azure.py to set up test data.
"""

import os
import sys
import pytest
from datetime import date, datetime

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from sources import crm_db
from models import UrgencyLevel, ClosingOption, ProspectTask


# ---------------------------------------------------------------------------
# Currency helpers (pure functions)
# ---------------------------------------------------------------------------

def test_parse_currency_with_millions():
    assert crm_db._parse_currency('$50M') == 50_000_000.0


def test_parse_currency_with_billions():
    assert crm_db._parse_currency('$1.5B') == 1_500_000_000.0


def test_parse_currency_with_thousands():
    assert crm_db._parse_currency('$500K') == 500_000.0


def test_parse_currency_with_commas():
    assert crm_db._parse_currency('$5,000,000') == 5_000_000.0


def test_parse_currency_zero():
    assert crm_db._parse_currency('$0') == 0.0
    assert crm_db._parse_currency('') == 0.0


def test_format_currency_millions():
    assert crm_db._format_currency(50_000_000) == '$50M'


def test_format_currency_billions():
    assert crm_db._format_currency(1_500_000_000) == '$1.50B'


def test_format_currency_zero():
    assert crm_db._format_currency(0) == '$0'


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_load_crm_config(full_test_db):
    """load_crm_config returns stages and org types."""
    config = crm_db.load_crm_config()

    assert 'stages' in config
    assert 'org_types' in config

    # Check stages
    stages = config['stages']
    assert len(stages) == 9
    assert stages[0] == '0. Declined'
    assert stages[1] == '1. Prospect'
    assert stages[5] == '5. Interested'

    # Check org types (uses hardcoded list from crm_db.py)
    org_types = config['org_types']
    assert 'Pension Fund' in org_types
    assert 'HNWI / FO' in org_types


# ---------------------------------------------------------------------------
# Offerings
# ---------------------------------------------------------------------------

def test_load_offerings(full_test_db):
    """load_offerings returns all offerings."""
    offerings = crm_db.load_offerings()

    assert len(offerings) == 2
    names = [o['name'] for o in offerings]
    assert 'AREC Fund I' in names
    assert 'AREC Fund II' in names

    # Check target/hard_cap formatted correctly
    fund_i = next(o for o in offerings if o['name'] == 'AREC Fund I')
    assert fund_i['Target'] == '$100M'
    assert fund_i['Hard Cap'] == '$120M'


def test_get_offering(full_test_db):
    """get_offering returns a specific offering by name."""
    offering = crm_db.get_offering('AREC Fund I')

    assert offering is not None
    assert offering['name'] == 'AREC Fund I'
    assert offering['Target'] == '$100M'


def test_get_offering_not_found(full_test_db):
    """get_offering returns None for nonexistent offering."""
    offering = crm_db.get_offering('Nonexistent Fund')
    assert offering is None


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------

def test_load_organizations(full_test_db):
    """load_organizations returns all organizations."""
    orgs = crm_db.load_organizations()

    assert len(orgs) == 4
    names = [o['name'] for o in orgs]
    assert 'UTIMCO' in names
    assert 'Blackstone' in names
    assert 'Texas PSF' in names
    assert 'Alpha Curve' in names


def test_get_organization(full_test_db):
    """get_organization returns a specific org."""
    org = crm_db.get_organization('UTIMCO')

    assert org is not None
    assert org['name'] == 'UTIMCO'
    assert org['Type'] == 'Pension / Endowment'
    assert org['Domain'] == 'utimco.org'


def test_get_organization_not_found(full_test_db):
    """get_organization returns None for nonexistent org."""
    org = crm_db.get_organization('Nonexistent Org')
    assert org is None


def test_write_organization_create(db_session, seed_pipeline_stages, seed_users):
    """write_organization creates a new org."""
    org_data = {
        'Type': 'Pension / Endowment',
        'Domain': 'calpers.ca.gov',
        'Notes': 'California Public Employees Retirement System',
    }

    crm_db.write_organization('CalPERS', org_data)

    # Verify created
    org = crm_db.get_organization('CalPERS')
    assert org is not None
    assert org['Type'] == 'Pension / Endowment'
    assert org['Domain'] == 'calpers.ca.gov'


def test_write_organization_update(full_test_db):
    """write_organization updates an existing org."""
    org_data = {
        'Type': 'Pension / Endowment',
        'Domain': 'utimco.org',
        'Notes': 'Updated notes',
    }

    crm_db.write_organization('UTIMCO', org_data)

    # Verify updated
    org = crm_db.get_organization('UTIMCO')
    assert org['Notes'] == 'Updated notes'


def test_delete_organization(full_test_db):
    """delete_organization removes an org (with cascade to prospects/contacts)."""
    # Alpha Curve has no prospects or contacts, safe to delete
    crm_db.delete_organization('Alpha Curve')

    # Verify deleted
    org = crm_db.get_organization('Alpha Curve')
    assert org is None


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

def test_get_contacts_for_org(full_test_db):
    """get_contacts_for_org returns all contacts for an org."""
    contacts = crm_db.get_contacts_for_org('UTIMCO')

    assert len(contacts) == 1
    contact = contacts[0]
    assert contact['name'] == 'Jared Brimberry'
    assert contact['role'] == 'Investment Officer'
    assert contact['email'] == 'jared@utimco.org'


def test_load_person(full_test_db):
    """load_person returns a contact by slug."""
    person = crm_db.load_person('jared-brimberry')

    assert person is not None
    assert person['name'] == 'Jared Brimberry'
    assert person['organization'] == 'UTIMCO'
    assert person['email'] == 'jared@utimco.org'


def test_load_person_not_found(full_test_db):
    """load_person returns None for nonexistent person."""
    person = crm_db.load_person('nonexistent-person')
    assert person is None


def test_find_person_by_email(full_test_db):
    """find_person_by_email returns contact by email."""
    person = crm_db.find_person_by_email('jared@utimco.org')

    assert person is not None
    assert person['name'] == 'Jared Brimberry'
    assert person['organization'] == 'UTIMCO'


def test_find_person_by_email_not_found(full_test_db):
    """find_person_by_email returns None for unknown email."""
    person = crm_db.find_person_by_email('unknown@example.com')
    assert person is None


def test_create_person_file(full_test_db):
    """create_person_file creates a new contact."""
    slug = crm_db.create_person_file(
        name='John Doe',
        org='UTIMCO',
        email='john.doe@utimco.org',
        role='Analyst',
        person_type='investor'
    )

    assert slug == 'john-doe'

    # Verify created
    person = crm_db.find_person_by_email('john.doe@utimco.org')
    assert person is not None
    assert person['name'] == 'John Doe'
    assert person['role'] == 'Analyst'


def test_update_contact_fields(full_test_db):
    """update_contact_fields updates a contact's fields."""
    fields = {
        'role': 'Senior Investment Officer',
        'phone': '512-555-9999',
    }

    result = crm_db.update_contact_fields('UTIMCO', 'Jared Brimberry', fields)
    assert result is True

    # Verify updated
    person = crm_db.load_person('jared-brimberry')
    assert person['role'] == 'Senior Investment Officer'
    assert person['phone'] == '512-555-9999'


def test_load_all_persons(full_test_db):
    """load_all_persons returns all contacts."""
    persons = crm_db.load_all_persons()

    assert len(persons) == 2
    names = [p['name'] for p in persons]
    assert 'Jared Brimberry' in names
    assert 'Amit Rind' in names


# ---------------------------------------------------------------------------
# Prospects
# ---------------------------------------------------------------------------

def test_load_prospects(full_test_db):
    """load_prospects returns all prospects."""
    prospects = crm_db.load_prospects()

    assert len(prospects) == 2

    # Check UTIMCO prospect
    utimco_prospect = next(p for p in prospects if p['org'] == 'UTIMCO')
    assert utimco_prospect['offering'] == 'AREC Fund I'
    assert utimco_prospect['Stage'] == '5. Interested'
    assert utimco_prospect['Target'] == '$5M'
    assert utimco_prospect['Primary Contact'] == 'Jared Brimberry'
    assert utimco_prospect['Urgent'] == 'Yes'
    assert utimco_prospect['Closing'] == '1st'


def test_get_prospect(full_test_db):
    """get_prospect returns a specific prospect."""
    prospect = crm_db.get_prospect('UTIMCO', 'AREC Fund I')

    assert prospect is not None
    assert prospect['org'] == 'UTIMCO'
    assert prospect['offering'] == 'AREC Fund I'
    assert prospect['Stage'] == '5. Interested'
    assert prospect['Notes'] == 'Strong interest, awaiting LP approval'


def test_get_prospect_not_found(full_test_db):
    """get_prospect returns None for nonexistent prospect."""
    prospect = crm_db.get_prospect('Nonexistent Org', 'AREC Fund I')
    assert prospect is None


def test_get_prospects_for_org(full_test_db):
    """get_prospects_for_org returns all prospects for an org."""
    prospects = crm_db.get_prospects_for_org('UTIMCO')

    assert len(prospects) == 1
    prospect = prospects[0]
    assert prospect['offering'] == 'AREC Fund I'


def test_write_prospect_create(full_test_db):
    """write_prospect creates a new prospect."""
    prospect_data = {
        'Stage': '2. Cold',
        'Target': '$15M',
        'Urgent': 'No',
        'Assigned To': 'Oscar',
        'Notes': 'Initial outreach',
    }

    crm_db.write_prospect('Texas PSF', 'AREC Fund II', prospect_data)

    # Verify created
    prospect = crm_db.get_prospect('Texas PSF', 'AREC Fund II')
    assert prospect is not None
    assert prospect['Stage'] == '2. Cold'
    assert prospect['Target'] == '$15M'


def test_write_prospect_update(full_test_db):
    """write_prospect updates an existing prospect."""
    prospect_data = {
        'Stage': '6. Verbal',
        'Target': '$7.5M',
        'Notes': 'Verbal commitment received',
    }

    crm_db.write_prospect('UTIMCO', 'AREC Fund I', prospect_data)

    # Verify updated
    prospect = crm_db.get_prospect('UTIMCO', 'AREC Fund I')
    assert prospect['Stage'] == '6. Verbal'
    assert prospect['Target'] == '$7.5M'
    assert prospect['Notes'] == 'Verbal commitment received'


def test_update_prospect_field(full_test_db):
    """update_prospect_field updates a single field."""
    crm_db.update_prospect_field('UTIMCO', 'AREC Fund I', 'stage', '6. Verbal')

    # Verify updated
    prospect = crm_db.get_prospect('UTIMCO', 'AREC Fund I')
    assert prospect['Stage'] == '6. Verbal'


def test_delete_prospect(full_test_db):
    """delete_prospect removes a prospect."""
    crm_db.delete_prospect('Blackstone', 'AREC Fund II')

    # Verify deleted
    prospect = crm_db.get_prospect('Blackstone', 'AREC Fund II')
    assert prospect is None


# ---------------------------------------------------------------------------
# Pipeline / Fund Summary
# ---------------------------------------------------------------------------

def test_get_fund_summary(full_test_db):
    """get_fund_summary returns summary for a single offering."""
    summary = crm_db.get_fund_summary('AREC Fund I')

    assert summary is not None
    assert summary['offering'] == 'AREC Fund I'
    assert summary['fund_target_fmt'] == '$100M'
    assert summary['prospect_count'] == 1
    assert summary['total_target_fmt'] == '$5M'


def test_get_fund_summary_all(full_test_db):
    """get_fund_summary_all returns summaries for all offerings."""
    summaries = crm_db.get_fund_summary_all()

    assert len(summaries) == 2
    names = [s['offering'] for s in summaries]
    assert 'AREC Fund I' in names
    assert 'AREC Fund II' in names


# ---------------------------------------------------------------------------
# Interactions
# ---------------------------------------------------------------------------

def test_load_interactions(full_test_db):
    """load_interactions returns all interactions."""
    interactions = crm_db.load_interactions()

    assert len(interactions) == 2

    # Check meeting
    meeting = next(i for i in interactions if i['type'] == 'Meeting')
    assert meeting['org'] == 'UTIMCO'
    assert meeting['Subject'] == 'Fund II Introduction Call'
    assert meeting['date'] == '2026-03-05'


def test_append_interaction(full_test_db):
    """append_interaction adds a new interaction."""
    interaction = {
        'org': 'UTIMCO',
        'offering': 'AREC Fund I',
        'Contact': 'Jared Brimberry',
        'date': '2026-03-12',
        'type': 'Call',
        'Subject': 'Follow-up call',
        'Summary': 'Discussed timeline',
        'Source': 'manual',
    }

    crm_db.append_interaction(interaction)

    # Verify added
    interactions = crm_db.load_interactions()
    assert len(interactions) == 3


# ---------------------------------------------------------------------------
# Email Log
# ---------------------------------------------------------------------------

def test_add_emails_to_log(full_test_db):
    """add_emails_to_log adds email log entries."""
    emails = [
        {
            'messageId': 'msg-001',
            'from': 'jared@utimco.org',
            'to': ['oscar@avilacapllc.com'],
            'subject': 'Test email',
            'timestamp': '2026-03-10T00:00:00Z',
            'orgMatch': 'UTIMCO',
            'snippet': 'Email snippet...',
        }
    ]

    crm_db.add_emails_to_log(emails)

    # Verify added
    email = crm_db.find_email_by_message_id('msg-001')
    assert email is not None
    assert email['from'] == 'jared@utimco.org'
    assert email['subject'] == 'Test email'


def test_get_emails_for_org(full_test_db):
    """get_emails_for_org returns emails for an org."""
    # First add some test emails
    emails = [
        {
            'messageId': 'msg-utimco-1',
            'from': 'jared@utimco.org',
            'to': ['oscar@avilacapllc.com'],
            'subject': 'Email 1',
            'timestamp': '2026-03-10T00:00:00Z',
            'orgMatch': 'UTIMCO',
        },
        {
            'messageId': 'msg-utimco-2',
            'from': 'oscar@avilacapllc.com',
            'to': ['jared@utimco.org'],
            'subject': 'Email 2',
            'timestamp': '2026-03-11T00:00:00Z',
            'orgMatch': 'UTIMCO',
        },
    ]
    crm_db.add_emails_to_log(emails)

    # Get emails for UTIMCO
    org_emails = crm_db.get_emails_for_org('UTIMCO')
    assert len(org_emails) >= 2


def test_load_email_log(full_test_db):
    """load_email_log returns all email log entries."""
    # Add test email
    emails = [
        {
            'messageId': 'msg-test',
            'from': 'test@example.com',
            'subject': 'Test',
            'timestamp': '2026-03-10T00:00:00Z',
            'orgMatch': '',
        }
    ]
    crm_db.add_emails_to_log(emails)

    log = crm_db.load_email_log()
    assert len(log['emails']) >= 1


# ---------------------------------------------------------------------------
# Briefs
# ---------------------------------------------------------------------------

def test_save_and_load_brief(db_session, seed_pipeline_stages, seed_users):
    """save_brief and load_saved_brief work together."""
    crm_db.save_brief(
        brief_type='relationship',
        key='UTIMCO_AREC-Fund-I',
        narrative='Strong relationship with Jared...',
        content_hash='abc123',
        at_a_glance='Follow-up scheduled'
    )

    # Load brief
    loaded = crm_db.load_saved_brief('relationship', 'UTIMCO_AREC-Fund-I')
    assert loaded is not None
    assert loaded['narrative'] == 'Strong relationship with Jared...'
    assert loaded['at_a_glance'] == 'Follow-up scheduled'


def test_load_saved_brief_not_found(full_test_db):
    """load_saved_brief returns None for nonexistent brief."""
    brief = crm_db.load_saved_brief('relationship', 'Nonexistent_Key')
    assert brief is None


def test_load_all_briefs(db_session, seed_pipeline_stages, seed_users):
    """load_all_briefs returns all briefs."""
    # Save multiple briefs
    crm_db.save_brief('relationship', 'Key1', 'Brief 1', 'hash1')
    crm_db.save_brief('relationship', 'Key2', 'Brief 2', 'hash2')
    crm_db.save_brief('org', 'UTIMCO', 'Org brief', 'hash3')

    all_briefs = crm_db.load_all_briefs()
    assert 'relationship' in all_briefs
    assert len(all_briefs['relationship']) >= 2


# ---------------------------------------------------------------------------
# Prospect Notes
# ---------------------------------------------------------------------------

def test_save_and_load_prospect_notes(db_session, seed_pipeline_stages, seed_users):
    """save_prospect_note and load_prospect_notes work together."""
    note = crm_db.save_prospect_note(
        org='UTIMCO',
        offering='AREC Fund I',
        author='Oscar',
        text='Called Jared, confirmed interest level'
    )

    assert note is not None
    assert note['author'] == 'Oscar'

    # Load notes
    notes = crm_db.load_prospect_notes('UTIMCO', 'AREC Fund I')
    assert len(notes) == 1
    assert notes[0]['author'] == 'Oscar'
    assert 'Called Jared' in notes[0]['text']


def test_load_prospect_notes_empty(full_test_db):
    """load_prospect_notes returns empty list for prospect with no notes."""
    notes = crm_db.load_prospect_notes('Blackstone', 'AREC Fund II')
    assert notes == []


# ---------------------------------------------------------------------------
# Unmatched Emails
# ---------------------------------------------------------------------------

def test_add_and_load_unmatched(db_session, seed_pipeline_stages, seed_users):
    """add_unmatched and load_unmatched work together."""
    unmatched = {
        'participant_email': 'unknown@example.com',
        'participant_name': 'Unknown Person',
        'subject': 'Test subject',
        'date': '2026-03-10',
    }

    crm_db.add_unmatched(unmatched)

    # Load unmatched
    unmatched_list = crm_db.load_unmatched()
    assert len(unmatched_list) == 1
    assert unmatched_list[0]['participant_email'] == 'unknown@example.com'


def test_remove_unmatched(db_session, seed_pipeline_stages, seed_users):
    """remove_unmatched removes an entry."""
    unmatched = {
        'participant_email': 'remove@example.com',
        'participant_name': 'Remove Me',
        'subject': 'Test',
        'date': '2026-03-10',
    }
    crm_db.add_unmatched(unmatched)

    # Remove
    crm_db.remove_unmatched('remove@example.com')

    # Verify removed
    unmatched_list = crm_db.load_unmatched()
    emails = [u['participant_email'] for u in unmatched_list]
    assert 'remove@example.com' not in emails


# ---------------------------------------------------------------------------
# Pending Interviews
# ---------------------------------------------------------------------------

def test_add_pending_interview(db_session, seed_pipeline_stages, seed_users):
    """add_pending_interview adds a pending interview."""
    interview = {
        'org': 'UTIMCO',
        'offering': 'AREC Fund I',
        'reason': 'New org, needs context',
    }

    crm_db.add_pending_interview(interview)


# ---------------------------------------------------------------------------
# Org Domains
# ---------------------------------------------------------------------------

def test_get_org_domains(full_test_db):
    """get_org_domains returns domain mapping."""
    domains = crm_db.get_org_domains()

    assert 'UTIMCO' in domains
    assert domains['UTIMCO'] == 'utimco.org'
    assert 'Blackstone' in domains
    assert domains['Blackstone'] == 'blackstone.com'


# ---------------------------------------------------------------------------
# Email Enrichment Functions
# ---------------------------------------------------------------------------

def test_enrich_org_domain(full_test_db):
    """enrich_org_domain updates org domain."""
    # Texas PSF already has domain, try with Alpha Curve which doesn't
    result = crm_db.enrich_org_domain('Alpha Curve', 'alphacurve.com')
    assert result is False  # Already has domain from fixture

    # Create new org without domain
    crm_db.write_organization('NewOrg', {'Type': 'HNWI / FO', 'Domain': '', 'Notes': ''})
    result = crm_db.enrich_org_domain('NewOrg', 'neworg.com')
    assert result is True

    # Verify enriched
    org = crm_db.get_organization('NewOrg')
    assert org['Domain'] == '@neworg.com'


def test_discover_and_enrich_contact_emails(full_test_db):
    """discover_and_enrich_contact_emails updates contact emails."""
    # Create a contact without email first
    crm_db.create_person_file('Jane Doe', 'UTIMCO', '', 'Analyst', 'investor')

    # Mock email discovery data - list of tuples (email, display_name)
    email_addresses = [
        ('jane.doe@utimco.org', 'Jane Doe'),
    ]

    result = crm_db.discover_and_enrich_contact_emails('UTIMCO', email_addresses)
    # This function returns stats, just verify it runs without error
    assert isinstance(result, dict)
    assert 'emails_enriched' in result


# ==============================================================================
# Coverage tests for previously untested functions
# ==============================================================================

def test_get_team_member_email(full_test_db):
    """get_team_member_email returns email for team member."""
    email = crm_db.get_team_member_email('Oscar Vasquez')
    assert email == 'oscar@avilacapllc.com'
    
    # Case insensitive
    email = crm_db.get_team_member_email('oscar')
    assert email == 'oscar@avilacapllc.com'
    
    # Not found
    email = crm_db.get_team_member_email('Nobody')
    assert email == ''


def test_load_contacts_index(full_test_db):
    """load_contacts_index returns org->contacts mapping."""
    index = crm_db.load_contacts_index()
    assert 'UTIMCO' in index
    assert 'jared-brimberry' in index['UTIMCO']


def test_enrich_person_email(full_test_db):
    """enrich_person_email updates contact email."""
    crm_db.enrich_person_email('jared-brimberry', 'jared.new@utimco.org')
    person = crm_db.load_person('jared-brimberry')
    assert person['email'] == 'jared.new@utimco.org'


def test_add_contact_to_index(full_test_db):
    """add_contact_to_index is a no-op in Phase I1."""
    # Should not raise
    crm_db.add_contact_to_index('UTIMCO', 'jared-brimberry')


def test_ensure_contact_linked(full_test_db):
    """ensure_contact_linked creates contact if missing."""
    crm_db.ensure_contact_linked('New Person', 'UTIMCO')
    contacts = crm_db.get_contacts_for_org('UTIMCO')
    names = [c['name'] for c in contacts]
    assert 'New Person' in names


def test_load_meeting_history(full_test_db):
    """load_meeting_history reads from markdown file (smoke test)."""
    # Just verify it doesn't crash - file may not exist
    meetings = crm_db.load_meeting_history('UTIMCO')
    assert isinstance(meetings, list)


def test_add_meeting_entry(full_test_db):
    """add_meeting_entry appends to markdown file (smoke test)."""
    # Just verify it doesn't crash - may not have write permission
    try:
        crm_db.add_meeting_entry('UTIMCO', '2026-03-12', 'Test Meeting', 'Oscar, Tony', 'manual')
    except (IOError, FileNotFoundError):
        pass  # Expected if file doesn't exist


def test_append_person_email_history(full_test_db):
    """append_person_email_history is a no-op in Phase I1."""
    # Should not raise
    crm_db.append_person_email_history('jared-brimberry', '2026-03-12', 'Test Email', 'sent')


def test_append_org_email_history(full_test_db):
    """append_org_email_history is a no-op in Phase I1."""
    # Should not raise
    crm_db.append_org_email_history('UTIMCO', '2026-03-12', 'Test Email', 'Jared', 'received')


def test_purge_old_unmatched(full_test_db):
    """purge_old_unmatched removes old entries."""
    # Add an old unmatched email
    old_email = {
        'participant_email': 'old@example.com',
        'participant_name': 'Old Person',
        'date': '2025-01-01',
        'timestamp': '2025-01-01T10:00:00',
        'subject': 'Old Email'
    }
    crm_db.add_unmatched(old_email)
    
    # Purge emails older than 14 days
    crm_db.purge_old_unmatched(days=14)
    
    unmatched = crm_db.load_unmatched()
    # The old email should be purged
    emails = [u['participant_email'] for u in unmatched]
    assert 'old@example.com' not in emails


def test_load_tasks_by_org(full_test_db):
    """load_tasks_by_org groups tasks by org (smoke test)."""
    # Just verify it doesn't crash - file may not exist
    tasks_by_org = crm_db.load_tasks_by_org()
    assert isinstance(tasks_by_org, dict)


def test_get_tasks_for_prospect(full_test_db):
    """get_tasks_for_prospect finds tasks for specific org (smoke test)."""
    # Just verify it doesn't crash - file may not exist
    tasks = crm_db.get_tasks_for_prospect('UTIMCO')
    assert isinstance(tasks, list)


def test_get_all_prospect_tasks(full_test_db):
    """get_all_prospect_tasks finds all tasks with org tags (smoke test)."""
    # Just verify it doesn't crash - file may not exist
    tasks = crm_db.get_all_prospect_tasks()
    assert isinstance(tasks, list)


def test_add_prospect_task(full_test_db):
    """add_prospect_task appends task to TASKS.md (smoke test)."""
    # Just verify it doesn't crash - file may not exist
    result = crm_db.add_prospect_task('UTIMCO', 'Test task', 'Oscar', 'Hi')
    assert isinstance(result, bool)


def test_complete_prospect_task(full_test_db):
    """complete_prospect_task marks task as done (smoke test)."""
    # Just verify it doesn't crash - file may not exist or task may not exist
    result = crm_db.complete_prospect_task('UTIMCO', 'Some task')
    assert isinstance(result, bool)


def test_get_prospect_full(full_test_db):
    """get_prospect_full returns prospect with enriched data."""
    prospect = crm_db.get_prospect_full('UTIMCO', 'AREC Fund I')
    assert prospect is not None
    assert prospect['org'] == 'UTIMCO'
    assert prospect['offering'] == 'AREC Fund I'
    # Should include org data with org_ prefix
    assert 'org_Type' in prospect
    assert prospect['org_Type'] == 'Pension / Endowment'



def test_resolve_primary_contact(full_test_db):
    """resolve_primary_contact returns contact dict from name."""
    contact = crm_db.resolve_primary_contact('UTIMCO', 'Jared Brimberry')
    assert contact is not None
    assert contact['name'] == 'Jared Brimberry'
    
    # Not found returns None
    contact = crm_db.resolve_primary_contact('UTIMCO', 'Nobody')
    assert contact is None


# ---------------------------------------------------------------------------
# Tasks Dashboard
# ---------------------------------------------------------------------------

def test_get_all_tasks_for_dashboard_returns_enriched_tasks(full_test_db):
    """get_all_tasks_for_dashboard returns open tasks with prospect data."""
    session = full_test_db['session']

    # Seed an open task for UTIMCO
    task = ProspectTask(
        org_name='UTIMCO',
        text='Send term sheet',
        owner='Oscar Vasquez',
        priority='Hi',
        status='open',
    )
    session.add(task)
    session.commit()

    tasks = crm_db.get_all_tasks_for_dashboard()

    assert len(tasks) == 1
    t = tasks[0]
    assert t['org'] == 'UTIMCO'
    assert t['text'] == 'Send term sheet'
    assert t['owner'] == 'Oscar Vasquez'
    assert t['priority'] == 'Hi'
    assert t['status'] == 'open'
    # Should be enriched with prospect target from UTIMCO prospect ($5M = 500000000 cents)
    assert t['target'] == 500000000
    assert t['target_display'] == '$5M'
    assert t['offering'] == 'AREC Fund I'


def test_get_all_tasks_for_dashboard_excludes_completed(full_test_db):
    """get_all_tasks_for_dashboard only returns open tasks."""
    session = full_test_db['session']

    session.add(ProspectTask(
        org_name='UTIMCO', text='Done task', owner='Oscar Vasquez',
        priority='Med', status='completed',
    ))
    session.commit()

    tasks = crm_db.get_all_tasks_for_dashboard()
    assert all(t['status'] == 'open' for t in tasks)
    assert len(tasks) == 0


# ---------------------------------------------------------------------------
# Contact enrichment
# ---------------------------------------------------------------------------

def test_save_enrichment_results_new_fields(full_test_db):
    """save_enrichment_results populates enrichment fields and stamps enriched_at."""
    fields = {
        'phone': '512-555-9999',
        'linkedin_url': 'https://linkedin.com/in/jared-brimberry',
        'enrichment_source': {'phone': 'email footer', 'linkedin_url': 'web search'},
    }
    ok = crm_db.save_enrichment_results('Jared Brimberry', fields)
    assert ok is True

    person = crm_db.load_person('jared-brimberry')
    assert person is not None
    assert person['phone'] == '512-555-9999'
    assert person['linkedin_url'] == 'https://linkedin.com/in/jared-brimberry'
    assert person['enriched_at'] is not None


def test_save_enrichment_results_unknown_contact(full_test_db):
    """save_enrichment_results returns False for an unknown contact name."""
    ok = crm_db.save_enrichment_results('Nobody Here', {'phone': '555-0000'})
    assert ok is False


def test_save_enrichment_results_sets_enriched_at(full_test_db):
    """enriched_at is always stamped, even when no new data fields are provided."""
    ok = crm_db.save_enrichment_results('Jared Brimberry', {})
    assert ok is True
    person = crm_db.load_person('jared-brimberry')
    assert person['enriched_at'] is not None


def test_load_person_returns_enrichment_fields(full_test_db):
    """load_person returns linkedin_url and enriched_at keys."""
    person = crm_db.load_person('jared-brimberry')
    assert person is not None
    assert 'linkedin_url' in person
    assert 'enriched_at' in person


def test_save_enrichment_results_title_update(full_test_db):
    """save_enrichment_results updates title via the 'title' key."""
    ok = crm_db.save_enrichment_results('Amit Rind', {'title': 'Senior Managing Director'})
    assert ok is True
    person = crm_db.load_person('amit-rind')
    assert person['role'] == 'Senior Managing Director'


# ---------------------------------------------------------------------------
# Email signature parser (pure function — no DB or network needed)
# ---------------------------------------------------------------------------

def test_parse_email_signature_phone():
    """_parse_email_signature extracts a US phone number from the last lines."""
    from sources.ms_graph import _parse_email_signature
    body = (
        "Hi Oscar, thanks for the call.\n\n"
        "Best regards,\n"
        "Jared Brimberry\n"
        "Investment Officer, UTIMCO\n"
        "512-555-0100\n"
        "jared@utimco.org\n"
    )
    result = _parse_email_signature(body)
    assert result['phone'] is not None
    assert '512' in result['phone']


def test_parse_email_signature_title():
    """_parse_email_signature extracts a job title from the last lines."""
    from sources.ms_graph import _parse_email_signature
    body = (
        "Please find the attached documents.\n\n"
        "Amit Rind\n"
        "Managing Director\n"
        "Blackstone\n"
        "amit.rind@blackstone.com\n"
    )
    result = _parse_email_signature(body)
    assert result['title'] is not None
    assert 'Managing Director' in result['title']


def test_parse_email_signature_no_match():
    """_parse_email_signature returns None values when no patterns match."""
    from sources.ms_graph import _parse_email_signature
    body = "Hi there, just following up on our conversation."
    result = _parse_email_signature(body)
    assert result['phone'] is None
    assert result['title'] is None
