"""
graph_auth.py — MSAL authentication for Microsoft Graph API (CC-04)

Device code flow (headless-friendly). Caches token to disk.
"""

import json
import os

import msal

SCOPES = [
    "https://graph.microsoft.com/Mail.Read",
    "https://graph.microsoft.com/Mail.Read.Shared",
    "https://graph.microsoft.com/Calendars.Read",
    "https://graph.microsoft.com/Chat.Read",
    "https://graph.microsoft.com/User.Read",
    "https://graph.microsoft.com/Contacts.Read",
]

TOKEN_CACHE_PATH = os.path.expanduser("~/.arec_briefing_token_cache.json")


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


def _build_app(cache):
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
    Return a valid Bearer token for Microsoft Graph.

    Flow:
    1. Check token cache for a valid (non-expired) token — return silently.
    2. Try silent refresh from cache.
    3. If no usable token and allow_device_flow=True, initiate device code flow (prints URL + code).

    Args:
        allow_device_flow: If False, raise error instead of initiating device flow.
                          Use False when calling from web contexts where user can't interact.
    """
    cache = _load_cache()
    app = _build_app(cache)

    # 1 + 2: Try silent acquisition using any cached account
    accounts = app.get_accounts()
    result = None
    if accounts:
        result = app.acquire_token_silent_with_error(SCOPES, account=accounts[0])

    # If the grant was revoked (e.g. password reset), clear the stale cache so
    # the next device-flow run starts fresh rather than re-hitting the bad token.
    if result and "error" in result and "access_token" not in result:
        error_code = result.get("error", "")
        if error_code in ("invalid_grant", "interaction_required"):
            if os.path.exists(TOKEN_CACHE_PATH):
                os.remove(TOKEN_CACHE_PATH)
            result = None  # fall through to device flow or raise below

    # 3: Device code flow
    if not result or "access_token" not in result:
        if not allow_device_flow:
            # Surface the actual reason from Azure AD when available
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

        flow = app.initiate_device_flow(scopes=SCOPES)
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
