#!/usr/bin/env python3
"""
Migration: Add auth columns to users table (role, display_name, last_login_at, created_at).

Idempotent — safe to run multiple times.
"""

import os
import sys

# Add app directory to path
APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
sys.path.insert(0, APP_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(APP_DIR, '.env'))

from sqlalchemy import text
from db import init_db


def migrate():
    """Add role, display_name, last_login_at, created_at columns if they don't exist."""
    engine = init_db()

    migrations = [
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'user'
        """,
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS display_name VARCHAR(255)
        """,
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP
        """,
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()
        """,
    ]

    with engine.connect() as conn:
        for sql in migrations:
            print(f"Running: {sql.strip()[:60]}...")
            conn.execute(text(sql))
            conn.commit()

    print("✓ Migration complete. All auth columns added.")


if __name__ == '__main__':
    migrate()
