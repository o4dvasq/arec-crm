"""email_matching.py — Participant/org matching utilities for email processing."""

import os
import yaml

from sources.crm_reader import find_person_by_email

# Internal AREC domains to skip
INTERNAL_DOMAINS = {
    "avilacapllc.com",
    "avilacapital.com",
    "builderadvisorgroup.com",
}


def _get_user_email() -> str:
    """Get user email from config or env."""
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.yaml')
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = yaml.safe_load(f)
            if config and 'graph' in config:
                return config['graph'].get('user_email', '')
    return os.getenv('MS_USER_ID', 'oscar@avilacapllc.com')


def _is_internal(email: str) -> bool:
    if not email:
        return True
    email_lower = email.lower()
    domain = email_lower.split("@")[-1]
    if domain in INTERNAL_DOMAINS:
        return True
    user_email = _get_user_email().lower()
    if user_email and email_lower == user_email:
        return True
    return False


def _fuzzy_match_org(display_name: str, org_names: list[str]) -> str | None:
    """
    Substring fuzzy match: find a single org whose name appears in or contains
    the display name (≥6 character overlap). Returns org name or None.
    If multiple orgs match, return None (ambiguous).
    """
    display_lower = display_name.lower()
    matches = []

    for org_name in org_names:
        org_lower = org_name.lower()
        overlap = min(len(org_lower), len(display_lower))
        if overlap < 6:
            continue
        if org_lower in display_lower or display_lower in org_lower:
            matches.append(org_name)

    if len(matches) == 1:
        return matches[0]
    return None


def _resolve_participant(email: str, display_name: str, all_org_names: list[str]) -> dict | None:
    """
    Try to resolve a participant (email + display name) to a CRM org.
    Returns {'org': name, 'contact': display_name} or None.
    """
    if _is_internal(email):
        return None

    # 1. Email exact match via person files
    person = find_person_by_email(email)
    if person:
        org = person.get("organization") or person.get("org", "")
        if org:
            return {"org": org, "contact": person.get("name", display_name)}

    # 2. Org name fuzzy match on display name
    org_match = _fuzzy_match_org(display_name, all_org_names)
    if org_match:
        return {"org": org_match, "contact": display_name}

    return None
