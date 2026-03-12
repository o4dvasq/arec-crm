"""
Migration script to add graph_consent columns to users table
and scanned_by column to email_scan_log table.

Run this script to add the new columns needed for multi-user email polling.
"""

import os
import sys

# Add app directory to path
APP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app')
sys.path.insert(0, APP_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(APP_DIR, '.env'))

from db import init_db
from sqlalchemy import text


def migrate():
    """Add graph consent columns to users and scanned_by to email_scan_log."""
    engine = init_db()

    with engine.connect() as conn:
        # Add graph_consent_granted to users table
        try:
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN graph_consent_granted BOOLEAN DEFAULT FALSE
            """))
            conn.commit()
            print("✓ Added graph_consent_granted column to users table")
        except Exception as e:
            conn.rollback()
            if 'already exists' in str(e) or 'duplicate column' in str(e).lower():
                print("⊘ graph_consent_granted column already exists")
            else:
                print(f"✗ Error adding graph_consent_granted: {e}")

        # Add graph_consent_date to users table
        try:
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN graph_consent_date TIMESTAMP
            """))
            conn.commit()
            print("✓ Added graph_consent_date column to users table")
        except Exception as e:
            conn.rollback()
            if 'already exists' in str(e) or 'duplicate column' in str(e).lower():
                print("⊘ graph_consent_date column already exists")
            else:
                print(f"✗ Error adding graph_consent_date: {e}")

        # Add scanned_by to email_scan_log table
        try:
            conn.execute(text("""
                ALTER TABLE email_scan_log
                ADD COLUMN scanned_by INTEGER REFERENCES users(id)
            """))
            conn.commit()
            print("✓ Added scanned_by column to email_scan_log table")
        except Exception as e:
            conn.rollback()
            if 'already exists' in str(e) or 'duplicate column' in str(e).lower():
                print("⊘ scanned_by column already exists")
            else:
                print(f"✗ Error adding scanned_by: {e}")

    print("\nMigration complete!")


if __name__ == '__main__':
    migrate()
