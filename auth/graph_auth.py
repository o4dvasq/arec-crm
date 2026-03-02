"""
graph_auth.py — MSAL authentication for Microsoft Graph API (CC-04)

Device code flow (headless-friendly). Caches token to disk.
"""

import json
import os

import msal

SCOPES = [
    "https://graph.microsoft.com/Mail.Read",
    "https://graph.microsoft.com/Calendars.Read",
    "https://graph.microsoft.com/Chat.Read",
    "https://graph.microsoft.com/User.Read",
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


def get_access_token() -> str:
    """
    Return a valid Bearer token for Microsoft Graph.

    Flow:
    1. Check token cache for a valid (non-expired) token — return silently.
    2. Try silent refresh from cache.
    3. If no usable token, initiate device code flow (prints URL + code).
    """
    cache = _load_cache()
    app = _build_app(cache)

    # 1 + 2: Try silent acquisition using any cached account
    accounts = app.get_accounts()
    result = None
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    # 3: Device code flow
    if not result or "access_token" not in result:
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
