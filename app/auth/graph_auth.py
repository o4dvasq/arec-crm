"""
graph_auth.py — MSAL authentication for Microsoft Graph API (CC-04)

Two authentication modes:
1. App-only (client credentials) — used by web routes and background jobs.
   Requires AZURE_CLIENT_SECRET. Tokens auto-refresh, no user interaction.
   Needs admin-consented application permissions (Mail.Read, Calendars.Read, etc.)

2. Delegated (device code flow) — used by CLI scripts (drain_inbox.py, main.py).
   Caches refresh token to disk. Falls back to interactive device flow.
"""

import os

import msal

# Delegated scopes (for device code flow)
DELEGATED_SCOPES = [
    "https://graph.microsoft.com/Mail.Read",
    "https://graph.microsoft.com/Mail.Read.Shared",
    "https://graph.microsoft.com/Calendars.Read",
    "https://graph.microsoft.com/Chat.Read",
    "https://graph.microsoft.com/User.Read",
    "https://graph.microsoft.com/Contacts.Read",
]

# App-only scope (client credentials always use .default)
APP_ONLY_SCOPE = ["https://graph.microsoft.com/.default"]

TOKEN_CACHE_PATH = os.path.expanduser("~/.arec_briefing_token_cache.json")


# ---------------------------------------------------------------------------
# App-only (client credentials) — for web routes
# ---------------------------------------------------------------------------

_confidential_app = None


def _get_confidential_app():
    """Lazy-init a ConfidentialClientApplication for client credentials flow."""
    global _confidential_app
    if _confidential_app is not None:
        return _confidential_app

    client_id = os.environ.get("AZURE_CLIENT_ID")
    tenant_id = os.environ.get("AZURE_TENANT_ID")
    client_secret = os.environ.get("AZURE_CLIENT_SECRET") or os.environ.get("ENTRA_CLIENT_SECRET")

    if not client_id or not tenant_id:
        raise RuntimeError(
            "AZURE_CLIENT_ID and AZURE_TENANT_ID must be set in environment / .env"
        )
    if not client_secret:
        raise RuntimeError(
            "AZURE_CLIENT_SECRET (or ENTRA_CLIENT_SECRET) must be set for app-only Graph auth. "
            "This is available in Azure Key Vault (ENTRA-CLIENT-SECRET)."
        )

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    _confidential_app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret,
    )
    return _confidential_app


def get_app_token() -> str:
    """
    Get an app-only access token via client credentials flow.

    No user interaction required. Tokens auto-refresh via MSAL's internal cache.
    Requires admin-consented application permissions in Azure AD.

    Returns:
        A valid Bearer token string.

    Raises:
        RuntimeError: If credentials are missing or token acquisition fails.
    """
    app = _get_confidential_app()
    result = app.acquire_token_for_client(scopes=APP_ONLY_SCOPE)

    if "access_token" not in result:
        error = result.get("error_description", result.get("error", "Unknown error"))
        raise RuntimeError(f"App-only Graph auth failed: {error}")

    return result["access_token"]


# ---------------------------------------------------------------------------
# Delegated (device code flow) — for CLI scripts
# ---------------------------------------------------------------------------

def _load_cache():
    cache = msal.SerializableTokenCache()
    if os.path.exists(TOKEN_CACHE_PATH):
        with open(TOKEN_CACHE_PATH, "r") as f:
            cache.deserialize(f.read())
    return cache


def _save_cache(cache):
    if cache.has_state_changed:
        with open(TOKEN_CACHE_PATH, "w") as f:
            f.write(cache.serialize())


def _build_public_app(cache):
    client_id = os.environ.get("AZURE_CLIENT_ID")
    tenant_id = os.environ.get("AZURE_TENANT_ID")
    if not client_id or not tenant_id:
        raise RuntimeError(
            "AZURE_CLIENT_ID and AZURE_TENANT_ID must be set in environment / .env"
        )
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    return msal.PublicClientApplication(
        client_id, authority=authority, token_cache=cache
    )


def get_access_token(allow_device_flow: bool = True) -> str:
    """
    Return a valid Bearer token for Microsoft Graph (delegated).

    Flow:
    1. Try app-only token first (if client secret available).
    2. Fall back to cached delegated token (silent refresh).
    3. If allow_device_flow=True and no cached token, initiate device code flow.

    Args:
        allow_device_flow: If False, raise error instead of initiating device flow.
                          Use False when calling from web contexts where user can't interact.
    """
    # Try app-only first — works in web and background contexts
    try:
        return get_app_token()
    except RuntimeError:
        pass  # No client secret or acquisition failed; fall through to delegated

    # Delegated flow
    cache = _load_cache()
    app = _build_public_app(cache)

    # Try silent acquisition using cached account
    accounts = app.get_accounts()
    result = None
    if accounts:
        result = app.acquire_token_silent_with_error(DELEGATED_SCOPES, account=accounts[0])

    # If the grant was revoked (e.g. password reset), clear the stale cache
    if result and "error" in result and "access_token" not in result:
        error_code = result.get("error", "")
        if error_code in ("invalid_grant", "interaction_required"):
            if os.path.exists(TOKEN_CACHE_PATH):
                os.remove(TOKEN_CACHE_PATH)
            result = None

    # Device code flow
    if not result or "access_token" not in result:
        if not allow_device_flow:
            reason = ""
            if result and "error_description" in result:
                reason = f": {result['error_description']}"
            elif result and "error" in result:
                reason = f": {result['error']}"
            raise RuntimeError(
                "Authentication required — token is expired or revoked"
                + reason
                + ". Run `python app/main.py` to re-authenticate."
            )

        flow = app.initiate_device_flow(scopes=DELEGATED_SCOPES)
        if "user_code" not in flow:
            raise RuntimeError(f"Device flow initiation failed: {flow}")

        print("\n" + flow["message"])
        print("Waiting for authentication...\n")

        result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        error = result.get("error_description", result.get("error", "Unknown error"))
        raise RuntimeError(f"Authentication failed: {error}")

    _save_cache(cache)
    return result["access_token"]
