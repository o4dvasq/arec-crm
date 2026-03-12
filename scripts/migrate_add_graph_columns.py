"""
Migration: Add graph_consent_granted and scanned_by columns.

Adds:
  - users.graph_consent_granted (BOOLEAN DEFAULT FALSE)
  - users.graph_consent_date (TIMESTAMP)
  - email_scan_log.scanned_by (INTEGER REFERENCES users(id))
"""

import os
import sys

# Add app/ to path
APP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app')
sys.path.insert(0, APP_DIR)

from db import init_db, get_session
from sqlalchemy import text
from dotenv import load_dotenv
load_dotenv(os.path.join(APP_DIR, '.env'))

def run_migration():
    """Run the migration to add graph consent and scanned_by columns."""
    init_db()
    session = get_session()
    try:
        # Check if columns already exist
        result = session.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'graph_consent_granted'
        """))
        if result.fetchone():
            print("Migration already applied (graph_consent_granted exists)")
            return

        print("Adding graph_consent_granted and graph_consent_date to users table...")
        session.execute(text("""
            ALTER TABLE users
            ADD COLUMN graph_consent_granted BOOLEAN DEFAULT FALSE,
            ADD COLUMN graph_consent_date TIMESTAMP;
        """))

        print("Adding scanned_by to email_scan_log table...")
        session.execute(text("""
            ALTER TABLE email_scan_log
            ADD COLUMN scanned_by INTEGER REFERENCES users(id);
        """))

        session.commit()
        print("Migration complete!")

    except Exception as e:
        session.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        session.close()


if __name__ == '__main__':
    run_migration()
