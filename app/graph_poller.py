"""
Multi-user Graph API email polling for AREC CRM.

This module implements background email polling that:
1. Iterates over users with graph_consent_granted=True
2. Acquires Graph API tokens for each user
3. Calls crm_graph_sync.run_auto_capture() with user_id parameter
4. Records scanned_by attribution in email_scan_log

Usage:
    python3 app/graph_poller.py              # Run once
    
    # Or schedule via cron (hourly):
    0 * * * * cd /path/to/arec-crm && python3 app/graph_poller.py
"""

import os
import sys
import logging
from datetime import datetime

# Add app directory to path
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(APP_DIR, '.env'))

from db import get_session
from models import User
from sources.crm_graph_sync import run_auto_capture
from auth.graph_auth import get_access_token

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def poll_all_users():
    """
    Poll emails for all users who have granted graph consent.
    
    Returns:
        dict: Statistics about the polling run (users scanned, emails found, etc.)
    """
    db_session = get_session()
    stats = {
        'users_scanned': 0,
        'users_skipped': 0,
        'total_emails_found': 0,
        'total_interactions_created': 0,
        'errors': []
    }
    
    try:
        # Get all users with graph consent granted
        users = db_session.query(User).filter(
            User.graph_consent_granted == True,
            User.is_active == True
        ).all()
        
        logger.info(f"Found {len(users)} users with graph consent granted")
        
        for user in users:
            try:
                logger.info(f"Polling emails for user: {user.email}")
                
                # Acquire Graph API token for this user
                # Note: This requires the user to have previously authenticated
                # and their refresh token to be stored/available
                token = get_access_token(allow_device_flow=False)
                
                # Run auto-capture for this user
                user_stats = run_auto_capture(token, user_id=user.id)
                
                stats['users_scanned'] += 1
                stats['total_emails_found'] += user_stats.get('emails_found', 0)
                stats['total_interactions_created'] += user_stats.get('interactions_created', 0)
                
                logger.info(f"Completed polling for {user.email}: "
                          f"{user_stats.get('emails_found', 0)} emails, "
                          f"{user_stats.get('interactions_created', 0)} interactions")
                
            except Exception as e:
                logger.error(f"Error polling emails for {user.email}: {e}")
                stats['errors'].append(f"{user.email}: {str(e)}")
                stats['users_skipped'] += 1
        
        logger.info(f"Polling complete. Stats: {stats}")
        return stats
        
    finally:
        db_session.close()


def main():
    """Main entry point for graph poller."""
    logger.info("Starting multi-user email polling...")
    stats = poll_all_users()
    
    print("\n" + "="*60)
    print("AREC CRM Multi-User Email Polling - Complete")
    print("="*60)
    print(f"Users scanned: {stats['users_scanned']}")
    print(f"Users skipped: {stats['users_skipped']}")
    print(f"Total emails found: {stats['total_emails_found']}")
    print(f"Total interactions created: {stats['total_interactions_created']}")
    
    if stats['errors']:
        print(f"\nErrors ({len(stats['errors'])}):")
        for error in stats['errors']:
            print(f"  - {error}")
    
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
