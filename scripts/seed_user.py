"""
Seed a new user into the users table.

Usage:
  python3 scripts/seed_user.py "Jane Doe" "jane@avilacapllc.com" "entra-id-guid-here"
"""

import os
import sys
from datetime import datetime

# Add app/ to path
APP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app')
sys.path.insert(0, APP_DIR)

from db import get_session
from models import User

def seed_user(display_name: str, email: str, entra_id: str):
    """Seed a new user into the users table."""
    session = get_session()
    try:
        # Check if user already exists
        existing = session.query(User).filter(User.entra_id == entra_id).first()
        if existing:
            print(f"User with entra_id {entra_id} already exists: {existing.display_name}")
            return

        # Create new user
        new_user = User(
            entra_id=entra_id,
            email=email,
            display_name=display_name,
            created_at=datetime.utcnow(),
            briefing_enabled=False,
            briefing_scope='none',
            graph_consent_granted=False,
        )
        session.add(new_user)
        session.commit()
        print(f"User created: {display_name} ({email}) with entra_id {entra_id}")

    except Exception as e:
        session.rollback()
        print(f"Failed to seed user: {e}")
        raise
    finally:
        session.close()


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python3 scripts/seed_user.py \"Display Name\" \"email@avilacapllc.com\" \"entra-id-guid\"")
        sys.exit(1)

    display_name = sys.argv[1]
    email = sys.argv[2]
    entra_id = sys.argv[3]

    seed_user(display_name, email, entra_id)
