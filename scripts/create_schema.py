"""
Create PostgreSQL schema for arec-crm using SQLAlchemy models.

Drops and recreates all tables, then seeds pipeline stages and users.
"""

import os
import sys

# Add app/ to path
APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
sys.path.insert(0, APP_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(APP_DIR, '.env'))

from models import Base, PipelineStage, User, BriefingScope
from db import init_db, session_scope


def create_all_tables():
    """Drop and recreate all tables."""
    engine = init_db()

    print("Dropping all tables...")
    Base.metadata.drop_all(engine)

    print("Creating all tables...")
    Base.metadata.create_all(engine)

    print("✓ Schema created successfully")


def seed_pipeline_stages():
    """Insert canonical pipeline stages."""
    stages = [
        (0, '0. Declined', True, 0),
        (1, '1. Prospect', False, 1),
        (2, '2. Cold', False, 2),
        (3, '3. Outreach', False, 3),
        (4, '4. Engaged', False, 4),
        (5, '5. Interested', False, 5),
        (6, '6. Verbal', False, 6),
        (7, '7. Legal / DD', False, 7),
        (8, '8. Closed', False, 8),
    ]

    with session_scope() as session:
        for number, name, is_terminal, sort_order in stages:
            stage = PipelineStage(
                number=number,
                name=name,
                is_terminal=is_terminal,
                sort_order=sort_order
            )
            session.add(stage)

    print(f"✓ Seeded {len(stages)} pipeline stages")


def seed_users():
    """Insert placeholder user records for the 8-person team."""
    users = [
        ('placeholder-tony', 'tony@avilacapllc.com', 'Tony Avila', BriefingScope.executive),
        ('placeholder-oscar', 'oscar@avilacapllc.com', 'Oscar Vasquez', BriefingScope.full),
        ('placeholder-truman', 'truman@avilacapllc.com', 'Truman Flynn', BriefingScope.standard),
        ('placeholder-zach', 'zach@avilacapllc.com', 'Zach Reisner', BriefingScope.standard),
        ('placeholder-james', 'james@avilacapllc.com', 'James Walton', BriefingScope.standard),
        ('placeholder-ian', 'ian@avilacapllc.com', 'Ian Morgan', BriefingScope.standard),
        ('placeholder-patrick', 'patrick@avilacapllc.com', 'Patrick McElhaney', BriefingScope.standard),
        ('placeholder-rob', 'rob@avilacapllc.com', 'Rob Banagale', BriefingScope.standard),
    ]

    with session_scope() as session:
        for entra_id, email, display_name, briefing_scope in users:
            user = User(
                entra_id=entra_id,
                email=email,
                display_name=display_name,
                briefing_scope=briefing_scope,
                is_active=True,
                briefing_enabled=True
            )
            session.add(user)

    print(f"✓ Seeded {len(users)} team members")


def main():
    """Create schema and seed initial data."""
    print("AREC CRM Schema Creation")
    print("=" * 50)

    try:
        create_all_tables()
        seed_pipeline_stages()
        seed_users()
        print("\n✓ Schema creation complete!")
        print("\nNext step: Run scripts/migrate_to_postgres.py to import data from markdown files.")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
