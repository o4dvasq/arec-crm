"""
migrate_add_enrichment_columns.py

Adds linkedin_url, enriched_at, and enrichment_source columns to the contacts table.

Usage:
    python scripts/migrate_add_enrichment_columns.py
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'app')
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(APP_DIR, '.env'))

from sqlalchemy import text
from db import init_db


MIGRATIONS = [
    ("linkedin_url",       "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS linkedin_url VARCHAR(500)"),
    ("enriched_at",        "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMP"),
    ("enrichment_source",  "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS enrichment_source JSONB"),
]


def run():
    engine = init_db()
    with engine.connect() as conn:
        for col_name, sql in MIGRATIONS:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"  [ok] {col_name}")
            except Exception as e:
                conn.rollback()
                print(f"  [skip] {col_name}: {e}")
    print("Done.")


if __name__ == '__main__':
    run()
