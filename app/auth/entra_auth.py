"""
Microsoft Entra ID (Azure AD) SSO authentication for AREC CRM.

Uses MSAL (Microsoft Authentication Library) for Python to authenticate
users via OAuth 2.0 / OpenID Connect.

Supports DEV_USER environment variable for local development.
"""

import os
import logging
from functools import wraps
from datetime import datetime
from flask import session, redirect, request, url_for, g
from msal import ConfidentialClientApplication

# Configuration from environment (support both ENTRA_* and AZURE_* names)
CLIENT_ID = os.environ.get('AZURE_CLIENT_ID') or os.environ.get('ENTRA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('AZURE_CLIENT_SECRET') or os.environ.get('ENTRA_CLIENT_SECRET')
TENANT_ID = os.environ.get('AZURE_TENANT_ID') or os.environ.get('ENTRA_TENANT_ID', '064d6342-5dc5-424e-802f-53ff17bc02be')
AUTHORITY = os.environ.get('AZURE_AUTHORITY', f'https://login.microsoftonline.com/{TENANT_ID}')
REDIRECT_URI = os.environ.get('AZURE_REDIRECT_URI', 'http://localhost:3001/.auth/login/aad/callback')
DEV_USER = os.environ.get('DEV_USER')

SCOPES = ['User.Read']  # OpenID Connect scopes

logger = logging.getLogger(__name__)


def init_msal_app():
    """Initialize MSAL confidential client application."""
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError(
            'AZURE_CLIENT_ID and AZURE_CLIENT_SECRET must be set. '
            'See .env.azure for template.'
        )

    return ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )


def get_auth_url():
    """Generate the Microsoft login URL."""
    msal_app = init_msal_app()
    auth_url = msal_app.get_authorization_request_url(
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    return auth_url


def acquire_token_from_code(code: str):
    """Exchange authorization code for access token."""
    msal_app = init_msal_app()
    result = msal_app.acquire_token_by_authorization_code(
        code,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    return result


def get_user_from_token(token_response: dict) -> dict:
    """Extract user info from token response.

    Returns dict with:
        - entra_id: User's object ID in Entra ID
        - email: User's email address
        - display_name: User's display name
    """
    id_token_claims = token_response.get('id_token_claims', {})

    return {
        'entra_id': id_token_claims.get('oid', ''),
        'email': id_token_claims.get('preferred_username', ''),
        'display_name': id_token_claims.get('name', ''),
    }


def get_or_create_user(email: str, entra_id: str = None, display_name: str = None) -> dict:
    """Get user from database or auto-provision if doesn't exist.

    Args:
        email: User's email address
        entra_id: User's Entra ID object ID (optional)
        display_name: User's display name (optional)

    Returns:
        dict with id, email, display_name, role, last_login_at
    """
    from models import User
    from db import get_session

    db_session = get_session()
    try:
        user = db_session.query(User).filter_by(email=email).first()

        if not user:
            # Auto-provision new user
            role = 'admin' if email == 'oscar@avilacapllc.com' else 'user'
            user = User(
                entra_id=entra_id or f'dev-{email}',
                email=email,
                display_name=display_name or email.split('@')[0],
                role=role,
                created_at=datetime.now(),
                last_login=datetime.now()
            )
            db_session.add(user)
            db_session.commit()
            logger.info(f"Auto-provisioned new user: {email} (role={role})")
        else:
            # Update last login
            user.last_login = datetime.now()
            # Update entra_id if it's a placeholder or dev
            if entra_id and (user.entra_id.startswith('placeholder-') or user.entra_id.startswith('dev-')):
                user.entra_id = entra_id
            db_session.commit()

        return {
            'id': user.id,
            'email': user.email,
            'display_name': user.display_name,
            'role': user.role,
            'last_login_at': user.last_login.isoformat() if user.last_login else None
        }
    finally:
        db_session.close()


def login_required(f):
    """Decorator to require authentication for a route.

    Usage:
        @app.route('/protected')
        @login_required
        def protected_route():
            return f"Hello, {g.user['display_name']}"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            # Save the intended destination
            session['next'] = request.url
            return redirect(url_for('login'))
        # Populate g.user for the request
        g.user = session['user']
        return f(*args, **kwargs)
    return decorated_function


def log_dev_user_warning():
    """Log warning if DEV_USER is set (dev mode active)."""
    if DEV_USER:
        logger.warning(
            f"⚠️  WARNING: DEV_USER is set ({DEV_USER}) — authentication is bypassed. "
            "Do not use in production."
        )


def init_auth_routes(app):
    """Register authentication routes on the Flask app.

    Call this from dashboard.py after app initialization.
    """
    # Log warning if DEV_USER is set
    log_dev_user_warning()

    @app.route('/.auth/login/aad')
    def login():
        """Redirect to Microsoft login page."""
        auth_url = get_auth_url()
        return redirect(auth_url)

    @app.route('/.auth/login/aad/callback')
    def auth_callback():
        """Handle the redirect from Microsoft after authentication."""
        code = request.args.get('code')
        if not code:
            return "Error: No authorization code received", 400

        try:
            token_response = acquire_token_from_code(code)
        except Exception as e:
            return f"Error acquiring token: {e}", 500

        if 'error' in token_response:
            return f"Authentication error: {token_response.get('error_description', 'Unknown error')}", 400

        # Extract user info from token
        user_info = get_user_from_token(token_response)

        # Auto-provision or get existing user from database
        user_record = get_or_create_user(
            email=user_info['email'],
            entra_id=user_info['entra_id'],
            display_name=user_info['display_name']
        )

        # Store user in session
        session['user'] = user_record
        session['access_token'] = token_response.get('access_token')

        # Redirect to the originally requested page or dashboard
        next_url = session.pop('next', '/')
        return redirect(next_url)

    @app.route('/.auth/logout')
    def logout():
        """Clear session and redirect to Microsoft logout."""
        session.clear()
        # Redirect to Microsoft logout endpoint
        logout_url = f"{AUTHORITY}/oauth2/v2.0/logout?post_logout_redirect_uri={request.url_root}"
        return redirect(logout_url)

    @app.before_request
    def load_user():
        """Make user available via g.user on every request.

        Priority:
        1. DEV_USER environment variable (local dev only)
        2. Session user (after OAuth login)
        """
        # DEV_USER bypass for local development
        if DEV_USER:
            g.user = get_or_create_user(email=DEV_USER)
            return

        # Load user from session (set during OAuth callback)
        g.user = session.get('user')
