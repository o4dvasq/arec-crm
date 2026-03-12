"""
Graph API email poller for multi-user CRM.

Runs hourly (via Azure Function timer trigger or cron job).
Iterates over users where graph_consent_granted = True,
acquires a token for each, and calls run_auto_capture() with user_id.
"""

import os
import sys
from datetime import datetime

# Add app/ to path
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(APP_DIR, ".env"))

from db import get_session
from models import User
from auth.graph_auth import get_access_token
from sources.crm_graph_sync import run_auto_capture


def poll_all_users():
    """Poll email for all users with graph_consent_granted = True."""
    session = get_session()
    try:
        users = session.query(User).filter(User.graph_consent_granted == True).all()

        if not users:
            print("[graph_poller] No users with graph consent granted")
            return

        print(f"[graph_poller] Polling {len(users)} user(s)...")

        for user in users:
            print(f"[graph_poller] Processing {user.display_name} ({user.email})...")
            try:
                # Acquire token for this user
                # NOTE: In production, this would use application permissions (Mail.Read)
                # with client credentials flow. For Phase 1, we use delegated permissions
                # with cached tokens.
                token = get_access_token(allow_device_flow=False)

                # Run auto-capture with user_id attribution
                stats = run_auto_capture(token, user_id=user.id)

                print(f"[graph_poller] {user.display_name}: {stats.get('matched', 0)} matched, "
                      f"{stats.get('unmatched', 0)} unmatched, "
                      f"{stats.get('skipped_dedup', 0)} skipped")

            except Exception as e:
                print(f"[graph_poller] Error processing {user.email}: {e}")
                continue

        print("[graph_poller] Polling complete")

    except Exception as e:
        print(f"[graph_poller] Fatal error: {e}")
        raise
    finally:
        session.close()


if __name__ == '__main__':
    poll_all_users()
