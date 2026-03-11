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
from models import UrgencyLevel, ClosingOption


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

    # Check org types
    org_types = config['org_types']
    assert 'Pension / Endowment' in org_types
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
    assert org['type'] == 'Pension / Endowment'
    assert org['domain'] == 'utimco.org'


def test_get_organization_not_found(full_test_db):
    """get_organization returns None for nonexistent org."""
    org = crm_db.get_organization('Nonexistent Org')
    assert org is None


def test_write_organization_create(db_session, seed_pipeline_stages, seed_users):
    """write_organization creates a new org."""
    org_dict = {
        'name': 'CalPERS',
        'type': 'Pension / Endowment',
        'domain': 'calpers.ca.gov',
        'notes': 'California Public Employees Retirement System',
    }

    result = crm_db.write_organization(org_dict)
    assert result is True

    # Verify created
    org = crm_db.get_organization('CalPERS')
    assert org is not None
    assert org['type'] == 'Pension / Endowment'
    assert org['domain'] == 'calpers.ca.gov'


def test_write_organization_update(full_test_db):
    """write_organization updates an existing org."""
    org_dict = {
        'name': 'UTIMCO',
        'type': 'Pension / Endowment',
        'domain': 'utimco.org',
        'notes': 'Updated notes',
    }

    result = crm_db.write_organization(org_dict)
    assert result is True

    # Verify updated
    org = crm_db.get_organization('UTIMCO')
    assert org['notes'] == 'Updated notes'


def test_delete_organization(full_test_db):
    """delete_organization removes an org (with cascade to prospects/contacts)."""
    # Alpha Curve has no prospects or contacts, safe to delete
    result = crm_db.delete_organization('Alpha Curve')
    assert result is True

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
    assert contact['title'] == 'Investment Officer'
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
    person_dict = {
        'name': 'John Doe',
        'organization': 'UTIMCO',
        'title': 'Analyst',
        'email': 'john.doe@utimco.org',
        'phone': '512-555-0200',
    }

    result = crm_db.create_person_file(person_dict)
    assert result is True

    # Verify created
    person = crm_db.find_person_by_email('john.doe@utimco.org')
    assert person is not None
    assert person['name'] == 'John Doe'
    assert person['title'] == 'Analyst'


def test_update_contact_fields(full_test_db):
    """update_contact_fields updates a contact's fields."""
    fields = {
        'title': 'Senior Investment Officer',
        'phone': '512-555-9999',
    }

    result = crm_db.update_contact_fields('jared-brimberry', fields)
    assert result is True

    # Verify updated
    person = crm_db.load_person('jared-brimberry')
    assert person['title'] == 'Senior Investment Officer'
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
    utimco_prospect = next(p for p in prospects if p['Organization'] == 'UTIMCO')
    assert utimco_prospect['Offering'] == 'AREC Fund I'
    assert utimco_prospect['Stage'] == '5. Interested'
    assert utimco_prospect['Target'] == '$5M'
    assert utimco_prospect['Primary Contact'] == 'Jared Brimberry'
    assert utimco_prospect['Urgent'] == 'Yes'
    assert utimco_prospect['Closing'] == '1st'


def test_get_prospect(full_test_db):
    """get_prospect returns a specific prospect."""
    prospect = crm_db.get_prospect('AREC Fund I', 'UTIMCO')

    assert prospect is not None
    assert prospect['Organization'] == 'UTIMCO'
    assert prospect['Offering'] == 'AREC Fund I'
    assert prospect['Stage'] == '5. Interested'
    assert prospect['Notes'] == 'Strong interest, awaiting LP approval'


def test_get_prospect_not_found(full_test_db):
    """get_prospect returns None for nonexistent prospect."""
    prospect = crm_db.get_prospect('AREC Fund I', 'Nonexistent Org')
    assert prospect is None


def test_get_prospects_for_org(full_test_db):
    """get_prospects_for_org returns all prospects for an org."""
    prospects = crm_db.get_prospects_for_org('UTIMCO')

    assert len(prospects) == 1
    prospect = prospects[0]
    assert prospect['Offering'] == 'AREC Fund I'


def test_write_prospect_create(full_test_db):
    """write_prospect creates a new prospect."""
    prospect_dict = {
        'Organization': 'Texas PSF',
        'Offering': 'AREC Fund II',
        'Stage': '2. Cold',
        'Target': '$15M',
        'Urgent': 'No',
        'Assigned To': 'Oscar',
        'Notes': 'Initial outreach',
    }

    result = crm_db.write_prospect(prospect_dict)
    assert result is True

    # Verify created
    prospect = crm_db.get_prospect('AREC Fund II', 'Texas PSF')
    assert prospect is not None
    assert prospect['Stage'] == '2. Cold'
    assert prospect['Target'] == '$15M'


def test_write_prospect_update(full_test_db):
    """write_prospect updates an existing prospect."""
    prospect_dict = {
        'Organization': 'UTIMCO',
        'Offering': 'AREC Fund I',
        'Stage': '6. Verbal',
        'Target': '$7.5M',
        'Notes': 'Verbal commitment received',
    }

    result = crm_db.write_prospect(prospect_dict)
    assert result is True

    # Verify updated
    prospect = crm_db.get_prospect('AREC Fund I', 'UTIMCO')
    assert prospect['Stage'] == '6. Verbal'
    assert prospect['Target'] == '$7.5M'
    assert prospect['Notes'] == 'Verbal commitment received'


def test_update_prospect_field(full_test_db):
    """update_prospect_field updates a single field."""
    result = crm_db.update_prospect_field('AREC Fund I', 'UTIMCO', 'stage', '6. Verbal')
    assert result is True

    # Verify updated
    prospect = crm_db.get_prospect('AREC Fund I', 'UTIMCO')
    assert prospect['Stage'] == '6. Verbal'


def test_delete_prospect(full_test_db):
    """delete_prospect removes a prospect."""
    result = crm_db.delete_prospect('AREC Fund II', 'Blackstone')
    assert result is True

    # Verify deleted
    prospect = crm_db.get_prospect('AREC Fund II', 'Blackstone')
    assert prospect is None


# ---------------------------------------------------------------------------
# Pipeline / Fund Summary
# ---------------------------------------------------------------------------

def test_get_fund_summary(full_test_db):
    """get_fund_summary returns summary for a single offering."""
    summary = crm_db.get_fund_summary('AREC Fund I')

    assert summary is not None
    assert summary['offering'] == 'AREC Fund I'
    assert summary['target'] == '$100M'
    assert summary['hard_cap'] == '$120M'

    # Check by_stage breakdown
    by_stage = summary['by_stage']
    assert '5. Interested' in by_stage
    assert by_stage['5. Interested']['count'] == 1
    assert by_stage['5. Interested']['target'] == '$5M'


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
    assert meeting['subject'] == 'Fund II Introduction Call'
    assert meeting['date'] == '2026-03-05'


def test_append_interaction(full_test_db):
    """append_interaction adds a new interaction."""
    interaction = {
        'org': 'UTIMCO',
        'offering': 'AREC Fund I',
        'contact': 'Jared Brimberry',
        'date': '2026-03-12',
        'type': 'Call',
        'subject': 'Follow-up call',
        'summary': 'Discussed timeline',
        'source': 'manual',
    }

    result = crm_db.append_interaction(interaction)
    assert result is True

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
            'message_id': 'msg-001',
            'from_email': 'jared@utimco.org',
            'to_emails': 'oscar@avilacapllc.com',
            'subject': 'Test email',
            'date': date(2026, 3, 10),
            'org_name': 'UTIMCO',
            'matched': True,
            'snippet': 'Email snippet...',
        }
    ]

    crm_db.add_emails_to_log(emails)

    # Verify added
    email = crm_db.find_email_by_message_id('msg-001')
    assert email is not None
    assert email['from_email'] == 'jared@utimco.org'
    assert email['subject'] == 'Test email'


def test_get_emails_for_org(full_test_db):
    """get_emails_for_org returns emails for an org."""
    # First add some test emails
    emails = [
        {
            'message_id': 'msg-utimco-1',
            'from_email': 'jared@utimco.org',
            'to_emails': 'oscar@avilacapllc.com',
            'subject': 'Email 1',
            'date': date(2026, 3, 10),
            'org_name': 'UTIMCO',
            'matched': True,
        },
        {
            'message_id': 'msg-utimco-2',
            'from_email': 'oscar@avilacapllc.com',
            'to_emails': 'jared@utimco.org',
            'subject': 'Email 2',
            'date': date(2026, 3, 11),
            'org_name': 'UTIMCO',
            'matched': True,
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
            'message_id': 'msg-test',
            'from_email': 'test@example.com',
            'subject': 'Test',
            'date': date(2026, 3, 10),
            'org_name': '',
            'matched': False,
        }
    ]
    crm_db.add_emails_to_log(emails)

    log = crm_db.load_email_log()
    assert len(log) >= 1


# ---------------------------------------------------------------------------
# Briefs
# ---------------------------------------------------------------------------

def test_save_and_load_brief(db_session, seed_pipeline_stages, seed_users):
    """save_brief and load_saved_brief work together."""
    brief_data = {
        'brief_type': 'relationship',
        'key': 'UTIMCO_AREC-Fund-I',
        'narrative': 'Strong relationship with Jared...',
        'at_a_glance': 'Follow-up scheduled',
    }

    result = crm_db.save_brief(brief_data)
    assert result is True

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
    briefs = [
        {'brief_type': 'relationship', 'key': 'Key1', 'narrative': 'Brief 1'},
        {'brief_type': 'relationship', 'key': 'Key2', 'narrative': 'Brief 2'},
        {'brief_type': 'org', 'key': 'UTIMCO', 'narrative': 'Org brief'},
    ]
    for b in briefs:
        crm_db.save_brief(b)

    all_briefs = crm_db.load_all_briefs()
    assert len(all_briefs) >= 3


# ---------------------------------------------------------------------------
# Prospect Notes
# ---------------------------------------------------------------------------

def test_save_and_load_prospect_notes(db_session, seed_pipeline_stages, seed_users):
    """save_prospect_note and load_prospect_notes work together."""
    note = {
        'org_name': 'UTIMCO',
        'offering_name': 'AREC Fund I',
        'author': 'Oscar',
        'text': 'Called Jared, confirmed interest level',
    }

    result = crm_db.save_prospect_note(note)
    assert result is True

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
        'email': 'unknown@example.com',
        'display_name': 'Unknown Person',
        'subject': 'Test subject',
        'date': date(2026, 3, 10),
    }

    crm_db.add_unmatched(unmatched)

    # Load unmatched
    unmatched_list = crm_db.load_unmatched()
    assert len(unmatched_list) == 1
    assert unmatched_list[0]['email'] == 'unknown@example.com'


def test_remove_unmatched(db_session, seed_pipeline_stages, seed_users):
    """remove_unmatched removes an entry."""
    unmatched = {
        'email': 'remove@example.com',
        'display_name': 'Remove Me',
        'subject': 'Test',
        'date': date(2026, 3, 10),
    }
    crm_db.add_unmatched(unmatched)

    # Remove
    result = crm_db.remove_unmatched('remove@example.com')
    assert result is True

    # Verify removed
    unmatched_list = crm_db.load_unmatched()
    emails = [u['email'] for u in unmatched_list]
    assert 'remove@example.com' not in emails


# ---------------------------------------------------------------------------
# Pending Interviews
# ---------------------------------------------------------------------------

def test_add_pending_interview(db_session, seed_pipeline_stages, seed_users):
    """add_pending_interview adds a pending interview."""
    interview = {
        'org_name': 'UTIMCO',
        'offering_name': 'AREC Fund I',
        'reason': 'New org, needs context',
    }

    result = crm_db.add_pending_interview(interview)
    assert result is True


# ---------------------------------------------------------------------------
# Org Domains
# ---------------------------------------------------------------------------

def test_get_org_domains(full_test_db):
    """get_org_domains returns domain mapping."""
    domains = crm_db.get_org_domains()

    assert 'utimco.org' in domains
    assert domains['utimco.org'] == 'UTIMCO'
    assert 'blackstone.com' in domains
    assert domains['blackstone.com'] == 'Blackstone'


# ---------------------------------------------------------------------------
# Email Enrichment Functions
# ---------------------------------------------------------------------------

def test_enrich_org_domain(full_test_db):
    """enrich_org_domain updates org domain."""
    result = crm_db.enrich_org_domain('Texas PSF', 'tea.texas.gov')
    assert result is True

    # Verify enriched
    org = crm_db.get_organization('Texas PSF')
    assert org['domain'] == 'tea.texas.gov'


def test_discover_and_enrich_contact_emails(full_test_db):
    """discover_and_enrich_contact_emails updates contact emails."""
    # Mock email discovery data
    emails_by_org = {
        'UTIMCO': [
            {'name': 'Jared Brimberry', 'email': 'jared.brimberry@utimco.org'},
        ]
    }

    result = crm_db.discover_and_enrich_contact_emails(emails_by_org)
    # This function returns stats, just verify it runs without error
    assert isinstance(result, dict)
