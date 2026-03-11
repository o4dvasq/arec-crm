"""conftest.py — pytest configuration for ClaudeProductivity tests."""

import os
import sys
import pytest
from datetime import date, datetime

# Add app/ to path so we can import sources.* modules
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# Import database models and fixtures for Azure/Postgres tests
try:
    from db import init_db, get_session, SessionLocal
    from models import Base, User, Organization, Offering, Contact, Prospect, PipelineStage
    from models import Interaction, InteractionType, InteractionSource, UrgencyLevel, ClosingOption
    _AZURE_IMPORTS_AVAILABLE = True
except ImportError:
    _AZURE_IMPORTS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Azure/Postgres Test Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='session')
def test_database_url():
    """Return database URL for testing. Use SQLite in-memory if DATABASE_URL not set."""
    if not _AZURE_IMPORTS_AVAILABLE:
        pytest.skip("Azure imports not available")
    database_url = os.environ.get('TEST_DATABASE_URL')
    if not database_url:
        # Default to SQLite in-memory for fast local testing
        database_url = 'sqlite:///:memory:'
    return database_url


@pytest.fixture(scope='session')
def test_engine(test_database_url):
    """Initialize database engine for testing."""
    engine = init_db(database_url=test_database_url, echo=False)
    yield engine
    # Teardown: close all connections
    if SessionLocal:
        SessionLocal.remove()
    engine.dispose()


@pytest.fixture(scope='function')
def db_session(test_engine):
    """Provide a clean database session for each test.

    Creates all tables before the test and drops them after.
    """
    # Create all tables
    Base.metadata.create_all(bind=test_engine)

    # Get a session
    session = get_session()

    yield session

    # Teardown: rollback any uncommitted changes, close session, drop all tables
    session.rollback()
    session.close()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def seed_users(db_session):
    """Seed test users."""
    users = [
        User(
            entra_id='test-oscar',
            email='oscar@avilacapllc.com',
            display_name='Oscar Vasquez'
        ),
        User(
            entra_id='test-tony',
            email='tony@avilacapllc.com',
            display_name='Tony Avila'
        ),
    ]
    for u in users:
        db_session.add(u)
    db_session.commit()
    return users


@pytest.fixture
def seed_pipeline_stages(db_session):
    """Seed pipeline stages."""
    stages = [
        PipelineStage(number=0, name='0. Declined', is_terminal=True, sort_order=0),
        PipelineStage(number=1, name='1. Prospect', is_terminal=False, sort_order=1),
        PipelineStage(number=2, name='2. Cold', is_terminal=False, sort_order=2),
        PipelineStage(number=3, name='3. Outreach', is_terminal=False, sort_order=3),
        PipelineStage(number=4, name='4. Engaged', is_terminal=False, sort_order=4),
        PipelineStage(number=5, name='5. Interested', is_terminal=False, sort_order=5),
        PipelineStage(number=6, name='6. Verbal', is_terminal=False, sort_order=6),
        PipelineStage(number=7, name='7. Legal / DD', is_terminal=False, sort_order=7),
        PipelineStage(number=8, name='8. Closed', is_terminal=False, sort_order=8),
    ]
    for s in stages:
        db_session.add(s)
    db_session.commit()
    return stages


@pytest.fixture
def seed_offerings(db_session):
    """Seed test offerings."""
    offerings = [
        Offering(name='AREC Fund I', target=10000000000, hard_cap=12000000000),  # $100M / $120M
        Offering(name='AREC Fund II', target=25000000000, hard_cap=30000000000),  # $250M / $300M
    ]
    for o in offerings:
        db_session.add(o)
    db_session.commit()
    return offerings


@pytest.fixture
def seed_organizations(db_session):
    """Seed test organizations."""
    orgs = [
        Organization(name='UTIMCO', type='Pension / Endowment', domain='utimco.org'),
        Organization(name='Blackstone', type='Institutional Investor', domain='blackstone.com'),
        Organization(name='Texas PSF', type='Pension / Endowment', domain='tea.texas.gov'),
        Organization(name='Alpha Curve', type='HNWI / FO', domain='alphacurve.com'),
    ]
    for org in orgs:
        db_session.add(org)
    db_session.commit()
    return orgs


@pytest.fixture
def seed_contacts(db_session, seed_organizations):
    """Seed test contacts."""
    utimco = seed_organizations[0]
    blackstone = seed_organizations[1]

    contacts = [
        Contact(
            name='Jared Brimberry',
            organization_id=utimco.id,
            title='Investment Officer',
            email='jared@utimco.org',
            phone='512-555-0100'
        ),
        Contact(
            name='Amit Rind',
            organization_id=blackstone.id,
            title='Managing Director',
            email='amit.rind@blackstone.com',
        ),
    ]
    for c in contacts:
        db_session.add(c)
    db_session.commit()
    return contacts


@pytest.fixture
def seed_prospects(db_session, seed_organizations, seed_offerings, seed_contacts, seed_users):
    """Seed test prospects."""
    utimco = seed_organizations[0]
    blackstone = seed_organizations[1]
    fund_i = seed_offerings[0]
    fund_ii = seed_offerings[1]
    jared = seed_contacts[0]
    oscar = seed_users[0]

    prospects = [
        Prospect(
            organization_id=utimco.id,
            offering_id=fund_i.id,
            stage='5. Interested',
            target=500000000,  # $5M
            committed=0,
            primary_contact_id=jared.id,
            urgency=UrgencyLevel.High,
            closing=ClosingOption.First,
            assigned_to=oscar.id,
            notes='Strong interest, awaiting LP approval',
            last_touch=date(2026, 3, 10),
        ),
        Prospect(
            organization_id=blackstone.id,
            offering_id=fund_ii.id,
            stage='3. Outreach',
            target=1000000000,  # $10M
            committed=0,
            urgency=UrgencyLevel.Med,
            assigned_to=oscar.id,
        ),
    ]
    for p in prospects:
        db_session.add(p)
    db_session.commit()
    return prospects


@pytest.fixture
def seed_interactions(db_session, seed_organizations, seed_offerings, seed_contacts, seed_users):
    """Seed test interactions."""
    utimco = seed_organizations[0]
    fund_i = seed_offerings[0]
    jared = seed_contacts[0]
    oscar = seed_users[0]

    interactions = [
        Interaction(
            organization_id=utimco.id,
            offering_id=fund_i.id,
            contact_id=jared.id,
            interaction_date=date(2026, 3, 5),
            type=InteractionType.Meeting,
            subject='Fund II Introduction Call',
            summary='Discussed fund strategy, timing, and LP fit',
            source=InteractionSource.manual,
            created_by=oscar.id,
        ),
        Interaction(
            organization_id=utimco.id,
            interaction_date=date(2026, 3, 8),
            type=InteractionType.Email,
            subject='Follow-up: Fund materials',
            summary='Sent pitch deck and DDQ',
            source=InteractionSource.manual,
            created_by=oscar.id,
        ),
    ]
    for i in interactions:
        db_session.add(i)
    db_session.commit()
    return interactions


@pytest.fixture
def full_test_db(
    db_session,
    seed_users,
    seed_pipeline_stages,
    seed_offerings,
    seed_organizations,
    seed_contacts,
    seed_prospects,
    seed_interactions
):
    """Fixture that seeds the full test database with all related data."""
    return {
        'session': db_session,
        'users': seed_users,
        'stages': seed_pipeline_stages,
        'offerings': seed_offerings,
        'organizations': seed_organizations,
        'contacts': seed_contacts,
        'prospects': seed_prospects,
        'interactions': seed_interactions,
    }
